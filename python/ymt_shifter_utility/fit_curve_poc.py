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

from dataclasses import dataclass
from logging import DEBUG, INFO, StreamHandler, getLogger
from typing import Iterable, Sequence

import maya.api.OpenMaya as om2

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

    @property
    def num_cvs(self):
        return len(self.cvs_world)

    @property
    def is_closed(self):
        return _is_closed_form(self.form)

    @property
    def is_periodic(self):
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
    scene_loss_after_write: float | None = None
    max_write_error: float | None = None


@dataclass
class EvaluatorValidation:
    """Difference between Maya curve evaluation and the POC evaluator."""

    max_error: float
    mean_error: float
    num_samples: int


def _as_mfn_curve(curve_like):
    # type: (om2.MFnNurbsCurve | str | object) -> om2.MFnNurbsCurve
    if isinstance(curve_like, om2.MFnNurbsCurve):
        return curve_like
    return curve.getMFnNurbsCurve(curve_like)


def _is_rational(mfn_curve):
    # type: (om2.MFnNurbsCurve) -> bool
    attr = getattr(mfn_curve, "isRational", False)
    if callable(attr):
        return bool(attr())
    return bool(attr)


def _form_constant(name, fallback):
    # type: (str, int) -> int
    return int(getattr(om2.MFnNurbsCurve, name, fallback))


def _is_periodic_form(form):
    # type: (int) -> bool
    return int(form) == _form_constant("kPeriodic", 3)


def _is_closed_form(form):
    # type: (int) -> bool
    return int(form) in (
        _form_constant("kClosed", 2),
        _form_constant("kPeriodic", 3),
    )


def _external_knot_vector(maya_knots, form):
    # type: (Sequence[float], int) -> list[float]
    if _is_periodic_form(form):
        first_interval = maya_knots[1] - maya_knots[0]
        last_interval = maya_knots[-1] - maya_knots[-2]
        return [maya_knots[0] - first_interval] + list(maya_knots) + [maya_knots[-1] + last_interval]

    return [maya_knots[0]] + list(maya_knots) + [maya_knots[-1]]


def _full_knot_vector(mfn_curve, degree, num_cvs, form):
    # type: (om2.MFnNurbsCurve, int, int, int) -> list[float]
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


def snapshot_curve(curve_like):
    # type: (om2.MFnNurbsCurve | str | object) -> NurbsCurveSnapshot
    """Capture curve data needed by the scene-free evaluator."""
    mfn_curve = _as_mfn_curve(curve_like)
    mfn_curve.updateCurve()
    if _is_rational(mfn_curve):
        raise NotImplementedError("fit_curve_poc does not support rational curves yet.")

    degree = int(mfn_curve.degree)
    form = int(mfn_curve.form)
    cvs_world = list(mfn_curve.cvPositions(om2.MSpace.kWorld))
    knots = _full_knot_vector(mfn_curve, degree, len(cvs_world), form)

    return NurbsCurveSnapshot(
        degree=degree,
        form=form,
        knots=knots,
        cvs_world=cvs_world,
    )


def _sample_params_by_length(mfn_curve, num_samples):
    # type: (om2.MFnNurbsCurve, int) -> list[float]
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


def _sample_params_by_parameter(snapshot, num_samples):
    # type: (NurbsCurveSnapshot, int) -> list[float]
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


def _find_span(num_cvs, degree, u, knots):
    # type: (int, int, float, Sequence[float]) -> int
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


def _basis_funs(span, u, degree, knots):
    # type: (int, float, int, Sequence[float]) -> list[float]
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


def basis_at_param(snapshot, u):
    # type: (NurbsCurveSnapshot, float) -> list[tuple[int, float]]
    """Return non-zero basis weights as ``(cv_index, weight)`` pairs."""
    span = _find_span(snapshot.num_cvs, snapshot.degree, u, snapshot.knots)
    weights = _basis_funs(span, u, snapshot.degree, snapshot.knots)
    first = span - snapshot.degree
    return [
        (first + i, weight)
        for i, weight in enumerate(weights)
        if weight != 0.0 and 0 <= first + i < snapshot.num_cvs
    ]


def _master_cv_index(snapshot, cv_index):
    # type: (NurbsCurveSnapshot, int) -> int
    if snapshot.is_periodic and cv_index >= snapshot.num_cvs - snapshot.degree:
        return cv_index - (snapshot.num_cvs - snapshot.degree)
    return cv_index


def _sync_periodic_bound_cvs(snapshot, cvs_world):
    # type: (NurbsCurveSnapshot, Sequence[om2.MPoint]) -> list[om2.MPoint]
    synced = [om2.MPoint(point) for point in cvs_world]
    if not snapshot.is_periodic:
        return synced

    first_bound = snapshot.num_cvs - snapshot.degree
    for offset in range(snapshot.degree):
        synced[first_bound + offset] = om2.MPoint(synced[offset])
    return synced


def _normalized_cv_indices(snapshot, cv_indices):
    # type: (NurbsCurveSnapshot, Sequence[int] | None) -> list[int]
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


def evaluate_point(cvs_world, basis):
    # type: (Sequence[om2.MPoint], Iterable[tuple[int, float]]) -> om2.MPoint
    x = 0.0
    y = 0.0
    z = 0.0
    for cv_index, weight in basis:
        point = cvs_world[cv_index]
        x += point.x * weight
        y += point.y * weight
        z += point.z * weight
    return om2.MPoint(x, y, z)


def evaluate_points(cvs_world, basis_list):
    # type: (Sequence[om2.MPoint], Sequence[Sequence[tuple[int, float]]]) -> list[om2.MPoint]
    return [evaluate_point(cvs_world, basis) for basis in basis_list]


def validate_snapshot_evaluator(curve_like, num_samples=100):
    # type: (om2.MFnNurbsCurve | str | object, int) -> EvaluatorValidation
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


def build_fit_context(curve_a, curve_b, num_samples=100, source_sample_mode="parameter"):
    # type: (...) -> FitContext
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


def compute_distance_loss(cvs_world, context):
    # type: (Sequence[om2.MPoint], FitContext) -> float
    """Compute mean squared distance loss without touching the scene."""
    source_points = evaluate_points(cvs_world, context.sample_basis)
    loss = 0.0
    for source_point, target_point in zip(source_points, context.target_points):
        diff = source_point - target_point
        loss += diff.x**2 + diff.y**2 + diff.z**2
    return loss / float(len(context.target_points))


def compute_distance_gradients(cvs_world, context, cv_indices=None):
    # type: (Sequence[om2.MPoint], FitContext, Sequence[int] | None) -> list[om2.MVector]
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


def _sign_vector(vector):
    # type: (om2.MVector) -> om2.MVector
    return om2.MVector(
        1.0 if vector.x > 0.0 else (-1.0 if vector.x < 0.0 else 0.0),
        1.0 if vector.y > 0.0 else (-1.0 if vector.y < 0.0 else 0.0),
        1.0 if vector.z > 0.0 else (-1.0 if vector.z < 0.0 else 0.0),
    )


def _lion_update_positions(cvs_world, momentum, gradients, cv_indices, beta, learning_rate):
    # type: (...) -> list[om2.MPoint]
    updated = [om2.MPoint(point) for point in cvs_world]
    for cv_index in cv_indices:
        momentum[cv_index] = momentum[cv_index] * beta + gradients[cv_index] * (1.0 - beta)
        updated[cv_index] = om2.MPoint(cvs_world[cv_index]) - _sign_vector(momentum[cv_index]) * learning_rate
    return updated


def set_scene_cv_positions(mfn_curve, positions_world):
    # type: (om2.MFnNurbsCurve, Sequence[om2.MPoint]) -> None
    """Write final world-space CV positions back to the scene once."""
    if len(positions_world) != mfn_curve.numCVs:
        raise ValueError("positions_world length does not match curve CV count.")

    positions_world = [om2.MPoint(point) for point in positions_world]
    if _is_periodic_form(int(mfn_curve.form)):
        # Periodic curves bind the trailing degree CVs to the first degree CVs.
        # Writing every CV with setCVPositions can make Maya remap those bound
        # CVs in a way that differs from this evaluator's positions. Write only
        # the independent CVs and let Maya maintain the periodic overlap.
        editable_count = int(mfn_curve.numCVs) - int(mfn_curve.degree)
        for cv_index in range(editable_count):
            mfn_curve.setCVPosition(cv_index, positions_world[cv_index], om2.MSpace.kWorld)
        mfn_curve.updateCurve()
        return

    mfn_curve.setCVPositions(positions_world, om2.MSpace.kWorld)
    mfn_curve.updateCurve()


def _max_position_error(points_a, points_b):
    # type: (Sequence[om2.MPoint], Sequence[om2.MPoint]) -> float
    max_error = 0.0
    for point_a, point_b in zip(points_a, points_b):
        max_error = max(max_error, (point_a - point_b).length())
    return max_error


def optimize_context(
    context,
    cv_indices=None,
    num_iterations=30,
    learning_rate=0.01,
    beta=0.9,
):
    # type: (FitContext, Sequence[int] | None, int, float, float) -> FitResult
    """Optimize the snapshot CV array without updating any scene curve."""
    cv_indices = _normalized_cv_indices(context.source, cv_indices)
    positions = _sync_periodic_bound_cvs(context.source, context.source.cvs_world)
    momentum = [om2.MVector(0.0, 0.0, 0.0) for _ in range(context.source.num_cvs)]
    initial_loss = compute_distance_loss(positions, context)

    for _ in range(num_iterations):
        gradients = compute_distance_gradients(positions, context, cv_indices)
        positions = _lion_update_positions(positions, momentum, gradients, cv_indices, beta, learning_rate)
        positions = _sync_periodic_bound_cvs(context.source, positions)

    final_loss = compute_distance_loss(positions, context)
    return FitResult(
        positions_world=positions,
        initial_loss=initial_loss,
        final_loss=final_loss,
        iterations=num_iterations,
    )


def fit_curve_on_curve_poc(
    curve_a,
    curve_b,
    cv_indices=None,
    num_samples=100,
    num_iterations=30,
    learning_rate=0.01,
    beta=0.9,
    source_sample_mode="parameter",
    write_back=True,
):
    # type: (...) -> FitResult
    """Fit ``curve_a`` toward ``curve_b`` with no loop-time scene updates.

    If ``write_back`` is true, the optimized CVs are written to ``curve_a`` once
    after the optimization loop. Set it false to benchmark or inspect the result
    without changing the scene.
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
    )

    if write_back:
        set_scene_cv_positions(mfn_a, result.positions_world)
        scene_positions = _sync_periodic_bound_cvs(
            context.source,
            mfn_a.cvPositions(om2.MSpace.kWorld),
        )
        result.scene_loss_after_write = compute_distance_loss(scene_positions, context)
        result.max_write_error = _max_position_error(result.positions_world, scene_positions)

    om2.MGlobal.displayInfo(
        "fit_curve_poc loss: {} -> {}".format(result.initial_loss, result.final_loss),
    )
    if result.scene_loss_after_write is not None:
        om2.MGlobal.displayInfo(
            "fit_curve_poc scene write loss: {}, max write error: {}".format(
                result.scene_loss_after_write,
                result.max_write_error,
            ),
        )
    return result
