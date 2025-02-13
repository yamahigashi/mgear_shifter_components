"""mGear shifter components"""
# pylint: disable=import-error,W0201,C0111,C0112
import re
import six
import sys
import traceback

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

from mgear import rigbits
from mgear.rigbits import ghost
from mgear.shifter import component

from mgear.core import (
    transform,
    applyop,
    # vector,
    node,
    primitive,
)

from mgear.core.transform import (
    getTransform,
    setMatrixPosition,
    # setMatrixRotation,
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
        self.surfRef = self.settings["surfaceReference"]
        self.cheekLeftRef = self.settings["cheekLeftReference"]
        self.cheekRightRef = self.settings["cheekRightReference"]
        # -------------------------------------------------------

        self.num_locs = self.getNumberOfLocators("_loc")

        self.upPos = self.guide.apos[-3]
        self.lowPos = self.guide.apos[-2]
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
        self.FRONT_OFFSET = 0.2

        self.numInterControls = 1  # TODO: extract to settings
        self.NB_CVS = self.numInterControls * 4 + 4  # means 4 spans with 2 controllers each + 4 controllers for the corners

        # odd / event
        if self.num_locs % 2 == 0:
            # even
            self.NB_ROPE = self.num_locs * 20 + 1
            self.bottom_index = int(self.num_locs / 2)
        else:
            # odd
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

        self.crv = None
        # self.lowCrv = None
        self.crv_ctl = None
        self.lowCrv_ctl = None
        self.upBlink = None
        self.lowBlink = None
        self.upTarget = None
        self.lowTarget = None
        self.midTarget = None
        self.midTargetLower = None

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

        t = getTransform(self.root)
        positions = [self._worldToObj(x) for x in self.locsPos]
        # plane = self.addDummyPlane()
        # planeNode = pm.PyNode(plane.longName())

        # -------------------------------------------------------------------
        # edgeList = ["{}.e[{}]".format(plane.longName(), 0)]
        # for i in range(1, self.num_locs + 1):
        #     edgeList.append("{}.e[{}]".format(plane.longName(), i * 2 + 1))
        # edgeList = [pm.PyNode(x) for x in edgeList]

        self.crv = curve.addCurve(
            crv_root,
            self.getName("crv"),
            positions,
            m=t,
            close=True,
            degree=3,
        )
        self.crv_ctl = curve.addCurve(
            crv_root,
            self.getName("ctl_crv"),
            positions,
            m=t,
            close=True,
            degree=3,
        )

    def addCurveBaseControllers(self, crv_root):

        t = getTransform(self.root)

        def curveFromCurve(crv, name, nbPoints, tobe_offset):
            new_crv = curve.createCurveFromCurve(
                crv,
                self.getName(name),
                nbPoints=nbPoints,
                parent=crv_root,
                m=t,
                close=True
            )
            new_crv.attr("visibility").set(False)

            # new_crv = curve.createCurveFromCurveEvenLength(
            #     crv,
            #     self.getName(name),
            #     nbPoints=nbPoints,
            #     parent=crv_root,
            #     m=t,
            #     close=True
            # )
            # new_crv.attr("visibility").set(False)
            crvFn = curve.getMFnNurbsCurve(new_crv)

            if tobe_offset:
                cvs = crvFn.cvPositions(om.MSpace.kObject)
                points = []
                for i, cv in enumerate(cvs):
                    offset = [cv[0], cv[1], cv[2] + self.FRONT_OFFSET]
                    point = om.MPoint(offset)
                    points.append(point)
                crvFn.setCVPositions(points, om.MSpace.kObject)

            return new_crv

        # -------------------------------------------------------------------
        self.rope = curveFromCurve(self.crv, "rope_crv", self.NB_ROPE, False)
        self.upv_crv = curveFromCurve(self.crv, "upv_crv", self.NB_ROPE, True)
        self.crv_ctl = curveFromCurve(self.crv, "ctl_crv",  self.NB_CVS,  False)

    def addControlJoints(self):
        self.joints = self._addControlJoints(self.crv, self.rope_root, self.rope)

    def _addControlJoints(self, crv, rope_root, rope):

        local_cvs = self.getCurveCVs(crv, "object")
        controls = []
        t = getTransform(self.root)

        icon_shape = "sphere"
        color = 4
        wd = .3
        po = self.offset * 0.3

        cvsObject = self.getCurveCVs(crv, "object")

        xforms = []  # type: List[datatypes.Matrix] # to store xforms for each cv
        for i, _ in enumerate(cvsObject):

            mirror = i > self.num_locs / 2
            lower = i > self.left_index and i < self.right_index

            # sub component name
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

                cvo = cvsObject[i]
                cvu = datatypes.Vector(cvo[0], cvo[1], cvo[2] + self.FRONT_OFFSET)

                upv = addTransform(self.upv_root, self.getName("rope_{}_upv".format(_index)))
                cns = addTransform(rope_root, self.getName("rope_{}_cns".format(_index)))
                curve.applyRopeCnsLocal(upv, self.crv_ctl, self.upv_crv, cvu)
                curve.applyRopeCnsLocalWithUpv(cns, upv, self.crv_ctl, self.rope, cvo)

                m = getTransform(cns)
                m = setMatrixPosition(m, self.locsPos[i])

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

                mAsList = [item for tup in m.get() for item in tup]
                xforms.append(mAsList)

                if i == (self.left_index + 1):
                    sideCtl = controls[self.left_index]
                    sideNpo = sideCtl.getParent()
                    pos = cmds.xform(sideNpo.longName(), q=True, ws=True, translation=True)
                    pm.xform(sideNpo, ws=True, matrix=xforms[self.left_index - 1])
                    pm.xform(sideNpo, ws=True, translation=pos)

                if i == self.right_index + 1:
                    rightCtl = controls[self.right_index]
                    rightNpo = rightCtl.getParent()
                    pos = cmds.xform(rightNpo.longName(), q=True, ws=True, translation=True)
                    pm.xform(rightNpo, ws=True, matrix=mAsList)
                    pm.xform(rightNpo, ws=True, translation=pos)

                npo_name = self.getName("rope_{}_jnt_npo".format(_index))
                npo = addTransform(cns, npo_name, m)
     
                t = getTransform(npo)
                ctl = self.addCtl(
                    npo,
                    "%s_crvdetail" % _index,
                    t,
                    color,
                    icon_shape,
                    w=wd,
                    d=wd,
                    po=po
                )

                controls.append(ctl)

                # getting joint parent
                # jnt = rigbits.addJnt(npo, noReplace=True, parent=self.j_parent)
                self.jnt_pos.append([ctl, "{}".format(i)])
                self.addToSubGroup(ctl, self.detailControllersGroupName)

        return controls

    def addToSubGroup(self, obj, group_name):

        if self.settings["ctlGrp"]:
            ctlGrp = self.settings["ctlGrp"]
        else:
            ctlGrp = "controllers"

        self.addToGroup(obj, group_name, parentGrp=ctlGrp)

    def addControllers(self):
        axis_list = ["sx", "sy", "sz", "ro"]
        ctlOptions = [
            # for referenece
            # name,      side, icon,   color, width, keyable
            # ["upcenter", "C", "square", 4,  .05, axis_list],
            # ["upinner",  "L", "circle", 14, .03, []],
            # ["upcorner", "L", "circle", 14, .03, []],
            # ["outer",    "L", "square", 4,  .05, axis_list],
            # ["lowouter", "L", "circle", 14, .03, []],
            # ["lowinner", "L", "circle", 14, .03, []],
            # ["lowcenter","C", "square", 4,  .05, axis_list],
            # ["lowinner", "R", "circle", 14, .03, []],
            # ["lowouter", "R", "circle", 14, .03, []],
            # ["outer",    "R", "square", 4,  .05, axis_list],
            # ["upcorner", "R", "circle", 14, .03, []],
            # ["upinner",  "R", "circle", 14, .03, []]
        ]

        ctlOptions.append(["upcenter", "C", "square", 4, .05, axis_list])
        for i in range(self.numInterControls):
            ctlOptions.append(["up{}".format(i), "L", "circle", 14, .03, []])

        ctlOptions.append(["outer", "L", "square", 4, .05, axis_list])
        for i in range(self.numInterControls):
            ctlOptions.append(["low{}".format(i), "L", "circle", 14, .03, []])

        ctlOptions.append(["lowcenter", "C", "square", 4, .05, axis_list])
        for i in reversed(range(self.numInterControls)):
            ctlOptions.append(["low{}".format(i), "R", "circle", 14, .03, []])

        ctlOptions.append(["outer", "R", "square", 4, .05, axis_list])
        for i in reversed(range(self.numInterControls)):
            ctlOptions.append(["up{}".format(i), "R", "circle", 14, .03, []])

        self.upNpos, self.upCtls = self._addControls(self.crv_ctl, ctlOptions)

        assert self.left_index > 0, "left_index is 0, could not find left most index, meaning x is not negative"
        assert self.right_index > 0, "right_index is 0, could not find right most index, meaning x is not positive"

        self.lips_C_upper_ctl  = self.upCtls[0]
        self.lips_C_lower_ctl  = self.upCtls[self.numInterControls * 2 + 2]

        self.lips_L_Corner_npo = self.upNpos[self.numInterControls + 1]
        self.lips_R_Corner_npo = self.upNpos[self.numInterControls * 3 + 3]

        # Connecting control crvs with controls
        applyop.gear_curvecns_op(self.crv_ctl, self.upCtls)

        # adding wires
        w1 = pm.wire(self.crv, w=self.crv_ctl, dropoffDistance=[0, self.size * 10])[0]
        w2 = pm.wire(self.rope, w=self.crv_ctl, dropoffDistance=[0, self.size * 10])[0]
        w3 = pm.wire(self.upv_crv, w=self.crv_ctl, dropoffDistance=[0, self.size * 10])[0]

        cmds.setAttr(w1.name() + ".rotation", 0.0)
        cmds.setAttr(w2.name() + ".rotation", 0.0)
        cmds.setAttr(w3.name() + ".rotation", 0.0)

    def addConstraints(self):
        def applyMultiCns(ctls, src1Index, src2Index, dstIndex, p1, p2):

            src1 = ctls[src1Index]
            src2 = ctls[src2Index]
            dst = ctls[dstIndex]

            src1Path = src1.longName()
            src2Path = src2.longName()
            dstPath = ctls[dstIndex].getParent().longName()

            r2, r1 = calcDistRatio(src1, src2, dst)

            cns_node = cmds.parentConstraint(src1Path, src2Path, dstPath, mo=True, skipRotate=("x", "y", "z"))[0]  # type: str
            attr1 = cns_node + "." + src1.name().split("|")[-1] + "W0"
            attr2 = cns_node + "." + src2.name().split("|")[-1] + "W1"

            cmds.setAttr(attr1, (r1 * 0.5) + (p1 * 0.5))
            cmds.setAttr(attr2, (r2 * 0.5) + (p2 * 0.5))

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
        nic = self.numInterControls  # shortcuts
        t = 0
        l = nic * 1 + 1  # noqa: E741
        b = nic * 2 + 2
        r = nic * 3 + 3
        for i in range(self.numInterControls):
            applyMultiCns(self.upCtls, t, l, nic * 0 + i + 1,  0.50, 0.25)
            applyMultiCns(self.upCtls, l, b, nic * 1 + i + 2,  0.20, 0.80)
            applyMultiCns(self.upCtls, b, r, nic * 2 + i + 3,  0.80, 0.20)
            applyMultiCns(self.upCtls, r, t, nic * 3 + i + 4,  0.25, 0.50)

    def _addControls(self, crv_ctl, option):

        cvs = self.getCurveCVs(crv_ctl)
        sum_cvs = datatypes.Vector()
        for cv in cvs:
            sum_cvs += cv

        center_pos = sum_cvs / len(cvs)  # type: ignore
        total_dist = sum([(x - center_pos).length() for x in cvs])
        average_dist = total_dist / len(cvs)

        distSize = average_dist * 5.0

        npos = []
        ctls = []
        params = ["tx", "ty", "tz", "rx", "ry", "rz"]

        for i, cv in enumerate(cvs):

            mirror = i > (len(cvs) / 2)
            lower = i > 2 and i < 6

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
                name = self.getName(oName + "_npo")
                npo = addTransform(self.ctl_root, name, t)
                npos.append(npo)

                name = self.getName(oName, side=oSide, ext=self.ctlName)
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

            ymt_util.setKeyableAttributesDontLockVisibility(ctl, params + oPar)
            self.addToSubGroup(ctl, self.primaryControllersGroupName)

        return npos, ctls

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
        raise
        self.parent.addChild(self.root)
        if self.surfRef:
            ref = self.rig.findComponent(self.surfRef)
            self.sliding_surface = ref.sliding_surface

    def connect_ghosts(self):

        corner_l_ref = self.rig.findRelative("mouthCorner_L0_root")
        corner_r_ref = self.rig.findRelative("mouthCorner_R0_root")

        if self.cheekLeftRef:
            query = self.cheekLeftRef.replace("_root", "_ctl")
            outer_l_ref = self.rig.findRelative(query)

            if not outer_l_ref:
                query = self.cheekLeftRef
                outer_l_ref = outer_l_ref.replace(query)

        else:
            outer_l_ref = self.root

        if self.cheekRightRef:
            query = self.cheekRightRef.replace("_root", "_ctl")
            outer_r_ref = self.rig.findRelative(query)

            if not outer_r_ref:
                query = self.cheekRightRef
                outer_r_ref = outer_r_ref.replace(query)

        else:
            outer_r_ref = self.root

        jaw_ctl_ref = self.rig.findRelative("mouth_C0_jaw")

        slide_c_comp = self.rig.findComponent("mouthSlide_C0_root")
        corner_l_comp = self.rig.findComponent("mouthCorner_L0_root")
        corner_r_comp = self.rig.findComponent("mouthCorner_R0_root")

        if outer_l_ref is None or outer_r_ref is None:
            logger.error("No outer mouth component found: mouthOuter_L0_root or mouthOuter_R0_root")
            raise Exception("No outer mouth component found: mouthOuter_L0_root or mouthOuter_R0_root")
            
        liplow_ref = self.parent_comp.liplow_ctl

        int_c = rigbits.createInterpolateTransform([jaw_ctl_ref, liplow_ref])
        int_l = rigbits.createInterpolateTransform([outer_l_ref, corner_l_ref], blend=0.8)
        int_r = rigbits.createInterpolateTransform([outer_r_ref, corner_r_ref], blend=0.8)
        pm.rename(int_c, int_c.name() + "_int")
        pm.rename(int_l, int_l.name() + "_int")
        pm.rename(int_r, int_r.name() + "_int")

        _drivers = self.connect_slide_ghost(
            int_c,
            self.lips_C_lower_ctl,
            int_l,
            int_r 
        )

        self.connect_mouth_ghost(liplow_ref)

        # remove elements from controllers group
        for comp in (slide_c_comp, corner_l_comp, corner_r_comp):
            if not comp:
                continue

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

    def connect_slide_ghost(self, intTra, slide_c_ref, outer_l_ref, outer_r_ref):

        # create ghost controls
        self.mouthSlide_ctl = self._createGhostCtl(slide_c_ref, intTra)

        # slide system
        drivers = ghostSliderForMouth(
            slide_c_ref,
            self.sliding_surface,
            self.sliding_surface.getParent()
        )
        drivers = ghostSliderForMouth2(
            [outer_l_ref, outer_r_ref],
            [self.lips_L_Corner_npo, self.lips_R_Corner_npo],
            self.sliding_surface,
            self.sliding_surface.getParent()
        )

        # connect scale
        pm.connectAttr(self.mouthSlide_ctl.scale, slide_c_ref.scale)

        # connect pucker
        cmds.setAttr("{}.tz".format(slide_c_ref.name()), l=False)
        pm.connectAttr(self.mouthSlide_ctl.tz, slide_c_ref.tz)

        ymt_util.setKeyableAttributesDontLockVisibility(slide_c_ref, [])
        ymt_util.setKeyableAttributesDontLockVisibility(outer_l_ref, [])
        ymt_util.setKeyableAttributesDontLockVisibility(outer_r_ref, [])

        return drivers

    def connect_mouth_ghost(self, liplow_ref):

        # center main controls
        self.lips_C_lower_ctl, lo_ghost_ctl = createGhostWithParentConstraint(self.lips_C_lower_ctl, liplow_ref)
        self._removeFromCtrlGroup(lo_ghost_ctl)
        self.addToSubGroup(self.lips_C_lower_ctl, self.primaryControllersGroupName)

        # add slider offset
        npos = rigbits.addNPO([self.lips_C_lower_ctl])
        for c in npos:
            rigbits.connectLocalTransform([self.mouthSlide_ctl, c])

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


def ghostSliderForMouth(ctlGhost, surface, sliderParent):
    """Modify the ghost control behaviour to slide on top of a surface

    Args:
        ghostControls (dagNode): The ghost control
        surface (Surface): The NURBS surface
        sliderParent (dagNode): The parent for the slider.
    """

    def conn(ctl, driver, ghost):
        for attr in ("translate", "scale", "rotate"):
            try:  # noqa: FURB107
                pm.connectAttr("{}.{}".format(ctl, attr), "{}.{}".format(driver, attr))
                pm.disconnectAttr("{}.{}".format(ctl, attr), "{}.{}".format(ghost, attr))
            except RuntimeError:
                pass

    def connCenter(ctl, driver, ghost):

        dm_node = ymt_util.getDecomposeMatrixOfAtoB(ctl, driver, skip_last=True)

        for attr in ("translate", "scale", "rotate"):
            pm.connectAttr("{}.output{}".format(dm_node, attr.capitalize()), "{}.{}".format(driver, attr))
            pm.disconnectAttr("{}.{}".format(ctl, attr), "{}.{}".format(ghost, attr))

    surfaceShape = surface.getShape()
    sliders = []
    drivers = []

    ctl = pm.listConnections(ctlGhost, t="transform")[-1]
    t = ctl.getMatrix(worldSpace=True)

    gDriver = primitive.addTransform(surface.getParent(), "{}_slideDriver".format(ctl.name()), t)
    drivers.append(gDriver)

    connCenter(ctl, gDriver, ctlGhost)

    oParent = ctlGhost.getParent()
    npoName = "_".join(ctlGhost.name().split("_")[:-1]) + "_npo"
    oTra = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))
    oTra.setTransformation(ctlGhost.getMatrix())
    pm.parent(ctlGhost, oTra)

    slider = primitive.addTransform(sliderParent, ctl.name() + "_slideDriven", t)
    sliders.append(slider)

    dm_node = node.createDecomposeMatrixNode(gDriver.attr("matrix"))

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
    for shape in ctlGhost.getShapes():
        pm.delete(shape)

    for slider in sliders[1:]:
        _visi_off_lock(slider)

    return drivers


def ghostSliderForMouth2(ghostControls, npos, surface, sliderParent):

    surfaceShape = surface.getShape()
    drivens = []

    for (ctlGhost, npo) in zip(ghostControls, npos):
        t = ctlGhost.getMatrix(worldSpace=True)

        driven = primitive.addTransform(sliderParent, ctlGhost.name() + "_slideDriven", t)
        drivens.append(driven)

        down, _, up = ymt_util.findPathAtoB(ctlGhost, sliderParent)
        dm_node = ymt_util.getDecomposeMatrixOfAtoB(ctlGhost, sliderParent, skip_last=True)
        cps_node = pm.createNode("closestPointOnSurface")
        dm_node.attr("outputTranslate") >> cps_node.attr("inPosition")
        surfaceShape.attr("local") >> cps_node.attr("inputSurface")
        cps_node.attr("position") >> driven.attr("translate")
        pm.parentConstraint(ctlGhost, npo, mo=True)

        ymt_util.setKeyableAttributesDontLockVisibility(driven, [])
        for shape in ctlGhost.getShapes():
            pm.delete(shape)

    for driven in drivens:
        _visi_off_lock(driven)


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
        with ymt_util.unlockAttribute(ctl.longName()):
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
