# import re

import maya.cmds as cmds
import pymel.core as pm

import mgear
from mgear.vendor.Qt import QtCore, QtWidgets
from mgear.core import attribute
from mgear.core import pyqt
import mgear.core.anim_utils as anim_utils
import mgear.synoptic.utils as syn_utils
import mgear.core.utils as utils

import gml_maya.decorator as deco
import gml_maya.node as node_utils

if False:
    # For type annotation
    from typing import Optional, Dict, List, Tuple, Pattern, Callable, Any, Text  # NOQA
    from pm.notetypes import Transform


class MirrorEntry(object):

    def __init__(self, target, attr, val):
        self.target = target
        self.attr = attr
        self.val = val


class MirrorPoseButton(QtWidgets.QPushButton):

    def mousePressEvent(self, event):

        mirrorPose()


class FlipPoseButton(QtWidgets.QPushButton):

    def mousePressEvent(self, event):

        mirrorPose(True)


class ikfkMatchButton(QtWidgets.QPushButton):

    MAXIMUM_TRY_FOR_SEARCHING_FK = 1000

    def __init__(self, *args, **kwargs):
        # type: (*str, **str) -> None
        super(ikfkMatchButton, self).__init__(*args, **kwargs)
        self.numFkControllers = None  # type: Optional[int]

    def searchNumberOfFkControllers(self):
        # type: () -> int

        for i in range(self.MAXIMUM_TRY_FOR_SEARCHING_FK):
            prop = self.property("fk{0}".format(str(i)))
            if not prop:
                return i

        return 0

    def mousePressEvent(self, event):
        # type: (QtCore.QEvent) -> None

        mouse_button = event.button()

        model = syn_utils.getModel(self)
        ikfk_attr = str(self.property("ikfk_attr"))
        uiHost_name = str(self.property("uiHost_name"))

        if not self.numFkControllers:
            self.numFkControllers = self.searchNumberOfFkControllers()

        additional_fk = self.property("additional_fk")
        if additional_fk:
            fks = [additional_fk]
        else:
            fks = []

        for i in range(self.numFkControllers):
            label = "fk{0}".format(str(i))
            prop = str(self.property(label))
            fks.append(prop)

        ik = str(self.property("ik"))
        upv = str(self.property("upv"))
        ikRot = str(self.property("ikRot"))
        if ikRot == "None":
            ikRot = None

        if mouse_button == QtCore.Qt.RightButton:
            IkFkTransfer.showUI(
                model, ikfk_attr, uiHost_name, fks, ik, upv, ikRot)
            return

        else:
            current_namespace = anim_utils.getNamespace(model)
            ikFkMatch(current_namespace, ikfk_attr, uiHost_name, fks, ik, upv, ikRot)
            return


@deco.autokey_off
@utils.one_undo
def mirrorPose(flip=False, nodes=None):
    """Summary

    Args:
        flip (bool, optiona): Set the function behaviout to flip
        nodes (None,  [PyNode]): Controls to mirro/flip the pose
    """
    if nodes is None:
        nodes = pm.selected()

    try:
        nameSpace = False
        if nodes:
            nameSpace = syn_utils.getNamespace(nodes[0])

        mirrorEntries = []
        for oSel in nodes:
            mirrorEntries.extend(gatherMirrorData(nameSpace, oSel, flip))
    except:
        import traceback
        traceback.print_exc()

    for dat in mirrorEntries:
        applyMirror(nameSpace, dat)


def applyMirror(nameSpace, mirrorEntry):
    """Apply mirro pose

    Args:
        nameSpace (str): Namespace
        mirrorEntry (list): List witht the mirror entry template
    """
    node = mirrorEntry.target
    attr = mirrorEntry.attr
    val = mirrorEntry.val

    try:
        if (
            pm.attributeQuery(attr, node=node, shortName=True, exists=True, keyable=True) and not node.attr(attr).isLocked()
        ):
            if isinstance(val, str) or isinstance(val, unicode):
                return

            node.attr(attr).set(val)

    except RuntimeError:
        mgear.log("applyMirror failed: {0} {1}: {2}".format(node.name(), attr, val), mgear.sev_error)


def gatherMirrorData(nameSpace, node, flip):
    """Get the data to mirror

    Args:
        nameSpace (str): Namespace
        node (PyNode): No
        flip (TYPE): flip option

    Returns:
        [dict[str]: The mirror data
    """
    if anim_utils.isSideElement(node.name()):

        nameParts = anim_utils.stripNamespace(node.name()).split("|")[-1]
        nameParts = anim_utils.swapSideLabel(nameParts)
        nameTarget = ":".join([nameSpace, nameParts])

        oTarget = anim_utils.getNode(nameTarget)

        return calculateMirrorData(node, oTarget, flip=flip)

    else:
        return calculateMirrorData(node, node, flip=False)


def calculateMirrorData(srcNode, targetNode, flip=False):
    # type: (Transform, Transform, bool) -> List[MirrorEntry]
    """Calculate the mirror data

    Args:
        srcNode (str): The source Node
        targetNode ([dict[str]]): Target node
        flip (bool, optional): flip option

    Returns:
        [{"target": node, "attr": at, "val": flipVal}]
    """

    results = []

    # mirror attribute of source
    for attrName in anim_utils.listAttrForMirror(srcNode):

        full_path = "{}.{}".format(srcNode.name(), attrName)
        if node_utils.is_proxy_attribute(full_path):
            continue

        # whether does attribute "invTx" exists when attrName is "tx"
        invCheckName = anim_utils.getInvertCheckButtonAttrName(attrName)
        if not pm.attributeQuery(invCheckName,
                                 node=srcNode,
                                 shortName=True,
                                 exists=True,
                                 keyable=True):

            # if not exists, straight
            inv = 1

        else:
            # if exists, check its value
            invAttr = srcNode.attr(invCheckName)
            if invAttr.get():
                inv = -1
            else:
                inv = 1

        # whether does attribute "invTx" exists when attrName is "tx"
        pivotCheckName = getPivotCheckButtonAttrName(attrName)
        if not pm.attributeQuery(pivotCheckName,
                                 node=srcNode,
                                 shortName=True,
                                 exists=True,
                                 keyable=True):

            # if not exists, straight
            pivot = 0.

        else:
            # if exists, check its value
            pivotAttr = srcNode.attr(pivotCheckName)
            pivot = pivotAttr.get()

        # if attr name is side specified, record inverted attr name
        if anim_utils.isSideElement(attrName):
            invAttrName = anim_utils.swapSideLabel(attrName)
        else:
            invAttrName = attrName

        # if flip enabled record self also
        if flip:
            flipVal = targetNode.attr(attrName).get()
            if isinstance(flipVal, float):
                entry = MirrorEntry(srcNode, invAttrName, (flipVal + pivot) * inv)
            else:
                entry = MirrorEntry(srcNode, invAttrName, (flipVal) * inv)

            results.append(entry)

        if isinstance(srcNode.attr(attrName).get(), float):
            entry = MirrorEntry(targetNode, invAttrName, (srcNode.attr(attrName).get() + pivot) * inv)
        else:
            entry = MirrorEntry(targetNode, invAttrName, (srcNode.attr(attrName).get()) * inv)
        results.append(entry)

    return results


def getPivotCheckButtonAttrName(str):
    # type: (Text) -> Text
    """Get the invert check butto attribute name

    Args:
        str (str): The attribute name

    Returns:
        str: The checked attribute name
    """
    return "invPivot{0}".format(str.lower().capitalize())


@deco.autokey_off
def ikFkMatch(namespace,
              ikfk_attr,
              ui_host,
              fks,
              ik,
              upv,
              ik_rot=None,
              key=None):
    """Switch IK/FK with matching functionality

    This function is meant to work with 2 joint limbs.
    i.e: human legs or arms

    Args:
        namespace (str): Rig name space
        ikfk_attr (str): Blend ik fk attribute name
        ui_host (str): Ui host name
        fks ([str]): List of fk controls names
        ik (str): Ik control name
        upv (str): Up vector control name
        ikRot (None, str): optional. Name of the Ik Rotation control
        key (None, bool): optional. Whether we do an snap with animation
    """

    # returns a pymel node on the given name
    def _get_node(name):
        # type: (str) -> pm.nodetypes.Transform
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
    is_leg = ("leg" in ikfk_attr)

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
            world_matrices.append(src.getMatrix(worldSpace=True))

        o_attr.set(0.0)

        for mat, dst in zip(world_matrices, fk_ctrls):
            dst.setMatrix(mat, worldSpace=True)

        for mat, dst in zip(world_matrices, fk_ctrls):
            dst.setMatrix(mat, worldSpace=True)

    # if is FKw then sanp IK
    elif switch_to_ik:

        shoulder_mat = fk_goals[0].getMatrix(worldSpace=True)
        ik_mat = ik_goal.getMatrix(worldSpace=True)

        # transform.matchWorldTransform(ik_goal, ik_ctrl)
        if ik_rot:
            rot_mat = ik_rot_goal.getMatrix(worldSpace=True)
            # transform.matchWorldTransform(ik_rot_goal, ik_rot_node)

        if is_leg:
            upv_mat = fk_goals[1].getMatrix(worldSpace=True)
        else:
            upv_mat = fk_goals[2].getMatrix(worldSpace=True)

        o_attr.set(1.0)

        ik_ctrl.setMatrix(ik_mat, worldSpace=True)
        if ik_rot:
            ik_rot_node.setMatrix(rot_mat, worldSpace=True)
        upv_ctrl.setMatrix(upv_mat, worldSpace=True)
        # for _ in range(10):
        #     fk_ctrls[0].setMatrix(shoulder_mat, worldSpace=True)

        _m = []
        for row in shoulder_mat:
            for elem in row:
                _m.append(elem)
        for _ in range(20):
            cmds.xform(fk_ctrls[0].name(), ws=True, matrix=_m)

        # transform.matchWorldTransform(fk_goals[1], upv_ctrl)
        # calculates new pole vector position
        if is_leg:
            start_end = (fk_goals[-1].getTranslation(space="world") - fk_goals[0].getTranslation(space="world"))
            start_mid = (fk_goals[1].getTranslation(space="world") - fk_goals[0].getTranslation(space="world"))
        else:
            start_end = (fk_goals[-1].getTranslation(space="world") - fk_goals[1].getTranslation(space="world"))
            start_mid = (fk_goals[2].getTranslation(space="world") - fk_goals[1].getTranslation(space="world"))

        dot_p = start_mid * start_end
        proj = float(dot_p) / float(start_end.length())
        proj_vector = start_end.normal() * proj
        arrow_vector = (start_mid - proj_vector) * 1.5
        arrow_vector *= start_end.normal().length()
        if is_leg:
            final_vector = (arrow_vector + fk_goals[1].getTranslation(space="world"))
        else:
            final_vector = (arrow_vector + fk_goals[2].getTranslation(space="world"))
        upv_ctrl.setTranslation(final_vector, space="world")

        # sets blend attribute new value
        # o_attr.set(1.0)
        roll_att = ui_node.attr(ikfk_attr.replace("blend", "roll"))
        roll_att.set(0.0)

        ik_ctrl.setMatrix(ik_mat, worldSpace=True)
        if ik_rot:
            ik_rot_node.setMatrix(rot_mat, worldSpace=True)
        # upv_ctrl.setMatrix(upv_mat, worldSpace=True)
        for _ in range(20):
            cmds.xform(fk_ctrls[0].name(), ws=True, matrix=_m)

    # sets keyframes
    if key:
        [cmds.setKeyframe("{}".format(elem),
                          time=(cmds.currentTime(query=True)))
         for elem in _all_controls]

    if is_leg:
        prefix = "_".join(ik.split("_")[0:2]).replace("leg", "foot")
        leg_tip_con = ["heel_ctl", "bk0_ctl", "tip_ctl", "roll_ctl"]

        for tip in leg_tip_con:
            node = _get_node("{}_{}".format(prefix, tip))
            if not node:
                continue
            attribute.reset_SRT([node, ])


class IkFkTransfer(anim_utils.AbstractAnimationTransfer):

    def __init__(self):
        # type: () -> None
        super(IkFkTransfer, self).__init__()
        self.getValue = self.getValueFromUI

    # ----------------------------------------------------------------

    def getChangeAttrName(self):
        # type: () -> str
        return "{}.{}".format(self.getHostName(), self.switchedAttrShortName)

    def getChangeRollAttrName(self):
        # type: () -> str
        return "{}.{}".format(
            self.getHostName(),
            self.switchedAttrShortName.replace("blend", "roll"))

    def changeAttrToBoundValue(self):
        # type: () -> None
        pm.setAttr(self.getChangeAttrName(), self.getValue())

    def getValueFromUI(self):
        # type: () -> float
        if self.comboBoxSpaces.currentIndex() == 0:
            # IK
            return 1.0
        else:
            # FK
            return 0.0

    def _getNode(self, name):
        # type: (str) -> pm.nodetypes.Transform
        node = anim_utils.getNode(":".join([self.nameSpace, name]))

        if not node:
            mgear.log("Can't find object : {0}".format(name), mgear.sev_error)

        return node

    def _getMth(self, name):
        # type: (Text) -> pm.nodetypes.Transform

        tmp = name.split("_")
        tmp[-1] = "mth"
        return self._getNode("_".join(tmp))

    def _get_node_mth(self, name):
        n = self._getNode(name)
        m = self._getMth(name)

        if not n:
            raise

        if not m:
            return n, n

        return n, m

    def setCtrls(self, fks, ik, upv, ikRot):
        # type: (list[str], str, str) -> None
        """gather core PyNode represented each controllers"""

        nm = [self._get_node_mth(x) for x in fks]
        self.fkCtrls = [x[0] for x in nm]
        self.fkTargets = [x[1] for x in nm]

        self.ikCtrl = self._getNode(ik)
        self.ikTarget = self._getMth(ik)

        self.upvCtrl = self._getNode(upv)
        self.upvTarget = self._getMth(upv)

        if ikRot:
            self.ikRotCtl = self._getNode(ikRot)
            self.ikRotTarget = self._getMth(ikRot)
            self.hasIkRot = True
        else:
            self.hasIkRot = False

    def setGroupBoxTitle(self):
        if hasattr(self, "groupBox"):
            # TODO: extract logic with naming convention
            part = "_".join(self.ikCtrl.name().split(":")[-1].split("_")[:-2])
            self.groupBox.setTitle(part)

    @deco.autokey_off
    def transfer(self,
                 startFrame,
                 endFrame,
                 onlyKeyframes,
                 ikRot,
                 switchTo=None,
                 *args,
                 **kargs):
        # type: (int, int, bool, str, *str, **str) -> None

        if switchTo is not None:
            if "fk" in switchTo.lower():
                to_fk = True

            else:
                to_fk = False

        else:
            if self.comboBoxSpaces.currentIndex() != 0:  # to FK
                to_fk = True

            else:  # to IK
                to_fk = False

            if to_fk:

                val_src_nodes = self.fkTargets
                key_src_nodes = [self.ikCtrl, self.upvCtrl]
                key_dst_nodes = self.fkCtrls
                if ikRot:
                    key_src_nodes.append(self.ikRotCtl)

            else:
                val_src_nodes = [self.ikTarget, self.upvTarget]
                key_src_nodes = self.fkCtrls
                key_dst_nodes = [self.ikCtrl, self.upvCtrl]
                if ikRot:
                    val_src_nodes.append(self.ikRotTarget)
                    key_dst_nodes.append(self.ikRotCtl)

                # reset roll channel:
                roll_att = self.getChangeRollAttrName()
                pm.cutKey(roll_att, time=(startFrame, endFrame), cl=True)
                pm.setAttr(roll_att, 0)

        self.bakeAnimation(self.getChangeAttrName(),
                           val_src_nodes,
                           key_src_nodes,
                           key_dst_nodes,
                           startFrame,
                           endFrame,
                           onlyKeyframes)

    @utils.one_undo
    @utils.viewport_off
    def bakeAnimation(self,
                      switch_attr_name,
                      val_src_nodes,
                      key_src_nodes,
                      key_dst_nodes,
                      startFrame,
                      endFrame,
                      onlyKeyframes=True):

        # Temporaly turn off cycle check to avoid misleading cycle message
        # on Maya 2016.  With Maya 2016.5 and 2017 the cycle warning doesn't
        # show up
        # if versions.current() <= 20180200:
        pm.cycleCheck(e=False)
        pm.displayWarning("Maya version older than: 2016.5: "
                          "CycleCheck temporal turn OFF")

        channels = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]

        if onlyKeyframes:
            keyframeList = sorted(set(pm.keyframe(key_src_nodes,
                                                  at=["t", "r", "s"],
                                                  q=True)))
        else:
            keyframeList = [x for x in range(startFrame, endFrame + 1)]

        worldMatrixList = self.getWorldMatrices(startFrame,
                                                endFrame,
                                                val_src_nodes,
                                                keyframeList)

        # delete animation in the space switch channel and destination ctrls
        pm.cutKey(key_dst_nodes, at=channels, time=(startFrame, endFrame))
        pm.cutKey(switch_attr_name, time=(startFrame, endFrame))

        def keyframe(x, i):
            pm.currentTime(x)

            # set the new space in the channel
            self.changeAttrToBoundValue()

            # bake the stored transforms to the cotrols
            for j, n in enumerate(key_dst_nodes):
                # n.setMatrix(worldMatrixList[i][j], worldSpace=True)

                _m = []
                for row in worldMatrixList[i][j]:
                    for elem in row:
                        _m.append(elem)
                for _ in range(2):
                    cmds.xform(n.name(), ws=True, matrix=_m)

            # bake the stored transforms to the cotrols
            for j, n in enumerate(key_dst_nodes):
                # n.setMatrix(worldMatrixList[i][j], worldSpace=True)

                _m = []
                for row in worldMatrixList[i][j]:
                    for elem in row:
                        _m.append(elem)
                for _ in range(2):
                    cmds.xform(n.name(), ws=True, matrix=_m)

            pm.setKeyframe(key_dst_nodes, at=channels)
            pm.setKeyframe(switch_attr_name)

        if onlyKeyframes:
            for i, x in enumerate(keyframeList):
                keyframe(x, i)

        else:
            for i, x in enumerate(range(startFrame, endFrame + 1)):
                keyframe(x, i)

        # if versions.current() <= 20180200:
        pm.cycleCheck(e=True)
        pm.displayWarning("CycleCheck turned back ON")

    # ----------------------------------------------------------------
    # re implement doItbyUI to have access to self.hasIKrot option
    def doItByUI(self):
        # type: () -> None

        # gather settings from UI
        startFrame = self.startFrame_value.value()
        endFrame = self.endFrame_value.value()
        onlyKeyframes = self.onlyKeyframes_check.isChecked()

        # main body
        self.transfer(startFrame, endFrame, onlyKeyframes, self.hasIkRot)

        # set the new space value in the synoptic combobox
        if self.comboObj is not None:
            self.comboObj.setCurrentIndex(self.comboBoxSpaces.currentIndex())

        for c in pyqt.maya_main_window().children():
            if isinstance(c, anim_utils.AbstractAnimationTransfer):
                c.deleteLater()
    # ----------------------------------------------------------------

    @staticmethod
    def showUI(model, ikfk_attr, uihost, fks, ik, upv, ikRot, *args):
        # type: (pm.nodetypes.Transform, str, str, List[str], str, str, *str) -> None

        try:
            for c in pyqt.maya_main_window().children():
                if isinstance(c, IkFkTransfer):
                    c.deleteLater()

        except RuntimeError:
            pass

        # Create minimal UI object
        ui = IkFkTransfer()
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(ikfk_attr)
        ui.setCtrls(fks, ik, upv, ikRot)
        ui.setComboObj(None)
        ui.setComboBoxItemsFormList(["IK", "FK"])

        # Delete the UI if errors occur to avoid causing winEvent
        # and event errors (in Maya 2014)
        try:
            ui.createUI(pyqt.maya_main_window())
            ui.show()

        except Exception as e:
            import traceback
            ui.deleteLater()
            traceback.print_exc()
            mgear.log(e, mgear.sev_error)

    @staticmethod
    def execute(model,
                ikfk_attr,
                uihost,
                fks,
                ik,
                upv,
                ikRot=None,
                startFrame=None,
                endFrame=None,
                onlyKeyframes=None,
                switchTo=None):
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
        ui.setCtrls(fks, ik, upv, ikRot)
        ui.setComboBoxItemsFormList(["IK", "FK"])
        ui.getValue = lambda: 0.0 if "fk" in switchTo.lower() else 1.0
        ui.transfer(startFrame, endFrame, onlyKeyframes, ikRot, switchTo="fk")

    @staticmethod
    def toIK(model, ikfk_attr, uihost, fks, ik, upv, ikRot, **kwargs):
        # type: (pm.nodetypes.Transform, str, str, List[str], str, str, **str) -> None

        kwargs.update({"switchTo": "ik"})
        IkFkTransfer.execute(model,
                             ikfk_attr,
                             uihost,
                             fks,
                             ik,
                             upv,
                             ikRot,
                             **kwargs)

    @staticmethod
    def toFK(model, ikfk_attr, uihost, fks, ik, upv, ikRot, **kwargs):
        # type: (pm.nodetypes.Transform, str, str, List[str], str, str, **str) -> None

        kwargs.update({"switchTo": "fk"})
        IkFkTransfer.execute(model, ikfk_attr, uihost, fks, ik, upv, ikRot, **kwargs)

    def getWorldMatrices(self, start, end, val_src_nodes, keyframes):
        # type: (int, int, List[pm.nodetypes.Transform]) -> \
        # List[List[pm.datatypes.Matrix]]
        """ returns matrice List[frame][controller number]."""

        res = []
        for x in keyframes:
            tmp = []
            pm.currentTime(x)
            for n in val_src_nodes:
                tmp.append(pm.getAttr(n + '.worldMatrix', time=x))

            res.append(tmp)

        return res


class toggleControllerVisibilityButton(QtWidgets.QPushButton):
    """Toggle Controllers visibility."""

    def __init__(self, *args, **kwargs):
        # type: (*str, **str) -> None
        super(toggleControllerVisibilityButton, self).__init__(*args, **kwargs)

    def mousePressEvent(self, event):
        # type: (QtCore.QEvent) -> None

        import ymt_synoptics.ymt_biped.logic as l

        mouse_button = event.button()
        model = syn_utils.getModel(self)

        obj = None
        try:
            obj = str(self.property("group_name")).split(",")
        except:
            obj = None

        l.hoge(model, mouse_button, obj)


if __name__ == "__main__":
    import ymt_synoptics.ymt_biped.control as c
    reload(c)  # NOQA
    print(c)
