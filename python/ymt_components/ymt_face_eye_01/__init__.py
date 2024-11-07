"""mGear shifter components"""
import sys
import re
import math
import functools

import maya.cmds as cmds
# import maya.OpenMaya as om1
# import maya.api.OpenMaya as om

import pymel.core as pm
from pymel.core import datatypes

from mgear.shifter import component

from mgear.core import (
    transform,
    # curve,
    applyop,
    attribute,
    # icon,
    # fcurve,
    # vector,
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
from mgear.rigbits import ghost

import ymt_shifter_utility as ymt_util
import ymt_shifter_utility.curve as curve

if sys.version_info > (3, 0):
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

from logging import (  # noqa:F401 pylint: disable=unused-import, wrong-import-order
    StreamHandler,
    getLogger,
    # WARN,
    DEBUG,
    INFO
)

handler = StreamHandler()
handler.setLevel(DEBUG)
logger = getLogger(__name__)
logger.setLevel(INFO)
logger.addHandler(handler)
logger.propagate = False


EPSILON = 1e-4


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
        self.normalVec = self.upPos - self.lowPos

        self.uplocsPos = self.guide.apos[2:self.num_uplocs + 2]
        self.lowlocsPos = self.guide.apos[2 + self.num_uplocs:-5]

        self.offset = self.frontPos - self.rootPos
        if self.negate:
            pass
            # self.offset[2] = self.offset[2] * -1.0

        # -------------------------------------------------------
        # TODO: extract to settings
        self.ctlName = "ctl"
        self.detailControllersGroupName = "controllers_detail"
        self.primaryControllersGroupName = "controllers_primary"
        self.blinkH = 0.2
        self.upperVTrackUp = 0.33
        self.upperVTrackLow = 0.10
        self.upperHTrack = 0.10
        self.lowerVTrackUp = 0.25
        self.lowerVTrackLow = 0.10
        self.lowerHTrack = 0.10

        # --------------------------------------------------------
        self.upControls = []
        self.lowControls = []
        self.trackLvl = []

        # self.arrow_ctl = None
        # self.arrow_npo = None
        # self.upCrv = None
        # self.lowCrv = None
        # self.upCrv_ctl = None
        # self.lowCrv_ctl = None
        # self.upBlink = None
        # self.lowBlink = None
        # self.upTarget = None
        # self.lowTarget = None
        # self.midTarget = None
        # self.midTargetLower = None

        self.previusTag = self.parentCtlTag
        self.guide.eyeMesh = self.guide.getObjects(self.guide.root)["pivotAndSizeRef"]
        # --------------------------------------------------------

        positions = [self.inPos]
        positions.extend(self.uplocsPos)
        positions.append(self.outPos)
        relativeUpPositions = [x - self.rootPos for x in positions]

        positions = [self.inPos]
        positions.extend(self.lowlocsPos)
        positions.append(self.outPos)
        relativeLowPositions = [x - self.rootPos for x in positions]

        self.crvroot, crvs = self.addCurves(relativeUpPositions, relativeLowPositions)
        self.upCrv = crvs[0]
        self.lowCrv = crvs[1]
        self.upCrv_ctl = crvs[2]
        self.lowCrv_ctl = crvs[3]
        self.upBlink = crvs[4]
        self.lowBlink = crvs[5]
        self.upTarget = crvs[6]
        self.lowTarget = crvs[7]

        self.addControllers()

        self.connect_surface_slider = self.settings["isSlidingSurface"]
        if not self.connect_surface_slider:
            return

        bt = transform.getTransform(self.root)
        self.slider_root = addTransform(self.root, self.getName("sliders"), bt)
        ymt_util.setKeyableAttributesDontLockVisibility(self.slider_root, [])

        self.surfRef = self.settings["surfaceReference"]
        if not self.surfRef:
            self.sliding_surface = pm.duplicate(self.guide.getObjects(self.guide.root)["sliding_surface"])[0]
            pm.parent(self.sliding_surface.name(), self.root)
            self.sliding_surface.visibility.set(False)
            pm.makeIdentity(self.sliding_surface, apply=True, t=1,  r=1, s=1, n=0, pn=1)  # type: ignore

    def getNumberOfLocators(self, query):
        # type: (Text) -> int
        """ _uplocs."""
        num = 0
        for k, v in self.guide.tra.items():
            if query in k:
                m = re.search(r"^(\d+)", k)
                if not m:
                    continue
                index = int(m.group(1))
                num = max(num, index + 1)

        return num

    def addCurves(self, upPositions, lowPositions):

        gen2 = curve.createCurveFromCurve
        gen3 = curve.addCurve

        t = getTransform(self.root)
        scl = [1, 1, 1]
        if self.negate:
            scl = [-1, 1, 1]
        t = transform.setMatrixScale(t, scl)
        crv_root = addTransform(self.root, self.getName("crvs"), t)

        t = getTransform(self.root)

        # -------------------------------------------------------------------
        upCrv = gen3(crv_root, self.getName("upperEyelid"), upPositions, m=t)
        upCrv_ctl = gen3(crv_root, self.getName("upCtl_crv"), upPositions, m=t)
        pm.rebuildCurve(upCrv_ctl, s=2, rt=0, rpo=True, ch=False)

        # -------------------------------------------------------------------

        lowCrv = gen3(crv_root, self.getName("lowerEyelid"), lowPositions, m=t)
        lowCrv_ctl = gen3(crv_root, self.getName("lowCtl_crv"), lowPositions, m=t)
        pm.rebuildCurve(lowCrv_ctl, s=2, rt=0, rpo=True, ch=False)

        # -------------------------------------------------------------------
        _ = gen2(upCrv, self.getName("upblink_crv"), nbPoints=30, parent=crv_root, m=t)
        pm.delete(_)
        upBlink = gen2(upCrv, self.getName("upblink_crv"), nbPoints=30, parent=crv_root, m=t)
        _ = gen2(lowCrv, self.getName("lowBlink_crv"), nbPoints=30, parent=crv_root, m=t)
        pm.delete(_)
        lowBlink = gen2(lowCrv, self.getName("lowBlink_crv"), nbPoints=30, parent=crv_root, m=t)

        upTarget = gen2(upCrv, self.getName("upblink_target"), nbPoints=30, parent=crv_root, m=t)
        lowTarget = gen2(lowCrv, self.getName("lowBlink_target"), nbPoints=30, parent=crv_root, m=t)

        # -------------------------------------------------------------------
        rigCrvs = [upCrv,
                   lowCrv,
                   upCrv_ctl,
                   lowCrv_ctl,
                   upBlink,
                   lowBlink,
                   upTarget,
                   lowTarget,
        ]

        for crv in rigCrvs:
            crv.attr("visibility").set(False)

        return crv_root, rigCrvs

    def getBboxRadius(self):
        # localBBOX

        localBBox = self.guide.eyeMesh.getBoundingBox(invisible=True, space="world")
        wRadius = abs((localBBox[0][0] - localBBox[1][0]))
        dRadius = abs((localBBox[0][1] - localBBox[1][1]) / 1.7)

        return wRadius, dRadius

    def addControllers(self):

        axis = "zy"
        self.bboxCenter = meshNavigation.bboxCenter(self.guide.eyeMesh)

        # normalPos = outPos
        if self.negate:
            pass

        t = transform.getTransformLookingAt(
            self.root.getTranslation(space="world"),
            self.frontPos,
            self.normalVec,
            axis=axis,
        ) 

        # averagePosition,
        t_arrow = setMatrixPosition(t, self.bboxCenter)
        scl = [1, 1, 1]
        t = transform.setMatrixScale(t, scl)
        bt = transform.setMatrixPosition(t, self.bboxCenter)

        self.eyeTargets_root = addTransform(self.root, self.getName("targets"), t)
        self.jnt_root = addTransform(self.root, self.getName("joints"), bt)
        if self.negate:
            scl = [-1, 1, 1]
        t = transform.setMatrixScale(t, scl)

        self.addOverControllers(t)
        self.addLookAtControlers(t, t_arrow)
        self.addAimControllers(t)
        self.addCurveControllers(t)
        self.addCurveJoints(t)
        self.addWires()
        self.addBlinkControllers(t)

    def addOverControllers(self, t):
        # po = self.offset + (self.outPos - self.inPos) * 1.1
        # po.z += self.offset.z * 0.5

        up_blink_pos = self.upPos
        lo_blink_pos = self.lowPos
        po = ((up_blink_pos + lo_blink_pos) / 2.0) - self.root.getTranslation(space="world")
        if self.negate:
            po.x *= -1.0

        self.over_npo = addTransform(self.root, self.getName("center_lookatRoot"), t)
        self.over_ctl = self.addCtl(
            self.over_npo,
            "over_%s" % self.ctlName,
            t,
            self.color_ik,
            "square",
            w=self.getBboxRadius()[0] * 0.15,
            d=self.getBboxRadius()[1] * 0.7,
            ro=datatypes.Vector(1.57079633, 0, 0),
            po=po,
        )
        self.jnt_pos.append([self.over_ctl, "base"])
        self.addToSubGroup(self.over_ctl, self.primaryControllersGroupName)
        ymt_util.setKeyableAttributesDontLockVisibility(
            self.over_ctl,
            params=["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"])

    def addLookAtControlers(self, t_root, t_look):
        # Tracking
        # Eye aim control

        self.center_lookat = addTransform(self.over_ctl, self.getName("center_lookat"), t_root)

        radius = abs(self.getBboxRadius()[0] / 1.7)
        if True or not self.negate:
            ro = datatypes.Vector(0, 0, 0)
            po = datatypes.Vector(0, 0, radius) + self.offset * 0.3

        else:
            ro = datatypes.Vector(math.pi, 0, 0)
            po = datatypes.Vector(0, 0, radius * -1.0) + self.offset * 0.3

        self.arrow_npo = addTransform(self.over_ctl, self.getName("aim_npo"), t_look)
        self.arrow_ctl = self.addCtl(
            self.arrow_npo,
            "aim_%s" % self.ctlName,
            t_look,
            self.color_ik,
            "arrow",
            w=1,
            ro=ro,
            po=po,
        )
        self.addToSubGroup(self.over_ctl, self.primaryControllersGroupName)

        ymt_util.setKeyableAttributesDontLockVisibility(self.arrow_ctl, params=["rx", "ry", "rz"])

    def addAimControllers(self, t):

        # tracking custom trigger
        aimTrigger_root = addTransform(self.center_lookat, self.getName("aimTrigger_root"), t)
        resetTransform(aimTrigger_root)
        aimTrigger_lvl = addTransform(aimTrigger_root, self.getName("aimTrigger_lvl"), t)

        resetTransform(aimTrigger_lvl)
        self.aimTrigger_ref = addTransform(aimTrigger_lvl, self.getName("aimTrigger_ref"), t)
        resetTransform(self.aimTrigger_ref)
        self.aimTrigger_ref.attr("tx").set(EPSILON)
        self.aimTrigger_ref.attr("ty").set(EPSILON)
        self.aimTrigger_ref.attr("tz").set(EPSILON)

        # connect trigger with arrow_ctl
        pm.parentConstraint(self.arrow_ctl, self.aimTrigger_ref, mo=True)

    def addBlinkControllers(self, t):
        blink_root = addTransform(self.over_ctl, self.getName("blink_root"), t)

        inv = datatypes.EulerRotation(180.0, 0.0, 0.0)
        upper_t = transform.setMatrixPosition(t, self.upPos)
        upper_t *= inv.asMatrix()
        upper_t = transform.setMatrixPosition(upper_t, self.upPos)
        lower_t = transform.setMatrixPosition(t, self.lowPos)

        blink_upper_npo = addTransform(blink_root, self.getName("blink_upper_npo"), upper_t)
        blink_lower_npo = addTransform(blink_root, self.getName("blink_lower_npo"), lower_t)
        height = (self.upPos - self.lowPos).length()
        width = height * 0.3

        self.blink_upper_ctl = self.addCtl(
                blink_upper_npo,
                self.getName("blink_upper"),
                upper_t,
                self.color_ik,
                "arrow",
                w=width,
                po=datatypes.Vector(0.0, width * -0.5, 0.0),
                ro=datatypes.Vector(0.0, 1.57079633, 1.57079633)
        )
        self.blink_lower_ctl = self.addCtl(
                blink_lower_npo,
                self.getName("blink_lower"),
                lower_t,
                self.color_ik,
                "arrow",
                w=width,
                po=datatypes.Vector(0.0, width * -0.5, 0.0),
                ro=datatypes.Vector(0.0, 1.57079633, 1.57079633)
        )
        ymt_util.setKeyableAttributesDontLockVisibility(self.blink_upper_ctl, params=["ty"])
        ymt_util.setKeyableAttributesDontLockVisibility(self.blink_lower_ctl, params=["ty"])

    def addCurveControllers(self, t):

        # upper eyelid controls
        upperCtlNames = ["inCorner", "upInMid", "upMid", "upOutMid", "outCorner"]
        self.upControls = self._addCurveControllers(t, self.upCrv_ctl, upperCtlNames)

        lowerCtlNames = ["inCorner", "lowInMid", "lowMid", "lowOutMid", "outCorner"]
        if self.settings.get("isSplitCorners", False):
            self.lowControls = self._addCurveControllers(t, self.lowCrv_ctl, lowerCtlNames)
        else:
            self.lowControls = self._addCurveControllers(t, self.lowCrv_ctl, lowerCtlNames, inCtl=self.upControls[0], outCtl=self.upControls[-1])

        # self.lowControls.insert(0, self.upControls[0])
        # self.lowControls.append(self.upControls[-1])

    def addCurveJoints(self, t):

        skip = not self.settings.get("isSplitCorners", False)

        # upper eyelid controls
        ctls, npos, aim_npos =  self._addCurveDetailControllers(t, self.upCrv, self.upBlink, "upEyelid")
        self.upDetailControllers = ctls
        self.upDetailNpos = npos
        self.upDetailAimNpos = aim_npos

        ctls, npos, aim_npos = self._addCurveDetailControllers(t, self.lowCrv, self.lowBlink, "lowEyelid", skipHeadAndTail=skip)
        self.lowDetailControllers = ctls
        self.lowDetailNpos = npos
        self.lowDetailAimNpos = aim_npos

    def _addCurveControllers(self, t, crv, ctlNames, inCtl=None, outCtl=None):

        cvs = crv.getCVs(space="world")
        if self.negate:
            # cvs = [cv for cv in reversed(cvs)]
            pass

        ctls = []
        for i, cv in enumerate(cvs):
            if inCtl is not None and i == 0:
                ctls.append(inCtl)
                continue

            if outCtl is not None and (i == len(cvs) - 1):
                ctls.append(outCtl)
                continue

            if utils.is_odd(i):
                color = 14
                wd = .5
                offset = self.offset * 0.33
                icon_shape = "circle"
                params = ["tx", "ty", "tz"]

            else:
                color = 4
                wd = .7
                offset = self.offset * 0.4
                icon_shape = "square"
                params = ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"]

            t = setMatrixPosition(t, cvs[i])
            npo = addTransform(self.center_lookat, self.getName("%s_npo" % ctlNames[i]), t)

            if i == 2:
                # we add an extra level to input the tracking ofset values
                npo = addTransform(npo, self.getName("%s_trk" % ctlNames[i]), t)
                self.trackLvl.append(npo)

            ctl = self.addCtl(npo,
                              "%s_%s" % (ctlNames[i], self.ctlName),
                              t,
                              color,
                              icon_shape,
                              w=wd,
                              d=wd,
                              ro=datatypes.Vector(1.57079633, 0, 0),
                              po=offset * 0.3
                              )

            self.addToSubGroup(self.over_ctl, self.primaryControllersGroupName)
            ymt_util.setKeyableAttributesDontLockVisibility(ctl, params)
            ctls.append(ctl)

        # adding parent average contrains to odd controls
        for i, ctl in enumerate(ctls):
            if utils.is_odd(i):
                s = ctls[i - 1]
                d = ctls[i + 1]
                pm.parentConstraint(s, d, ctl.getParent(), mo=True)

        curve.gear_curvecns_op_local(crv, ctls)

        return ctls

    def addToSubGroup(self, obj, group_name):

        if self.settings["ctlGrp"]:
            ctlGrp = self.settings["ctlGrp"]
        else:
            ctlGrp = "controllers"

        self.addToGroup(obj, group_name, parentGrp=ctlGrp)

    def _selectNearestCvIndex(self, crv, pos):

        cvs = crv.getCVs(space="world")
        min_dist = 9999999999
        nearest = None
        for i, cv in enumerate(cvs):
            dist = (pos - cv).length()
            if dist < min_dist:
                min_dist = dist
                nearest = i

        return nearest

    def _addCurveDetailControllers(self, t, crv, detailCrv, name, skipHeadAndTail=False):

        controls = []
        npos = []
        aim_npos = []

        cvs = crv.getCVs(space="world")
        crv_info = node.createCurveInfoNode(detailCrv)

        if self.negate:
            pass
            # cvs = [cv for cv in reversed(cvs)]

        # aim constrain targets and joints
        icon_shape = "sphere"
        color = 4
        wd = .3
        offset = self.offset * 0.1

        for i, cv in enumerate(cvs):

            if skipHeadAndTail and i == 0:
                continue

            if skipHeadAndTail and (i == len(cvs) - 1):
                continue

            nearestCvId = self._selectNearestCvIndex(detailCrv, cv)

            # aim targets
            trn_name = self.getName("{}_aimTarget{}".format(name, i))
            trn = primitive.addTransformFromPos(self.eyeTargets_root, trn_name, pos=cv)

            # connecting positions with crv
            pm.connectAttr(crv_info + ".controlPoints[%s]" % str(nearestCvId), trn.attr("translate"))

            # joints
            xform = setMatrixPosition(t, self.bboxCenter)
            npo_name = self.getName("{}{}_jnt_base".format(name, str(i)))
            aim_npo = addTransform(self.jnt_root, npo_name, xform)
            applyop.aimCns(aim_npo, trn, axis="zy", wupObject=self.jnt_root)
            aim_npos.append(aim_npo)

            xform = setMatrixPosition(t, cv)

            npo_name = self.getName("{}{}_jnt_npo".format(name, str(i)))
            npo = addTransform(aim_npo, npo_name, xform)

            ctl_name = "%s_crvdetail%s_%s" % (name, i, self.ctlName)
            ctl = self.addCtl(
                npo,
                ctl_name,
                xform,
                color,
                icon_shape,
                w=wd,
                d=wd,
                ro=datatypes.Vector(1.57079633, 0, 0),
                po=offset * 0.3
            )

            self.addToSubGroup(ctl, self.detailControllersGroupName)
            controls.append(ctl)
            npos.append(npo)

            jnt_name = "{}{}".format(name, i)
            self.jnt_pos.append([ctl, jnt_name])

        return controls, npos, aim_npos

    def addWires(self):
        # adding wires
        self.w1 = pm.wire(self.upCrv, w=self.upBlink)[0]
        self.w2 = pm.wire(self.lowCrv, w=self.lowBlink)[0]

        # WIP: adding curve param cns
        # curve.applyCurveParamCns(self.upBlink, self.upCrv)
        # curve.applyCurveParamCns(self.lowBlink, self.lowCrv)

        self.w3 = pm.wire(self.upTarget, w=self.upCrv_ctl)[0]
        self.w4 = pm.wire(self.lowTarget, w=self.lowCrv_ctl)[0]

        for wire in (self.w1, self.w2, self.w3, self.w4):
            wire.attr("dropoffDistance[0]").set(self.size)
            wire.attr("dropoffDistance[1]").set(self.size)

        # adding blendshapes
        self.bs_upBlink  = pm.blendShape(self.upTarget, self.lowTarget, self.upBlink, n=self.getName("blendShapeUpBlink"))
        self.bs_lowBlink = pm.blendShape(self.lowTarget, self.upTarget, self.lowBlink, n=self.getName("blendShapeLowBlink"))

        # setting blendshape reverse connections
        rev_node = pm.createNode("reverse")
        pm.connectAttr(self.bs_upBlink[0].attr(self.lowTarget.name().split("|")[-1]), rev_node + ".inputX")
        pm.connectAttr(rev_node + ".outputX", self.bs_upBlink[0].attr(self.upTarget.name().split("|")[-1]))

        rev_node = pm.createNode("reverse")
        rev_nodeLower = pm.createNode("reverse")
        pm.connectAttr(self.bs_lowBlink[0].attr(self.upTarget.name().split("|")[-1]), rev_node + ".inputX")
        pm.connectAttr(rev_node + ".outputX", self.bs_lowBlink[0].attr(self.lowTarget.name().split("|")[-1]))

        rev_node = pm.createNode("reverse")
        pm.connectAttr(self.bs_lowBlink[0].attr(self.upTarget.name().split("|")[-1]), rev_node + ".inputX")
        pm.connectAttr(self.bs_upBlink[0].attr(self.lowTarget.name().split("|")[-1]), rev_nodeLower + ".inputX")

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

        # shortcuts
        addAttrNonAnim = functools.partial(
                attribute.addAttribute,
                minValue=0,
                maxValue=1,
                keyable=False,
                channelBox=False
        )

        # Adding and connecting attributes for the blinks
        self.blink_att = self.addAnimParam("blink" + self.side, "Blink", "float", 0, minValue=0, maxValue=1)
        self.blinkMult_att = self.addAnimParam("blinkMult", "Blink Multiplyer", "float", 1, minValue=1, maxValue=2)
        self.blinkUpper_att = addAttrNonAnim(self.blink_upper_ctl, "upperBlink", "float", value=0, minValue=-1.0, maxValue=1.0)
        self.blinkLower_att = addAttrNonAnim(self.blink_upper_ctl, "lowerBlink", "float", value=0, minValue=-1.0, maxValue=1.0)
        # self.midBlinkH_att = addAttrNonAnim(self.blink_upper_ctl, "blinkHeight", "float", value=self.blinkH)

        height = (self.upPos - self.lowPos).length()
        invHeight = 1.0 / height

        # Add blink + upper and blink + lower so animator can use both.
        # But also clamp them so using both doesn't exceed 1.0
        blinkAdd = pm.createNode("plusMinusAverage")
        blinkClamp = pm.createNode("clamp")
        blinkClamp.maxR.set(1.0)
        blinkClamp.maxG.set(1.0)
        self.blink_att.connect(blinkAdd.input2D[0].input2Dx)
        self.blink_att.connect(blinkAdd.input2D[0].input2Dy)
        self.blinkUpper_att.connect(blinkAdd.input2D[1].input2Dx)
        self.blinkLower_att.connect(blinkAdd.input2D[1].input2Dy)

        # calculate mid blink height: (height + low - hi) / (height * 2.0)
        self.upHeightRatio = pm.createNode("multiplyDivide")
        self.upHeightRatio.operation.set(1)  # mult
        self.upHeightRatio.input1X.set(invHeight)
        self.blink_upper_ctl.attr("translateY").connect(self.upHeightRatio.input2X)

        self.loHeightRatio = pm.createNode("multiplyDivide")
        self.loHeightRatio.operation.set(1)  # mult
        self.loHeightRatio.input1X.set(invHeight)
        self.blink_lower_ctl.attr("translateY").connect(self.loHeightRatio.input2X)

        pm.connectAttr(self.upHeightRatio + ".outputX", self.bs_upBlink[0].attr(self.lowTarget.name()))
        pm.connectAttr(self.loHeightRatio + ".outputX", self.bs_lowBlink[0].attr(self.upTarget.name()))

    def addEyeTrackingAttributes(self):

        height = (self.upPos - self.lowPos).length()

        def add(name, blinkCrv, upDefault, lowDefault, hDefault):
            cap = name.capitalize()
            vTrackingUp_att = self.addAnimParam("vTracking{}Up".format(cap), "Lookat Tracking Vertical {} Upper".format(cap), "float", upDefault, minValue=0, maxValue=1)
            vTrackingLow_att = self.addAnimParam("vTracking{}Low".format(cap), "Lookat Tracking Vertical {} Lower".format(cap), "float", lowDefault, minValue=0, maxValue=1)
            hTracking_att = self.addAnimParam("hTracking{}".format(cap), "Lookat Tracking Horizontal {}".format(cap), "float", hDefault, minValue=0, maxValue=1)

            # get num edit points
            numPoints = pm.getAttr(blinkCrv + ".controlPoints", size=True)
            crvShape = blinkCrv.getShape()
            add1 = pm.createNode("addDoubleLinear")
            add2 = pm.createNode("addDoubleLinear")
            add3 = pm.createNode("addDoubleLinear")
            pm.connectAttr("{}.editPoints[{}].yValueEp".format(crvShape, int(numPoints / 2)), add1 + ".input1")
            pm.connectAttr("{}.translateY".format(blinkCrv), add1 + ".input2")

            pm.connectAttr(add1 + ".output", add2 + ".input1")
            # pm.connectAttr("pupil_L0_proj_cns_slideDriven.translateY", add2 + ".input2")

            pm.connectAttr(add2 + ".output", add3 + ".input1")
            pm.setAttr(add3 + ".input2", pm.getAttr(add1 + ".output"))

            cond = pm.createNode("condition")
            pm.connectAttr(add3 + ".output", cond + ".firstTerm")
            pm.setAttr(cond + ".secondTerm", 0)
            pm.setAttr(cond + ".operation", 2)  # greater than

            mult_node = pm.createNode("multiplyDivide")
            pm.setAttr(mult_node + ".input2X", height * 0.3)
            pm.connectAttr(vTrackingUp_att, mult_node + ".input1X")
            pm.connectAttr(mult_node + ".outputX", cond + ".colorIfTrueR")

            mult_node = pm.createNode("multiplyDivide")
            pm.setAttr(mult_node + ".input2X", height * 0.3)
            pm.connectAttr(vTrackingLow_att, mult_node + ".input1X")
            pm.connectAttr(mult_node + ".outputX", cond + ".colorIfFalseR")

            # mult_node = node.createMulNode(cond + ".outColorR", self.aimTrigger_ref.attr("ty"))
            pm.connectAttr(mult_node + ".outputX", self.trackLvl[0].attr("ty"))
            pm.connectAttr(mult_node + ".outputX", self.trackLvl[0].attr("tx"))

        # add("up", self.upBlink, self.upperVTrackUp, self.upperVTrackLow, self.upperHTrack)
        # return

        # Adding channels for eye tracking
        # self.blink_att = self.addAnimParam("blink" + self.side, "Blink", "float", 0, minValue=0, maxValue=1)
        self.upVTrackingUp_att = self.addAnimParam("vTrackingUpUp", "Lookat Tracking Vertical Up Upper", "float", self.upperVTrackUp, minValue=0, maxValue=1)
        self.upVTrackingLow_att = self.addAnimParam("vTrackingUpLow", "Lookat Tracking Vertical Up Lower", "float", self.upperVTrackLow, minValue=0, maxValue=1)
        self.upHTracking_att = self.addAnimParam("hTrackingUp", "Lookat Tracking Horizontal Up", "float", self.upperHTrack, minValue=0, maxValue=1)

        self.lowVTrackingUp_att = self.addAnimParam("vTrackingLowUp", "Lookat Tracking Vertical Low Upper", "float", self.lowerVTrackUp, minValue=0, maxValue=1)
        self.lowVTrackingLow_att = self.addAnimParam("vTrackingLowLow", "Lookat Tracking Vertical Low Lower", "float", self.lowerVTrackLow, minValue=0, maxValue=1)
        self.lowHTracking_att = self.addAnimParam("hTrackingLow", "Lookat Tracking Horizontal Low", "float", self.lowerHTrack, minValue=0, maxValue=1)

        height = (self.upPos - self.lowPos).length()

        cond_up_or_low = pm.createNode("condition")
        pm.connectAttr(self.aimTrigger_ref.attr("ty"), cond_up_or_low + ".firstTerm")
        pm.setAttr(cond_up_or_low + ".secondTerm", 0)
        pm.setAttr(cond_up_or_low + ".operation", 2)  # greater than

        mult_node = pm.createNode("multiplyDivide")
        pm.setAttr(mult_node + ".input2X", height * 0.3)
        pm.connectAttr(self.upVTrackingUp_att, mult_node + ".input1X")
        pm.connectAttr(mult_node + ".outputX", cond_up_or_low + ".colorIfTrueR")

        mult_node = pm.createNode("multiplyDivide")
        pm.setAttr(mult_node + ".input2X", height * 0.3)
        pm.connectAttr(self.upVTrackingLow_att, mult_node + ".input1X")
        pm.connectAttr(mult_node + ".outputX", cond_up_or_low + ".colorIfFalseR")

        mult_node = node.createMulNode(cond_up_or_low + ".outColorR", self.aimTrigger_ref.attr("ty"))
        pm.connectAttr(mult_node + ".outputX", self.trackLvl[0].attr("ty"))
        mult_node = node.createMulNode(self.upHTracking_att, self.aimTrigger_ref.attr("tx"))

        # Correct right side horizontal tracking
        if self.negate:
            pass
            # mult_node = node.createMulNode(mult_node.attr("outputX"), -1)

        pm.connectAttr(mult_node + ".outputX", self.trackLvl[0].attr("tx"))

        cond_up_or_low = pm.createNode("condition")
        pm.connectAttr(self.aimTrigger_ref.attr("ty"), cond_up_or_low + ".firstTerm")
        pm.setAttr(cond_up_or_low + ".secondTerm", 0)
        pm.setAttr(cond_up_or_low + ".operation", 2)  # greater than

        mult_node = pm.createNode("multiplyDivide")
        pm.setAttr(mult_node + ".input2X", height * 0.3)
        pm.connectAttr(self.lowVTrackingUp_att, mult_node + ".input1X")
        pm.connectAttr(mult_node + ".outputX", cond_up_or_low + ".colorIfTrueR")

        mult_node = pm.createNode("multiplyDivide")
        pm.setAttr(mult_node + ".input2X", height * 0.3)
        pm.connectAttr(self.lowVTrackingLow_att, mult_node + ".input1X")
        pm.connectAttr(mult_node + ".outputX", cond_up_or_low + ".colorIfFalseR")

        mult_node = node.createMulNode(cond_up_or_low + ".outColorR", self.aimTrigger_ref.attr("ty"))
        pm.connectAttr(mult_node + ".outputX", self.trackLvl[1].attr("ty"))
        mult_node = node.createMulNode(self.lowHTracking_att, self.aimTrigger_ref.attr("tx"))

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
        blinkAdd = pm.createNode("plusMinusAverage")
        blinkClamp = pm.createNode("clamp")
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

    def connect_standard(self):

        self.parent.addChild(self.root)
        if self.connect_surface_slider and self.surfRef:
            ref = self.rig.findComponent(self.surfRef)
            self.sliding_surface = ref.sliding_surface

        if self.connect_surface_slider:
            try:
                # TODO: extract conditions to a settings dictionary
                if False:
                    self.connect_slide_ghost()
                else:
                    self.connect_detail_controller_to_slide_ghost()

            except Exception as _:
                import traceback
                traceback.print_exc()

    def connect_pupil(self):
        try:
            self.connect_standard()
        except Exception as _:
            import traceback
            traceback.print_exc()

        lookat = self.rig.findRelative("pupil_{}0_lookat".format(self.side))
        if not lookat:
            print("error: pupil_{}0_lookat not found".format(self.side))
            raise Exception("pupil_{}0_lookat not found".format(self.side))

        _cns_node = cmds.aimConstraint(lookat.getName(), self.arrow_npo.getName(), maintainOffset=True)[0]  # type: ignore
        cmds.setAttr(_cns_node + ".worldUpType", 2)  # 2 means object rotation up
        cmds.setAttr(_cns_node + ".worldUpVector", 0, 1, 0)
        cmds.connectAttr(
            lookat.getName() + ".worldMatrix[0]",
            _cns_node + ".worldUpMatrix",
            force=True
        )

    def connect_slide_ghost(self):

        upGhostControls = []
        lowGhostControls = []
        upPositions = []
        lowPositions = []

        for i, ctl in enumerate(self.upControls):
            ghost = self._connect_slide_ghost(ctl, i)
            upGhostControls.append(ghost)
            upPositions.append(getTransform(ghost))

        relativeUpPositions = [x.translate - self.rootPos for x in upPositions]

        for i, ctl in enumerate(self.lowControls):
            ghost = self._connect_slide_ghost(ctl, i)
            lowGhostControls.append(ghost)
            lowPositions.append(getTransform(ghost))
        relativeLowPositions = [x.translate - self.rootPos for x in lowPositions]

        root, crvs = self.addCurves(relativeUpPositions, relativeLowPositions)
        self.upCrv = crvs[0]
        self.lowCrv = crvs[1]
        self.upCrv_ctl = crvs[2]
        self.lowCrv_ctl = crvs[3]
        self.upBlink = crvs[4]
        self.lowBlink = crvs[5]
        self.upTarget = crvs[6]
        self.lowTarget = crvs[7]

        curve.gear_curvecns_op_local(self.upCrv_ctl, upGhostControls)
        curve.gear_curvecns_op_local(self.lowCrv_ctl, lowGhostControls)

        self.addWires()
        pm.connectAttr(self.upHeightRatio + ".outputX", self.bs_upBlink[0].attr(self.lowTarget.name().split("|")[-1]))
        pm.connectAttr(self.loHeightRatio + ".outputX", self.bs_lowBlink[0].attr(self.upTarget.name().split("|")[-1]))

        # rebind DetailControls
        bt = transform.getTransform(self.root)
        self.detail_root = addTransform(self.root, self.getName("detail_ctls"), bt)

        for i, npo in enumerate(self.upDetailNpos):
            tra = transform.getTransform(npo)
            adj = addTransform(self.detail_root, self.getName("detail{}_adj".format(str(i))), tra)
            cns = curve.applyPathConstrainLocal(adj, self.upCrv)

            ymt_util.setKeyableAttributesDontLockVisibility(npo, ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "ro"])
            npo.setParent(adj, absolute=True)
            aim = self.upDetailAimNpos[i]
            pm.aimConstraint(aim, npo, maintainOffset=True)

            ymt_util.setKeyableAttributesDontLockVisibility(npo, [])

        for i, npo in enumerate(self.lowDetailNpos):
            tra = transform.getTransform(npo)
            adj = addTransform(self.detail_root, self.getName("detail{}_adj".format(str(i))), tra)
            cns = curve.applyPathConstrainLocal(adj, self.lowCrv)

            ymt_util.setKeyableAttributesDontLockVisibility(npo, ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "ro"])
            npo.setParent(adj, absolute=True)
            aim = self.lowDetailAimNpos[i]
            pm.aimConstraint(aim, npo, maintainOffset=True)

            ymt_util.setKeyableAttributesDontLockVisibility(npo, [])

        pm.delete(self.crvroot)

    def _connect_slide_ghost(self, surfaceCtl, index):

        # create ghost controls
        ghostCtl = ghost.createGhostCtl(surfaceCtl, self.slider_root)
        ghostCtl.rename(self.getName("{}_ghost".format(index)))
        shapes = cmds.listRelatives(ghostCtl.fullPathName(), shapes=True)
        cmds.delete(shapes)

        oParent = ghostCtl.getParent()
        npoName = "_".join(ghostCtl.name().split("_")[:-1]) + "{}_npo".format(index)
        npo = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))
        npo.addChild(ghostCtl)

        ghostCtl.attr("isCtl") // surfaceCtl.attr("isCtl")  # pyright: ignore [reportUnusedExpression]        ghostCtl.attr("translate") // surfaceCtl.attr("translate")
        ghostCtl.attr("rotate") // surfaceCtl.attr("rotate")  # pyright: ignore [reportUnusedExpression]
        ghostCtl.attr("scale") // surfaceCtl.attr("scale")  # pyright: ignore [reportUnusedExpression]
        ymt_util.setKeyableAttributesDontLockVisibility(npo, [])
        ymt_util.setKeyableAttributesDontLockVisibility(ghostCtl, [])
        cmds.deleteAttr(ghostCtl.fullPathName(), attribute="isCtl")

        surfaceCtl.rename(self.getName("{}_ctl".format(index)))

        ctl = pm.listConnections(ghostCtl, t="transform")[-1]
        ghostCtl.attr("translate") // surfaceCtl.attr("translate")  # pyright: ignore [reportUnusedExpression]        ghostCtl.attr("translate") // surfaceCtl.attr("translate")

        t = ctl.getMatrix(worldSpace=True)

        oParent = ghostCtl.getParent()
        npoName = "_".join(ghostCtl.name().split("_")[:-1]) + "_npo"
        npo = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))
        npo.setTransformation(ghostCtl.getMatrix())
        ymt_util.setKeyableAttributesDontLockVisibility(npo, [])

        pm.parent(ghostCtl, npo)

        slider = primitive.addTransform(
                self.sliding_surface.getParent(),
                ctl.name() + "_slideDriven",
                t)

        down, _, up = ymt_util.findPathAtoB(ctl, self.sliding_surface.getParent())
        mul_node = pm.createNode("multMatrix")
        j = k = 0
        for j, d in enumerate(down):
            d.attr("matrix") >> mul_node.attr("matrixIn[{}]".format(j))  # pyright: ignore [reportUnusedExpression]
        for k, u in enumerate(up):
            u.attr("inverseMatrix") >> mul_node.attr("matrixIn[{}]".format(k + j + 1))  # pyright: ignore [reportUnusedExpression]

        dm_node = node.createDecomposeMatrixNode(mul_node.attr("matrixSum"))

        cps_node = pm.createNode("closestPointOnSurface")
        dm_node.attr("outputTranslate") >> cps_node.attr("inPosition")  # pyright: ignore [reportUnusedExpression]
        surfaceShape = self.sliding_surface.getShape()
        surfaceShape.attr("local") >> cps_node.attr("inputSurface")  # pyright: ignore [reportUnusedExpression]
        cps_node.attr("position") >> slider.attr("translate")  # pyright: ignore [reportUnusedExpression]

        if self.negate:
            aim = [0, 0, -1]
        else:
            aim = [0, 0, 1]
        pm.normalConstraint(surfaceShape,
                            slider,
                            aimVector=aim,
                            upVector=[0, 1, 0],
                            worldUpType="objectrotation",
                            worldUpVector=[0, 1, 0],
                            worldUpObject=self.root)
        pm.parent(ghostCtl.getParent(), slider)
        # self.removeFromControllerGroup(ghostCtl)

        # self.setRelation()  # MUST re-setRelation, swapped ghost and real controls
        return ghostCtl

    def connect_detail_controller_to_slide_ghost(self):

        for i, ctl in enumerate(self.upDetailControllers):
            self._connect_slide_ghost2(ctl, "upEyelid_crvdetail" + str(i))

        for i, ctl in enumerate(self.lowDetailControllers):
            self._connect_slide_ghost2(ctl, "lowEyelid_crvdetail" + str(i))

    def _connect_slide_ghost2(self, surfaceCtl, index):

        # create ghost controls
        t = surfaceCtl.getMatrix(worldSpace=True)
        slider = primitive.addTransform(
                self.sliding_surface.getParent(),
                surfaceCtl.name() + "_slideDriven",
                t)

        slideNpo = primitive.addTransform(
                surfaceCtl.getParent(),
                surfaceCtl.name() + "_slideNpo",
                t)

        down, _, up = ymt_util.findPathAtoB(surfaceCtl.getParent(), self.sliding_surface.getParent())
        mul_node = pm.createNode("multMatrix")
        j = k = 0
        for j, d in enumerate(down):
            d.attr("matrix") >> mul_node.attr("matrixIn[{}]".format(j))  # pyright: ignore [reportUnusedExpression]
        for k, u in enumerate(up):
            u.attr("inverseMatrix") >> mul_node.attr("matrixIn[{}]".format(k + j + 1))  # pyright: ignore [reportUnusedExpression]

        dm_node = node.createDecomposeMatrixNode(mul_node.attr("matrixSum"))

        cps_node = pm.createNode("closestPointOnSurface")
        dm_node.attr("outputTranslate") >> cps_node.attr("inPosition")  # pyright: ignore [reportUnusedExpression]
        surfaceShape = self.sliding_surface.getShape()
        surfaceShape.attr("local") >> cps_node.attr("inputSurface")  # pyright: ignore [reportUnusedExpression]
        cps_node.attr("position") >> slider.attr("translate")  # pyright: ignore [reportUnusedExpression]

        if self.negate:
            aim = [0, 0, -1]
        else:
            aim = [0, 0, 1]
        pm.normalConstraint(surfaceShape,
                            slider,
                            aimVector=aim,
                            upVector=[0, 1, 0],
                            worldUpType="objectrotation",
                            worldUpVector=[0, 1, 0],
                            worldUpObject=self.root)
        pm.parentConstraint(slider, slideNpo, mo=True)
        cmds.parent(surfaceCtl.getName(), slideNpo.getName())

        ymt_util.setKeyableAttributesDontLockVisibility(slideNpo, [])
        ymt_util.setKeyableAttributesDontLockVisibility(slider, [])

    # =====================================================
    # CONNECTOR
    # =====================================================
    def addConnection(self):
        self.connections["standard"] = self.connect_standard
        self.connections["pupil_01"] = self.connect_pupil

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.over_ctl

        for i, ctl in enumerate(self.upDetailControllers):

            self.relatives["%s_uploc" % i] = ctl
            self.controlRelatives["%s_uploc" % i] = ctl

        for i, ctl in enumerate(self.lowDetailControllers):

            self.relatives["%s_lowloc" % i] = ctl
            self.controlRelatives["%s_lowloc" % i] = ctl

        self.relatives["inloc"] = self.upDetailControllers[0]
        self.relatives["outloc"] = self.upDetailControllers[-1]


if __name__ == "__main__":
    pass
