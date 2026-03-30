"""Module for curve fitting using Lion optimizer."""
#############################################
import typing

import maya.api.OpenMaya as om2
import maya.cmds as cmds
import maya.mel as mel

from . import curve

from logging import (  # noqa:F401 pylint: disable=unused-import, wrong-import-order
    DEBUG,
    INFO,
    StreamHandler,
    WARN,
    getLogger,
)


handler = StreamHandler()
handler.setLevel(DEBUG)
logger = getLogger(__name__)
logger.setLevel(INFO)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


#############################################

def sample_points_on_curve(mfn_curve, num_samples=100, space=om2.MSpace.kObject, matrix=None):
    # type: (om2.MFnNurbsCurve, int, int, om2.MMatrix|None) -> list[om2.MPoint]
    """Return a list of sampled points sampled at equal intervals along the curve.

    Args:
        mfn_curve: MFnNurbsCurve object
        num_samples: Number of samples
        space: Space to sample the points
        matrix: Transformation matrix to apply to the sampled points

    Returns:
        list[om2.MPoint]: List of sampled points
    """
    if not isinstance(mfn_curve, om2.MFnNurbsCurve):
        mfn_curve = curve.getMFnNurbsCurve(mfn_curve)

    length = mfn_curve.length()

    mfn_curve.updateCurve()
    close = mfn_curve.form == 3 or mfn_curve.form == 2

    total_length = mfn_curve.length()
    if close:
        cycle_nb = num_samples
    else:
        cycle_nb = num_samples - 1

    if close:
        pos0 = mfn_curve.cvPosition(0)
        _, p = mfn_curve.closestPoint(pos0)
        start_length = mfn_curve.findLengthFromParam(p)
    else:
        start_length = 0.0

    positions = []
    segment_length = total_length / cycle_nb
    for i in range(num_samples):
        length = segment_length * i + start_length
        if length > total_length:
            if close:
                length -= total_length
            else:
                length = total_length

        param = mfn_curve.findParamFromLength(length)
        pos = mfn_curve.getPointAtParam(param, space=om2.MSpace.kWorld)
        pos = curve.__applyInverseMatrixToPosition(pos, matrix)
        positions.append(pos)

    return positions


def compute_loss(curveA, curveB, num_samples=100):
    # type: (om2.MFnNurbsCurve, om2.MFnNurbsCurve, int) -> float
    """Return the loss value between two curves.

    The loss is computed as the sum of the squared distances between the sampled points on the two curves.
    Additionally, a loss term is added to ensure that the CVs are evenly spaced.

    Args:
        curveA: MFnNurbsCurve object
        curveB: MFnNurbsCurve object
        num_samples: Number of samples to compute the loss

    Returns:
        float: Loss value
    """

    distance_loss = compute_distance_loss(curveA, curveB, num_samples)
    cv_interval_loss = compute_cv_interval_loss(curveA)

    return distance_loss + cv_interval_loss * 0.5


def compute_distance_loss(curveA, curveB, num_samples=100):
    # type: (om2.MFnNurbsCurve, om2.MFnNurbsCurve, int) -> float
    """Return the distance loss between two curves.

    The loss is computed as the sum of the squared distances between
    the sampled points on the two curves.

    Args:
        curveA: MFnNurbsCurve object
        curveB: MFnNurbsCurve object
        num_samples: Number of samples to compute the loss

    Returns:
        float: Distance loss value between the two curves
    """
    pointsA = sample_points_on_curve(curveA, num_samples)
    pointsB = sample_points_on_curve(curveB, num_samples)
    
    loss_val = 0.0
    for pA, pB in zip(pointsA, pointsB):
        diff = pA - pB
        dist_sq = diff.x**2 + diff.y**2 + diff.z**2
        loss_val += dist_sq

    loss_val /= num_samples
    
    return loss_val


def compute_cv_interval_loss(curveA):
    # type: (om2.MFnNurbsCurve) -> float
    """Return the loss value to ensure that the CVs are evenly spaced.

    The loss is computed as the sum of the squared differences between the
    distances of the CVs from the ideal interval.

    Args:
        curveA: MFnNurbsCurve object

    Returns:
        float: CV interval loss value in the curve
    """
    cv_positions = curveA.cvPositions(om2.MSpace.kWorld)
    num_cvs = len(cv_positions)
    total_length = curveA.length()
    interval = total_length / (num_cvs - 1)

    loss_val = 0.0
    for i in range(num_cvs - 1):
        p1 = cv_positions[i]
        p2 = cv_positions[i + 1]
        dist = (p1 - p2).length()
        diff = dist - interval
        loss_val += diff**2
    
    return loss_val / num_cvs


def set_cv_positions(mfn_curve, new_positions_world):
    # type: (om2.MFnNurbsCurve, list[om2.MPoint]) -> None
    """Set the positions of multiple CVs at once.

    The new_positions_world is a list of positions in world space.

    Args:
        mfn_curve: MFnNurbsCurve object
        new_positions_world: List of new positions in world space

    Returns:
        None
    """

    assert len(new_positions_world) == mfn_curve.numCVs

    # オブジェクト空間で更新するため、まず現在のCVリスト(オブジェクト空間)を取得
    current_cvs_obj = mfn_curve.cvPositions(om2.MSpace.kObject)
    
    # ワールド→オブジェクト空間変換用の行列を取得
    dag_path = mfn_curve.getPath()
    world_matrix_inv = dag_path.inclusiveMatrixInverse()
    
    # new_positions_world をオブジェクト空間に変換
    for i in range(len(current_cvs_obj)):
        # MPoint * MMatrix = 位置変換
        current_cvs_obj[i] = new_positions_world[i] * world_matrix_inv
    
    # カーブに反映
    mfn_curve.setCVPositions(current_cvs_obj, om2.MSpace.kObject)
    mfn_curve.updateCurve()


def sign_mvector(v):
    # type: (om2.MVector) -> om2.MVector
    """Return the sign of the MVector components.

    If v.x > 0, return +1.0,
    if v.x < 0, return -1.0,
    otherwise return 0.0 (same for y, z).
    """
    sx = 1.0 if v.x > 0 else (-1.0 if v.x < 0 else 0.0)
    sy = 1.0 if v.y > 0 else (-1.0 if v.y < 0 else 0.0)
    sz = 1.0 if v.z > 0 else (-1.0 if v.z < 0 else 0.0)

    return om2.MVector(sx, sy, sz)


def compute_finite_diff_gradients(curveA, curveB, cv_indices, epsilon, num_samples):
    # type: (om2.MFnNurbsCurve, om2.MFnNurbsCurve, list[int], float, int) -> list[om2.MVector]
    """Compute the gradients vector using finite differences (central differences).

    The function computes the gradients for the specified multiple CVs using finite differences.
    The return value grads is a list of the same length as the number of CVs, and the gradients of the unnecessary CVs are (0, 0, 0).

    Args:
        curveA: MFnNurbsCurve object
        curveB: MFnNurbsCurve object
        cv_indices: List of CV indices to compute the gradients
        epsilon: Small value for finite differences
        num_samples: Number of samples to compute the loss

    Returns:
        list[om2.MVector]: List of gradients for the specified CV
    """

    base_positions = curveA.cvPositions(om2.MSpace.kWorld)
    num_cvs = len(base_positions)
    grads = [om2.MVector(0.0, 0.0, 0.0) for _ in range(num_cvs)]
    
    for cv_id in cv_indices:
        orig_pos = base_positions[cv_id]
        
        for axis in ["x", "y", "z"]:
            # +epsilon
            pos_plus = om2.MPoint(orig_pos)
            setattr(pos_plus, axis, getattr(pos_plus, axis) + epsilon)
            plus_positions = list(base_positions)
            plus_positions[cv_id] = pos_plus
            set_cv_positions(curveA, plus_positions)
            loss_plus = compute_loss(curveA, curveB, num_samples)

            # -epsilon
            pos_minus = om2.MPoint(orig_pos)
            setattr(pos_minus, axis, getattr(pos_minus, axis) - epsilon)
            minus_positions = list(base_positions)
            minus_positions[cv_id] = pos_minus
            set_cv_positions(curveA, minus_positions)
            loss_minus = compute_loss(curveA, curveB, num_samples)
            
            # 中心差分
            diff = (loss_plus - loss_minus) / (2.0 * epsilon)
            if axis == "x":
                grads[cv_id].x = diff
            elif axis == "y":
                grads[cv_id].y = diff
            else:
                grads[cv_id].z = diff
            
            # 元に戻す
            set_cv_positions(curveA, base_positions)
    
    return grads


def lion_update_positions(base_positions, momentum, grads, cv_indices, beta, learning_rate):
    # type: (list[om2.MPoint], list[om2.MVector], list[om2.MVector], list[int], float, float) -> list[om2.MPoint]
    """
    Lion (EvoLved Sign Momentum) による更新処理を行い、更新後のCV位置一覧(ワールド空間)を返す。
    
    更新式:
        m_t[i] = beta * m_t-1[i] + (1-beta)*grad[i]
        pos[i] = pos[i] - lr * sign(m_t[i])
    """
    updated_positions = [om2.MPoint(p) for p in base_positions]  # コピー作成
    
    for i in cv_indices:
        # モメンタム更新
        momentum[i] = momentum[i] * beta + grads[i] * (1.0 - beta)
        
        # Lion 更新: 符号方向に一定幅動かす
        s = sign_mvector(momentum[i])
        updated_positions[i] = om2.MPoint(base_positions[i]) - s * learning_rate
    
    return updated_positions


def optimize_multiple_cvs(
        curveA, 
        curveB, 
        cv_indices,
        num_iterations=20, 
        epsilon=0.001, 
        learning_rate=0.01,
        beta=0.9,
        num_samples=100):
    # type: (om2.MFnNurbsCurve, om2.MFnNurbsCurve, list[int], int, float, float, float, int) -> None
    """This function optimizes multiple CVs of curveA to fit curveB using Lion optimizer.

    1. Compute the initial loss
    2. Compute the gradients using finite differences
    3. Update the CV positions using Lion optimizer
    4. Display the loss value
    """
    init_loss = compute_loss(curveA, curveB, num_samples)
    om2.MGlobal.displayInfo("初期損失: {}".format(init_loss))
    
    # カーブAのCV数チェック
    cvs_world = curveA.cvPositions(om2.MSpace.kWorld)
    num_cvs = len(cvs_world)
    for cv_id in cv_indices:
        if cv_id < 0 or cv_id >= num_cvs:
            raise IndexError("cv_indicesの値 {} が不正です。".format(cv_id))
    
    # Lion用モメンタムバッファ
    momentum = [om2.MVector(0.0, 0.0, 0.0) for _ in range(num_cvs)]
    gMainProgressBar = None
    if not cmds.about(batch=True):
        gMainProgressBar = mel.eval("$tmp = $gMainProgressBar")
        cmds.progressBar(gMainProgressBar, edit=True, beginProgress=True, isInterruptable=True, maxValue=num_iterations)
    
    for it in range(num_iterations):
        # 現在の損失
        current_loss = compute_loss(curveA, curveB, num_samples)
        
        # 有限差分で勾配計算
        grads = compute_finite_diff_gradients(curveA, curveB, cv_indices, epsilon, num_samples)
        
        # Lion更新
        base_positions = curveA.cvPositions(om2.MSpace.kWorld)
        updated_positions = lion_update_positions(base_positions, momentum, grads, cv_indices, beta, learning_rate)
        
        # カーブ反映
        set_cv_positions(curveA, updated_positions)
        
        # 新しい損失
        new_loss = compute_loss(curveA, curveB, num_samples)
        # om2.MGlobal.displayInfo("Iteration {}: loss = {}".format(it+1, new_loss))

        if not cmds.about(batch=True):
            cmds.progressBar(gMainProgressBar, edit=True, step=1)
    
    final_loss = compute_loss(curveA, curveB, num_samples)
    om2.MGlobal.displayInfo("最終損失: {}".format(final_loss))
    if not cmds.about(batch=True):
        gMainProgressBar = mel.eval("$tmp = $gMainProgressBar")
        cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)


SYMMETRY_AXIS = typing.Literal["X", "Y", "Z"]
def fit_curve_on_curve(
    curve_a,
    curve_b,
    cv_indices=None,
    num_samples=100,
    num_iterations=30,
    symmetry=False,
    symmetry_axis="X",
):
    # type: (om2.MFnNurbsCurve|str, om2.MFnNurbsCurve|str, list[int]|None, int, int, bool, MIRROR_AXIS) -> None
    """Fit curve_a on curve_b using Lion optimizer.

    Args:
        curve_a: MFnNurbsCurve or curve name
        curve_b: MFnNurbsCurve or curve name
        cv_indices: List of CV indices to optimize (default: all CVs)
        num_samples: Number of samples to compute the loss
        num_iterations: Number of optimization iterations
        symmetry: Whether to apply symmetrying after optimization
        symmetry_axis: Axis to symmetry ("X", "Y", or "Z")

    Returns:
        None
    """

    if not isinstance(curve_a, om2.MFnNurbsCurve):
        curve_a = curve.getMFnNurbsCurve(curve_a)

    if not isinstance(curve_b, om2.MFnNurbsCurve):
        curve_b = curve.getMFnNurbsCurve(curve_b)

    if cv_indices is None:
        cv_indices = list(range(curve_a.numCVs))  # type: ignore

    optimize_multiple_cvs(curve_a, curve_b, cv_indices, num_samples=num_samples, num_iterations=num_iterations)
    if symmetry:
        symmetry_curve(curve_a, axis=symmetry_axis)


def symmetry_curve(mfn_curve, axis="X"):
    # type: (om2.MFnNurbsCurve, SYMMETRY_AXIS) -> None
    """Symmetry the curve along the specified axis.

    Args:
        mfn_curve: MFnNurbsCurve object
        axis: Axis to symmetry ("X", "Y", or "Z")

    Returns:
        None
    """
    def _get_average_with_symmetry(a, b, axis_index):
        b[axis_index] = -b[axis_index]
        avg = om2.MPoint(
            (a.x + b.x) / 2.0,
            (a.y + b.y) / 2.0,
            (a.z + b.z) / 2.0,
        )

        return avg

    cvs_world = mfn_curve.cvPositions(om2.MSpace.kWorld)
    num_cvs = len(cvs_world)
    axis_index = {"X": 0, "Y": 1, "Z": 2}[axis.upper()]
    mid_index = num_cvs // 2
    for i in range(mid_index):
        opposite_index = num_cvs - 1 - i
        a = cvs_world[i]
        b = cvs_world[opposite_index]
        mirrored_pos = _get_average_with_symmetry(a, b, axis_index)
        cvs_world[i] = mirrored_pos

    mfn_curve.setCVPositions(cvs_world, om2.MSpace.kWorld)
    mfn_curve.updateCurve()
