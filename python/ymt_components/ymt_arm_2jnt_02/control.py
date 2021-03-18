##################################################
# GLOBAL
##################################################
import re
import traceback

import maya.cmds as cmds
import pymel.core as pm

import mgear
import mgear.core.pyqt as gqt

import mgear.core.transform as tra
import mgear.synoptic.utils as syn_uti
# import mgear.core.synoptic.widgets as syn_widget

from ymt_components.control import AbstractControllerButton
import ymt_components.ymt_arm_2jnt_02 as comp

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


##################################################
# IK FK switch match
##################################################
# ================================================
def ikFkMatch(model, ikfk_attr, uiHost_name, fks, ik, upv, ikRot=None):
    # type: (pm.nodetypes.Transform, str, str, List[str], str, str, str) -> None

    nameSpace = syn_uti.getNamespace(model)

    fkCtrls = [_getNode(nameSpace, x) for x in fks]
    fkTargets = [_getMth(nameSpace, x) for x in fks]

    ikCtrl = _getNode(nameSpace, ik)
    ikTarget = _getMth(nameSpace, ik)

    upvCtrl = _getNode(nameSpace, upv)
    upvTarget = _getMth(nameSpace, upv)

    if ikRot:
        ikRotNode = _getNode(nameSpace, ikRot)
        ikRotTarget = ikTarget

    uiNode = _getNode(nameSpace, uiHost_name)
    oAttr = uiNode.attr(ikfk_attr)
    val = oAttr.get()

    # if is IK change to FK
    if val == 1.0:

        for target, ctl in zip(fkTargets, fkCtrls):
            tra.matchWorldTransform(target, ctl)

        if ikRot:
            tra.matchWorldTransform(ikRotNode, fkCtrls[-1])
            rot = cmds.xform(ikTarget.name(), query=True, ro=True)

            if re.search(r"_L\d", ikCtrl.name()):
                cmds.rotate(rot[0] * -1., rot[2], rot[1] * -1, fkCtrls[-1].name(), relative=True, objectSpace=True)

            else:
                cmds.rotate(rot[0] * -1., rot[2] * -1, rot[1], fkCtrls[-1].name(), relative=True, objectSpace=True)

        oAttr.set(0.0)

    # if is FK change to IK
    elif val == 0.0:

        tra.matchWorldTransform(ikTarget, ikCtrl)
        if ikRot:
            tra.matchWorldTransform(ikRotTarget, ikRotNode)

        tra.matchWorldTransform(upvTarget, upvCtrl)
        oAttr.set(1.0)


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

    node = syn_uti.getNode(":".join([nameSpace, name]))

    if not node:
        mgear.log("Can't find object : {0}".format(name), mgear.sev_error)

    return node


def _getMth(nameSpace, name):
    # type: (str, str) -> pm.nodetypes.Transform
    tmp = name.split("_")
    tmp[-1] = "mth"
    return _getNode(nameSpace, "_".join(tmp))
