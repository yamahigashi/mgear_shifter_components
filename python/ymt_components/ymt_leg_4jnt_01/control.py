"""Animation helpers for ymt_leg_4jnt_01."""

import traceback
from typing import Optional

import maya.cmds as cmds
import importlib
try:
    pm = importlib.import_module("mgear.pymaya")
except ImportError:
    pm = importlib.import_module("pymel.core")
try:
    datatypes = importlib.import_module("mgear.pymaya.datatypes")
except ImportError:
    datatypes = importlib.import_module("pymel.core.datatypes")

import mgear
from mgear.core import anim_utils
from mgear.core import pyqt as gqt
from mgear.core import transform
from mgear.core import vector

from ymt_shifter_utility.type_protocols import DagNodeLike, MatrixLike, MatrixValue, PlugLike, WorldPoint


ENDPOINT_NAMES = ["ankle", "foot", "toe"]
ENDPOINT_LABELS = ["Ankle", "Foot", "Toe"]

QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()


def _namespace_from_model(model: object) -> str:
    if model is None:
        return ""
    if isinstance(model, str):
        return model.strip(":")
    import mgear.synoptic.utils as syn_uti
    return (syn_uti.getNamespace(model) or "").strip(":")


def _strip_namespace(name: str) -> str:
    return anim_utils.stripNamespace(str(name))


def _get_node(namespace: str, name: str) -> Optional[DagNodeLike]:
    query = _strip_namespace(name)
    node = anim_utils.getNode(query)
    if node:
        return node

    if namespace:
        node = anim_utils.getNode(":".join([namespace, query]))
        if node:
            return node

    mgear.log("Can't find object : {0}".format(name), mgear.sev_error)
    return None


def _get_attr(node: DagNodeLike, attr_name: str, required: bool = True) -> Optional[PlugLike]:
    if node.hasAttr(attr_name):
        return node.attr(attr_name)

    suffix = "_" + attr_name
    for attr in cmds.listAttr(node.name()) or []:
        if attr.endswith(suffix):
            return node.attr(attr)

    if not required:
        return None

    mgear.log("Can't find attribute : {0}.{1}".format(node, attr_name), mgear.sev_error)
    return node.attr(attr_name)


def _get_match_node(namespace: str, name: str) -> Optional[DagNodeLike]:
    node = _get_node(namespace, name)
    if node and node.hasAttr("match_ref"):
        match_nodes = node.match_ref.listConnections()
        if match_nodes:
            return match_nodes[0]

    parts = _strip_namespace(name).split("_")
    parts[-1] = "mth"
    return _get_node(namespace, "_".join(parts))


def _get_endpoint_match_node(namespace: str, ik_name: str, endpoint: object) -> Optional[DagNodeLike]:
    endpoint_index = _endpoint_index(endpoint)
    endpoint_name = ENDPOINT_NAMES[endpoint_index]
    base = _strip_namespace(ik_name)
    if base.endswith("_ik_ctl"):
        query = base[:-len("_ik_ctl")] + "_ikEndpoint_{0}_mth".format(endpoint_name)
    else:
        query = "_".join(base.split("_")[:-1] + ["ikEndpoint", endpoint_name, "mth"])
    return _get_node(namespace, query)


def _get_offset_controls(namespace: str, ik_name: str) -> list[DagNodeLike]:
    base = _strip_namespace(ik_name)
    if base.endswith("_ik_ctl"):
        prefix = base[:-len("_ik_ctl")]
        names = [
            prefix + "_footOffset_ctl",
            prefix + "_ankleOffset_ctl",
        ]
    else:
        parts = base.split("_")[:-1]
        names = [
            "_".join(parts + ["footOffset", "ctl"]),
            "_".join(parts + ["ankleOffset", "ctl"]),
        ]

    return [node for node in [_get_node(namespace, name) for name in names] if node]


def _get_upv_control(namespace: str, ik_name: str) -> Optional[DagNodeLike]:
    base = _strip_namespace(ik_name)
    if base.endswith("_ik_ctl"):
        query = base[:-len("_ik_ctl")] + "_upv_ctl"
    else:
        query = "_".join(base.split("_")[:-1] + ["upv", "ctl"])
    return _get_node(namespace, query)


def _endpoint_index(endpoint: object) -> int:
    if isinstance(endpoint, str):
        lowered = endpoint.lower()
        if lowered in ENDPOINT_NAMES:
            return ENDPOINT_NAMES.index(lowered)
        if lowered in [x.lower() for x in ENDPOINT_LABELS]:
            return [x.lower() for x in ENDPOINT_LABELS].index(lowered)
        return int(endpoint)
    return int(endpoint)


def _get_matrix(obj: DagNodeLike, time: Optional[int] = None) -> MatrixValue:
    if time is None:
        return cmds.xform(obj.name(), q=True, ws=True, matrix=True)
    return pm.getAttr(str(obj) + ".worldMatrix", time=time)


def _get_translation(obj: DagNodeLike, time: Optional[int] = None) -> WorldPoint:
    if time is None:
        return cmds.xform(obj.name(), q=True, ws=True, translation=True)
    matrix = pm.getAttr(str(obj) + ".worldMatrix", time=time)
    return matrix.translate


def _set_matrix(obj: DagNodeLike, mat: MatrixValue) -> None:
    if isinstance(mat, (list, tuple)):
        cmds.xform(obj.name(), ws=True, matrix=mat)
    else:
        obj.setMatrix(mat, worldSpace=True)


def _set_translation(obj: DagNodeLike, pos: WorldPoint) -> None:
    if isinstance(pos, (list, tuple)):
        cmds.xform(obj.name(), ws=True, translation=pos)
        return
    obj.setTranslation(pos, space="world")


def _matrix_from_vector(pos: WorldPoint) -> MatrixLike:
    return transform.setMatrixPosition(datatypes.Matrix(), pos)


def _set_keyframes(nodes: list[DagNodeLike], attrs: tuple[str, ...] = ("t", "r", "s")) -> None:
    cmds.setKeyframe([x.name() for x in nodes], at=list(attrs))


def _set_translation_keyframes(nodes: list[DagNodeLike]) -> None:
    cmds.setKeyframe([x.name() for x in nodes], at=["tx", "ty", "tz"])


def _keyframe_times(nodes: list[DagNodeLike], start_frame: int, end_frame: int) -> list[int]:
    keys = pm.keyframe(nodes, at=["t", "r", "s"], q=True)
    if not keys:
        return []
    return sorted(set(int(x) for x in keys if start_frame <= x <= end_frame))


def _cut_transform_keys(nodes: list[DagNodeLike], start_frame: int, end_frame: int) -> None:
    channels = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]
    pm.cutKey(nodes, at=channels, time=(start_frame, end_frame))


def _set_attr_key(attr: PlugLike) -> None:
    pm.setKeyframe(attr)


def _set_roll_zero(ui_node: DagNodeLike, ikfk_attr: str) -> None:
    roll_name = ikfk_attr.replace("blend", "roll")
    roll_attr = _get_attr(ui_node, roll_name, required=False)
    if roll_attr:
        roll_attr.set(0.0)


def _pole_vector_position(fk_goals: list[DagNodeLike], endpoint_goal: DagNodeLike, time: Optional[int] = None) -> WorldPoint:
    frame = time or int(pm.currentTime(q=True))
    return vector.calculatePoleVector(fk_goals[0], fk_goals[1], endpoint_goal, 1.0, frame)


def _apply_fk_matrices(fk_ctrls: list[DagNodeLike], matrices: list[MatrixValue]) -> None:
    for _ in range(2):
        for mat, ctrl in zip(matrices, fk_ctrls):
            _set_matrix(ctrl, mat)


def _resolve_leg_nodes(namespace: str, ui_host: str, fks: list[str], ik: str, upv: str, endpoint_attr: str) -> tuple[object, ...]:
    fk_ctrls = [_get_node(namespace, x) for x in fks]
    fk_goals = [_get_match_node(namespace, x) for x in fks]
    ik_ctrl = _get_node(namespace, ik)
    ik_goal = _get_match_node(namespace, ik)
    offset_ctrls = _get_offset_controls(namespace, ik)
    offset_goals = [_get_match_node(namespace, x.name()) for x in offset_ctrls]
    upv_ctrl = _get_node(namespace, upv)
    ui_node = _get_node(namespace, ui_host)
    endpoint = int(_get_attr(ui_node, endpoint_attr).get())
    endpoint_goal = _get_endpoint_match_node(namespace, ik, endpoint)
    return (
        fk_ctrls,
        fk_goals,
        ik_ctrl,
        ik_goal,
        offset_ctrls,
        offset_goals,
        upv_ctrl,
        ui_node,
        endpoint,
        endpoint_goal,
    )


def ikFkMatch(namespace: str, ikfk_attr: str, ui_host: str, fks: list[str], ik: str, upv: str, endpoint_attr: str = "ikEndpoint", key: Optional[bool] = None) -> None:
    """Switch IK/FK on the current frame while preserving the current pose."""
    namespace = _namespace_from_model(namespace)
    (
        fk_ctrls,
        fk_goals,
        ik_ctrl,
        ik_goal,
        offset_ctrls,
        offset_goals,
        upv_ctrl,
        ui_node,
        _,
        endpoint_goal,
    ) = _resolve_leg_nodes(
        namespace, ui_host, fks, ik, upv, endpoint_attr
    )

    blend_attr = _get_attr(ui_node, ikfk_attr)
    switch_to_fk = blend_attr.get() == 1.0

    key_nodes = fk_ctrls + [ik_ctrl, upv_ctrl, ui_node] + offset_ctrls
    if key:
        pm.setKeyframe(key_nodes, time=(pm.currentTime(q=True) - 1.0))

    if switch_to_fk:
        fk_matrices = [_get_matrix(x) for x in fk_goals]
        blend_attr.set(0.0)
        _apply_fk_matrices(fk_ctrls, fk_matrices)
    else:
        ik_matrix = _get_matrix(ik_goal)
        offset_matrices = [_get_matrix(x) for x in offset_goals]
        pole_position = _pole_vector_position(fk_goals, endpoint_goal)
        blend_attr.set(1.0)
        _set_roll_zero(ui_node, ikfk_attr)
        _set_matrix(ik_ctrl, ik_matrix)
        for ctrl, matrix in zip(offset_ctrls, offset_matrices):
            _set_matrix(ctrl, matrix)
        upv_ctrl.setTranslation(pole_position, space="world")
        _set_matrix(ik_ctrl, ik_matrix)
        for ctrl, matrix in zip(offset_ctrls, offset_matrices):
            _set_matrix(ctrl, matrix)

    if key:
        pm.setKeyframe(key_nodes, time=pm.currentTime(q=True))


def ikEndpointSpaceSwitch(namespace: str, ui_host: str, ik: str, endpoint: object, endpoint_attr: str = "ikEndpoint", key: Optional[bool] = None) -> None:
    """Switch IK endpoint on the current frame while matching the destination endpoint."""
    namespace = _namespace_from_model(namespace)
    ik_ctrl = _get_node(namespace, ik)
    upv_ctrl = _get_upv_control(namespace, ik)
    upv_position = _get_translation(upv_ctrl)
    offset_ctrls = _get_offset_controls(namespace, ik)
    offset_goals = [_get_match_node(namespace, x.name()) for x in offset_ctrls]
    ui_node = _get_node(namespace, ui_host)
    endpoint_index = _endpoint_index(endpoint)
    endpoint_goal = _get_endpoint_match_node(namespace, ik, endpoint_index)
    endpoint_matrix = _get_matrix(endpoint_goal)
    offset_matrices = [_get_matrix(x) for x in offset_goals]

    if key:
        pm.setKeyframe([ik_ctrl, upv_ctrl, ui_node] + offset_ctrls, time=(pm.currentTime(q=True) - 1.0))

    endpoint_attr_obj = _get_attr(ui_node, endpoint_attr)
    endpoint_attr_obj.set(endpoint_index)
    _set_matrix(ik_ctrl, endpoint_matrix)
    for ctrl, matrix in zip(offset_ctrls, offset_matrices):
        _set_matrix(ctrl, matrix)
    _set_translation(upv_ctrl, upv_position)

    if key:
        pm.setKeyframe([ik_ctrl] + offset_ctrls, time=pm.currentTime(q=True))
        _set_translation_keyframes([upv_ctrl])
        pm.setKeyframe(endpoint_attr_obj, time=pm.currentTime(q=True))


class _TransferBase(anim_utils.AbstractAnimationTransfer):
    def setModel(self, model: object) -> None:
        self.model = model
        self.nameSpace = _namespace_from_model(model)

    def setUiHost(self, uihost: str) -> None:
        self.uihost = uihost

    def setSwitchedAttrShortName(self, attr: str) -> None:
        self.switchedAttrShortName = attr

    def getHostName(self) -> str:
        if self.nameSpace:
            return ":".join([self.nameSpace, self.uihost])
        return self.uihost

    def getChangeAttrName(self) -> str:
        return _get_attr(_get_node(self.nameSpace, self.uihost), self.switchedAttrShortName).name()

    def getValueFromUI(self) -> int:
        return self.comboBoxSpaces.currentIndex()

    def changeAttrToBoundValue(self) -> None:
        pm.setAttr(self.getChangeAttrName(), self.getValueFromUI())


class IkFkTransfer(_TransferBase):
    def setCtrls(self, fks: list[str], ik: str, upv: str, endpoint_attr: str = "ikEndpoint") -> None:
        self.fks = fks
        self.ik = ik
        self.upv = upv
        self.endpoint_attr = endpoint_attr

    def transfer(self, startFrame: int, endFrame: int, onlyKeyframes: bool, switchTo: Optional[str] = None, *args: object, **kwargs: object) -> None:
        namespace = self.nameSpace
        (
            fk_ctrls,
            fk_goals,
            ik_ctrl,
            ik_goal,
            offset_ctrls,
            offset_goals,
            upv_ctrl,
            ui_node,
            _,
            endpoint_goal,
        ) = _resolve_leg_nodes(
            namespace, self.uihost, self.fks, self.ik, self.upv, self.endpoint_attr
        )
        to_fk = "fk" in switchTo.lower() if switchTo else self.comboBoxSpaces.currentIndex() == 1
        ik_side_ctrls = [ik_ctrl, upv_ctrl] + offset_ctrls
        key_src_nodes = ik_side_ctrls if to_fk else fk_ctrls
        key_times = _keyframe_times(key_src_nodes, startFrame, endFrame)

        values = []
        for frame in range(startFrame, endFrame + 1):
            if to_fk:
                values.append([_get_matrix(x, frame) for x in fk_goals])
            else:
                ik_matrix = _get_matrix(ik_goal, frame)
                offset_matrices = [_get_matrix(x, frame) for x in offset_goals]
                pole_matrix = _matrix_from_vector(_pole_vector_position(fk_goals, endpoint_goal, frame))
                values.append([ik_matrix] + offset_matrices + [pole_matrix])

        pm.cycleCheck(e=False)
        try:
            _cut_transform_keys(fk_ctrls if to_fk else ik_side_ctrls, startFrame, endFrame)
            switch_attr = _get_attr(ui_node, self.switchedAttrShortName)
            pm.cutKey(switch_attr, time=(startFrame, endFrame))
            if not to_fk:
                roll_attr = _get_attr(ui_node, self.switchedAttrShortName.replace("blend", "roll"), required=False)
                if roll_attr:
                    pm.cutKey(roll_attr, time=(startFrame, endFrame))

            for i, frame in enumerate(range(startFrame, endFrame + 1)):
                if onlyKeyframes and frame not in key_times:
                    continue
                pm.currentTime(frame)
                switch_attr.set(0.0 if to_fk else 1.0)
                if to_fk:
                    _apply_fk_matrices(fk_ctrls, values[i])
                    _set_keyframes(fk_ctrls)
                else:
                    _set_roll_zero(ui_node, self.switchedAttrShortName)
                    _set_matrix(ik_ctrl, values[i][0])
                    for offset_index, ctrl in enumerate(offset_ctrls):
                        _set_matrix(ctrl, values[i][offset_index + 1])
                    _set_matrix(upv_ctrl, values[i][-1])
                    _set_keyframes(ik_side_ctrls)
                _set_attr_key(switch_attr)
        finally:
            pm.cycleCheck(e=True)

    @staticmethod
    def showUI(model: object, ikfk_attr: str, uihost: str, fks: list[str], ik: str, upv: str, endpoint_attr: str = "ikEndpoint") -> None:
        try:
            for child in gqt.maya_main_window().children():
                if isinstance(child, IkFkTransfer):
                    child.deleteLater()
        except RuntimeError:
            pass

        ui = IkFkTransfer()
        ui.setComboObj(None)
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(ikfk_attr)
        ui.setCtrls(fks, ik, upv, endpoint_attr)
        ui.setComboBoxItemsFormList(["IK", "FK"])
        try:
            ui.createUI(gqt.maya_main_window())
            ui.show()
        except Exception as exc:
            ui.deleteLater()
            traceback.print_exc()
            mgear.log(exc, mgear.sev_error)

    @staticmethod
    def execute(model: object, ikfk_attr: str, uihost: str, fks: list[str], ik: str, upv: str, endpoint_attr: str = "ikEndpoint", startFrame: Optional[int] = None, endFrame: Optional[int] = None, onlyKeyframes: Optional[bool] = None, switchTo: Optional[str] = None) -> None:
        if startFrame is None:
            startFrame = int(pm.playbackOptions(q=True, ast=True))
        if endFrame is None:
            endFrame = int(pm.playbackOptions(q=True, aet=True))
        if onlyKeyframes is None:
            onlyKeyframes = True
        if switchTo is None:
            switchTo = "fk"

        ui = IkFkTransfer()
        ui.setComboObj(None)
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(ikfk_attr)
        ui.setCtrls(fks, ik, upv, endpoint_attr)
        ui.setComboBoxItemsFormList(["IK", "FK"])
        ui.transfer(startFrame, endFrame, onlyKeyframes, switchTo=switchTo)

    @staticmethod
    def toIK(model: object, ikfk_attr: str, uihost: str, fks: list[str], ik: str, upv: str, endpoint_attr: str = "ikEndpoint", **kwargs: object) -> None:
        kwargs.update({"switchTo": "ik"})
        IkFkTransfer.execute(model, ikfk_attr, uihost, fks, ik, upv, endpoint_attr, **kwargs)

    @staticmethod
    def toFK(model: object, ikfk_attr: str, uihost: str, fks: list[str], ik: str, upv: str, endpoint_attr: str = "ikEndpoint", **kwargs: object) -> None:
        kwargs.update({"switchTo": "fk"})
        IkFkTransfer.execute(model, ikfk_attr, uihost, fks, ik, upv, endpoint_attr, **kwargs)


class IkEndpointTransfer(_TransferBase):
    def setCtrls(self, ik: str) -> None:
        self.ik = ik

    def transfer(self, startFrame: int, endFrame: int, onlyKeyframes: bool, switchTo: Optional[str] = None, *args: object, **kwargs: object) -> None:
        endpoint_index = _endpoint_index(switchTo) if switchTo is not None else self.comboBoxSpaces.currentIndex()
        namespace = self.nameSpace
        ik_ctrl = _get_node(namespace, self.ik)
        upv_ctrl = _get_upv_control(namespace, self.ik)
        offset_ctrls = _get_offset_controls(namespace, self.ik)
        offset_goals = [_get_match_node(namespace, x.name()) for x in offset_ctrls]
        ui_node = _get_node(namespace, self.uihost)
        endpoint_goal = _get_endpoint_match_node(namespace, self.ik, endpoint_index)
        key_nodes = [ik_ctrl, upv_ctrl] + offset_ctrls
        key_times = _keyframe_times(key_nodes, startFrame, endFrame)

        matrices = []
        for frame in range(startFrame, endFrame + 1):
            endpoint_matrix = _get_matrix(endpoint_goal, frame)
            offset_matrices = [_get_matrix(x, frame) for x in offset_goals]
            upv_position = _get_translation(upv_ctrl, frame)
            matrices.append([endpoint_matrix] + offset_matrices + [upv_position])

        pm.cycleCheck(e=False)
        try:
            _cut_transform_keys(key_nodes, startFrame, endFrame)
            switch_attr = _get_attr(ui_node, self.switchedAttrShortName)
            pm.cutKey(switch_attr, time=(startFrame, endFrame))
            for i, frame in enumerate(range(startFrame, endFrame + 1)):
                if onlyKeyframes and frame not in key_times:
                    continue
                pm.currentTime(frame)
                switch_attr.set(endpoint_index)
                _set_matrix(ik_ctrl, matrices[i][0])
                for offset_index, ctrl in enumerate(offset_ctrls):
                    _set_matrix(ctrl, matrices[i][offset_index + 1])
                _set_translation(upv_ctrl, matrices[i][-1])
                _set_keyframes([ik_ctrl] + offset_ctrls)
                _set_translation_keyframes([upv_ctrl])
                _set_attr_key(switch_attr)
        finally:
            pm.cycleCheck(e=True)

    @staticmethod
    def showUI(model: object, uihost: str, ik: str, endpoint_attr: str = "ikEndpoint") -> None:
        try:
            for child in gqt.maya_main_window().children():
                if isinstance(child, IkEndpointTransfer):
                    child.deleteLater()
        except RuntimeError:
            pass

        ui = IkEndpointTransfer()
        ui.setComboObj(None)
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(endpoint_attr)
        ui.setCtrls(ik)
        ui.setComboBoxItemsFormList(ENDPOINT_LABELS)
        try:
            ui.createUI(gqt.maya_main_window())
            ui.show()
        except Exception as exc:
            ui.deleteLater()
            traceback.print_exc()
            mgear.log(exc, mgear.sev_error)

    @staticmethod
    def execute(model: object, uihost: str, ik: str, endpoint: object, endpoint_attr: str = "ikEndpoint", startFrame: Optional[int] = None, endFrame: Optional[int] = None, onlyKeyframes: Optional[bool] = None) -> None:
        if startFrame is None:
            startFrame = int(pm.playbackOptions(q=True, ast=True))
        if endFrame is None:
            endFrame = int(pm.playbackOptions(q=True, aet=True))
        if onlyKeyframes is None:
            onlyKeyframes = True

        ui = IkEndpointTransfer()
        ui.setComboObj(None)
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(endpoint_attr)
        ui.setCtrls(ik)
        ui.setComboBoxItemsFormList(ENDPOINT_LABELS)
        ui.transfer(startFrame, endFrame, onlyKeyframes, switchTo=endpoint)
