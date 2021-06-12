"""mGear shifter components"""
# pylint: disable=import-error,W0201,C0111,C0112

import maya.cmds as cmds
import maya.OpenMaya as om1
import maya.api.OpenMaya as om

import pymel.core as pm
from pymel.core import datatypes

import exprespy.cmd
from mgear.shifter import component
from mgear.rigbits.facial_rigger import helpers
from mgear.rigbits.facial_rigger import constraints
from mgear.rigbits import ghost

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

from mgear.core.transform import (
    getTransform,
    resetTransform,
    # getTransformLookingAt,
    # getChainTransform2,
    setMatrixPosition,
)

from mgear.core.primitive import (
    addTransform,
)
import ymt_shifter_utility as ymt_util

if False:  # pylint: disable=using-constant-test, wrong-import-order
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
    from pathlib import Path  # NOQA: F401, F811 pylint: disable=unused-import,reimported
    from types import ModuleType  # NOQA: F401 pylint: disable=unused-import
    from six.moves import reload_module as reload  # NOQA: F401 pylint: disable=unused-import

from logging import (  # noqa:F401 pylint: disable=unused-import, wrong-import-order
    StreamHandler,
    getLogger,
    WARN,
    DEBUG,
    INFO
)

handler = StreamHandler()
handler.setLevel(DEBUG)
logger = getLogger(__name__)
logger.setLevel(INFO)
logger.addHandler(handler)
logger.propagate = False


#############################################
# COMPONENT
#############################################
class Component(component.Main):
    """Shifter component Class"""

    # =====================================================
    # OBJECTS
    # =====================================================
    def addToSubGroup(self, obj, group_name):

        if self.settings["ctlGrp"]:
            ctlGrp = self.settings["ctlGrp"]
        else:
            ctlGrp = "controllers"

        self.addToGroup(obj, group_name, parentGrp=ctlGrp)

    def addObjects(self):
        """Add all the objects needed to create the component."""

        if self.settings["neutralRotation"]:
            t = transform.getTransformFromPos(self.guide.pos["root"])
        else:
            t = self.guide.tra["root"]
            if self.settings["mirrorBehaviour"] and self.negate:
                scl = [1, 1, -1]
            else:
                scl = [1, 1, 1]
            t = transform.setMatrixScale(t, scl)
        self.detailControllersGroupName = "controllers_detail"  # TODO: extract to settings
        self.primaryControllersGroupName = "controllers_primary"  # TODO: extract to settings

        self.ik_cns = primitive.addTransform(
            self.root, self.getName("ik_cns"), t)

        self.ctl = self.addCtl(self.ik_cns,
                               "ctl",
                               t,
                               self.color_ik,
                               self.settings["icon"],
                               w=self.settings["ctlSize"] * self.size,
                               h=self.settings["ctlSize"] * self.size,
                               d=self.settings["ctlSize"] * self.size,
                               tp=self.parentCtlTag)
        self.addToSubGroup(self.ctl, self.primaryControllersGroupName)

        t = self.guide.tra["lookat"]
        self.lookat = self.addCtl(self.ik_cns,
                                  "lookat_ctl",
                                  t,
                                  self.color_ik,
                                  self.settings["icon"],
                                  w=self.settings["ctlSize"] * self.size,
                                  h=self.settings["ctlSize"] * self.size,
                                  d=self.settings["ctlSize"] * self.size,
                                  tp=self.parentCtlTag)
        self.addToSubGroup(self.lookat, self.primaryControllersGroupName)

        # we need to set the rotation order before lock any rotation axis
        if self.settings["k_ro"]:
            rotOderList = ["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"]
            attribute.setRotOrder(
                self.ctl, rotOderList[self.settings["default_rotorder"]])

        params = [s for s in
                  ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"]
                  if self.settings["k_" + s]]
        ymt_util.setKeyableAttributesDontLockVisibility(self.ctl, params)

        if self.settings["joint"]:
            self.jnt_pos.append([self.ctl, 0, None, self.settings["uniScale"]])

        self.sliding_surface = pm.duplicate(self.guide.getObjects(self.guide.root)["sliding_surface"])[0]
        pm.parent(self.sliding_surface, self.root)
        self.sliding_surface.visibility.set(False)
        pm.makeIdentity(self.sliding_surface, apply=True, t=1,  r=1, s=1, n=0, pn=1)

    def addAttributes(self):
        # Ref
        if self.settings["ikrefarray"]:
            ref_names = self.get_valid_alias_list(
                self.settings["ikrefarray"].split(","))
            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam(
                    "ikref",
                    "Ik Ref",
                    0,
                    ref_names)

    def addOperators(self):
        return

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.ctl
        self.relatives["lookat"] = self.lookat
        self.controlRelatives["root"] = self.ctl
        if self.settings["joint"]:
            self.jointRelatives["root"] = 0

        self.aliasRelatives["root"] = "ctl"

    def addConnection(self):
        """Add more connection definition to the set"""
        self.connections["standard"] = self.connect_standard
        self.connections["orientation"] = self.connect_orientation

    def connect_standard(self):
        """standard connection definition for the component"""

        self.connect_standardWithSimpleIkRef()
        self.connect_slide_ghost()

    def connect_orientation(self):
        """Orient connection definition for the component"""
        self.connect_orientCns()

    def _visi_off_lock(self, node):
        """Short cuts."""

        return
        node.visibility.set(False)
        ymt_util.setKeyableAttributesDontLockVisibility(node, [])
        cmds.setAttr("{}.visibility".format(node.name()), l=False)

    def connect_slide_ghost(self):

        # slide system
        try:
            ghostSliderForPupil(
                self.lookat,
                self.ctl,
                self.sliding_surface,
                self.root)
        except:
            import traceback as tb
            tb.print_exc()
            raise


def ghostSliderForPupil(ctl, ghostCtl, surface, sliderParent):
    """Modify the ghost control behaviour to slide on top of a surface

    Args:
        ghostControls (dagNode): The ghost control
        surface (Surface): The NURBS surface
        sliderParent (dagNode): The parent for the slider.
    """

    def conn(ctl, driver, ghost):
        for attr in ["translate", "scale", "rotate"]:
            pm.connectAttr("{}.{}".format(ctl, attr), "{}.{}".format(driver, attr))
            # pm.disconnectAttr("{}.{}".format(ctl, attr), "{}.{}".format(ghost, attr))

    surfaceShape = surface.getShape()

    t = ctl.getMatrix(worldSpace=True)

    gDriver = primitive.addTransform(ghostCtl.getParent(), "{}_slideDriver".format(ctl.name()), t)
    # conn(ctl, gDriver, ghostCtl)
    print("ctl: {}, gDriver: {}, ghostCtl: {}".format(ctl, gDriver, ghostCtl))

    oParent = ghostCtl.getParent()
    npoName = "_".join(ghostCtl.name().split("_")[:-1]) + "_npo"
    oTra = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))
    oTra.setTransformation(ghostCtl.getMatrix())
    pm.parent(ghostCtl, oTra)

    slider = primitive.addTransform(sliderParent, ctl.name() + "_slideDriven", t)

    down, _, up = findPathAtoB(ctl, sliderParent)
    mul_node = pm.createNode("multMatrix")
    j = k = 0
    for j, d in enumerate(down):
        d.attr("matrix") >> mul_node.attr("matrixIn[{}]".format(j))
    for k, u in enumerate(up):
        u.attr("inverseMatrix") >> mul_node.attr("matrixIn[{}]".format(k + j))

    dm_node = node.createDecomposeMatrixNode(mul_node.attr("matrixSum"))

    cps_node = pm.createNode("closestPointOnSurface")
    dm_node.attr("outputTranslate") >> cps_node.attr("inPosition")
    surfaceShape.attr("local") >> cps_node.attr("inputSurface")
    cps_node.attr("position") >> slider.attr("translate")

    pm.normalConstraint(surfaceShape,
                        slider,
                        aimVector=[0, 0, 1],
                        upVector=[0, 1, 0],
                        worldUpType="objectrotation",
                        worldUpVector=[0, 1, 0],
                        worldUpObject=gDriver)

    pm.parent(ghostCtl.getParent(), slider)


def getFullPath(start, routes=None):
    # type: (pm.nt.transform, List[pm.nt.transform]) -> List[pm.nt.transform]
    if not routes:
        routes = []

    if not start.getParent():
        return routes

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
