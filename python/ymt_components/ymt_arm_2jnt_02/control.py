##################################################
# GLOBAL
##################################################
import sys
import re
import traceback

import maya.cmds as cmds
import pymel.core as pm

import mgear
from mgear.core import (
    pyqt as gqt,
    transform,
    anim_utils,
)

import mgear.synoptic.utils as syn_uti
# import mgear.core.synoptic.widgets as syn_widget

import gml_maya.decorator as deco

from ymt_components.control import AbstractControllerButton
import ymt_components.ymt_arm_2jnt_02 as comp

from logging import (  # noqa:F401 pylint: disable=unused-import, wrong-import-order
    StreamHandler,
    getLogger,
    WARN,
    DEBUG,
    INFO
)

if sys.version_info >= (3, 0):  # pylint: disable=using-constant-test  # pylint: disable=using-constant-test, wrong-import-order
    # For type annotation
    from typing import (  # NOQA: F401 pylint: disable=unused-import
        Optional,
        Dict,
        List,
        Tuple,
        Pattern,
        Callable,
        Any,
        Text,
        Generator,
        Union
    )
###############################################################################
handler = StreamHandler()
handler.setLevel(DEBUG)

logger = getLogger(__name__)
logger.setLevel(WARN)
logger.setLevel(DEBUG)
logger.setLevel(INFO)
logger.addHandler(handler)
logger.propagate = False
# =============================================================================

QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()


##################################################
# PROMOTED WIDGETS
##################################################
# They must be declared first because they are used in the widget.ui


class ikfkMatchAllButton(AbstractControllerButton):

    def __init__(self, *args, **kwargs):

        super(ikfkMatchAllButton, self).__init__(*args, **kwargs)
        self.model = syn_uti.getModel(self)

    controllers = {
        "ikfk_attr": "arm_blend",
        "fk0": "arm_"
    }

    def mousePressEvent(self, event):
        # type: (QtCore.QEvent) -> None

        mouse_button = event.button()

        if not self.isControllerSetup():
            self.lookupControllers()
            self.ikRot = self.ik.replace("_ik_", "_rot_")

        if mouse_button == QtCore.Qt.RightButton:
            IkFkTransfer.showUI(
                self.model, self.ikfk_attr, self.uiHost_name, self.fks, self.ik, self.upv, self.ikRot)
            return

        else:
            ikFkMatch(
                self.model, self.ikfk_attr, self.uiHost_name, self.fks, self.ik, self.upv, self.ikRot)
            return


class ikfkMatchButton(AbstractControllerButton):
    def __init__(self, *args, **kwargs):

        print(args)
        print(kwargs)
        super(ikfkMatchButton, self).__init__(*args, **kwargs)
        print(self.parentWidget())
        self.model = syn_uti.getModel(self)

    def mousePressEvent(self, event):
        # type: (QtCore.QEvent) -> None

        mouse_button = event.button()
        model = syn_uti.getModel(self)

        if not self.isControllerSetup():
            self.lookupControllers()
            self.ikRot = self.ik.replace("_ik_", "_rot_")

        if mouse_button == QtCore.Qt.RightButton:
            IkFkTransfer.showUI(
                model, self.ikfk_attr, self.uiHost_name, self.fks, self.ik, self.upv, self.ikRot)
            return

        else:
            ikFkMatch(
                model, self.ikfk_attr, self.uiHost_name, self.fks, self.ik, self.upv, self.ikRot)
            return


class ikRotSpaceMatchButton(AbstractControllerButton):

    def mousePressEvent(self, event):
        # type: (QtCore.QEvent) -> None

        mouse_button = event.button()
        model = syn_uti.getModel(self)

        if not self.button.isControllerSetup():
            self.button.lookupControllers()
            self.button.ikRot = self.button.ik.replace("_ik_", "_rot_")

        if mouse_button == QtCore.Qt.RightButton:
            IkFkTransfer.showUI(
                model, self.button.ikfk_attr, self.button.uiHost_name, self.button.fks, self.button.ik, self.button.upv, self.button.ikRot)
            return

        else:
            ikRotSpaceMatch(model, self.button.uiHost_name, self.button.ikRot)
            return


class IkFkTransfer(syn_uti.IkFkTransfer):

    # ----------------------------------------------------------------

    def setCtrls(self, fks, ik, upv):
        # type: (list[str], str, str) -> None
        """gather maya PyNode represented each controllers"""

        self.fkCtrls = [self._getNode(x) for x in fks]
        self.fkTargets = [self._getMth(x) for x in fks]

        self.ikCtrl = self._getNode(ik)
        self.ikTarget = self._getMth(ik)

        self.upvCtrl = self._getNode(upv)
        self.upvTarget = self._getMth(upv)

        self.ikRotCtrl = self._getNode(ik.replace("_ik_", "_rot_"))
        self.ikRotTarget = self.ikTarget

    # ----------------------------------------------------------------

    def transfer(self, startFrame, endFrame, onlyKeyframes, switchTo=None, *args, **kargs):
        # type: (int, int, bool, str, *str, **str) -> None

        if switchTo is not None:
            if "fk" in switchTo.lower():

                targets = self.fkTargets[0:-1] + [self.ikRotCtrl]
                val_src_nodes = targets
                key_src_nodes = [self.ikCtrl, self.upvCtrl, self.ikRotCtrl]
                key_dst_nodes = self.fkCtrls

            else:

                val_src_nodes = [self.ikTarget, self.upvTarget]
                key_src_nodes = self.fkCtrls
                key_dst_nodes = [self.ikCtrl, self.upvCtrl]

        else:
            if self.comboBoxSpaces.currentIndex() != 0:  # to FK

                targets = self.fkTargets[0:-1] + [self.ikRotCtrl]
                val_src_nodes = targets
                key_src_nodes = [self.ikCtrl, self.upvCtrl]
                key_dst_nodes = self.fkCtrls

            else:  # to IK

                val_src_nodes = [self.ikTarget, self.upvTarget]
                key_src_nodes = self.fkCtrls
                key_dst_nodes = [self.ikCtrl, self.upvCtrl]

        self.bakeAnimation(self.getChangeAttrName(), val_src_nodes, key_src_nodes, key_dst_nodes,
                           startFrame, endFrame, onlyKeyframes)

    @staticmethod
    def showUI(model, ikfk_attr, uihost, fks, ik, upv, *args):
        # type: (pm.nodetypes.Transform, str, str, List[str], str, str, *str) -> None

        try:
            for c in gqt.maya_main_window().children():
                if isinstance(c, IkFkTransfer):
                    c.deleteLater()

        except RuntimeError:
            pass

        # Create minimal UI object
        ui = IkFkTransfer()
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(ikfk_attr)
        ui.setCtrls(fks, ik, upv)
        ui.setComboObj(None)
        ui.setComboBoxItemsFormList(["IK", "FK"])

        # Delete the UI if errors occur to avoid causing winEvent
        # and event errors (in Maya 2014)
        try:
            ui.createUI(gqt.maya_main_window())
            ui.show()

        except Exception as e:
            ui.deleteLater()
            traceback.print_exc()
            mgear.log(e, mgear.sev_error)

    @staticmethod
    def execute(model, ikfk_attr, uihost, fks, ik, upv,
                startFrame=None, endFrame=None, onlyKeyframes=None, switchTo=None):
        # type: (pm.nodetypes.Transform, str, str, List[str], str, str, int, int, bool, str) -> None
        """transfer without displaying UI"""

        if startFrame is None:
            startFrame = int(pm.playbackOptions(q=True, ast=True))

        if endFrame is None:
            endFrame = int(pm.playbackOptions(q=True, aet=True))

        if onlyKeyframes is None:
            onlyKeyframes = True

        if switchTo is None:
            switchTo = "fk"

        # Create minimal UI object
        ui = IkFkTransfer()

        ui.setComboObj(None)
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(ikfk_attr)
        ui.setCtrls(fks, ik, upv)
        ui.setComboBoxItemsFormList(["IK", "FK"])
        ui.getValue = lambda: 0.0 if "fk" in switchTo.lower() else 1.0
        ui.transfer(startFrame, endFrame, onlyKeyframes, switchTo="fk")

    @staticmethod
    def toIK(model, ikfk_attr, uihost, fks, ik, upv, **kwargs):
        # type: (pm.nodetypes.Transform, str, str, List[str], str, str, **str) -> None

        kwargs.update({"switchTo": "ik"})
        IkFkTransfer.execute(model, ikfk_attr, uihost, fks, ik, upv, **kwargs)

    @staticmethod
    def toFK(model, ikfk_attr, uihost, fks, ik, upv, **kwargs):
        # type: (pm.nodetypes.Transform, str, str, List[str], str, str, **str) -> None

        kwargs.update({"switchTo": "fk"})
        IkFkTransfer.execute(model, ikfk_attr, uihost, fks, ik, upv, **kwargs)


def getMatrix(obj):
    # type: (pm.datatypes.Transform) -> List[float]
    xform = cmds.xform("{}".format(obj.name()), q=True, ws=True, matrix=True)
    return xform


def setMatrix(obj, mat):
    # type: (pm.datatypes.Transform) -> None
    cmds.xform("{}".format(obj.name()), ws=True, matrix=mat)


##################################################
# IK FK switch match
##################################################
# ================================================

@deco.autokey_off
def ikFkMatch(
        namespace,
        ikfk_attr,
        ui_host,
        fks,
        ik,
        upv,
        ik_rot=None,
        key=None):
    """Switch IK/FK with matching functionality."""

    # returns a pymel node on the given name
    def _get_node(name):
        # type: (Text) -> pm.nodetypes.Transform
        name = anim_utils.stripNamespace(name)
        if namespace:
            node = anim_utils.getNode(":".join([namespace, name]))
        else:
            node = anim_utils.getNode(name)

        if not node:
            mgear.log("Can't find object : {0}".format(name), mgear.sev_error)

        return node

    # returns matching node
    def _get_mth(name):
        # type: (str) -> pm.nodetypes.Transform
        tmp = name.split("_")
        tmp[-1] = "mth"
        query = "_".join(tmp)
        n = _get_node(query)

        if not n:
            mgear.log("Can't find mth object : {0} for {1}".format(query, name), mgear.sev_comment)
            return _get_node(name)
        else:
            return n

    # get things ready
    fk_ctrls = [_get_node(x) for x in fks]
    fk_goals = [_get_mth(x) for x in fks]
    ik_ctrl = _get_node(ik)
    ik_goal = _get_mth(ik)
    upv_ctrl = _get_node(upv)

    if ik_rot:
        ik_rot_node = _get_node(ik_rot)
        ik_rot_goal = _get_mth(ik_rot)

    ui_node = _get_node(ui_host)
    o_attr = ui_node.attr(ikfk_attr)

    switch_to_fk = (o_attr.get() == 1.0)
    switch_to_ik = (not switch_to_fk)

    # sets keyframes before snapping
    if key:
        _all_controls = []
        _all_controls.extend(fk_ctrls)
        _all_controls.extend([ik_ctrl, upv_ctrl, ui_node])
        if ik_rot:
            _all_controls.extend([ik_rot_node])
        [cmds.setKeyframe("{}".format(elem),
                          time=(cmds.currentTime(query=True) - 1.0))
         for elem in _all_controls]

    # if is IKw then snap FK
    if switch_to_fk:

        world_matrices = []
        for src, _ in zip(fk_goals, fk_ctrls):
            world_matrices.append(getMatrix(src))

        o_attr.set(0.0)

        for mat, dst in zip(world_matrices, fk_ctrls):
            setMatrix(dst, mat)

        for mat, dst in zip(world_matrices, fk_ctrls):
            setMatrix(dst, mat)

    # if is FKw then sanp IK
    elif switch_to_ik:

        shoulder_mat = getMatrix(fk_goals[0])
        ik_mat = getMatrix(ik_goal)

        # transform.matchWorldTransform(ik_goal, ik_ctrl)
        if ik_rot:
            rot_mat = getMatrix(ik_rot_goal)
            # transform.matchWorldTransform(ik_rot_goal, ik_rot_node)

        upv_mat = getMatrix(fk_goals[2])

        o_attr.set(1.0)

        setMatrix(ik_ctrl, ik_mat)
        setMatrix(upv_ctrl, upv_mat)
        # for _ in range(10):
        #     fk_ctrls[0].setMatrix(shoulder_mat, worldSpace=True)

        for _ in range(20):
            cmds.xform(fk_ctrls[0].name(), ws=True, matrix=shoulder_mat)
        if ik_rot:
            setMatrix(ik_rot_node, rot_mat)

        # transform.matchWorldTransform(fk_goals[1], upv_ctrl)
        # calculates new pole vector position
        start_end = (fk_goals[-1].getTranslation(space="world") - fk_goals[1].getTranslation(space="world"))
        start_mid = (fk_goals[2].getTranslation(space="world") - fk_goals[1].getTranslation(space="world"))

        dot_p = start_mid * start_end
        proj = float(dot_p) / float(start_end.length())
        proj_vector = start_end.normal() * proj
        arrow_vector = (start_mid - proj_vector) * 1.5
        arrow_vector *= start_end.normal().length()
        final_vector = (arrow_vector + fk_goals[2].getTranslation(space="world"))
        upv_ctrl.setTranslation(final_vector, space="world")

        # sets blend attribute new value
        # o_attr.set(1.0)
        roll_att = ui_node.attr(ikfk_attr.replace("blend", "roll"))
        roll_att.set(0.0)

        setMatrix(ik_ctrl, ik_mat)
        if ik_rot:
            setMatrix(ik_rot_node, rot_mat)
        # upv_ctrl.setMatrix(upv_mat, worldSpace=True)
        for _ in range(20):
            cmds.xform(fk_ctrls[0].name(), ws=True, matrix=shoulder_mat)

    # sets keyframes
    if key:
        [cmds.setKeyframe("{}".format(elem),
                          time=(cmds.currentTime(query=True)))
         for elem in _all_controls]


def ikRotSpaceMatch(model, uiHost_name, ikRot, rotSpaceAttr="arm_rot_space"):

    nameSpace = syn_uti.getNamespace(model)

    ikRot = _getNode(nameSpace, ikRot)
    uiNode = _getNode(nameSpace, uiHost_name)

    oAttr = uiNode.attr(rotSpaceAttr)
    val = oAttr.get()

    worldRot = cmds.xform(ikRot.name(), q=True, worldSpace=True, matrix=True)

    # toggle attribute of parent space
    if val == 1.0:
        oAttr.set(0.0)

    elif val == 0.0:
        oAttr.set(1.0)

    cmds.xform(ikRot.name(), worldSpace=True, matrix=worldRot)


def _getNode(nameSpace, name):
    # type: (str, str) -> pm.nodetypes.Transform
    node = syn_uti.getNode(name)

    if node:
        return node

    node = syn_uti.getNode(":".join([nameSpace, name]))

    if not node:
        mgear.log("Can't find object : {0}".format(name), mgear.sev_error)

    return node


def _getMth(nameSpace, name):
    # type: (str, str) -> pm.nodetypes.Transform
    tmp = name.split("_")
    tmp[-1] = "mth"
    return _getNode(nameSpace, "_".join(tmp))
