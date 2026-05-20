"""Controller helpers for ymt_birdwing_3jnt_01."""

import math
import traceback
from typing import Any, ClassVar, Optional, cast

import maya.cmds as cmds
from maya.api import OpenMaya as om2

import importlib
try:
    pm = importlib.import_module("mgear.pymaya")
except ImportError:
    pm = importlib.import_module("pymel.core")

import mgear
from mgear.core import anim_utils, pyqt as gqt
import mgear.synoptic.utils as syn_uti

from ymt_components.control import AbstractControllerButton
from ymt_shifter_utility.type_protocols import PymelNode, SettablePlug, VectorLike, WorldPoint

QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()

Matrix = list[float]
TransferFrameData = tuple[Matrix, list[float], list[float], Matrix]


class ikfkMatchAllButton(AbstractControllerButton):
    controllers: ClassVar[dict[str, str]] = {
        "ikfk_attr": "wing_blend",
        "fk0": "wing_",
    }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super(ikfkMatchAllButton, self).__init__(*args, **kwargs)
        self.model = syn_uti.getModel(self)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if not self.isControllerSetup():
            self.lookupControllers()
            self.hand_ik = self.ik.replace("_ik_", "_hand_ik_")
            self.ik_rot = self.ik.replace("_ik_", "_ikRot_")
            self.hand_ik_rot = self.ik.replace("_ik_", "_handIkRot_")

        if event.button() == QtCore.Qt.RightButton:
            IkFkTransfer.showUI(
                self.model,
                self.ikfk_attr,
                self.uiHost_name,
                self.fks,
                self.ik,
                self.upv,
                self.hand_ik,
                self.ik_rot,
                self.hand_ik_rot,
            )
            return

        ikFkMatch(
            self.model,
            self.ikfk_attr,
            self.uiHost_name,
            self.fks,
            self.ik,
            self.upv,
            self.hand_ik,
            self.ik_rot,
            self.hand_ik_rot,
        )


class ikfkMatchButton(ikfkMatchAllButton):
    pass


class IkFkTransfer(syn_uti.IkFkTransfer):
    """Small transfer wrapper for the wing-specific control set."""

    def setCtrls(self, fks: list[str], ik: str, upv: str, hand_ik: str, ik_rot: str, hand_ik_rot: str) -> None:
        self.fkCtrls = [self._getNode(x) for x in fks]
        self.fkTargets = [self._getMth(x) for x in fks]
        self.ikCtrl = self._getNode(ik)
        self.ikTarget = self._getMth(ik)
        self.upvCtrl = self._getNode(upv)
        self.upvTarget = self._getMth(upv)
        self.handIkCtrl = self._getNode(hand_ik)
        self.handIkTarget = self._getNode(hand_ik.replace("_hand_ik_ctl", "_handIk_mth"))
        self.ikRotCtrl = self._getNode(ik_rot)
        self.handIkRotCtrl = self._getNode(hand_ik_rot)
        self.handIkRotTarget = self._getNode(hand_ik_rot.replace("_handIkRot_ctl", "_handIkRot_mth"))

    def transfer(
        self,
        startFrame: int,
        endFrame: int,
        onlyKeyframes: bool,
        switchTo: Optional[str] = None,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        if switchTo is not None and "fk" in switchTo.lower():
            val_src_nodes = self.fkTargets
            key_src_nodes = [self.ikCtrl, self.upvCtrl, self.handIkCtrl]
            key_src_nodes.append(self.ikRotCtrl)
            key_src_nodes.append(self.handIkRotCtrl)
            key_dst_nodes = self.fkCtrls
            self.bakeAnimation(
                self.getChangeAttrName(),
                val_src_nodes,
                key_src_nodes,
                key_dst_nodes,
                startFrame,
                endFrame,
                onlyKeyframes,
            )
            return

        self._transfer_to_ik(startFrame, endFrame, onlyKeyframes)

    def _get_transfer_to_ik_dst_nodes(self) -> list[PymelNode]:
        return [self.ikCtrl, self.upvCtrl, self.handIkCtrl, self.ikRotCtrl, self.handIkRotCtrl]

    def _collect_transfer_to_ik_data(
        self, startFrame: int, endFrame: int, onlyKeyframes: bool
    ) -> list[Optional[TransferFrameData]]:
        src_keys = pm.keyframe(self.fkCtrls, at=["t", "r", "s"], q=True) or []
        keyframe_list = sorted({int(x) for x in src_keys})
        frame_data = []
        for frame in range(startFrame, endFrame + 1):
            if onlyKeyframes and frame not in keyframe_list:
                frame_data.append(None)
                continue

            pm.currentTime(frame)
            frame_data.append(
                (
                    getMatrix(self.ikTarget),
                    _calculate_effective_upv_translate(self.upvCtrl, self.fkTargets),
                    getTranslation(self.handIkTarget),
                    getMatrix(self.handIkRotTarget),
                )
            )
        return frame_data

    def _clear_transfer_to_ik_keys(
        self, key_dst_nodes: list[PymelNode], switch_attr_name: str, startFrame: int, endFrame: int
    ) -> tuple:
        channels = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]
        roll_attrs = _get_roll_attrs_from_switch(switch_attr_name)
        mode_attrs = _get_attrs_from_switch(switch_attr_name, ("wristControlMode",))
        pm.cutKey(key_dst_nodes, at=channels, time=(startFrame, endFrame))
        pm.cutKey(switch_attr_name, time=(startFrame, endFrame))
        if roll_attrs:
            pm.cutKey(roll_attrs, time=(startFrame, endFrame))
        if mode_attrs:
            pm.cutKey(mode_attrs, time=(startFrame, endFrame))
        return channels, roll_attrs, mode_attrs

    def _apply_transfer_to_ik_frame(
        self,
        key_dst_nodes: list[PymelNode],
        switch_attr_name: str,
        channels: list[str],
        roll_attrs: list[str],
        mode_attrs: list[str],
        data: TransferFrameData,
    ) -> None:
        self.changeAttrToBoundValue()
        ik_matrix, upv_translate, hand_ik_translate, hand_ik_rot_matrix = data
        setMatrix(self.ikCtrl, ik_matrix)
        _set_upv_translate(self.upvCtrl, upv_translate)
        _reset_attrs(self.ikRotCtrl, ["rx", "ry", "rz"])
        setTranslation(self.handIkCtrl, hand_ik_translate)
        _reset_attrs(self.handIkCtrl, ["rx", "ry", "rz"])
        setRotationFromMatrix(self.handIkRotCtrl, hand_ik_rot_matrix)
        _set_attrs_zero(roll_attrs)
        pm.setKeyframe(key_dst_nodes, at=channels)
        pm.setKeyframe(switch_attr_name)
        if roll_attrs:
            pm.setKeyframe(roll_attrs)
        if mode_attrs:
            pm.setKeyframe(mode_attrs)

    def _transfer_to_ik(self, startFrame: int, endFrame: int, onlyKeyframes: bool) -> None:
        key_dst_nodes = self._get_transfer_to_ik_dst_nodes()
        switch_attr_name = self.getChangeAttrName()
        frame_data = self._collect_transfer_to_ik_data(startFrame, endFrame, onlyKeyframes)
        channels, roll_attrs, mode_attrs = self._clear_transfer_to_ik_keys(
            key_dst_nodes, switch_attr_name, startFrame, endFrame
        )
        for index, frame in enumerate(range(startFrame, endFrame + 1)):
            data = frame_data[index]
            if data is None:
                continue

            pm.currentTime(frame)
            self._apply_transfer_to_ik_frame(key_dst_nodes, switch_attr_name, channels, roll_attrs, mode_attrs, data)

    @staticmethod
    def showUI(
        model: object,
        ikfk_attr: str,
        uihost: str,
        fks: list[str],
        ik: str,
        upv: str,
        hand_ik: str,
        ik_rot: str,
        hand_ik_rot: str,
    ) -> None:
        try:
            for child in gqt.maya_main_window().children():
                if isinstance(child, IkFkTransfer):
                    child.deleteLater()
        except RuntimeError:
            pass

        try:
            ui = IkFkTransfer()
            ui.setModel(model)
            ui.setUiHost(uihost)
            ui.setSwitchedAttrShortName(ikfk_attr)
            ui.setCtrls(fks, ik, upv, hand_ik, ik_rot, hand_ik_rot)
            ui.setComboObj(None)
            ui.setComboBoxItemsFormList(["IK", "FK"])
            ui.createUI(gqt.maya_main_window())
            ui.show()
        except Exception as exc:
            traceback.print_exc()
            mgear.log(exc, mgear.sev_error)

    @staticmethod
    def execute(
        model: object,
        ikfk_attr: str,
        uihost: str,
        fks: list[str],
        ik: str,
        upv: str,
        hand_ik: str,
        ik_rot: str,
        hand_ik_rot: str,
        startFrame: Optional[int] = None,
        endFrame: Optional[int] = None,
        onlyKeyframes: Optional[bool] = None,
        switchTo: Optional[str] = None,
    ) -> None:
        if startFrame is None:
            startFrame = int(pm.playbackOptions(q=True, ast=True))
        if endFrame is None:
            endFrame = int(pm.playbackOptions(q=True, aet=True))
        if onlyKeyframes is None:
            onlyKeyframes = True
        if switchTo is None:
            switchTo = "fk"

        ui = IkFkTransfer()
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(ikfk_attr)
        ui.setCtrls(fks, ik, upv, hand_ik, ik_rot, hand_ik_rot)
        ui.setComboObj(None)
        ui.setComboBoxItemsFormList(["IK", "FK"])
        ui.getValue = lambda: 0.0 if "fk" in switchTo.lower() else 1.0
        ui.transfer(startFrame, endFrame, onlyKeyframes, switchTo=switchTo)

    @staticmethod
    def toIK(
        model: object,
        ikfk_attr: str,
        uihost: str,
        fks: list[str],
        ik: str,
        upv: str,
        hand_ik: str,
        ik_rot: str,
        hand_ik_rot: str,
        **kwargs: Any,
    ) -> None:
        kwargs.update({"switchTo": "ik"})
        IkFkTransfer.execute(
            model, ikfk_attr, uihost, fks, ik, upv, hand_ik, ik_rot=ik_rot, hand_ik_rot=hand_ik_rot, **kwargs
        )

    @staticmethod
    def toFK(
        model: object,
        ikfk_attr: str,
        uihost: str,
        fks: list[str],
        ik: str,
        upv: str,
        hand_ik: str,
        ik_rot: str,
        hand_ik_rot: str,
        **kwargs: Any,
    ) -> None:
        kwargs.update({"switchTo": "fk"})
        IkFkTransfer.execute(
            model, ikfk_attr, uihost, fks, ik, upv, hand_ik, ik_rot=ik_rot, hand_ik_rot=hand_ik_rot, **kwargs
        )


def getMatrix(obj: PymelNode) -> Matrix:
    return cmds.xform(obj.name(), q=True, ws=True, matrix=True)


def setMatrix(obj: PymelNode, mat: Matrix) -> None:
    cmds.xform(obj.name(), ws=True, matrix=mat)


def getTranslation(obj: PymelNode) -> list[float]:
    return cmds.xform(obj.name(), q=True, ws=True, translation=True)


def setTranslation(obj: PymelNode, values: list[float]) -> None:
    cmds.xform(obj.name(), ws=True, translation=values)


def setRotationFromMatrix(obj: PymelNode, mat: Matrix) -> None:
    rotation = om2.MTransformationMatrix(om2.MMatrix(mat)).rotation()
    cmds.xform(
        obj.name(),
        ws=True,
        rotation=[math.degrees(rotation.x), math.degrees(rotation.y), math.degrees(rotation.z)],
    )


def _set_upv_translate(upv_ctrl: PymelNode, values: list[float]) -> None:
    cmds.setAttr(upv_ctrl.name() + ".translate", values[0], values[1], values[2])


def _set_attrs_zero(attrs: list[str]) -> None:
    for attr in attrs:
        pm.setAttr(attr, 0.0)


def _reset_attrs(obj: PymelNode, attrs: list[str]) -> None:
    for attr in attrs:
        if obj.hasAttr(attr):
            obj.attr(attr).set(0.0)


def _get_roll_attrs_from_switch(switch_attr_name: str) -> list[str]:
    return _get_attrs_from_switch(switch_attr_name, ("roll",))


def _get_attrs_from_switch(switch_attr_name: str, attr_names: tuple[str, ...]) -> list[str]:
    node_name, blend_name = switch_attr_name.rsplit(".", 1)
    attrs = []
    for attr_name in attr_names:
        candidate = node_name + "." + blend_name.replace("blend", attr_name)
        if cmds.objExists(candidate):
            attrs.append(candidate)
    return attrs


def _get_node(namespace: str, name: str) -> PymelNode:
    name = anim_utils.stripNamespace(name)
    if namespace:
        node = anim_utils.getNode(":".join([namespace, name]))
    else:
        node = anim_utils.getNode(name)
    if not node:
        mgear.log("Can't find object : {0}".format(name), mgear.sev_error)
    return node


def _get_mth(namespace: str, name: str) -> PymelNode:
    if "_handIkRot_ctl" in name:
        query = name.replace("_handIkRot_ctl", "_handIkRot_mth")
        node = _get_node(namespace, query)
        if node:
            return node

    if "_hand_ik_ctl" in name:
        query = name.replace("_hand_ik_ctl", "_handIk_mth")
        node = _get_node(namespace, query)
        if node:
            return node

    parts = name.split("_")
    parts[-1] = "mth"
    query = "_".join(parts)

    node = _get_node(namespace, query)
    if not node:
        mgear.log("Can't find mth object : {0} for {1}".format(query, name), mgear.sev_comment)
        return _get_node(namespace, name)
    return node


def _calculate_upv_position(fk_goals: list[PymelNode]) -> VectorLike:
    start = fk_goals[0].getTranslation(space="world")
    mid = fk_goals[1].getTranslation(space="world")
    end = fk_goals[2].getTranslation(space="world")
    start_end = end - start
    start_mid = mid - start
    if start_end.length() == 0:
        return mid
    dot_p = start_mid * start_end
    proj = float(dot_p) / float(start_end.length())
    proj_vector = start_end.normal() * proj
    arrow_vector = (start_mid - proj_vector) * 1.5
    arrow_vector *= start_end.normal().length()
    return arrow_vector + mid


def _get_effective_upv_ref(upv_ctrl: PymelNode) -> Optional[PymelNode]:
    candidates = []
    for attr_name in ("translate", "tx", "ty", "tz"):
        candidates.extend(
            cmds.listConnections(
                upv_ctrl.name() + "." + attr_name,
                source=False,
                destination=True,
                plugs=False,
            )
            or []
        )

    for candidate in candidates:
        if cmds.nodeType(candidate) == "transform" and candidate.endswith("effectiveUpv_ref"):
            return pm.PyNode(candidate)

    for candidate in candidates:
        if cmds.nodeType(candidate) == "transform":
            return pm.PyNode(candidate)

    mgear.log("Can't find effective upv object from : {0}".format(upv_ctrl), mgear.sev_error)
    return None


def _world_point_to_local(point: WorldPoint, parent: PymelNode) -> list[float]:
    parent_matrix = om2.MMatrix(cmds.xform(parent.name(), q=True, ws=True, matrix=True))
    local_point = om2.MPoint(point[0], point[1], point[2], 1.0) * parent_matrix.inverse()
    return [local_point.x, local_point.y, local_point.z]


def _calculate_effective_upv_translate(upv_ctrl: PymelNode, fk_goals: list[PymelNode]) -> list[float]:
    upv_ref = _get_effective_upv_ref(upv_ctrl)
    if not upv_ref:
        position = _calculate_upv_position(fk_goals)
        return [position[0], position[1], position[2]]

    raw_parent = upv_ref.getParent()
    if raw_parent is None:
        raise ValueError("Effective upv object has no parent: {0}".format(upv_ref))

    parent = cast("PymelNode", raw_parent)
    return _world_point_to_local(_calculate_upv_position(fk_goals), parent)


def _key_controls(controls: list[PymelNode], time: float) -> None:
    for elem in controls:
        cmds.setKeyframe(str(elem), time=time)


def _match_to_fk(blend_attr: SettablePlug, fk_goals: list[PymelNode], fk_ctrls: list[PymelNode]) -> None:
    fk_mats = [getMatrix(src) for src in fk_goals]
    blend_attr.set(0.0)
    for mat, dst in zip(fk_mats, fk_ctrls):
        setMatrix(dst, mat)


def _match_to_ik(
    ikfk_attr: str,
    ui_node: PymelNode,
    ik_ctrl: PymelNode,
    ik_goal: PymelNode,
    upv_ctrl: PymelNode,
    fk_ctrls: list[PymelNode],
    fk_goals: list[PymelNode],
    hand_ik_ctrl: PymelNode,
    hand_ik_goal: PymelNode,
    ik_rot_ctrl: PymelNode,
    hand_ik_rot_ctrl: PymelNode,
    hand_ik_rot_goal: PymelNode,
) -> None:
    ik_mat = getMatrix(ik_goal)
    hand_translate = getTranslation(hand_ik_goal)
    hand_rot_mat = getMatrix(hand_ik_rot_goal)
    upv_translate = _calculate_effective_upv_translate(upv_ctrl, fk_goals)
    root_mat = getMatrix(fk_goals[0])
    ui_node.attr(ikfk_attr).set(1.0)
    setMatrix(ik_ctrl, ik_mat)
    _reset_attrs(ik_rot_ctrl, ["rx", "ry", "rz"])
    setTranslation(hand_ik_ctrl, hand_translate)
    _reset_attrs(hand_ik_ctrl, ["rx", "ry", "rz"])
    setRotationFromMatrix(hand_ik_rot_ctrl, hand_rot_mat)
    _set_upv_translate(upv_ctrl, upv_translate)
    for _ in range(10):
        cmds.xform(fk_ctrls[0].name(), ws=True, matrix=root_mat)
    for attr_name in ("roll",):
        attr = ikfk_attr.replace("blend", attr_name)
        if ui_node.hasAttr(attr):
            ui_node.attr(attr).set(0.0)


def ikFkMatch(
    namespace: object,
    ikfk_attr: str,
    ui_host: str,
    fks: list[str],
    ik: str,
    upv: str,
    hand_ik: str,
    ik_rot: str,
    hand_ik_rot: str,
    key: Optional[bool] = None,
) -> None:
    """Switch IK/FK while matching the visible controls."""

    if not isinstance(namespace, str):
        namespace = syn_uti.getNamespace(namespace)

    fk_ctrls = [_get_node(namespace, x) for x in fks]
    fk_goals = [_get_mth(namespace, x) for x in fks]
    ik_ctrl = _get_node(namespace, ik)
    ik_goal = _get_mth(namespace, ik)
    upv_ctrl = _get_node(namespace, upv)
    hand_ik_ctrl = _get_node(namespace, hand_ik)
    hand_ik_goal = _get_mth(namespace, hand_ik)
    ik_rot_ctrl = _get_node(namespace, ik_rot)
    hand_ik_rot_ctrl = _get_node(namespace, hand_ik_rot)
    hand_ik_rot_goal = _get_mth(namespace, hand_ik_rot)
    ui_node = _get_node(namespace, ui_host)
    blend_attr = ui_node.attr(ikfk_attr)

    all_controls = [*list(fk_ctrls), ik_ctrl, upv_ctrl, ui_node]
    all_controls.append(ik_rot_ctrl)
    all_controls.append(hand_ik_ctrl)
    all_controls.append(hand_ik_rot_ctrl)
    if key:
        _key_controls(all_controls, cmds.currentTime(query=True) - 1.0)

    switch_to_fk = blend_attr.get() == 1.0
    if switch_to_fk:
        _match_to_fk(blend_attr, fk_goals, fk_ctrls)
    else:
        _match_to_ik(
            ikfk_attr,
            ui_node,
            ik_ctrl,
            ik_goal,
            upv_ctrl,
            fk_ctrls,
            fk_goals,
            hand_ik_ctrl,
            hand_ik_goal,
            ik_rot_ctrl,
            hand_ik_rot_ctrl,
            hand_ik_rot_goal,
        )

    if key:
        _key_controls(all_controls, cmds.currentTime(query=True))
