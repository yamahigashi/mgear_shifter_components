"""Bird/dragon wing component.

This component solves a three-section wing with two IK layers:

* A: root/elbow/wrist 2-bone IK
* B: wrist/hand 1-bone look-at IK

The implementation follows the more explicit chain separation used by
``ymt_leg_4jnt_01``: setup solve chains, FK/IK result chains, final blended
chain, and deformation anchors are kept separate so each layer remains easy to
inspect in Maya.
"""

import math

try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm
try:
    from mgear.pymaya import datatypes
except ImportError:
    from pymel.core import datatypes

from maya.api import OpenMaya as om2

from mgear.shifter import component
from mgear.core import applyop, attribute, icon, node, primitive, transform, vector

import ymt_shifter_utility as yu


class Component(component.Main):
    """Shifter component class."""

    def _get_division_percents(self):
        percents = []
        for span_index, div_count in enumerate(
            [self.settings["div0"], self.settings["div1"], self.settings["div2"]]
        ):
            span_start = span_index / 3.0
            for div_index in range(div_count):
                perc = span_start + ((div_index + 1.0) / (div_count + 1.0)) / 3.0
                percents.append(max(0.001, min(0.999, perc)))
        return percents

    def _sample_profile_values(self, profile_name, percents):
        profile_values = self.guide.paramDefs[profile_name].value
        if profile_values:
            return self._interpolate_profile_values(profile_values, percents)

        fcv_node = self.settings[profile_name]
        values = []
        for perc in percents:
            pm.setAttr(fcv_node + ".input", perc)
            values.append(pm.getAttr(fcv_node + ".output"))
        return values

    def _interpolate_profile_values(self, profile_values, percents):
        if not profile_values:
            return [0] * len(percents)

        values = [float(value) for value in profile_values]
        if len(values) == 1:
            return [values[0]] * len(percents)

        max_index = len(values) - 1
        interpolated = []
        for perc in percents:
            position = max(0.0, min(1.0, perc)) * max_index
            low_index = int(math.floor(position))
            high_index = min(low_index + 1, max_index)
            blend = position - low_index
            value = values[low_index] + ((values[high_index] - values[low_index]) * blend)
            interpolated.append(value)
        return interpolated

    def _add_match_ref_from(self, ctl, source, parent, name, cnx=True):
        match = primitive.addTransform(parent, self.getName(name), transform.getTransform(source))
        if cnx:
            ctl.addAttr("match_ref", at="message", multi=False)
            pm.connectAttr(match.message, ctl.match_ref)
        return match

    def addObjects(self):
        """Add all objects needed to create the component."""

        self.setup = primitive.addTransformFromPos(self.setupWS, self.getName("WS"))
        attribute.lockAttribute(self.setup)

        self.WIP = self.options["mode"]
        root_matrix = om2.MMatrix(self.guide.tra["root"])
        self.root_normal = datatypes.Vector(root_matrix[1], root_matrix[5], root_matrix[9]).normal()
        self.normal = self.guide.blades["blade"].z * -1
        self.binormal = self.guide.blades["blade"].x

        self.length0 = vector.getDistance(self.guide.apos[0], self.guide.apos[1])
        self.length1 = vector.getDistance(self.guide.apos[1], self.guide.apos[2])
        self.length2 = vector.getDistance(self.guide.apos[2], self.guide.apos[3])

        self.chain2bones = yu.add3DChain(
            self.setup,
            self.getName("chain2bones%s_jnt"),
            self.guide.apos[0:3],
            self.normal,
            False,
            self.WIP,
        )
        self.handChain = yu.add3DChain(
            self.setup,
            self.getName("handChain%s_jnt"),
            self.guide.apos[2:4],
            self.normal,
            False,
            self.WIP,
        )
        self.wingBones = yu.add3DChain(
            self.root,
            self.getName("wingBones%s_jnt"),
            self.guide.apos[0:4],
            self.normal,
            False,
            self.WIP,
        )
        self.wingBonesFK = yu.add3DChain(
            self.root,
            self.getName("wingFK%s_jnt"),
            self.guide.apos[0:4],
            self.normal,
            False,
            self.WIP,
        )
        self.wingBonesIK = yu.add3DChain(
            self.root,
            self.getName("wingIK%s_jnt"),
            self.guide.apos[0:4],
            self.normal,
            False,
            self.WIP,
        )
        self.upvRefChain = yu.add3DChain(
            self.root,
            self.getName("wingUpvRef%s_jnt"),
            [self.guide.apos[0], self.guide.apos[2]],
            self.normal,
            False,
            self.WIP,
        )

        # Base control
        t = transform.getTransformFromPos(self.guide.apos[0])
        self.root_npo = primitive.addTransform(self.root, self.getName("root_npo"), t)
        self.root_ctl = self.addCtl(
            self.root_npo,
            "root_ctl",
            t,
            self.color_fk,
            "circle",
            w=self.size * 0.18,
            tp=self.parentCtlTag,
        )
        attribute.lockAttribute(self.root_ctl, ["sx", "sy", "sz", "v"])

        # FK controls
        self.fk_ctl = []
        parent = self.root_ctl
        tag_parent = self.root_ctl
        for index, (start, end, length) in enumerate(
            [
                (self.guide.apos[0], self.guide.apos[1], self.length0),
                (self.guide.apos[1], self.guide.apos[2], self.length1),
                (self.guide.apos[2], self.guide.apos[3], self.length2),
            ]
        ):
            t = transform.getTransformLookingAt(start, end, self.normal, "xz", self.negate)
            npo = primitive.addTransform(parent, self.getName("fk%s_npo" % index), t)
            ctl = self.addCtl(
                npo,
                "fk%s_ctl" % index,
                t,
                self.color_fk,
                "cube",
                w=length,
                h=self.size * 0.1,
                d=self.size * 0.1,
                po=datatypes.Vector(0.5 * length * self.n_factor, 0, 0),
                tp=tag_parent,
            )
            attribute.setKeyableAttributes(ctl)
            attribute.setInvertMirror(ctl, ["tx", "ty", "tz"])
            setattr(self, "fk%s_npo" % index, npo)
            setattr(self, "fk%s_ctl" % index, ctl)
            self.fk_ctl.append(ctl)
            parent = ctl
            tag_parent = ctl

        # Corrective controls at elbow and wrist.
        self.elbow_lvl = primitive.addTransform(
            self.root, self.getName("elbow_lvl"), transform.getTransform(self.wingBones[1])
        )
        self.elbow_ctl = self.addCtl(
            self.elbow_lvl,
            "elbow_ctl",
            transform.getTransform(self.wingBones[1]),
            self.color_ik,
            "sphere",
            w=self.size * 0.18,
            tp=self.root_ctl,
        )
        attribute.setInvertMirror(self.elbow_ctl, ["tx", "ty", "tz"])
        attribute.lockAttribute(self.elbow_ctl, ["sx", "sy", "sz", "v"])

        self.wrist_lvl = primitive.addTransform(
            self.root, self.getName("wrist_lvl"), transform.getTransform(self.wingBones[2])
        )
        self.wrist_ctl = self.addCtl(
            self.wrist_lvl,
            "wrist_ctl",
            transform.getTransform(self.wingBones[2]),
            self.color_ik,
            "sphere",
            w=self.size * 0.18,
            tp=self.elbow_ctl,
        )
        attribute.setInvertMirror(self.wrist_ctl, ["tx", "ty", "tz"])
        attribute.lockAttribute(self.wrist_ctl, ["sx", "sy", "sz", "v"])

        # IK A: upper/lower wing 2-bone IK.
        t = transform.getTransformFromPos(self.guide.pos["wrist"])
        self.ik_cns = primitive.addTransform(self.root_ctl, self.getName("ik_cns"), t)
        self.ik_ctl = self.addCtl(
            self.ik_cns,
            "ik_ctl",
            t,
            self.color_ik,
            "cube",
            w=self.size * 0.22,
            h=self.size * 0.22,
            d=self.size * 0.22,
            tp=self.root_ctl,
        )
        attribute.setKeyableAttributes(self.ik_ctl)
        attribute.setRotOrder(self.ik_ctl, "XZY")
        attribute.setInvertMirror(self.ik_ctl, ["tx", "ry", "rz"])
        attribute.lockAttribute(self.ik_ctl, ["sx", "sy", "sz", "v"])

        self.ik_ref = primitive.addTransform(self.ik_ctl, self.getName("ik_ref"), transform.getTransform(self.ik_ctl))

        v = self.guide.pos["upv"]
        upv_source_normal = vector.getPlaneNormal(self.guide.apos[0], self.guide.apos[2], v)
        upv_source_basis = transform.getTransformLookingAt(
            self.guide.apos[0], self.guide.apos[2], upv_source_normal, "xz", False
        )
        blade_target_basis = transform.getTransformLookingAt(
            self.guide.apos[0], self.guide.apos[2], self.normal, "xz", False
        )
        upv_t = transform.setMatrixPosition(upv_source_basis, v)
        self.upv_lvl = primitive.addTransform(self.root, self.getName("upv_lvl"), upv_t)
        self.upv_cns = primitive.addTransform(self.upv_lvl, self.getName("upv_cns"), upv_t)
        self.upv_ctl = self.addCtl(
            self.upv_cns,
            "upv_ctl",
            transform.getTransform(self.upv_cns),
            self.color_ik,
            "diamond",
            w=self.size * 0.12,
            tp=self.ik_ctl,
        )
        attribute.setInvertMirror(self.upv_ctl, ["tx"])
        attribute.setKeyableAttributes(self.upv_ctl, ["tx", "ty", "tz"])

        blade_pole_dir = self.guide.apos[2] - self.guide.apos[0]
        blade_pole_dir = blade_pole_dir ^ self.normal
        blade_pole_dir.normalize()
        blade_pole_pos = self.guide.apos[1] + (blade_pole_dir * self.size)
        blade_pole_t = transform.setMatrixPosition(blade_target_basis, blade_pole_pos)
        self.effective_upv_npo = primitive.addTransform(
            self.upv_cns, self.getName("effectiveUpv_npo"), blade_pole_t
        )
        self.effective_upv_ref = primitive.addTransform(
            self.effective_upv_npo,
            self.getName("effectiveUpv_ref"),
            transform.getTransform(self.effective_upv_npo),
        )
        self.effective_upv_npo.attr("visibility").set(False)

        # Soft IK objects for IK A: root/elbow/wrist.
        t = transform.getTransformLookingAt(self.guide.pos["root"], self.guide.pos["wrist"], self.normal, "zx", False)
        self.aim_tra = primitive.addTransform(self.root_ctl, self.getName("aimSoftIK"), t)

        t = transform.getTransformFromPos(self.guide.pos["wrist"])
        self.wristSoftIK = primitive.addTransform(self.aim_tra, self.getName("wristSoftIK"), t)
        self.softblendLoc = primitive.addTransform(self.root, self.getName("softblendLoc"), t)

        # IK B: wrist/hand look-at target.
        t = transform.getTransformLookingAt(self.guide.apos[2], self.guide.apos[3], self.root_normal, "zx", False)
        t = transform.setMatrixPosition(t, self.guide.pos["eff"])
        self.hand_ik_cns = primitive.addTransform(self.softblendLoc, self.getName("hand_ik_cns"), t)
        self.hand_ik_ctl = self.addCtl(
            self.hand_ik_cns,
            "hand_ik_ctl",
            t,
            self.color_ik,
            "cube",
            w=self.size * 0.20,
            h=self.size * 0.20,
            d=max(self.length2, self.size * 0.1) * 0.18,
            tp=self.ik_ctl,
        )
        attribute.setKeyableAttributes(self.hand_ik_ctl)
        attribute.setRotOrder(self.hand_ik_ctl, "XZY")
        attribute.setInvertMirror(self.hand_ik_ctl, ["tx", "ry", "rz"])
        attribute.lockAttribute(self.hand_ik_ctl, ["sx", "sy", "sz", "v"])

        self.hand_ik_ref = primitive.addTransform(
            self.hand_ik_ctl, self.getName("hand_ik_ref"), transform.getTransform(self.hand_ik_ctl)
        )
        self.hand_roll_ref = primitive.addTransform(
            self.hand_ik_ref, self.getName("hand_roll_ref"), transform.getTransform(self.hand_ik_ctl)
        )
        self.fk_ref = primitive.addTransform(
            self.fk_ctl[2], self.getName("fk_ref"), transform.getTransform(self.hand_ik_ctl)
        )

        # Twist references and deformation drivers.
        self.rollRef = primitive.add2DChain(
            self.root, self.getName("rollChain"), self.guide.apos[:2], self.normal, False, self.WIP
        )
        self.tws0_loc = primitive.addTransform(
            self.rollRef[0], self.getName("tws0_loc"), transform.getTransform(self.wingBones[0])
        )
        self.tws0_rot = primitive.addTransform(
            self.tws0_loc, self.getName("tws0_rot"), transform.getTransform(self.wingBones[0])
        )
        self.tws0_rot.setAttr("sx", 0.001)
        self.tws1_loc = primitive.addTransform(
            self.wingBones[1], self.getName("tws1_loc"), transform.getTransform(self.wingBones[1])
        )
        self.tws1_rot = primitive.addTransform(
            self.tws1_loc, self.getName("tws1_rot"), transform.getTransform(self.wingBones[1])
        )
        self.tws1_rot.setAttr("sx", 0.001)
        self.tws2_loc = primitive.addTransform(
            self.wingBones[2], self.getName("tws2_loc"), transform.getTransform(self.wingBones[2])
        )
        self.tws2_rot = primitive.addTransform(
            self.tws2_loc, self.getName("tws2_rot"), transform.getTransform(self.wingBones[2])
        )
        self.tws2_rot.setAttr("sx", 0.001)
        self.tws3_loc = primitive.addTransform(
            self.wingBones[3], self.getName("tws3_loc"), transform.getTransform(self.wingBones[3])
        )
        self.tws3_rot = primitive.addTransform(
            self.tws3_loc, self.getName("tws3_rot"), transform.getTransform(self.wingBones[3])
        )
        self.tws3_rot.setAttr("sx", 0.001)

        self.divisions = self.settings["div0"] + self.settings["div1"] + self.settings["div2"]
        self.joint_indices = {}
        self.deform_anchor_refs = {}
        self.deform_anchor_drivers = {}
        for name, wing_bone, correction_ctl in [
            ("root", self.wingBones[0], None),
            ("elbow", self.wingBones[1], self.elbow_ctl),
            ("wrist", self.wingBones[2], self.wrist_ctl),
            ("eff", self.wingBones[3], None),
        ]:
            ref = primitive.addTransform(
                self.root_ctl,
                self.getName("%s_jnt_ref" % name),
                transform.getTransform(wing_bone),
            )
            self.deform_anchor_refs[name] = ref
            pm.parentConstraint(wing_bone, ref, mo=False)
            driver = ref
            if correction_ctl:
                driver = primitive.addTransform(
                    self.root_ctl,
                    self.getName("%s_jnt_corr" % name),
                    transform.getTransform(ref),
                )
                node.createMultMatrixNode(
                    correction_ctl.attr("worldMatrix"),
                    self.root_ctl.attr("worldInverseMatrix"),
                    driver,
                    "rt",
                )
            self.deform_anchor_drivers[name] = driver

        self.div_cns = []
        div_index = 0
        joint_index = 0
        for anchor_name, div_count in [
            ("root", self.settings["div0"]),
            ("elbow", self.settings["div1"]),
            ("wrist", self.settings["div2"]),
        ]:
            self.joint_indices[anchor_name] = joint_index
            self.jnt_pos.append([self.deform_anchor_drivers[anchor_name], anchor_name])
            joint_index += 1
            for _ in range(div_count):
                div_cns = primitive.addTransform(self.root_ctl, self.getName("div%s_loc" % div_index))
                self.div_cns.append(div_cns)
                self.jnt_pos.append([div_cns, div_index])
                div_index += 1
                joint_index += 1

        self.joint_indices["eff"] = joint_index
        self.jnt_pos.append([self.deform_anchor_drivers["eff"], "eff"])
        joint_index += 1
        self.end_ref = primitive.addTransform(
            self.tws3_rot, self.getName("end_ref"), transform.getTransform(self.wingBones[3])
        )
        self.jnt_pos.append([self.end_ref, "end"])
        self.joint_indices["end"] = joint_index

        self.match_fk = []
        for index, fk_ctl in enumerate(self.fk_ctl):
            match_off = self._add_match_ref_from(
                fk_ctl, self.wingBones[index], self.root, "matchFk%s_npo" % index, False
            )
            match_ref = self._add_match_ref_from(fk_ctl, self.wingBones[index], match_off, "fk%s_mth" % index)
            setattr(self, "match_fk%s_off" % index, match_off)
            setattr(self, "match_fk%s" % index, match_ref)
            self.match_fk.append(match_ref)

        self.match_ik = self._add_match_ref_from(self.ik_ctl, self.wingBones[2], self.root, "ik_mth")
        self.match_hand_ik = self._add_match_ref_from(
            self.hand_ik_ctl, self.wingBones[3], self.root, "handIk_mth"
        )
        self.match_ikUpv = self.add_match_ref(self.upv_ctl, self.fk0_ctl, "upv_mth")

        self.line_ref = icon.connection_display_curve(self.getName("visalRef"), [self.upv_ctl, self.elbow_ctl])
        self.hand_line_ref = icon.connection_display_curve(
            self.getName("handVisalRef"), [self.wrist_ctl, self.hand_ik_ctl]
        )

    def addAttributes(self):
        """Create anim and setup attributes."""

        self.blend_att = self.addAnimParam("blend", "Fk/Ik Blend", "double", self.settings["blend"], 0, 1)
        self.volume_att = self.addAnimParam("volume", "Volume", "double", 1, 0, 1)
        self.roll_att = self.addAnimParam("roll", "Roll", "double", 0, -180, 180)
        self.handRoll_att = self.addAnimParam("handRoll", "Hand Roll", "double", 0, -180, 180)
        self.soft_attr = self.addAnimParam("softIKRange", "Soft IK Range", "double", 0.0001, 0.0001, 100)
        self.softSpeed_attr = self.addAnimParam("softIKSpeed", "Soft IK Speed", "double", 2.5, 1.001, 10)
        self.stretch_attr = self.addAnimParam("stretch", "Stretch", "double", 0, 0, 1)
        self.roundnessElbow_att = self.addAnimParam("roundnessElbow", "Roundness Elbow", "double", 0, 0, self.size)
        self.roundnessWrist_att = self.addAnimParam("roundnessWrist", "Roundness Wrist", "double", 0, 0, self.size)
        self.boneALenghtMult_attr = self.addAnimParam("boneALenMult", "Bone A Mult", "double", 1)
        self.boneBLenghtMult_attr = self.addAnimParam("boneBLenMult", "Bone B Mult", "double", 1)
        self.boneCLenghtMult_attr = self.addAnimParam("boneCLenMult", "Bone C Mult", "double", 1)
        self.boneALenght_attr = self.addAnimParam("boneALen", "Bone A Length", "double", self.length0, keyable=False)
        self.boneBLenght_attr = self.addAnimParam("boneBLen", "Bone B Length", "double", self.length1, keyable=False)
        self.boneCLenght_attr = self.addAnimParam("boneCLen", "Bone C Length", "double", self.length2, keyable=False)

        if self.settings["ikrefarray"]:
            ref_names = self.get_valid_alias_list(self.settings["ikrefarray"].split(","))
            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam("ikref", "Ik Ref", 0, ref_names)

        if self.settings["upvrefarray"]:
            ref_names = self.get_valid_alias_list(self.settings["upvrefarray"].split(","))
            ref_names = ["Auto"] + ref_names
            if len(ref_names) > 1:
                self.upvref_att = self.addAnimEnumParam("upvref", "UpV Ref", 0, ref_names)

        if self.validProxyChannels:
            attribute.addProxyAttribute(
                [
                    self.blend_att,
                    self.soft_attr,
                    self.softSpeed_attr,
                    self.stretch_attr,
                    self.roundnessElbow_att,
                    self.roundnessWrist_att,
                ],
                [self.fk0_ctl, self.fk1_ctl, self.fk2_ctl, self.ik_ctl, self.hand_ik_ctl, self.upv_ctl],
            )
            attribute.addProxyAttribute([self.roll_att, self.handRoll_att], [self.ik_ctl, self.hand_ik_ctl, self.upv_ctl])

        self.division_percents = self._get_division_percents()
        self.st_value = self._sample_profile_values("st_profile", self.division_percents)
        self.sq_value = self._sample_profile_values("sq_profile", self.division_percents)

        self.st_att = []
        self.sq_att = []
        for i in range(self.divisions):
            st_val = self.st_value[i] if i < len(self.st_value) else 0
            sq_val = self.sq_value[i] if i < len(self.sq_value) else 0
            self.st_att.append(self.addSetupParam("stretch_%s" % i, "Stretch %s" % i, "double", st_val, -1, 0))
            self.sq_att.append(self.addSetupParam("squash_%s" % i, "Squash %s" % i, "double", sq_val, 0, 1))

        self.resample_att = self.addSetupParam("resample", "Resample", "bool", True)
        self.absolute_att = self.addSetupParam("absolute", "Absolute", "bool", False)
        self.elbowFlipOffset_att = self.addSetupParam(
            "elbowFlipOffset", "Elbow Flip Offset", "double", self.chain2bones[1].attr("jointOrientZ").get() / 2, -180, 180
        )
        self.wristFlipOffset_att = self.addSetupParam("wristFlipOffset", "Wrist Flip Offset", "double", 0, -180, 180)

    def addOperators(self):
        """Apply operators, constraints, and expressions."""

        soft_cond_node = node.createConditionNode(self.soft_attr, 0.0001, 4, 0.0001, self.soft_attr)
        self.soft_attr_cond = soft_cond_node.outColorR

        if self.settings["ikSolver"]:
            self.ikSolver = "ikRPsolver"
        else:
            pm.mel.eval("ikSpringSolver;")
            self.ikSolver = "ikSpringSolver"

        self.ikHandleUpvRef = primitive.addIkHandle(
            self.root, self.getName("ikHandleWingUpvRef"), self.upvRefChain, "ikSCsolver"
        )
        pm.pointConstraint(self.ik_ctl, self.ikHandleUpvRef)
        pm.parentConstraint(self.upvRefChain[0], self.upv_cns, mo=True)

        pm.parentConstraint(self.wingBones[1], self.elbow_lvl)
        pm.parentConstraint(self.wingBones[2], self.wrist_lvl)

        multJnt1_node = node.createMulNode(self.boneALenght_attr, self.boneALenghtMult_attr)
        multJnt2_node = node.createMulNode(self.boneBLenght_attr, self.boneBLenghtMult_attr)
        multJnt3_node = node.createMulNode(self.boneCLenght_attr, self.boneCLenghtMult_attr)

        self.ikHandle2 = primitive.addIkHandle(
            self.softblendLoc, self.getName("ik2BonesHandle"), self.chain2bones, self.ikSolver, self.effective_upv_ref
        )
        if self.ikSolver == "ikSpringSolver":
            pm.mel.eval("ikSpringSolver;")

        pm.pointConstraint(self.root_ctl, self.chain2bones[0], maintainOffset=True)
        pm.connectAttr(self.upv_ctl.attr("translate"), self.effective_upv_ref.attr("translate"), f=True)
        pm.pointConstraint(self.chain2bones[2], self.handChain[0], maintainOffset=False)

        self.ikHandleHand = primitive.addIkHandle(
            self.root, self.getName("ikHandHandle"), self.handChain, "ikSCsolver"
        )
        pm.pointConstraint(self.hand_ik_ctl, self.ikHandleHand, maintainOffset=False)

        chain_pos = [x.getTranslation(space="world") for x in self.chain2bones]
        same_dir = self.verifyAlignmentAccuracy(chain_pos, self.guide.apos[:3])
        angle = 0 if same_dir else 180
        add_node_twist = node.createAddNode(angle, self.roll_att)
        mul_val = 1 if self.negate else -1
        node.createMulNode(add_node_twist + ".output", mul_val, self.ikHandle2.attr("twist"))

        applyop.aimCns(
            self.aim_tra,
            self.ik_ref,
            axis="zx",
            wupType=4,
            wupVector=[1, 0, 0],
            wupObject=self.root_ctl,
            maintainOffset=False,
        )

        plus_total_length_node = node.createPlusMinusAverage1D(
            [multJnt1_node.attr("outputX"), multJnt2_node.attr("outputX")]
        )
        subtract1_node = node.createPlusMinusAverage1D(
            [plus_total_length_node.attr("output1D"), self.soft_attr_cond], 2
        )
        distance1_node = node.createDistNode(self.ik_ref, self.aim_tra)
        div1_node = node.createDivNode(1.0, self.rig.global_ctl + ".sx")
        mult1_node = node.createMulNode(distance1_node + ".distance", div1_node + ".outputX")
        subtract2_node = node.createPlusMinusAverage1D([mult1_node.attr("outputX"), subtract1_node.attr("output1D")], 2)
        div2_node = node.createDivNode(subtract2_node + ".output1D", self.soft_attr_cond)
        mult2_node = node.createMulNode(-1, div2_node + ".outputX")
        power_node = node.createPowNode(self.softSpeed_attr, mult2_node + ".outputX")
        mult3_node = node.createMulNode(self.soft_attr_cond, power_node + ".outputX")
        subtract3_node = node.createPlusMinusAverage1D(
            [plus_total_length_node.attr("output1D"), mult3_node.attr("outputX")], 2
        )
        cond1_node = node.createConditionNode(
            self.soft_attr_cond, 0, 2, subtract3_node + ".output1D", plus_total_length_node + ".output1D"
        )
        cond2_node = node.createConditionNode(
            mult1_node + ".outputX",
            subtract1_node + ".output1D",
            2,
            cond1_node + ".outColorR",
            mult1_node + ".outputX",
        )
        pm.connectAttr(cond2_node + ".outColorR", self.wristSoftIK + ".tz")

        soft_blend_cns = pm.pointConstraint(self.wristSoftIK, self.ik_ref, self.softblendLoc)
        node.createReverseNode(self.stretch_attr, soft_blend_cns + ".target[0].targetWeight")
        pm.connectAttr(self.stretch_attr, soft_blend_cns + ".target[1].targetWeight", f=True)

        distance2_node = node.createDistNode(self.softblendLoc, self.wristSoftIK)
        mult4_node = node.createMulNode(distance2_node + ".distance", div1_node + ".outputX")
        for index, mul_node in enumerate([multJnt1_node, multJnt2_node]):
            div3_node = node.createDivNode(mul_node + ".outputX", plus_total_length_node + ".output1D")
            mult5_node = node.createMulNode(mult4_node + ".outputX", div3_node + ".outputX")
            mult6_node = node.createMulNode(self.stretch_attr, mult5_node + ".outputX")
            length_node = node.createPlusMinusAverage1D([mul_node.attr("outputX"), mult6_node.attr("outputX")], 1)
            pm.connectAttr(length_node + ".output1D", self.chain2bones[index + 1] + ".tx")

        pm.connectAttr(multJnt3_node + ".outputX", self.handChain[1] + ".tx")

        # FK result chain.
        for i, ctl in enumerate(self.fk_ctl):
            pm.parentConstraint(ctl, self.wingBonesFK[i], mo=True)
        pm.orientConstraint(self.fk_ref, self.wingBonesFK[-1], mo=True)

        # IK result chain. A solves root/elbow/wrist. B solves wrist/hand.
        for i, src in enumerate([self.chain2bones[0], self.chain2bones[1]]):
            pm.parentConstraint(src, self.wingBonesIK[i], mo=True)
        pm.parentConstraint(self.handChain[0], self.wingBonesIK[2], mo=True)
        pm.connectAttr(multJnt3_node + ".outputX", self.wingBonesIK[3] + ".tx")
        pm.connectAttr(self.handRoll_att, self.hand_roll_ref.attr("rx"))
        pm.orientConstraint(self.hand_roll_ref, self.wingBonesIK[-1], mo=True)

        for i, wing_bone in enumerate(self.wingBones):
            node.createPairBlend(self.wingBonesFK[i], self.wingBonesIK[i], self.blend_att, 1, wing_bone)

        self.ikhRollRef, self.tmpCrv = applyop.splineIK(
            self.getName("wingRollRef"), self.rollRef, parent=self.root, cParent=self.wingBones[0]
        )

        init_round = 0.001
        add_node = node.createAddNode(self.roundnessElbow_att, init_round)
        pm.connectAttr(add_node + ".output", self.tws1_rot + ".sx")
        pm.connectAttr(self.elbow_ctl + ".translate", self.tws1_loc + ".translate")
        pm.connectAttr(self.elbow_ctl + ".rx", self.tws1_loc + ".rx")
        pm.connectAttr(self.elbow_ctl + ".ry", self.tws1_loc + ".ry")

        add_node = node.createAddNode(self.roundnessWrist_att, init_round)
        pm.connectAttr(add_node + ".output", self.tws2_rot + ".sx")
        pm.connectAttr(self.wrist_ctl + ".translate", self.tws2_loc + ".translate")
        pm.connectAttr(self.wrist_ctl + ".rx", self.tws2_loc + ".rx")
        pm.connectAttr(self.wrist_ctl + ".ry", self.tws2_loc + ".ry")

        distA_node = node.createDistNode(self.tws0_loc, self.tws1_loc)
        distB_node = node.createDistNode(self.tws1_loc, self.tws2_loc)
        distC_node = node.createDistNode(self.tws2_loc, self.tws3_loc)
        add_node = node.createAddNode(distA_node + ".distance", distB_node + ".distance")
        add_node2 = node.createAddNode(distC_node + ".distance", add_node + ".output")
        div_node = node.createDivNode(add_node2 + ".output", self.root_ctl.attr("sx"))
        dm_node = node.createDecomposeMatrixNode(self.root.attr("worldMatrix"))
        div_node2 = node.createDivNode(div_node + ".outputX", dm_node + ".outputScaleX")
        self.volDriver_att = div_node2 + ".outputX"

        pm.connectAttr(self.elbowFlipOffset_att, self.tws1_loc + ".rz")
        pm.connectAttr(self.wristFlipOffset_att, self.tws2_loc + ".rz")

        cts = [self.tws0_rot, self.tws1_rot, self.tws2_rot, self.tws3_rot]
        for i, div_cns in enumerate(self.div_cns):
            o_node = applyop.gear_rollsplinekine_op(div_cns, cts, self.division_percents[i], 45)
            pm.connectAttr(self.resample_att, o_node + ".resample")
            pm.connectAttr(self.absolute_att, o_node + ".absolute")

            o_node = applyop.gear_squashstretch2_op(div_cns, None, pm.getAttr(self.volDriver_att), "x")
            pm.connectAttr(self.volume_att, o_node + ".blend")
            pm.connectAttr(self.volDriver_att, o_node + ".driver")
            pm.connectAttr(self.st_att[i], o_node + ".stretch")
            pm.connectAttr(self.sq_att[i], o_node + ".squash")

        fkvis_node = node.createReverseNode(self.blend_att)
        for ctrl in self.fk_ctl:
            for shp in ctrl.getShapes():
                pm.connectAttr(fkvis_node + ".outputX", shp.attr("visibility"))
        for ctrl in [self.ik_ctl, self.hand_ik_ctl, self.upv_ctl, self.line_ref, self.hand_line_ref]:
            for shp in ctrl.getShapes():
                pm.connectAttr(self.blend_att, shp.attr("visibility"))

        pm.connectAttr(self.rig.global_ctl + ".scale", self.setup + ".scale")

        for wing_bone, match_off in zip(
            self.wingBones,
            [self.match_fk0_off, self.match_fk1_off, self.match_fk2_off],
        ):
            pm.parentConstraint(wing_bone, match_off, mo=False)
        pm.parentConstraint(self.wingBones[2], self.match_ik, mo=True)
        pm.parentConstraint(self.wingBones[3], self.match_hand_ik, mo=True)

    def verifyAlignmentAccuracy(self, jnts, guides, degree=10.0):
        if len(jnts) != len(guides):
            raise ValueError("jnts and guides must have the same number of positions.")
        if len(jnts) < 2:
            raise ValueError("At least 2 positions are required.")
        if degree < 0:
            raise ValueError("degree must be non-negative.")

        for j0, j1, g0, g1 in zip(jnts, jnts[1:], guides, guides[1:]):
            joint_vec = om2.MVector(j1[0] - j0[0], j1[1] - j0[1], j1[2] - j0[2])
            guide_vec = om2.MVector(g1[0] - g0[0], g1[1] - g0[1], g1[2] - g0[2])
            if joint_vec.length() == 0 or guide_vec.length() == 0:
                return False
            joint_vec.normalize()
            guide_vec.normalize()
            if math.degrees(joint_vec.angle(guide_vec)) > degree:
                return False
        return True

    def setRelation(self):
        """Set the relation between guide objects and rig objects."""

        self.relatives["root"] = self.deform_anchor_drivers["root"]
        self.relatives["elbow"] = self.deform_anchor_drivers["elbow"]
        self.relatives["wrist"] = self.deform_anchor_drivers["wrist"]
        self.relatives["eff"] = self.deform_anchor_drivers["eff"]

        self.controlRelatives["root"] = self.fk0_ctl
        self.controlRelatives["elbow"] = self.fk1_ctl
        self.controlRelatives["wrist"] = self.ik_ctl
        self.controlRelatives["eff"] = self.hand_ik_ctl

        self.jointRelatives["root"] = self.joint_indices["root"]
        self.jointRelatives["elbow"] = self.joint_indices["elbow"]
        self.jointRelatives["wrist"] = self.joint_indices["wrist"]
        self.jointRelatives["eff"] = self.joint_indices["end"]

        self.aliasRelatives["eff"] = "hand"

    def addConnection(self):
        self.connections["standard"] = self.connect_standard
        self.connections["ymt_shoulder_01"] = self.connect_ymt_shoulder

    def connect_standard(self):
        self.parent.addChild(self.root)
        self.connectRef(self.settings["ikrefarray"], self.ik_cns)
        if self.settings["upvrefarray"]:
            self.connectRef("Auto," + self.settings["upvrefarray"], self.upv_cns, True)

    def connect_ymt_shoulder(self):
        if self.parent_comp is not None and "ymt_shoulder" in str(type(self.parent_comp)):
            self.parent_comp.connect_arm(self)
        self.connect_standard()
