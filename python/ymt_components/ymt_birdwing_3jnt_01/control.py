"""Controller helpers for ymt_birdwing_3jnt_01."""

import traceback

import maya.cmds as cmds
try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm

import mgear
from mgear.core import anim_utils, pyqt as gqt
import mgear.synoptic.utils as syn_uti

from ymt_components.control import AbstractControllerButton

QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()


class ikfkMatchAllButton(AbstractControllerButton):
    controllers = {
        "ikfk_attr": "wing_blend",
        "fk0": "wing_",
    }

    def __init__(self, *args, **kwargs):
        super(ikfkMatchAllButton, self).__init__(*args, **kwargs)
        self.model = syn_uti.getModel(self)

    def mousePressEvent(self, event):
        if not self.isControllerSetup():
            self.lookupControllers()
            self.hand_ik = self.ik.replace("_ik_", "_hand_ik_")

        if event.button() == QtCore.Qt.RightButton:
            IkFkTransfer.showUI(
                self.model,
                self.ikfk_attr,
                self.uiHost_name,
                self.fks,
                self.ik,
                self.upv,
                self.hand_ik,
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
        )


class ikfkMatchButton(ikfkMatchAllButton):
    pass


class IkFkTransfer(syn_uti.IkFkTransfer):
    """Small transfer wrapper for the wing-specific control set."""

    def setCtrls(self, fks, ik, upv, hand_ik):
        self.fkCtrls = [self._getNode(x) for x in fks]
        self.fkTargets = [self._getMth(x) for x in fks]
        self.ikCtrl = self._getNode(ik)
        self.ikTarget = self._getMth(ik)
        self.upvCtrl = self._getNode(upv)
        self.upvTarget = self._getMth(upv)
        self.handIkCtrl = self._getNode(hand_ik)
        self.handIkTarget = self._getNode(hand_ik.replace("_hand_ik_ctl", "_handIk_mth"))

    def transfer(self, startFrame, endFrame, onlyKeyframes, switchTo=None, *args, **kwargs):
        if switchTo is not None and "fk" in switchTo.lower():
            val_src_nodes = self.fkTargets
            key_src_nodes = [self.ikCtrl, self.upvCtrl, self.handIkCtrl]
            key_dst_nodes = self.fkCtrls
        else:
            val_src_nodes = [self.ikTarget, self.upvTarget, self.handIkTarget]
            key_src_nodes = self.fkCtrls
            key_dst_nodes = [self.ikCtrl, self.upvCtrl, self.handIkCtrl]

        self.bakeAnimation(
            self.getChangeAttrName(),
            val_src_nodes,
            key_src_nodes,
            key_dst_nodes,
            startFrame,
            endFrame,
            onlyKeyframes,
        )

    @staticmethod
    def showUI(model, ikfk_attr, uihost, fks, ik, upv, hand_ik):
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
            ui.setCtrls(fks, ik, upv, hand_ik)
            ui.setComboObj(None)
            ui.setComboBoxItemsFormList(["IK", "FK"])
            ui.createUI(gqt.maya_main_window())
            ui.show()
        except Exception as exc:
            traceback.print_exc()
            mgear.log(exc, mgear.sev_error)

    @staticmethod
    def execute(
        model,
        ikfk_attr,
        uihost,
        fks,
        ik,
        upv,
        hand_ik,
        startFrame=None,
        endFrame=None,
        onlyKeyframes=None,
        switchTo=None,
    ):
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
        ui.setCtrls(fks, ik, upv, hand_ik)
        ui.setComboObj(None)
        ui.setComboBoxItemsFormList(["IK", "FK"])
        ui.getValue = lambda: 0.0 if "fk" in switchTo.lower() else 1.0
        ui.transfer(startFrame, endFrame, onlyKeyframes, switchTo=switchTo)

    @staticmethod
    def toIK(model, ikfk_attr, uihost, fks, ik, upv, hand_ik, **kwargs):
        kwargs.update({"switchTo": "ik"})
        IkFkTransfer.execute(model, ikfk_attr, uihost, fks, ik, upv, hand_ik, **kwargs)

    @staticmethod
    def toFK(model, ikfk_attr, uihost, fks, ik, upv, hand_ik, **kwargs):
        kwargs.update({"switchTo": "fk"})
        IkFkTransfer.execute(model, ikfk_attr, uihost, fks, ik, upv, hand_ik, **kwargs)


def getMatrix(obj):
    return cmds.xform(obj.name(), q=True, ws=True, matrix=True)


def setMatrix(obj, mat):
    cmds.xform(obj.name(), ws=True, matrix=mat)


def _get_node(namespace, name):
    name = anim_utils.stripNamespace(name)
    if namespace:
        node = anim_utils.getNode(":".join([namespace, name]))
    else:
        node = anim_utils.getNode(name)
    if not node:
        mgear.log("Can't find object : {0}".format(name), mgear.sev_error)
    return node


def _get_mth(namespace, name):
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


def _calculate_upv_position(fk_goals):
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


def ikFkMatch(namespace, ikfk_attr, ui_host, fks, ik, upv, hand_ik=None, key=None):
    """Switch IK/FK while matching the visible controls."""

    if not isinstance(namespace, str):
        namespace = syn_uti.getNamespace(namespace)

    fk_ctrls = [_get_node(namespace, x) for x in fks]
    fk_goals = [_get_mth(namespace, x) for x in fks]
    ik_ctrl = _get_node(namespace, ik)
    ik_goal = _get_mth(namespace, ik)
    upv_ctrl = _get_node(namespace, upv)
    hand_ik_ctrl = _get_node(namespace, hand_ik) if hand_ik else None
    hand_ik_goal = _get_mth(namespace, hand_ik) if hand_ik else None
    ui_node = _get_node(namespace, ui_host)
    blend_attr = ui_node.attr(ikfk_attr)

    all_controls = list(fk_ctrls) + [ik_ctrl, upv_ctrl, ui_node]
    if hand_ik_ctrl:
        all_controls.append(hand_ik_ctrl)
    if key:
        for elem in all_controls:
            cmds.setKeyframe(str(elem), time=(cmds.currentTime(query=True) - 1.0))

    switch_to_fk = blend_attr.get() == 1.0
    if switch_to_fk:
        fk_mats = [getMatrix(src) for src in fk_goals]
        blend_attr.set(0.0)
        for mat, dst in zip(fk_mats, fk_ctrls):
            setMatrix(dst, mat)
    else:
        ik_mat = getMatrix(ik_goal)
        hand_mat = getMatrix(hand_ik_goal) if hand_ik_goal else None
        upv_pos = _calculate_upv_position(fk_goals)
        root_mat = getMatrix(fk_goals[0])
        blend_attr.set(1.0)
        setMatrix(ik_ctrl, ik_mat)
        if hand_ik_ctrl and hand_mat:
            setMatrix(hand_ik_ctrl, hand_mat)
        upv_ctrl.setTranslation(upv_pos, space="world")
        for _ in range(10):
            cmds.xform(fk_ctrls[0].name(), ws=True, matrix=root_mat)
        for attr_name in ("roll", "handRoll"):
            attr = ikfk_attr.replace("blend", attr_name)
            if ui_node.hasAttr(attr):
                ui_node.attr(attr).set(0.0)

    if key:
        for elem in all_controls:
            cmds.setKeyframe(str(elem), time=cmds.currentTime(query=True))
