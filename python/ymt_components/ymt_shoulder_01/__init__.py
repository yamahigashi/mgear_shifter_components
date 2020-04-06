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

if False:
    from typing import List, Tuple, Any


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
        chain_pos = [
            self.guide.apos[0],
            arm_comp.guide.apos[1],
            arm_comp.guide.apos[2]
        ]
        arm_comp.dummy_chain = pri.add2DChain(arm_comp.root, arm_comp.getName("dummy_chain"), chain_pos, arm_comp.normal, arm_comp.negate)
        arm_comp.dummy_chain[0].attr("visibility").set(arm_comp.WIP)
        arm_comp.dummy_ikh = pri.addIkHandle(arm_comp.root, arm_comp.getName("dummy_ikh"), arm_comp.dummy_chain)
        arm_comp.dummy_ikh.attr("visibility").set(False)
        pm.poleVectorConstraint(arm_comp.upv_ctl, arm_comp.dummy_ikh)
        pm.makeIdentity(arm_comp.dummy_chain[0], a=1, t=1, r=1, s=1)

        t = tra.getTransform(arm_comp.dummy_chain[0])
        arm_comp.dummy_chain_npo = pri.addTransform(arm_comp.dummy_chain[0], self.getName("dummychain_npo"), t)
        arm_comp.dummy_chain_offset = pm.createNode("math_MatrixFromRotation")
        mult = pm.createNode("multMatrix")
        pm.connectAttr("{}.matrix".format(arm_comp.dummy_chain[0]), "{}.matrixIn[0]".format(mult))
        pm.connectAttr("{}.output".format(arm_comp.dummy_chain_offset), "{}.matrixIn[1]".format(mult))

        rot = pm.createNode("math_RotationFromMatrix")
        cmds.setAttr("{}.rotationOrder".format(rot), cmds.getAttr("{}.rotateOrder".format(arm_comp.dummy_chain[0])))
        pm.connectAttr("{}.matrixSum".format(mult), "{}.input".format(rot))
        pm.connectAttr("{}.output".format(rot), "{}.rotate".format(arm_comp.dummy_chain_npo))

    def set_softik_dummy(self, arm_comp):
        # --------------------------------------------------
        # refs: https://qiita.com/hossan_TK9004/items/a76a58a49f6affb1ab21
        nt = cmds.createNode('network', n='softIK_info')
        cmds.addAttr(nt, ln='ikMaxLength', at='float')
        cmds.addAttr(nt, ln='startLengthSoftCorrection', at='float')

        # get max Distance
        rootVector = self.guide.apos[0]
        currentVector = arm_comp.guide.pos["wrist"]
        t = tra.getTransformFromPos(arm_comp.guide.pos["wrist"])
        self.softdummy_npo = pri.addTransform(self.root, self.getName("softdummy_npo"), t)
        pm.pointConstraint(self.softdummy_npo, arm_comp.dummy_ikh, maintainOffset=False)

        distanceVector = rootVector - currentVector
        maxDistance = distanceVector.length()
        softStartLength = maxDistance * 0.8

        cmds.setAttr('{}.ikMaxLength'.format(nt), maxDistance)
        cmds.setAttr('{}.startLengthSoftCorrection'.format(nt), softStartLength)

        # culculate soft pct
        distNode = cmds.shadingNode('distanceBetween', au=True, n='currentLength')
        down, _, up = findPathAtoB(arm_comp.ik_ctl, self.root)
        ikMat = pm.createNode("multMatrix")
        for i, d in enumerate(down):
            pm.connectAttr("{}.matrix".format(d), "{}.matrixIn[{}]".format(ikMat, i))
        pm.connectAttr("{}.matrixSum".format(ikMat), "{}.inMatrix2".format(distNode))

        # ---
        culLength = cmds.shadingNode('plusMinusAverage', au=True, n='culLength')
        cmds.setAttr('{}.operation'.format(culLength), 2)
        cmds.connectAttr('{}.distance'.format(distNode), '{}.input2D[0].input2Dx'.format(culLength))
        cmds.connectAttr('{}.startLengthSoftCorrection'.format(nt), '{}.input2D[1].input2Dx'.format(culLength))
        cmds.connectAttr('{}.ikMaxLength'.format(nt), '{}.input2D[0].input2Dy'.format(culLength))
        cmds.connectAttr('{}.startLengthSoftCorrection'.format(nt), '{}.input2D[1].input2Dy'.format(culLength))

        culSoftPct = cmds.shadingNode('multiplyDivide', au=True, n='culSoftPct')
        cmds.setAttr('{}.operation'.format(culSoftPct), 2)
        cmds.connectAttr('{}.output2Dx'.format(culLength), '{}.input1X'.format(culSoftPct))
        cmds.connectAttr('{}.output2Dy'.format(culLength), '{}.input2X'.format(culSoftPct))

        # create animCurveNode
        culSoftLength = cmds.shadingNode('multDoubleLinear', au=True, n='culSoftLength')
        cv = cmds.createNode('animCurveUU', n='softCorrectionCurve')
        cmds.connectAttr('{}.outputX'.format(culSoftPct), '{}.input'.format(cv))
        cmds.connectAttr('{}.output'.format(cv), '{}.input1'.format(culSoftLength))
        cmds.connectAttr('{}.output2Dy'.format(culLength), '{}.input2'.format(culSoftLength))

        cmds.setDrivenKeyframe(culSoftLength, at=('input1'), cd='{}.outputX'.format(culSoftPct), dv=0.0, v=0.0, itt='clamped', ott='clamped')
        cmds.setDrivenKeyframe(culSoftLength, at=('input1'), cd='{}.outputX'.format(culSoftPct), dv=1.0, v=1.0, itt='clamped', ott='clamped')
        angle = cmds.keyTangent(cv, q=True, index=(0, 0), inAngle=True)[0]
        cmds.keyframe(cv, index=(1, 1), floatChange=2)
        cmds.keyTangent(cv, index=(1, 1), itt='flat', ott='flat')
        cmds.keyTangent(cv, index=(0, 0), inAngle=angle)
        cmds.setAttr('{}.preInfinity'.format(cv), 1)
        cmds.setAttr('{}.postInfinity'.format(cv), 1)

        # cul softLength
        culAllSoftLength = cmds.shadingNode('addDoubleLinear', au=True, n='culAllSoftLength')
        cmds.connectAttr('{}.output'.format(culSoftLength), '{}.input1'.format(culAllSoftLength))
        cmds.connectAttr('{}.startLengthSoftCorrection'.format(nt), '{}.input2'.format(culAllSoftLength))
        culSoftLengthPct = cmds.shadingNode('multiplyDivide', au=True, n='culSoftLengthPct')
        cmds.setAttr('{}.operation'.format(culSoftLengthPct), 2)
        cmds.connectAttr('{}.output'.format(culAllSoftLength), '{}.input1X'.format(culSoftLengthPct))
        cmds.connectAttr('{}.distance'.format(distNode), '{}.input2X'.format(culSoftLengthPct))

        trans = pm.createNode('math_TranslationFromMatrix')
        softedTrns = cmds.shadingNode('multiplyDivide', au=True, n='softedTrns')
        cmds.connectAttr('{}.outputX'.format(culSoftLengthPct), '{}.input1X'.format(softedTrns))
        cmds.connectAttr('{}.outputX'.format(culSoftLengthPct), '{}.input1Y'.format(softedTrns))
        cmds.connectAttr('{}.outputX'.format(culSoftLengthPct), '{}.input1Z'.format(softedTrns))
        cmds.connectAttr('{}.outputX'.format(trans), '{}.input2X'.format(softedTrns))
        cmds.connectAttr('{}.outputY'.format(trans), '{}.input2Y'.format(softedTrns))
        cmds.connectAttr('{}.outputZ'.format(trans), '{}.input2Z'.format(softedTrns))

        # createCondition
        cond = cmds.shadingNode('condition', au=True, n='checkCurrentDistance')
        cmds.setAttr('{}.operation'.format(cond), 2)
        cmds.connectAttr('{}.distance'.format(distNode), '{}.firstTerm'.format(cond))
        cmds.connectAttr('{}.startLengthSoftCorrection'.format(nt), '{}.secondTerm'.format(cond))

        cmds.connectAttr('{}.matrixSum'.format(ikMat), '{}.input'.format(trans))
        cmds.connectAttr('{}.outputX'.format(trans), '{}.colorIfFalseR'.format(cond))
        cmds.connectAttr('{}.outputY'.format(trans), '{}.colorIfFalseG'.format(cond))
        cmds.connectAttr('{}.outputZ'.format(trans), '{}.colorIfFalseB'.format(cond))
        cmds.connectAttr('{}.outputX'.format(softedTrns), '{}.colorIfTrueR'.format(cond))
        cmds.connectAttr('{}.outputY'.format(softedTrns), '{}.colorIfTrueG'.format(cond))
        cmds.connectAttr('{}.outputZ'.format(softedTrns), '{}.colorIfTrueB'.format(cond))

        # connect softIK
        cmds.connectAttr('{}.outColorR'.format(cond), '{}.translateX'.format(self.softdummy_npo))
        cmds.connectAttr('{}.outColorG'.format(cond), '{}.translateY'.format(self.softdummy_npo))
        cmds.connectAttr('{}.outColorB'.format(cond), '{}.translateZ'.format(self.softdummy_npo))

        # apply offset to rest angle
        cmds.setAttr("{}.inputX".format(arm_comp.dummy_chain_offset), -1. * cmds.getAttr("{}.rx".format(arm_comp.dummy_chain[0])))
        cmds.setAttr("{}.inputY".format(arm_comp.dummy_chain_offset), -1. * cmds.getAttr("{}.ry".format(arm_comp.dummy_chain[0])))
        cmds.setAttr("{}.inputZ".format(arm_comp.dummy_chain_offset), -1. * cmds.getAttr("{}.rz".format(arm_comp.dummy_chain[0])))
        cmds.setAttr("{}.rotationOrder".format(arm_comp.dummy_chain_offset), cmds.getAttr("{}.rotateOrder".format(arm_comp.dummy_chain[0])))

    def add_arm_connection_attr(self, arm_comp):
        self.roll_att_pos = self.addAnimParam("roll_pos", "rollPositive", "double", 0.0, 0, 1.0)
        self.roll_att_neg = self.addAnimParam("roll_neg", "rollNegative", "double", 0.0, 0, 1.0)
        self.bendH_att_pos = self.addAnimParam("bendH_pos", "bendHorizonPositive", "double", 0.12, 0, 1.0)
        self.bendH_att_neg = self.addAnimParam("bendH_neg", "bendHorizonNegative", "double", 0.6, 0, 1.0)
        self.bendV_att_pos = self.addAnimParam("bendV_pos", "bendVerticalPositive", "double", 0.45, 0, 1.0)
        self.bendV_att_neg = self.addAnimParam("bendV_neg", "bendVerticalNegative", "double", 0.4, 0, 1.0)

    def decompose_rotate(self, src, rate_for_radian=2. / math.pi, smooth_step=False):
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

            if smooth_step:
                stepped_port = self.smooth_step(out_port)
            else:
                stepped_port = out_port

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
        self.arm_npo.addChild(arm_comp.dummy_chain_npo)
        self.arm_npo.addChild(arm_comp.dummy_ikh)

        self.shoulder_npo = pri.addTransform(self.ctl_npo, self.getName("dummy_npo2"), t)
        self.shoulder_npo.addChild(self.ctl)

        fk_quat = self.decompose_rotate(arm_comp.fk_ctl[0], smooth_step=arm_comp.settings["smoothStep"])
        ik_quat = self.decompose_rotate(arm_comp.dummy_chain_npo, smooth_step=arm_comp.settings["smoothStep"])

        slerp = pm.createNode("quatSlerp")
        pm.connectAttr("{}.outputQuat".format(fk_quat), "{}.input1Quat".format(slerp))
        pm.connectAttr("{}.outputQuat".format(ik_quat), "{}.input2Quat".format(slerp))
        pm.connectAttr(arm_comp.blend_att, "{}.inputT".format(slerp))

        quat2euler = pm.createNode("quatToEuler")
        pm.connectAttr(slerp + ".outputQuat", quat2euler + ".inputQuat")
        pm.connectAttr(quat2euler + ".outputRotate", self.shoulder_npo + ".rotate")

    def reparent_arm_hierarchy(self, arm_comp):

        self.orbit_ref2.addChild(arm_comp.ik_cns)
        self.orbit_ref2.addChild(arm_comp.upv_cns)

        if "ymt_arm_2jnt_01" in str(type(arm_comp)):
            self.orbit_ref2.addChild(arm_comp.ikRot_npo)
        self.orbit_ref2.addChild(arm_comp.armChainUpvRef[0])
        self.orbit_ref2.addChild(arm_comp.ikHandleUpvRef)

    def connect_arm(self, arm_comp):
        if not cmds.pluginInfo("rotationDriver.py", q=True, loaded=True):
            cmds.loadPlugin("rotationDriver.py", quiet=True)

        if not cmds.pluginInfo("maya-math-nodes.mll", q=True, loaded=True):
            cmds.loadPlugin("maya-math-nodes.mll", quiet=True)

        cycle = cmds.cycleCheck(q=True, evaluation=True)
        try:
            cmds.cycleCheck(evaluation=False)

            self.insert_dummy_arm(arm_comp)
            self.add_arm_connection_attr(arm_comp)
            self.add_arm_connection_object(arm_comp)
            self.reparent_arm_hierarchy(arm_comp)
            self.set_softik_dummy(arm_comp)

        except Exception:
            import traceback as tb
            tb.print_exc()
            tb.print_stack()

        finally:
            cycle = cmds.cycleCheck(evaluation=cycle)


def getFullPath(start, routes=None):
    # type: (pm.nt.transform, List[pm.nt.transform]) -> List[pm.nt.transform]
    if not routes:
        routes = []

    if not start.getParent():
        return routes

    else:
        return getFullPath(start.getParent(), routes + [start, ])


def findPathAtoB(a, b):
    # type: (pm.nt.transform, pm.nt.transform) -> Tuple[List[pm.nt.transform], pm.nt.transform, List[pm.nt.transform]]
    """Returns route of A to B in formed Tuple[down(to root), turning point, up(to leaf)]"""
    # aPath = ["x", "a", "b", "c"]
    # bPath = ["b", "c"]
    # down [x, a]
    # turn b
    # up []

    aPath = getFullPath(a)
    bPath = getFullPath(b)

    return _findPathAtoB(aPath, bPath)


def _findPathAtoB(aPath, bPath):
    # type: (List, List) -> Tuple[List, Any, List]
    """Returns route of A to B in formed Tuple[down(to root), turning point, up(to leaf)]

    >>> aPath = ["x", "a", "b", "c"]
    >>> bPath = ["b", "c"]
    >>> d, c, u = _findPathAtoB(aPath, bPath)
    >>> d == ["x", "a"]
    True
    >>> c == "b"
    True
    >>> u == []
    True

    """
    down = []
    up = []
    sharedNode = None

    for u in aPath:
        if u in bPath:
            sharedNode = u
            break

        down.append(u)

    idx = bPath.index(sharedNode)
    up = list(reversed(bPath[:(idx)]))

    return down, sharedNode, up
