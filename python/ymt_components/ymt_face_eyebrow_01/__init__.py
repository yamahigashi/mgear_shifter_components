"""mGear shifter components"""
# pylint: disable=import-error,W0201,C0111,C0112
import re
import sys
import math

import maya.cmds as cmds
import maya.api.OpenMaya as om

try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm
try:
    from mgear.pymaya import datatypes
except ImportError:
    from pymel.core import datatypes

from mgear.shifter import component
from mgear.rigbits.facial_rigger import helpers
from mgear.rigbits.facial_rigger import constraints
from mgear.rigbits import ghost
from mgear.rigbits import addNPO

from mgear.core import (
    transform,
    applyop,
    node,
    primitive,
)

from mgear.core.transform import (
    getTransform,
)

from mgear.core.primitive import (
    addTransform,
)
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
        from pathlib import Path  # NOQA: F401, F811 pylint: disable=unused-import,reimported
        from types import ModuleType  # NOQA: F401 pylint: disable=unused-import
        from six.moves import reload_module as reload  # NOQA: F401 pylint: disable=unused-import

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
        self.detailControllersGroupName = "controllers_detail"  # TODO: extract to settings
        self.primaryControllersGroupName = "controllers_primary"  # TODO: extract to settings

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
        self.num_uplocs = self.getNumberOfLocators("_loc")

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
        self.addCurves(self.crv_root)
        self.addRope()
        self.attachSecondaryControlsToMainCurve()
        self.connectWires()

        self.surfRef = self.settings["surfaceReference"]
        if not self.surfRef:
            self.sliding_surface = pm.duplicate(self.guide.getObjects(self.guide.root)["sliding_surface"])[0]
            pm.parent(self.sliding_surface.name(), self.root)
            self.sliding_surface.visibility.set(False)
            pm.makeIdentity(self.sliding_surface, apply=True, t=1,  r=1, s=1, n=0, pn=1)

    def _visi_off_lock(self, node):
        """Short cuts."""
        node.visibility.set(False)
        ymt_util.setKeyableAttributesDontLockVisibility(node, [])
        cmds.setAttr("{}.visibility".format(node.name()), l=False)

    def addContainers(self):

        t = getTransform(self.root)
        scl = [1, 1, 1]
        if self.negate:
            scl = [-1, 1, 1]
        t = transform.setMatrixScale(t, scl)

        self.crv_root = addTransform(self.root, self.getName("crvs"), t)
        self.rope_root = addTransform(self.root, self.getName("ropes"), t)
        self.browsHooks_root = addTransform(self.root, self.getName("hooks"), t)

        self._visi_off_lock(self.crv_root)
        self._visi_off_lock(self.rope_root)
        self._visi_off_lock(self.browsHooks_root)

        if self.connect_surface_slider:
            bt = getTransform(self.root)
            self.slider_root = addTransform(self.root, self.getName("sliders"), bt)
            ymt_util.setKeyableAttributesDontLockVisibility(self.slider_root, [])

        # self.mainControlParentGrp = addTransform(self.root, self.getName("mainControls"), t)
        w = (self.outPos - self.inPos).length()
        d = (self.upPos - self.lowPos).length()
        po_x = ((self.inPos - self.rootPos).x * 0.4 + (w * self.n_factor / 2.0)) * self.n_factor
        po_y = ((self.upPos + self.outPos) / 2.0 - self.rootPos).y + (d / 2.0)

        self.mainControlParentGrp = addTransform(self.root, self.getName("mainControls"), t)
        self.mainControl = self.addCtl(
                self.mainControlParentGrp,
                "main_ctl",
                t,
                self.color_ik,
                "square",
                w=w,
                d=d,
                ro=datatypes.Vector(1.57079633, 0, 0),
                po=datatypes.Vector(po_x, po_y, 1.0)
        )
        self.addToSubGroup(self.mainControl, self.primaryControllersGroupName)
        self.secondaryControlsParentGrp = addTransform(self.root, self.getName("secondaryControls"), t)

    def getNumberOfLocators(self, query):
        # type: (Text) -> int
        num = 0
        for k, v in self.guide.tra.items():
            if query in k:
                index = int(re.search(r"^(\d+)", k).group(1))
                num = max(num, index + 1)

        return num

    def addCurves(self, crv_root):

        t = getTransform(self.root)
        points = [x - self.root.getTranslation(space="world") for x in self.uplocsPos]

        name = "main_crv"
        crv = curve.addCurve(
            self.crv_root,
            self.getName(name),
            points,
            m=t
        )

        crv.attr("visibility").set(False)
        ymt_util.setKeyableAttributesDontLockVisibility(crv, [])

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
            ctl, upv = self._foreachControlOption(self.mainControl, ctlOptions)
            self.mainControls.append(ctl)
            self.mainUpvs.append(upv)
        self.reparentControls()
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
        scl = [1, 1, 1]
        if self.negate:
            scl = [-1, 1, 1]
        t = transform.setMatrixScale(position, scl)
        npo = addTransform(controlParentGrp, self.getName("%s_npo" % oName, oSide), t)
        npoBuffer = addTransform(npo, self.getName("%s_bufferNpo" % oName, oSide), t)

        # Create casual control
        if o_icon != "npo":
            if o_icon == "sphere":
                rot_offset = None
            else:
                rot_offset = datatypes.Vector(1.57079633, 0, 0)

            ctl = self.addCtl(
                npoBuffer,
                "{}_ctl".format(oName),
                t,
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
                t)

        # Create up vectors for each control
        upv = addTransform(ctl, self.getName("%s_upv" % oName, oSide), t)
        upv.attr("tz").set(self.FRONT_OFFSET)

        return ctl, upv

    def addMainCnsCurve(self, ctls):
        crv_degree = 2

        t = getTransform(self.root)
        crv = curve.addCnsCurve(
                self.crv_root,
                self.getName("mainCtl_crv"),
                ctls,
                degree=crv_degree,
                m=t,
                local=True)
        deformer = crv.getShape().attr("create").inputs()[0]

        ymt_util.setKeyableAttributesDontLockVisibility(crv, [])
        v = self.root.getTranslation(space="world")
        crv.setTranslation(v, om.MSpace.kWorld)
        self.mainCtlCurves.append(crv)

        # create upvector curve to drive secondary control
        if self.secondary_ctl_check:
            points = [ctl.getTranslation(space="world") for ctl in ctls]
            mainCtlUpv = curve.addCurve(self.crv_root, self.getName("mainCtl_upv"), points, degree=crv_degree, m=t)
            ymt_util.setKeyableAttributesDontLockVisibility(mainCtlUpv, [])
            v = self.root.getTranslation(space="world")
            mainCtlUpv.setTranslation(v, om.MSpace.kWorld)
            # connect upv curve to mainCrv_ctl driver node.
            pm.connectAttr(deformer.attr("outputGeometry[0]"), mainCtlUpv.getShape().attr("create"))

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

        t = getTransform(self.root)
        crv = curve.addCnsCurve(
                self.crv_root,
                self.getName("secCtl_crv"),
                ctls,
                crv_degree,
                m=t,
                local=True)
        ymt_util.setKeyableAttributesDontLockVisibility(crv, [])
        v = self.root.getTranslation(space="world")
        crv.setTranslation(v, om.MSpace.kWorld)

        self.secondaryCurves.append(crv)
        self.rigCurves.append(crv)

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

    def attachSecondaryControlsToMainCurve(self):

        secControlsMerged = []
        tempMainCtlCurves = self.mainCtlCurves
        tempMainUpvCurves = self.mainCtlUpvs
        secControlsMerged.append(self.secondaryControls)

        for secCtl in self.secondaryControls:
            constraints.matrixConstraint(self.root, secCtl.getParent(2), 'rs', True)

        # create hooks on the main ctl curve
        for j, crv in enumerate(self.secondaryCurves):

            lvlType = "transform"
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

    def addToSubGroup(self, obj, group_name):

        if self.settings["ctlGrp"]:
            ctlGrp = self.settings["ctlGrp"]
        else:
            ctlGrp = "controllers"

        self.addToGroup(obj, group_name, parentGrp=ctlGrp)

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        if not self.settings["ui_host"]:
            self.uihost = self.mainControl

        self.follow_lookat_threshold_x_attr = self.addAnimParam(
                "lookat_threshold_x", "LookAt threshold X", "double", 90.0, 0.0001, 179.9999)
        self.follow_lookat_threshold_y_attr = self.addAnimParam(
                "lookat_threshold_y", "LookAt threshold Y", "double", 36.0, 0.0001, 179.9999)

        self.follow_lookat_0_x_attr = self.addAnimParam("lookat_0_x", "LookAt inner X", "double", 0.010, 0, 1)
        self.follow_lookat_1_x_attr = self.addAnimParam("lookat_1_x", "LookAt mid X", "double", 0.020, 0, 1)
        self.follow_lookat_2_x_attr = self.addAnimParam("lookat_2_x", "LookAt out X", "double", 0.013, 0, 1)
        self.follow_lookat_0_y_attr = self.addAnimParam("lookat_0_y", "LookAt inner Y", "double", 0.066, 0, 1)
        self.follow_lookat_1_y_attr = self.addAnimParam("lookat_1_y", "LookAt mid Y", "double", 0.133, 0, 1)
        self.follow_lookat_2_y_attr = self.addAnimParam("lookat_2_y", "LookAt out Y", "double", 0.059, 0, 1)

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
        if self.surfRef:
            ref = self.rig.findComponent(self.surfRef)
            self.sliding_surface = ref.sliding_surface

        if self.connect_surface_slider:
            try:
                self.connect_slide_ghost()

            except Exception as _:
                import traceback
                traceback.print_exc()

        if self.settings["addJoints"]:
            self.jnt_pos.append([self.mainControl, "main"])
            for i, ctl in enumerate(self.secondaryControls):
                self.jnt_pos.append([ctl, str(i).zfill(2)])

        if True:
            try:
                self.connect_eyelookat()
            except Exception as _:
                import traceback
                traceback.print_exc()
                raise

    def connect_eyelookat(self):
        attrsX = [
            self.follow_lookat_0_x_attr,
            self.follow_lookat_1_x_attr,
            self.follow_lookat_2_x_attr,
        ]
        attrsY = [
            self.follow_lookat_0_y_attr,
            self.follow_lookat_1_y_attr,
            self.follow_lookat_2_y_attr,
        ]
        self.connect_eyelookat_axis(self.follow_lookat_threshold_x_attr, "translateX", -1.0,1.0, attrsX)
        self.connect_eyelookat_axis(self.follow_lookat_threshold_y_attr, "translateY", 0.0, 1.0, attrsY)

    def connect_eyelookat_axis(self, threshold_attr, attr, clamp_neg, clamp_pos, attrs):

        eye_comp = self.rig.findComponent("eye_{}0_root".format(self.side))
        aim = eye_comp.aimTrigger_ref
        radius = abs(eye_comp.arrow_npo.attr("translateZ").get())

        # base = radius * math.sin(0.5 * math.pi * 0.4)  # in degree 36 
        # sin = pm.createNode("sin")  # this node is in degree... not radian
        deg2rad_mul = pm.createNode("multiplyDivide")
        deg2rad_mul.operation.set(1)  # multiply
        deg2rad_mul.input2X.set(math.pi / 180.0)
        threshold_attr.connect(deg2rad_mul.input1X)

        mult = pm.createNode("multiplyDivide")
        mult.operation.set(1)  # multiply
        mult.input1X.set(radius)
        deg2rad_mul.outputX.connect(mult.input2X)

        # avoid zero division
        cond = pm.createNode("condition")
        pm.setAttr(cond + ".colorIfTrueR", 0.0001)
        pm.connectAttr(mult + ".outputX", cond + ".firstTerm")
        pm.setAttr(cond + ".secondTerm", 0)
        pm.setAttr(cond + ".operation", 0)  # equal
        pm.connectAttr(mult + ".outputX", cond + ".colorIfFalseR")

        # smoothstep 3x^2 - 2x^3
        div = pm.createNode("multiplyDivide")
        div.operation.set(2)  # divide
        aim.attr(attr).connect(div.input1X)
        cond.outColorR.connect(div.input2X)
        # mult.outputX.connect(div.input2X)

        clamp = pm.createNode("clamp")
        clamp.minR.set(clamp_neg)
        clamp.maxR.set(clamp_pos)
        div.outputX.connect(clamp.inputR)

        # 3x^2 = A
        pow2 = pm.createNode("multiplyDivide")
        pow2.operation.set(3)  # power
        clamp.outputR.connect(pow2.input1X)
        pow2.input2X.set(2)
        mult3 = pm.createNode("multiplyDivide")
        mult3.operation.set(1)  # multiply
        pow2.outputX.connect(mult3.input1X)
        mult3.input2X.set(3)

        # 2x^3 = B
        pow3 = pm.createNode("multiplyDivide")
        pow3.operation.set(3)  # pow
        clamp.outputR.connect(pow3.input1X)
        pow3.input2X.set(3)
        mult2 = pm.createNode("multiplyDivide")
        mult2.operation.set(1)  # multiply
        pow3.outputX.connect(mult2.input1X)
        clamp.outputR.connect(mult2.input2X)

        # A - B
        sub = pm.createNode("plusMinusAverage")
        sub.operation.set(2)  # subtract
        mult3.outputX.connect(sub.input1D[0])
        mult2.outputX.connect(sub.input1D[1])

        mult_res = pm.createNode("multiplyDivide")
        mult_res.operation.set(1)  # multiply
        aim.attr(attr).connect(mult_res.input1X)
        sub.output1D.connect(mult_res.input2X)

        res0 = pm.createNode("multiplyDivide")
        res1 = pm.createNode("multiplyDivide")
        res2 = pm.createNode("multiplyDivide")
        res0.operation.set(1)  # multiply
        res1.operation.set(1)  # multiply
        res2.operation.set(1)  # multiply
        mult_res.outputX.connect(res0.input1X)
        mult_res.outputX.connect(res1.input1X)
        mult_res.outputX.connect(res2.input1X)
        attrs[0].connect(res0.input2X)
        attrs[1].connect(res1.input2X)
        attrs[2].connect(res2.input2X)

        # insert npo
        npo0 = ymt_util.addNPOPreservingMatrixConnections(self.mainControls[0])[0]
        npo1 = ymt_util.addNPOPreservingMatrixConnections(self.mainControls[2])[0]
        npo2 = ymt_util.addNPOPreservingMatrixConnections(self.mainControls[4])[0]
        res0.outputX.connect(npo0.attr(attr))
        res1.outputX.connect(npo1.attr(attr))
        res2.outputX.connect(npo2.attr(attr))

    def connect_slide_ghost(self):

        # create ghost controls
        ghosts = []
        real_ctls = []
        for sec in self.secondaryControls:
            ghostCtl = ghost.createGhostCtl(sec, self.slider_root)
            ghosts.append(ghostCtl)
            ghostCtl.attr("isCtl").set(True)
            self._visi_off_lock(sec)
            self.addToSubGroup(ghostCtl, self.detailControllersGroupName)

            ghostCtl.attr("isCtl") // sec.attr("isCtl")
            ghostCtl.attr("translate") // sec.attr("translate")
            ghostCtl.attr("rotate") // sec.attr("rotate")
            ghostCtl.attr("scale") // sec.attr("scale")

            sec.attr("isCtl").set(False)
            sec.rename(sec.name().replace("ctl_ghost", "ghost"))

            if self.settings["ctlGrp"]:
                ctlGrp = self.settings["ctlGrp"]

            else:
                ctlGrp = "controllers"

            if ctlGrp not in self.groups.keys():
                self.groups[ctlGrp] = []

            try:
                self.groups[ctlGrp].remove(sec)
            except:
                pass

            real_ctls.append(ghostCtl)

        self._visi_off_lock(self.secondaryControlsParentGrp)

        # slide system
        self.ghostSliderForEyeBrow(
            ghosts,
            self.sliding_surface,
            self.sliding_surface.getParent())

        self.secondaryControls = real_ctls
        self.setRelation()  # MUST re-setRelation, swapped ghost and real controls

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.root
        self.controlRelatives["root"] = self.root
        self.aliasRelatives["root"] = "ctl"

        for i, ctl in enumerate(self.secondaryControls):

            self.relatives["%s_loc" % i] = ctl
            self.controlRelatives["%s_loc" % i] = ctl

            self.jointRelatives["%s_loc" % (i)] = (i + 1)
            self.aliasRelatives["%s_ctl" % (i)] = (i + 1)

    def ghostSliderForEyeBrow(self, ghostControls, surface, sliderParent):
        """Modify the ghost control behaviour to slide on top of a surface

        Args:
            ghostControls (dagNode): The ghost control
            surface (Surface): The NURBS surface
            sliderParent (dagNode): The parent for the slider.
        """

        if not isinstance(ghostControls, list):
            ghostControls = [ghostControls]

        surfaceShape = surface.getShape()
        sliders = []

        for i, ctlGhost in enumerate(ghostControls):
            ctl = pm.listConnections(ctlGhost, t="transform")[-1]
            t = ctl.getMatrix(worldSpace=True)
            scl = [1, 1, 1]
            if self.negate:
                scl = [-1, 1, 1]
            # t = transform.setMatrixScale(t, scl)

            gDriver = primitive.addTransform(ctlGhost.getParent(), "{}_slideDriver".format(ctl.name()), t)

            oParent = ctlGhost.getParent()
            npoName = "_".join(ctlGhost.name().split("_")[:-1]) + "_npo"
            npo = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))

            npo.setTransformation(ctlGhost.getMatrix())
            pm.parent(ctlGhost, npo, absolute=True)

            slider = primitive.addTransform(sliderParent, ctl.name() + "_slideDriven", t)
            sliders.append(slider)

            down, _, up = ymt_util.findPathAtoB(ctl, sliderParent)
            mul_node = pm.createNode("multMatrix")
            j = k = 0
            for j, d in enumerate(down):
                d.attr("matrix") >> mul_node.attr("matrixIn[{}]".format(j))
            # mid.attr("matrix") >> mul_node.attr("matrixIn[{}]".format(j + 1))
            for k, u in enumerate(up):
                u.attr("inverseMatrix") >> mul_node.attr("matrixIn[{}]".format(k + j + 1))

            dm_node = node.createDecomposeMatrixNode(mul_node.attr("matrixSum"))

            cps_node = pm.createNode("closestPointOnSurface")
            dm_node.attr("outputTranslate") >> cps_node.attr("inPosition")
            surfaceShape.attr("local") >> cps_node.attr("inputSurface")
            cps_node.attr("position") >> slider.attr("translate")

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
                                worldUpObject=gDriver)
            pm.parent(ctlGhost.getParent(), slider, absolute=True)
            pm.parent(gDriver.getParent(), self.mainControl, absolute=True)
            ymt_util.setKeyableAttributesDontLockVisibility(npo, [])


def draw_eye_guide_mesh_plane(points, t):
    # type: (Tuple[float, float, float], datatypes.Matrix) -> om.MFnMesh

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

    mesh_trans = om.MFnTransform(mesh_obj)
    n = pm.PyNode(mesh_trans.name())
    v = t.getTranslation(space="world")
    n.setTranslation(v, om.MSpace.kWorld)

    return mesh


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
