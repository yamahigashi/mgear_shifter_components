"""Proof-of-concept curve fitting without per-iteration scene updates.

This module intentionally keeps the scope narrow:

* non-rational NURBS curves
* fixed sample parameters captured from the initial curves
* analytic distance-loss gradients
* one optional scene write-back at the end

The goal is to validate the performance direction before replacing
``fit_curve.py``.
"""
from __future__ import annotations

import math
from contextlib import contextmanager
from dataclasses import dataclass
from logging import DEBUG, INFO, StreamHandler, getLogger
from collections.abc import Iterator, Sequence


import maya.api.OpenMaya as om2
import maya.cmds as cmds

from . import curve


handler = StreamHandler()
handler.setLevel(DEBUG)
logger = getLogger(__name__)
logger.setLevel(INFO)
if not logger.handlers:
    logger.addHandler(handler)
logger.propagate = False


@dataclass
class NurbsCurveSnapshot:
    """Static curve data used by the pure Python evaluator."""

    degree: int
    form: int
    knots: list[float]
    cvs_world: list[om2.MPoint]
    world_matrix: om2.MMatrix
    world_matrix_inv: om2.MMatrix

    @property
    def num_cvs(self) -> int:
        return len(self.cvs_world)

    @property
    def is_closed(self) -> bool:
        return _is_closed_form(self.form)

    @property
    def is_periodic(self) -> bool:
        return _is_periodic_form(self.form)


@dataclass
class FitContext:
    """Precomputed fitting data for scene-free optimization."""

    source: NurbsCurveSnapshot
    source_sample_mode: str
    sample_params: list[float]
    sample_basis: list[list[tuple[int, float]]]
    target_points: list[om2.MPoint]


@dataclass
class FitResult:
    """Optimization result."""

    positions_world: list[om2.MPoint]
    initial_loss: float
    final_loss: float
    iterations: int
    initial_smoothness_loss: float = 0.0
    final_smoothness_loss: float = 0.0
    initial_objective_loss: float = 0.0
    final_objective_loss: float = 0.0
    smoothness_weight: float = 0.0
    effective_smoothness_weight: float = 0.0
    smoothness_cv_scale: float = 1.0
    target_complexity: float = 0.0
    smoothness_complexity_scale: float = 1.0
    symmetry: bool = False
    symmetry_axis: str = "X"
    scene_loss_after_write: float | None = None
    scene_smoothness_loss_after_write: float | None = None
    scene_objective_loss_after_write: float | None = None
    max_write_error: float | None = None


@dataclass
class EvaluatorValidation:
    """Difference between Maya curve evaluation and the POC evaluator."""

    max_error: float
    mean_error: float
    num_samples: int


def _as_mfn_curve(curve_like: om2.MFnNurbsCurve | str | object) -> om2.MFnNurbsCurve:
    if isinstance(curve_like, om2.MFnNurbsCurve):
        return curve_like
    return curve.getMFnNurbsCurve(curve_like)


def _is_rational(mfn_curve: om2.MFnNurbsCurve) -> bool:
    attr = getattr(mfn_curve, "isRational", False)
    if callable(attr):
        return bool(attr())
    return bool(attr)


def _form_constant(name: str, fallback: int) -> int:
    return int(getattr(om2.MFnNurbsCurve, name, fallback))


def _is_periodic_form(form: int) -> bool:
    return int(form) == _form_constant("kPeriodic", 3)


def _is_closed_form(form: int) -> bool:
    return int(form) in (
        _form_constant("kClosed", 2),
        _form_constant("kPeriodic", 3),
    )


def _external_knot_vector(maya_knots: Sequence[float], form: int) -> list[float]:
    if _is_periodic_form(form):
        first_interval = maya_knots[1] - maya_knots[0]
        last_interval = maya_knots[-1] - maya_knots[-2]
        return [maya_knots[0] - first_interval, *maya_knots, maya_knots[-1] + last_interval]

    return [maya_knots[0], *maya_knots, maya_knots[-1]]


def _full_knot_vector(mfn_curve: om2.MFnNurbsCurve, degree: int, num_cvs: int, form: int) -> list[float]:
    """Return a full knot vector suitable for standard basis evaluation.

    Maya exposes ``numCVs + degree - 1`` knots for regular curves, omitting
    one duplicated knot at each end. The standard Cox-de Boor evaluator needs
    ``numCVs + degree + 1`` values, so this fills those two endpoint knots.
    Periodic curves use offset endpoint knots instead of duplicated ones.
    """
    maya_knots = [float(k) for k in mfn_curve.knots()]
    expected_full = num_cvs + degree + 1

    if len(maya_knots) == expected_full:
        return maya_knots

    if len(maya_knots) == expected_full - 2:
        return _external_knot_vector(maya_knots, form)

    raise ValueError(
        "Unsupported knot count: got {}, expected {} or {}.".format(
            len(maya_knots),
            expected_full - 2,
            expected_full,
        ),
    )


def snapshot_curve(curve_like: om2.MFnNurbsCurve | str | object) -> NurbsCurveSnapshot:
    """Capture curve data needed by the scene-free evaluator."""
    mfn_curve = _as_mfn_curve(curve_like)
    mfn_curve.updateCurve()
    if _is_rational(mfn_curve):
        raise NotImplementedError("fit_curve_poc does not support rational curves yet.")

    degree = int(mfn_curve.degree)
    form = int(mfn_curve.form)
    cvs_world = list(mfn_curve.cvPositions(om2.MSpace.kWorld))
    knots = _full_knot_vector(mfn_curve, degree, len(cvs_world), form)
    dag_path = mfn_curve.getPath()

    return NurbsCurveSnapshot(
        degree=degree,
        form=form,
        knots=knots,
        cvs_world=cvs_world,
        world_matrix=dag_path.inclusiveMatrix(),
        world_matrix_inv=dag_path.inclusiveMatrixInverse(),
    )


def _sample_params_by_length(mfn_curve: om2.MFnNurbsCurve, num_samples: int) -> list[float]:
    if num_samples < 2:
        raise ValueError("num_samples must be at least 2.")

    mfn_curve.updateCurve()
    is_closed = _is_closed_form(int(mfn_curve.form))
    cycle_count = num_samples if is_closed else num_samples - 1
    total_length = float(mfn_curve.length())
    segment_length = total_length / float(cycle_count)

    if is_closed:
        pos0 = mfn_curve.cvPosition(0)
        _, start_param = mfn_curve.closestPoint(pos0)
        start_length = float(mfn_curve.findLengthFromParam(start_param))
    else:
        start_length = 0.0

    params = []
    for i in range(num_samples):
        length = segment_length * float(i) + start_length
        if length > total_length:
            if is_closed:
                length -= total_length
            else:
                length = total_length
        params.append(float(mfn_curve.findParamFromLength(length)))

    return params


def _sample_params_by_parameter(snapshot: NurbsCurveSnapshot, num_samples: int) -> list[float]:
    if num_samples < 2:
        raise ValueError("num_samples must be at least 2.")

    start = float(snapshot.knots[snapshot.degree])
    end = float(snapshot.knots[snapshot.num_cvs])
    if start == end:
        raise ValueError("Invalid curve parameter range: {} to {}.".format(start, end))

    if snapshot.is_closed:
        step = (end - start) / float(num_samples)
    else:
        step = (end - start) / float(num_samples - 1)

    params = []
    for i in range(num_samples):
        u = start + step * float(i)
        if u > end:
            u = end
        params.append(u)
    return params


def _find_span(num_cvs: int, degree: int, u: float, knots: Sequence[float]) -> int:
    n = num_cvs - 1

    if u >= knots[n + 1]:
        return n
    if u <= knots[degree]:
        return degree

    low = degree
    high = n + 1
    mid = (low + high) // 2
    while u < knots[mid] or u >= knots[mid + 1]:
        if u < knots[mid]:
            high = mid
        else:
            low = mid
        mid = (low + high) // 2
    return mid


def _basis_funs(span: int, u: float, degree: int, knots: Sequence[float]) -> list[float]:
    values = [0.0 for _ in range(degree + 1)]
    left = [0.0 for _ in range(degree + 1)]
    right = [0.0 for _ in range(degree + 1)]

    values[0] = 1.0
    for j in range(1, degree + 1):
        left[j] = u - knots[span + 1 - j]
        right[j] = knots[span + j] - u
        saved = 0.0
        for r in range(j):
            denominator = right[r + 1] + left[j - r]
            if denominator == 0.0:
                temp = 0.0
            else:
                temp = values[r] / denominator
            values[r] = saved + right[r + 1] * temp
            saved = left[j - r] * temp
        values[j] = saved

    return values


def basis_at_param(snapshot: NurbsCurveSnapshot, u: float) -> list[tuple[int, float]]:
    """Return non-zero basis weights as ``(cv_index, weight)`` pairs."""
    span = _find_span(snapshot.num_cvs, snapshot.degree, u, snapshot.knots)
    weights = _basis_funs(span, u, snapshot.degree, snapshot.knots)
    first = span - snapshot.degree
    return [
        (first + i, weight)
        for i, weight in enumerate(weights)
        if weight != 0.0 and 0 <= first + i < snapshot.num_cvs
    ]


def _master_cv_index(snapshot: NurbsCurveSnapshot, cv_index: int) -> int:
    if snapshot.is_periodic and cv_index >= snapshot.num_cvs - snapshot.degree:
        return cv_index - (snapshot.num_cvs - snapshot.degree)
    return cv_index


def _sync_periodic_bound_cvs(snapshot: NurbsCurveSnapshot, cvs_world: Sequence[om2.MPoint]) -> list[om2.MPoint]:
    synced = [om2.MPoint(point) for point in cvs_world]
    if not snapshot.is_periodic:
        return synced

    first_bound = snapshot.num_cvs - snapshot.degree
    for offset in range(snapshot.degree):
        synced[first_bound + offset] = om2.MPoint(synced[offset])
    return synced


def _normalized_cv_indices(snapshot: NurbsCurveSnapshot, cv_indices: Sequence[int] | None) -> list[int]:
    if cv_indices is None:
        limit = snapshot.num_cvs - snapshot.degree if snapshot.is_periodic else snapshot.num_cvs
        return list(range(limit))

    normalized = []
    seen = set()
    for cv_index in cv_indices:
        if cv_index < 0 or cv_index >= snapshot.num_cvs:
            raise IndexError("Invalid cv index: {}".format(cv_index))
        master_index = _master_cv_index(snapshot, cv_index)
        if master_index not in seen:
            normalized.append(master_index)
            seen.add(master_index)
    return normalized


def _axis_index(axis: str) -> int:
    try:
        return {"X": 0, "Y": 1, "Z": 2}[axis.upper()]
    except KeyError:
        raise ValueError("Unsupported symmetry_axis: {}".format(axis)) from None


def _to_symmetry_space(snapshot: NurbsCurveSnapshot, point: om2.MPoint) -> om2.MPoint:
    return om2.MPoint(point) * snapshot.world_matrix_inv


def _from_symmetry_space(snapshot: NurbsCurveSnapshot, point: om2.MPoint) -> om2.MPoint:
    return om2.MPoint(point) * snapshot.world_matrix


def _project_point_to_symmetry_axis(point: om2.MPoint, axis_index: int) -> om2.MPoint:
    projected = om2.MPoint(point)
    projected[axis_index] = 0.0
    return projected


def _closed_symmetry_pairs_and_centers_for_center(count: int, center_index: int) -> tuple[list[tuple[int, int]], list[int]]:
    if count <= 0:
        return [], []

    center_index %= count
    centers = [center_index]
    if count % 2 == 0:
        centers.append((center_index + count // 2) % count)
        pair_count = count // 2 - 1
    else:
        pair_count = count // 2

    pairs = [
        ((center_index + offset) % count, (center_index - offset) % count)
        for offset in range(1, pair_count + 1)
    ]
    return pairs, centers


def _symmetry_pairs_and_centers_for_count(count: int, closed: bool) -> tuple[list[tuple[int, int]], list[int]]:
    if count <= 0:
        return [], []

    if closed:
        return _closed_symmetry_pairs_and_centers_for_center(count, 0)

    pairs = [
        (i, count - 1 - i)
        for i in range(count // 2)
    ]
    centers = [count // 2] if count % 2 else []
    return pairs, centers


def _symmetry_score(points: Sequence[om2.MPoint], pairs: Sequence[tuple[int, int]], centers: Sequence[int], axis_index: int) -> float:
    score = 0.0
    for center_index in centers:
        score += abs(points[center_index][axis_index]) * 2.0

    for left_index, right_index in pairs:
        left_point = points[left_index]
        right_point = points[right_index]
        score += abs(left_point[axis_index] + right_point[axis_index])
        for component_index in range(3):
            if component_index == axis_index:
                continue
            score += abs(left_point[component_index] - right_point[component_index])
    return score


def _auto_symmetry_pairs_and_centers_for_points(points: Sequence[om2.MPoint], closed: bool, axis_index: int) -> tuple[list[tuple[int, int]], list[int]]:
    count = len(points)
    if count <= 0:
        return [], []

    if not closed:
        return _symmetry_pairs_and_centers_for_count(count, closed)

    # Closed/periodic CV index 0 is just a seam, not necessarily a mirror
    # center. Score every possible seam so common Maya circles do not pair the
    # wrong CVs when post-projecting symmetry.
    best_pairs = []
    best_centers = []
    best_score = None
    for center_index in range(count):
        pairs, centers = _closed_symmetry_pairs_and_centers_for_center(count, center_index)
        score = _symmetry_score(points, pairs, centers, axis_index)
        if best_score is None or score < best_score:
            best_pairs = pairs
            best_centers = centers
            best_score = score
    return best_pairs, best_centers


def _symmetry_pairs_and_centers(snapshot: NurbsCurveSnapshot, points: Sequence[om2.MPoint], axis_index: int) -> tuple[list[tuple[int, int]], list[int]]:
    count = _independent_cv_count(snapshot)
    return _auto_symmetry_pairs_and_centers_for_points(
        points[:count],
        snapshot.is_closed,
        axis_index,
    )


def _axis_side_sign(left_point: om2.MPoint, right_point: om2.MPoint, axis_index: int) -> float:
    if left_point[axis_index] > 0.0:
        return 1.0
    if left_point[axis_index] < 0.0:
        return -1.0
    if right_point[axis_index] > 0.0:
        return -1.0
    if right_point[axis_index] < 0.0:
        return 1.0
    return 1.0


def _symmetrized_pair_points(left_point: om2.MPoint, right_point: om2.MPoint, axis_index: int) -> tuple[om2.MPoint, om2.MPoint]:
    axis_magnitude = (abs(left_point[axis_index]) + abs(right_point[axis_index])) * 0.5
    side_sign = _axis_side_sign(left_point, right_point, axis_index)
    average = om2.MPoint(
        (left_point.x + right_point.x) * 0.5,
        (left_point.y + right_point.y) * 0.5,
        (left_point.z + right_point.z) * 0.5,
    )
    average[axis_index] = axis_magnitude * side_sign

    mirrored = om2.MPoint(average)
    mirrored[axis_index] = -average[axis_index]
    return average, mirrored


def apply_symmetry_projection(snapshot: NurbsCurveSnapshot, cvs_world: Sequence[om2.MPoint], axis: str = "X") -> list[om2.MPoint]:
    """Project CV positions onto the configured symmetry constraint."""
    axis_index = _axis_index(axis)
    projected_local = [_to_symmetry_space(snapshot, point) for point in cvs_world]
    pairs, centers = _symmetry_pairs_and_centers(snapshot, projected_local, axis_index)

    for left_index, right_index in pairs:
        left_point = projected_local[left_index]
        right_point = projected_local[right_index]
        projected_local[left_index], projected_local[right_index] = _symmetrized_pair_points(
            left_point,
            right_point,
            axis_index,
        )

    for center_index in centers:
        projected_local[center_index] = _project_point_to_symmetry_axis(projected_local[center_index], axis_index)

    projected = [_from_symmetry_space(snapshot, point) for point in projected_local]
    return _sync_periodic_bound_cvs(snapshot, projected)


def evaluate_point(cvs_world: Sequence[om2.MPoint], basis: Iterable[tuple[int, float]]) -> om2.MPoint:
    """Evaluate one point from precomputed sparse basis weights."""
    x = 0.0
    y = 0.0
    z = 0.0
    for cv_index, weight in basis:
        point = cvs_world[cv_index]
        x += point.x * weight
        y += point.y * weight
        z += point.z * weight
    return om2.MPoint(x, y, z)


def evaluate_points(cvs_world: Sequence[om2.MPoint], basis_list: Sequence[Sequence[tuple[int, float]]]) -> list[om2.MPoint]:
    """Evaluate multiple points from precomputed sparse basis weights."""
    return [evaluate_point(cvs_world, basis) for basis in basis_list]


def validate_snapshot_evaluator(curve_like: om2.MFnNurbsCurve | str | object, num_samples: int = 100) -> EvaluatorValidation:
    """Compare the POC evaluator with Maya's curve evaluation at fixed params."""
    mfn_curve = _as_mfn_curve(curve_like)
    snapshot = snapshot_curve(mfn_curve)
    sample_params = _sample_params_by_length(mfn_curve, num_samples)

    total_error = 0.0
    max_error = 0.0
    for u in sample_params:
        maya_point = mfn_curve.getPointAtParam(u, space=om2.MSpace.kWorld)
        poc_point = evaluate_point(snapshot.cvs_world, basis_at_param(snapshot, u))
        error = (maya_point - poc_point).length()
        total_error += error
        max_error = max(max_error, error)

    return EvaluatorValidation(
        max_error=max_error,
        mean_error=total_error / float(num_samples),
        num_samples=num_samples,
    )


def build_fit_context(
    curve_a: om2.MFnNurbsCurve | str | object,
    curve_b: om2.MFnNurbsCurve | str | object,
    num_samples: int = 100,
    source_sample_mode: str = "parameter",
) -> FitContext:
    """Precompute fixed source bases and target points.

    By default, source samples are taken from the knot parameter domain so
    repeated runs measure the same source locations. ``source_sample_mode`` can
    be set to ``"length"`` to use the source curve's initial arc-length spacing.
    Target samples are still captured by arc length because the target curve is
    not modified during optimization.
    """
    mfn_a = _as_mfn_curve(curve_a)
    mfn_b = _as_mfn_curve(curve_b)
    source = snapshot_curve(mfn_a)

    if source_sample_mode == "parameter":
        sample_params = _sample_params_by_parameter(source, num_samples)
    elif source_sample_mode == "length":
        sample_params = _sample_params_by_length(mfn_a, num_samples)
    else:
        raise ValueError("Unsupported source_sample_mode: {}".format(source_sample_mode))

    target_params = _sample_params_by_length(mfn_b, num_samples)
    sample_basis = [basis_at_param(source, u) for u in sample_params]
    target_points = [
        mfn_b.getPointAtParam(u, space=om2.MSpace.kWorld)
        for u in target_params
    ]

    return FitContext(
        source=source,
        source_sample_mode=source_sample_mode,
        sample_params=sample_params,
        sample_basis=sample_basis,
        target_points=target_points,
    )


def compute_distance_loss(cvs_world: Sequence[om2.MPoint], context: FitContext) -> float:
    """Compute mean squared distance loss without touching the scene."""
    source_points = evaluate_points(cvs_world, context.sample_basis)
    loss = 0.0
    for source_point, target_point in zip(source_points, context.target_points):
        diff = source_point - target_point
        loss += diff.x**2 + diff.y**2 + diff.z**2
    return loss / float(len(context.target_points))


def compute_distance_gradients(cvs_world: Sequence[om2.MPoint], context: FitContext, cv_indices: Sequence[int] | None = None) -> list[om2.MVector]:
    """Compute analytic gradients for the fixed-basis distance loss."""
    gradients = [om2.MVector(0.0, 0.0, 0.0) for _ in range(context.source.num_cvs)]
    active = None if cv_indices is None else set(_normalized_cv_indices(context.source, cv_indices))
    scale = 2.0 / float(len(context.target_points))

    for basis, target_point in zip(context.sample_basis, context.target_points):
        source_point = evaluate_point(cvs_world, basis)
        diff = source_point - target_point
        for cv_index, weight in basis:
            master_index = _master_cv_index(context.source, cv_index)
            if active is not None and master_index not in active:
                continue
            gradients[master_index] += diff * (scale * weight)

    return gradients


def _independent_cv_count(snapshot: NurbsCurveSnapshot) -> int:
    if snapshot.is_periodic:
        return snapshot.num_cvs - snapshot.degree
    return snapshot.num_cvs


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _average_segment_length(points: Sequence[om2.MPoint], closed: bool) -> float:
    if len(points) < 2:
        return 0.0

    count = len(points) if closed else len(points) - 1
    if count <= 0:
        return 0.0

    total = 0.0
    for i in range(count):
        total += (points[(i + 1) % len(points)] - points[i]).length()
    return total / float(count)


def compute_target_complexity(target_points: Sequence[om2.MPoint], closed: bool) -> float:
    """Return normalized target second-difference complexity."""
    if len(target_points) < 3:
        return 0.0

    if closed:
        triples = [
            ((i - 1) % len(target_points), i, (i + 1) % len(target_points))
            for i in range(len(target_points))
        ]
    else:
        triples = [
            (i - 1, i, i + 1)
            for i in range(1, len(target_points) - 1)
        ]

    total = 0.0
    for prev_index, index, next_index in triples:
        total += _second_difference(target_points, prev_index, index, next_index).length()

    average_segment_length = _average_segment_length(target_points, closed)
    if average_segment_length <= 0.0:
        return 0.0
    return (total / float(len(triples))) / average_segment_length


def compute_effective_smoothness_weight(
    context: FitContext,
    cv_indices: Sequence[int],
    smoothness_weight: float,
    smoothness_auto_scale: bool = True,
    smoothness_complexity_gain: float = 1.0,
) -> tuple[float, float, float, float]:
    """Scale smoothness weight by active CV count and target complexity."""
    if smoothness_weight == 0.0 or not smoothness_auto_scale:
        target_complexity = compute_target_complexity(context.target_points, context.source.is_closed)
        return smoothness_weight, 1.0, target_complexity, 1.0

    active_cv_count = float(len(cv_indices))
    if active_cv_count <= 0.0:
        cv_scale = 0.0
    else:
        cv_scale = _clamp((active_cv_count - 4.0) / active_cv_count, 0.0, 1.0)

    target_complexity = compute_target_complexity(context.target_points, context.source.is_closed)
    complexity_scale = 1.0 / (1.0 + target_complexity * smoothness_complexity_gain)
    effective_weight = smoothness_weight * cv_scale * complexity_scale
    return effective_weight, cv_scale, target_complexity, complexity_scale


def _is_ring_smoothness(snapshot: NurbsCurveSnapshot) -> bool:
    return snapshot.is_closed


def _smoothness_indices(snapshot: NurbsCurveSnapshot) -> list[tuple[int, int, int]]:
    count = _independent_cv_count(snapshot)
    if count < 3:
        return []

    if _is_ring_smoothness(snapshot):
        return [
            ((i - 1) % count, i, (i + 1) % count)
            for i in range(count)
        ]

    return [
        (i - 1, i, i + 1)
        for i in range(1, count - 1)
    ]


def _second_difference(cvs_world: Sequence[om2.MPoint], prev_index: int, cv_index: int, next_index: int) -> om2.MVector:
    prev_point = cvs_world[prev_index]
    point = cvs_world[cv_index]
    next_point = cvs_world[next_index]
    return om2.MVector(
        prev_point.x - point.x * 2.0 + next_point.x,
        prev_point.y - point.y * 2.0 + next_point.y,
        prev_point.z - point.z * 2.0 + next_point.z,
    )


def compute_smoothness_loss(cvs_world: Sequence[om2.MPoint], context: FitContext) -> float:
    """Compute mean squared second-difference loss for CV smoothness."""
    triples = _smoothness_indices(context.source)
    if not triples:
        return 0.0

    loss = 0.0
    for prev_index, cv_index, next_index in triples:
        diff = _second_difference(cvs_world, prev_index, cv_index, next_index)
        loss += diff.x**2 + diff.y**2 + diff.z**2
    return loss / float(len(triples))


def compute_smoothness_gradients(cvs_world: Sequence[om2.MPoint], context: FitContext, cv_indices: Sequence[int] | None = None) -> list[om2.MVector]:
    """Compute gradients for the second-difference smoothness loss."""
    gradients = [om2.MVector(0.0, 0.0, 0.0) for _ in range(context.source.num_cvs)]
    triples = _smoothness_indices(context.source)
    if not triples:
        return gradients

    active = None if cv_indices is None else set(_normalized_cv_indices(context.source, cv_indices))
    scale = 2.0 / float(len(triples))

    for prev_index, cv_index, next_index in triples:
        diff = _second_difference(cvs_world, prev_index, cv_index, next_index)
        contributions = (
            (prev_index, diff * scale),
            (cv_index, diff * (-2.0 * scale)),
            (next_index, diff * scale),
        )
        for target_index, contribution in contributions:
            master_index = _master_cv_index(context.source, target_index)
            if active is not None and master_index not in active:
                continue
            gradients[master_index] += contribution

    return gradients


def compute_objective_loss(cvs_world: Sequence[om2.MPoint], context: FitContext, smoothness_weight: float) -> tuple[float, float, float]:
    """Return ``(objective, distance, smoothness)`` for the current CV positions."""
    distance_loss = compute_distance_loss(cvs_world, context)
    smoothness_loss = compute_smoothness_loss(cvs_world, context)
    return (
        distance_loss + smoothness_weight * smoothness_loss,
        distance_loss,
        smoothness_loss,
    )


def compute_objective_gradients(cvs_world: Sequence[om2.MPoint], context: FitContext, cv_indices: Sequence[int] | None = None, smoothness_weight: float = 0.2) -> list[om2.MVector]:
    """Combine distance and smoothness gradients."""
    gradients = compute_distance_gradients(cvs_world, context, cv_indices)
    if smoothness_weight == 0.0:
        return gradients

    smoothness_gradients = compute_smoothness_gradients(cvs_world, context, cv_indices)
    for cv_index, smoothness_gradient in enumerate(smoothness_gradients):
        gradients[cv_index] += smoothness_gradient * smoothness_weight
    return gradients


def _sign_vector(vector: om2.MVector) -> om2.MVector:
    return om2.MVector(
        1.0 if vector.x > 0.0 else (-1.0 if vector.x < 0.0 else 0.0),
        1.0 if vector.y > 0.0 else (-1.0 if vector.y < 0.0 else 0.0),
        1.0 if vector.z > 0.0 else (-1.0 if vector.z < 0.0 else 0.0),
    )


def _lion_update_positions(
    cvs_world: Sequence[om2.MPoint],
    momentum: list[om2.MVector],
    gradients: Sequence[om2.MVector],
    cv_indices: Sequence[int],
    beta: float,
    learning_rate: float,
) -> list[om2.MPoint]:
    updated = [om2.MPoint(point) for point in cvs_world]
    for cv_index in cv_indices:
        momentum[cv_index] = momentum[cv_index] * beta + gradients[cv_index] * (1.0 - beta)
        updated[cv_index] = om2.MPoint(cvs_world[cv_index]) - _sign_vector(momentum[cv_index]) * learning_rate
    return updated


def _adam_update_positions(
    cvs_world: Sequence[om2.MPoint],
    first_moment: list[om2.MVector],
    second_moment: list[om2.MVector],
    gradients: Sequence[om2.MVector],
    cv_indices: Sequence[int],
    learning_rate: float,
    beta1: float,
    beta2: float,
    epsilon: float,
    step: int,
) -> list[om2.MPoint]:
    updated = [om2.MPoint(point) for point in cvs_world]
    bias_correction1 = 1.0 - beta1**step
    bias_correction2 = 1.0 - beta2**step

    for cv_index in cv_indices:
        gradient = gradients[cv_index]
        first_moment[cv_index] = first_moment[cv_index] * beta1 + gradient * (1.0 - beta1)
        second_moment[cv_index] = om2.MVector(
            second_moment[cv_index].x * beta2 + gradient.x * gradient.x * (1.0 - beta2),
            second_moment[cv_index].y * beta2 + gradient.y * gradient.y * (1.0 - beta2),
            second_moment[cv_index].z * beta2 + gradient.z * gradient.z * (1.0 - beta2),
        )
        m_hat = first_moment[cv_index] / bias_correction1
        v_hat = second_moment[cv_index] / bias_correction2
        update = om2.MVector(
            m_hat.x / (math.sqrt(v_hat.x) + epsilon),
            m_hat.y / (math.sqrt(v_hat.y) + epsilon),
            m_hat.z / (math.sqrt(v_hat.z) + epsilon),
        )
        updated[cv_index] = om2.MPoint(cvs_world[cv_index]) - update * learning_rate

    return updated


@contextmanager
def _undo_chunk(name: str) -> Iterator[None]:
    if not cmds.undoInfo(query=True, state=True):
        yield
        return

    cmds.undoInfo(openChunk=True, chunkName=name)
    try:
        yield
    finally:
        cmds.undoInfo(closeChunk=True)


def _editable_cv_count(mfn_curve: om2.MFnNurbsCurve) -> int:
    if _is_periodic_form(int(mfn_curve.form)):
        return int(mfn_curve.numCVs) - int(mfn_curve.degree)
    return int(mfn_curve.numCVs)


def _set_scene_cv_positions_api(mfn_curve: om2.MFnNurbsCurve, positions_world: Sequence[om2.MPoint]) -> None:
    positions_world = [om2.MPoint(point) for point in positions_world]
    if _is_periodic_form(int(mfn_curve.form)):
        # Periodic curves bind the trailing degree CVs to the first degree CVs.
        # Writing every CV with setCVPositions can make Maya remap those bound
        # CVs in a way that differs from this evaluator's positions. Write only
        # the independent CVs and let Maya maintain the periodic overlap.
        for cv_index in range(_editable_cv_count(mfn_curve)):
            mfn_curve.setCVPosition(cv_index, positions_world[cv_index], om2.MSpace.kWorld)
        mfn_curve.updateCurve()
        return

    mfn_curve.setCVPositions(positions_world, om2.MSpace.kWorld)
    mfn_curve.updateCurve()


def _set_scene_cv_positions_undoable(mfn_curve: om2.MFnNurbsCurve, positions_world: Sequence[om2.MPoint], undo_name: str) -> None:
    shape_name = mfn_curve.getPath().fullPathName()
    with _undo_chunk(undo_name):
        for cv_index in range(_editable_cv_count(mfn_curve)):
            point = positions_world[cv_index]
            cmds.xform(
                "{}.cv[{}]".format(shape_name, cv_index),
                worldSpace=True,
                absolute=True,
                translation=(point.x, point.y, point.z),
            )
        mfn_curve.updateCurve()


def set_scene_cv_positions(mfn_curve: om2.MFnNurbsCurve, positions_world: Sequence[om2.MPoint], undoable: bool = True, undo_name: str = "fit_curve_poc") -> None:
    """Write final world-space CV positions back to the scene once."""
    if len(positions_world) != mfn_curve.numCVs:
        raise ValueError("positions_world length does not match curve CV count.")

    if undoable:
        _set_scene_cv_positions_undoable(mfn_curve, positions_world, undo_name)
        return

    _set_scene_cv_positions_api(mfn_curve, positions_world)


def symmetry_curve_poc(curve_like: om2.MFnNurbsCurve | str | object, axis: str = "X", undoable: bool = True) -> list[om2.MPoint]:
    """Apply the POC symmetry projection to a scene curve and write it back."""
    mfn_curve = _as_mfn_curve(curve_like)
    snapshot = snapshot_curve(mfn_curve)
    positions = apply_symmetry_projection(snapshot, snapshot.cvs_world, axis)
    set_scene_cv_positions(
        mfn_curve,
        positions,
        undoable=undoable,
        undo_name="fit_curve_poc symmetry",
    )
    # Periodic curves expose trailing degree CVs that are bound copies of the
    # first CVs. Return only the editable/independent CVs to make diagnostics
    # match what this function actually writes.
    return positions[:_independent_cv_count(snapshot)]


def _max_position_error(points_a: Sequence[om2.MPoint], points_b: Sequence[om2.MPoint]) -> float:
    max_error = 0.0
    for point_a, point_b in zip(points_a, points_b):
        max_error = max(max_error, (point_a - point_b).length())
    return max_error


def optimize_context(
    context: FitContext,
    cv_indices: Sequence[int] | None = None,
    num_iterations: int = 30,
    learning_rate: float = 0.01,
    beta: float = 0.9,
    optimizer: str = "adam",
    smoothness_weight: float = 0.2,
    smoothness_auto_scale: bool = True,
    smoothness_complexity_gain: float = 1.0,
    adam_beta1: float = 0.9,
    adam_beta2: float = 0.999,
    adam_epsilon: float = 1e-8,
    symmetry: bool = False,
    symmetry_axis: str = "X",
) -> FitResult:
    """Optimize the snapshot CV array without updating any scene curve."""
    cv_indices = _normalized_cv_indices(context.source, cv_indices)
    if symmetry:
        _axis_index(symmetry_axis)

    smoothness_weight_data = compute_effective_smoothness_weight(
        context,
        cv_indices,
        smoothness_weight,
        smoothness_auto_scale,
        smoothness_complexity_gain,
    )
    effective_smoothness_weight, cv_scale, target_complexity, complexity_scale = smoothness_weight_data
    positions = _sync_periodic_bound_cvs(context.source, context.source.cvs_world)

    first_moment = [om2.MVector(0.0, 0.0, 0.0) for _ in range(context.source.num_cvs)]
    second_moment = [om2.MVector(0.0, 0.0, 0.0) for _ in range(context.source.num_cvs)]
    initial_objective_loss, initial_loss, initial_smoothness_loss = compute_objective_loss(
        positions,
        context,
        effective_smoothness_weight,
    )

    if optimizer not in ("adam", "lion"):
        raise ValueError("Unsupported optimizer: {}".format(optimizer))

    for step in range(1, num_iterations + 1):
        gradients = compute_objective_gradients(
            positions,
            context,
            cv_indices=cv_indices,
            smoothness_weight=effective_smoothness_weight,
        )
        if optimizer == "adam":
            positions = _adam_update_positions(
                positions,
                first_moment,
                second_moment,
                gradients,
                cv_indices,
                learning_rate,
                adam_beta1,
                adam_beta2,
                adam_epsilon,
                step,
            )
        else:
            positions = _lion_update_positions(
                positions,
                first_moment,
                gradients,
                cv_indices,
                beta,
                learning_rate,
            )
        positions = _sync_periodic_bound_cvs(context.source, positions)

    if symmetry:
        positions = apply_symmetry_projection(context.source, positions, symmetry_axis)

    final_objective_loss, final_loss, final_smoothness_loss = compute_objective_loss(
        positions,
        context,
        effective_smoothness_weight,
    )
    return FitResult(
        positions_world=positions,
        initial_loss=initial_loss,
        final_loss=final_loss,
        iterations=num_iterations,
        initial_smoothness_loss=initial_smoothness_loss,
        final_smoothness_loss=final_smoothness_loss,
        initial_objective_loss=initial_objective_loss,
        final_objective_loss=final_objective_loss,
        smoothness_weight=smoothness_weight,
        effective_smoothness_weight=effective_smoothness_weight,
        smoothness_cv_scale=cv_scale,
        target_complexity=target_complexity,
        smoothness_complexity_scale=complexity_scale,
        symmetry=bool(symmetry),
        symmetry_axis=symmetry_axis.upper(),
    )


def fit_curve_on_curve_poc(
    curve_a: om2.MFnNurbsCurve | str | object,
    curve_b: om2.MFnNurbsCurve | str | object,
    cv_indices: Sequence[int] | None = None,
    num_samples: int = 100,
    num_iterations: int = 30,
    learning_rate: float = 0.01,
    beta: float = 0.9,
    source_sample_mode: str = "parameter",
    optimizer: str = "adam",
    smoothness_weight: float = 0.2,
    smoothness_auto_scale: bool = True,
    smoothness_complexity_gain: float = 1.0,
    adam_beta1: float = 0.9,
    adam_beta2: float = 0.999,
    adam_epsilon: float = 1e-8,
    symmetry: bool = False,
    symmetry_axis: str = "X",
    write_back: bool = True,
    undoable: bool = True,
) -> FitResult:
    """Fit ``curve_a`` toward ``curve_b`` with no loop-time scene updates.

    If ``write_back`` is true, the optimized CVs are written to ``curve_a`` once
    after the optimization loop. Set it false to benchmark or inspect the result
    without changing the scene. ``undoable`` controls whether that final write
    uses Maya commands so Ctrl+Z/redo can restore it as a single undo item.
    """
    mfn_a = _as_mfn_curve(curve_a)
    context = build_fit_context(
        mfn_a,
        curve_b,
        num_samples=num_samples,
        source_sample_mode=source_sample_mode,
    )
    result = optimize_context(
        context,
        cv_indices=cv_indices,
        num_iterations=num_iterations,
        learning_rate=learning_rate,
        beta=beta,
        optimizer=optimizer,
        smoothness_weight=smoothness_weight,
        smoothness_auto_scale=smoothness_auto_scale,
        smoothness_complexity_gain=smoothness_complexity_gain,
        adam_beta1=adam_beta1,
        adam_beta2=adam_beta2,
        adam_epsilon=adam_epsilon,
        symmetry=symmetry,
        symmetry_axis=symmetry_axis,
    )

    if write_back:
        set_scene_cv_positions(
            mfn_a,
            result.positions_world,
            undoable=undoable,
            undo_name="fit_curve_poc fit",
        )
        scene_positions = _sync_periodic_bound_cvs(
            context.source,
            mfn_a.cvPositions(om2.MSpace.kWorld),
        )
        scene_objective, scene_distance, scene_smoothness = compute_objective_loss(
            scene_positions,
            context,
            result.effective_smoothness_weight,
        )
        result.scene_loss_after_write = scene_distance
        result.scene_smoothness_loss_after_write = scene_smoothness
        result.scene_objective_loss_after_write = scene_objective
        result.max_write_error = _max_position_error(result.positions_world, scene_positions)

    om2.MGlobal.displayInfo(
        "fit_curve_poc distance loss: {} -> {}".format(result.initial_loss, result.final_loss),
    )
    om2.MGlobal.displayInfo(
        "fit_curve_poc smoothness loss: {} -> {}".format(
            result.initial_smoothness_loss,
            result.final_smoothness_loss,
        ),
    )
    om2.MGlobal.displayInfo(
        "fit_curve_poc objective loss: {} -> {}".format(
            result.initial_objective_loss,
            result.final_objective_loss,
        ),
    )
    om2.MGlobal.displayInfo(
        "fit_curve_poc smoothness weight: base={}, effective={}, cv_scale={}, target_complexity={}, "
        "complexity_scale={}".format(
            result.smoothness_weight,
            result.effective_smoothness_weight,
            result.smoothness_cv_scale,
            result.target_complexity,
            result.smoothness_complexity_scale,
        ),
    )
    om2.MGlobal.displayInfo(
        "fit_curve_poc symmetry post-process: enabled={}, axis={}".format(
            result.symmetry,
            result.symmetry_axis,
        ),
    )
    if result.scene_loss_after_write is not None:
        om2.MGlobal.displayInfo(
            "fit_curve_poc scene write distance: {}, objective: {}, max write error: {}".format(
                result.scene_loss_after_write,
                result.scene_objective_loss_after_write,
                result.max_write_error,
            ),
        )
    return result
