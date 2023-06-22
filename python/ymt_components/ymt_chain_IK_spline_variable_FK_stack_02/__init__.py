"""mGear shifter components"""
# pylint: disable=import-error
# pylint: disable=W0201
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

from mgear.core import transform, primitive, curve, applyop
from mgear.core import attribute, node, icon, fcurve, vector

from mgear.core.transform import getTransform
from mgear.core.transform import getTransformLookingAt
from mgear.core.transform import getChainTransform2
from mgear.core.transform import setMatrixPosition
from mgear.core.primitive import addTransform
import ymt_shifter_utility as ymt_util


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
        self.ik_global_in = []
        self.ik_local_in = []
        self.ik_global_out = []
        self.ik_global_ref = []
        self.ik_uv_param = []
        self.previusTag = self.parentCtlTag

        self.length_ctl = None
        self.div_cns = []
        self.div_cns_npo = []
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

        # IK controls ---------------------------------------------
        self.dummy_crv = curve.addCurve(
            self.root,
            self.getName("dummy_crv"),
            self.guide.apos,
            close=False,
            degree=min([len(self.guide.apos) - 1, 3])
        )

        for i in range(self.settings["ikNb"]):
            self.addObjectsChainIk(i, self.dummy_crv)

        # add npo
        t = getTransform(self.guide.root)
        self.aim_npo = addTransform(self.root, self.getName("aim_npo"), t)

        self.addLengthCtrl(self.dummy_crv)
        pm.delete(self.dummy_crv)

        # Curves -------------------------------------------
        self.mst_crv = curve.addCnsCurve(
            self.root,
            self.getName("mst_crv"),
            self.ik_ctl,
            3)
        self.slv_crv = curve.addCurve(
            self.root,
            self.getName("slv_crv"),
            [datatypes.Vector()] * 10,
            False,
            3)

        icon.connection_display_curve(self.getName("visualIKRef"), self.ik_ctl)
        if self.settings["isGlobalMaster"]:
            return

        else:
            self.addObjectsFkControl()

    def addObjectsFkControl(self):

        parentdiv = self.root
        parentctl = self.root

        parent_twistRef = addTransform(
            self.root,
            self.getName("reference"),
            getTransform(self.root))

        self.jointList = []
        self.preiviousCtlTag = self.parentCtlTag
        chain = getChainTransform2(self.guide.apos, self.normal, self.negate)
        # chain = getChainTransform2(self.guide.apos, self.normal, False)
        for i, t in enumerate(chain):
            parentdiv, parentctl = self._addObjectsFkControl(i, parentdiv, parentctl, t, parent_twistRef)

        # add visual reference
        icon.connection_display_curve(self.getName("visualFKRef"), self.fk_ctl)

    def addLengthCtrl(self, crv):
        t = getTransform(self.guide.root)
        global_t = self._getTransformWithRollByBlade(t)
        cvs = crv.length()
        tm = datatypes.TransformationMatrix(t)
        tm.addTranslation([cvs * -0.4, cvs * 0.2, 0.], om.MSpace.kObject)

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
            ro=datatypes.Vector([-math.pi / 2., 0., 0.])
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
        ymt_util.setKeyableAttributesDontLockVisibility(self.length_ctl, ["ty"])

    def addObjectsChainIk(self, i, crv):

        cvs = crv.length()
        if i == 0:
            u = 0.
        else:
            u = crv.findParamFromLength(cvs / (self.settings["ikNb"] - 1) * i)

        self.ik_uv_param.append(1. / (self.settings["ikNb"] - 1) * i)
        space = om.MSpace.kWorld
        pos = crv.getPointAtParam(u, space)

        if i in [0, (self.settings["ikNb"] - 1)]:
            t = getTransform(self.guide.root)
            global_t = self._getTransformWithRollByBlade(t)

        else:
            u2 = crv.findParamFromLength(cvs / (self.settings["ikNb"] - 1) * i + 1)
            pos2 = crv.getPointAtParam(u2, space)
            t = getTransformLookingAt(pos, pos2, self.guide.blades["blade"].y, axis="yx", negate=self.negate)

            # FIXME:
            t = getTransform(self.guide.root)
            global_t = self._getTransformWithRollByBlade(t)

        global_t = setMatrixPosition(global_t, pos)
        local_t = global_t

        # global input
        ik_global_npo = addTransform(self.root, self.getName("ik%s_global_npo" % i), global_t)
        ik_global_in = addTransform(ik_global_npo, self.getName("ik%s_global_in" % i), global_t)
        self.ik_global_in.append(ik_global_in)

        # local input
        ik_local_npo = addTransform(ik_global_in, self.getName("ik%s_local_npo" % i), local_t)
        ik_local_in = addTransform(ik_local_npo, self.getName("ik%s_local_in" % i), local_t)
        self.ik_local_in.append(ik_local_in)

        ik_npo = addTransform(ik_local_in, self.getName("ik%s_npo" % i), local_t)
        self.ik_npo.append(ik_npo)

        # output
        ik_global_out_npo = addTransform(self.root, self.getName("ik%s_global_out_npo" % i), global_t)
        ik_global_out = addTransform(ik_global_out_npo, self.getName("ik%s_global_out" % i), global_t)
        self.ik_global_out.append(ik_global_out)

        # if i == 0 or i == (len(self.guide.apos) - 1):
        if i == 0:
            ctl_form = "compas"
            col = self.color_ik
            size = self.size
            w = size
            h = size
            d = size
        elif i == (self.settings["ikNb"] - 1):
            ctl_form = "cubewithpeak"
            col = self.color_ik
            size = self.size
            w = size
            h = size
            d = size
        else:
            ctl_form = "compas"  # TODO: set more better
            col = self.color_ik
            size = self.size * .85
            w = size
            h = size
            d = size

        ik_ctl = self.addCtl(
            ik_npo,
            "ik%s_ctl" % i,
            local_t,
            col,
            ctl_form,
            w=w,
            h=h,
            d=d,
            # ro=datatypes.Vector([0, math.pi * self.negate, 0]),
            tp=self.previusTag,
            mirrorConf=self.mirror_conf)

        ymt_util.setKeyableAttributesDontLockVisibility(ik_ctl, self.tr_params)
        self.ik_ctl.append(ik_ctl)

        # ik global ref
        ik_global_ref = primitive.addTransform(
            ik_ctl,
            self.getName("ik%s_global_ref" % i),
            global_t)
        self.ik_global_ref.append(ik_global_ref)
        ymt_util.setKeyableAttributesDontLockVisibility(ik_global_ref, [])

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

    def _addObjectsFkControl(self, i, parentdiv, parentctl, t, parent_twistRef):
        # References
        tm = datatypes.TransformationMatrix(t)
        tm.addRotation([0., 0., math.pi / -2.], 'XYZ', om.MSpace.kObject)  # TODO: align with convention
        tm.addRotation([0., math.pi / -2., 0], 'XYZ', om.MSpace.kObject)
        global_t  = datatypes.Matrix(tm)

        # global input
        div_cns = addTransform(parentdiv, self.getName("%s_cns" % i))
        div_cns_npo = addTransform(div_cns, self.getName("%s_cns_npo" % i))
        pm.setAttr(div_cns + ".inheritsTransform", False)
        div_cns.setMatrix(global_t, worldSpace=True)
        self.div_cns.append(div_cns)
        self.div_cns_npo.append(div_cns_npo)
        parentdiv = div_cns

        # t = getTransform(parentctl)
        if i == 0:
            p = parentctl
        else:
            # p = self.scl_transforms[i - 1]
            p = self.fk_local_in[i - 1]
        fk_npo = addTransform(p, self.getName("fk%s_npo" % (i)), global_t)

        # local input
        fk_local_npo = addTransform(fk_npo, self.getName("fk%s_local_npo" % i), global_t)
        fk_local_in = addTransform(fk_local_npo, self.getName("fk%s_local_in" % i), global_t)
        fk_local_in2 = addTransform(fk_local_in, self.getName("fk%s_local_in2" % i), global_t)
        self.fk_local_in.append(fk_local_in)
        self.fk_local_in2.append(fk_local_in2)

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
            global_t,
            self.color_fk,
            "cube",
            w=h * .66,
            h=h,
            d=h * 0.3,
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
        t = transform.getTransformLookingAt(
            self.guide.apos[0],
            self.guide.apos[-1],
            self.guide.blades["blade"].z * -1,
            "yx",
            self.negate)

        twister = addTransform(
            parent_twistRef, self.getName("%s_rot_ref" % i), t)

        ref_twist = addTransform(
            parent_twistRef, self.getName("%s_pos_ref" % i), t)

        ref_twist.setTranslation(
            datatypes.Vector(1.0, 0, 0), space="preTransform")

        self.twister.append(twister)
        self.ref_twist.append(ref_twist)

        for x in self.fk_ctl[:-1]:
            attribute.setInvertMirror(x, ["tx", "rz", "ry"])

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

        if not self.settings["isGlobalMaster"]:
            # Anim -------------------------------------------
            self.volume_att = self.addAnimParam(
                "volume", "Volume", "double", 1, 0, 1)

            self.maxstretch_att = self.addAnimParam(
                "maxstretch",
                "Max Stretch",
                "double",
                self.settings["maxstretch"],
                0.1,
                1000.)

            self.maxsquash_att = self.addAnimParam(
                "maxsquash",
                "Max Squash",
                "double",
                self.settings["maxsquash"],
                0.,
                1.)

            self.softness_att = self.addAnimParam(
                "softness",
                "Softness",
                "double",
                self.settings["softness"],
                0,
                1)

        self.lock_ori0_att = self.addAnimParam(
            "lock_ori0",
            "Lock Ori 0",
            "double",
            # self.settings["lock_ori"],
            0.0,
            0,
            1
        )

        self.lock_ori1_att = self.addAnimParam(
            "lock_ori1",
            "Lock Ori 1",
            "double",
            # self.settings["lock_ori"],
            1.,
            0,
            1
        )

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
            2.5
        )

        self.sinewave_wavelength_y_att = self.addAnimParam(
            "sinewave_wavelength_",
            "SineWave length Y",
            "double",
            2.,
            0.,
            10.
        )

        self.sinewave_offset_y_att = self.addAnimParam(
            "sinewave_offset_y",
            "SineWave Offset Y",
            "double",
            0.,
            -1.,
            1.,
        )

        self.sinewave_power_x_att = self.addAnimParam(
            "sinewave_power_x",
            "SineWave Power X",
            "double",
            0.,
            0.,
            2.5
        )

        self.sinewave_wavelength_x_att = self.addAnimParam(
            "sinewave_wavelength_x",
            "SineWave length X",
            "double",
            2.,
            0.,
            10.
        )

        self.sinewave_offset_x_att = self.addAnimParam(
            "sinewave_offset_x",
            "SineWave Offset X",
            "double",
            0.,
            -1.,
            1.,
        )

        # Setup ------------------------------------------
        # Eval Fcurve
        ikname = "{}_ik_profile".format(self.guide.root.split("|")[-1])
        self.ik_value = fcurve.getFCurveValues(ikname, self.settings["ikNb"])
        self.ik_att = [self.addAnimParam("gravity_rate_ik%s" % i,
                                         "Planetary Ik ratio %s" % i,
                                         "double",
                                         self.ik_value[i],
                                         0,
                                         1)
                       for i in range(1, self.settings["ikNb"] - 1)]

        stname = "{}_st_profile".format(self.guide.root.split("|")[-1])
        sqname = "{}_sq_profile".format(self.guide.root.split("|")[-1])
        self.st_value = fcurve.getFCurveValues(stname, self.divisions)
        self.sq_value = fcurve.getFCurveValues(sqname, self.divisions)

        self.st_att = [self.addSetupParam("stretch_%s" % i,
                                          "Stretch %s" % i,
                                          "double",
                                          self.st_value[i],
                                          -1,
                                          0)
                       for i in range(self.divisions)]

        self.sq_att = [self.addSetupParam("squash_%s" % i,
                                          "Squash %s" % i,
                                          "double",
                                          self.sq_value[i],
                                          0,
                                          1)
                       for i in range(self.divisions)]

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        for e, _ in enumerate(self.ik_ctl):

            out_glob = self.ik_global_out[e]
            out_ref = self.ik_global_ref[e]

            applyop.gear_mulmatrix_op(
                out_ref.attr("worldMatrix"),
                out_glob.attr("parentInverseMatrix[0]"),
                out_glob)

        if self.settings["isGlobalMaster"]:
            pass
        else:
            self.addOperatorsNotGlobalMaster()

        pm.parentConstraint(self.ik_ctl[0], self.aim_npo, mo=True, skipRotate=("x", "y", "z"))
        aim = pm.aimConstraint(self.ik_ctl[-1], self.aim_npo, mo=True, worldUpType="objectrotation", worldUpObject=self.ik_ctl[0], worldUpVector=(-1.0, 0., 0.))
        # pm.setAttr(aim + ".upVectorX", 0)
        # pm.setAttr(aim + ".upVectorY", 1)
        # pm.setAttr(aim + ".upVectorZ", 0)

        # TODO: optional for sine curve deformer
        self.addOperatorSineCurveGenerator()

        # TODO: Add option for length controller to be added or not
        self.addOperatorLengthExpression()

    def addOperatorsNotGlobalMaster(self):
        # Curves -------------------------------------------
        op = applyop.gear_curveslide2_op(self.slv_crv, self.mst_crv, 0, 1.5, .5, .5)
        op.rename(self.getName("slideCurveOp"))

        # pm.connectAttr(self.position_att, op + ".position")
        pm.connectAttr(self.maxstretch_att, op + ".maxstretch")
        pm.connectAttr(self.maxsquash_att, op + ".maxsquash")
        pm.connectAttr(self.softness_att, op + ".softness")
        self.slv_crv_op = op

        # Volume driver ------------------------------------
        crv_node = node.createCurveInfoNode(self.slv_crv)

        if not self.settings["isPlanetaryIkBindToGlobal"]:
            self.addOperatorsIkTwist()

        # Division -----------------------------------------
        rootWorld_node = node.createDecomposeMatrixNode(self.root.attr("worldMatrix"))
        for i in range(len(self.guide.apos)):
            self.addFkOperator(i, rootWorld_node, crv_node)

        # CONNECT STACK
        # master components
        mstr_global = self.settings["masterChainGlobal"]
        mstr_local = self.settings["masterChainLocal"]

        if mstr_global:
            mstr_global = self.rig.components[mstr_global]
        if mstr_local:
            mstr_local = self.rig.components[mstr_local]

        # connect  global IK
        if mstr_global:
            for e, _ in enumerate(self.ik_ctl):
                # connect in global
                self.connect_master(mstr_global.ik_global_out,
                                    self.ik_global_in,
                                    e,
                                    self.settings["cnxOffset"])

        # connect in local
        if mstr_local:
            for e, _ in enumerate(self.ik_ctl):
                self.connect_master(mstr_local.ik_ctl,
                                    self.ik_local_in,
                                    e,
                                    self.settings["cnxOffset"])

            for e, _ in enumerate(self.fk_ctl):
                self.connect_master(mstr_local.fk_ctl,
                                    self.fk_local_in,
                                    e,
                                    self.settings["cnxOffset"])

    def addOperatorsIkTwist(self):

        for i in range(1, self.settings["ikNb"] - 1):

            '''
            intMatrix = applyop.gear_intmatrix_op(
                self.ik_ctl[0] + ".matrix",
                self.ik_ctl[-1] + ".matrix",
                self.ik_att[i])
            # self.ik_uv_param[i])
            dm_node = node.createDecomposeMatrixNode(intMatrix + ".output")
            pm.connectAttr(dm_node + ".outputRotate", self.ik_npo[i].attr("rotate"))
            pm.connectAttr(dm_node + ".outputTranslate", self.ik_npo[i].attr("translate"))
            '''

            # TODO: connect attribute on weight
            s = [self.ik_ctl[0], self.ik_ctl[-1]]
            d = self.ik_npo[i]
            c = pm.parentConstraint(s, d, mo=True)

            for _i, _s in enumerate(s):
                pm.disconnectAttr("{}.{}W{}".format(c, _s, _i), "{}.target[{}].targetWeight".format(c, _i))

            inv = pm.createNode("floatMath")
            pm.setAttr(inv + ".floatA", 1.0)
            pm.setAttr(inv + ".operation", 1)
            pm.connectAttr(self.ik_att[i - 1], inv + ".floatB")
            pm.connectAttr(inv + ".outFloat", c + ".target[0].targetWeight")
            pm.connectAttr(self.ik_att[i - 1], c + ".target[1].targetWeight")

    def addFkOperator(self, i, rootWorld_node, crv_node):

        fk_local_npo_xfoms = []
        if i not in [len(self.guide.apos), 0]:
            xform = getTransform(self.fk_local_npo[i])
            fk_local_npo_xfoms.append(xform)

        # break FK hierarchical orient
        if i not in [len(self.guide.apos), 0]:
            s = self.fk_ctl[i - 1]
            s2 = self.fk_npo[i]
            d = self.fk_local_npo[i]

            mulmat_node = applyop.gear_mulmatrix_op(s2.attr("matrix"), s.attr("matrix"))
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
        if i == 0:  # we add extra 10% to the first position
            u = (1.0 / (len(self.guide.apos) - 1.0)) / 10000
        else:
            u = getCurveUAtPoint(self.slv_crv, self.guide.apos[i])

        tmp_div_npo_transform = getTransform(self.div_cns_npo[i])  # to fix mismatch before/after later
        cns = applyop.pathCns(self.div_cns[i], self.slv_crv, False, u, True)
        cns.setAttr("frontAxis", 1)  # front axis is 'Y'
        cns.setAttr("upAxis", 0)  # front axis is 'X'

        # Roll
        # choose ik_ctls
        for _i, uv in enumerate(self.ik_uv_param):
            if u < uv:

                ik_a = self.ik_ctl[_i - 1]
                ik_b = self.ik_ctl[_i]

                ratio = u / uv

                break

        else:
            ik_a = self.ik_ctl[-2]
            ik_b = self.ik_ctl[-1]
            ratio = 1.

        intMatrix = applyop.gear_intmatrix_op(
            ik_a + ".worldMatrix",
            ik_b + ".worldMatrix",
            ratio)

        dm_node = node.createDecomposeMatrixNode(intMatrix + ".output")
        pm.connectAttr(dm_node + ".outputRotate", self.twister[i].attr("rotate"))
        pm.parentConstraint(self.twister[i], self.ref_twist[i], maintainOffset=True)

        pm.connectAttr(self.ref_twist[i] + ".translate", cns + ".worldUpVector")
        self.div_cns_npo[i].setMatrix(tmp_div_npo_transform, worldSpace=True)

        # compensate scale reference
        div_node = node.createDivNode(
            [1, 1, 1],
            [rootWorld_node + ".outputScaleX",
             rootWorld_node + ".outputScaleY",
             rootWorld_node + ".outputScaleZ"])

        # Squash n Stretch
        op = applyop.gear_squashstretch2_op(self.scl_transforms[i],
                                            self.root,
                                            pm.arclen(self.slv_crv),
                                            "y",
                                            div_node + ".output")

        pm.connectAttr(self.volume_att, op + ".blend")
        pm.connectAttr(crv_node + ".arcLength", op + ".driver")
        # pm.connectAttr(self.st_att[i], op + ".stretch")
        # pm.connectAttr(self.sq_att[i], op + ".squash")

        # Controlers
        tmp_local_npo_transform = getTransform(self.fk_local_npo[i])  # to fix mismatch before/after later
        if i == 0:
            mulmat_node = applyop.gear_mulmatrix_op(
                self.div_cns_npo[i].attr("worldMatrix"),
                self.root.attr("worldInverseMatrix"))

            dm_node = node.createDecomposeMatrixNode(mulmat_node + ".output")
            pm.connectAttr(dm_node + ".outputTranslate", self.fk_npo[i].attr("t"))

        else:
            mulmat_node = applyop.gear_mulmatrix_op(
                self.div_cns_npo[i].attr("worldMatrix"),
                self.div_cns_npo[i - 1].attr("worldInverseMatrix"))

            dm_node = node.createDecomposeMatrixNode(mulmat_node + ".output")
            mul_node = node.createMulNode(div_node + ".output", dm_node + ".outputTranslate")
            pm.connectAttr(mul_node + ".output", self.fk_npo[i].attr("t"))

        pm.connectAttr(dm_node + ".outputRotate", self.fk_npo[i].attr("r"))
        self.addOperatorsOrientationLock(i, cns)
        self.fk_local_npo[i].setMatrix(tmp_local_npo_transform, worldSpace=True)

        # References
        if i < (len(self.fk_ctl) - 1):
            aim = pm.aimConstraint(self.div_cns_npo[i + 1], self.div_cns_npo[i], maintainOffset=False)
            pm.setAttr(aim + ".aimVectorX", 0)
            if self.negate:
                pm.setAttr(aim + ".aimVectorY", -1)
            else:
                pm.setAttr(aim + ".aimVectorY", 1)
            pm.setAttr(aim + ".aimVectorZ", 0)
            pm.setAttr(aim + ".upVectorX", 0)
            pm.setAttr(aim + ".upVectorY", 1)
            pm.setAttr(aim + ".upVectorZ", 0)
            # applyop.aimCns(self.div_cns_npo[i], self.div_cns[i - 1], axis="yx", maintainOffset=True)

    def addOperatorsOrientationLock(self, i, cns):
        # Orientation Lock
        if i == 0:
            dm_node = node.createDecomposeMatrixNode(
                self.ik_ctl[0] + ".worldMatrix")

            blend_node = node.createBlendNode(
                [dm_node + ".outputRotate%s" % s for s in "XYZ"],
                [cns + ".rotate%s" % s for s in "XYZ"],
                self.lock_ori0_att)
            # 0)

            self.div_cns[i].attr("rotate").disconnect()
            pm.connectAttr(blend_node + ".output", self.div_cns[i] + ".rotate")

        elif i == len(self.fk_ctl) - 1:
            dm_node = node.createDecomposeMatrixNode(
                self.ik_ctl[-1] + ".worldMatrix")

            blend_node = node.createBlendNode(
                [dm_node + ".outputRotate%s" % s for s in "XYZ"],
                [cns + ".rotate%s" % s for s in "XYZ"],
                self.lock_ori1_att)
            # 1)

            self.div_cns[i].attr("rotate").disconnect()
            pm.connectAttr(blend_node + ".output", self.div_cns[i] + ".rotate")

    def addOperatorLengthExpression(self):
        rewrite_map = [
            ["sine_npo", self.getName("sine_npo")],
            ["scale_ctl", self.length_ctl],
            ["fk0_npo", self.fk_npo[0]],
            ["curve_op", self.slv_crv_op],
            ["scale_cns", self.scale_npo],
            ["curve_length", self.slv_crv.length()]
        ]
        self.length_ctl.setTranslation(datatypes.Vector(0.0, self.slv_crv.length(), 0), space="preTransform")
        self.exprespy = create_exprespy_node(self.length_control_expression_archtype, self.getName("exprespy"), rewrite_map)

    def length_control_expression_archtype(curve_length, scale_ctl, fk0_npo, curve_op, scale_cns, sine_npo):
        from maya.api.OpenMaya import MVector
        def sigmoid(x, mi, mx):
            return mi + (mx-mi)*(lambda t: (1+((200. / curve_length)*100.)**(-t+0.5))**(-1) )( (x-mi)/(mx-mi))

        tz = scale_ctl.translateY
        if 0.0 < tz:
            s = sigmoid(tz * (200. / curve_length), 0.0001, 100.0) * 0.01
            vis = True
            fk0_npo.scale = MVector(1., 1., 1.)
            curve_op.slave_length = curve_length * s
        else:
            s = 0.001
            vis = False
            fk0_npo.scale = MVector(s, s, s)
        scale_cns.scale = MVector(s, s, s)
        fk0_npo.visibility = vis

        length_ratio = tz / curve_length
        if 1.0 < length_ratio:
            sine_npo.scale = MVector(length_ratio, length_ratio, length_ratio)
        else:
            sine_npo.scale = MVector(1., 1., 1.)

    def addOperatorSineCurveGenerator(self):

        # add npo
        t = getTransform(self.guide.root)
        cvs = self.slv_crv.length()
        tm = datatypes.TransformationMatrix(t)
        tm.addTranslation([0., cvs * 0.1, 0.], om.MSpace.kObject)

        local_t = datatypes.Matrix(tm)
        self.sine_npo = addTransform(self.aim_npo, self.getName("sine_npo"), t)

        # add deformer
        self.sine_deformer_y, self.sine_handle_y = pm.nonLinear(self.slv_crv, type='sine')
        self.sine_deformer_x, self.sine_handle_x = pm.nonLinear(self.slv_crv, type='sine')
        rot = self.sine_npo.getRotation(space="world")
        self.sine_handle_y.setRotation(rot, worldSpace=True)
        self.sine_handle_x.setRotation(rot, worldSpace=True)

        cmds.setAttr("{}.dropoff".format(self.sine_deformer_y), 1.)
        pm.rename(self.sine_deformer_y, self.getName("sine_deformer_y"))
        pm.rename(self.sine_handle_y, self.getName("sine_handle_y"))
        pm.parent(self.sine_handle_y, self.sine_npo)

        cmds.setAttr("{}.dropoff".format(self.sine_deformer_x), 1.)
        pm.rename(self.sine_deformer_x, self.getName("sine_deformer_x"))
        pm.rename(self.sine_handle_x, self.getName("sine_handle_x"))
        pm.parent(self.sine_handle_x, self.sine_npo)
        pm.parentConstraint(self.ik_ctl[0], self.sine_npo, mo=True, skipRotate=("x", "y", "z"))

        self.sine_handle_y.setRotatePivot(self.sine_handle_y.getTranslation(om.MSpace.kObject) * -1., space=om.MSpace.kObject, balance=False)
        self.sine_handle_y.setScalePivot(pm.datatypes.Vector(0., -1., 0.), space=om.MSpace.kWorld, balance=True)
        self.sine_handle_x.setRotatePivot(self.sine_handle_x.getTranslation(om.MSpace.kObject) * -1., space=om.MSpace.kObject, balance=False)
        self.sine_handle_x.setScalePivot(pm.datatypes.Vector(0., -1., 0.), space=om.MSpace.kWorld, balance=True)

        pm.connectAttr(self.sinewave_power_y_att, self.sine_deformer_y + ".amplitude")
        pm.connectAttr(self.sinewave_wavelength_y_att, self.sine_deformer_y + ".wavelength")

        pm.connectAttr(self.sinewave_power_x_att, self.sine_deformer_x + ".amplitude")
        pm.connectAttr(self.sinewave_wavelength_x_att, self.sine_deformer_x + ".wavelength")
        t = getTransform(self.sine_handle_x)

        rot_offset = om.MEulerRotation(0., math.radians(90.), 0., 0).asQuaternion()
        # self.sine_handle_x.rotateBy(rot_offset, space="object")
        cmds.setAttr("{}.ry".format(self.sine_handle_x), 90.0)

        # ensure plugin loaded
        if 0 == cmds.pluginInfo("maya-math-nodes", query=True, loaded=True):
            cmds.loadPlugin("maya-math-nodes")
        mult = pm.createNode("math_Multiply")
        pm.connectAttr(self.sinewave_offset_y_att, "{}.input1".format(mult))
        pm.connectAttr(self.sinewave_wavelength_y_att, "{}.input2".format(mult))
        pm.connectAttr("{}.output".format(mult), self.sine_deformer_y + ".offset")

        mult = pm.createNode("math_Multiply")
        pm.connectAttr(self.sinewave_offset_x_att, "{}.input1".format(mult))
        pm.connectAttr(self.sinewave_wavelength_x_att, "{}.input2".format(mult))
        pm.connectAttr("{}.output".format(mult), self.sine_deformer_x + ".offset")

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
        self.connectRef(self.settings["ik0refarray"], self.ik_npo[0])
        self.connectRef(self.settings["ik1refarray"], self.ik_npo[-1])

        if self.settings["isPlanetaryIkBindToGlobal"]:
            for i in range(2, self.settings["ikNb"] - 1):
                self.connectRef(self.settings["ik1refarray"], self.ik_npo[i])

        self.mst_crv.setAttr("visibility", False)
        self.slv_crv.setAttr("visibility", False)

    def connect_master(self, mstr_out, slave_in, idx, offset):
        """Connect master and slave chain

        Args:
            mstr_out (list): List of master outputs
            slave_in (list): List of slave inputs
            idx (int): Input index
            offset (int): Offset for the mastr ouput index
        """
        # we need to check if  master have enought sections
        # if  connection is out of index, will fallback to the latest
        # section in the master
        if (idx + offset) > len(mstr_out) - 1:
            mstr_e = len(mstr_out) - 1
        else:
            mstr_e = idx + offset
        m_out = mstr_out[mstr_e]
        s_in = slave_in[idx]
        for srt in ["scale", "rotate", "translate"]:
            pm.connectAttr(m_out.attr(srt), s_in.attr(srt))

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


def test():
    import pymel.core as pm
    import maya.cmds as cmds
    for x in [
            'spine_C0_fk0_local_npo',
            'spine_C0_fk1_local_npo',
            'spine_C0_fk2_local_npo',
            'spine_C0_fk3_local_npo'
    ]:
        n = pm.PyNode(x)
        xf = getTransform(n)[3]
        xf = map(lambda x: "{0:.2f}".format(x), xf)
        print(x, xf)
        print(x, map(lambda x: "{0:.2f}".format(x), n.getMatrix(worldSpace=False)[3]))
    cmds.refresh(suspend=True)
    cmds.refresh(suspend=False)


def cross(u, v):
    dim = len(u)
    s = []
    for i in range(dim):
        if i == 0:
            j, k = 1, 2
            s.append(u[j] * v[k] - u[k] * v[j])
        elif i == 1:
            j, k = 2, 0
            s.append(u[j] * v[k] - u[k] * v[j])
        else:
            j, k = 0, 1
            s.append(u[j] * v[k] - u[k] * v[j])

    return s


def getCurveUAtPoint(crv, position):
    point = om1.MPoint(position[0], position[1], position[2])

    dag = om1.MDagPath()
    obj = om1.MObject()
    oList = om1.MSelectionList()
    oList.add(crv.name())
    oList.getDagPath(0, dag, obj)

    curveFn = om1.MFnNurbsCurve(dag)
    length = curveFn.length()
    crv.findParamFromLength(length)

    paramUtill = om1.MScriptUtil()
    paramPtr = paramUtill.asDoublePtr()

    point = curveFn.closestPoint(point, paramPtr, 0.001, om1.MSpace.kObject)
    curveFn.getParamAtPoint(point, paramPtr, 0.001, om1.MSpace.kObject)

    param = paramUtill.getDouble(paramPtr)
    curveFn.getPointAtParam(param, point, om1.MSpace.kObject)
    length_at = curveFn.findLengthFromParam(param)

    return length_at / length


def vecProjection(a, b):

    dot = a.dot(b)
    length = b.length()
    tmp = dot / (length * length)
    p = [tmp * b.x, tmp * b.y, tmp * b.z]

    return p


def create_exprespy_node(func, name, rewrite_map):
    code = inspect.getsource(func)
    code = textwrap.dedent("".join(code.splitlines(True)[1:]))

    for src, dst in rewrite_map:
        code = re.sub(r"{}(\W)".format(src), "{}\\1".format(dst), code)

    exp_node = cmds.createNode("exprespy", name=name)
    cmds.setAttr("{}.code".format(exp_node), code, type="string")
    exprespy.cmd.setCode(exp_node, code, raw=False)

    return exp_node


if __name__ == "__main__":
    import maya.cmds as cmds
    import ymt_spine_ik_01 as m
    reload(m)
    try:
        cmds.delete("rig")

    except Exception:
        pass
    try:
        cmds.select("guide")

    except Exception:
        pass
    try:

        import mgear.shifter.guide_manager as gm
        gm.build_from_selection()

    except Exception:
        pass
