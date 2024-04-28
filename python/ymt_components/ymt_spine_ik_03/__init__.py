import math
import six

import maya.OpenMaya as om1
import maya.api.OpenMaya as om
import maya.cmds as cmds

import pymel.core as pm
from pymel.core import datatypes

from mgear.shifter import component

from mgear.core import transform, primitive, curve, applyop
from mgear.core import attribute, node, icon, fcurve, vector

from mgear.core.transform import getTransform
from mgear.core.transform import getTransformLookingAt
from mgear.core.transform import getChainTransform2
from mgear.core.transform import setMatrixPosition
# from mgear.core.transform import getPositionFromMatrix
from mgear.core.primitive import addTransform


import ymt_shifter_utility as ymtutil
from ymt_shifter_utility import twistSplineBuilder as tsBuilder


def initialize_tsbuilder_conventions():
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
    tsBuilder.CTRL_TWIST_FMT = "{0}_roll{1:02d}_ctl"  # Twist
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
        self.detailControllersGroupName = "controllers_detail"  # TODO: extract to settings
        self.primaryControllersGroupName = "controllers_primary"  # TODO: extract to settings

        self.divisions = len(self.guide.apos)

        self.normal = self.guide.blades["blade"].z * -1
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
        self.previusTag = self.parentCtlTag

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
        self.fk_global_out = []
        self.fk_global_ref = []
        self.fk_uv_param = []

        self.ik_roll_npo = []
        self.ik_decompose_rot = []

        self.length_ctl = None
        self.div_roll_npo = []
        self.fk_local_in2 = []

        self.ikNb = 2
        self.fkNb = self.settings["fkNb"]
        self.surplusFkNb = self.settings["surplusFkNb"]

        # IK controls ---------------------------------------------
        initialize_tsbuilder_conventions()

        if self.surplusFkNb > 1:
            positions = [x for x in self.guide.apos][:-(self.surplusFkNb - 1)]
        else:
            positions = [x for x in self.guide.apos]

        self.dummy_crv = curve.addCurve(
            self.root,
            self.getName("dummy_crv"),
            positions,
            close=False,
            degree=min([len(positions) - 1, 3])
        )
        cmds.nurbsCurveToBezier()  # type: ignore
        self.length = self.dummy_crv.length()
        self.division = len(positions)

        norm = self.guide.blades["blade"].y
        pfx = self.getName("twistSpline")

        tmpRes = ymtutil.convertToTwistSpline(
                self,
                pfx,
                positions,
                self.dummy_crv,
                2,
                norm,
                is_cv_ctl=False,
                is_roll_ctl=True,
                is_otans_ctl=True,
                is_itans_ctl=True
        )
        cvs, oTans, iTans, joints, master_control, self.spline = tmpRes
        cmds.delete(master_control)

        self.out_ctl = [pm.PyNode(x) for x in oTans]
        self.in_ctl = [pm.PyNode(x) for x in iTans]
        self.bts_joints = [pm.PyNode(x) for x in joints]

        for i in range(self.ikNb):
            self.addObjectsChainIk(i, self.dummy_crv, cvs)

        pm.delete(self.dummy_crv)
        # Curves -------------------------------------------
        centers = [x for x in self.ik_ctl]
        for _ in range(2):
            centers.insert(0, self.ik_ctl[0])

        icon.connection_display_curve(self.getName("visualIKRef"), self.ik_ctl)
        self.fk_ctl = self.addObjectsFkControl(self.bts_joints)

    def addObjectsChainIk(self, i, crv, twist_iks):

        cvs = crv.length()
        if i == 0:
            u = 0.
        else:
            u = crv.findParamFromLength(cvs / i)

        space = om.MSpace.kWorld
        pos = crv.getPointAtParam(u, space)

        if i < self.ikNb - 1:
            t = getTransform(self.guide.root)
        else:
            t = getTransform(self.guide.root)
            t = self.guide.atra[-2]

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
        ctl_form = "compas"
        col = self.color_ik
        size = self.size
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
            # ro=datatypes.Vector([0, -math.pi / 2., 0]),
            tp=self.previusTag,
            mirrorConf=self.mirror_conf)

        spline_ik_npo = pm.PyNode(twist_iks[i]).getParent().getName()
        for attr in ymtutil.iter_tr_xyz(spline_ik_npo):
            cmds.setAttr(attr, lock=False)
        cmds.parentConstraint(ik_ctl.getName(), pm.PyNode(twist_iks[i]).getParent().getName(), maintainOffset=True)
        for attr in ymtutil.iter_tr_xyz(spline_ik_npo):
            cmds.setAttr(attr, lock=True)

        ymtutil.setKeyableAttributesDontLockVisibility(ik_ctl, self.tr_params)
        self.ik_ctl.append(ik_ctl)
        attribute.setInvertMirror(ik_ctl, ["tx", "rz", "ry"])

        # ik global ref
        ik_global_ref = primitive.addTransform(
            ik_ctl,
            self.getName("ik%s_global_ref" % i),
            global_t)
        self.ik_global_ref.append(ik_global_ref)
        ymtutil.setKeyableAttributesDontLockVisibility(ik_global_ref, [])

    def _getTransformWithRollByBlade(self, t):
        # t = getTransform(self.guide.root)
        a = self.guide.blades["blade"].y
        x = vector.Blade(t).x
        z = vector.Blade(t).z

        x = vecProjection(a, x)[0]
        z = vecProjection(a, z)[2]

        if abs(x) < 0.001 or abs(z) < 0.001:
            theta = 0.0
        else:
            theta = math.atan2(x, z)
        roll = math.degrees(theta)

        tm = datatypes.TransformationMatrix(t)
        tm.addRotation([0., roll, 0], 'XYZ', om.MSpace.kObject)

        return datatypes.Matrix(tm)

    def addObjectsFkControl(self, joints):

        parentdiv = self.root
        parentctl = self.root

        self.jointList = []
        self.preiviousCtlTag = self.parentCtlTag
        self.div_roll_npo = []

        for i, j in enumerate(joints):
            jt = getTransform(pm.PyNode(j))
            pt = setMatrixPosition(jt, self.guide.apos[i])

            parentdiv, parentctl = self._addObjectsFkControl(i, parentdiv, parentctl, jt, pt)

        if self.surplusFkNb > 1:
            chain = getChainTransform2(self.guide.apos, self.normal, self.negate)
            for i, t in enumerate(chain[-(self.surplusFkNb - 1):]):
                parentdiv, parentctl = self._addObjectsFkControl(i + len(joints), parentdiv, parentctl, t, t)

        # add visual reference
        icon.connection_display_curve(self.getName("visualFKRef"), self.fk_ctl)
        return self.fk_ctl

    def _addObjectsFkControl(self, i, parentdiv, parentctl, t, pt):
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

        self.addToSubGroup(fk_ctl, self.detailControllersGroupName)
        ymtutil.setKeyableAttributesDontLockVisibility(fk_ctl, ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "ro"])
        attribute.setRotOrder(fk_ctl, "ZXY")
        self.fk_ctl.append(fk_ctl)
        self.preiviousCtlTag = fk_ctl

        self.fk_npo.append(fk_npo)
        self.fk_local_npo.append(fk_local_npo)
        parentctl = fk_ctl
        scl_ref = addTransform(parentctl, self.getName("%s_scl_ref" % i), getTransform(parentctl))
        self.scl_transforms.append(scl_ref)

        # Twist references (This objects will replace the spinlookup
        # slerp solver behavior)

        if i == 0 and self.settings["isSplitHip"]:
            t = self._getTransformWithRollByBlade(getTransform(self.guide.root))
            h = (self.guide.apos[-1] - self.guide.apos[0]).length() / (len(self.guide.apos) - 1)
            po = datatypes.Vector([0, self.size / len(self.guide.apos) * -.8, 0])
            hip_fk_local_in = addTransform(p, self.getName("hip_fk_local_in"), t)
            self.hip_fk_local_in = hip_fk_local_in

            self.fk_hip_ctl = self.addCtl(
                hip_fk_local_in,
                "fk_hip_ctl",
                t,
                self.color_fk,
                "cube",
                w=h * .66,
                h=h,
                d=h * 0.3,
                # ro=datatypes.Vector([0, -math.pi / 2., 0]),
                po=po,
                tp=self.preiviousCtlTag,
                mirrorConf=self.mirror_conf)
            hip_scl_ref = addTransform(self.fk_hip_ctl, self.getName("hip_scl_ref"), t)
            ymtutil.setKeyableAttributesDontLockVisibility(
                    self.fk_hip_ctl, ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "ro"])

        # Deformers (Shadow)
        if self.settings["addJoints"]:

            if self.settings["isSplitHip"]:
                if i == 0:
                    self.jnt_pos.append([hip_scl_ref, 0])  # type: ignore

                self.jnt_pos.append([scl_ref, i + 1])

            else:
                self.jnt_pos.append([scl_ref, i])

        return parentdiv, parentctl

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

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

        # Anim -------------------------------------------
        self.volume_att = self.addAnimParam(
            "volume", "Volume", "double", 1, 0, 1)

        self.maxstretch_att = self.addAnimParam(
            "maxstretch",
            "Max Stretch",
            "double",
            self.settings["maxstretch"],
            0.1,
            10.)

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

        self.fk_collapsed_att_rib = self.addAnimParam(
            "rib_traditional_fk",
            "Rib Traditional FK",
            "bool",
            True
        )

        self.fk_collapsed_att_belly = self.addAnimParam(
            "belly_traditional_fk",
            "Belly Traditional FK",
            "bool",
            False
        )

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

        pm.parentConstraint(self.bts_joints[0], self.fk_npo[0], maintainOffset=True, skipRotate=("x", "y", "z"))

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

        for i, jnt in enumerate(self.bts_joints[:-1]):
            cmds.aimConstraint(
                self.bts_joints[i + 1].getName(),
                jnt.getName(),
                mo=True,
                aimVector=(1, 0, 0),
                upVector=(1, 0, 0),
                worldUpType="object",
                worldUpObject=self.root.longName()
            )

        for i in range(len(self.guide.apos)):
            self.addFkOperator(i, rootWorld_node)

        driver_shape = self.spline.getShape()
        for attr in cmds.listAttr("{}.vertexData".format(driver_shape.getName()), multi=True) or []:
                if "useOrient" in attr:
                    cmds.setAttr("{}.{}".format(driver_shape.getName(), attr), True)

    def addFkOperator(self, i, rootWorld_node):

        if i == 0 and self.settings["isSplitHip"]:
            self.addFkHipOperator()

        fk_local_npo_xfoms = []
        if i not in [len(self.guide.apos), 0]:
            xform = getTransform(self.fk_local_npo[i])
            fk_local_npo_xfoms.append(xform)

        # break FK hierarchical orient
        tail_count = len(self.guide.apos) - self.surplusFkNb + 1

        print(f"{i=}, {tail_count=}, {len(self.guide.apos)=}, {self.surplusFkNb=}")
        if i not in (0, len(self.guide.apos)):

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

            check_list = (pm.Attribute, six.string_types)  # noqa

            cond = pm.createNode("condition")
            pm.setAttr(cond + ".operation", 4)  # greater

            if i >= tail_count:
                attribute.connectSet(self.fk_collapsed_att_rib, cond + ".secondTerm", check_list)
            else:
                attribute.connectSet(self.fk_collapsed_att_belly, cond + ".secondTerm", check_list)

            attribute.connectSet(dm_node + ".outputRotate", cond + ".colorIfTrue", check_list)

            pm.setAttr(cond + ".colorIfFalseR", 0.)
            pm.setAttr(cond + ".colorIfFalseG", 0.)
            pm.setAttr(cond + ".colorIfFalseB", 0.)

            pm.connectAttr(cond + ".outColor", d.attr("r"))
            
        # References
        tmp_div_npo_transform = getTransform(self.div_cns_npo[i])  # to fix mismatch before/after later

        if i < (len(self.fk_ctl) - self.surplusFkNb):
            cns = pm.parentConstraint(self.bts_joints[i], self.div_cns[i], maintainOffset=True)

        elif i == (len(self.fk_ctl) - self.surplusFkNb):
            cns = pm.parentConstraint(self.bts_joints[i], self.div_cns[i], maintainOffset=True, skipRotate=("x", "y", "z"))
            cns = pm.parentConstraint(self.ik_ctl[-1], self.div_cns[i], maintainOffset=True, skipTranslate=("x", "y", "z"))

        elif i > (len(self.fk_ctl) - self.surplusFkNb):
            pass

        self.div_cns[i].attr("r") >> self.fk_npo[i].attr("r")
        self.div_cns[i].attr("t") >> self.fk_npo[i].attr("t")

    def addFkHipOperator(self):
        s = self.fk_hip_ctl
        d = self.fk_local_npo[0],
        # maintainOffset, skipRotate, skipTranslate
        _ = pm.parentConstraint(s, d, mo=True, sr=("x", "y", "z"), st=())

        s = self.ik_global_out[0]
        d = self.hip_fk_local_in,
        # maintainOffset, skipRotate, skipTranslate
        pm.parentConstraint(s, d, mo=True)

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

    # =====================================================
    # CONNECTOR
    # =====================================================

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""

        self.relatives["root"] = self.fk_ctl[0]
        self.relatives["eff"] = self.fk_ctl[-1]
        self.controlRelatives["root"] = self.fk_ctl[0]

        self.jointRelatives["root"] = 0

        # for i in range(0, len(self.fk_ctl) - 1):

        for i in range(0, len(self.guide.apos) - 1):

            if self.settings["isSplitHip"]:
                self.relatives["root"] = self.fk_hip_ctl
                self.controlRelatives["root"] = self.fk_hip_ctl

            self.relatives["%s_loc" % i] = self.fk_ctl[i + 1]
            self.controlRelatives["%s_loc" % i] = self.fk_ctl[i + 1]

            self.jointRelatives["%s_loc" % (i)] = (i + 2)
            self.aliasRelatives["%s_ctl" % (i)] = (i + 2)

            self.relatives["0_loc"] = self.fk_ctl[1]
            self.controlRelatives["0_loc"] = self.fk_ctl[1]

            self.jointRelatives["0_loc"] = (2)
            self.aliasRelatives["0_ctl"] = (2)

    def addToSubGroup(self, obj, group_name):

        if self.settings["ctlGrp"]:
            ctlGrp = self.settings["ctlGrp"]
        else:
            ctlGrp = "controllers"

        self.addToGroup(obj, group_name, parentGrp=ctlGrp)


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
