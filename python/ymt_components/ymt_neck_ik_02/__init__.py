import sys
import six
import textwrap

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import importlib
try:
    pm = importlib.import_module("mgear.pymaya")
except ImportError:
    pm = importlib.import_module("pymel.core")
try:
    dt = importlib.import_module("mgear.pymaya.datatypes")
except ImportError:
    dt = importlib.import_module("pymel.core.datatypes")


# mgear
import mgear
from mgear.shifter.component import MainComponent

import mgear.core.primitive as pri
import mgear.core.transform as tra
import mgear.core.attribute as att
import mgear.core.vector as vec
import ymt_shifter_utility as ymt_util

if sys.version_info >= (3, 0):  # pylint: disable=using-constant-test
    # For type annotation
    from typing import Optional, Dict, List, Tuple, Pattern, Callable, Any, Text  # NOQA
    import pathlib


##########################################################
# COMPONENT
##########################################################
class Component(MainComponent):

    def addNeckBones(self, positions: object, upv0: object, upv1: object) -> None:

        root_t = tra.getTransform(self.root)
        neck_t = tra.getTransformLookingAt(positions[0], upv0, self.normal, "yx", self.negate)
        head_t = tra.getTransformLookingAt(positions[-1], upv1, self.normal, "yx", self.negate)
        head_pos = positions[-1]

        self.neck_cnss = []
        self.neck_ctls = []
        self.neck_npos = []
        self.neck_refs = []

        for i, pos in enumerate(positions[:-1]):

            t = tra.setMatrixPosition(root_t, pos)
            cns = pri.addTransform(self.root, self.getName("neck{}_cns".format(i)), t)

            t = tra.setMatrixPosition(neck_t, pos)
            npo = pri.addTransform(cns, self.getName("neck{}_npo".format(i)), t)

            length = vec.getDistance(positions[i], positions[i + 1])
            w = self.size * 0.1
            h = length * 0.5
            d = self.size * 0.55
            ctl = self.addCtl(
                npo,
                "fk{}_ctl".format(i),
                t,
                self.color_fk,
                "cube",
                po=dt.Vector(0, length * 0.5, 0),
                w=w,
                h=h,
                d=d,
            )
            ymt_util.setKeyableAttributesDontLockVisibility(ctl, ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "ro"])
            att.setRotOrder(ctl, "ZXY")
            att.setInvertMirror(ctl, ["tx", "ry", "rz"])

            if i < len(positions) - 2:
                next_t = tra.setMatrixPosition(neck_t, positions[i + 1])
                pos_ref = pri.addTransform(ctl, self.getName("pos{}_ref".format(i)), next_t)
            else:
                pos_ref = pri.addTransform(ctl, self.getName("pos{}_ref".format(i)), head_t)

            self.jnt_pos.append([ctl, i])
            self.neck_cnss.append(cns)
            self.neck_ctls.append(ctl)
            self.neck_npos.append(npo)
            self.neck_refs.append(pos_ref)

        t = tra.getTransformLookingAt(head_pos, upv1, self.normal, "yx", self.negate)
        self.head_pos_ref = pri.addTransform(self.neck_ctls[-1], self.getName("head_pos_ref"), t)

    # Add all the objects needed to create the component.
    # @param self
    def addObjects(self) -> None:

        self.normal = self.guide.blades["blade"].z * -1.

        tan_pos = self.guide.apos[1]
        eff0_pos = self.guide.apos[2]
        eff1_pos = self.guide.apos[3]
        neck_pos = self.guide.apos[4]
        head_pos = self.guide.apos[-1]
        jnts_pos = self.guide.apos[4:]

        self.division = len(jnts_pos)
        self.addNeckBones(jnts_pos, eff0_pos, eff1_pos)

        # Head ---------------------------------------------
        t = tra.getTransform(self.root)
        t = tra.setMatrixPosition(t, head_pos)
        self.head_cns = pri.addTransform(self.root, self.getName("head_cns"), t)

        t = tra.getTransformLookingAt(head_pos, eff1_pos, self.normal, "yx", self.negate)
        self.head_npo = pri.addTransform(self.head_cns, self.getName("head_npo"), t)

        dist = vec.getDistance(head_pos, eff1_pos)
        w = self.size * 0.5
        h = dist
        d = self.size * 0.5
        po = dt.Vector(0, dist * 0.5, 0)

        self.head_ctl = self.addCtl(
            self.head_npo,
            "head_ctl",
            t,
            self.color_ik,
            "compas",
            w=w,
            h=h,
            d=d,
            po=po,
        )
        ymt_util.setKeyableAttributesDontLockVisibility(
            self.head_ctl,
            ["rx", "ry", "rz", "sx", "sy", "sz", "ro"],
        )
        att.setRotOrder(self.head_ctl, "ZXY")
        att.setInvertMirror(self.head_ctl, ["tx", "ry", "rz"])

        self.jnt_pos.append([self.head_ctl, "head"])

    # =====================================================
    # PROPERTY
    # =====================================================
    # Add parameters to the anim and setup properties to control the component.
    # @param self
    def addAttributes(self) -> None:
        # Anim -------------------------------------------
        ref_names = ["self", "head"]
        self.neckref_att = self.addAnimEnumParam("neck_ref", "Neck Ref", 1, ref_names)
        self.neckrate_att = self.addAnimParam("neck_rate", "Neck Rate", "double", 0.8, 0.0, 1.0)  # TODO: setting

        if self.settings["headrefarray"]:
            ref_names = self.settings["headrefarray"].split(",")
            ref_names.insert(0, "self")
            self.headref_att = self.addAnimEnumParam("headref", "Head Ref", 1, ref_names)
        else:
            self.headref_att = self.addAnimEnumParam("headref", "Head Ref", 0, ["self"])

    # =====================================================
    # OPERATORS
    # =====================================================
    # Apply operators, constraints, expressions to the hierarchy.\n
    # In order to keep the code clean and easier to debug,
    # we shouldn't create any new object in this method.
    # @param self
    def addOperators(self) -> None:
        pass

    # =====================================================
    # CONNECTOR
    # =====================================================
    # Set the relation beetween object from guide to rig.\n
    # @param self
    def setRelation(self) -> None:
        self.relatives["root"] = self.root
        self.relatives["eff0"] = self.root
        self.relatives["tan2"] = self.head_ctl

        self.relatives["head"] = self.head_ctl
        self.relatives["eff1"] = self.head_ctl

        self.jointRelatives["root"] = 0
        self.jointRelatives["eff0"] = 0
        self.jointRelatives["tan2"] = len(self.jnt_pos) - 1
        self.jointRelatives["neck"] = len(self.jnt_pos) - 1
        self.jointRelatives["head"] = len(self.jnt_pos) - 1
        self.jointRelatives["eff1"] = len(self.jnt_pos) - 1

        for i, ctl in enumerate(self.neck_ctls):
            self.relatives["neck{}".format(i)] = ctl
            self.relatives["%s_loc" % i] = ctl
            self.controlRelatives["%s_loc" % i] = ctl

            self.jointRelatives["%s_loc" % (i)] = (i + 2)
            self.aliasRelatives["%s_ctl" % (i)] = (i + 2)

    def connect_standard(self) -> None:

        self.parent.addChild(self.root)
        self.connect_with_nodespaghetti()

    def connect_spaghetti_head_position(self, i: int, next_cns: object) -> None:

        npo = self.neck_npos[i]
        cns = self.neck_cnss[i]
        ctl = self.neck_ctls[i]
        ref = self.neck_refs[i]

        # Neck position
        mult = pm.createNode("multMatrix")
        pm.connectAttr("{}.matrix".format(ref), "{}.matrixIn[0]".format(mult))
        pm.connectAttr("{}.matrix".format(ctl), "{}.matrixIn[1]".format(mult))
        pm.setAttr("{}.matrixIn[2]".format(mult), *cmds.getAttr("{}.matrix".format(npo)), type="matrix")
        pm.setAttr("{}.matrixIn[3]".format(mult), *cmds.getAttr("{}.matrix".format(npo)), type="matrix")

        decomp = pm.createNode("decomposeMatrix")
        pm.connectAttr("{}.matrixSum".format(mult), "{}.inputMatrix".format(decomp))
        # pm.connectAttr("{}.outputTranslate".format(decomp), "{}.translate".format(self.head_cns))

        cond = pm.createNode("condition")
        pm.connectAttr(str(self.neckref_att), "{}.firstTerm".format(cond))
        pm.setAttr("{}.secondTerm".format(cond), 0)
        pm.setAttr("{}.operation".format(cond), 0)
        pm.connectAttr("{}.outputTranslate".format(decomp), "{}.colorIfTrue".format(cond))
        pm.connectAttr("{}.outColor".format(cond), "{}.translate".format(next_cns))

        return cond

    def connect_spaghetti_head_rotation(self, i: int, head_ref_cond: object, head_space_mult: object) -> None:

        # npo = self.neck_npos[i]
        # ctl = self.neck_ctls[i]
        # ref = self.neck_refs[i]
        cns = self.neck_cnss[i]

        # Neck Rotation
        cond = pm.createNode("condition")
        pm.connectAttr(str(self.neckref_att), "{}.firstTerm".format(cond))
        pm.setAttr("{}.secondTerm".format(cond), 0)
        pm.setAttr("{}.operation".format(cond), 0)
        pm.setAttr("{}.colorIfTrueR".format(cond), 0)
        pm.setAttr("{}.colorIfTrueG".format(cond), 0)
        pm.setAttr("{}.colorIfTrueB".format(cond), 0)

        toQuat = pm.createNode("eulerToQuat")
        decomp = pm.createNode("decomposeMatrix")
        pm.connectAttr("{}.matrixSum".format(head_space_mult), "{}.inputMatrix".format(decomp))
        pm.connectAttr("{}.outputRotate".format(decomp), "{}.inputRotate".format(toQuat))

        mult = pm.createNode("multDoubleLinear")
        slerp = pm.createNode("quatSlerp")
        pm.connectAttr(str(self.neckrate_att), "{}.input1".format(mult))
        ratio = float(i) / float(max(self.division - 2, 1))
        pm.setAttr("{}.input2".format(mult), 1.0 - ratio)

        pm.connectAttr("{}.outputQuat".format(toQuat), "{}.input1Quat".format(slerp))
        pm.connectAttr("{}.output".format(mult), "{}.inputT".format(slerp))
        pm.setAttr("{}.input2QuatX".format(slerp), 0.)
        pm.setAttr("{}.input2QuatY".format(slerp), 0.)
        pm.setAttr("{}.input2QuatZ".format(slerp), 0.)
        pm.setAttr("{}.input2QuatW".format(slerp), 1.)

        toEul = pm.createNode("quatToEuler")
        pm.connectAttr("{}.outputQuat".format(slerp), "{}.inputQuat".format(toEul))
        pm.connectAttr("{}.outputRotateX".format(toEul), "{}.colorIfFalseR".format(cond))
        pm.connectAttr("{}.outputRotateY".format(toEul), "{}.colorIfFalseG".format(cond))
        pm.connectAttr("{}.outputRotateZ".format(toEul), "{}.colorIfFalseB".format(cond))

        pm.connectAttr("{}.outColor".format(cond), "{}.rotate".format(cns))

        return cond, slerp

    def connect_spaghetti_head_position2(self, i: int, prev_mult: object, slerp: object, pos_cond: object) -> None:

        npo = self.neck_npos[i]
        cns = self.neck_cnss[i]
        ctl = self.neck_ctls[i]
        ref = self.neck_refs[i]

        comp = pm.createNode("composeMatrix")
        pm.connectAttr("{}.outputQuat".format(slerp), "{}.inputQuat".format(comp))
        pm.setAttr("{}.useEulerRotation".format(comp), False)
        pm.setAttr("{}.inputTranslateX".format(comp), cmds.getAttr("{}.translateX".format(cns)))
        pm.setAttr("{}.inputTranslateY".format(comp), cmds.getAttr("{}.translateY".format(cns)))
        pm.setAttr("{}.inputTranslateZ".format(comp), cmds.getAttr("{}.translateZ".format(cns)))
        inv = pm.createNode("inverseMatrix")
        pm.connectAttr("{}.outputMatrix".format(comp), "{}.inputMatrix".format(inv))

        mult = pm.createNode("multMatrix")

        if i > 0:
            pm.connectAttr("{}.inverseMatrix".format(cns), "{}.matrixIn[0]".format(mult))
            pm.connectAttr("{}.inverseMatrix".format(npo), "{}.matrixIn[2]".format(mult))
            pm.connectAttr("{}.inverseMatrix".format(ctl), "{}.matrixIn[3]".format(mult))
            pm.connectAttr("{}.inverseMatrix".format(ref), "{}.matrixIn[4]".format(mult))

        else:
            pm.connectAttr("{}.outputMatrix".format(inv), "{}.matrixIn[0]".format(mult))
            pm.connectAttr("{}.inverseMatrix".format(npo), "{}.matrixIn[1]".format(mult))
            pm.connectAttr("{}.inverseMatrix".format(ctl), "{}.matrixIn[2]".format(mult))
            pm.connectAttr("{}.inverseMatrix".format(ref), "{}.matrixIn[3]".format(mult))

        inv = pm.createNode("inverseMatrix")
        pm.connectAttr("{}.matrixSum".format(mult), "{}.inputMatrix".format(inv))
        decomp = pm.createNode("decomposeMatrix")
        pm.connectAttr("{}.outputMatrix".format(inv), "{}.inputMatrix".format(decomp))

        pm.connectAttr("{}.outputTranslate".format(decomp), "{}.colorIfFalse".format(pos_cond))

        return mult

    def connect_with_nodespaghetti(self) -> None:

        neck_ref_cond_positions = []
        for i in range(self.division - 1):
            cns = self.neck_cnss[i]
            if i < (self.division - 2):
                next_cns = self.neck_cnss[i + 1]
            else:
                next_cns = self.head_cns

            cond = self.connect_spaghetti_head_position(i, next_cns)
            neck_ref_cond_positions.append(cond)

        # Head ref switch
        head_ref_cond = pm.createNode("condition")
        pm.connectAttr(str(self.headref_att), "{}.firstTerm".format(head_ref_cond))
        pm.setAttr("{}.secondTerm".format(head_ref_cond), 0)
        pm.setAttr("{}.operation".format(head_ref_cond), 0)
        pm.setAttr("{}.colorIfTrueR".format(head_ref_cond), 0)
        pm.setAttr("{}.colorIfTrueG".format(head_ref_cond), 0)
        pm.setAttr("{}.colorIfTrueB".format(head_ref_cond), 0)
        pm.setAttr("{}.colorIfFalseR".format(head_ref_cond), 0)
        pm.setAttr("{}.colorIfFalseG".format(head_ref_cond), 0)
        pm.setAttr("{}.colorIfFalseB".format(head_ref_cond), 0)

        pm.connectAttr("{}.outColorR".format(head_ref_cond), "{}.rotateX".format(self.head_cns))
        pm.connectAttr("{}.outColorG".format(head_ref_cond), "{}.rotateY".format(self.head_cns))
        pm.connectAttr("{}.outColorB".format(head_ref_cond), "{}.rotateZ".format(self.head_cns))

        neck_ref_cond_rotations = []
        neck_slerps = []

        head_ctl_space_mult = pm.createNode("multMatrix")
        pm.connectAttr("{}.inverseMatrix".format(self.head_npo), "{}.matrixIn[0]".format(head_ctl_space_mult))
        pm.connectAttr("{}.matrix".format(self.head_ctl), "{}.matrixIn[1]".format(head_ctl_space_mult))
        pm.connectAttr("{}.matrix".format(self.head_npo), "{}.matrixIn[2]".format(head_ctl_space_mult))

        head_ref_comp = pm.createNode("composeMatrix")
        pm.connectAttr("{}.outColorR".format(head_ref_cond), "{}.inputRotateX".format(head_ref_comp))
        pm.connectAttr("{}.outColorG".format(head_ref_cond), "{}.inputRotateY".format(head_ref_comp))
        pm.connectAttr("{}.outColorB".format(head_ref_cond), "{}.inputRotateZ".format(head_ref_comp))

        head_space_mult = pm.createNode("multMatrix")
        pm.connectAttr("{}.outputMatrix".format(head_ref_comp), "{}.matrixIn[0]".format(head_space_mult))
        pm.connectAttr("{}.matrixSum".format(head_ctl_space_mult), "{}.matrixIn[1]".format(head_space_mult))

        for i in range(self.division - 1):
            cond, slerp = self.connect_spaghetti_head_rotation(i, head_ref_cond, head_space_mult)
            neck_ref_cond_rotations.append(cond)
            neck_slerps.append(slerp)

        # Head pos2
        mult = None
        for i in range(self.division - 1):

            slerp = neck_slerps[i]
            pos_cond = neck_ref_cond_positions[i]

            mult = self.connect_spaghetti_head_position2(i, mult, slerp, pos_cond)

        if self.settings["headrefarray"]:

            ref_names = self.settings["headrefarray"].split(",")
            for h, ref_name in enumerate(ref_names):

                _head_ref_cond = pm.createNode("condition")
                pm.connectAttr("{}.outColorR".format(_head_ref_cond), "{}.colorIfFalseR".format(head_ref_cond))
                pm.connectAttr("{}.outColorG".format(_head_ref_cond), "{}.colorIfFalseG".format(head_ref_cond))
                pm.connectAttr("{}.outColorB".format(_head_ref_cond), "{}.colorIfFalseB".format(head_ref_cond))
                head_ref_cond = _head_ref_cond

                pm.connectAttr(str(self.headref_att), "{}.firstTerm".format(_head_ref_cond))
                pm.setAttr("{}.secondTerm".format(_head_ref_cond), h + 1)
                pm.setAttr("{}.operation".format(_head_ref_cond), 0)

                src = self.rig.findRelative(ref_name)

                down, _, up = ymt_util.findPathAtoB(src, self.root)
                mult = pm.createNode("multMatrix")

                for i, d in enumerate(down):
                    pm.connectAttr("{}.matrix".format(d), "{}.matrixIn[{}]".format(mult, i))

                for j, u in enumerate(up):
                    pm.connectAttr("{}.inverseMatrix".format(u), "{}.matrixIn[{}]".format(mult, i + j + 1))

                decomp = pm.createNode("decomposeMatrix")
                pm.connectAttr("{}.matrixSum".format(mult), "{}.inputMatrix".format(decomp))
                pm.connectAttr("{}.outputRotateX".format(decomp), "{}.colorIfTrueR".format(head_ref_cond))
                pm.connectAttr("{}.outputRotateY".format(decomp), "{}.colorIfTrueG".format(head_ref_cond))
                pm.connectAttr("{}.outputRotateZ".format(decomp), "{}.colorIfTrueB".format(head_ref_cond))
