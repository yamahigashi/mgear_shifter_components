"""Module for curve fitting using Lion optimizer."""
#############################################
import sys

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om2
from . import curve

from logging import (  # noqa:F401 pylint: disable=unused-import, wrong-import-order
    StreamHandler,
    getLogger,
    WARN,  # noqa: F401
    DEBUG,
    INFO
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
    """
    指定した MFnNurbsCurve から、長さを当分割した位置にサンプリングした
    それぞれの位置ベクトル(om2.MPoint)リストを返す（ワールド座標）。
    """
    if not isinstance(mfn_curve, om2.MFnNurbsCurve):
        mfn_curve = curve.getMFnNurbsCurve(mfn_curve)

    length = mfn_curve.length()

    mfn_curve.updateCurve()
    close = mfn_curve.form == 3 or mfn_curve.form == 2

    totalLength = mfn_curve.length()
    if close:
        cycleNb = num_samples
    else:
        cycleNb = num_samples - 1

    if close:
        pos0 = mfn_curve.cvPosition(0)
        _, p = mfn_curve.closestPoint(pos0)
        startLength = mfn_curve.findLengthFromParam(p)
    else:
        startLength = 0.0

    positions = []
    segmentLength = totalLength / cycleNb
    for i in range(num_samples):
        length = segmentLength * i + startLength
        if length > totalLength:
            if close:
                length -= totalLength
            else:
                length = totalLength

        param = mfn_curve.findParamFromLength(length)
        pos = mfn_curve.getPointAtParam(param, space=om2.MSpace.kWorld)
        pos = curve.__applyInverseMatrixToPosition(pos, matrix)
        positions.append(pos)

    return positions


def compute_loss(curveA, curveB, num_samples=100):
    # type: (om2.MFnNurbsCurve, om2.MFnNurbsCurve, int) -> float

    distance_loss = compute_distance_loss(curveA, curveB, num_samples)
    cv_interval_loss = compute_cv_intervel_loss(curveA)

    return distance_loss + cv_interval_loss * 0.5


def compute_distance_loss(curveA, curveB, num_samples=100):
    # type: (om2.MFnNurbsCurve, om2.MFnNurbsCurve, int) -> float
    """
    2つのカーブを同数サンプリングして、
    点同士の二乗距離の合計を損失として返す。
    
    ※ closestPoint ベースにしたい場合は、下記を:
    return compute_loss_closestPoint(curveA, curveB, num_samples)
    のように置き換えればOK。
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


def compute_cv_intervel_loss(curveA):
    # type: (om2.MFnNurbsCurve) -> float
    """
    CV間が等間隔になるように損失を計算する。
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
    """
    複数CVの位置を一括でセットする。new_positions_world はワールド空間のリスト。
    mfn_curve のCV数と len(new_positions_world) は同じ前提。
    """
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
    """
    MVector の符号関数: 成分ごとにsignを返す。
    v.x > 0 なら +1, v.x < 0 なら -1, それ以外は 0 (同様に y,z)
    """
    sx = 1.0 if v.x > 0 else (-1.0 if v.x < 0 else 0.0)
    sy = 1.0 if v.y > 0 else (-1.0 if v.y < 0 else 0.0)
    sz = 1.0 if v.z > 0 else (-1.0 if v.z < 0 else 0.0)

    return om2.MVector(sx, sy, sz)


def compute_finite_diff_gradients(curveA, curveB, cv_indices, epsilon, num_samples):
    # type: (om2.MFnNurbsCurve, om2.MFnNurbsCurve, list[int], float, int) -> list[om2.MVector]
    """
    有限差分(中心差分)で、指定した複数CVの勾配ベクトルを計算して返す。
    戻り値 grads は CV数と同じ長さで、不要なCVの勾配は (0,0,0)。
    
    Parameters:
        curveA      : 最適化対象のカーブ (MFnNurbsCurve)
        curveB      : 比較対象のカーブ
        cv_indices  : 勾配を計算するCVのリスト (例: [0,1,2])
        epsilon     : 微小量
        num_samples : 損失計算用のサンプリング点数
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
    """
    複数のCVをLionで最適化するメインループ。
    1. 現在の損失計算
    2. 有限差分で勾配を求める
    3. Lionのモメンタム更新&パラメータ(CV位置)更新
    4. 損失のログ表示
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


def fit_curve_on_curve(curveA, curveB, cv_indices=None, num_samples=100, num_iterations=100):
    # type: (om2.MFnNurbsCurve|str, om2.MFnNurbsCurve|str, list[int]|None, int, int) -> None
    """
    curveA を curveB にフィットさせる。
    両カーブのCV数は同じ前提。
    """
    if not isinstance(curveA, om2.MFnNurbsCurve):
        curveA = curve.getMFnNurbsCurve(curveA)

    if not isinstance(curveB, om2.MFnNurbsCurve):
        curveB = curve.getMFnNurbsCurve(curveB)

    if cv_indices is None:
        cv_indices = list(range(curveA.numCVs))  # type: ignore

    optimize_multiple_cvs(curveA, curveB, cv_indices, num_samples=num_samples, num_iterations=num_iterations)
