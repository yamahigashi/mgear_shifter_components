"""mGear shifter components"""
# pylint: disable=import-error,W0201,C0111,C0112
import re
import six
import sys
import math
import traceback

import maya.cmds as cmds
import maya.api.OpenMaya as om

import pymel.core as pm
from pymel.core import datatypes

from mgear import rigbits
from mgear.rigbits import ghost
from mgear.shifter import component

from mgear.core import (
    transform,
    node,
    primitive,
)

from mgear.core.transform import (
    getTransform,
    setMatrixPosition,
    setMatrixScale,
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

from logging import (  # noqa:F401 pylint: disable=unused-import, wrong-import-order
    StreamHandler,
    getLogger,
    WARN,  # noqa: F401
    DEBUG,
    INFO
)

handler = StreamHandler()
handler.setLevel(DEBUG)
logger = getLogger(__name__)
logger.setLevel(INFO)
logger.setLevel(DEBUG)
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
        self.surfRef = self.settings["surfaceReference"]
        self.mouthCenterRef = self.settings["mouthCenterReference"]
        self.mouthLeftRef = self.settings["mouthLeftReference"]
        self.mouthRightRef = self.settings["mouthRightReference"]
        # -------------------------------------------------------

        self.num_locs = self.getNumberOfLocators("_loc")
        self.frontPos = self.guide.apos[-1]
        self.rootPos = self.guide.apos[0]
        self.locsPos = self.guide.apos[2:self.num_locs + 2]

        self.offset = (self.frontPos - self.rootPos) * 0.3
        if self.negate:
            pass
            # self.offset[2] = self.offset[2] * -1.0

        # -------------------------------------------------------
        self.ctlName = "ctl"
        self.detailControllersGroupName = "controllers_detail"  # TODO: extract to settings
        self.primaryControllersGroupName = "controllers_primary"  # TODO: extract to settings

        self.thickness = 0.07
        self.FRONT_OFFSET = self.size * 0.1
        self.NB_CVS = 2 * 4 + 4  # means 4 spans with 2 controllers each + 4 controllers for the corners

        # odd / event
        if self.num_locs % 2 == 0:
            # even
            self.NB_ROPE = self.num_locs * 20 + 1
            self.bottom_index = int(self.num_locs / 2)
        else:
            self.NB_ROPE = self.num_locs * 20
            self.bottom_index = int((self.num_locs -1) / 2)

        # treat most left side as corner index
        peek_x = 0.0
        self.left_index = 0
        for i in range(0, self.bottom_index):
            if self.locsPos[i][0] > peek_x:
                peek_x = self.locsPos[i][0]
                self.left_index = i

        peek_x = 0.0
        self.right_index = 0
        for i in range(self.bottom_index, self.num_locs):
            if self.locsPos[i][0] < peek_x:
                peek_x = self.locsPos[i][0]
                self.right_index = i

        # --------------------------------------------------------
        self.crv = None
        self.crv_ctl = None

        self.previusTag = self.parentCtlTag

        self.addContainers()
        self.addCurve()
        self.addControlJoints()
        self.addControllers()
        self.addConstraints()

    def addContainers(self):

        t = getTransform(self.root)

        self.crv_root = addTransform(self.root, self.getName("crvs"), t)
        self.ctl_root = addTransform(self.root, self.getName("ctls"), t)
        self.rope_root = addTransform(self.root, self.getName("rope"), t)
        self.upv_root = addTransform(self.root, self.getName("upv"), t)

        self.crv_root.visibility.set(False)
        ymt_util.setKeyableAttributesDontLockVisibility(self.crv_root, [])
        ymt_util.setKeyableAttributesDontLockVisibility(self.ctl_root, [])
        ymt_util.setKeyableAttributesDontLockVisibility(self.rope_root, [])
        ymt_util.setKeyableAttributesDontLockVisibility(self.upv_root, [])

    def getNumberOfLocators(self, query):
        # type: (Text) -> int
        """ _uplocs."""
        num = 0
        for k, v in self.guide.tra.items():
            if query in k:
                index = int(re.search(r"^(\d+)", k).group(1))
                num = max(num, index + 1)

        return num

    def addCurve(self):

        self.addCurves(self.crv_root)
        self.addCurveBaseControllers(self.crv_root)

        if not self.surfRef:
            self.sliding_surface = pm.duplicate(self.guide.getObjects(self.guide.root)["sliding_surface"])[0]
            pm.parent(self.sliding_surface.name(), self.root)
            self.sliding_surface.visibility.set(False)
            pm.makeIdentity(self.sliding_surface, apply=True, t=1,  r=1, s=1, n=0, pn=1)

    def getCurveCVs(self, crv, space="world"):
        # type: (...) -> List[om.MPoint]

        cvs = crv.getCVs(space=space)
        degree = cmds.getAttr("{}.degree".format(crv))

        # TODO: extract to settings later
        # if self.settings["close"]:
        cvs = cvs[:len(cvs) - degree]  # closed curve goes not get cvs properly

        return cvs

    def addCurves(self, crv_root):
        m = getTransform(self.root)
        positions = [self._worldToObj(x) for x in self.locsPos]

        crv = curve.addCurve(
            crv_root,
            self.getName("crv"),
            positions,
            m=m,
            close=True
        )
        crv.attr("visibility").set(False)
        cvs = self.getCurveCVs(crv)
        center_pos = sum(cvs) / len(cvs)  # type: ignore
        for i, cv in enumerate(cvs):
            offset = (cv - center_pos).normal() * self.thickness
            new_pos = [cv[0] + offset[0], cv[1] + offset[1], cv[2] + offset[2]]
            crv.setCV(i, new_pos, space="world")
        self.crv = crv

    def addCurveBaseControllers(self, crv_root):

        t = getTransform(self.root)

        def curveFromCurve(crv, name, nbPoints):

            new_crv = curve.createCurveFromCurveEvenLength(
                crv,
                self.getName(name),
                nbPoints=nbPoints,
                parent=crv_root,
                m=t,
                close=True
            )
            new_crv.attr("visibility").set(False)

            return new_crv

        # -------------------------------------------------------------------
        self.rope = curveFromCurve(self.crv, "rope_crv", self.NB_ROPE)
        self.upv_crv = curveFromCurve(self.crv, "upv_crv", self.NB_ROPE)

        # -------------------------------------------------------------------
        posTop = self.locsPos[0]
        posLeft = self.locsPos[self.left_index]
        posBottom = self.locsPos[self.bottom_index]
        posRight = self.locsPos[self.right_index]

        posLeft = inflate_position_by_curve_flattness(self.crv, posLeft)
        posRight = inflate_position_by_curve_flattness(self.crv, posRight)

        ropeFn = curve.getMFnNurbsCurve(self.rope)
        ropeLength = ropeFn.length()

        positions = [
            posTop,
            ropeFn.getPointAtParam(ropeFn.findParamFromLength(ropeLength * 1.0 / 12.0), om.MSpace.kObject),
            ropeFn.getPointAtParam(ropeFn.findParamFromLength(ropeLength * 2.0 / 12.0), om.MSpace.kObject),
            posLeft,
            ropeFn.getPointAtParam(ropeFn.findParamFromLength(ropeLength * 4.0 / 12.0), om.MSpace.kObject),
            ropeFn.getPointAtParam(ropeFn.findParamFromLength(ropeLength * 5.0 / 12.0), om.MSpace.kObject),
            posBottom,
            ropeFn.getPointAtParam(ropeFn.findParamFromLength(ropeLength * 7.0 / 12.0), om.MSpace.kObject),
            ropeFn.getPointAtParam(ropeFn.findParamFromLength(ropeLength * 8.0 / 12.0), om.MSpace.kObject),
            posRight,
            ropeFn.getPointAtParam(ropeFn.findParamFromLength(ropeLength * 10.0 / 12.0), om.MSpace.kObject),
            ropeFn.getPointAtParam(ropeFn.findParamFromLength(ropeLength * 11.0 / 12.0), om.MSpace.kObject),
        ]
        positions = [datatypes.Vector(x[0], x[1], x[2]) for x in positions]
        self.crv_ctl = curve.addCurve(crv_root, self.getName("crv_ctl"), positions, close=True, degree=3, m=t)
        cvs = self.getCurveCVs(self.crv_ctl)
        center_pos = sum(cvs) / len(cvs)  # type: ignore
        for i, cv in enumerate(cvs):
            offset = (cv - center_pos).normal() * self.thickness
            new_pos = [cv[0] + offset[0], cv[1] + offset[1], cv[2] + offset[2]]
            self.crv_ctl.setCV(i, new_pos, space="world")

    def addControlJoints(self):

        # local_cvs = self.getCurveCVs(self.crv, "object")
        t = getTransform(self.root)

        icon_shape = "sphere"
        color = 4
        wd = .3
        po = self.offset * 0.3

        cvsObject = self.getCurveCVs(self.crv, "object")
        cvsWorld = self.getCurveCVs(self.crv, "world")
        cvPairs = list(zip(cvsObject, cvsWorld))

        if self.num_locs % 2 == 0:
            cvs = cvPairs[0:]
        else:
            cvs = cvPairs[0:-1]

        controls = []
        for i, (cvo, cvw) in enumerate(cvs):

            mirror = i > self.num_locs / 2
            lower = i > self.left_index and i < self.right_index

            if i == 0: 
                oSide = "C"
                _index = 0

            elif i == self.bottom_index: 
                oSide = "C"
                _index = 1

            elif not mirror:
                oSide = "L"
                if i <= self.left_index:
                    _index = i - 1
                else:
                    _index = (self.bottom_index - i + self.left_index - 1)

            else:
                tmp = self.num_locs - self.right_index
                oSide = "R"
                if i < self.right_index:
                    _index = (i - self.bottom_index + tmp - 1)
                else:
                    _index = (tmp - i + self.right_index - 1)

            with ymt_util.overrideNamingAttributeTemporary(self, side=oSide):
                cvu = datatypes.Vector(cvo[0], cvo[1], cvo[2])

                upv = addTransform(self.upv_root, self.getName("rope_{}_upv".format(_index)))
                cns = addTransform(self.rope_root, self.getName("rope_{}_cns".format(_index)))
                curve.applyRopeCnsLocal(upv, self.crv_ctl, self.upv_crv, cvu)
                curve.applyRopeCnsLocalWithUpv(cns, upv, self.crv_ctl, self.rope, cvo)

                m = getTransform(cns)
                m = setMatrixPosition(m, self._objToWorld(self.locsPos[i]))
     
                if mirror:
                    if lower:
                        m = setMatrixScale(m, scl=[1, 1, 1])
                    else:
                        m = setMatrixScale(m, scl=[-1, 1, 1])
     
                else:
                    if lower:
                        m = setMatrixScale(m, scl=[-1, 1, 1])
                    else:
                        m = setMatrixScale(m, scl=[1, 1, 1])


                # if i == self.left_index:
                #     prev = getTransform(controls[i-1]).rotate
                #     m = setMatrixRotation(m, prev)
                if i == self.right_index + 1:
                    rightCtl = controls[self.right_index]
                    rightNpo = rightCtl.getParent()
                    pos = cmds.xform(rightNpo.fullPath(), q=True, ws=True, translation=True)
                    pm.xform(rightNpo, ws=True, matrix=m)
                    pm.xform(rightNpo, ws=True, translation=pos)
     
                npo_name = self.getName("rope_{}_jnt_npo".format(_index))
                npo = addTransform(cns, npo_name, m)
                ymt_util.setKeyableAttributesDontLockVisibility(npo, [])
     
                t = getTransform(npo)
                ctl = self.addCtl(
                    npo,
                    "%s_crvdetail" % _index,
                    t,
                    color,
                    icon_shape,
                    w=wd,
                    d=wd,
                    # ro=datatypes.Vector(1.57079633, 0, 0),
                    po=po
                )
     
                controls.append(ctl)
     
                # getting joint parent
                self.jnt_pos.append([ctl, "{}".format(i)])
                self.addToSubGroup(ctl, self.detailControllersGroupName)

        self.tweakControllers = controls

    def addToSubGroup(self, obj, group_name):

        if self.settings["ctlGrp"]:
            ctlGrp = self.settings["ctlGrp"]
        else:
            ctlGrp = "controllers"

        self.addToGroup(obj, group_name, parentGrp=ctlGrp)

    def addControllers(self):

        paramsMain = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "ro"]
        paramsSub = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "ro"]
        paramsSub = ["tx", "ty", "tz"]

        ctlOptions = [
            # name,      side, icon,   color, width, keyable
            ["upper",    "C", "square", 4,  .05, paramsMain],  # 0
            ["upInner",  "L", "circle", 14, .03, paramsSub],         # 1
            ["upOuter",  "L", "circle", 14, .03, paramsSub],         # 2
            ["corner",   "L", "square", 4,  .05, paramsMain],  # 3
            ["lowOuter", "L", "circle", 14, .03, paramsSub],         # 4
            ["lowInner", "L", "circle", 14, .03, paramsSub],         # 5
            ["lower",    "C", "square", 4,  .05, paramsMain],  # 6
            ["lowInner", "R", "circle", 14, .03, paramsSub],         # 7
            ["lowOuter", "R", "circle", 14, .03, paramsSub],         # 8
            ["corner",   "R", "square", 4,  .05, paramsMain],  # 9
            ["upOuter",  "R", "circle", 14, .03, paramsSub],         # 10
            ["upInner",  "R", "circle", 14, .03, paramsSub],         # 11
        ]

        self.upNpos, self.upCtls = self._addControls(self.crv_ctl, ctlOptions)

        self.lips_C_upper_ctl  = self.upCtls[0]
        self.lips_C_lower_ctl  = self.upCtls[6]

        self.lips_L_Corner_npo = self.upNpos[3]
        self.lips_R_Corner_npo = self.upNpos[9]

        # Connecting control crvs with controls
        curve.gear_curvecns_op_local_skip_rotate(self.crv_ctl, self.upCtls)

        # adding wires
        w1 = pm.wire(self.crv, w=self.crv_ctl, dropoffDistance=[0, self.size * 10])[0]
        w2 = pm.wire(self.rope, w=self.crv_ctl, dropoffDistance=[0, self.size * 10])[0]
        w3 = pm.wire(self.upv_crv, w=self.crv_ctl, dropoffDistance=[0, self.size * 10])[0]

        cmds.setAttr(w1.name() + ".rotation", 0.0)
        cmds.setAttr(w2.name() + ".rotation", 0.0)
        cmds.setAttr(w3.name() + ".rotation", 0.0)

        # offset upv with FRONT_OFFSET
        cvs = self.getCurveCVs(self.upv_crv)
        for i, cv in enumerate(cvs):
            new_pos = [cv[0], cv[1], cv[2] + self.FRONT_OFFSET]
            self.upv_crv.setCV(i, new_pos, space="world")

    def addConstraints(self):

        def applyMultiCns(ctls, src1Index, src2Index, dstIndex, p1, p2):

            src1 = ctls[src1Index]
            src2 = ctls[src2Index]
            dst = ctls[dstIndex]

            src1Path = src1.fullPath()
            src2Path = src2.fullPath()
            dstPath = ctls[dstIndex].getParent().fullPath()

            r2, r1 = calcDistRatio(src1, src2, dst)

            cns_node = cmds.parentConstraint(src1Path, src2Path, dstPath, mo=True, skipRotate=("x", "y", "z"))[0]  # type: str
            attr1 = cns_node + "." + src1.name().split("|")[-1] + "W0"
            attr2 = cns_node + "." + src2.name().split("|")[-1] + "W1"

            cmds.setAttr(attr1, (r1 * 0.4) + (p1 * 0.6))
            cmds.setAttr(attr2, (r2 * 0.4) + (p2 * 0.6))

        def calcDistRatio(a, b, c):
            pa = a.getTranslation(space="world")
            pb = b.getTranslation(space="world")
            pc = c.getTranslation(space="world")

            d1 = abs((pa- pc).length())
            d2 = abs((pb- pc).length())

            r1 = d1 / (d1 + d2)
            r2 = 1.0 - abs(r1)

            return r1, r2

        # if 8 locs, : up is 0, left is 2, bottom is 4, right is 6
        applyMultiCns(self.upCtls, 0, 3, 1,  0.70, 0.10)
        applyMultiCns(self.upCtls, 0, 3, 2,  0.70, 0.15)

        applyMultiCns(self.upCtls, 3, 6, 4,  0.20, 0.80)
        applyMultiCns(self.upCtls, 3, 6, 5,  0.20, 0.80)

        applyMultiCns(self.upCtls, 6, 9, 7,  0.80, 0.20)
        applyMultiCns(self.upCtls, 6, 9, 8,  0.80, 0.20)

        applyMultiCns(self.upCtls, 9, 0, 10, 0.10, 0.70)
        applyMultiCns(self.upCtls, 9, 0, 11, 0.15, 0.70)

        self._constrainCtlRotToCurve(self.upCtls, self.crv)

    def _addControls(self, crv_ctl, option):

        cvs = self.getCurveCVs(crv_ctl)

        center_pos = sum(cvs) / len(cvs)  # type: ignore
        total_dist = sum([(x - center_pos).length() for x in cvs])
        average_dist = total_dist / len(cvs)

        distSize = average_dist * 5.0

        npos = []
        ctls = []

        for i, cv in enumerate(cvs):

            mirror = i > (len(cvs) / 2)
            lower = i > 3 and i < 9

            oName  = option[i][0]
            oSide  = option[i][1]
            o_icon = option[i][2]
            color  = option[i][3]
            wd     = option[i][4]
            oPar   = option[i][5]

            scl = [1, 1, 1]
            if mirror:
                scl[0] = -1
            if lower:
                scl[1] = -1

            t = transform.getTransformFromPos(cv)
            t = transform.setMatrixScale(t, scl)

            with ymt_util.overrideNamingAttributeTemporary(self, side=oSide):
                npo = addTransform(self.ctl_root, self.getName("%s_npo" % oName), t)
                npos.append(npo)

                ctl = self.addCtl(
                    npo,
                    oName,
                    t,
                    color,
                    o_icon,
                    w=wd * distSize,
                    d=wd * distSize,
                    ro=datatypes.Vector(1.57079633, 0, 0),
                    po=datatypes.Vector(0, 0, .07 * distSize),
                )

                ctls.append(ctl)
                ymt_util.setKeyableAttributesDontLockVisibility(ctl, oPar)
                self.addToSubGroup(ctl, self.primaryControllersGroupName)

        return npos, ctls

    def _constrainCtlRotToCurve(self, ctls, crv): 

        # for i, cv in enumerate(cvs):
        for i in (1, 2, 4, 5, 7, 8, 10, 11):
            crvShape = crv.getShape().fullPath()

            ctl = ctls[i]
            dm_node = ymt_util.getDecomposeMatrixOfAtoB(ctl, crv, skip_last=True)

            point = cmds.createNode("nearestPointOnCurve")
            cmds.connectAttr(dm_node + ".outputTranslate", point + ".inPosition")
            cmds.connectAttr(crvShape + ".local", point + ".inputCurve")

            uvalue = cmds.getAttr(point + ".parameter")
            cmds.delete(point)
            # cmds.delete(dm_node.fullPath())

            motPath = cmds.createNode("motionPath")
            cmds.setAttr(motPath + ".uValue", uvalue)
            cmds.setAttr(motPath + ".frontAxis", 0)
            cmds.setAttr(motPath + ".upAxis", 1)
            cmds.setAttr(motPath + ".worldUpType", 3)  # vector
            cmds.setAttr(motPath + ".worldUpVector", 0, 1, 0)
            cmds.connectAttr(crvShape + ".local", motPath + ".geometryPath")

            mirror = i > 6
            lower = 3 < i and i < 9
            outpath = motPath + ".rotateZ"

            if lower:
                cmds.setAttr(motPath + ".inverseFront", 1)

                if not mirror:
                    mul = cmds.createNode("multDoubleLinear")
                    cmds.connectAttr(motPath + ".rotateZ", mul + ".input1")
                    cmds.setAttr(mul + ".input2", -1)
                    outpath = mul + ".output"

            else:
                cmds.setAttr(motPath + ".inverseFront", 0)

                if mirror:
                    mul = cmds.createNode("multDoubleLinear")
                    cmds.connectAttr(motPath + ".rotateZ", mul + ".input1")
                    cmds.setAttr(mul + ".input2", -1)
                    outpath = mul + ".output"

            # Inserting an orient constraint node in between because
            # dagPose command cannot be applied when connected dilectly to the output
            cmds.setAttr("{}.rotateZ".format(ctl), lock=False)
            oriCns = cmds.createNode("orientConstraint")
            cmds.parent(oriCns, ctl.fullPath(), relative=True)
            cmds.connectAttr(outpath, oriCns + ".target[0].targetRotateZ")
            cmds.connectAttr(oriCns + ".constraintRotateZ", ctl + ".rotateZ")
            cmds.setAttr("{}.rotateZ".format(ctl), lock=True)

    def _worldToObj(self, pos):
        # type: (list[float]) -> dt.Vector

        m = getTransform(self.root)
        m = om.MMatrix(m)

        np = om.MMatrix()
        np.setToIdentity()
        np[12] = pos[0]
        np[13] = pos[1]
        np[14] = pos[2]

        pos[0] = (m.inverse() * np)[12]
        pos[1] = (m.inverse() * np)[13]
        pos[2] = (m.inverse() * np)[14]
        positions = datatypes.Vector(pos[0], pos[1], pos[2])

        return positions

    def _objToWorld(self, pos):
        # type: (list[float]) -> dt.Vector

        m = getTransform(self.root)
        m = om.MMatrix(m)

        np = om.MMatrix()
        np.setToIdentity()
        np[12] = pos[0]
        np[13] = pos[1]
        np[14] = pos[2]

        pos[0] = (m * np)[12]
        pos[1] = (m * np)[13]
        pos[2] = (m * np)[14]

        positions = datatypes.Vector(pos[0], pos[1], pos[2])

        return positions

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        pass
        # if not self.settings["ui_host"]:
        #     self.uihost = self.over_ctl

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
        self.connections["mouth_01"] = self.connect_mouth
        self.connections["lip_01"] = self.connect_mouth
        self.connections["standard"] = self.connect_mouth

    def connect_mouth(self):

        if self.parent is None:
            return

        if self.surfRef:
            ref = self.rig.findComponent(self.surfRef)
            self.sliding_surface = ref.sliding_surface

        self.parent.addChild(self.root)

        try:
            self.connect_ghosts()
        except:
            traceback.print_exc()
            raise

    def connect_standard(self):
        self.parent.addChild(self.root)
        if self.surfRef:
            ref = self.rig.findComponent(self.surfRef)
            self.sliding_surface = ref.sliding_surface

    def connect_ghosts(self):

        lipup_ref = self.parent_comp.lipup_ctl
        liplow_ref = self.parent_comp.liplow_ctl

        slide_c_ref = self.rig.findRelative(self.mouthCenterRef)
        corner_l_ref = self.rig.findRelative(self.mouthLeftRef)
        corner_r_ref = self.rig.findRelative(self.mouthRightRef)

        slide_c_comp = self.rig.findComponent(self.mouthCenterRef)
        corner_l_comp = self.rig.findComponent(self.mouthLeftRef)
        corner_r_comp = self.rig.findComponent(self.mouthRightRef)

        if slide_c_comp.root.parent(0) != self.parent:
            self.parent.addChild(slide_c_comp.root)

        if corner_l_comp.root.parent(0) != self.parent:
            self.parent.addChild(corner_l_comp.root)

        if corner_r_comp.root.parent(0) != self.parent:
            self.parent.addChild(corner_r_comp.root)

        # create interpose lvl for the ctl
        intTra = rigbits.createInterpolateTransform([lipup_ref, liplow_ref], blend=0.38)
        pm.rename(intTra, intTra.name() + "_int")

        drivers = self.connect_slide_ghost(
            intTra,
            slide_c_ref,
            corner_l_ref,
            corner_r_ref
        )
        self.connect_mouth_ghost(lipup_ref, liplow_ref)

        pm.parent(corner_l_comp.ik_cns, self.mouthSlide_ctl)
        pm.parent(corner_r_comp.ik_cns, self.mouthSlide_ctl)

        pm.parent(drivers[0], slide_c_comp.ik_cns)
        pm.parent(drivers[1], corner_l_comp.ik_cns)
        pm.parent(drivers[2], corner_r_comp.ik_cns)

        # remove elements from controllers group
        for comp in [slide_c_comp, corner_l_comp, corner_r_comp]:
            for k, v in comp.groups.items():
                if "componentsRoots" in k:
                    continue

                comp.groups[k] = []

    def _createGhostCtl(self, ghost_ctl, parent):

        ctl = ghost.createGhostCtl(ghost_ctl, parent=parent, connect=True)
        # rigbits.connectLocalTransform([ctl, ghost_ctl])
        ctl.attr("isCtl") // ghost_ctl.attr("isCtl")
        ctl.attr("isCtl").set(True)
        ghost_ctl.attr("isCtl").set(False)

        shape = ghost_ctl.getShape()
        if shape:
            _visi_off_lock(shape)

        shape = ctl.getShape()
        if shape:
            ctl.getShape().visibility.set(True)

        if self.settings["ctlGrp"]:
            ctlGrp = self.settings["ctlGrp"]
            self.addToGroup(ctl, ctlGrp, "controllers")

        else:
            ctlGrp = "controllers"
            self.addToGroup(ctl, ctlGrp)

        if ctlGrp not in self.groups.keys():
            self.groups[ctlGrp] = []

        self._removeFromCtrlGroup(ghost_ctl)
        self.addToSubGroup(ctl, self.primaryControllersGroupName)

        return ctl

    def _removeFromCtrlGroup(self, obj):

        if self.settings["ctlGrp"]:
            ctlGrp = self.settings["ctlGrp"]

        else:
            ctlGrp = "controllers"

        if ctlGrp not in self.groups.keys():
            return

        for grp_name, grp in self.groups.items():
            try:  # noqa: FURB107
                grp.remove(obj)
            except ValueError:
                pass

    def connect_slide_ghost(self, intTra, slide_c_ref, corner_l_ref, corner_r_ref):

        # create ghost controls
        self.mouthSlide_ctl = self._createGhostCtl(slide_c_ref, intTra)
        self.cornerL_ctl = self._createGhostCtl(corner_l_ref, slide_c_ref)
        self.cornerR_ctl = self._createGhostCtl(corner_r_ref, slide_c_ref)
        self.jnt_pos.insert(0, [self.mouthSlide_ctl, "slide_c"])

        # slide system
        drivers = ghostSliderForMouth(
            [slide_c_ref, corner_l_ref, corner_r_ref],
            intTra,
            self.sliding_surface,
            self.sliding_surface.getParent()
        )

        # connect scale
        pm.connectAttr(self.mouthSlide_ctl.scale, slide_c_ref.scale)
        pm.connectAttr(self.cornerL_ctl.scale, corner_l_ref.scale)
        pm.connectAttr(self.cornerR_ctl.scale, corner_r_ref.scale)

        # connect pucker
        cmds.setAttr("{}.tz".format(slide_c_ref.name()), l=False)
        pm.connectAttr(self.mouthSlide_ctl.tz, slide_c_ref.tz)

        pm.parentConstraint(corner_l_ref, self.lips_L_Corner_npo, mo=True)
        pm.parentConstraint(corner_r_ref, self.lips_R_Corner_npo, mo=True)

        ymt_util.setKeyableAttributesDontLockVisibility(slide_c_ref, [])
        ymt_util.setKeyableAttributesDontLockVisibility(corner_l_ref, [])
        ymt_util.setKeyableAttributesDontLockVisibility(corner_r_ref, [])

        return drivers

    def connect_mouth_ghost(self, lipup_ref, liplow_ref):

        # center main controls
        self.lips_C_upper_ctl, up_ghost_ctl = createGhostWithParentConstraint(self.lips_C_upper_ctl, lipup_ref)
        self.lips_C_lower_ctl, lo_ghost_ctl = createGhostWithParentConstraint(self.lips_C_lower_ctl, liplow_ref)

        self._removeFromCtrlGroup(up_ghost_ctl)
        self._removeFromCtrlGroup(lo_ghost_ctl)
        self.addToSubGroup(self.lips_C_upper_ctl, self.primaryControllersGroupName)
        self.addToSubGroup(self.lips_C_lower_ctl, self.primaryControllersGroupName)

        # add slider offset
        s = self.mouthSlide_ctl.name()
        up_npo = rigbits.addNPO(self.lips_C_upper_ctl)[0].name()
        low_npo = rigbits.addNPO(self.lips_C_lower_ctl)[0].name()

        pm.connectAttr(s + ".translate", up_npo + ".translate", force=True)
        pm.connectAttr(s + ".scale", up_npo + ".scale", force=True)
        pm.connectAttr(s + ".rotate", up_npo + ".rotate", force=True)

        r = pm.createNode("multiplyDivide")
        pm.setAttr(r + ".input2Y", -1)
        pm.connectAttr(s + ".translateY", r + ".input1Y", force=True)
        pm.connectAttr(r + ".outputY",    low_npo + ".translateY", force=True)
        pm.connectAttr(s + ".translateX", low_npo + ".translateX", force=True)
        pm.connectAttr(s + ".translateZ", low_npo + ".translateZ", force=True)
        pm.connectAttr(s + ".scale", low_npo + ".scale", force=True)
        for axis in ("X", "Y", "Z"):
            inv = cmds.createNode("multiplyDivide")
            cmds.setAttr(inv + ".input2" + axis, -1)
            cmds.connectAttr(
                s + ".rotate" + axis,
                inv + ".input1" + axis
            )
            cmds.connectAttr(
                inv + ".output" + axis,
                low_npo + ".rotate" + axis
            )

        return

    def connect_averageParentCns(self, parents, target):
        """
        Connection definition using average parent constraint.
        """

        if len(parents) == 1:
            pm.parent(parents[0], target)

        else:
            parents.append(target)
            cns_node = pm.parentConstraint(*parents, maintainOffset=True)
            cns_attr = pm.parentConstraint(
                cns_node, query=True, weightAliasList=True)

            for i, attr in enumerate(cns_attr):
                pm.setAttr(attr, 1.0)

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""

        self.relatives["root"] = self.root
        for i, ctl in enumerate(self.tweakControllers):

            self.relatives["%s_loc" % i] = ctl
            self.controlRelatives["%s_loc" % i] = ctl


def ghostSliderForMouth(ghostControls, intTra, surface, sliderParent):
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
            pm.disconnectAttr("{}.{}".format(ctl, attr), "{}.{}".format(ghost, attr))

    def connCenter(ctl, driver, ghost):
        dm_node = ymt_util.getDecomposeMatrixOfAtoB(ctl, driver, skip_last=True)

        for attr in ["translate", "scale"]:
            pm.connectAttr("{}.output{}".format(dm_node, attr.capitalize()), "{}.{}".format(driver, attr))
            pm.disconnectAttr("{}.{}".format(ctl, attr), "{}.{}".format(ghost, attr))

    surfaceShape = surface.getShape()
    sliders = []
    drivers = []

    for i, ctlGhost in enumerate(ghostControls):
        ctl = pm.listConnections(ctlGhost, t="transform")[-1]
        t = ctl.getMatrix(worldSpace=True)

        gDriver = addTransform(surface.getParent(), "{}_slideDriver".format(ctl.name()), t)
        drivers.append(gDriver)

        if 0 == i:
            connCenter(ctl, gDriver, ctlGhost)

        else:
            conn(ctl, gDriver, ctlGhost)

        oParent = ctlGhost.getParent()
        npoName = "_".join(ctlGhost.name().split("_")[:-1]) + "_npo"
        oTra = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))
        oTra.setTransformation(ctlGhost.getMatrix())
        pm.parent(ctlGhost, oTra)

        slider = addTransform(sliderParent, ctl.name() + "_slideDriven", t)
        sliders.append(slider)

        # connexion
        if 0 == i:
            dm_node = node.createDecomposeMatrixNode(gDriver.attr("matrix"))

        else:
            dm_node = ymt_util.getDecomposeMatrixOfAtoB(ctl, slider, skip_last=True)

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
        ymt_util.setKeyableAttributesDontLockVisibility(slider, [])
        # for shape in ctlGhost.getShapes():
        #     pm.delete(shape)

    for slider in sliders[1:]:
        _visi_off_lock(slider)

    return drivers


def createGhostWithParentConstraint(ctl, parent=None, connect=True):
    """Create a duplicated Ghost control

    Create a duplicate of the control and rename the original with _ghost.
    Later connect the local transforms and the Channels.
    This is useful to connect local rig controls with the final rig control.

    Args:
        ctl (dagNode): Original Control to duplicate
        parent (dagNode): Parent for the new created control

    Returns:
       pyNode: The new created control

    """
    if isinstance(ctl, (six.string_types, six.text_type)):
        ctl = pm.PyNode(ctl)

    if parent:
        if isinstance(parent, (six.string_types, six.text_type)):
            parent = pm.PyNode(parent)

    grps = ctl.listConnections(t="objectSet")
    for grp in grps:
        grp.remove(ctl)
    oName = ctl.name()
    pm.rename(ctl, oName + "_ghost")
    newCtl = pm.duplicate(ctl, po=True)[0]
    pm.rename(newCtl, oName)
    source2 = pm.duplicate(ctl)[0]
    for shape in source2.getShapes():
        pm.parent(shape, newCtl, r=True, s=True)
        pm.rename(shape, newCtl.name() + "Shape")
        pm.parent(shape, newCtl, r=True, s=True)
    pm.delete(source2)
    if parent:
        pm.parent(newCtl, parent)
        oTra = pm.createNode("transform",
                             n=newCtl.name() + "_npo",
                             p=parent, ss=True)
        oTra.setMatrix(ctl.getParent().getMatrix(worldSpace=True),
                       worldSpace=True)
        pm.parent(newCtl, oTra)
    if connect:
        pm.parentConstraint(newCtl, ctl, mo=True)
        # rigbits.connectLocalTransform([newCtl, ctl])
        rigbits.connectUserDefinedChannels(newCtl, ctl)
    for grp in grps:
        grp.add(newCtl)

    # add control tag
    node.add_controller_tag(newCtl, parent)
    for shape in ctl.getShapes():
        pm.delete(shape)

    return newCtl, ctl


def _visi_off_lock(node):
    """Short cuts."""
    if not node:
        raise Exception("node is null")

    cmds.setAttr("{}.visibility".format(node.name()), l=False)
    node.visibility.set(False)
    try:
        ymt_util.setKeyableAttributesDontLockVisibility(node, [])
    except:
        pass


def calculate_flatness_ratio(points):
    # type: (list[tuple[float, float, float]]) -> tuple[tuple[float, float, float], float]

    try:
        import numpy as np  # type: ignore  # noqa: F401
        return calculate_flatness_ratio_using_numpy(points)

    except ImportError:
        logger.warning("This function requires numpy, using simple calculation instead.")
        return calculate_flatness_ratio_simple(points)


def calculate_flatness_ratio_using_numpy(points):
    # type: (list[tuple[float, float, float]]) -> tuple[tuple[float, float, float], float]

    import numpy as np  # type: ignore  # noqa: F401
    mean = np.mean(points, axis=0)
    centered_points = points - mean

    cov_matrix = np.cov(centered_points, rowvar=False)

    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)

    sorted_idx = np.argsort(eigenvalues)[::-1]
    sorted_eigenvalues = eigenvalues[sorted_idx]
    sorted_eigenvectors = eigenvectors[:, sorted_idx]

    principal_directions = sorted_eigenvectors

    lambda1 = sorted_eigenvalues[0]
    lambda2 = sorted_eigenvalues[1]
    lambda3 = sorted_eigenvalues[2]

    flatness_ratio = (lambda3 * 0.3 + lambda2) / lambda1

    # direction = [
    #     principal_directions[0][0],
    #     principal_directions[0][1],
    #     principal_directions[0][2]
    # ]

    return principal_directions, flatness_ratio


def calculate_flatness_ratio_simple(points):
    # type: (list[tuple[float, float, float]]) -> tuple[tuple[float, float, float], float]

    if not points:
        raise ValueError("ポイントリストが空です。")

    n = len(points)
    
    # 1. データの中心化
    mean_x = sum(p[0] for p in points) / n
    mean_y = sum(p[1] for p in points) / n
    mean_z = sum(p[2] for p in points) / n

    centered = [(p[0] - mean_x, p[1] - mean_y, p[2] - mean_z) for p in points]

    # 2. 共分散行列の計算
    cov_xx = sum(p[0] * p[0] for p in centered) / (n - 1)
    cov_xy = sum(p[0] * p[1] for p in centered) / (n - 1)
    cov_xz = sum(p[0] * p[2] for p in centered) / (n - 1)
    cov_yy = sum(p[1] * p[1] for p in centered) / (n - 1)
    cov_yz = sum(p[1] * p[2] for p in centered) / (n - 1)
    cov_zz = sum(p[2] * p[2] for p in centered) / (n - 1)

    cov_matrix = [
        [cov_xx, cov_xy, cov_xz],
        [cov_xy, cov_yy, cov_yz],
        [cov_xz, cov_yz, cov_zz]
    ]

    # 3. 固有値と固有ベクトルの計算
    # 3x3 対称行列の固有値を解析的に計算
    eigenvalues, eigenvectors = eigen_decomposition_3x3(cov_matrix)

    # 4. 固有値のソート（降順）
    sorted_indices = sorted(range(3), key=lambda i: eigenvalues[i], reverse=True)
    sorted_eigenvalues = [eigenvalues[i] for i in sorted_indices]
    sorted_eigenvectors = [[eigenvectors[i][j] for i in sorted_indices] for j in range(3)]

    lambda1, lambda2, lambda3 = sorted_eigenvalues

    # 5. 扁平率の計算
    flatness_ratio = (lambda3 * 0.3 + lambda2) / lambda1

    # 主成分の方向（固有ベクトル）の取得
    # 主成分3（最小の固有値）の固有ベクトル
    principal_direction = tuple(sorted_eigenvectors[2])

    return principal_direction, flatness_ratio


def eigen_decomposition_3x3(matrix):
    """
    3x3 対称行列の固有値と固有ベクトルを計算する関数。
    数値的な精度は低く、実際の用途では numpy を使用することを推奨します。
    
    Parameters:
        matrix (list of list of float): 3x3 対称行列
    
    Returns:
        tuple: (固有値リスト, 固有ベクトルリスト)
    """
    # ヘッセ行列の固有値を求めるための特性方程式を解く
    # |A - λI| = 0
    # ここでは3x3の対称行列を仮定
    a = matrix[0][0]
    b = matrix[0][1]
    c = matrix[0][2]
    d = matrix[1][1]
    e = matrix[1][2]
    f = matrix[2][2]

    # 計算を簡略化するために変数を定義
    p1 = b**2 + c**2 + e**2
    if p1 == 0:
        # 対角行列の場合
        eigenvalues = [a, d, f]
        eigenvectors = [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1]
        ]
        return eigenvalues, eigenvectors

    # カルダノの方法を用いて固有値を求める
    q = (a + d + f) / 3
    p2 = (a - q)**2 + (d - q)**2 + (f - q)**2 + 2 * p1
    p = math.sqrt(p2 / 6)
    B = [
        [(matrix[i][j] - q if i == j else matrix[i][j]) / p for j in range(3)]
        for i in range(3)
    ]

    r = determinant_3x3(B) / 2

    # 確定
    if r <= -1:
        phi = math.pi / 3
    elif r >= 1:
        phi = 0
    else:
        phi = math.acos(r) / 3

    # 固有値
    eig1 = q + 2 * p * math.cos(phi)
    eig3 = q + 2 * p * math.cos(phi + (2 * math.pi / 3))
    eig2 = 3 * q - eig1 - eig3  # 因式分解を使用

    eigenvalues = [eig1, eig2, eig3]

    # 固有ベクトルの計算
    eigenvectors = []
    for eig in eigenvalues:
        # (A - λI)v = 0 を解く
        A_minus_lambda_I = [
            [matrix[0][0] - eig, matrix[0][1], matrix[0][2]],
            [matrix[1][0], matrix[1][1] - eig, matrix[1][2]],
            [matrix[2][0], matrix[2][1], matrix[2][2] - eig]
        ]
        # 3つの式の中から2つを選び、解を求める
        # ここでは最初の2行を使用
        v = solve_linear_system_3x3(A_minus_lambda_I)
        if v is not None:
            # 正規化
            norm = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
            if norm != 0:
                v = [v[i] / norm for i in range(3)]
            eigenvectors.append(v)
        else:
            # 解けない場合は単位ベクトルを使用
            eigenvectors.append([1, 0, 0])

    return eigenvalues, eigenvectors

def determinant_3x3(m):
    """
    3x3行列の行列式を計算する関数。
    
    Parameters:
        m (list of list of float): 3x3行列
    
    Returns:
        float: 行列式の値
    """
    return (
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) -
        m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) +
        m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    )

def solve_linear_system_3x3(m):
    """
    3x3行列の線形方程式を解く関数。
    解が一意でない場合は None を返す。
    
    Parameters:
        m (list of list of float): 3x3行列 (A)
    
    Returns:
        list of float or None: 解ベクトル [x, y, z] または None
    """
    # 拡大係数行列を作成 (A | 0)
    A = [
        [m[0][0], m[0][1], m[0][2]],
        [m[1][0], m[1][1], m[1][2]],
        [m[2][0], m[2][1], m[2][2]]
    ]

    # ランクを計算して解の存在を確認
    # 簡易的なランクチェック
    rank = matrix_rank_3x3(A)
    if rank < 2:
        return None  # 無限に多くの解が存在するか、解が存在しない

    # 2つの方程式を選び、3つ目を無視して解を求める
    # ここでは最初の2行を使用
    a1, b1, c1 = A[0]
    a2, b2, c2 = A[1]

    # 例えば、x = 1 と仮定して y と z を求める
    # しかし、これは一般的ではないため、別の方法を使用
    # クラメールの法則を用いて解を求める

    # ラインを見つけるために、小さい値を無視
    epsilon = 1e-6
    if abs(a1) > epsilon or abs(b1) > epsilon:
        # 解を y と z に対して表現
        # 例: a1 * x + b1 * y + c1 * z = 0
        #       a2 * x + b2 * y + c2 * z = 0
        # ここでは z をパラメータとする
        z = 1.0
        if c1 != 0:
            y = (-a1 * 0 - c1 * z) / b1 if b1 != 0 else 0
        else:
            y = 0
        x = 0  # 任意の値
        return [x, y, z]
    elif abs(a2) > epsilon or abs(b2) > epsilon:
        # 同様に他の行を使用
        z = 1.0
        y = (-a2 * 0 - c2 * z) / b2 if b2 != 0 else 0
        x = 0
        return [x, y, z]
    else:
        return None

def matrix_rank_3x3(m):
    """
    3x3行列のランクを計算する関数。
    
    Parameters:
        m (list of list of float): 3x3行列
    
    Returns:
        int: ランク (0, 1, 2, 3)
    """
    det = determinant_3x3(m)
    if det != 0:
        return 3
    # チェック2x2の小行列
    submatrices = [
        [m[0][0], m[0][1]],
        [m[0][0], m[0][2]],
        [m[0][1], m[0][2]],
        [m[1][0], m[1][1]],
        [m[1][0], m[1][2]],
        [m[1][1], m[1][2]],
        [m[2][0], m[2][1]],
        [m[2][0], m[2][2]],
        [m[2][1], m[2][2]],
    ]
    for sm in submatrices:
        det2 = sm[0] * sm[1] - sm[1] * sm[0]  # 2x2の行列式
        if det2 != 0:
            return 2
    # チェック1x1の小行列
    for row in m:
        for val in row:
            if val != 0:
                return 1
    return 0


def calculate_principal_direction_and_flatness_ratio(crv):

    fnCurve = curve.getMFnNurbsCurve(crv)
    u_min, u_max = fnCurve.knotDomain

    samplePos = []
    for i in range(100):
        u = u_min + (u_max - u_min) * i / 100
        p = fnCurve.getPointAtParam(u)
        samplePos.append(p)

    direction, flatness_ratio = calculate_flatness_ratio(samplePos)
    return direction, flatness_ratio


def inflate_position_by_curve_flattness(crv, position):
    # type: (pm.PyNode, tuple[float, float, float]) -> tuple[float, float, float]

    directions, flatness_ratio = calculate_principal_direction_and_flatness_ratio(crv)

    ratio = math.pow(max(1.0, (1.0 - flatness_ratio)), 0.8) * 0.1
    for i, vec in enumerate(directions[0]):
        if i > 2:
            break
        position[i] *= (abs(vec) * ratio + 1.0)

    for i, vec in enumerate(directions[1]):
        if i > 2:
            break
        position[i] *= (abs(vec) * ratio * 0.3 + 1.0)

    return position
