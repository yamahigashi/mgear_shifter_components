"""mGear shifter components"""
# pylint: disable=import-error,W0201,C0111,C0112
import re
import sys
import six
import inspect
import textwrap
import math

import maya.cmds as cmds
import maya.api.OpenMaya as om

import pymel.core as pm
from pymel.core import datatypes

import exprespy.cmd
from mgear.shifter import component

from mgear.core import (
    # transform,
    # primitive,
    curve,
    applyop,
)

from mgear.core import (
    attribute,
    node,
    icon,
    # fcurve,
    vector,
)

from mgear.core.transform import (
    getTransform,
    setMatrixPosition,
    getTransformLookingAt,
)

from mgear.core.primitive import addTransform

import ymt_shifter_utility as ymt_util
from . import twistSplineBuilder as tsBuilder

from logging import (  # noqa:F401 pylint: disable=unused-import, wrong-import-order
    StreamHandler,
    getLogger,
    WARN,
    DEBUG,
    INFO
)

if sys.version_info >= (3, 0):
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
    import pathlib

logger = getLogger(__name__)
logger.setLevel(INFO)
# logger.setLevel(WARN)
# logger.setLevel(WARN)


# Naming Convention
tsBuilder.DFM_ORG_FMT = "{0}_deformers"  # Deformer Organizer
tsBuilder.DFM_BFR_FMT = "{0}_riderPart{1:02d}"  # Rider Buffer
tsBuilder.DFM_FMT = "{0}_riderPart{1:02d}_jnt"  # Deformer
tsBuilder.SPLINE_FMT = "{0}_driver"  # Spline name
tsBuilder.MASTER_FMT = "{}_SplineGlobal_ctl"  # Global control
tsBuilder.CTRL_ORG_FMT = "{0}_Ctrls"  # Control organizer
tsBuilder.BFR_CV_FMT = "{0}_splinePartBuffer{1:02d}"  # CV Buffer
tsBuilder.CTRL_CV_FMT = "{0}_ik{1:02d}_ctl"  # CV
tsBuilder.BFR_TWIST_FMT = "{0}_twistPart_{1:02d}_npo"  # Twist Buffer
tsBuilder.CTRL_TWIST_FMT = "{0}_rot{1:02d}_ctl"  # Twist
tsBuilder.CTRL_INTAN_FMT = "{0}_in{1:02d}_ctl"  # In-Tangent
tsBuilder.CTRL_OUTTAN_FMT = "{0}_out{1:02d}_ctl"  # Out-Tangent
tsBuilder.BFR_AINTAN_FMT = "{0}_autoIn{1:02d}"  # Auto In-Tangent Buffer
tsBuilder.BFR_AOUTTAN_FMT = "{0}_autoOut{1:02d}"  # Auto Out-Tangent Buffer



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

        # FIXME: remove unneccessary guide.tan
        self.guide.apos.pop()

        self.divisions = len(self.guide.apos)

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
        self.previusTag = self.parentCtlTag

        self.length_ctl = None
        self.div_cns = []
        self.div_cns_npo = []
        self.div_roll_npo = []
        self.fk_ctl = []
        self.fk_npo = []
        self.fk_local_npo = []
        self.scl_transforms = []
        self.twister = []
        self.ref_twist = []
        self.fk_global_in = []
        self.fk_local_in = []
        self.fk_local_in2 = []
        self.fk_global_out = []
        self.fk_global_ref = []
        self.fk_uv_param = []
        self.ikNb = self.settings["ikNb"]

        # IK controls ---------------------------------------------
        self.dummy_crv = curve.addCurve(
            self.root,
            self.getName("dummy_crv"),
            self.guide.apos,
            close=False,
            degree=min([len(self.guide.apos) - 1, 3])
        )
        cmds.nurbsCurveToBezier()
        self.length = self.dummy_crv.length()
        self.division = len(self.guide.apos)

        tmpRes = self.convertToTwistSpline(self.guide.apos, self.dummy_crv, self.ikNb)
        self.ik_ctl, self.in_ctl, self.out_ctl, self.bts_joints, self.master_ctl, self.mst_crv = tmpRes
        self.ik_ctl = [pm.PyNode(x) for x in self.ik_ctl]
        self.in_ctl = [pm.PyNode(x) for x in self.in_ctl]
        self.out_ctl = [pm.PyNode(x) for x in self.out_ctl]
        self.bts_joints = [pm.PyNode(x) for x in self.bts_joints]
        self.master_ctl = pm.PyNode(self.master_ctl)
        self.fk_ctl = self.addObjectsFkControl(self.bts_joints)

        # add npo
        t = getTransform(self.guide.root)
        self.aim_npo = addTransform(self.root, self.getName("aim_npo"), t)

        self.addLengthCtrl(self.dummy_crv)
        pm.delete(self.dummy_crv)

        # icon.connection_display_curve(self.getName("visualIKRef"), self.ik_ctl)

    def addObjectsFkControl(self, joints):

        parentdiv = self.root
        parentctl = self.root

        parent_twistRef = addTransform(
            self.root,
            self.getName("reference"),
            getTransform(self.root))

        self.jointList = []
        self.preiviousCtlTag = self.parentCtlTag

        for i, j in enumerate(joints):
            jt = getTransform(pm.PyNode(j))
            pt = setMatrixPosition(jt, self.guide.apos[i])

            parentdiv, parentctl = self._addObjectsFkControl(i, parentdiv, parentctl, jt, pt, parent_twistRef)

        # add visual reference
        icon.connection_display_curve(self.getName("visualFKRef"), self.fk_ctl)
        return self.fk_ctl

    def addLengthCtrl(self, crv):
        t = getTransform(self.guide.root)
        t = self._getTransformWithRollByBlade(t)
        cvs = crv.length()
        tm = datatypes.TransformationMatrix(t)
        tm.addTranslation([0.0, cvs * 0.01, cvs * 1.4], om.MSpace.kObject)

        local_t = datatypes.Matrix(tm)
        self.length_npo = addTransform(self.aim_npo, self.getName("length_npo"), local_t)
        self.length_in = addTransform(self.length_npo, self.getName("sacle_in"), local_t)
        size = self.size
        w = size
        h = size
        d = size
        self.length_ctl = self.addCtl(
            self.length_in,
            "length_ctl",
            local_t,
            self.color_ik,
            "arrow",
            w=w,
            h=h,
            d=d,
            ro=datatypes.Vector([-math.pi / 2., math.pi / 2., 0.])
        )

        # global input
        self.scale_npo = addTransform(self.root, self.getName("scale_npo"), local_t)
        self.scale_in = addTransform(self.scale_npo, self.getName("sacle_in"), local_t)

        self.scale_ctl = self.addCtl(
            self.scale_in,
            "scale_ctl",
            local_t,
            self.color_ik,
            "cube",
            w=w*.2,
            h=h*.2,
            d=d*.2,
            ro=datatypes.Vector([-math.pi / 2., 0., 0.])
        )

        ymt_util.setKeyableAttributesDontLockVisibility(self.scale_ctl, self.s_params)
        ymt_util.setKeyableAttributesDontLockVisibility(self.length_ctl, ["tx", "ty", "tz"])

    def _getTransformWithRollByBlade(self, t):
        # t = getTransform(self.guide.root)
        a = self.guide.blades["blade"].y
        x = vector.Blade(t).x
        z = vector.Blade(t).z

        x = vecProjection(a, x)[0]
        z = vecProjection(a, z)[2]
        theta = math.atan2(x, z)
        roll = theta + math.pi

        tm = datatypes.TransformationMatrix(t)
        tm.addRotation([0., roll, 0], 'XYZ', om.MSpace.kObject)

        return datatypes.Matrix(tm)

    def _addObjectsFkControl(self, i, parentdiv, parentctl, t, pt, parent_twistRef):
        # References
        tm = datatypes.TransformationMatrix(t)
        tm.addRotation([0., 0., math.pi / -2.], 'XYZ', om.MSpace.kObject)  # TODO: align with convention
        tm.addRotation([0., math.pi / -2., 0], 'XYZ', om.MSpace.kObject)
        global_t  = datatypes.Matrix(tm)

        tm = datatypes.TransformationMatrix(pt)
        tm.addRotation([0., 0., math.pi / -2.], 'XYZ', om.MSpace.kObject)  # TODO: align with convention
        tm.addRotation([0., math.pi / -2., 0], 'XYZ', om.MSpace.kObject)
        local_t  = datatypes.Matrix(tm)

        # global input
        div_cns = addTransform(parentdiv, self.getName("%s_cns" % i))
        div_cns_npo = addTransform(div_cns, self.getName("%s_cns_npo" % i))
        div_roll_npo = addTransform(div_cns_npo, self.getName("%s_roll_npo" % i))
        # pm.setAttr(div_cns + ".inheritsTransform", False)
        div_cns.setMatrix(global_t, worldSpace=True)
        div_cns_npo.setMatrix(local_t, worldSpace=True)
        self.div_cns.append(div_cns)
        self.div_cns_npo.append(div_cns_npo)
        self.div_roll_npo.append(div_roll_npo)
        parentdiv = div_cns

        # t = getTransform(parentctl)
        if i == 0:
            p = parentctl
        else:
            # p = self.scl_transforms[i - 1]
            p = self.fk_local_in[i - 1]

        fk_npo = addTransform(p, self.getName("fk%s_npo" % (i)), global_t)
        # local input
        fk_local_npo = addTransform(fk_npo, self.getName("fk%s_local_npo" % i), global_t)  # for switch to inherit parent rot
        fk_local_in = addTransform(fk_local_npo, self.getName("fk%s_local_in" % i), global_t)
        fk_local_in2 = addTransform(fk_local_in, self.getName("fk%s_local_in2" % i), local_t)  # for sine wave
        self.fk_local_in.append(fk_local_in)
        self.fk_local_in2.append(fk_local_in2)

        if i == len(self.guide.apos) - 1:
            self.fk_local_npo2 = addTransform(fk_local_in2, self.getName("fk%s_local_npo2" % i), local_t)
            fk_local_in2 = self.fk_local_npo2

        if i < len(self.guide.apos) - 1:
            h = (self.guide.apos[i] - self.guide.apos[i + 1]).length() * .8
        else:
            h = (self.guide.apos[-1] - self.guide.apos[0]).length() / (len(self.guide.apos) - 1)

        # FIXME: rotate by blade
        if self.negate:
            po = datatypes.Vector([0, h / -2., 0])
        else:
            po = datatypes.Vector([0, h / 2., 0])

        fk_ctl = self.addCtl(
            fk_local_in2,
            "fk%s_ctl" % (i),
            local_t,
            self.color_fk,
            "cube",
            w=self.length * (1. / self.division) * 1.3,
            # h=h,
            h=self.length * (1. / self.division) * 0.1,
            d=self.length * (1. / self.division) * 2.6,
            # ro=datatypes.Vector([0, -math.pi / 2., 0]),
            po=po,
            tp=self.preiviousCtlTag,
            mirrorConf=self.mirror_conf)

        ymt_util.setKeyableAttributesDontLockVisibility(self.fk_ctl)
        attribute.setRotOrder(fk_ctl, "ZXY")
        self.fk_ctl.append(fk_ctl)
        self.preiviousCtlTag = fk_ctl

        self.fk_npo.append(fk_npo)
        self.fk_local_npo.append(fk_local_npo)
        parentctl = fk_ctl
        scl_ref = addTransform(parentctl, self.getName("%s_scl_ref" % i), getTransform(parentctl))
        self.scl_transforms.append(scl_ref)

        # Deformers (Shadow)
        if self.settings["addJoints"]:
            self.jnt_pos.append([scl_ref, i])

        # Twist references (This objects will replace the spinlookup
        # slerp solver behavior)

        return parentdiv, parentctl

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        if not self.settings["ui_host"]:
            self.uihost = self.length_ctl

        if self.settings["ik0refarray"]:
            ref_names = self.get_valid_alias_list(
                self.settings["ik0refarray"].split(","))

            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam(
                    "ik0ref",
                    "Ik0 Ref",
                    0,
                    ref_names)

        if self.settings["ik1refarray"]:
            ref_names = self.get_valid_alias_list(
                self.settings["ik1refarray"].split(","))

            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam(
                    "ik1ref",
                    "Ik1 Ref",
                    0,
                    ref_names)

        self.fk_collapsed_att = self.addAnimParam(
            "traditional_fk",
            "Traditional FK",
            "bool",
            False
        )

        self.sinewave_power_y_att = self.addAnimParam(
            "sinewave_power_y",
            "SineWave Power Y",
            "double",
            0.,
            0.,
            255
        )

        self.sinewave_wavelength_y_att = self.addAnimParam(
            "sinewave_wavelength_y",
            "SineWave length Y",
            "double",
            100.,
            0.,
            1000.
        )

        self.sinewave_offset_y_att = self.addAnimParam(
            "sinewave_offset_y",
            "SineWave Offset Y",
            "double",
            0.,
            -100.,
            100.,
        )

        self.sinewave_power_x_att = self.addAnimParam(
            "sinewave_power_x",
            "SineWave Power X",
            "double",
            0.,
            0.,
            255
        )

        self.sinewave_wavelength_x_att = self.addAnimParam(
            "sinewave_wavelength_x",
            "SineWave length X",
            "double",
            100.,
            0.,
            1000.
        )

        self.sinewave_offset_x_att = self.addAnimParam(
            "sinewave_offset_x",
            "SineWave Offset X",
            "double",
            0.,
            -100.,
            100.,
        )

        self.sinewave_dropoff_att = self.addAnimParam(
            "sinewave_dropoff",
            "SineWave DropOff",
            "double",
            30,
            0.,
            100.,
        )

    def _getRotationsAtEachPoint(self, bfrs):
        # type: (List[Text]) -> List[Tuple[float, float, float]]
        # pylint: disable=too-many-locals

        rotations = []
        norm = self.guide.blades["blade"].y
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

    def withCurvePos(self, curveFn, it, offset=0.):
        curveLen = curveFn.length()

        for i, element in enumerate(it):
            param = curveFn.findParamFromLength((curveLen / (len(it) - 1)) * (i + offset))
            point = curveFn.getPointAtParam(param, om.MSpace.kObject)
            pos = point[0], point[1], point[2]
            yield pos, element

    def alignControllers(self, bfrs, cvs, oTans, iTans, curveFn):
        curveLen = curveFn.length()

        # Set the positions
        for pos, cv in self.withCurvePos(curveFn, bfrs):
            cmds.xform(cv, ws=True, a=True, t=pos)

        for i, cv in enumerate(cvs):
            cmds.setAttr("{0}.Pin".format(cv), 1)

            if i == (len(cvs) - 1):
                roll = cv.replace("_ik", "_rot")
                npo = re.sub(r"_ik(\d+)_ctl", r"_twistPart_\1_npo", cv)
                cmds.setAttr("{0}.UseTwist".format(roll), 1)
                cmds.setAttr("{0}.sz".format(npo), -1)

        for pos, cv in self.withCurvePos(curveFn, oTans, 0.4):
            cmds.xform(cv, ws=True, a=True, t=pos)
            cmds.setAttr("{0}.Auto".format(cv), 0)

        for pos, cv in self.withCurvePos(curveFn, iTans, 0.6):
            cmds.xform(cv, ws=True, a=True, t=pos)
            cmds.setAttr("{0}.Auto".format(cv), 0)

        # Get the rotations at each CV point
        rotations = self._getRotationsAtEachPoint(bfrs)

        for i, ctrl in enumerate(bfrs):
            rot = rotations[i]
            cmds.setAttr("{0}.rotate".format(ctrl), *rot)

        # Un-pin everything but the first, so back to length preservation
        for cv in cvs[1:]:
            cmds.setAttr("{0}.Pin".format(cv), 0)

        # Re-set the tangent worldspace positions now that things have changed
        for pos, cv in self.withCurvePos(curveFn, oTans, 0.4):
            cmds.setAttr("{0}.tx".format(cv), curveLen / self.ikNb * 0.7)
            cmds.setAttr("{0}.ty".format(cv), 0.0)
            cmds.setAttr("{0}.tz".format(cv), 0.0)
            cmds.setAttr("{0}.Auto".format(cv), 0)

        for pos, cv in self.withCurvePos(curveFn, iTans, 0.6):
            cmds.setAttr("{0}.tx".format(cv), curveLen / self.ikNb * -0.7)
            cmds.setAttr("{0}.ty".format(cv), 0.0)
            cmds.setAttr("{0}.tz".format(cv), 0.0)
            cmds.setAttr("{0}.Auto".format(cv), 0)

    def alignDeformers(self, ikNb, joints, positions, riderCnst, curveFn):
        # align deformer joints

        curveLen = curveFn.length()
        max_param = (ikNb - 1) * 3.0 * 2.
        maximum_iteration = 1000
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

    def convertToTwistSpline(self, positions, crv, ikNb, isClosed=False):

        crvShape = crv.getShape()
        curveFn = getAsMFnNode(crvShape.name(), om.MFnNurbsCurve)

        # Get the curve data
        knots = curveFn.knots()
        params = list(knots)[1::3]
        numCVs = len(params)
        numJoints = numCVs + 2  # head and tail

        # Build the spline
        pfx = self.getName("twistSpline")
        tempRet = tsBuilder.makeTwistSpline(pfx, ikNb, numJoints=numJoints, maxParam=None, spread=1.0, closed=isClosed)
        cvs, bfrs, oTans, iTans, jPars, joints, group, spline, master, riderCnst = tempRet

        self.alignControllers(bfrs, cvs, oTans, iTans, curveFn)
        self.alignDeformers(ikNb, joints, positions, riderCnst, curveFn)

        # grouping
        self.root.addChild(group)
        self.root.addChild(spline)
        self.root.addChild(pm.PyNode(bfrs[0]).getParent())
        self.root.addChild(master)
        offset = cmds.xform(master, q=True, os=True, t=True)
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
        # self.root.addChild(riderCnst)

        for bfr in bfrs:
            cur = cmds.getAttr("{0}.t".format(bfr))[0]
            cmds.setAttr("{0}.tx".format(bfr), cur[0] + offset[0])
            cmds.setAttr("{0}.ty".format(bfr), cur[1] + offset[1])
            cmds.setAttr("{0}.tz".format(bfr), cur[2] + offset[2])
            for att in [x+y for x in 'trs' for y in 'xyz']:
                cmds.setAttr("{0}.{1}".format(bfr, att), lock=True)

        for cv in cvs:
            ctl = pm.PyNode(cv)
            ymt_util.setKeyableAttributesDontLockVisibility(ctl, self.tr_params)
            ymt_util.addCtlMetadata(self, ctl)

        for x in oTans:
            ctl = pm.PyNode(x)
            ymt_util.setKeyableAttributesDontLockVisibility(ctl, ["tx", "ty", "tz"])
            ymt_util.addCtlMetadata(self, ctl)

        for x in iTans:
            ctl = pm.PyNode(x)
            ymt_util.setKeyableAttributesDontLockVisibility(ctl, ["tx", "ty", "tz"])
            ymt_util.addCtlMetadata(self, ctl)

        return cvs, oTans, iTans, joints, master, pm.PyNode(spline)

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """

        pm.parentConstraint(self.ik_ctl[0], self.aim_npo, mo=True, skipRotate=("x", "y", "z"))
        pm.parentConstraint(self.bts_joints[0], self.fk_npo[0], maintainOffset=True, skipRotate=("x", "y", "z"))
        self.addOperatorsNotGlobalMaster()

        # TODO: Add option for length controller to be added or not
        self.addOperatorLengthExpression()

        # TODO: optional for sine curve deformer
        self.addOperatorSineCurveExprespy()

    def addOperatorsNotGlobalMaster(self):
        # Curves -------------------------------------------

        # ensure plugin loaded
        if 0 == cmds.pluginInfo("rotationDriver", query=True, loaded=True):
            cmds.loadPlugin("rotationDriver")

        self.decomp_tip_ik_rot = pm.createNode("decomposeRotate")
        # self.ik_decompose_rot.append(self.decomp_tip_ik_rot)
        pm.setAttr(self.decomp_tip_ik_rot.attr("axisOrientX"), 90.0)
        pm.setAttr(self.decomp_tip_ik_rot.attr("axisOrientZ"), 90.0)
        pm.connectAttr(self.ik_ctl[-1].rotate, self.decomp_tip_ik_rot.attr("rotate"))

        # Division -----------------------------------------
        rootWorld_node = node.createDecomposeMatrixNode(self.root.attr("worldMatrix"))
        for i in range(len(self.guide.apos)):
            self.addFkOperator(i, rootWorld_node)

    def addFkOperator(self, i, rootWorld_node):

        fk_local_npo_xfoms = []
        if i not in [len(self.guide.apos), 0]:
            xform = getTransform(self.fk_local_npo[i])
            fk_local_npo_xfoms.append(xform)

        # break FK hierarchical orient
        if i not in [len(self.guide.apos), 0]:
            s = self.fk_ctl[i - 1]
            s2 = self.fk_npo[i]
            d = self.fk_local_npo[i]

            dm_node = node.createDecomposeMatrixNode(s.attr("inverseMatrix"))
            comp_node = pm.PyNode(cmds.createNode("composeMatrix"))
            pm.connectAttr(dm_node + ".outputScale", comp_node.attr("inputScale"))
            pm.connectAttr(dm_node + ".outputShear", comp_node.attr("inputShear"))
            mulmat_node = applyop.gear_mulmatrix_op(comp_node.attr("outputMatrix"), s.attr("matrix"))

            mulmat_node = applyop.gear_mulmatrix_op(s2.attr("matrix"), mulmat_node.attr("output"))
            mulmat_node2 = applyop.gear_mulmatrix_op(mulmat_node.attr("output"), s2.attr("inverseMatrix"))

            dm_node = node.createDecomposeMatrixNode(mulmat_node2 + ".output")
            pm.connectAttr(dm_node + ".outputTranslate", d.attr("t"))

            check_list = (pm.Attribute, unicode, str)  # noqa
            cond = pm.createNode("condition")
            pm.setAttr(cond + ".operation", 4)  # greater
            attribute.connectSet(self.fk_collapsed_att, cond + ".secondTerm", check_list)
            attribute.connectSet(dm_node + ".outputRotate", cond + ".colorIfTrue", check_list)
            pm.setAttr(cond + ".colorIfFalseR", 0.)
            pm.setAttr(cond + ".colorIfFalseG", 0.)
            pm.setAttr(cond + ".colorIfFalseB", 0.)
            pm.connectAttr(cond + ".outColor", d.attr("r"))

        # References
        tmp_div_npo_transform = getTransform(self.div_cns_npo[i])  # to fix mismatch before/after later
        cns = pm.parentConstraint(self.bts_joints[i], self.div_cns[i], maintainOffset=True)
        self.div_cns[i].attr("r") >> self.fk_npo[i].attr("r")
        self.div_cns[i].attr("t") >> self.fk_npo[i].attr("t")

    def addOperatorLengthExpression(self):
        rewrite_map = [
            ["scale_ctl", self.length_ctl],
            ["fk0_npo", self.fk_npo[0]],
            ["scale_cns", self.scale_npo],
            ["scale_master", self.master_ctl],
            ["number_of_points", self.divisions],
            ["curve_length", self.length]
        ]
        additional_code = ""
        self.length_ctl.setTranslation(datatypes.Vector(0.0, self.length, 0), space="preTransform")
        self.exprespy = create_exprespy_node(self.length_control_expression_archtype, self.getName("exprespy"), rewrite_map, additional_code)

    def length_control_expression_archtype(curve_length, scale_ctl, fk0_npo, scale_master, scale_cns):
        from maya.api.OpenMaya import MVector
        def sigmoid(x, mi, mx):
            return mi + (mx-mi)*(lambda t: (1+((200. / curve_length)*100.)**(-t+0.5))**(-1) )( (x-mi)/(mx-mi))

        tz = scale_ctl.translateY
        if curve_length < tz:
            # s = sigmoid(tz * (200. / curve_length), 0.0001, 100.0) * 0.01
            s = tz / curve_length
            vis = True
            fk0_npo.scale = MVector(1., 1., 1.)
            scale_master.Stretch = s

        elif 0.0 < tz:
            s = tz / curve_length
            vis = True
            fk0_npo.scale = MVector(1., 1., 1.)
            scale_master.Stretch = s

        else:
            s = 0.001
            vis = False
            fk0_npo.scale = MVector(s, s, s)
        scale_cns.scale = MVector(s, s, s)
        fk0_npo.visibility = vis

    def addOperatorSineCurveExprespy(self):
        rewrite_map = [
            ["__scale_ctl", self.length_ctl],
            ["__curve_length", self.length],
            ["__wave_offset_att", self.sinewave_offset_y_att],
            ["__wave_power_att", self.sinewave_power_y_att],
            ["__wave_length_att", self.sinewave_wavelength_y_att],
            ["__mst_crv", "{}.outputSpline".format(self.mst_crv.getShape().name())],
            ["__divisions", self.divisions],
            ["__negate", self.negate],
            ["__dropoff", self.sinewave_dropoff_att],
        ]
        additional_code = ""
        for i, loc in enumerate(self.fk_local_in2):
            rate = (i + 0.000000001) / self.divisions
            additional_code += "\n{}.translateZ = get_sin_at_pos({}, s)".format(loc, rate)

            if i < self.divisions:
                additional_code += "\n{}.rotateX = get_tan_at_pos({}, s)".format(loc, rate)
        self.exprespy2 = create_exprespy_node(self.sinewave_expression_archtype, self.getName("exprespy"), rewrite_map, additional_code)
        # cmds.setAttr("{}.IN[4]".format(self.exprespy2), "{}.worldSpace".format(self.mst_crv.name()))

        rewrite_map = [
            ["__scale_ctl", self.length_ctl],
            ["__curve_length", self.length],
            ["__wave_offset_att", self.sinewave_offset_x_att],
            ["__wave_power_att", self.sinewave_power_x_att],
            ["__wave_length_att", self.sinewave_wavelength_x_att],
            ["__mst_crv", "{}.outputSpline".format(self.mst_crv.getShape().name())],
            ["__divisions", self.divisions],
            ["__negate", self.negate],
            ["__dropoff", self.sinewave_dropoff_att],
        ]
        additional_code = ""
        for i, loc in enumerate(self.fk_local_in2):
            rate = (i + 0.000000001) / self.divisions
            additional_code += "\n{}.translateX = get_sin_at_pos({}, s)".format(loc, rate)
            if i < self.divisions:
                additional_code += "\n{}.rotateZ = -1. * get_tan_at_pos({}, s)".format(loc, rate)
        self.exprespy2 = create_exprespy_node(self.sinewave_expression_archtype,
                                              self.getName("exprespy"),
                                              rewrite_map,
                                              additional_code)
        # cmds.setAttr("{}.IN[4]".format(self.exprespy2), "{}.worldSpace".format(self.mst_crv.name()))

    def sinewave_expression_archtype(COUNT, __scale_ctl, __curve_length, __wave_offset_att, __wave_power_att, __wave_length_att, __mst_crv, __divisions, __negate, __dropoff):

        if not COUNT:
            import math

            def sigmoid(x, mx):
                # return mi + (mx-mi)*(lambda t: (1+(100.)**(-t+0.5))**(-1) )( (x-mi)/(mx-mi))
                x = (x * 10) / mx - 5.
                return 1 / (1 + math.exp(-x))

            def get_sin_at_pos(pos, s):

                x = math.sin(math.pi * (2. / (__wave_length_att / 100.0)) * ((__wave_offset_att / 100.0) * (__wave_length_att / 100.0) + pos * s)) * __curve_length * (__wave_power_att / 100.0) * 0.5
                return sigmoid(pos, __dropoff / 100.0) * x

            def get_tan_at_pos(pos, s):
                a = get_sin_at_pos(pos, s)
                b = get_sin_at_pos(pos + (1. / __divisions), s)
                if (b - a) < 0.:
                    if __negate:
                        return math.atan(abs(b - a) / (__curve_length * s / __divisions)) * 1
                    else:
                        return math.atan(abs(b - a) / (__curve_length * s / __divisions)) * -1
                else:
                    if __negate:
                        return math.atan(abs(b - a) / (__curve_length * s / __divisions)) * -1
                    else:
                        return math.atan(abs(b - a) / (__curve_length * s / __divisions))

        mst_crv = api.MFnNurbsCurve(__mst_crv)
        # s2 = mst_crv.length() / __curve_length
        s = __scale_ctl.ty / __curve_length
        # s = min(s, s2)

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
        # self.connectRef(self.settings["ik0refarray"], self.ik_npo[0])
        # self.connectRef(self.settings["ik1refarray"], self.ik_npo[-1])

    # =====================================================
    # CONNECTOR
    # =====================================================

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        if self.settings["isGlobalMaster"]:
            return

        self.relatives["root"] = self.fk_ctl[0]
        self.relatives["eff"] = self.fk_ctl[-1]
        self.controlRelatives["root"] = self.fk_ctl[0]
        self.jointRelatives["root"] = 0

        for i, ctl in enumerate(self.fk_ctl):

            self.relatives["%s_loc" % i] = ctl
            self.controlRelatives["%s_loc" % i] = ctl

            self.jointRelatives["%s_loc" % (i)] = (i + 1)
            self.aliasRelatives["%s_ctl" % (i)] = (i + 1)


def vecProjection(a, b):

    dot = a.dot(b)
    length = b.length()
    tmp = dot / (length * length)
    p = [tmp * b.x, tmp * b.y, tmp * b.z]

    return p


def create_exprespy_node(func, name, rewrite_map, additional_code=None):
    code = inspect.getsource(func)
    code = textwrap.dedent("".join(code.splitlines(True)[1:]))

    for src, dst in rewrite_map:
        code = re.sub(r"{}(\W)".format(src), "{}\\1".format(dst), code)

    if additional_code is not None:
        code += additional_code

    exp_node = cmds.createNode("exprespy", name=name)
    cmds.setAttr("{}.code".format(exp_node), code, type="string")
    exprespy.cmd.setCode(exp_node, code, raw=False)

    return exp_node


def get_nearest_axis_orient(a, b):
    # returns normalized axis of orientation of a to b
    ta = getTransform(a)
    tb = getTransform(b)
    tb - ta


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


if __name__ == "__main__":
    pass
