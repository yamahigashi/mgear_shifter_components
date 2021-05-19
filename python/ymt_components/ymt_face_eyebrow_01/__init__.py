"""mGear shifter components"""
# pylint: disable=import-error,W0201,C0111,C0112
import re
import inspect
import textwrap
import math

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


##########################################################
# COMPONENT
##########################################################
class Component(component.Main):
    """Shifter component Class"""

    # =====================================================
    # OBJECTS
    # =====================================================
    def addObjects(self):
        """Add all the objects needed to create the component."""

        self.normal = self.guide.blades["blade"].z * -1.
        self.binormal = self.guide.blades["blade"].x

        self.WIP = self.options["mode"]

        if self.negate and self.settings["overrideNegate"]:
            self.negate = False
            self.n_factor = 1

        if self.settings["overrideNegate"]:
            self.mirror_conf = [0, 0, 1,
                                1, 1, 0,
                                0, 0, 0]
        else:
            self.mirror_conf = [0, 0, 0,
                                0, 0, 0,
                                0, 0, 0]

        self.connect_surface_slider = self.settings["isSlidingSurface"]

        # -------------------------------------------------------
        self.ctlName = "ctl"

        self.FRONT_OFFSET = .02
        self.NB_ROPE = 15
        self.midDivisions = 3
        self.secDivisions = 3
        self.secondary_ctl_check = True
        self.secCtlColor = 13

        self.rigCurves = []
        self.mainCtlCurves = []
        self.mainCtlUpvs = []
        self.secondaryCurves = []
        self.mainRopes = []
        self.mainRopeUpvs = []
        self.mainCurveUpvs = []
        self.mainCurves = []

        # collect objects
        self.mainControls = []
        self.mainUpvs = []
        self.secondaryControls = []

        # --------------------------------------------------------------------
        self.num_uplocs = self.getNumberOfLocators("_uploc")

        self.inPos = self.guide.apos[2]
        self.outPos = self.guide.apos[-4]
        self.upPos = self.guide.apos[-3]
        self.lowPos = self.guide.apos[-2]
        self.frontPos = self.guide.apos[-1]
        self.rootPos = self.guide.apos[0]

        self.uplocsPos = self.guide.apos[2:self.num_uplocs + 2]

        self.offset = (self.frontPos - self.rootPos) * 0.3
        if self.negate:
            pass
            # self.offset[2] = self.offset[2] * -1.0

        # --------------------------------------------------------------------
        self.addContainers()
        self.addCurve()
        self.addRope()
        self.reparentControls()
        self.attachSecondaryControlsToMainCurve()
        self.connectWires()

        self.sliding_surface = pm.duplicate(self.guide.getObjects(self.guide.root)["sliding_surface"])[0]
        pm.parent(self.sliding_surface, self.root)
        self.sliding_surface.visibility.set(False)
        pm.makeIdentity(self.sliding_surface, apply=True, t=1,  r=1, s=1, n=0, pn=1)

        # self.addControllers()
        # self.addConstraints()
        # for crv in self.mainCurves:
        #     pm.delete(crv)

    def _visi_off_lock(self, node):
        """Short cuts."""
        node.visibility.set(False)
        attribute.setKeyableAttributes(node, [])
        cmds.setAttr("{}.visibility".format(node.name()), l=False)

    def addContainers(self):

        t = getTransform(self.root)

        self.crv_root = addTransform(self.root, self.getName("crvs"), t)
        self.rope_root = addTransform(self.root, self.getName("ropes"), t)
        self.browsHooks_root = addTransform(self.root, self.getName("hooks"), t)

        self._visi_off_lock(self.crv_root)
        self._visi_off_lock(self.rope_root)
        self._visi_off_lock(self.browsHooks_root)

        if self.connect_surface_slider:
            self.slider_root = addTransform(self.root, self.getName("sliders"), t)
            attribute.setKeyableAttributes(self.slider_root, [])

        # self.mainControlParentGrp = addTransform(self.root, self.getName("mainControls"), t)
        w = (self.outPos - self.inPos).length()
        d = (self.upPos - self.lowPos).length()
        self.mainControlParentGrp = self.addCtl( self.root, "mainControls", t, self.color_ik, "square", w=w, d=d, ro=datatypes.Vector(1.57079633, 0, 0), po=datatypes.Vector(0, 0, 1.0))
        self.secondaryControlsParentGrp = addTransform(self.root, self.getName("secondaryControls"), t)

    def getNumberOfLocators(self, query):
        # type: (Text) -> int
        num = 0
        for k, v in self.guide.tra.items():
            if query in k:
                index = int(re.search(r"^(\d+)", k).group(1))
                num = max(num, index + 1)

        return num

    def addDummyPlane(self):
        # type: () -> om.MFnMesh

        return draw_eye_guide_mesh_plane(self.uplocsPos, self.root)
        # return mgear_util.draw_eye_guide_mesh_plane(joint_points)

    def addCurve(self):

        plane = self.addDummyPlane()

        self.addCurves(self.crv_root, plane)
        # pm.delete(pm.PyNode(plane.name()))

    def addCurves(self, crv_root, plane):

        t = getTransform(self.root)
        gen = curve.createCurveFromOrderedEdges
        planeNode = pm.PyNode(plane.fullPathName())

        # -------------------------------------------------------------------
        edgeList = ["{}.e[{}]".format(plane.fullPathName(), 0)]
        for i in range(1, self.num_uplocs + 1):
            edgeList.append("{}.e[{}]".format(plane.fullPathName(), i * 2 + 1))
        edgeList = [pm.PyNode(x) for x in edgeList]

        name = "main_crv"
        crv = gen(edgeList, planeNode.verts[1], self.getName("{}Crv".format(name)), parent=crv_root, m=t)
        crv.attr("visibility").set(False)
        attribute.setKeyableAttributes(crv, [])

        mainCtrlPos = helpers.divideSegment(crv, self.midDivisions)
        secCtrlPos = self.uplocsPos

        self.mainCurve = crv
        self.mainCurves.append(crv)

        # -------------------------------------------------------------------
        mainCtrlOptions = []
        secCtrlOptions = []

        iterator = enumerate(mainCtrlPos)
        for i, ctlPos in iterator:
            isLast = (i == (len(mainCtrlPos) - 1))
            mainCtrlOptions.extend(self._foreachMainCtrlPos(i, ctlPos, isLast))

        if self.secondary_ctl_check:
            sec_number_index = len(secCtrlPos) - 1
            controlType = "circle"

            iterator = enumerate(secCtrlPos)
            for i, ctlPos in iterator:
                secCtrlOptions.append(self._foreachSecCtrlPos(i, ctlPos, sec_number_index))

        # mainCtrl = self.addCtl(self.root, )
        self.mainControls = []
        self.mainUpvs = []
        for ctlOptions in mainCtrlOptions:
            ctl, upv = self._foreachControlOption(self.mainControlParentGrp, ctlOptions)
            self.mainControls.append(ctl)
            self.mainUpvs.append(upv)
        self.addMainCnsCurve(self.mainControls)

        self.secondaryControls = []
        self.secUpvs = []
        for ctlOptions in secCtrlOptions:
            ctl, upv = self._foreachControlOption(self.secondaryControlsParentGrp, ctlOptions)
            self.secondaryControls.append(ctl)
            self.secUpvs.append(upv)
        self.addSecondaryCnsCurve(self.secondaryControls)

    def _foreachControlOption(self, controlParentGrp, ctlOptions):

        oName = ctlOptions[0]
        oSide = ctlOptions[1]
        o_icon = ctlOptions[2]
        color = ctlOptions[3]
        wd = ctlOptions[4]
        oPar = ctlOptions[5]
        point = ctlOptions[6]

        position = transform.getTransformFromPos(point)
        npo = addTransform(controlParentGrp, self.getName("%s_npo" % oName, oSide), position)
        npoBuffer = addTransform(npo, self.getName("%s_bufferNpo" % oName, oSide), position)

        # Create casual control
        if o_icon is not "npo":
            if o_icon == "sphere":
                rot_offset = None
            else:
                rot_offset = datatypes.Vector(1.57079633, 0, 0)

            ctl = self.addCtl(
                npoBuffer,
                "{}_ctl".format(oName),
                position,
                color,
                o_icon,
                w=wd,
                d=wd,
                ro=rot_offset,
                po=datatypes.Vector(0, 0, 0),
            )

        # Create buffer node instead
        else:
            ctl = addTransform(
                npoBuffer,
                self.getName("%s_HookNpo" % oName, oSide),
                position)

        # Create up vectors for each control
        upv = addTransform(ctl, self.getName("%s_upv" % oName, oSide), position)
        upv.attr("tz").set(self.FRONT_OFFSET)

        return ctl, upv

    def addMainCnsCurve(self, ctls):
        crv_degree = 2

        crv = helpers.addCnsCurve(self.crv_root, self.getName("mainCtl_crv"), ctls, crv_degree)
        attribute.setKeyableAttributes(crv[0], [])
        v = self.root.getTranslation(space="world")
        crv[0].setTranslation(v, om.MSpace.kWorld)
        self.mainCtlCurves.append(crv[0])

        # create upvector curve to drive secondary control
        if self.secondary_ctl_check:
            mainCtlUpv = helpers.addCurve(self.crv_root, self.getName("mainCtl_upv"), ctls, crv_degree)
            attribute.setKeyableAttributes(mainCtlUpv, [])
            v = self.root.getTranslation(space="world")
            mainCtlUpv.setTranslation(v, om.MSpace.kWorld)
            # connect upv curve to mainCrv_ctl driver node.
            pm.connectAttr(crv[1].attr("outputGeometry[0]"), mainCtlUpv.getShape().attr("create"))

            # offset upv curve
            cvs = mainCtlUpv.getCVs(space="world")
            for i, cv in enumerate(cvs):
                offset = [cv[0], cv[1], cv[2] + self.FRONT_OFFSET]
                mainCtlUpv.setCV(i, offset, space='world')
            # collect mainCrv upv
            self.mainCtlUpvs.append(mainCtlUpv)

    def addRope(self):
        v = self.root.getTranslation(space="world")

        mainRope = curve.createCurveFromCurve(self.mainCurve, self.getName("mainRope"), nbPoints=self.NB_ROPE, parent=self.rope_root)
        # mainRope.setTranslation(v, om.MSpace.kWorld)
        self.rigCurves.append(mainRope)
        self.mainRopes.append(mainRope)

        mainRope_upv = curve.createCurveFromCurve(self.mainCurve, self.getName("mainRope_upv"), nbPoints=self.NB_ROPE, parent=self.rope_root)
        # mainRope_upv.setTranslation(v, om.MSpace.kWorld)
        self.rigCurves.append(mainRope_upv)
        self.mainRopeUpvs.append(mainRope_upv)

        mainCrv_upv = curve.createCurveFromCurve(self.mainCurve, self.getName("mainCrv_upv"), nbPoints=7, parent=self.rope_root)
        # mainCrv_upv.setTranslation(v, om.MSpace.kWorld)
        self.rigCurves.append(mainCrv_upv)
        self.mainCurveUpvs.append(mainCrv_upv)

        for crv in [mainRope_upv, mainCrv_upv]:
            cvs = crv.getCVs(space="world")
            for i, cv in enumerate(cvs):
                # we populate the closest vertext list here to skipt the first
                # and latest point
                offset = [cv[0], cv[1], cv[2] + self.FRONT_OFFSET]
                crv.setCV(i, offset, space='world')

    def addSecondaryCnsCurve(self, ctls):
        crv_degree = 2

        crv = helpers.addCnsCurve(self.crv_root, self.getName("secCtl_crv"), ctls, crv_degree)
        attribute.setKeyableAttributes(crv[0], [])
        v = self.root.getTranslation(space="world")
        crv[0].setTranslation(v, om.MSpace.kWorld)

        self.secondaryCurves.append(crv[0])
        self.rigCurves.append(crv[0])

    def _foreachSecCtrlPos(self, i, ctlPos, sec_number_index):

        i_name = i

        controlType = "sphere"
        posPrefix = "sec_" + str(i_name).zfill(2)
        options = [posPrefix, self.side, controlType, self.secCtlColor, 0.55, [], ctlPos]

        return options

    def _foreachMainCtrlPos(self, i, ctlPos, isLast):

        options = []

        if i == 0:
            posPrefix = "in"
            if self.side == "C":
                posPrefix = "out_R"

        elif isLast:
            posPrefix = "out"
            if self.side == "C":
                posPrefix = "out_L"

        else:
            posPrefix = "mid_0" + str(i)

        controlType = "square"
        tControlType = ["circle", controlType]
        tControlSize = [0.8, 1.0]
        tPrefix = [posPrefix + "_tangent", posPrefix]

        if i == 0:
            options.append([tPrefix[1], self.side, tControlType[1], self.color_ik, tControlSize[1], [], ctlPos])
            options.append([tPrefix[0], self.side, tControlType[0], self.color_fk, tControlSize[0], [], ctlPos])

        elif isLast:
            options.append([tPrefix[0], self.side, tControlType[0], self.color_fk, tControlSize[0], [], ctlPos])
            options.append([tPrefix[1], self.side, tControlType[1], self.color_ik, tControlSize[1], [], ctlPos])

        else:
            options.append([posPrefix, self.side, "circle", self.color_ik, 1.0, [], ctlPos])

        return options

    def reparentControls(self):
        pm.parent(self.mainControls[1].getParent(2), self.mainControls[0])
        pm.parent(self.mainControls[-2].getParent(2), self.mainControls[-1])

        return

        # TODO: fix later
        for ctl in self.mainControls:
            if "_tangent" not in ctl.name():
                pm.parent(ctl.getParent(2), self.root)

        # controls tags
        # node.add_controller_tag(ctl, tagParent=tag_parent)

    def attachSecondaryControlsToMainCurve(self):

        secControlsMerged = []
        tempMainCtlCurves = self.mainCtlCurves
        tempMainUpvCurves = self.mainCtlUpvs
        secControlsMerged.append(self.secondaryControls)

        for secCtl in self.secondaryControls:
            constraints.matrixConstraint(self.root, secCtl.getParent(2), 'rs', True)

            # controls tags
            # node.add_controller_tag(secCtl, tagParent=parent_tag_L)

        # create hooks on the main ctl curve
        for j, crv in enumerate(self.secondaryCurves):

            lvlType = 'transform'
            cvs = crv.getCVs(space="object")

            for i, cv in enumerate(cvs):

                oTransUpV = pm.PyNode(pm.createNode(lvlType, n=self.getName("secNpoUpv", str(i).zfill(3)), p=self.browsHooks_root, ss=True))
                oTrans = pm.PyNode(pm.createNode(lvlType, n=self.getName("secNpo", str(i).zfill(3)), p=self.browsHooks_root, ss=True))

                oParam, oLength = curve.getCurveParamAtPosition(crv, cv)
                uLength = curve.findLenghtFromParam(crv, oParam)
                u = uLength / oLength

                # create motion paths transforms on main ctl curves
                cns = applyPathCnsLocal(oTransUpV, tempMainUpvCurves[j], u)
                cns = applyPathCnsLocal(oTrans, tempMainCtlCurves[j], u)

                pm.connectAttr(oTransUpV.attr("worldMatrix[0]"),
                               cns.attr("worldUpMatrix"))

                # connect secondary control to oTrans hook.
                constraints.matrixConstraint(
                    oTrans,
                    secControlsMerged[j][i].getParent(2),
                    't',
                    True)

    def connectWires(self):
        # set drivers
        def wire(s, d):
            wire = pm.wire(s, w=d, dropoffDistance=[0, 1000])
            # pm.connectAttr(s.attr("local"),       wire[0].attr("baseWire[0]"),     f=True)  # tobe local space
            # pm.connectAttr(d.attr("local"), wire[0].attr("deformedWire[0]"), f=True)  # tobe local space

        crvDrivers = []
        if self.secondary_ctl_check is True:
            crvDrivers = self.secondaryCurves

        else:
            crvDrivers = self.mainCtlCurves

        for i, drv in enumerate(crvDrivers):
            wire(self.mainCurves[i],    drv)
            wire(self.mainCurveUpvs[i], drv)
            wire(self.mainRopes[i],     drv)
            wire(self.mainRopeUpvs[i],  drv)

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        # if not self.settings["ui_host"]:
        #     self.uihost = self.over_ctl

        return

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        pass

    # =====================================================
    # CONNECTOR
    # =====================================================
    def addConnection(self):
        pass

    def connect_standard(self):

        self.parent.addChild(self.root)

        if self.connect_surface_slider:
            try:
                self.connect_slide_ghost()

            except Exception as _:
                import traceback
                traceback.print_exc()

        if self.settings["addJoints"]:
            for i, ctl in enumerate(self.secondaryControls):
                self.jnt_pos.append([ctl, str(i).zfill(2)])

    def connect_ghosts(self):

        lipup_ref = self.parent_comp.lipup_ctl
        liplow_ref = self.parent_comp.liplow_ctl

        slide_c_ref = self.rig.findRelative("mouthSlide_C0_root")
        corner_l_ref = self.rig.findRelative("mouthCorner_L0_root")
        corner_r_ref = self.rig.findRelative("mouthCorner_R0_root")

        self.connect_slide_ghost(lipup_ref, liplow_ref, slide_c_ref, corner_l_ref, corner_r_ref)
        self.connect_mouth_ghost(lipup_ref, liplow_ref, slide_c_ref, corner_l_ref, corner_r_ref)

    def connect_slide_ghost(self):

        # create ghost controls
        ghosts = []
        for sec in self.secondaryControls:
            ghostCtl = ghost.createGhostCtl(sec, self.slider_root)
            ghosts.append(ghostCtl)
            ghostCtl.attr("isCtl").set(True)
            self._visi_off_lock(sec)
        self._visi_off_lock(self.secondaryControlsParentGrp)

        # slide system
        ghostSliderForEyeBrow(
            ghosts,
            self.sliding_surface,
            self.slider_root)

        self.secondaryControls = ghosts

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.root
        self.controlRelatives["root"] = self.root
        self.aliasRelatives["root"] = "ctl"


def draw_eye_guide_mesh_plane(points, t):
    # type: (Tuple[float, float, float], datatypes.MMatrix) -> om.MFnMesh

    mesh = om.MFnMesh()

    points = [x - t.getTranslation(space="world") for x in points]
    # points = [x - t.getTranslation(space="world") for x in points]

    mean_x = sum(p[0] for p in points) / len(points)
    mean_y = sum(p[1] for p in points) / len(points)
    mean_z = sum(p[2] for p in points) / len(points)
    mean = (mean_x, mean_y, mean_z)

    # Simple unitCube coordinates
    vertices = [om.MPoint(mean), ]
    polygonCounts = []
    polygonConnects = []

    for i, p in enumerate(points):
        vertices.append(om.MPoint(p))    # 0

        if 1 < i:
            polygonCounts.append(3)
            polygonConnects.append(i)
            polygonConnects.append(i - 1)
            polygonConnects.append(0)

        if len(points) == (i + 1):
            polygonCounts.append(3)
            polygonConnects.append(i + 1)
            polygonConnects.append(i)
            polygonConnects.append(0)

            polygonCounts.append(3)
            polygonConnects.append(1)
            polygonConnects.append(i + 1)
            polygonConnects.append(0)

    mesh_obj = mesh.create(vertices, polygonCounts, polygonConnects)
    return mesh

    mesh_trans = om.MFnTransform(mesh_obj)
    n = pm.PyNode(mesh_trans.name())
    v = t.getTranslation(space="world")
    n.setTranslation(v, om.MSpace.kWorld)

    return mesh


def ghostSliderForEyeBrow(ghostControls, surface, sliderParent):
    """Modify the ghost control behaviour to slide on top of a surface

    Args:
        ghostControls (dagNode): The ghost control
        surface (Surface): The NURBS surface
        sliderParent (dagNode): The parent for the slider.
    """

    if not isinstance(ghostControls, list):
        ghostControls = [ghostControls]

    def conn(ctl, driver, ghost):
        for attr in ["translate", "scale", "rotate"]:
            pm.connectAttr("{}.{}".format(ctl, attr), "{}.{}".format(driver, attr))
            # pm.disconnectAttr("{}.{}".format(ctl, attr), "{}.{}".format(ghost, attr))

    surfaceShape = surface.getShape()
    sliders = []

    for i, ctlGhost in enumerate(ghostControls):
        ctl = pm.listConnections(ctlGhost, t="transform")[-1]
        t = ctl.getMatrix(worldSpace=True)

        gDriver = primitive.addTransform(ctlGhost.getParent(), "{}_slideDriver".format(ctl.name()), t)
        # conn(ctl, gDriver, ctlGhost)
        print("ctl: {}, gDriver: {}, ctlGhost: {}".format(ctl, gDriver, ctlGhost))

        oParent = ctlGhost.getParent()
        npoName = "_".join(ctlGhost.name().split("_")[:-1]) + "_npo"
        oTra = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))
        oTra.setTransformation(ctlGhost.getMatrix())
        pm.parent(ctlGhost, oTra)

        slider = primitive.addTransform(sliderParent, ctl.name() + "_slideDriven", t)
        sliders.append(slider)

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

        pm.parent(ctlGhost.getParent(), slider)


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
