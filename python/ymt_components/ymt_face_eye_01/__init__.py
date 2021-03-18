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

        # -------------------------------------------------------

        self.num_uplocs = self.getNumberOfLocators("_uploc")
        self.num_lowlocs = self.getNumberOfLocators("_lowloc")

        self.inPos = self.guide.apos[-5]
        self.outPos = self.guide.apos[-4]
        self.upPos = self.guide.apos[-3]
        self.lowPos = self.guide.apos[-2]
        self.frontPos = self.guide.apos[-1]
        self.rootPos = self.guide.apos[0]

        self.uplocsPos = self.guide.apos[2:self.num_uplocs + 2]
        self.lowlocsPos = self.guide.apos[2 + self.num_uplocs:-5]

        self.offset = (self.frontPos - self.rootPos) * 0.3
        if self.negate:
            pass
            # self.offset[2] = self.offset[2] * -1.0

        # -------------------------------------------------------
        self.ctlName = "ctl"
        self.blinkH = 0.2
        self.upperVTrack = 0.04
        self.upperHTrack = 0.01
        self.lowerVTrack = 0.02
        self.lowerHTrack = 0.01

        # --------------------------------------------------------
        self.ik_ctl = []
        self.ik_npo = []
        self.ik_roll_npo = []
        self.ik_global_in = []
        self.ik_local_in = []
        self.ik_global_out = []
        self.ik_global_ref = []
        self.ik_uv_param = []
        self.ik_decompose_rot = []

        self.arrow_ctl = None
        self.arrow_npo = None
        self.upControls = []
        self.lowControls = []
        self.trackLvl = []

        self.upCrv = None
        self.lowCrv = None
        self.upCrv_ctl = None
        self.lowCrv_ctl = None
        self.upBlink = None
        self.lowBlink = None
        self.upTarget = None
        self.lowTarget = None
        self.midTarget = None
        self.midTargetLower = None

        self.previusTag = self.parentCtlTag
        self.guide.eyeMesh = self.guide.getObjects(self.guide.root)["eyeMesh"]

        self.addCurve()
        self.addControllers()

    def getNumberOfLocators(self, query):
        # type: (Text) -> int
        """ _uplocs."""
        num = 0
        for k, v in self.guide.tra.items():
            if query in k:
                index = int(re.search(r"^(\d+)", k).group(1))
                num = max(num, index + 1)

        return num

    def addDummyPlane(self):
        # type: () -> om.MFnMesh

        positions = [self.inPos]
        positions.extend(self.uplocsPos)
        positions.append(self.outPos)
        positions.extend(reversed(self.lowlocsPos))

        return draw_eye_guide_mesh_plane(positions, self.root)
        # return mgear_util.draw_eye_guide_mesh_plane(joint_points)

    def addCurve(self):

        t = getTransform(self.root)
        crv_root = addTransform(self.root, self.getName("crvs"), t)

        plane = self.addDummyPlane()
        self.addCurves(crv_root, plane)
        pm.delete(pm.PyNode(plane.name()))

    def addCurves(self, crv_root, plane):

        t = getTransform(self.root)
        gen = curve.createCurveFromOrderedEdges
        gen2 = curve.createCurveFromCurve
        planeNode = pm.PyNode(plane.fullPathName())

        # -------------------------------------------------------------------
        edgeList = ["{}.e[{}]".format(plane.fullPathName(), 0)]
        for i in range(1, self.num_uplocs + 1):
            edgeList.append("{}.e[{}]".format(plane.fullPathName(), i * 2 + 1))
        edgeList = [pm.PyNode(x) for x in edgeList]

        # upEyelid = meshNavigation.edgeRangeInLoopFromMid(edgeList, upPos, inPos, outPos)
        self.upCrv = gen(edgeList, planeNode.verts[1], self.getName("upperEyelid"), parent=crv_root, m=t)
        self.upCrv_ctl = gen(edgeList, planeNode.verts[1], self.getName("upCtl_crv"), parent=crv_root, m=t)
        pm.rebuildCurve(self.upCrv_ctl, s=2, rt=0, rpo=True, ch=False)

        # -------------------------------------------------------------------
        edgeList = []
        for i in reversed(range(self.num_uplocs + 1, self.num_uplocs + self.num_lowlocs + 2)):
            edgeList.append("{}.e[{}]".format(plane.fullPathName(), i * 2 + 1))
        edgeList = [pm.PyNode(x) for x in edgeList]

        self.lowCrv = gen(edgeList, planeNode.verts[1], self.getName("lowerEyelid"), parent=crv_root, m=t)
        self.lowCrv_ctl = gen(edgeList, planeNode.verts[1], self.getName("lowCtl_crv"), parent=crv_root, m=t)
        pm.rebuildCurve(self.lowCrv_ctl, s=2, rt=0, rpo=True, ch=False)

        # -------------------------------------------------------------------
        self.upBlink = gen2(self.upCrv, self.getName("upblink_crv"), nbPoints=30, parent=crv_root)
        self.lowBlink = gen2(self.lowCrv, self.getName("lowBlink_crv"), nbPoints=30, parent=crv_root)

        self.upTarget = gen2(self.upCrv, self.getName("upblink_target"), nbPoints=30, parent=crv_root)
        self.lowTarget = gen2(self.lowCrv, self.getName("lowBlink_target"), nbPoints=30, parent=crv_root)
        self.midTarget = gen2(self.lowCrv, self.getName("midBlink_target"), nbPoints=30, parent=crv_root)
        self.midTargetLower = gen2(self.lowCrv, self.getName("midBlinkLower_target"), nbPoints=30, parent=crv_root)

        rigCrvs = [self.upCrv,
                   self.lowCrv,
                   self.upCrv_ctl,
                   self.lowCrv_ctl,
                   self.upBlink,
                   self.lowBlink,
                   self.upTarget,
                   self.lowTarget,
                   self.midTarget,
                   self.midTargetLower]

        for crv in rigCrvs:
            crv.attr("visibility").set(False)

    def getBboxRadius(self):
        # localBBOX

        localBBox = self.guide.eyeMesh.getBoundingBox(invisible=True, space='world')
        wRadius = abs((localBBox[0][0] - localBBox[1][0]))
        dRadius = abs((localBBox[0][1] - localBBox[1][1]) / 1.7)

        return wRadius, dRadius

    def addControllers(self):
        axis = "zy"

        inPos = self.guide.apos[-5]
        outPos = self.guide.apos[-4]
        upPos = self.guide.apos[-3]
        lowPos = self.guide.apos[-2]
        frontPos = self.guide.apos[-1]

        self.bboxCenter = meshNavigation.bboxCenter(self.guide.eyeMesh)
        averagePosition = ((upPos + lowPos + inPos + outPos) / 4)

        # normalPos = outPos
        normalVec = upPos - lowPos
        if self.negate:
            pass
            # normalVec = normalVec * -1.0

        t = transform.getTransformLookingAt(
            self.root.getTranslation(space="world"),
            # self.bboxCenter,
            frontPos,
            normalVec,
            axis=axis,
            # negate=self.negate)
        ) 

        # averagePosition,
        t_arrow = setMatrixPosition(t, self.bboxCenter)

        self.eyeTargets_root = addTransform(self.root, self.getName("targets"), t)
        self.jnt_root = primitive.addTransformFromPos(self.root, self.getName("joints"), pos=self.bboxCenter)
        # TODO: implement later
        # if deformers_group:
        #     deformers_group = pm.PyNode(deformers_group)
        #     pm.parentConstraint(self.root, jnt_root, mo=True)
        #     pm.scaleConstraint(self.root, jnt_root, mo=True)
        #     deformers_group.addChild(jnt_root)

        self.addOverControllers(t)
        self.addLookAtControlers(t, t_arrow)
        self.addAimControllers(t)
        self.addCurveControllers(t)
        self.addCurveJoints(t)
        self.addWires()

    def addOverControllers(self, t):

        self.over_npo = addTransform(self.root, self.getName("center_lookatRoot"), t)
        self.over_ctl = self.addCtl(self.over_npo,
                                    self.getName("over_%s" % self.ctlName),
                                    t,
                                    self.color_ik,
                                    "square",
                                    w=self.getBboxRadius()[0],
                                    d=self.getBboxRadius()[1],
                                    ro=datatypes.Vector(1.57079633, 0, 0),
                                    po=self.offset,
                                    )

        if self.negate:
            # TODO: implement later
            # self.over_npo.attr("rx").set(self.over_npo.attr("rx").get() * -1)
            # self.over_npo.attr("ry").set(self.over_npo.attr("ry").get() + 180)
            # self.over_npo.attr("sz").set(-1)
            pass

        # node.add_controller_tag(over_ctl)
        # self.addAnimParam(over_ctl, "isCtl", "bool", keyable=False)
        # attribute.add_mirror_config_channels(over_ctl)
        attribute.setKeyableAttributes(
            self.over_ctl,
            params=["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"])

    def addLookAtControlers(self, t_root, t_look):
        self.center_lookat = addTransform(self.over_ctl, self.getName("center_lookat"), t_root)

        # Tracking
        # Eye aim control

        radius = abs(self.getBboxRadius()[0] / 1.7)
        if True or not self.negate:
            ro = datatypes.Vector(0, 0, 0)
            po = datatypes.Vector(0, 0, radius) + self.offset
        else:
            ro = datatypes.Vector(math.pi, 0, 0)
            po = datatypes.Vector(0, 0, radius * -1.0) + self.offset

            addRot = datatypes.TransformationMatrix()
            addRot.setRotation(0, math.pi / 2.0, 0)
            t_look = t_look * addRot

        self.arrow_npo = addTransform(self.root, self.getName("aim_npo"), t_look)
        self.arrow_ctl = self.addCtl(
            self.arrow_npo,
            self.getName("aim_%s" % self.ctlName),
            t_look,
            self.color_ik,
            "arrow",
            w=1,
            ro=ro,
            po=po,
        )

        attribute.setKeyableAttributes(self.arrow_ctl, params=["rx", "ry", "rz"])
        # self.addAnimParam(self.arrow_ctl, "isCtl", "bool", keyable=False)

    def addAimControllers(self, t):

        # tracking custom trigger
        aimTrigger_root = addTransform(self.center_lookat, self.getName("aimTrigger_root"), t)
        # For some unknown reason the right side gets scewed rotation values
        resetTransform(aimTrigger_root)
        aimTrigger_lvl = addTransform(aimTrigger_root, self.getName("aimTrigger_lvl"), t)

        # For some unknown reason the right side gets scewed rotation values
        resetTransform(aimTrigger_lvl)
        aimTrigger_lvl.attr("tz").set(1.0)
        self.aimTrigger_ref = addTransform(aimTrigger_lvl, self.getName("self.aimTrigger_ref"), t)

        # For some unknown reason the right side gets scewed rotation values
        resetTransform(self.aimTrigger_ref)
        self.aimTrigger_ref.attr("tz").set(0.0)

        # connect  trigger with arrow_ctl
        pm.parentConstraint(self.arrow_ctl, self.aimTrigger_ref, mo=True)

    def addCurveControllers(self, t):

        # upper eyelid controls
        upperCtlNames = ["inCorner", "upInMid", "upMid", "upOutMid", "outCorner"]
        self.upControls = self._addCurveControllers(t, self.upCrv_ctl, upperCtlNames)

        lowerCtlNames = ["inCorner", "lowInMid", "lowMid", "lowOutMid", "outCorner"]
        self.lowControls = self._addCurveControllers(t, self.lowCrv_ctl, lowerCtlNames)
        self.lowControls.insert(0, self.upControls[0])

    def addCurveJoints(self, t):

        # upper eyelid controls
        self.upDetailControllers = self._addCurveDetailControllers(t, self.upCrv, "upEyelid")
        self.lowDetailControllers = self._addCurveDetailControllers(t, self.lowCrv, "lowEyelid")

    def _addCurveControllers(self, t, crv, ctlNames):

        cvs = crv.getCVs(space="world")
        if self.negate:
            # cvs = [cv for cv in reversed(cvs)]
            pass

        ctls = []
        for i, cv in enumerate(cvs):
            if utils.is_odd(i):
                color = 14
                wd = .5
                offset = self.offset * 1.1
                icon_shape = "circle"
                params = ["tx", "ty", "tz"]

            else:
                color = 4
                wd = .7
                offset = self.offset * 1.3
                icon_shape = "square"
                params = ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"]

            t = setMatrixPosition(t, cvs[i])
            npo = addTransform(self.center_lookat, self.getName("%s_npo" % ctlNames[i]), t)
            npoBase = npo

            if i == 2:
                # we add an extra level to input the tracking ofset values
                npo = addTransform(npo, self.getName("%s_trk" % ctlNames[i]), t)
                self.trackLvl.append(npo)

            ctl = self.addCtl(npo,
                              self.getName("%s_%s" % (ctlNames[i], self.ctlName)),
                              t,
                              color,
                              icon_shape,
                              w=wd,
                              d=wd,
                              ro=datatypes.Vector(1.57079633, 0, 0),
                              po=offset
                              )

            attribute.setKeyableAttributes(ctl, params)
            if self.negate:
                pass
                # npoBase.attr("ry").set(180)
                # npoBase.attr("sz").set(-1)

            ctls.append(ctl)

        # adding parent average contrains to odd controls
        for i, ctl in enumerate(ctls):
            if utils.is_odd(i):
                pm.parentConstraint(ctls[i - 1],
                                    ctls[i + 1],
                                    ctl.getParent(),
                                    mo=True)

        applyop.gear_curvecns_op(crv, ctls)
        return ctls

    def _addCurveDetailControllers(self, t, crv, name):

        controls = []

        cvs = crv.getCVs(space="world")
        crv_info = node.createCurveInfoNode(crv)

        if self.negate:
            pass
            # cvs = [cv for cv in reversed(cvs)]

        # aim constrain targets and joints
        icon_shape = "sphere"
        color = 4
        wd = .3
        offset = self.offset * 0.3

        for i, cv in enumerate(cvs):

            # aim targets
            trn_name = self.getName("{}_aimTarget{}".format(name, i))
            trn = primitive.addTransformFromPos(self.eyeTargets_root, trn_name, pos=cv)

            # connecting positions with crv
            pm.connectAttr(crv_info + ".controlPoints[%s]" % str(i), trn.attr("translate"))

            # joints
            xform = setMatrixPosition(t, self.bboxCenter)
            npo_name = self.getName("{}_jnt_base{}".format(name, str(i)))
            npo = addTransform(self.jnt_root, npo_name, xform)
            applyop.aimCns(npo, trn, axis="zy", wupObject=self.jnt_root)

            ctl_name = self.getName("crvdetail%s_%s" % (i, self.ctlName))
            xform = setMatrixPosition(t, cv)
            ctl = self.addCtl(
                npo,
                ctl_name,
                xform,
                color,
                icon_shape,
                w=wd,
                d=wd,
                ro=datatypes.Vector(1.57079633, 0, 0),
                po=offset
            )

            controls.append(ctl)

            jnt_name = "{}{}".format(name, i)
            self.jnt_pos.append([ctl, jnt_name])

        return controls

    def addWires(self):
        # adding wires
        self.w1 = pm.wire(self.upCrv, w=self.upBlink)[0]
        self.w2 = pm.wire(self.lowCrv, w=self.lowBlink)[0]

        self.w3 = pm.wire(self.upTarget, w=self.upCrv_ctl)[0]
        self.w4 = pm.wire(self.lowTarget, w=self.lowCrv_ctl)[0]

        # adding blendshapes
        self.bs_upBlink  = pm.blendShape(self.upTarget,  self.midTarget,      self.upBlink,        n=self.getName("blendShapeUpBlink"))
        self.bs_lowBlink = pm.blendShape(self.lowTarget, self.midTargetLower, self.lowBlink,       n=self.getName("blendShapeLowBlink"))
        self.bs_mid      = pm.blendShape(self.lowTarget, self.upTarget,       self.midTarget,      n=self.getName("blendShapeMidBlink"))
        self.bs_midLower = pm.blendShape(self.lowTarget, self.upTarget,       self.midTargetLower, n=self.getName("blendShapeMidLowerBlink"))

        # setting blendshape reverse connections
        rev_node = pm.createNode("reverse")
        pm.connectAttr(self.bs_upBlink[0].attr(self.midTarget.name()), rev_node + ".inputX")
        pm.connectAttr(rev_node + ".outputX", self.bs_upBlink[0].attr(self.upTarget.name()))

        rev_node = pm.createNode("reverse")
        rev_nodeLower = pm.createNode("reverse")
        pm.connectAttr(self.bs_lowBlink[0].attr(self.midTargetLower.name()), rev_node + ".inputX")
        pm.connectAttr(rev_node + ".outputX",self.bs_lowBlink[0].attr(self.lowTarget.name()))

        rev_node = pm.createNode("reverse")
        pm.connectAttr(self.bs_mid[0].attr(self.upTarget.name()), rev_node + ".inputX")
        pm.connectAttr(self.bs_midLower[0].attr(self.upTarget.name()), rev_nodeLower + ".inputX")
        pm.connectAttr(rev_node + ".outputX", self.bs_mid[0].attr(self.lowTarget.name()))
        pm.connectAttr(rev_nodeLower + ".outputX", self.bs_midLower[0].attr(self.lowTarget.name()))

        # setting default values
        self.bs_mid[0].attr(self.upTarget.name()).set(self.blinkH)
        self.bs_midLower[0].attr(self.upTarget.name()).set(self.blinkH)

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        if not self.settings["ui_host"]:
            self.uihost = self.over_ctl
        # blinkH = blinkH / 100.0

        self.addBlinkAttributes()
        self.addEyeTrackingAttributes()
        self.addTensionOnBlinkAttributes()

    def addBlinkAttributes(self):

        # Adding and connecting attributes for the blinks

        self.blink_att      = self.addAnimParam("blink",       "Blink",            "float", 0,           minValue=0, maxValue=1)
        self.blinkUpper_att = self.addAnimParam("upperBlink",  "Upper Blink",      "float", 0,           minValue=0, maxValue=1)
        self.blinkLower_att = self.addAnimParam("lowerBlink",  "Lower Blink",      "float", 0,           minValue=0, maxValue=1)
        self.blinkMult_att  = self.addAnimParam("blinkMult",   "Blink Multiplyer", "float", 1,           minValue=1, maxValue=2)
        self.midBlinkH_att  = self.addAnimParam("blinkHeight", "Blink Height",     "float", self.blinkH, minValue=0, maxValue=1)

        # Add blink + upper and blink + lower so animator can use both.
        # But also clamp them so using both doesn't exceed 1.0
        blinkAdd = pm.createNode('plusMinusAverage')
        blinkClamp = pm.createNode('clamp')
        blinkClamp.maxR.set(1.0)
        blinkClamp.maxG.set(1.0)
        self.blink_att.connect(blinkAdd.input2D[0].input2Dx)
        self.blink_att.connect(blinkAdd.input2D[0].input2Dy)
        self.blinkUpper_att.connect(blinkAdd.input2D[1].input2Dx)
        self.blinkLower_att.connect(blinkAdd.input2D[1].input2Dy)
        addOutput = blinkAdd.output2D
        addOutput.output2Dx.connect(blinkClamp.inputR)
        addOutput.output2Dy.connect(blinkClamp.inputG)

        # Drive the clamped blinks through blinkMult, then to the blendshapes
        mult_node = node.createMulNode(blinkClamp.outputR, self.blinkMult_att)
        mult_nodeLower = node.createMulNode(blinkClamp.outputG, self.blinkMult_att)
        pm.connectAttr(mult_node + ".outputX", self.bs_upBlink[0].attr(self.midTarget.name()))
        pm.connectAttr(mult_nodeLower + ".outputX", self.bs_lowBlink[0].attr(self.midTargetLower.name()))
        pm.connectAttr(self.midBlinkH_att, self.bs_mid[0].attr(self.upTarget.name()))
        pm.connectAttr(self.midBlinkH_att, self.bs_midLower[0].attr(self.upTarget.name()))

    def addEyeTrackingAttributes(self):

        up_ctl = self.upControls[2]
        low_ctl = self.lowControls[3]

        # Adding channels for eye tracking
        upVTracking_att  = attribute.addAttribute(up_ctl,  "vTracking", "float", self.upperVTrack, minValue=0, keyable=False, channelBox=True)
        upHTracking_att  = attribute.addAttribute(up_ctl,  "hTracking", "float", self.upperHTrack, minValue=0, keyable=False, channelBox=True)

        lowVTracking_att = attribute.addAttribute(low_ctl, "vTracking", "float", self.lowerVTrack, minValue=0, keyable=False, channelBox=True)
        lowHTracking_att = attribute.addAttribute(low_ctl, "hTracking", "float", self.lowerHTrack, minValue=0, keyable=False, channelBox=True)

        mult_node = node.createMulNode(upVTracking_att, self.aimTrigger_ref.attr("ty"))
        pm.connectAttr(mult_node + ".outputX", self.trackLvl[0].attr("ty"))
        mult_node = node.createMulNode(upHTracking_att, self.aimTrigger_ref.attr("tx"))

        # Correct right side horizontal tracking
        if self.negate:
            pass
            # mult_node = node.createMulNode(mult_node.attr("outputX"), -1)

        pm.connectAttr(mult_node + ".outputX", self.trackLvl[0].attr("tx"))

        mult_node = node.createMulNode(lowVTracking_att, self.aimTrigger_ref.attr("ty"))
        pm.connectAttr(mult_node + ".outputX", self.trackLvl[1].attr("ty"))
        mult_node = node.createMulNode(lowHTracking_att, self.aimTrigger_ref.attr("tx"))

        # Correct right side horizontal tracking
        if self.negate:
            pass
            # mult_node = node.createMulNode(mult_node.attr("outputX"), -1)

        pm.connectAttr(mult_node + ".outputX", self.trackLvl[1].attr("tx"))

    def addTensionOnBlinkAttributes(self):
        # Tension on blink
        # Drive the clamped blinks through to the blink tension wire deformers
        # Add blink + upper and blink + lower so animator can use both.
        # But also clamp them so using both doesn't exceed 1.0
        blinkAdd = pm.createNode('plusMinusAverage')
        blinkClamp = pm.createNode('clamp')
        blinkClamp.maxR.set(1.0)
        blinkClamp.maxG.set(1.0)
        self.blink_att.connect(blinkAdd.input2D[0].input2Dx)
        self.blink_att.connect(blinkAdd.input2D[0].input2Dy)
        self.blinkUpper_att.connect(blinkAdd.input2D[1].input2Dx)
        self.blinkLower_att.connect(blinkAdd.input2D[1].input2Dy)

        addOutput = blinkAdd.output2D
        addOutput.output2Dx.connect(blinkClamp.inputR)
        addOutput.output2Dy.connect(blinkClamp.inputG)
        # 1 and 3 are upper. 2 and 4 are lower.
        node.createReverseNode(blinkClamp.outputR, self.w1.scale[0])
        node.createReverseNode(blinkClamp.outputR, self.w3.scale[0])
        node.createReverseNode(blinkClamp.outputG, self.w2.scale[0])
        node.createReverseNode(blinkClamp.outputG, self.w4.scale[0])

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

    def connectRef(self, refArray, cns_obj, upVAttr=None, init_refNames=False):
        """Connect the cns_obj to a multiple object using parentConstraint.

        Args:
            refArray (list of dagNode): List of driver objects
            cns_obj (dagNode): The driven object.
            upVAttr (bool): Set if the ref Array is for IK or Up vector
        """
        if refArray:
            if upVAttr and not init_refNames:
                # we only can perform name validation if the init_refnames are
                # provided in a separated list. This check ensures backwards
                # copatibility
                ref_names = refArray.split(",")
            else:
                ref_names = self.get_valid_ref_list(refArray.split(","))

            if not ref_names:
                # return if the not ref_names list
                return
            elif len(ref_names) == 1:
                ref = self.rig.findRelative(ref_names[0])
                pm.parent(cns_obj, ref)
            else:
                ref = []
                for ref_name in ref_names:
                    ref.append(self.rig.findRelative(ref_name))

                ref.append(cns_obj)
                cns_node = pm.parentConstraint(*ref, maintainOffset=True)
                cns_attr = pm.parentConstraint(
                    cns_node, query=True, weightAliasList=True)
                # check if the ref Array is for IK or Up vector
                try:
                    if upVAttr:
                        oAttr = self.upvref_att
                    else:
                        oAttr = self.ikref_att

                except AttributeError:
                    oAttr = None

                if oAttr:
                    for i, attr in enumerate(cns_attr):
                        node_name = pm.createNode("condition")
                        pm.connectAttr(oAttr, node_name + ".firstTerm")
                        pm.setAttr(node_name + ".secondTerm", i)
                        pm.setAttr(node_name + ".operation", 0)
                        pm.setAttr(node_name + ".colorIfTrueR", 1)
                        pm.setAttr(node_name + ".colorIfFalseR", 0)
                        pm.connectAttr(node_name + ".outColorR", attr)

    def connect_standard(self):
        self.parent.addChild(self.root)
        return

    # =====================================================
    # CONNECTOR
    # =====================================================

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        if self.settings["isGlobalMaster"]:
            return

        # self.relatives["root"] = self.fk_ctl[0]


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


if __name__ == "__main__":
    pass
