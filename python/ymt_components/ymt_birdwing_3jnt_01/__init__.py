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

import importlib
try:
    pm = importlib.import_module("mgear.pymaya")
except ImportError:
    pm = importlib.import_module("pymel.core")
try:
    datatypes = importlib.import_module("mgear.pymaya.datatypes")
except ImportError:
    datatypes = importlib.import_module("pymel.core.datatypes")

from maya.api import OpenMaya as om2

from mgear.shifter import component
from mgear.core import applyop, attribute, icon, node, primitive, transform, vector

import ymt_shifter_utility as yu
from ymt_shifter_utility.type_protocols import PymelNode


class Component(component.Main):
    """Shifter component class."""

    wrist_control_mode_names = ("IK", "Chain")

    def _connect_enum_condition(
        self, enum_attr: object, enum_index: int, target_weight: object, true_value: int = 1, false_value: int = 0
    ) -> PymelNode:
        cond_node = pm.createNode("condition")
        pm.setAttr(cond_node + ".operation", 0)
        pm.connectAttr(enum_attr, cond_node + ".firstTerm")
        pm.setAttr(cond_node + ".secondTerm", enum_index)
        pm.setAttr(cond_node + ".colorIfTrueR", true_value)
        pm.setAttr(cond_node + ".colorIfFalseR", false_value)
        pm.connectAttr(cond_node + ".outColorR", target_weight, f=True)
        return cond_node

    def _get_division_percents(self) -> list[float]:
        percents = []
        for span_index, div_count in enumerate([self.settings["div0"], self.settings["div1"], self.settings["div2"]]):
            span_start = span_index / 3.0
            for div_index in range(div_count):
                perc = span_start + ((div_index + 1.0) / (div_count + 1.0)) / 3.0
                percents.append(max(0.001, min(0.999, perc)))
        return percents

    def _sample_profile_values(self, profile_name: str, percents: list[float]) -> list[float]:
        profile_values = self.guide.paramDefs[profile_name].value
        if profile_values:
            return self._interpolate_profile_values(profile_values, percents)

        fcv_node = self.settings[profile_name]
        values = []
        for perc in percents:
            pm.setAttr(fcv_node + ".input", perc)
            values.append(pm.getAttr(fcv_node + ".output"))
        return values

    def _interpolate_profile_values(self, profile_values: list[float], percents: list[float]) -> list[float]:
        if not profile_values:
            return [0] * len(percents)

        values = [float(value) for value in profile_values]
        if len(values) == 1:
            return [values[0]] * len(percents)

        max_index = len(values) - 1
        interpolated = []
        for perc in percents:
            position = max(0.0, min(1.0, perc)) * max_index
            low_index = math.floor(position)
            high_index = min(low_index + 1, max_index)
            blend = position - low_index
            value = values[low_index] + ((values[high_index] - values[low_index]) * blend)
            interpolated.append(value)
        return interpolated

    def _add_match_ref_from(
        self, ctl: PymelNode, source: PymelNode, parent: PymelNode, name: str, cnx: bool = True
    ) -> PymelNode:
        match = primitive.addTransform(parent, self.getName(name), transform.getTransform(source))
        if cnx:
            ctl.addAttr("match_ref", at="message", multi=False)
            pm.connectAttr(match.message, ctl.match_ref)
        return match

    def _get_hand_upv_position(self, wrist_pos: datatypes.Vector, pole_dir: datatypes.Vector) -> datatypes.Vector:
        distance = max(self.size * 0.5, self.length2 * 0.25, 0.001)
        return wrist_pos + (pole_dir * distance)

    def _add_hand_upv_refs(self, wrist_t: datatypes.Matrix, pole_dir: datatypes.Vector) -> None:
        self.handUpvRefChain = yu.add3DChain(
            self.root,
            self.getName("handUpvRef%s_jnt"),
            [self.guide.apos[2], self.guide.apos[3]],
            self.normal,
            False,
            self.WIP,
        )

        hand_upv_t = transform.setMatrixPosition(
            transform.getTransform(self.handUpvRefChain[0]),
            self._get_hand_upv_position(self.guide.apos[2], pole_dir),
        )
        self.hand_effective_upv_npo = primitive.addTransform(
            self.handUpvRefChain[0], self.getName("handEffectiveUpv_npo"), hand_upv_t
        )
        self.hand_effective_upv_ref = primitive.addTransform(
            self.hand_effective_upv_npo,
            self.getName("handEffectiveUpv_ref"),
            transform.getTransform(self.hand_effective_upv_npo),
        )
        self.hand_effective_upv_npo.attr("visibility").set(False)

        self.hand_upv_aim_ref = primitive.addTransform(self.root, self.getName("handUpvAim_ref"), wrist_t)
        self.hand_upv_aim_ref.attr("visibility").set(False)

    def addObjects(self) -> None:
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

        self.elbow_mid_jnt = primitive.addJoint(
            self.wingBones[0],
            self.getName("elbowMid_jnt"),
            self.wingBones[1].getMatrix(worldSpace=True),
            self.WIP,
        )
        self.elbow_mid_jnt.attr("radius").set(3)
        self.elbow_mid_jnt.setAttr("jointOrient", 0, 0, 0)

        self.wrist_mid_jnt = primitive.addJoint(
            self.wingBones[1],
            self.getName("wristMid_jnt"),
            self.wingBones[2].getMatrix(worldSpace=True),
            self.WIP,
        )
        self.wrist_mid_jnt.attr("radius").set(3)
        self.wrist_mid_jnt.setAttr("jointOrient", 0, 0, 0)

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
            self.root, self.getName("elbow_lvl"), transform.getTransform(self.elbow_mid_jnt)
        )
        self.elbow_ctl = self.addCtl(
            self.elbow_lvl,
            "elbow_ctl",
            transform.getTransform(self.elbow_mid_jnt),
            self.color_ik,
            "sphere",
            w=self.size * 0.18,
            tp=self.root_ctl,
        )
        attribute.setInvertMirror(self.elbow_ctl, ["tx", "ty", "tz"])
        attribute.lockAttribute(self.elbow_ctl, ["sx", "sy", "sz", "v"])

        self.wrist_lvl = primitive.addTransform(
            self.root, self.getName("wrist_lvl"), transform.getTransform(self.wrist_mid_jnt)
        )
        self.wrist_ctl = self.addCtl(
            self.wrist_lvl,
            "wrist_ctl",
            transform.getTransform(self.wrist_mid_jnt),
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

        blade_pole_dir = self.guide.apos[2] - self.guide.apos[0]
        blade_pole_dir = blade_pole_dir ^ self.normal
        blade_pole_dir.normalize()
        blade_pole_pos = self.guide.apos[1] + (blade_pole_dir * self.size)
        blade_plane_normal = vector.getPlaneNormal(self.guide.apos[0], self.guide.apos[2], blade_pole_pos)
        blade_target_basis = transform.getTransformLookingAt(
            self.guide.apos[0], self.guide.apos[2], blade_plane_normal, "xz", False
        )
        upv_t = transform.setMatrixPosition(blade_target_basis, blade_pole_pos)
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

        blade_pole_t = transform.setMatrixPosition(blade_target_basis, blade_pole_pos)
        self.effective_upv_npo = primitive.addTransform(self.upv_cns, self.getName("effectiveUpv_npo"), blade_pole_t)
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
        wrist_t = transform.getTransformFromPos(self.guide.pos["wrist"])
        self._add_hand_upv_refs(wrist_t, blade_pole_dir)
        hand_t = transform.getTransformLookingAt(self.guide.apos[2], self.guide.apos[3], self.root_normal, "zx", False)
        hand_t = transform.setMatrixPosition(hand_t, self.guide.pos["eff"])
        self.hand_ik_parent_cns = primitive.addTransform(self.root, self.getName("hand_ik_parent_cns"), wrist_t)
        self.hand_ik_parent_ik_ref = primitive.addTransform(
            self.softblendLoc, self.getName("hand_ik_parent_ik_ref"), wrist_t
        )
        wrist_chain_t = transform.setMatrixPosition(
            transform.getTransform(self.chain2bones[1]), self.guide.pos["wrist"]
        )
        self.hand_ik_parent_chain_pos = primitive.addTransform(
            self.root, self.getName("hand_ik_parent_chain_pos"), wrist_chain_t
        )
        self.hand_ik_parent_chain_ref = primitive.addTransform(
            self.hand_ik_parent_chain_pos, self.getName("hand_ik_parent_chain_ref"), wrist_t
        )
        length = vector.getDistance(self.guide.apos[3], self.guide.apos[2])
        self.ikRot_npo = primitive.addTransform(self.hand_ik_parent_cns, self.getName("ikRot_npo"), wrist_t)
        self.ikRot_ctl = self.addCtl(
            self.ikRot_npo,
            "ikRot_ctl",
            wrist_t,
            self.color_ik,
            "cube",
            d=self.size * 0.16,
            h=self.size * 0.16,
            w=length * 0.5,
            po=datatypes.Vector(0.25 * length, 0, 0),
            tp=self.ik_ctl,
        )
        attribute.setRotOrder(self.ikRot_ctl, "XZY")
        attribute.setKeyableAttributes(self.ikRot_ctl, ["rx", "ry", "rz"])
        attribute.setInvertMirror(self.ikRot_ctl, ["ry", "rz"])
        attribute.lockAttribute(self.ikRot_ctl, ["tx", "ty", "tz", "sx", "sy", "sz", "v"])

        self.hand_ik_cns = primitive.addTransform(self.ikRot_ctl, self.getName("hand_ik_cns"), hand_t)
        self.hand_ik_ctl = self.addCtl(
            self.hand_ik_cns,
            "hand_ik_ctl",
            hand_t,
            self.color_ik,
            "cube",
            w=self.size * 0.20,
            h=self.size * 0.20,
            d=max(self.length2, self.size * 0.1) * 0.18,
            tp=self.ikRot_ctl,
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
            self.elbow_mid_jnt, self.getName("tws1_loc"), transform.getTransform(self.elbow_mid_jnt)
        )
        self.tws1_rot = primitive.addTransform(
            self.tws1_loc, self.getName("tws1_rot"), transform.getTransform(self.elbow_mid_jnt)
        )
        self.tws1_rot.setAttr("sx", 0.001)
        self.tws2_loc = primitive.addTransform(
            self.wrist_mid_jnt, self.getName("tws2_loc"), transform.getTransform(self.wrist_mid_jnt)
        )
        self.tws2_rot = primitive.addTransform(
            self.tws2_loc, self.getName("tws2_rot"), transform.getTransform(self.wrist_mid_jnt)
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
        for name, wing_bone in [
            ("root", self.wingBones[0]),
            ("elbow", self.wingBones[1]),
            ("wrist", self.wingBones[2]),
            ("eff", self.wingBones[3]),
        ]:
            ref = primitive.addTransform(
                self.root_ctl,
                self.getName("%s_jnt_ref" % name),
                transform.getTransform(wing_bone),
            )
            self.deform_anchor_refs[name] = ref
            pm.parentConstraint(wing_bone, ref, mo=False)
            self.deform_anchor_drivers[name] = ref

        self.support_anchor_drivers = {}
        for name, correction_ctl in [
            ("elbow_mid", self.elbow_ctl),
            ("wrist_mid", self.wrist_ctl),
        ]:
            driver = primitive.addTransform(
                self.root_ctl,
                self.getName("%s_jnt_corr" % name),
                transform.getTransform(correction_ctl),
            )
            node.createMultMatrixNode(
                correction_ctl.attr("worldMatrix"),
                self.root_ctl.attr("worldInverseMatrix"),
                driver,
                "rt",
            )
            self.support_anchor_drivers[name] = driver

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
        joint_index += 1

        self.joint_indices["elbow_mid"] = joint_index
        self.jnt_pos.append([self.support_anchor_drivers["elbow_mid"], "elbow_mid", "elbow"])
        joint_index += 1
        self.joint_indices["wrist_mid"] = joint_index
        self.jnt_pos.append([self.support_anchor_drivers["wrist_mid"], "wrist_mid", "wrist"])

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
        self.match_hand_ik = self._add_match_ref_from(self.hand_ik_ctl, self.wingBones[3], self.root, "handIk_mth")
        self.match_ikUpv = self.add_match_ref(self.upv_ctl, self.fk0_ctl, "upv_mth")

        self.line_ref = icon.connection_display_curve(self.getName("visalRef"), [self.upv_ctl, self.elbow_ctl])
        self.hand_line_ref = icon.connection_display_curve(
            self.getName("handVisalRef"), [self.ikRot_ctl, self.hand_ik_ctl]
        )

    def addAttributes(self) -> None:
        """Create anim and setup attributes."""

        self.blend_att = self.addAnimParam("blend", "Fk/Ik Blend", "double", self.settings["blend"], 0, 1)
        self.volume_att = self.addAnimParam("volume", "Volume", "double", 1, 0, 1)
        self.roll_att = self.addAnimParam("roll", "Roll", "double", 0, -180, 180)
        self.handRoll_att = self.addAnimParam("handRoll", "Hand Roll", "double", 0, -180, 180)
        self.wristControlMode_att = self.addAnimEnumParam(
            "wristControlMode",
            "Wrist Control Mode",
            int(max(0, min(len(self.wrist_control_mode_names) - 1, self.settings.get("wristControlMode", 0)))),
            self.wrist_control_mode_names,
        )
        self.soft_attr = self.addAnimParam("softIKRange", "Soft IK Range Ratio", "double", 0.0001, 0.0001, 1)
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
            ref_names = ["Auto", *ref_names]
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
            attribute.addProxyAttribute(
                [self.roll_att, self.handRoll_att, self.wristControlMode_att],
                [self.ik_ctl, self.ikRot_ctl, self.hand_ik_ctl, self.upv_ctl],
            )

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
        elbow_flip_offset = self.chain2bones[1].attr("jointOrientZ").get() / 2
        self.elbowFlipOffset_att = self.addSetupParam(
            "elbowFlipOffset", "Elbow Flip Offset", "double", elbow_flip_offset, -180, 180
        )
        self.wristFlipOffset_att = self.addSetupParam("wristFlipOffset", "Wrist Flip Offset", "double", 0, -180, 180)

    def _set_ik_solver(self) -> None:
        if self.settings["ikSolver"]:
            self.ikSolver = "ikRPsolver"
        else:
            pm.mel.eval("ikSpringSolver;")
            self.ikSolver = "ikSpringSolver"

    def _connect_mid_support_operators(self) -> None:
        for wing_bone, mid_jnt in [
            (self.wingBones[1], self.elbow_mid_jnt),
            (self.wingBones[2], self.wrist_mid_jnt),
        ]:
            node.createPairBlend(None, wing_bone, 0.5, 1, mid_jnt)
            pm.connectAttr(wing_bone + ".translate", mid_jnt + ".translate", f=True)

    def _connect_upv_ref_operator(self) -> None:
        self.ikHandleUpvRef = primitive.addIkHandle(
            self.root, self.getName("ikHandleWingUpvRef"), self.upvRefChain, "ikSCsolver"
        )
        pm.pointConstraint(self.ik_ctl, self.ikHandleUpvRef)
        pm.parentConstraint(self.upvRefChain[0], self.upv_cns, mo=True)

        pm.parentConstraint(self.elbow_mid_jnt, self.elbow_lvl)
        pm.parentConstraint(self.wrist_mid_jnt, self.wrist_lvl)

    def _connect_ik_handles(self) -> None:
        self.ikHandle2 = primitive.addIkHandle(
            self.softblendLoc, self.getName("ik2BonesHandle"), self.chain2bones, self.ikSolver, self.effective_upv_ref
        )
        if self.ikSolver == "ikSpringSolver":
            pm.mel.eval("ikSpringSolver;")

        pm.pointConstraint(self.root_ctl, self.chain2bones[0], maintainOffset=True)
        pm.connectAttr(self.upv_ctl.attr("translate"), self.effective_upv_ref.attr("translate"), f=True)
        pm.connectAttr(self.upv_ctl.attr("translate"), self.hand_effective_upv_ref.attr("translate"), f=True)
        pm.pointConstraint(self.chain2bones[2], self.handChain[0], maintainOffset=False)

        self.ikHandleHand = primitive.addIkHandle(self.root, self.getName("ikHandHandle"), self.handChain, "ikSCsolver")
        pm.pointConstraint(self.hand_ik_ctl, self.ikHandleHand, maintainOffset=False)
        self.ikHandleHandUpvRef = primitive.addIkHandle(
            self.root, self.getName("ikHandleHandUpvRef"), self.handUpvRefChain, "ikSCsolver"
        )
        pm.pointConstraint(self.handChain[0], self.handUpvRefChain[0], maintainOffset=False)
        pm.pointConstraint(self.hand_ik_ctl, self.ikHandleHandUpvRef, maintainOffset=False)
        pm.pointConstraint(self.handChain[0], self.hand_upv_aim_ref, maintainOffset=False)
        applyop.aimCns(
            self.hand_upv_aim_ref,
            self.hand_ik_ctl,
            axis="xz",
            wupType="object",
            wupVector=[0, 0, 1],
            wupObject=self.hand_effective_upv_ref,
            maintainOffset=False,
        )
        pm.orientConstraint(self.hand_upv_aim_ref, self.ikHandleHand, maintainOffset=False)

    def _connect_hand_parent_mode(self) -> None:
        pm.parentConstraint(self.ik_ctl, self.softblendLoc, skipTranslate=["x", "y", "z"], maintainOffset=False)
        pm.parentConstraint(
            self.chain2bones[2],
            self.hand_ik_parent_chain_pos,
            skipRotate=["x", "y", "z"],
            maintainOffset=False,
        )
        pm.parentConstraint(
            self.chain2bones[1],
            self.hand_ik_parent_chain_pos,
            skipTranslate=["x", "y", "z"],
            maintainOffset=True,
        )
        hand_parent_cns = pm.parentConstraint(
            self.hand_ik_parent_ik_ref,
            self.hand_ik_parent_chain_ref,
            self.hand_ik_parent_cns,
            maintainOffset=False,
        )
        self._connect_enum_condition(self.wristControlMode_att, 0, hand_parent_cns + ".target[0].targetWeight")
        self._connect_enum_condition(self.wristControlMode_att, 1, hand_parent_cns + ".target[1].targetWeight")

    def _connect_hand_ik_cns_offset(self) -> None:
        down, _, up = yu.findPathAtoB(self.ik_ctl, self.ikRot_ctl)
        mult = pm.createNode("multMatrix")
        compose = pm.createNode("composeMatrix")
        pm.setAttr(compose + ".inputTranslate", self.hand_ik_cns.attr("translate").get())

        for i, d in enumerate(down):
            pm.connectAttr("{}.matrix".format(d), "{}.matrixIn[{}]".format(mult, i))

        for j, u in enumerate(up):
            pm.connectAttr("{}.inverseMatrix".format(u), "{}.matrixIn[{}]".format(mult, i + j + 1))

        pm.connectAttr(compose + ".outputMatrix", mult + ".matrixIn[{}]".format(i + j + 2))
        decomp = pm.createNode("decomposeMatrix")
        pm.connectAttr(mult + ".matrixSum", decomp + ".inputMatrix")
        pm.connectAttr(decomp + ".outputTranslate", self.hand_ik_cns.attr("translate"))

    def _connect_twist_and_aim(self) -> None:
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

    def _connect_soft_ik_and_stretch(self, multJnt1_node: PymelNode, multJnt2_node: PymelNode) -> None:
        plus_total_length_node = node.createPlusMinusAverage1D(
            [multJnt1_node.attr("outputX"), multJnt2_node.attr("outputX")]
        )
        soft_range_node = node.createMulNode(plus_total_length_node.attr("output1D"), self.soft_attr_cond)
        soft_range_attr = soft_range_node.attr("outputX")
        subtract1_node = node.createPlusMinusAverage1D([plus_total_length_node.attr("output1D"), soft_range_attr], 2)
        distance1_node = node.createDistNode(self.ik_ref, self.aim_tra)
        div1_node = node.createDivNode(1.0, self.rig.global_ctl + ".sx")
        mult1_node = node.createMulNode(distance1_node + ".distance", div1_node + ".outputX")
        subtract2_node = node.createPlusMinusAverage1D([mult1_node.attr("outputX"), subtract1_node.attr("output1D")], 2)
        div2_node = node.createDivNode(subtract2_node + ".output1D", soft_range_attr)
        mult2_node = node.createMulNode(-1, div2_node + ".outputX")
        power_node = node.createPowNode(self.softSpeed_attr, mult2_node + ".outputX")
        mult3_node = node.createMulNode(soft_range_attr, power_node + ".outputX")
        subtract3_node = node.createPlusMinusAverage1D(
            [plus_total_length_node.attr("output1D"), mult3_node.attr("outputX")], 2
        )
        cond1_node = node.createConditionNode(
            soft_range_attr, 0, 2, subtract3_node + ".output1D", plus_total_length_node + ".output1D"
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

    def _connect_result_chains(self, multJnt3_node: PymelNode) -> None:
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

    def _connect_twist_driver_controls(self) -> None:
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

    def _connect_volume_driver(self) -> None:
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

    def _connect_division_operators(self) -> None:
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

    def _connect_visibility(self) -> None:
        fkvis_node = node.createReverseNode(self.blend_att)
        for ctrl in self.fk_ctl:
            for shp in ctrl.getShapes():
                pm.connectAttr(fkvis_node + ".outputX", shp.attr("visibility"))
        for ctrl in [self.ik_ctl, self.ikRot_ctl, self.hand_ik_ctl, self.upv_ctl, self.line_ref, self.hand_line_ref]:
            for shp in ctrl.getShapes():
                pm.connectAttr(self.blend_att, shp.attr("visibility"))

    def _connect_match_refs(self) -> None:
        pm.connectAttr(self.rig.global_ctl + ".scale", self.setup + ".scale")

        for wing_bone, match_off in zip(
            self.wingBones,
            [self.match_fk0_off, self.match_fk1_off, self.match_fk2_off],
        ):
            pm.parentConstraint(wing_bone, match_off, mo=False)
        pm.parentConstraint(self.wingBones[2], self.match_ik, mo=True)
        pm.parentConstraint(self.wingBones[3], self.match_hand_ik, mo=True)

    def addOperators(self) -> None:
        """Apply operators, constraints, and expressions."""

        soft_cond_node = node.createConditionNode(self.soft_attr, 0.0001, 4, 0.0001, self.soft_attr)
        self.soft_attr_cond = soft_cond_node.outColorR
        self._set_ik_solver()

        multJnt1_node = node.createMulNode(self.boneALenght_attr, self.boneALenghtMult_attr)
        multJnt2_node = node.createMulNode(self.boneBLenght_attr, self.boneBLenghtMult_attr)
        multJnt3_node = node.createMulNode(self.boneCLenght_attr, self.boneCLenghtMult_attr)

        self._connect_upv_ref_operator()
        self._connect_ik_handles()
        self._connect_hand_parent_mode()
        self._connect_hand_ik_cns_offset()
        self._connect_twist_and_aim()
        self._connect_soft_ik_and_stretch(multJnt1_node, multJnt2_node)
        self._connect_result_chains(multJnt3_node)
        self._connect_mid_support_operators()
        self._connect_twist_driver_controls()
        self._connect_volume_driver()
        self._connect_division_operators()
        self._connect_visibility()
        self._connect_match_refs()

    def verifyAlignmentAccuracy(
        self, jnts: list[datatypes.Vector], guides: list[datatypes.Vector], degree: float = 10.0
    ) -> bool:
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

    def setRelation(self) -> None:
        """Set the relation between guide objects and rig objects."""

        self.relatives["root"] = self.root
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

    def addConnection(self) -> None:
        self.connections["standard"] = self.connect_standard
        self.connections["ymt_shoulder_01"] = self.connect_ymt_shoulder

    def get_feather_ribbon_refs(self) -> dict[str, object]:
        """Return stable driver objects used by feather ribbon child components."""
        return {
            "root": self.root,
            # "elbow": self.deform_anchor_drivers["elbow"],
            # "wrist": self.deform_anchor_drivers["wrist"],
            # "hand": self.deform_anchor_drivers["eff"],
            "elbow": self.support_anchor_drivers["elbow_mid"],
            "wrist": self.support_anchor_drivers["wrist_mid"],
            "hand": self.deform_anchor_drivers["eff"],
            "root_ctl": self.root_ctl,
            "normal": self.normal,
            "binormal": self.binormal,
            "size": self.size,
        }

    def connect_standard(self) -> None:
        self.parent.addChild(self.root)
        self.connectRef(self.settings["ikrefarray"], self.ik_cns)
        if self.settings["upvrefarray"]:
            self.connectRef("Auto," + self.settings["upvrefarray"], self.upv_cns, True)

    def connect_ymt_shoulder(self) -> None:
        if self.parent_comp is not None and "ymt_shoulder" in str(type(self.parent_comp)):
            self.armChainUpvRef = self.upvRefChain
            self.parent_comp.connect_arm(self)
        self.connect_standard()
