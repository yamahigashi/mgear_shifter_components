# -*- coding: utf-8 -*-
import re
import math
import sys

from pymel.core import datatypes
from pymel import versions
import pymel.core as pm

import maya.cmds as cmds
import maya.api.OpenMaya as om

from Qt import QtWidgets

import mgear.synoptic as synoptic
from mgear.core import (
    attribute,
    primitive,
    icon,
    applyop,
    node,
)
from mgear.core.transform import (
    getTransform,
    getTransformLookingAt,
)
from mgear.core.primitive import addTransform


from ymt_shifter_utility import twistSplineBuilder as tsBuilder

from logging import (
    StreamHandler,  # noqa: F401
    getLogger,
    WARN,  # noqa: F401
    DEBUG,  # noqa: F401
    INFO,  # noqa: F401
)
logger = getLogger(__name__)
logger.setLevel(INFO)

if sys.version_info > (3, 0):
    unicode = str
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from typing import (
            Optional,  # noqa: F401
            Dict,  # noqa: F401
            List,  # noqa: F401
            Tuple,  # noqa: F401
            Pattern,  # noqa: F401
            Callable,  # noqa: F401
            Any,  # noqa: F401
            Text,  # noqa: F401
            Generator,  # noqa: F401
            Union  # noqa: F401
        )
        import mgear.shifter.component as component  # noqa: F401


##########################################################
def collect_synoptic_windows(parent=None):
    synoptics = []
    # active_window = None
    for w in QtWidgets.QApplication.topLevelWidgets():
        if not w.isVisible():
            continue
        if parent and w == parent:
            continue
        if not w.children():
            continue
        if w.isActiveWindow():
            # active_window = w
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
    # type: (pm.nt.transform, List[pm.nt.transform]|None) -> List[pm.nt.transform]
    if not routes:
        routes = []

    if not start.getParent():
        return routes + [start, ]

    return getFullPath(start.getParent(), routes + [start, ])


def getDecomposeMatrixOfAtoB(a, b):
    # type: (pm.PyNode, pm.PyNode) -> pm.nt.DecomposeMatrix
    """Returns matrix of A to B"""
    down, _, up = findPathAtoB(a, b)
    mul_node = pm.createNode("multMatrix")

    for i, d in enumerate(down):
        d.attr("matrix") >> mul_node.attr("matrixIn[{}]".format(i))

    for j, u in enumerate(up[:-1]):
        u.attr("inverseMatrix") >> mul_node.attr("matrixIn[{}]".format(i + j + 1))

    dm_node = node.createDecomposeMatrixNode(mul_node.attr("matrixSum"))
    return dm_node


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

    try:
        idx = bPath.index(sharedNode)
    except ValueError:
        idx = 0
        logger.warning("No shared node found in path {} and {}".format(aPath, bPath))
    up = list(reversed(bPath[:(idx)]))

    return down, sharedNode, up


def applyPathCnsLocal(target, curve, u):
    cns = applyop.pathCns(target, curve, cnsType=False, u=u, tangent=False)
    pm.connectAttr(curve.attr("local"), cns.attr("geometryPath"), f=True)  # tobe local space

    comp_node = pm.createNode("composeMatrix")
    cns.attr("allCoordinates") >> comp_node.attr("inputTranslate")
    cns.attr("rotate") >> comp_node.attr("inputRotate")
    cns.attr("rotateOrder") >> comp_node.attr("inputRotateOrder")

    mul_node = pm.createNode("multMatrix")
    comp_node.attr("outputMatrix") >> mul_node.attr("matrixIn[0]")
    curve.attr("matrix") >> mul_node.attr("matrixIn[1]")

    decomp_node = pm.createNode("decomposeMatrix")
    mul_node.attr("matrixSum") >> decomp_node.attr("inputMatrix")
    decomp_node.attr("outputTranslate") >> target.attr("translate")
    decomp_node.attr("outputRotate") >> target.attr("rotate")

    return cns


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


def transform_to_euler(t):
    # type: (om.MTransformationMatrix) -> Tuple[float, float, float]
    rot = t.rotate.asEulerRotation().asVector()
    rot = (math.degrees(rot[0]), math.degrees(rot[1]), math.degrees(rot[2]))

    return rot


# norm = self.guide.blades["blade"].y
# pfx = self.getName("twistSpline")
def convertToTwistSpline(comp, prefix, positions, crv, ikNb, norm, isClosed=False, is_cv_ctl=True, is_roll_ctl=True, is_otans_ctl=True, is_itans_ctl=True):

    crvShape = crv.getShape()
    curveFn = getAsMFnNode(crvShape.name(), om.MFnNurbsCurve)

    # Get the curve data
    knots = curveFn.knots()
    params = list(knots)[1::3]
    numCVs = len(params)
    numJoints = min(len(positions), numCVs + 2)  # head and tail

    # Build the spline
    # curveLen = curveFn.length()
    # maxParam = curveLen / 3.0
    max_param = (ikNb - 1) * 3.0 * 2.
    tempRet = build_twist_spline(prefix, ikNb, numJoints, max_param, spread=1.0, closed=isClosed)
    cvs, bfrs, oTans, iTans, jPars, joints, group, spline, master, riderCnst = tempRet

    alignControllers(cvs, bfrs, oTans, iTans, curveFn, ikNb, norm)
    alignDeformers(joints, positions, riderCnst, curveFn)

    # grouping
    twistspline_ctrls = pm.PyNode(bfrs[0]).getParent()
    cmds.setAttr("{}.visibility".format(group), False)

    comp.root.addChild(group)
    comp.root.addChild(spline)
    comp.root.addChild(twistspline_ctrls)
    comp.root.addChild(master)
    offset = cmds.xform(master, q=True, os=True, t=True)
    if not isinstance(offset, list):
        raise

    cmds.setAttr("{0}.tx".format(master), 0.0)
    cmds.setAttr("{0}.ty".format(master), 0.0)
    cmds.setAttr("{0}.tz".format(master), 0.0)
    cmds.setAttr("{0}.tx".format(group), 0.)
    cmds.setAttr("{0}.ty".format(group), 0.)
    cmds.setAttr("{0}.tz".format(group), 0.)

    cmds.setAttr("{0}.visibility".format(spline), False)
    cmds.setAttr("{0}.inheritsTransform".format(spline), False)

    # Lock the buffers
    attribute.setKeyableAttributes(pm.PyNode(spline), [])
    attribute.setKeyableAttributes(pm.PyNode(group), [])
    cmds.setAttr("{}.visibility".format(spline), lock=False)
    cmds.setAttr("{}.visibility".format(group), lock=False)
    # comp.root.addChild(riderCnst)

    for bfr in bfrs:
        cur = cmds.getAttr("{0}.t".format(bfr))[0]
        cmds.setAttr("{0}.tx".format(bfr), cur[0] + offset[0])
        cmds.setAttr("{0}.ty".format(bfr), cur[1] + offset[1])
        cmds.setAttr("{0}.tz".format(bfr), cur[2] + offset[2])
        for att in [x+y for x in "trs" for y in "xyz"]:
            cmds.setAttr("{0}.{1}".format(bfr, att), lock=True)

    scl = comp.length * (1. / comp.division) * 1.3
    col = comp.color_ik
    roll = [cv.replace("_ik", "_roll") for cv in cvs]

    edit_twistspline_ctl_of_shifter_attributes(comp, cvs, is_cv_ctl, False, comp.tr_params, scl, col)
    edit_twistspline_ctl_of_shifter_attributes(comp, roll, False, is_roll_ctl, ["rx"], scl, comp.color_fk)
    edit_twistspline_ctl_of_shifter_attributes(comp, oTans, False, is_otans_ctl, ["tx", "ty", "tz"], scl, col)
    edit_twistspline_ctl_of_shifter_attributes(comp, iTans, False, is_itans_ctl, ["tx", "ty", "tz"], scl, col)

    return cvs, oTans, iTans, joints, master, pm.PyNode(spline)


def edit_twistspline_ctl_of_shifter_attributes(comp, objects, is_primary_ctl, is_detail_ctl, ctl_params, scl, col):

    for x in objects:
        ctl = pm.PyNode(x)

        if is_primary_ctl or is_detail_ctl:
            setKeyableAttributesDontLockVisibility(ctl, ctl_params)
            edit_controller_shape(ctl.name(), scl=(scl, scl, scl), color=col)
            addCtlMetadata(comp, ctl)

            if is_primary_ctl:
                comp.addToSubGroup(ctl, comp.primaryControllersGroupName)

            if is_detail_ctl:
                comp.addToSubGroup(ctl, comp.detailControllersGroupName)

        else:
            attribute.setKeyableAttributes(ctl, [])
            edit_controller_shape(ctl.name(), scl=(0., 0., 0.), color=col)


def build_twist_spline(name, num_ik, num_joints, max_param, spread=1.0, closed=True):
    # type: (Text, int, int, float, float, bool) -> Tuple[List[Text], List[Text], List[Text], List[Text], List[Text], List[Text], Text, Text, Text, Text]
    """ Wrapper of tsBuilder.makeTwistSpline

    Arguments:
        pfx (str): The user name of the spline. Will be formatted into the given naming convention
        numCVs (int): The number of CV's to make that control the spline
        numJoints (int): The number of joints to make that ride the spline. Defaults to 10
        maxParam (int): The U-Value of the last CV. Defaults to 3*spread*(numCVs - 1)
        spread (float): The distance between each controller (including tangents). Defaults to 1
        closed (bool): Whether the spline forms a closed loop

    Returns:
        [str, ...]: All the CV's
        [str, ...]: All the CV's parent transforms
        [str, ...]: All the Out-Tangents
        [str, ...]: All the In-Tangents
        [str, ...]: All the joint parents
        [str, ...]: All the joints
        str: The joint organizer object (None if no joints requested)
        str: The spline object transform
        str: The base controller
        str: The rider constraint (None if no joints requested)
    """

    tempRet = tsBuilder.makeTwistSpline(
        name,
        num_ik,
        numJoints=num_joints,
        maxParam=max_param,
        spread=1.0,
        closed=closed
    )

    cvs, bfrs, oTans, iTans, jPars, joints, group, spline, master, riderCnst = tempRet
    return cvs, bfrs, oTans, iTans, jPars, joints, group, spline, master, riderCnst  # type: ignore


def alignControllers(cvs, bfrs, oTans, iTans, curveFn, ikNb, norm):
    # type: (List[Text], List[Text], List[Text], List[Text], om.MFnNurbsCurve, int, om.MVector) -> None

    curveLen = curveFn.length()

    def insertNpo(obj):
        # type: (Text) -> Text
        obj_node = pm.PyNode(obj)
        parent = obj_node.getParent()
        t = getTransform(obj_node)
        name = obj.replace("_ctl", "_npo")
        npo = addTransform(parent, name, t)
        pm.parent(obj_node, npo)
        attribute.setKeyableAttributes(npo, [])

        return npo

    # Set the positions
    for pos, cv in withCurvePos(curveFn, bfrs):
        cmds.xform(cv, ws=True, a=True, t=pos)

    for i, cv in enumerate(cvs):
        cmds.setAttr("{0}.Pin".format(cv), 1)

        npo = re.sub(r"_ik(\d+)_ctl", r"_twistPart_\1_npo", cv)
        roll = cv.replace("_ik", "_roll")
        if i == (len(cvs) - 1):
            cmds.setAttr("{0}.sz".format(npo), -1)
        cmds.setAttr("{0}.UseTwist".format(roll), 1)
        attribute.setKeyableAttributes(pm.PyNode(npo), [])
        insertNpo(cv)

    for pos, cv in withCurvePos(curveFn, oTans, 0.4):
        cmds.xform(cv, ws=True, a=True, t=pos)
        cmds.setAttr("{0}.Auto".format(cv), 0)

    for pos, cv in withCurvePos(curveFn, iTans, 0.6):
        cmds.xform(cv, ws=True, a=True, t=pos)
        cmds.setAttr("{0}.Auto".format(cv), 0)

    # Get the rotations at each CV point
    rotations = _getRotationsAtEachPoint(bfrs, norm)

    for i, ctrl in enumerate(bfrs):
        rot = rotations[i]
        cmds.setAttr("{0}.rotate".format(ctrl), *rot)

    # Un-pin everything but the first, so back to length preservation
    for cv in cvs[1:]:
        cmds.setAttr("{0}.Pin".format(cv), 0)

    # Re-set the tangent worldspace positions now that things have changed
    for pos, cv in withCurvePos(curveFn, oTans, 0.4):
        cmds.setAttr("{0}.tx".format(cv), curveLen / ikNb * 0.7)
        cmds.setAttr("{0}.ty".format(cv), 0.0)
        cmds.setAttr("{0}.tz".format(cv), 0.0)
        cmds.setAttr("{0}.Auto".format(cv), 0)
        insertNpo(cv)

    for pos, cv in withCurvePos(curveFn, iTans, 0.6):
        cmds.setAttr("{0}.tx".format(cv), curveLen / ikNb * -0.7)
        cmds.setAttr("{0}.ty".format(cv), 0.0)
        cmds.setAttr("{0}.tz".format(cv), 0.0)
        cmds.setAttr("{0}.Auto".format(cv), 0)
        insertNpo(cv)


def alignDeformers(joints, positions, riderCnst, curveFn):
    # type: (List, List, Text, om.MFnNurbsCurve) -> None
    # align deformer joints to the given positions

    curveLen = curveFn.length()
    max_param = curveLen * len(positions) / 33.3
    maximum_iteration = 10000

    joint = getAsMFnNode(joints[0], om.MFnTransform)
    _positions = []

    for param in [(max_param / maximum_iteration) * x for x in range(maximum_iteration)]:
        cmds.setAttr("{0}.params[0].param".format(riderCnst), param)
        cmds.dgeval(riderCnst)
        p = joint.translation(om.MSpace.kWorld)
        _positions.append(p)

    def _searchNearestParam(pos):

        res = _positions[0]
        cur = None
        pos = om.MVector(pos)

        for i, p in enumerate(_positions):
            d = (p - pos).length()
            if not cur or cur > d:
                cur = d
                res = p

        return max_param / maximum_iteration * _positions.index(res)

    cmds.setAttr("{0}.params[0].param".format(riderCnst), 0.0)
    for i, pos in enumerate(positions[1:]):
        i = i + 1  # skiped first
        param = _searchNearestParam(pos)
        cmds.setAttr("{0}.params[{1}].param".format(riderCnst, i), param)


def withCurvePos(curveFn, it, offset=0.):

    curveLen = curveFn.length()

    if len(it) == 1:
        param = curveFn.findParamFromLength(curveLen * offset)
        point = curveFn.getPointAtParam(param, om.MSpace.kObject)
        pos = point[0], point[1], point[2]

        yield pos, it[0]
        return 

    for i, element in enumerate(it):

        param = curveFn.findParamFromLength((curveLen / (len(it) - 1)) * (i + offset))
        point = curveFn.getPointAtParam(param, om.MSpace.kObject)
        pos = point[0], point[1], point[2]

        yield pos, element

    
def _getRotationsAtEachPoint(bfrs, norm):
    # type: (List[Text], om.MVector) -> List[Tuple[float, float, float]]
    # pylint: disable=too-many-locals

    rotations = []
    # norm = self.guide.blades["blade"].y
    for i, ctrl in enumerate(bfrs):

        c = pm.PyNode(ctrl).getTranslation(space="world")

        if i == 0:
            n = pm.PyNode(bfrs[1]).getTranslation(space="world")
            t = getTransformLookingAt(c, n, norm, axis="xy")
            rot = transform_to_euler(t)

        elif i == (len(bfrs) - 1):
            p = pm.PyNode(bfrs[i - 1]).getTranslation(space="world")
            t = getTransformLookingAt(c, p, norm, axis="-xy")
            rot = transform_to_euler(t)

        else:
            p = pm.PyNode(bfrs[i - 1]).getTranslation(space="world")
            n = pm.PyNode(bfrs[i + 1]).getTranslation(space="world")

            t1 = getTransformLookingAt(c, p, norm, axis="-xy")
            t2 = getTransformLookingAt(c, n, norm, axis="xy")

            q1 = om.MQuaternion(t1.rotate.x, t1.rotate.y, t1.rotate.z, t1.rotate.w)
            q2 = om.MQuaternion(t2.rotate.x, t2.rotate.y, t2.rotate.z, t2.rotate.w)
            q = om.MQuaternion.slerp(q1, q2, 0.5)

            rot = q.asEulerRotation().asVector()
            rot = (math.degrees(rot[0]), math.degrees(rot[1]), math.degrees(rot[2]))

        rotations.append(rot)

    return rotations


def iter_tr_xyz(object_name):
    for attr in ("t", "r"):
        for axis in ("x", "y", "z"):
            yield "{}.{}{}".format(object_name, attr, axis)


def add3DChain(parent, name, positions, normal, negate=False, vis=True):
    """Create a 2D joint chain. And then align given positions to the chain.

    Warning:
        This function will create un expected results if all the
        positions are not in the same 2D plane.

    Arguments:
        parent (dagNode): The parent for the chain.
        name (str): The node name.
        positions(list of vectors): the positons to define the chain.
        normal (vector): The normal vector to define the direction of
            the chain.
        negate (bool): If True will negate the direction of the chain

    Returns;
        list of dagNodes: The list containg all the joints of the chain

    >>> self.rollRef = pri.add2DChain(
        self.root,
        self.getName("rollChain"),
        self.guide.apos[:2],
        self.normal,
        self.negate)

    """

    joints = primitive.add2DChain(parent, name, positions, normal, negate, vis)
    jointNames = [x.longName() for x in joints]
    for i, joint in enumerate(jointNames[:-1]):
        nextPos  = positions[i + 1]
        dummy = cmds.spaceLocator(n="{}_dummy".format(joint))[0]
        cmds.xform(dummy, ws=True, t=nextPos)
        if parent is not None:
            cmds.aimConstraint(dummy, joint, aimVector=[1, 0, 0], upVector=[0, 0, 1], worldUpType="vector", worldUpObject=parent.longName(), worldUpVector=normal)
        else:
            cmds.aimConstraint(dummy, joint, aimVector=[1, 0, 0], upVector=[0, 0, 1], worldUpType="vector", worldUpVector=normal)
        cmds.delete(dummy)

    for joint in jointNames:
        cmds.makeIdentity(joint, apply=True, t=1, r=1, s=1, n=0, pn=1)

    return joints


def __has_make_nurbs_surface_hostory(surface_name):
    # type: (str) -> bool
    """Return True if the surface has makeNurbPlane history"""
    for history in cmds.listHistory(surface_name) or []:
        if cmds.nodeType(history) == "makeNurbPlane":
            return True

    return False


def serialize_nurbs_surface(surface_name):
    # type: (str) -> str
    """Serialize a NURBS surface to a string"""

    if not isinstance(surface_name, (str, unicode)):
        raise TypeError("surface_name must be a string")

    # if has make history, then freeze history
    if __has_make_nurbs_surface_hostory(surface_name):
        temp_surface = cmds.duplicate(surface_name, name="temp_surface")[0]
        cmds.delete(temp_surface, constructionHistory=True)
        surface_name = temp_surface
    else:
        temp_surface = None

    # Get the control vertices of the NURBS surface
    control_vertices_names = cmds.ls("{0}.cv[*][*]".format(surface_name), flatten=True)
    control_vertices = {}

    for path in control_vertices_names:
        cv = path.split(".")[-1]
        control_vertices[cv] = cmds.getAttr(path)[0]

    # Get other relevant attributes
    degreeU = cmds.getAttr("{0}.degreeU".format(surface_name))
    degreeV = cmds.getAttr("{0}.degreeV".format(surface_name))
    patchU = cmds.getAttr("{0}.spansU".format(surface_name))
    patchV = cmds.getAttr("{0}.spansV".format(surface_name))

    # Create a dictionary to hold the serialized data
    serialized_data = {
        "controlVertices": control_vertices,
        "degreeU": degreeU,
        "degreeV": degreeV,
        "patchU": patchU,
        "patchV": patchV,
        "localRotatePivot": cmds.xform(surface_name, q=True, os=True, rp=True),
        "localScalePivot": cmds.xform(surface_name, q=True, os=True, sp=True),
        "rotate": cmds.xform(surface_name, q=True, os=True, ro=True),
        "scale": cmds.xform(surface_name, q=True, os=True, s=True),
        "translate": cmds.xform(surface_name, q=True, os=True, t=True)
    }

    # Convert the dictionary to a string
    serialized_text = str(serialized_data)

    if temp_surface:
        cmds.delete(temp_surface)

    return serialized_text


def deserialize_nurbs_surface(surface_name, serialized_data):
    # type: (str, str) -> str
    """Deserialize a NURBS surface from a string"""

    if not isinstance(surface_name, (str, unicode)):
        raise TypeError("surface_name must be a string but got {0}".format(type(surface_name)))

    deserializedData = eval(serialized_data)

    # Retrieve the necessary information from the deserialized data
    control_vertices = deserializedData["controlVertices"]
    degreeU = deserializedData["degreeU"]
    degreeV = deserializedData["degreeV"]
    patchU = deserializedData["patchU"]
    patchV = deserializedData["patchV"]
    localRotatePivot = deserializedData["localRotatePivot"]
    localScalePivot = deserializedData["localScalePivot"]
    rotate = deserializedData["rotate"]
    scale = deserializedData["scale"]
    translate = deserializedData["translate"]

    # Create a new NURBS surface
    new_surface = cmds.nurbsPlane(
        n=surface_name,
        d=3,
        u=patchU,
        v=patchV,
        width=0,
        lengthRatio=0,
        constructionHistory=False)[0]  # type: str

    cmds.xform(new_surface, os=True, rp=localRotatePivot)
    cmds.xform(new_surface, os=True, sp=localScalePivot)
    cmds.xform(new_surface, os=True, ro=rotate)
    cmds.xform(new_surface, os=True, s=scale)
    cmds.xform(new_surface, os=True, t=translate)

    cmds.setAttr("{0}.degreeU".format(new_surface), degreeU)
    cmds.setAttr("{0}.degreeV".format(new_surface), degreeV)
    # Set the control point positions
    for cv, pos in control_vertices.items():
        posX, posY, posZ = pos
        cmds.setAttr("{0}.{1}".format(new_surface, cv), posX, posY, posZ, type="double3")

    return new_surface
