# -*- coding: utf-8 -*-
import sys
from pymel.core import datatypes
from pymel import versions
import pymel.core as pm
import maya.cmds as cmds
from Qt import QtWidgets

import mgear.shifter.component as component
import mgear.synoptic as synoptic

# from mgear.shifter import naming

from mgear.core import (
    transform,
    curve,
    applyop,
    attribute,
    icon,
    fcurve,
    vector,
    meshNavigation,
    node,
    primitive,
    utils,
)

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


def collect_synoptic_windows(parent=None):
    synoptics = []
    active_window = None
    for w in QtWidgets.QApplication.topLevelWidgets():
        if not w.isVisible():
            continue
        if parent and w == parent:
            continue
        if not w.children():
            continue
        if w.isActiveWindow():
            active_window = w
            continue

        if not isinstance(w, synoptic.Synoptic):
            continue

        if not w.windowTitle() and w.height() < 20:
            # workaround for Maya2019 outliner bug.
            continue

        synoptics.append(w)

    return synoptics


def show():
    wins = collect_synoptic_windows()
    for w in wins:
        w.showNormal()


def hide():
    wins = collect_synoptic_windows()
    for w in wins:
        w.showNormal()
        w.showMinimized()


def setKeyableAttributesDontLockVisibility(nodes, params=None):

    if not params:
        params = ["tx", "ty", "tz",
                  "ro", "rx", "ry", "rz",
                  "sx", "sy", "sz"]

    attribute.setKeyableAttributes(nodes, params)

    if not isinstance(nodes, list):
        nodes = [nodes]
        for n in nodes:
            n.setAttr("v", lock=False)


def getFullPath(start, routes=None):
    # type: (pm.nt.transform, List[pm.nt.transform]) -> List[pm.nt.transform]
    if not routes:
        routes = []

    if not start.getParent():
        return routes + [start, ]

    else:
        return getFullPath(start.getParent(), routes + [start, ])


def findPathAtoB(a, b):
    # type: (pm.nt.transform, pm.nt.transform) -> Tuple[List[pm.nt.transform], pm.nt.transform, List[pm.nt.transform]]
    """Returns route of A to B in formed Tuple[down(to root), turning point, up(to leaf)]"""
    # aPath = ["x", "a", "b", "c"]
    # bPath = ["b", "c"]
    # down [x, a]
    # turn b
    # up []

    aPath = getFullPath(a)
    bPath = getFullPath(b)

    return _findPathAtoB(aPath, bPath)


def _findPathAtoB(aPath, bPath):
    # type: (List, List) -> Tuple[List, Any, List]
    """Returns route of A to B in formed Tuple[down(to root), turning point, up(to leaf)]

    >>> aPath = ["x", "a", "b", "c"]
    >>> bPath = ["b", "c"]
    >>> d, c, u = _findPathAtoB(aPath, bPath)
    >>> d == ["x", "a"]
    True
    >>> c == "b"
    True
    >>> u == []
    True

    """
    down = []
    up = []
    sharedNode = None

    for u in aPath:
        if u in bPath:
            sharedNode = u
            break

        down.append(u)

    idx = bPath.index(sharedNode)
    up = list(reversed(bPath[:(idx)]))

    return down, sharedNode, up


def addCtlMetadata(self, ctl):
    # type: (component.Main, pm.datatypes.Transform) -> None

    name = ctl.name()

    attribute.addAttribute(ctl, "isCtl", "bool", keyable=False)
    attribute.addAttribute(ctl, "uiHost", "string", keyable=False)
    ctl.addAttr("uiHost_cnx", at='message', multi=False)
    # set the control Role for complex components. If the component is
    # of type control_01 or world_ctl the control role will default to None
    # since is only one control the role is not needed
    attribute.addAttribute(
        ctl, "ctl_role", "string", keyable=False, value=name)

    # mgear name. This keep track of the default shifter name. This naming
    # system ensure that each control has a unique id. Tools like mirror or
    # flip pose can use it to track symmetrical controls
    attribute.addAttribute(ctl,
                           "shifter_name",
                           "string",
                           keyable=False,
                           value=self.getName(name) + "_ctl")

    attribute.addAttribute(
        ctl, "side_label", "string", keyable=False, value=self.side)
    attribute.addAttribute(ctl,
                           "L_custom_side_label",
                           "string",
                           keyable=False,
                           value=self.options["side_left_name"])
    attribute.addAttribute(ctl,
                           "R_custom_side_label",
                           "string",
                           keyable=False,
                           value=self.options["side_right_name"])
    attribute.addAttribute(ctl,
                           "C_custom_side_label",
                           "string",
                           keyable=False,
                           value=self.options["side_center_name"])


def edit_controller_shape(name, pos=None, rot=None, scl=None, color=None):
    # type: (Text, Optional[Tuple[float, float, float]], Optional[Tuple[float, float, float]], Optional[Tuple[float, float, float]], Optional[int]) -> None
    """Change controller shape."""
    locator = cmds.ls(name, recursive=True) or None
    if not locator:
        return

    shapes = cmds.listRelatives(locator, shapes=True) or []

    if scl:
        if scl[0] == 0 and scl[1] == 0 and scl[1] == 0:
            cmds.delete(shapes)
            return

        for shape in shapes:
            cmds.xform("{}.cv[*]".format(shape), ws=False, relative=True, scale=scl)

    if rot:
        for shape in shapes:
            cmds.xform("{}.cv[*]".format(shape), ws=False, relative=True, rotation=rot)

    if pos:
        for shape in shapes:
            cmds.xform("{}.cv[*]".format(shape), ws=False, relative=True, translation=pos)

    if color:
        for shape in shapes:
            cmds.setAttr("{}.overrideEnabled".format(shape), True)
            cmds.setAttr("{}.overrideColor".format(shape), color)


def addJointCtl(self,
                parent,
                name,
                m,
                color,
                iconShape,
                tp=None,
                lp=True,
                mirrorConf=[0, 0, 0, 0, 0, 0, 0, 0, 0],
                guide_loc_ref=None,
                ** kwargs):
    """
    Create the control and apply the shape, if this is alrealdy stored
    in the guide controllers grp.

    Args:
        parent (dagNode): The control parent
        name (str): The control name.
        m (matrix): The transfromation matrix for the control.
        color (int or list of float): The color for the control in index or
            RGB.
        iconShape (str): The controls default shape.
        tp (dagNode): Tag Parent Control object to connect as a parent
            controller
        lp (bool): Lock the parent controller channels
        kwargs (variant): Other arguments for the iconShape type variations

    Returns:
        dagNode: The Control.

    """
    if "degree" not in kwargs.keys():
        kwargs["degree"] = 1

    # print name
    # fullName = self.getName(name)

    # remove the _ctl hardcoded in component name
    if name.endswith("_ctl"):
        name = name[:-4]
    # in some situation the name will be only ctl and should be removed
    # for example control_01
    if name.endswith("ctl"):
        name = name[:-3]

    # NOTE: this is a dirty workaround to keep backwards compatibility on
    # control_01 component where the description of the cotrol was just
    # the ctl suffix.
    rule = self.options["ctl_name_rule"]
    if not name:
        """
        if rule == naming.DEFAULT_NAMING_RULE:
            rule = r"{component}_{side}{index}_{extension}"
        else:
            # this ensure we always have name if the naming rule is custom
            name = "control"
        """
        rule = r"{component}_{side}{index}_{extension}"

    fullName = self.getName(
        name,
        rule=rule,
        ext="ctl",
        letter_case=self.options["ctl_description_letter_case"])

    bufferName = fullName + "_controlBuffer"
    if bufferName in self.rig.guide.controllers.keys():
        ctl_ref = self.rig.guide.controllers[bufferName]
    else:
        ctl_ref = icon.create(parent, fullName + "ref", m, color, iconShape, **kwargs)

    ctl = primitive.addJoint(parent, fullName, m)
    ctl.setAttr("drawStyle", 2)  # draw none
    for shape in ctl_ref.getShapes():
        ctl.addChild(shape, shape=True, add=True)
        pm.rename(shape, fullName + "Shape")

    pm.delete(ctl_ref)
    icon.setcolor(ctl, color)

    # add metadata attirbutes.
    attribute.addAttribute(ctl, "isCtl", "bool", keyable=False)
    attribute.addAttribute(ctl, "uiHost", "string", keyable=False)
    ctl.addAttr("uiHost_cnx", at='message', multi=False)
    # set the control Role for complex components. If the component is
    # of type control_01 or world_ctl the control role will default to None
    # since is only one control the role is not needed
    attribute.addAttribute(
        ctl, "ctl_role", "string", keyable=False, value=name)

    # locator reference for quick guide matching
    # TODO: this is a temporal implementation. We should store the full
    # guide data in future iterations
    if guide_loc_ref:
        attribute.addAttribute(ctl,
                               "guide_loc_ref",
                               "string",
                               keyable=False,
                               value=guide_loc_ref)

    # mgear name. This keep track of the default shifter name. This naming
    # system ensure that each control has a unique id. Tools like mirror or
    # flip pose can use it to track symmetrical controls
    attribute.addAttribute(ctl,
                           "shifter_name",
                           "string",
                           keyable=False,
                           value=self.getName(name) + "_ctl")
    attribute.addAttribute(
        ctl, "side_label", "string", keyable=False, value=self.side)
    attribute.addAttribute(ctl,
                           "L_custom_side_label",
                           "string",
                           keyable=False,
                           value=self.options["side_left_name"])
    attribute.addAttribute(ctl,
                           "R_custom_side_label",
                           "string",
                           keyable=False,
                           value=self.options["side_right_name"])
    attribute.addAttribute(ctl,
                           "C_custom_side_label",
                           "string",
                           keyable=False,
                           value=self.options["side_center_name"])

    # create the attributes to handlde mirror and symetrical pose
    attribute.add_mirror_config_channels(ctl, mirrorConf)

    if self.settings["ctlGrp"]:
        ctlGrp = self.settings["ctlGrp"]
        self.addToGroup(ctl, ctlGrp, "controllers")
    else:
        ctlGrp = "controllers"
        self.addToGroup(ctl, ctlGrp)

    # lock the control parent attributes if is not a control
    if parent not in self.groups[ctlGrp] and lp:
        self.transform2Lock.append(parent)

    # Set the control shapes isHistoricallyInteresting
    for oShape in ctl.getShapes():
        oShape.isHistoricallyInteresting.set(False)
        # connecting the always draw shapes on top to global attribute
        if versions.current() >= 20220000:
            pm.connectAttr(self.rig.ctlXRay_att,
                           oShape.attr("alwaysDrawOnTop"))

    # set controller tag
    if versions.current() >= 201650:
        try:
            oldTag = pm.PyNode(ctl.name() + "_tag")
            if not oldTag.controllerObject.connections():
                # NOTE:  The next line is comment out. Because this will
                # happend alot since core does't clean
                # controller tags after deleting the control Object of the
                # tag. This have been log to Autodesk.
                # If orphane tags are found, it will be clean in silence.
                # pm.displayWarning("Orphane Tag: %s  will be delete and
                # created new for: %s"%(oldTag.name(), ctl.name()))
                pm.delete(oldTag)

        except TypeError:
            pass

        self.add_controller_tag(ctl, tp)
    self.controlers.append(ctl)

    return ctl


def addJointTransform(parent, name, m=datatypes.Matrix()):
    """Create a transform dagNode.

    Arguments:
        parent (dagNode): The parent for the node.
        name (str): The Node name.
        m (matrix): The matrix for the node transformation (optional).

    Returns:
        dagNode: The newly created node.

    """
    # node = pm.PyNode(pm.createNode("transform", n=name))
    # node.setTransformation(m)
    node = primitive.addJoint(parent, name, m)
    node.setAttr("drawStyle", 2)  # draw none
    for shape in node.getShapes():
        pm.delete(shape)

    return node


def addJointTransformFromPos(parent, name, pos=datatypes.Vector(0, 0, 0)):
    """Create a transform dagNode.

    Arguments:
        parent (dagNode): The parent for the node.
        name (str): The Node name.
        pos (vector): The vector for the node position (optional).

    Returns:
        dagNode: The newly created node.

    """
    node = primitive.addJoint(parent, name)
    node.setAttr("drawStyle", 2)  # draw none
    for shape in node.getShapes():
        pm.delete(shape)
    node.setTranslation(pos, space="world")

    return node


def getAsMFnNode(name, ctor):
    objects = om.MSelectionList()
    objects.add(name)
    dag = objects.getDagPath(0)
    return ctor(dag)


def get_nearest_axis_orient(a, b):
    # returns normalized axis of orientation of a to b
    ta = getTransform(a)
    tb = getTransform(b)
    tb - ta


def transform_to_euler(t):
    # type: (om.MTransformationMatrix) -> Tuple[float, float, float]
    rot = t.rotate.asEulerRotation().asVector()
    rot = (math.degrees(rot[0]), math.degrees(rot[1]), math.degrees(rot[2]))

    return rot
