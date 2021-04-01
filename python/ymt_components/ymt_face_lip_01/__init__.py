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

from mgear import rigbits
from mgear.rigbits import ghost
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

        # print(len(self.uplocsPos), self.num_uplocs, self.uplocsPos)
        # print(len(self.lowlocsPos),self.num_lowlocs,  self.lowlocsPos)

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

        self.thickness = 0.3
        self.FRONT_OFFSET = .02
        self.NB_ROPE = 15

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

        self.addContainers()

        self.addCurve()
        self.addControlJoints()
        self.addControllers()
        self.addConstraints()

    def addContainers(self):

        t = getTransform(self.root)

        self.crv_root = addTransform(self.root, self.getName("crvs"), t)
        self.lipsRope_root = addTransform(self.root, self.getName("rope"), t)

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

        plane = self.addDummyPlane()

        self.addCurves(self.crv_root, plane)
        self.addCurveBaseControllers(self.crv_root, plane)
        pm.delete(pm.PyNode(plane.name()))

    def addCurves(self, crv_root, plane):

        t = getTransform(self.root)
        gen = curve.createCurveFromOrderedEdges
        planeNode = pm.PyNode(plane.fullPathName())

        # -------------------------------------------------------------------
        def _inner(edges, name):
            crv = gen(edges, planeNode.verts[1], self.getName("{}Crv".format(name)), parent=crv_root, m=t)
            ctl = gen(edges, planeNode.verts[1], self.getName("{}Ctl_crv".format(name)), parent=crv_root, m=t)
            crv.attr("visibility").set(False)
            ctl.attr("visibility").set(False)

            cvs = crv.getCVs(space="world")
            for i, cv in enumerate(cvs):

                if i == 0:
                    # we know the curv starts from right to left
                    offset = [cv[0] - self.thickness, cv[1], cv[2] - self.thickness]

                elif i == len(cvs) - 1:
                    offset = [cv[0] + self.thickness, cv[1], cv[2] - self.thickness]

                else:
                    offset = [cv[0], cv[1] + self.thickness, cv[2]]

                crv.setCV(i, offset, space='world')

            return crv, ctl

        # -------------------------------------------------------------------
        edgeList = ["{}.e[{}]".format(plane.fullPathName(), 0)]
        for i in range(1, self.num_uplocs + 1):
            edgeList.append("{}.e[{}]".format(plane.fullPathName(), i * 2 + 1))
        edgeList = [pm.PyNode(x) for x in edgeList]
        self.upCrv, self.upCrv_ctl = _inner(edgeList, "upper")

        # -------------------------------------------------------------------
        edgeList = []
        for i in reversed(range(self.num_uplocs + 1, self.num_uplocs + self.num_lowlocs + 2)):
            edgeList.append("{}.e[{}]".format(plane.fullPathName(), i * 2 + 1))
        edgeList = [pm.PyNode(x) for x in edgeList]
        self.lowCrv, self.lowCrv_ctl = _inner(edgeList, "lower")

    def addCurveBaseControllers(self, crv_root, plane):

        def gen2(crv, name, nbPoints, tobe_offset):
            t = getTransform(self.root)

            new_crv = curve.createCurveFromCurve(crv, self.getName(name), nbPoints=nbPoints, parent=crv_root, m=t)
            new_crv.attr("visibility").set(False)

            # double translation denial
            cvs = new_crv.getCVs(space="world")
            for i, cv in enumerate(cvs):
                x, y, z = transform.getTranslation(new_crv)
                offset = [cv[0] - x, cv[1] - y, cv[2] - z]
                new_crv.setCV(i, offset, space='world')

            if not tobe_offset:
                return new_crv

            cvs = new_crv.getCVs(space="world")
            for i, cv in enumerate(cvs):

                # we populate the closest vertext list here to skipt the first
                # and latest point
                offset = [cv[0], cv[1], cv[2] + self.FRONT_OFFSET]

                new_crv.setCV(i, offset, space='world')

            return new_crv

        # -------------------------------------------------------------------
        self.upCrv_ctl   = gen2(self.upCrv,  "upCtl_crv",   7, False)
        self.lowCrv_ctl  = gen2(self.lowCrv, "lowCtl_crv",  7, False)

        self.upRope      = gen2(self.upCrv,  "upRope_crv",  self.NB_ROPE, False)
        self.lowRope     = gen2(self.lowCrv, "lowRope_crv", self.NB_ROPE, False)

        self.upCrv_upv   = gen2(self.upCrv,  "upCtl_upv",   7, True)
        self.lowCrv_upv  = gen2(self.lowCrv, "lowCtl_upv",  7, True)

        self.upRope_upv  = gen2(self.upCrv,  "upRope_upv",  self.NB_ROPE, True)
        self.lowRope_upv = gen2(self.lowCrv, "lowRope_upv", self.NB_ROPE, True)

    def addControlJoints(self):
        self.upJoints = self._addControlJoints(self.upCrv, "up", self.lipsRope_root, self.upRope, self.upRope_upv)
        self.lowJoints = self._addControlJoints(self.lowCrv, "low", self.lipsRope_root, self.lowRope, self.lowRope_upv)

    def _addControlJoints(self, crv, name, rope_root, rope, rope_upv):

        lvlType = "transform"
        cvs = crv.getCVs(space="world")
        local_cvs = crv.getCVs(space="object")
        controls = []
        t = getTransform(self.root)

        icon_shape = "sphere"
        color = 4
        wd = .3
        po = self.offset * 0.3

        pm.progressWindow(title='Creating Upper Joints', progress=0, max=len(cvs))

        for i, cv in enumerate(cvs):
            pm.progressWindow(e=True, step=1, status='\nCreating Joint for  %s' % cv)

            upv = addTransform(rope_root, self.getName("{}LipRope_upv{}".format(name, str(i).zfill(3))))
            npo = addTransform(rope_root, self.getName("{}LipRope_npo{}".format(name, str(i).zfill(3))))

            oParam, oLength = curve.getCurveParamAtPosition(rope, local_cvs[i])
            uLength = curve.findLenghtFromParam(rope, oParam)
            u = uLength / oLength

            cns = applyop.pathCns(upv, rope_upv, cnsType=False, u=u, tangent=False)
            pm.connectAttr(rope_upv.attr("local"), cns.attr("geometryPath"), f=True)  # tobe local space

            cns = applyop.pathCns(npo, rope, cnsType=False, u=u, tangent=False)
            pm.connectAttr(rope.attr("local"), cns.attr("geometryPath"), f=True)  # tobe local space
            cns.setAttr("worldUpType", 1)
            cns.setAttr("frontAxis", 0)
            cns.setAttr("upAxis", 1)

            pm.connectAttr(upv.attr("worldMatrix[0]"), cns.attr("worldUpMatrix"))

            ctl_name = self.getName("crvdetail%s_%s" % (i, self.ctlName))

            if i == 0:
                # we know the curv starts from right to left
                offset = [cv[0] + self.thickness, cv[1], cv[2] + self.thickness]

            elif i == len(cvs) - 1:
                offset = [cv[0] - self.thickness, cv[1], cv[2] + self.thickness]

            else:
                offset = [cv[0], cv[1] - self.thickness, cv[2]]

            # offset = [cv[0], cv[1], cv[2] - self.FRONT_OFFSET]
            xform = setMatrixPosition(t, offset)
            # xform = setMatrixPosition(t, cv)
            ctl = self.addCtl(
                npo,
                ctl_name,
                xform,
                color,
                icon_shape,
                w=wd,
                d=wd,
                ro=datatypes.Vector(1.57079633, 0, 0),
                po=po
            )

            controls.append(ctl)

            # getting joint parent
            # jnt = rigbits.addJnt(npo, noReplace=True, parent=self.j_parent)
            self.jnt_pos.append([ctl, "{}{}".format(name, i)])

        pm.progressWindow(e=True, endProgress=True)
        return controls

    def addControllers(self):
        axis_list = ["sx", "sy", "sz", "ro"]
        upCtlOptions = [["corner", "R", "square", 4, .05, axis_list],
                        ["upOuter", "R", "circle", 14, .03, []],
                        ["upInner", "R", "circle", 14, .03, []],
                        ["upper", "C", "square", 4, .05, axis_list],
                        ["upInner", "L", "circle", 14, .03, []],
                        ["upOuter", "L", "circle", 14, .03, []],
                        ["corner", "L", "square", 4, .05, axis_list]]

        lowCtlOptions = [["lowOuter", "R", "circle", 14, .03, []],
                         ["lowInner", "R", "circle", 14, .03, []],
                         ["lower", "C", "square", 4, .05, axis_list],
                         ["lowInner", "L", "circle", 14, .03, []],
                         ["lowOuter", "L", "circle", 14, .03, []]]

        self.upNpos, self.upCtls, self.upUpvs = self._addControls(self.upCrv_ctl, upCtlOptions, False)
        self.lowNpos, self.lowCtls, self.lowUpvs = self._addControls(self.lowCrv_ctl, lowCtlOptions, True)

        self.lips_R_Corner_ctl   = self.upCtls[0]
        self.lips_R_upOuter_ctl  = self.upCtls[1]
        self.lips_R_upInner_ctl  = self.upCtls[2]
        self.lips_C_upper_ctl    = self.upCtls[3]
        self.lips_L_upInner_ctl  = self.upCtls[4]
        self.lips_L_upOuter_ctl  = self.upCtls[5]
        self.lips_L_Corner_ctl   = self.upCtls[6]

        self.lips_R_lowOuter_ctl = self.lowCtls[0]
        self.lips_R_lowInner_ctl = self.lowCtls[1]
        self.lips_C_lower_ctl    = self.lowCtls[2]
        self.lips_L_lowInner_ctl = self.lowCtls[3]
        self.lips_L_lowOuter_ctl = self.lowCtls[4]

        self.lips_R_Corner_npo   = self.upNpos[0]
        self.lips_R_upOuter_npo  = self.upNpos[1]
        self.lips_R_upInner_npo  = self.upNpos[2]
        self.lips_C_upper_npo    = self.upNpos[3]
        self.lips_L_upInner_npo  = self.upNpos[4]
        self.lips_L_upOuter_npo  = self.upNpos[5]
        self.lips_L_Corner_npo   = self.upNpos[6]

        self.lips_R_lowOuter_npo = self.lowNpos[0]
        self.lips_R_lowInner_npo = self.lowNpos[1]
        self.lips_C_lower_npo    = self.lowNpos[2]
        self.lips_L_lowInner_npo = self.lowNpos[3]
        self.lips_L_lowOuter_npo = self.lowNpos[4]

        upvec = self.upUpvs + self.lowUpvs

        pm.parent(self.lips_R_upOuter_npo,  self.lips_R_lowOuter_npo,  self.upCtls[0])
        pm.parent(self.lips_R_upInner_npo,  self.lips_L_upInner_npo,   self.upCtls[3])
        pm.parent(self.lips_L_lowInner_npo, self.lips_L_lowOuter_npo,  self.upCtls[-1])
        pm.parent(self.lips_R_lowInner_npo, self.lips_L_lowInner_npo,  self.lowCtls[2])

        # Connecting control crvs with controls
        applyop.gear_curvecns_op(self.upCrv_ctl, self.upCtls)
        applyop.gear_curvecns_op(self.lowCrv_ctl,
                                 [self.upCtls[0]] + self.lowCtls + [self.upCtls[-1]])

        applyop.gear_curvecns_op(self.upCrv_upv, upvec)
        applyop.gear_curvecns_op(self.lowCrv_upv, [upvec[0]] + self.lowUpvs + [upvec[-1]])

        # adding wires
        pm.wire(self.upCrv, w=self.upCrv_ctl, dropoffDistance=[0, 1000])
        pm.wire(self.lowCrv, w=self.lowCrv_ctl, dropoffDistance=[0, 1000])
        pm.wire(self.upRope, w=self.upCrv_ctl, dropoffDistance=[0, 1000])
        pm.wire(self.lowRope, w=self.lowCrv_ctl, dropoffDistance=[0, 1000])

        pm.wire(self.upRope_upv, w=self.upCrv_upv, dropoffDistance=[0, 1000])
        pm.wire(self.lowRope_upv, w=self.lowCrv_upv, dropoffDistance=[0, 1000])

        return

    def addConstraints(self):

        def __upper(ctls, s1, s2, d, p1, p2):
            s1o = ctls[s1]
            s2o = ctls[s2]
            do = ctls[d].getParent()

            cns_node = pm.parentConstraint(s1o, s2o, do, mo=True, skipRotate=["x", "y", "z"])
            cns_node.attr(ctls[s1].name() + "W0").set(p1)
            cns_node.attr(ctls[s2].name() + "W1").set(p2)

        def __lower(s1, s2, d, p1, p2):
            cns_node = pm.parentConstraint(s1, s2, d.getParent(), mo=True, skipRotate=["x", "y", "z"])
            cns_node.attr(s1.name() + "W0").set(p1)
            cns_node.attr(s2.name() + "W1").set(p2)

        __upper(self.upCtls, 0, 3, 1, 0.75, 0.25)
        __upper(self.upCtls, 0, 3, 2, 0.25, 0.75)
        __upper(self.upCtls, 3, 6, 4, 0.75, 0.25)
        __upper(self.upCtls, 3, 6, 5, 0.25, 0.75)

        __lower(self.upCtls[0], self.lowCtls[2], self.lowCtls[0], 0.75, 0.25)
        __lower(self.upCtls[0], self.lowCtls[2], self.lowCtls[1], 0.25, 0.75)
        __lower(self.lowCtls[2], self.upCtls[6], self.lowCtls[3], 0.75, 0.25)
        __lower(self.lowCtls[2], self.upCtls[6], self.lowCtls[4], 0.25, 0.75)

        return

    def _addControls(self, crv_ctl, option, sidecut):

        cvs = crv_ctl.getCVs(space="world")

        pm.progressWindow(title='controls', progress=0, max=len(cvs))

        v0 = transform.getTransformFromPos(cvs[0])
        v1 = transform.getTransformFromPos(cvs[-1])
        distSize = vector.getDistance(v0, v1) * 3

        npos = []
        ctls = []
        upvs = []
        params = ["tx", "ty", "tz", "rx", "ry", "rz"]
        joints = self.upJoints + self.lowJoints

        iterator = enumerate(cvs)
        if sidecut:
            iterator = enumerate(cvs[1:-1])

        for i, cv in iterator:

            pm.progressWindow(e=True, step=1, status='\nCreating control for%s' % cv)

            t = transform.getTransformFromPos(cv)

            # Get nearest joint for orientation of controls
            nearest_joint = None
            nearest_distance = None

            for joint in joints:
                distance = vector.getDistance(transform.getTranslation(joint), cv)
                if distance < nearest_distance or nearest_distance is None:
                    nearest_distance = distance
                    nearest_joint = joint

            if nearest_joint:

                t = transform.setMatrixPosition(transform.getTransform(nearest_joint), cv)
                temp = addTransform(self.root, self.getName("temp"), t)
                temp.rx.set(0)
                t = transform.getTransform(temp)
                pm.delete(temp)

            oName  = option[i][0]
            oSide  = option[i][1]
            o_icon = option[i][2]
            color  = option[i][3]
            wd     = option[i][4]
            oPar   = option[i][5]

            npo = addTransform(self.root, self.getName("%s_npo" % oName, oSide), t)
            npos.append(npo)

            ctl = self.addCtl(npo,
                              self.getName("{}_{}".format(oName, self.ctlName), oSide),
                              t,
                              color,
                              o_icon,
                              w=wd * distSize,
                              d=wd * distSize,
                              ro=datatypes.Vector(1.57079633, 0, 0),
                              po=datatypes.Vector(0, 0, .07 * distSize),
                              )

            ctls.append(ctl)

            attribute.setKeyableAttributes(ctl, params + oPar)

            upv = addTransform(ctl, self.getName("%s_upv" % oName, oSide), t)
            upv.attr("tz").set(self.FRONT_OFFSET)
            upvs.append(upv)

            if oSide == "R":
                npo.attr("sx").set(-1)

        pm.progressWindow(e=True, endProgress=True)

        return npos, ctls, upvs

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
        self.connections["mouth_01"] = self.connect_mouth
        self.connections["mouth_02"] = self.connect_mouth

    def connect_mouth(self):

        if self.parent is None:
            return

        self.parent.addChild(self.root)

        try:
            self.connect_ghosts()

        except Exception as e:
            import traceback
            traceback.print_exc()

            raise

    def connect_standard(self):
        print("ccccccccccccccccccc")

        self.parent.addChild(self.root)

        return

    def connect_ghosts(self):

        lipup_ref = self.parent_comp.lipup_ctl
        liplow_ref = self.parent_comp.liplow_ctl
        slide_c_ref = self.rig.findRelative("mouthSlide_C0_root")
        corner_l_ref = self.rig.findRelative("mouthCorner_L0_root")
        corner_r_ref = self.rig.findRelative("mouthCorner_R0_root")

        self.connect_slide_ghost(lipup_ref, liplow_ref, slide_c_ref, corner_l_ref, corner_r_ref)
        self.connect_mouth_ghost(lipup_ref, liplow_ref, slide_c_ref, corner_l_ref, corner_r_ref)

    def connect_slide_ghost(self, lipup_ref, liplow_ref, slide_c_ref, corner_l_ref, corner_r_ref):

        self.sliding_surface = pm.duplicate(self.guide.getObjects(self.guide.root)["sliding_surface"])[0]
        pm.parent(self.sliding_surface, self.root)
        self.sliding_surface.visibility.set(False)

        # create interpose lvl for the ctl
        intTra = rigbits.createInterpolateTransform([lipup_ref, liplow_ref])
        pm.rename(intTra, intTra.name() + "_int")

        # create ghost controls
        self.mouthSlide_ctl = ghost.createGhostCtl(slide_c_ref, intTra)
        self.cornerL_ctl = ghost.createGhostCtl(corner_l_ref, slide_c_ref)
        self.cornerR_ctl = ghost.createGhostCtl(corner_r_ref, slide_c_ref)
        # self.cornerL_ctl = createGhostWithParentConstraint(corner_l_ref, slide_c_ref)
        # self.cornerR_ctl = createGhostWithParentConstraint(corner_r_ref, slide_c_ref)

        # pm.parent(corner_l_ref.parent, slide_c_ref)
        # pm.parent(corner_r_ref.parent, slide_c_ref)
        # attribute.setKeyableAttributes(self.lips_L_Corner_npo)
        # attribute.setKeyableAttributes(self.lips_R_Corner_npo)

        # slide system
        ghostSliderForMouth(
            [slide_c_ref, corner_l_ref, corner_r_ref],
            intTra,
            self.sliding_surface,
            self.root)

        # connect scale
        pm.connectAttr(self.mouthSlide_ctl.scale, slide_c_ref.scale)
        pm.connectAttr(self.cornerL_ctl.scale, corner_l_ref.scale)
        pm.connectAttr(self.cornerR_ctl.scale, corner_r_ref.scale)

        # connect pucker
        pm.connectAttr(self.mouthSlide_ctl.tz, slide_c_ref.tz)

        pm.parentConstraint(corner_l_ref, self.lips_L_Corner_npo, mo=True)
        pm.parentConstraint(corner_r_ref, self.lips_R_Corner_npo, mo=True)

    def connect_mouth_ghost(self, lipup_ref, liplow_ref, slide_c_ref, corner_l_ref, corner_r_ref):

        # center main controls
        # self.lips_C_upper_ctl = ghost.createGhostCtl(self.lips_C_upper_ctl, lipup_ref)
        # self.lips_C_lower_ctl = ghost.createGhostCtl(self.lips_C_lower_ctl, liplow_ref)
        self.lips_C_upper_ctl = createGhostWithParentConstraint(self.lips_C_upper_ctl, lipup_ref)
        self.lips_C_lower_ctl = createGhostWithParentConstraint(self.lips_C_lower_ctl, liplow_ref)

        # unlock all the attributes in the upper and lower lip control
        # attribute.setKeyableAttributes(self.lips_C_upper_ctl)
        # attribute.setKeyableAttributes(self.lips_C_lower_ctl)

        # add slider offset
        npos = rigbits.addNPO([self.lips_C_upper_ctl, self.lips_C_lower_ctl])
        for c in npos:
            rigbits.connectLocalTransform([self.mouthSlide_ctl, c])
            # pm.parentConstraint(slide_c_ref, c, mo=True)

        # Left side controls
        self.lips_L_upInner_ctl = createGhostWithParentConstraint(self.lips_L_upInner_ctl, self.lips_C_upper_ctl)
        self.lips_L_lowInner_ctl = createGhostWithParentConstraint(self.lips_L_lowInner_ctl, self.lips_C_lower_ctl)

        # Right side controls
        self.lips_R_upInner_ctl = createGhostWithParentConstraint(self.lips_R_upInner_ctl, self.lips_C_upper_ctl)
        self.lips_R_lowInner_ctl = createGhostWithParentConstraint(self.lips_R_lowInner_ctl, self.lips_C_lower_ctl)

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

        pass
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
            try:
                pm.connectAttr("{}.{}".format(ctl, attr), "{}.{}".format(driver, attr))
                pm.disconnectAttr("{}.{}".format(ctl, attr), "{}.{}".format(ghost, attr))
            except RuntimeError:
                pass

    def connCenter(ctl, driver, ghost):
        mul_node1 = pm.createNode("multMatrix")
        mul_node2 = pm.createNode("multMatrix")
        intTra.attr("matrix") >> mul_node1.attr("matrixIn[0]")
        mul_node1.attr("matrixIn[1]")
        pm.setAttr(mul_node1 + ".matrixIn[1]",
                   intTra.attr("inverseMatrix").get(),
                   type="matrix")
        ctl.attr("matrix") >> mul_node2.attr("matrixIn[0]")
        mul_node1.attr("matrixSum") >> mul_node2.attr("matrixIn[1]")
        dm_node = node.createDecomposeMatrixNode(mul_node2.attr("matrixSum"))

        for attr in ["translate", "scale", "rotate"]:
            pm.connectAttr("{}.output{}".format(dm_node, attr.capitalize()), "{}.{}".format(driver, attr))
            pm.disconnectAttr("{}.{}".format(ctl, attr), "{}.{}".format(ghost, attr))

    surfaceShape = surface.getShape()
    sliders = []

    for i, ctlGhost in enumerate(ghostControls):
        ctl = pm.listConnections(ctlGhost, t="transform")[-1]
        t = ctl.getMatrix(worldSpace=True)

        gDriver = primitive.addTransform(ctlGhost.getParent(), "{}_slideDriver".format(ctl.name()), t)
        if 0 == i:
            connCenter(ctl, gDriver, ctlGhost)

        else:
            conn(ctl, gDriver, ctlGhost)

        oParent = ctlGhost.getParent()
        npoName = "_".join(ctlGhost.name().split("_")[:-1]) + "_npo"
        oTra = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))
        oTra.setTransformation(ctlGhost.getMatrix())
        pm.parent(ctlGhost, oTra)

        slider = primitive.addTransform(sliderParent, ctl.name() + "_slideDriven", t)
        sliders.append(slider)

        # connexion
        if 0 == i:
            dm_node = node.createDecomposeMatrixNode(gDriver.attr("matrix"))

        else:
            mul_node = pm.createNode("multMatrix")
            i = 0
            parent = ctl
            while parent != sliderParent:
                parent.attr("matrix") >> mul_node.attr("matrixIn[{}]".format(i))
                parent = parent.getParent()
                print(parent)
                i += 1
                if 10 < i:
                    logger.error("maximum recursion")
                    break

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

    sliders[0].visibility.set(False)
    attribute.setKeyableAttributes(sliders[0], [])


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
    if isinstance(ctl, basestring):
        ctl = pm.PyNode(ctl)
    if parent:
        if isinstance(parent, basestring):
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

    return newCtl


if __name__ == "__main__":
    pass
