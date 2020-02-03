import math

# Maya
import maya.cmds as cmds

import pymel.core as pm
import pymel.core.datatypes as dt

# mgear
from mgear.shifter.component import MainComponent

import mgear.core.primitive as pri
import mgear.core.transform as tra

import mgear.core.vector as vec


##########################################################
# COMPONENT
##########################################################
class Component(MainComponent):

    # =====================================================
    # OBJECTS
    # =====================================================
    # Add all the objects needed to create the component.
    # @param self
    def addObjects(self):

        po = dt.Vector(self.settings["ctlOffsetPosX"], self.settings["ctlOffsetPosY"], self.settings["ctlOffsetPosZ"])
        so = dt.Vector(self.settings["ctlOffsetSclX"], self.settings["ctlOffsetSclY"], self.settings["ctlOffsetSclZ"])
        ro = [self.settings["ctlOffsetRotX"], self.settings["ctlOffsetRotY"], self.settings["ctlOffsetRotZ"]]
        ro = set(map(lambda x: math.radians(x), ro))
        ro = dt.Vector(*ro)

        self.normal = self.guide.blades["blade"].z * -1
        self.binormal = self.guide.blades["blade"].x

        self.length0 = vec.getDistance(self.guide.apos[0], self.guide.apos[1])

        t = tra.getTransformLookingAt(self.guide.apos[0], self.guide.apos[1], self.normal, axis="xy", negate=self.negate)
        self.ctl_npo = pri.addTransform(self.root, self.getName("ctl_npo"), t)

        self.ctl = self.addCtl(
            self.ctl_npo, "ctl", t, self.color_fk, "cube",
            w=(self.length0 * so.x), h=(self.size * .1 * so.y), d=(self.size * .1 * so.z),
            po=(dt.Vector(.5 * self.length0 * self.n_factor, 0, 0) + po)
        )

        t = tra.getTransformFromPos(self.guide.apos[0])
        self.orbit_ref1 = pri.addTransform(self.root, self.getName("orbit_ref1"), t)
        t = tra.getTransformFromPos(self.guide.apos[1])
        self.orbit_ref2 = pri.addTransform(self.root, self.getName("orbit_ref2"), t)

        self.orbit_cns = pri.addTransform(self.ctl, self.getName("orbit_cns"), t)

        self.orbit_npo = pri.addTransform(self.orbit_cns, self.getName("orbit_npo"), t)
        self.orbit_ctl = self.addCtl(self.orbit_npo, "orbit_ctl", t, self.color_fk, "sphere", w=self.length0 / 4)

        self.jnt_pos.append([self.ctl, "shoulder"])

    # =====================================================
    # PROPERTY
    # =====================================================
    def addAttributes(self):

        cmds.loadPlugin("lookdevKit.mll", quiet=True)

        # Ref
        if self.settings["refArray"]:
            ref_names = self.settings["refArray"].split(",")
            if len(ref_names) >= 1:
                self.ref_att = self.addAnimEnumParam("rotRef", "Ref", 0, self.settings["refArray"].split(","))

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        return

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        self.relatives["root"] = self.ctl
        self.relatives["tip"] = self.orbit_ctl

        self.jointRelatives["root"] = 0
        self.jointRelatives["tip"] = 0

    # @param self
    def addConnection(self):
        self.connections["arm"] = self.connect_arm

    def connect_standard(self):
        self.parent.addChild(self.root)
        self.connect_standardWithRotRef(self.settings["refArray"], self.orbit_cns)

    def insert_dummy_arm(self, arm_comp):
        # IK dummy Chain -----------------------------------------
        arm_comp.dummy_chain = pri.add2DChain(arm_comp.root, arm_comp.getName("dummy_chain"), arm_comp.guide.apos[0:-1], arm_comp.normal, arm_comp.negate)
        arm_comp.dummy_chain[0].attr("visibility").set(arm_comp.WIP)
        arm_comp.dummy_ikh = pri.addIkHandle(arm_comp.root, arm_comp.getName("dummy_ikh"), arm_comp.dummy_chain)
        arm_comp.dummy_ikh.attr("visibility").set(False)
        pm.poleVectorConstraint(arm_comp.upv_ctl, arm_comp.dummy_ikh)
        pm.pointConstraint(arm_comp.ik_ctl, arm_comp.dummy_ikh, maintainOffset=False)
        pm.makeIdentity(arm_comp.dummy_chain[0], a=1, t=1, r=1, s=1)

    def add_arm_connection_attr(self, arm_comp):
        self.roll_att_pos = self.addAnimParam("roll_pos", "rollPositive", "double", 0.0, 0, 1.0)
        self.roll_att_neg = self.addAnimParam("roll_neg", "rollNegative", "double", 0.0, 0, 1.0)
        self.bendH_att_pos = self.addAnimParam("bendH_pos", "bendHorizonPositive", "double", 0.08, 0, 1.0)
        self.bendH_att_neg = self.addAnimParam("bendH_neg", "bendHorizonNegative", "double", 0.45, 0, 1.0)
        self.bendV_att_pos = self.addAnimParam("bendV_pos", "bendVerticalPositive", "double", 0.1, 0, 1.0)
        self.bendV_att_neg = self.addAnimParam("bendV_neg", "bendVerticalNegative", "double", 0.3, 0, 1.0)

    def decompose_rotate(self, src, rate_for_radian=1. / math.pi):
        decomp = pm.createNode("decomposeRotate")
        pm.connectAttr(src + ".rotate", decomp + ".rotate")
        pm.connectAttr(src + ".rotateOrder", decomp + ".rotateOrder")

        comp = pm.createNode("composeRotate")
        pm.connectAttr(src + ".rotateOrder", comp + ".rotateOrder")
        if not self.negate:
            pass
            # pm.setAttr("{}.reverseOrder".format(decomp), True)
            # pm.setAttr("{}.reverseOrder".format(comp), True)
        else:
            pm.setAttr("{}.axisOrient".format(decomp), dt.Vector(180, 0, 0))
            pm.setAttr("{}.axisOrient".format(comp), dt.Vector(180, 0, 0))

        for att in ["roll", "bendH", "bendV"]:
            # conv_in = pm.createNode("unitConversion")a
            out = "out" + att[0].upper() + att[1:]
            out_port = "{}.{}".format(decomp, out)
            stepped_port = self.smooth_step(out_port)

            multiply = pm.createNode("floatMath")
            pm.connectAttr(stepped_port, "{}.floatA".format(multiply))
            pm.setAttr(multiply + ".operation", 2)

            try:
                pm.connectAttr(multiply + ".outFloat", comp + "." + att)
            except AttributeError:
                pm.connectAttr(multiply + ".outValue", comp + "." + att)

            if self.negate:
                attr_neg = self.__getattribute__(att + "_att_pos")
                attr_pos = self.__getattribute__(att + "_att_neg")
            else:
                attr_pos = self.__getattribute__(att + "_att_pos")
                attr_neg = self.__getattribute__(att + "_att_neg")
            cond = pm.createNode("condition")
            pm.connectAttr(attr_pos, cond + ".colorIfTrue.colorIfTrueR")
            pm.connectAttr(attr_neg, cond + ".colorIfFalse.colorIfFalseR")
            pm.connectAttr(decomp + "." + out, cond + ".firstTerm")
            pm.setAttr(cond + ".operation", 2)

            pm.connectAttr(cond + ".outColor.outColorR", multiply + ".floatB")

            for unit_conv in cmds.listConnections(out_port, s=False, d=True, type="unitConversion"):
                pm.setAttr("{}.conversionFactor".format(unit_conv), rate_for_radian)

        toQuat = pm.createNode("eulerToQuat")
        pm.connectAttr("{}.outRotate".format(comp), "{}.inputRotate".format(toQuat))

        for unit_conv in cmds.listConnections("{}".format(comp), s=True, d=False, type="unitConversion"):
            pm.setAttr("{}.conversionFactor".format(unit_conv), 1.0 / rate_for_radian)

        return toQuat

    def smooth_step(self, in_port):
        cond = pm.createNode("condition")
        pm.connectAttr(in_port, "{}.firstTerm".format(cond))
        pm.setAttr("{}.secondTerm".format(cond), 0.)
        pm.setAttr("{}.operation".format(cond), 3)  # Greater Equal
        pm.setAttr("{}.colorIfTrue.colorIfTrueR".format(cond), 1.)
        pm.setAttr("{}.colorIfFalse.colorIfFalseR".format(cond), -1.)

        absval = pm.createNode("math_Absolute")
        smooth = pm.createNode("math_Smoothstep")

        pm.connectAttr(in_port, "{}.input".format(absval))
        pm.connectAttr("{}.output".format(absval), "{}.input".format(smooth))

        multiply = pm.createNode("floatMath")
        pm.connectAttr("{}.output".format(smooth), "{}.floatA".format(multiply))
        pm.connectAttr("{}.outColor.outColorR".format(cond), "{}.floatB".format(multiply))
        pm.setAttr(multiply + ".operation", 2)

        return "{}.outFloat".format(multiply)

    # def sigmoid(self):
    #    return vec3(1.0) / (vec3(1.0) + exp(-(x * 10.0 - 5.0)))

    def add_arm_connection_object(self, arm_comp):
        t = tra.getTransformLookingAt(self.guide.apos[0], self.guide.apos[1], self.normal, axis="xy", negate=self.negate)
        self.arm_npo = pri.addTransform(self.ctl_npo, self.getName("dummy_npo"), t)
        pm.connectAttr("{}.rotate".format(self.ctl), "{}.rotate".format(self.arm_npo))
        self.arm_npo.addChild(arm_comp.dummy_chain[0])
        self.arm_npo.addChild(arm_comp.dummy_ikh)

        self.shoulder_npo = pri.addTransform(self.ctl_npo, self.getName("dummy_npo2"), t)
        self.shoulder_npo.addChild(self.ctl)

        t = tra.getTransformFromPos(self.guide.apos[0])
        # self.orbit_ref3 = pri.addTransform(self.orbit_cns, self.getName("orbit_ref3"), t)
        self.orbit_ref3 = pri.addTransform(self.root, self.getName("orbit_ref3"), t)
        npo = pm.duplicate(arm_comp.dummy_chain[0])[0]
        # self.orbit_npo = pri.addTransform(self.orbit_cns, self.getName("orbit_npo"), t)
        self.orbit_ref1.addChild(npo)

        fk_quat = self.decompose_rotate(arm_comp.fk_ctl[0])
        ik_quat = self.decompose_rotate(arm_comp.dummy_chain[0])

        slerp = pm.createNode("quatSlerp")
        pm.connectAttr("{}.outputQuat".format(fk_quat), "{}.input1Quat".format(slerp))
        pm.connectAttr("{}.outputQuat".format(ik_quat), "{}.input2Quat".format(slerp))
        pm.connectAttr(arm_comp.blend_att, "{}.inputT".format(slerp))

        quat2euler = pm.createNode("quatToEuler")
        pm.connectAttr(slerp + ".outputQuat", quat2euler + ".inputQuat")
        pm.connectAttr(quat2euler + ".outputRotate", self.shoulder_npo + ".rotate")

        self.orbit_ref2.addChild(arm_comp.ik_cns)
        self.orbit_ref2.addChild(arm_comp.upv_cns)

        if "ymt_arm_2jnt_01" in str(type(arm_comp)):
            self.orbit_ref2.addChild(arm_comp.ikRot_npo)
        self.orbit_ref2.addChild(arm_comp.armChainUpvRef[0])
        self.orbit_ref2.addChild(arm_comp.ikHandleUpvRef)

        return
        t = tra.getTransformFromPos(self.guide.apos[0])
        self.orbit_ref3 = pri.addTransform(self.root, self.getName("orbit_ref3"), t)
        pm.parentConstraint(self.orbit_ctl, self.orbit_ref3, maintainOffset=True)
        try:
            self.orbit_ref3.addChild(arm_comp.fk_cns)
        except AttributeError:
            try:
                self.orbit_ref3.addChild(arm_comp.fk_npo[0])
            except AttributeError:
                self.orbit_ref3.addChild(arm_comp.fk0_cns)

    def connect_arm(self, arm_comp):
        if not cmds.pluginInfo("rotationDriver.py", q=True, loaded=True):
            cmds.loadPlugin("rotationDriver.py", quiet=True)

        cycle = cmds.cycleCheck(q=True, evaluation=True)
        try:
            cmds.cycleCheck(evaluation=False)
            self.insert_dummy_arm(arm_comp)
            self.add_arm_connection_attr(arm_comp)
            self.add_arm_connection_object(arm_comp)

        except Exception:
            import traceback as tb
            tb.print_exc()
            tb.print_stack()

        finally:
            cycle = cmds.cycleCheck(evaluation=cycle)
