# import re

import maya.cmds as cmds
import pymel.core as pm

import mgear
from mgear.vendor.Qt import QtCore, QtWidgets
from mgear.core import attribute
import mgear.core.anim_utils as anim_utils
import mgear.synoptic.utils as syn_utils
import mgear.core.utils as utils
# import gml_maya.decorator as deco


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
        self.numFkControllers = None

    def searchNumberOfFkControllers(self):
        # type: () -> None

        for i in range(self.MAXIMUM_TRY_FOR_SEARCHING_FK):
            prop = self.property("fk{0}".format(str(i)))
            if not prop:
                self.numFkControllers = i
                break

    def mousePressEvent(self, event):
        # type: (QtCore.QEvent) -> None

        mouse_button = event.button()

        model = syn_utils.getModel(self)
        ikfk_attr = str(self.property("ikfk_attr"))
        uiHost_name = str(self.property("uiHost_name"))

        if not self.numFkControllers:
            self.searchNumberOfFkControllers()

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
            syn_utils.IkFkTransfer.showUI(
                model, ikfk_attr, uiHost_name, fks, ik, upv, ikRot)
            return

        else:
            current_namespace = anim_utils.getNamespace(model)
            ikFkMatch(current_namespace, ikfk_attr, uiHost_name, fks, ik, upv, ikRot)
            return


@utils.one_undo
def mirrorPose(flip=False, nodes=None):
    """Summary

    Args:
        flip (bool, optiona): Set the function behaviout to flip
        nodes (None,  [PyNode]): Controls to mirro/flip the pose
    """
    if nodes is None:
        nodes = pm.selected()

    nameSpace = False
    if nodes:
        nameSpace = syn_utils.getNamespace(nodes[0])

    mirrorEntries = []
    for oSel in nodes:
        mirrorEntries.extend(gatherMirrorData(nameSpace, oSel, flip))

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
    # type: (pm.PyNode, pm.PyNode, bool) -> List[MirrorEntry]
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
    """Get the invert check butto attribute name

    Args:
        str (str): The attribute name

    Returns:
        str: The checked attribute name
    """
    # type: (Text) -> Text
    return "invPivot{0}".format(str.lower().capitalize())


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
            attribute.reset_SRT([node, ])
