"""Component Leg 3 joints 01 module"""
import math

from maya.api import OpenMaya as om2
from maya import cmds

import importlib
try:
    pm = importlib.import_module("mgear.pymaya")
except ImportError:
    pm = importlib.import_module("pymel.core")
try:
    datatypes = importlib.import_module("mgear.pymaya.datatypes")
except ImportError:
    datatypes = importlib.import_module("pymel.core.datatypes")

from mgear.shifter import component

from mgear.core import node, applyop, vector, icon
from mgear.core import attribute, transform, primitive

import ymt_shifter_utility as yu

import typing
if typing.TYPE_CHECKING:
    from typing import Union, Optional
    from collections.abc import Sequence
    Vector3 = Sequence[float]

#############################################
# COMPONENT
#############################################


class Component(component.Main):
    """Four-bone leg component with endpoint-selectable IK.

    The component keeps three IK solve layers for the same guide chain:
    ``chain2bones`` solves root-to-ankle, ``chain3bones`` solves root-to-foot,
    and ``chain4bones`` solves root-to-toe. ``ikEndpoint`` selects which
    endpoint is considered active and moves a child endpoint offset under
    ``ik_cns`` so the animator's IK control is displayed at that point.
    Endpoint refs under ``ik_ctl`` are compensated to keep the raw ankle, foot,
    and toe target positions coherent for the active endpoint.

    Stretch is endpoint-local. Toe distributes stretch over A/B/C/D, Foot over
    A/B/C, and Ankle over A/B. Segments beyond the active endpoint keep their
    base guide length and follow the active solve through guide offset and
    ``ik_ctl`` rotation. The final IK chain selects active A/B/C/D lengths from
    the three solve layers so downstream deformation sees one coherent length
    state.

    Intermediate offset controls, historically named WIK in this component's
    internals, are layered between endpoints. Their local translate/rotate must
    affect the actual IK target, so Foot and Ankle also build shadow effective
    targets from the soft/raw blend locator plus the same local offset. Stretch
    distance is measured to those shadow targets, not merely to
    ``softblendLocFoot`` or ``softblendLoc2``.

    Keep the stretch distance graph solver-independent. It may read the IK
    control endpoint refs, soft IK locators, soft/raw blend locators, static
    guide offsets, and offset-control local channels. It must not read IK
    handles, solved chain joints, WIK auto-follow constraint results, or any
    downstream final IK joints, otherwise Maya can form evaluation cycles.
    """

    ik_endpoint_names = ["ankle", "foot", "toe"]
    ik_endpoint_labels = ["Ankle", "Foot", "Toe"]

    def _get_ik_endpoint_index(self):
        return int(max(0, min(len(self.ik_endpoint_names) - 1, self.settings.get("ikEndpoint", 2))))

    def _connect_endpoint_condition(self, endpoint_index, target_weight, true_value=1, false_value=0):
        cond_node = pm.createNode("condition")
        pm.setAttr(cond_node + ".operation", 0)
        pm.connectAttr(self.ikEndpoint_att, cond_node + ".firstTerm")
        pm.setAttr(cond_node + ".secondTerm", endpoint_index)
        pm.setAttr(cond_node + ".colorIfTrueR", true_value)
        pm.setAttr(cond_node + ".colorIfFalseR", false_value)
        pm.connectAttr(cond_node + ".outColorR", target_weight, f=True)

    def _connect_or_set(self, value, target_attr):
        attr_type = getattr(pm, "Attribute", None)
        if isinstance(value, str) or (attr_type and isinstance(value, attr_type)):
            pm.connectAttr(value, target_attr, f=True)
        else:
            pm.setAttr(target_attr, value)

    def _select_endpoint_scalar(self, ankle_value, foot_value, toe_value):
        foot_or_toe = pm.createNode("condition")
        pm.setAttr(foot_or_toe + ".operation", 0)
        pm.connectAttr(self.ikEndpoint_att, foot_or_toe + ".firstTerm")
        pm.setAttr(foot_or_toe + ".secondTerm", 1)
        self._connect_or_set(foot_value, foot_or_toe + ".colorIfTrueR")
        self._connect_or_set(toe_value, foot_or_toe + ".colorIfFalseR")

        ankle_or_distal = pm.createNode("condition")
        pm.setAttr(ankle_or_distal + ".operation", 0)
        pm.connectAttr(self.ikEndpoint_att, ankle_or_distal + ".firstTerm")
        pm.setAttr(ankle_or_distal + ".secondTerm", 0)
        self._connect_or_set(ankle_value, ankle_or_distal + ".colorIfTrueR")
        pm.connectAttr(foot_or_toe + ".outColorR", ankle_or_distal + ".colorIfFalseR", f=True)
        return ankle_or_distal + ".outColorR"

    def _parent_constraint_by_endpoint(self, endpoint_sources, target, maintainOffset=True):
        sources = []
        source_indices = []
        for name in self.ik_endpoint_names:
            source = endpoint_sources[name]
            if source not in sources:
                sources.append(source)
            source_indices.append(sources.index(source))

        cns = pm.parentConstraint(*sources, target, maintainOffset=maintainOffset)
        for source_index in range(len(sources)):
            weights = [
                1 if endpoint_source_index == source_index else 0
                for endpoint_source_index in source_indices
            ]
            selected = self._select_endpoint_scalar(weights[0], weights[1], weights[2])
            pm.connectAttr(selected, cns + ".target[%s].targetWeight" % source_index, f=True)
        return cns

    def _get_division_percents(self):
        percents = []
        for span_index, div_count in enumerate(
            [
                self.settings["div0"],
                self.settings["div1"],
                self.settings["div2"],
                self.settings["div3"],
            ]
        ):
            span_start = span_index * 0.25
            for div_index in range(div_count):
                perc = span_start + ((div_index + 1.0) / (div_count + 1.0)) * 0.25
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

    def _connect_endpoint_translate(self, endpoint_values, target):
        for i, axis in enumerate("xyz"):
            selected = self._select_endpoint_scalar(
                endpoint_values[0][i],
                endpoint_values[1][i],
                endpoint_values[2][i],
            )
            pm.connectAttr(selected, target.attr("t%s" % axis), f=True)

    def _point_in_matrix_space(self, point, space_matrix):
        local_point = om2.MPoint(point[0], point[1], point[2]) * om2.MMatrix(space_matrix).inverse()
        return datatypes.Vector(local_point.x, local_point.y, local_point.z)

    def _connect_ik_endpoint_offsets(self):
        self._connect_endpoint_translate(self.ik_endpoint_cns_offsets, self.ik_endpoint_cns)
        for name in self.ik_endpoint_names:
            self._connect_endpoint_translate(self.ik_endpoint_ref_offsets[name], self.ik_endpoint_refs[name])

    def _add_match_ref_from(self, ctl, source, parent, name, cnx=True):
        match = primitive.addTransform(parent, self.getName(name), transform.getTransform(source))
        if cnx:
            ctl.addAttr("match_ref", at="message", multi=False)
            pm.connectAttr(match.message, ctl.match_ref)
        return match

    def _add_match_ref_from_matrix(self, ctl, matrix, parent, name, cnx=True):
        match = primitive.addTransform(parent, self.getName(name), matrix)
        if cnx:
            ctl.addAttr("match_ref", at="message", multi=False)
            pm.connectAttr(match.message, ctl.match_ref)
        return match

    # =====================================================
    # OBJECTS
    # =====================================================
    def addObjects(self):
        """Add all the objects needed to create the component."""

        self.setup = primitive.addTransformFromPos(self.setupWS, self.getName("WS"))
        attribute.lockAttribute(self.setup)

        self.WIP = self.options["mode"]

        m = om2.MMatrix(self.guide.tra["root"])
        self.root_normal = datatypes.Vector(m[1], m[5], m[9]).normal()  # Y-up axis of the root guide transform
        self.normal = self.getNormalFromPos(self.guide.apos)

        self.length0 = vector.getDistance(self.guide.apos[0], self.guide.apos[1])
        self.length1 = vector.getDistance(self.guide.apos[1], self.guide.apos[2])
        self.length2 = vector.getDistance(self.guide.apos[2], self.guide.apos[3])
        self.length3 = vector.getDistance(self.guide.apos[3], self.guide.apos[4])
        self.length4 = vector.getDistance(self.guide.apos[4], self.guide.apos[5])

        # 4bones chain
        self.chain4bones = yu.add3DChain(
            self.setup, self.getName("chain4bones%s_jnt"), self.guide.apos[0:5], self.normal, False, self.WIP
        )

        # 3bones chain
        self.chain3bones = yu.add3DChain(
            self.setup, self.getName("chain3bones%s_jnt"), self.guide.apos[0:4], self.normal, False, self.WIP
        )

        # 2bones chain
        self.chain2bones = yu.add3DChain(
            self.setup, self.getName("chain2bones%s_jnt"), self.guide.apos[0:3], self.normal, False, self.WIP
        )

        # Leg chain
        self.legBones = yu.add3DChain(
            self.root, self.getName("legBones%s_jnt"), self.guide.apos[0:5], self.normal, False, self.WIP
        )

        # Leg chain FK ref
        self.legBonesFK = yu.add3DChain(
            self.root, self.getName("legFK%s_jnt"), self.guide.apos[0:5], self.normal, False, self.WIP
        )

        # Leg chain IK ref
        self.legBonesIK = yu.add3DChain(
            self.root, self.getName("legIK%s_jnt"), self.guide.apos[0:5], self.normal, False, self.WIP
        )

        # 1 bone chain for upv ref
        self.legChainUpvRef = yu.add3DChain(
            self.root,
            self.getName("legUpvRef%s_jnt"),
            [self.guide.apos[0], self.guide.apos[3]],
            self.normal,
            False,
            self.WIP,
        )

        # mid joints
        self.mid1_jnt = primitive.addJoint(
            self.legBones[0], self.getName("mid1_jnt"), self.legBones[1].getMatrix(worldSpace=True), self.WIP
        )

        self.mid1_jnt.attr("radius").set(3)
        self.mid1_jnt.setAttr("jointOrient", 0, 0, 0)

        self.mid2_jnt = primitive.addJoint(
            self.legBones[1], self.getName("mid2_jnt"), self.legBones[2].getMatrix(worldSpace=True), self.WIP
        )

        self.mid2_jnt.attr("radius").set(3)
        self.mid2_jnt.setAttr("jointOrient", 0, 0, 0)

        # base Controlers -----------------------------------
        t = transform.getTransformFromPos(self.guide.apos[0])
        self.root_npo = primitive.addTransform(self.root, self.getName("root_npo"), t)

        self.root_ctl = self.addCtl(
            self.root_npo, "root_ctl", t, self.color_fk, "circle", w=self.length0 / 6, tp=self.parentCtlTag
        )
        attribute.lockAttribute(self.root_ctl, ["sx", "sy", "sz", "v"])

        ##################################################>
        # FK Controlers
        ##################################################>

        # FK0 --------------------------------------------
        t = transform.getTransformLookingAt(self.guide.apos[0], self.guide.apos[1], self.normal, "xz", self.negate)
        self.fk0_npo = primitive.addTransform(self.root_ctl, self.getName("fk0_npo"), t)
        self.fk0_ctl = self.addCtl(
            self.fk0_npo,
            "fk0_ctl",
            t,
            self.color_fk,
            "cube",
            w=self.length0,
            h=self.size * 0.1,
            d=self.size * 0.1,
            po=datatypes.Vector(0.5 * self.length0 * self.n_factor, 0, 0),
            tp=self.root_ctl,
        )
        attribute.setKeyableAttributes(self.fk0_ctl)

        # FK1 --------------------------------------------
        t = transform.getTransformLookingAt(self.guide.apos[1], self.guide.apos[2], self.normal, "xz", self.negate)
        self.fk1_npo = primitive.addTransform(self.fk0_ctl, self.getName("fk1_npo"), t)
        self.fk1_ctl = self.addCtl(
            self.fk1_npo,
            "fk1_ctl",
            t,
            self.color_fk,
            "cube",
            w=self.length1,
            h=self.size * 0.1,
            d=self.size * 0.1,
            po=datatypes.Vector(0.5 * self.length1 * self.n_factor, 0, 0),
            tp=self.fk0_ctl,
        )
        attribute.setKeyableAttributes(self.fk1_ctl)

        # FK2 --------------------------------------------
        t = transform.getTransformLookingAt(self.guide.apos[2], self.guide.apos[3], self.normal, "xz", self.negate)
        self.fk2_npo = primitive.addTransform(self.fk1_ctl, self.getName("fk2_npo"), t)
        self.fk2_ctl = self.addCtl(
            self.fk2_npo,
            "fk2_ctl",
            t,
            self.color_fk,
            "cube",
            w=self.length2,
            h=self.size * 0.1,
            d=self.size * 0.1,
            po=datatypes.Vector(0.5 * self.length2 * self.n_factor, 0, 0),
            tp=self.fk1_ctl,
        )
        attribute.setKeyableAttributes(self.fk2_ctl)

        # FK3 --------------------------------------------
        t = transform.getTransformLookingAt(self.guide.apos[3], self.guide.apos[4], self.normal, "xz", self.negate)
        self.fk3_npo = primitive.addTransform(self.fk2_ctl, self.getName("fk3_npo"), t)
        self.fk3_ctl = self.addCtl(
            self.fk3_npo,
            "fk3_ctl",
            t,
            self.color_fk,
            "cube",
            w=self.length3,
            h=self.size * 0.1,
            d=self.size * 0.1,
            po=datatypes.Vector(0.5 * self.length3 * self.n_factor, 0, 0),
            tp=self.fk2_ctl,
        )
        attribute.setKeyableAttributes(self.fk3_ctl)

        # FK4 --------------------------------------------
        t = transform.getTransformLookingAt(self.guide.apos[4], self.guide.apos[5], self.normal, "xz", self.negate)
        self.fk4_npo = primitive.addTransform(self.fk2_ctl, self.getName("fk4_npo"), t)
        self.fk4_ctl = self.addCtl(
            self.fk4_npo,
            "fk4_ctl",
            t,
            self.color_fk,
            "cube",
            w=self.length4,
            h=self.size * 0.1,
            d=self.size * 0.1,
            po=datatypes.Vector(0.5 * self.length4 * self.n_factor, 0, 0),
            tp=self.fk2_ctl,
        )
        attribute.setKeyableAttributes(self.fk4_ctl)

        self.fk_ctl = [self.fk0_ctl, self.fk1_ctl, self.fk2_ctl, self.fk3_ctl, self.fk4_ctl]

        for x in self.fk_ctl:
            attribute.setInvertMirror(x, ["tx", "ty", "tz"])

        # Mid Controlers ------------------------------------
        self.knee_lvl = primitive.addTransform(
            self.root, self.getName("knee_lvl"), transform.getTransform(self.mid1_jnt)
        )

        self.knee_ctl = self.addCtl(
            self.knee_lvl,
            "knee_ctl",
            transform.getTransform(self.mid1_jnt),
            self.color_ik,
            "sphere",
            w=self.size * 0.2,
            tp=self.root_ctl,
        )

        attribute.setInvertMirror(self.knee_ctl, ["tx", "ty", "tz"])
        attribute.lockAttribute(self.knee_ctl, ["sx", "sy", "sz", "v"])

        self.ankle_lvl = primitive.addTransform(
            self.root, self.getName("ankle_lvl"), transform.getTransform(self.mid2_jnt)
        )

        self.ankle_ctl = self.addCtl(
            self.ankle_lvl,
            "ankle_ctl",
            transform.getTransform(self.mid2_jnt),
            self.color_ik,
            "sphere",
            w=self.size * 0.2,
            tp=self.knee_ctl,
        )

        attribute.setInvertMirror(self.ankle_ctl, ["tx", "ty", "tz"])
        attribute.lockAttribute(self.ankle_ctl, ["sx", "sy", "sz", "v"])

        self.foot_lvl = primitive.addTransform(
            self.root, self.getName("foot_lvl"), transform.getTransform(self.legBones[3])
        )

        self.foot_ctl = self.addCtl(
            self.foot_lvl,
            "foot_ctl",
            transform.getTransform(self.legBones[3]),
            self.color_ik,
            "sphere",
            w=self.size * 0.2,
            tp=self.ankle_ctl,
        )

        attribute.setInvertMirror(self.foot_ctl, ["tx", "ty", "tz"])
        attribute.lockAttribute(self.foot_ctl, ["sx", "sy", "sz", "v"])

        # IK controls --------------------------------------------------------
        try:
            rot_x_p90 = datatypes.EulerRotation(math.radians(90), 0, 0, unit="radians").asMatrix()
            rot_x_m90 = datatypes.EulerRotation(math.radians(-90), 0, 0, unit="radians").asMatrix()
            rot_y_p90 = datatypes.EulerRotation(0, math.radians(90), 0, unit="radians").asMatrix()
            rot_z_p90 = datatypes.EulerRotation(0, 0, math.radians(90), unit="radians").asMatrix()

        except ValueError:
            rot_x_p90 = datatypes.EulerRotation(math.radians(90), 0, 0).asMatrix()
            rot_x_m90 = datatypes.EulerRotation(math.radians(-90), 0, 0).asMatrix()
            rot_y_p90 = datatypes.EulerRotation(0, math.radians(90), 0).asMatrix()
            rot_z_p90 = datatypes.EulerRotation(0, 0, math.radians(90)).asMatrix()

        # --------------------------------------------------------------------
        # foot IK
        # "z-x",
        t_align = transform.getTransformLookingAt(self.guide.apos[4], self.guide.apos[5], self.root_normal, "zx", False)

        ik_endpoint_index = self._get_ik_endpoint_index()
        ik_endpoint_name = self.ik_endpoint_names[ik_endpoint_index]

        if self.settings["ikOri"]:
            t = transform.getTransformFromPos(self.guide.pos["toe"])
        else:
            t = t_align
            t = rot_y_p90 * t
            t = rot_x_m90 * t
        t = transform.setMatrixPosition(t, self.guide.pos[ik_endpoint_name])

        length = vector.getDistance(self.guide.apos[5], self.guide.apos[4])
        self.ik_cns = primitive.addTransform(self.root_ctl, self.getName("ik_cns"), t)
        self.ik_endpoint_cns = primitive.addTransform(self.ik_cns, self.getName("ikEndpoint_cns"), t)
        self.ik_endpoint_cns_offsets = [
            self._point_in_matrix_space(self.guide.pos[name], t)
            for name in self.ik_endpoint_names
        ]
        self.ik_endpoint_match_transforms = {}
        for name in self.ik_endpoint_names:
            self.ik_endpoint_match_transforms[name] = transform.setMatrixPosition(t, self.guide.pos[name])

        self.ik_endpoint_ref_offsets = {}
        for ref_name in self.ik_endpoint_names:
            self.ik_endpoint_ref_offsets[ref_name] = []
            for active_name in self.ik_endpoint_names:
                self.ik_endpoint_ref_offsets[ref_name].append(
                    self._point_in_matrix_space(
                        self.guide.pos[ref_name],
                        self.ik_endpoint_match_transforms[active_name],
                    )
                )

        self.ik_ctl = self.addCtl(
            self.ik_endpoint_cns,
            "ik_ctl",
            t,
            self.color_ik,
            "cube",
            w=self.size * 0.25,
            h=length * 0.08,
            d=length * 2.00,
            tp=self.ik_endpoint_cns,
        )
        attribute.setKeyableAttributes(self.ik_ctl)
        attribute.setRotOrder(self.ik_ctl, "XZY")
        attribute.setInvertMirror(self.ik_ctl, ["tx", "ry", "rz"])
        attribute.lockAttribute(self.ik_ctl, ["sx", "sy", "sz", "v"])

        # --------------------------------------------------------------------
        # foot intermediate offset control

        t_align2 = transform.getTransformLookingAt(self.guide.apos[4], self.guide.apos[3], self.root_normal, "zx", False)
        if self.settings["ikOri"]:
            t_align2 = rot_y_p90 * t_align2
            t_align2 = rot_z_p90 * t_align2
            t_align2 = rot_x_p90 * t_align2
            w = self.size * 0.36
            h = self.size * 0.20
            d = length * 0.1
            po = datatypes.Vector(0.0, 0.0, length * -0.5)
        else:
            t_align2 = rot_y_p90 * t_align2
            t_align2 = rot_x_m90 * t_align2
            h = self.size * 0.36
            d = self.size * 0.20
            w = length * 0.1
            po = datatypes.Vector(length * -0.5, 0.0, 0.0)

        length = vector.getDistance(self.guide.apos[4], self.guide.apos[3])
        self.wik_cns_01 = primitive.addTransform(self.root_ctl, self.getName("wik_cns_01"), t_align2)
        self.wik_ctl_01 = self.addCtl(
            self.wik_cns_01,
            "footOffset_ctl",
            t_align2,
            self.color_fk,
            "cube",
            h=h,
            d=d,
            w=w,
            po=po,
            tp=self.ik_cns,
        )
        attribute.setKeyableAttributes(self.wik_ctl_01)
        attribute.setRotOrder(self.wik_ctl_01, "XZY")
        attribute.setInvertMirror(self.wik_ctl_01, ["tx", "ry", "rz"])
        attribute.lockAttribute(self.wik_ctl_01, ["sx", "sy", "sz", "v"])

        length = vector.getDistance(self.guide.apos[3], self.guide.apos[2])
        t_align3 = transform.getTransformLookingAt(self.guide.apos[3], self.guide.apos[2], self.root_normal, "zx", False)
        if self.settings["ikOri"]:
            t_align3 = rot_y_p90 * t_align3
            t_align3 = rot_z_p90 * t_align3
            t_align3 = rot_x_p90 * t_align3
            w = self.size * 0.36
            h = self.size * 0.20
            d = length * 0.1
            po = datatypes.Vector(0.0, 0.0, length * -0.5)
        else:
            t_align3 = rot_y_p90 * t_align3
            t_align3 = rot_x_m90 * t_align3
            h = self.size * 0.36
            d = self.size * 0.20
            w = length * 0.1
            po = datatypes.Vector(length * -0.5, 0.0, 0.0)

        length = vector.getDistance(self.guide.apos[3], self.guide.apos[2])
        self.wik_cns_02 = primitive.addTransform(self.root_ctl, self.getName("wik_cns_02"), t_align3)
        self.wik_ctl_02 = self.addCtl(
            self.wik_cns_02,
            "ankleOffset_ctl",
            t_align3,
            self.color_fk,
            "cube",
            h=h,
            d=d,
            w=w,
            po=po,
            tp=self.ik_cns,
        )
        attribute.setKeyableAttributes(self.wik_ctl_02)
        attribute.setRotOrder(self.wik_ctl_02, "XZY")
        attribute.setInvertMirror(self.wik_ctl_02, ["tx", "ry", "rz"])
        attribute.lockAttribute(self.wik_ctl_02, ["sx", "sy", "sz", "v"])

        # IK endpoint position references
        self.ik_endpoint_refs = {
            name: primitive.addTransformFromPos(
                self.ik_ctl, self.getName("ikEndpoint_%s_ref" % name), self.guide.pos[name]
            )
            for name in self.ik_endpoint_names
        }

        self.ik3b_ik_ref = primitive.addTransformFromPos(
            self.wik_ctl_01, self.getName("ik3B_ik_ref"), self.guide.pos["foot"]
        )

        roll_t = transform.getTransformLookingAt(
            self.guide.apos[0], self.guide.apos[1], self.guide.apos[5] - self.guide.apos[4], "yz", False
        )
        roll_t = transform.setMatrixPosition(roll_t, self.guide.apos[0])
        self.ik2b_ik_npo = primitive.addTransform(
            self.wik_ctl_02, self.getName("ik2B_ik_npo"), transform.getTransform(self.chain3bones[-1])
        )

        self.ik2b_ik_ref = primitive.addTransformFromPos(
            self.ik2b_ik_npo, self.getName("ik2B_ik_ref"), self.guide.pos["ankle"]
        )

        # upv
        v = self.guide.apos[2] - self.guide.apos[0]
        v = self.normal ^ v
        v.normalize()
        v *= self.size * 0.5
        v += self.guide.apos[1]

        self.upv_lvl = primitive.addTransformFromPos(self.root, self.getName("upv_lvl"), v)
        self.upv_cns = primitive.addTransformFromPos(self.upv_lvl, self.getName("upv_cns"), v)

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

        # Soft IK objects 4 bones chain --------------------------------
        t = transform.getTransformLookingAt(self.guide.pos["root"], self.guide.pos["toe"], self.x_axis, "zx", False)

        self.aim_tra = primitive.addTransform(self.root_ctl, self.getName("aimSoftIK"), t)

        t = transform.getTransformFromPos(self.guide.pos["toe"])
        self.wristSoftIK = primitive.addTransform(self.aim_tra, self.getName("wristSoftIK"), t)

        self.softblendLoc = primitive.addTransform(self.root, self.getName("softblendLoc"), t)

        # Soft IK objects 3 Bones chain ----------------------------
        t = transform.getTransformLookingAt(self.guide.pos["root"], self.guide.pos["foot"], self.x_axis, "zx", False)

        self.aim_tra_foot = primitive.addTransform(self.root_ctl, self.getName("aimSoftIKFoot"), t)

        t = transform.getTransformFromPos(self.guide.pos["foot"])
        self.footSoftIK = primitive.addTransform(self.aim_tra_foot, self.getName("footSoftIK"), t)

        self.softblendLocFoot = primitive.addTransform(self.root, self.getName("softblendLocFoot"), t)
        self.ik3b_stretch_npo = primitive.addTransform(
            self.softblendLocFoot, self.getName("ik3B_stretch_npo"), transform.getTransform(self.wik_ctl_01)
        )
        self.ik3b_stretch_ctl = primitive.addTransform(
            self.ik3b_stretch_npo, self.getName("ik3B_stretch_ctl"), transform.getTransform(self.wik_ctl_01)
        )
        attribute.setRotOrder(self.ik3b_stretch_ctl, "XZY")
        self.ik3b_stretch_ref = primitive.addTransformFromPos(
            self.ik3b_stretch_ctl, self.getName("ik3B_stretch_ref"), self.guide.pos["foot"]
        )

        # Soft IK objects 2 Bones chain ----------------------------
        t = transform.getTransformLookingAt(self.guide.pos["root"], self.guide.pos["ankle"], self.x_axis, "zx", False)

        self.aim_tra2 = primitive.addTransform(self.root_ctl, self.getName("aimSoftIK2"), t)

        t = transform.getTransformFromPos(self.guide.pos["ankle"])

        self.ankleSoftIK = primitive.addTransform(self.aim_tra2, self.getName("ankleSoftIK"), t)

        self.softblendLoc2 = primitive.addTransform(self.root, self.getName("softblendLoc2"), t)
        self.ankleSoftFoot_ref = primitive.addTransformFromPos(
            self.softblendLoc2, self.getName("ankleSoftFoot_ref"), self.guide.pos["foot"]
        )
        self.ik2b_stretch_npo = primitive.addTransform(
            self.softblendLoc2, self.getName("ik2B_stretch_npo"), transform.getTransform(self.wik_ctl_02)
        )
        self.ik2b_stretch_ctl = primitive.addTransform(
            self.ik2b_stretch_npo, self.getName("ik2B_stretch_ctl"), transform.getTransform(self.wik_ctl_02)
        )
        attribute.setRotOrder(self.ik2b_stretch_ctl, "XZY")
        self.ik2b_stretch_ref = primitive.addTransformFromPos(
            self.ik2b_stretch_ctl, self.getName("ik2B_stretch_ref"), self.guide.pos["ankle"]
        )

        # References --------------------------------------
        self.ik_ref = primitive.addTransform(self.ik_ctl, self.getName("ik_ref"), transform.getTransform(self.ik_ctl))

        self.fk_ref = primitive.addTransform(
            self.fk_ctl[4], self.getName("fk_ref"), transform.getTransform(self.ik_ctl)
        )

        # twist references --------------------------------------
        self.rollRef = primitive.add2DChain(
            self.root, self.getName("rollChain"), self.guide.apos[:2], self.normal, False, self.WIP
        )

        self.tws0_loc = primitive.addTransform(
            self.rollRef[0], self.getName("tws0_loc"), transform.getTransform(self.legBones[0])
        )
        self.tws0_rot = primitive.addTransform(
            self.tws0_loc, self.getName("tws0_rot"), transform.getTransform(self.legBones[0])
        )
        self.tws0_rot.setAttr("sx", 0.001)

        self.tws1_loc = primitive.addTransform(
            self.mid1_jnt, self.getName("tws1_loc"), transform.getTransform(self.mid1_jnt)
        )
        self.tws1_rot = primitive.addTransform(
            self.tws1_loc, self.getName("tws1_rot"), transform.getTransform(self.mid1_jnt)
        )
        self.tws1_rot.setAttr("sx", 0.001)

        self.tws2_loc = primitive.addTransform(
            self.mid2_jnt, self.getName("tws2_loc"), transform.getTransform(self.mid2_jnt)
        )
        self.tws2_rot = primitive.addTransform(
            self.tws2_loc, self.getName("tws2_rot"), transform.getTransform(self.mid2_jnt)
        )
        self.tws2_rot.setAttr("sx", 0.001)

        self.tws3_loc = primitive.addTransform(
            self.legBones[3], self.getName("tws3_loc"), transform.getTransform(self.legBones[3])
        )
        self.tws3_rot = primitive.addTransform(
            self.tws3_loc, self.getName("tws3_rot"), transform.getTransform(self.legBones[3])
        )
        self.tws3_rot.setAttr("sx", 0.001)

        self.tws4_loc = primitive.addTransform(
            self.legBones[4], self.getName("tws4_loc"), transform.getTransform(self.legBones[4])
        )
        self.tws4_rot = primitive.addTransform(
            self.tws4_loc, self.getName("tws4_rot"), transform.getTransform(self.legBones[4])
        )
        self.tws4_rot.setAttr("sx", 0.001)

        # Deform joint anchors and divisions ----------------
        # Anchor refs keep exact joint orientation at anatomical points.
        # div_cns are only the in-span roll/squash/stretch drivers.
        o_set = self.settings
        self.divisions = o_set["div0"] + o_set["div1"] + o_set["div2"] + o_set["div3"]

        self.joint_indices = {}
        self.deform_anchor_refs = {}
        self.deform_anchor_drivers = {}
        anchor_specs = [
            ("root", self.legBones[0], None),
            ("knee", self.legBones[1], self.knee_ctl),
            ("ankle", self.legBones[2], self.ankle_ctl),
            ("foot", self.legBones[3], self.foot_ctl),
            ("toe", self.legBones[4], None),
        ]
        for name, leg_bone, correction_ctl in anchor_specs:
            ref = primitive.addTransform(
                self.root_ctl,
                self.getName("%s_jnt_ref" % name),
                transform.getTransform(leg_bone),
            )
            self.deform_anchor_refs[name] = ref
            pm.parentConstraint(leg_bone, ref, mo=False)
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
                    "t",
                )
                node.createMultMatrixNode(
                    ref.attr("worldMatrix"),
                    self.root_ctl.attr("worldInverseMatrix"),
                    driver,
                    "r",
                )
            self.deform_anchor_drivers[name] = driver

        self.div_cns = []
        div_index = 0
        joint_index = 0
        span_specs = [
            ("root", o_set["div0"]),
            ("knee", o_set["div1"]),
            ("ankle", o_set["div2"]),
            ("foot", o_set["div3"]),
        ]
        for anchor_name, div_count in span_specs:
            self.joint_indices[anchor_name] = joint_index
            self.jnt_pos.append([self.deform_anchor_drivers[anchor_name], anchor_name])
            joint_index += 1
            for _ in range(div_count):
                div_cns = primitive.addTransform(self.root_ctl, self.getName("div%s_loc" % div_index))
                self.div_cns.append(div_cns)
                self.jnt_pos.append([div_cns, div_index])
                div_index += 1
                joint_index += 1

        self.joint_indices["toe"] = joint_index
        self.jnt_pos.append([self.deform_anchor_drivers["toe"], "toe"])
        joint_index += 1

        # for i in range(self.divisions):
        #     div_cns = primitive.addTransform(self.root_ctl, self.getName("div%s_loc" % i))
        #     self.div_cns.append(div_cns)
        #     self.jnt_pos.append([div_cns, i])

        # End reference ------------------------------------
        # To help the deformation on the foot
        self.end_ref = primitive.addTransform(
            self.tws4_rot, self.getName("end_ref"), transform.getTransform(self.legBones[4])
        )
        self.jnt_pos.append([self.end_ref, "end"])
        self.joint_indices["end"] = joint_index

        # match IK FK references
        self.match_fk = []
        for i, fk_ctl in enumerate(self.fk_ctl):
            match_off = self._add_match_ref_from(
                fk_ctl, self.legBones[i], self.root, "matchFk%s_npo" % i, False
            )
            match_ref = self._add_match_ref_from(fk_ctl, self.legBones[i], match_off, "fk%s_mth" % i)
            setattr(self, "match_fk%s_off" % i, match_off)
            setattr(self, "match_fk%s" % i, match_ref)
            self.match_fk.append(match_ref)

        self.match_ik_endpoint_refs = {}
        for name in self.ik_endpoint_names:
            self.match_ik_endpoint_refs[name] = self._add_match_ref_from_matrix(
                self.ik_ctl,
                self.ik_endpoint_match_transforms[name],
                self.root,
                "ikEndpoint_%s_mth" % name,
                False,
            )

        self.match_ik = self._add_match_ref_from_matrix(
            self.ik_ctl,
            self.ik_endpoint_match_transforms[ik_endpoint_name],
            self.root,
            "ik_mth",
        )

        self.match_foot_offset = self._add_match_ref_from_matrix(
            self.wik_ctl_01,
            transform.getTransform(self.wik_ctl_01),
            self.root,
            "footOffset_mth",
        )
        self.match_ankle_offset = self._add_match_ref_from_matrix(
            self.wik_ctl_02,
            transform.getTransform(self.wik_ctl_02),
            self.root,
            "ankleOffset_mth",
        )

        self.match_ikUpv = self.add_match_ref(self.upv_ctl, self.fk0_ctl, "upv_mth")

        # add visual reference
        self.line_ref = icon.connection_display_curve(self.getName("visalRef"), [self.upv_ctl, self.knee_ctl])

    def addAttributes(self):
        self.blend_att = self.addAnimParam("blend", "Fk/Ik Blend", "double", self.settings["blend"], 0, 1)
        self.ikEndpoint_att = self.addAnimEnumParam(
            "ikEndpoint",
            "IK Endpoint",
            self._get_ik_endpoint_index(),
            self.ik_endpoint_labels,
        )
        self.soft_attr = self.addAnimParam("softIKRange", "Soft IK Range", "double", 0.0001, 0.0001, 100)
        self.softSpeed_attr = self.addAnimParam("softIKSpeed", "Soft IK Speed", "double", 2.5, 1.001, 10)
        self.stretch_attr = self.addAnimParam("stretch", "Stretch", "double", 0, 0, 1)
        self.volume_att = self.addAnimParam("volume", "Volume", "double", 1, 0, 1)
        self.roll_att = self.addAnimParam("roll", "Roll", "double", 0, -180, 180)

        self.roundnessKnee_att = self.addAnimParam("roundnessKnee", "Roundness Knee", "double", 0, 0, self.size)
        self.roundnessAnkle_att = self.addAnimParam("roundnessAnkle", "Roundness Ankle", "double", 0, 0, self.size)
        self.roundnessFoot_att = self.addAnimParam("roundnessFoot", "Roundness Foot", "double", 0, 0, self.size)

        self.boneALenghtMult_attr = self.addAnimParam("boneALenMult", "Bone A Mult", "double", 1)
        self.boneBLenghtMult_attr = self.addAnimParam("boneBLenMult", "Bone B Mult", "double", 1)
        self.boneCLenghtMult_attr = self.addAnimParam("boneCLenMult", "Bone C Mult", "double", 1)
        self.boneDLenghtMult_attr = self.addAnimParam("boneDLenMult", "Bone D Mult", "double", 1)
        self.boneALenght_attr = self.addAnimParam("boneALen", "Bone A Length", "double", self.length0, keyable=False)
        self.boneBLenght_attr = self.addAnimParam("boneBLen", "Bone B Length", "double", self.length1, keyable=False)
        self.boneCLenght_attr = self.addAnimParam("boneCLen", "Bone C Length", "double", self.length2, keyable=False)
        self.boneDLenght_attr = self.addAnimParam("boneDLen", "Bone D Length", "double", self.length3, keyable=False)

        # Ref
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
                [self.blend_att, self.roundnessAnkle_att, self.roundnessKnee_att, self.roundnessFoot_att],
                [self.fk0_ctl, self.fk1_ctl, self.fk2_ctl, self.ik_ctl, self.upv_ctl],
            )
            attribute.addProxyAttribute(self.roll_att, [self.ik_ctl, self.upv_ctl])

        # Setup ------------------------------------------
        # Eval Fcurve
        self.division_percents = self._get_division_percents()
        self.st_value = self._sample_profile_values("st_profile", self.division_percents)
        self.sq_value = self._sample_profile_values("sq_profile", self.division_percents)

        self.st_att = []
        self.sq_att = []
        for i in range(self.divisions):
            st_val = self.st_value[i] if i < len(self.st_value) else 0
            sq_val = self.sq_value[i] if i < len(self.sq_value) else 0

            st_att = self.addSetupParam("stretch_%s" % i, "Stretch %s" % i, "double", st_val, -1, 0)
            sq_att = self.addSetupParam("squash_%s" % i, "Squash %s" % i, "double", sq_val, 0, 1)
            self.st_att.append(st_att)
            self.sq_att.append(sq_att)

        self.resample_att = self.addSetupParam("resample", "Resample", "bool", True)
        self.absolute_att = self.addSetupParam("absolute", "Absolute", "bool", False)

        defValu = self.chain3bones[1].attr("jointOrientZ").get() / 2
        self.kneeFlipOffset_att = self.addSetupParam("kneeFlipOffset", "Knee Flip Offset", "double", defValu, -180, 180)
        defValu = self.chain3bones[2].attr("jointOrientZ").get() / 2
        self.ankleFlipOffset_att = self.addSetupParam(
            "ankleFlipOffset", "Ankle Flip Offset", "double", defValu, -180, 180
        )
        defValu = self.chain4bones[3].attr("jointOrientZ").get() / 2
        self.footFlipOffset_att = self.addSetupParam(
            "footFlipOffset", "Foot Flip Offset", "double", defValu, -180, 180
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
        # Soft condition
        soft_cond_node = node.createConditionNode(self.soft_attr, 0.0001, 4, 0.0001, self.soft_attr)
        self.soft_attr_cond = soft_cond_node.outColorR
        self._connect_ik_endpoint_offsets()

        if self.settings["ikSolver"]:
            self.ikSolver = "ikRPsolver"
        else:
            pm.mel.eval("ikSpringSolver;")
            self.ikSolver = "ikSpringSolver"

        # 1 bone chain Upv ref ===============================
        self.ikHandleUpvRef = primitive.addIkHandle(
            self.root, self.getName("ikHandleLegChainUpvRef"), self.legChainUpvRef, "ikSCsolver"
        )
        pm.pointConstraint(self.ik_ctl, self.ikHandleUpvRef)
        pm.parentConstraint(self.legChainUpvRef[0], self.upv_cns, mo=True)

        # mid joints ================================================
        for xjnt, midJ in zip(self.legBones[1:3], [self.mid1_jnt, self.mid2_jnt]):
            node.createPairBlend(None, xjnt, 0.5, 1, midJ)
            pm.connectAttr(xjnt + ".translate", midJ + ".translate", f=True)

        pm.parentConstraint(self.mid1_jnt, self.knee_lvl)
        pm.parentConstraint(self.mid2_jnt, self.ankle_lvl)
        pm.parentConstraint(self.legBones[3], self.foot_lvl)

        # joint length multiply
        multJnt1_node = node.createMulNode(self.boneALenght_attr, self.boneALenghtMult_attr)
        multJnt2_node = node.createMulNode(self.boneBLenght_attr, self.boneBLenghtMult_attr)
        multJnt3_node = node.createMulNode(self.boneCLenght_attr, self.boneCLenghtMult_attr)
        multJnt4_node = node.createMulNode(self.boneDLenght_attr, self.boneDLenghtMult_attr)

        # Shadow targets copy only animator local offsets. They intentionally do
        # not read actual WIK world matrices, IK handles, or solved chains, so
        # stretch distance stays upstream of the solver graph.
        def connect_local_tr(src, dst):
            for attr_name in ("translate", "rotate"):
                pm.connectAttr(src.attr(attr_name), dst.attr(attr_name), f=True)

        connect_local_tr(self.wik_ctl_01, self.ik3b_stretch_ctl)
        connect_local_tr(self.wik_ctl_02, self.ik2b_stretch_ctl)

        # # IK 4 bones ===============================================

        self.ikHandle4 = primitive.addIkHandle(
            self.softblendLoc, self.getName("ik4BonesHandle"), self.chain4bones, self.ikSolver, self.upv_ctl
        )
        # # IK 3 bones ===============================================

        self.ikHandle3 = primitive.addIkHandle(
            self.ik3b_ik_ref, self.getName("ik3BonesHandle"), self.chain3bones, self.ikSolver, self.upv_ctl
        )

        self.ikHandle2 = primitive.addIkHandle(
            self.ik2b_ik_ref, self.getName("ik2BonesHandle"), self.chain2bones, self.ikSolver, self.upv_ctl
        )

        # TwistTest
        chainPos = [x.getTranslation(space="world") for x in self.chain4bones]
        sameDir = self.verifyAlignmentAccuracy(chainPos, self.guide.apos[:5])
        angle = 0 if sameDir else 180
        add_nodeTwist = node.createAddNode(angle, self.roll_att)
        if self.negate:
            mulVal = 1
        else:
            mulVal = -1
        node.createMulNode(add_nodeTwist + ".output", mulVal, self.ikHandle4.attr("twist"))

        chainPos = [x.getTranslation(space="world") for x in self.chain3bones]
        sameDir = self.verifyAlignmentAccuracy(chainPos, self.guide.apos[:4])
        angle = 0 if sameDir else 180
        add_nodeTwist = node.createAddNode(angle, self.roll_att)
        if self.negate:
            mulVal = 1
        else:
            mulVal = -1
        node.createMulNode(add_nodeTwist + ".output", mulVal, self.ikHandle3.attr("twist"))
        node.createMulNode(self.roll_att, mulVal, self.ikHandle2.attr("twist"))

        # stable spring solver doble rotation
        pm.pointConstraint(self.root_ctl, self.chain4bones[0], maintainOffset=True)
        pm.pointConstraint(self.root_ctl, self.chain3bones[0], maintainOffset=True)
        pm.pointConstraint(self.root_ctl, self.chain2bones[0], maintainOffset=True)

        # Constraint and up vector
        pm.poleVectorConstraint(self.upv_ctl, self.ikHandle4)
        self._parent_constraint_by_endpoint(
            {
                "ankle": self.ankleSoftFoot_ref,
                "foot": self.softblendLocFoot,
                "toe": self.chain4bones[3],
            },
            self.wik_cns_01,
            maintainOffset=True,
        )

        # Foot and Toe endpoint modes both consume the 3-bone foot solve here.
        # This keeps footOffset_ctl rotation layered into ankleOffset/chain2
        # while toe endpoint stretch and final target remain 4-bone based.
        self._parent_constraint_by_endpoint(
            {
                "ankle": self.softblendLoc2,
                "foot": self.chain3bones[2],
                "toe": self.chain3bones[2],
            },
            self.wik_cns_02,
            maintainOffset=True,
        )

        # softIK 4 bones operators
        applyop.aimCns(
            self.aim_tra,
            self.ik_endpoint_refs["toe"],
            axis="zx",
            wupType=4,
            wupVector=[1, 0, 0],
            wupObject=self.root_ctl,
            maintainOffset=False,
        )

        plusTotalLength_node = node.createPlusMinusAverage1D(
            [
                multJnt1_node.attr("outputX"),
                multJnt2_node.attr("outputX"),
                multJnt3_node.attr("outputX"),
                multJnt4_node.attr("outputX"),
            ]
        )
        subtract1_node = node.createPlusMinusAverage1D([plusTotalLength_node.attr("output1D"), self.soft_attr_cond], 2)
        distance1_node = node.createDistNode(self.ik_endpoint_refs["toe"], self.aim_tra)
        div1_node = node.createDivNode(1.0, self.rig.global_ctl + ".sx")
        mult1_node = node.createMulNode(distance1_node + ".distance", div1_node + ".outputX")
        subtract2_node = node.createPlusMinusAverage1D([mult1_node.attr("outputX"), subtract1_node.attr("output1D")], 2)
        div2_node = node.createDivNode(subtract2_node + ".output1D", self.soft_attr_cond)
        mult2_node = node.createMulNode(-1, div2_node + ".outputX")
        power_node = node.createPowNode(self.softSpeed_attr, mult2_node + ".outputX")
        mult3_node = node.createMulNode(self.soft_attr_cond, power_node + ".outputX")
        subtract3_node = node.createPlusMinusAverage1D(
            [plusTotalLength_node.attr("output1D"), mult3_node.attr("outputX")], 2
        )
        cond1_node = node.createConditionNode(
            self.soft_attr_cond, 0, 2, subtract3_node + ".output1D", plusTotalLength_node + ".output1D"
        )

        cond2_node = node.createConditionNode(
            mult1_node + ".outputX",
            subtract1_node + ".output1D",
            2,
            cond1_node + ".outColorR",
            mult1_node + ".outputX",
        )
        pm.connectAttr(cond2_node + ".outColorR", self.wristSoftIK + ".tz")

        # soft blend
        pc_node = pm.pointConstraint(self.wristSoftIK, self.ik_endpoint_refs["toe"], self.softblendLoc)
        node.createReverseNode(self.stretch_attr, pc_node + ".target[0].targetWeight")
        pm.connectAttr(str(self.stretch_attr), pc_node + ".target[1].targetWeight", f=True)

        # Stretch
        distance2_node = node.createDistNode(self.softblendLoc, self.wristSoftIK)
        mult4_node = node.createMulNode(distance2_node + ".distance", div1_node + ".outputX")
        toe_len_outputs = []
        for i, mulNode in enumerate([multJnt1_node, multJnt2_node, multJnt3_node, multJnt4_node]):
            div3_node = node.createDivNode(mulNode + ".outputX", plusTotalLength_node + ".output1D")

            mult5_node = node.createMulNode(mult4_node + ".outputX", div3_node + ".outputX")

            mult6_node = node.createMulNode(self.stretch_attr, mult5_node + ".outputX")

            toe_len_node = node.createPlusMinusAverage1D(
                [mulNode.attr("outputX"), mult6_node.attr("outputX")], 1
            )
            toe_len_outputs.append(toe_len_node + ".output1D")
            pm.connectAttr(toe_len_node + ".output1D", self.chain4bones[i + 1] + ".tx")

        # softIK 3 bones operators
        applyop.aimCns(
            self.aim_tra_foot,
            self.ik_endpoint_refs["foot"],
            axis="zx",
            wupType=4,
            wupVector=[1, 0, 0],
            wupObject=self.root_ctl,
            maintainOffset=False,
        )

        plusTotalLength_node = node.createPlusMinusAverage1D(
            [multJnt1_node.attr("outputX"), multJnt2_node.attr("outputX"), multJnt3_node.attr("outputX")]
        )
        subtract1_node = node.createPlusMinusAverage1D([plusTotalLength_node.attr("output1D"), self.soft_attr_cond], 2)
        distance1_node = node.createDistNode(self.ik_endpoint_refs["foot"], self.aim_tra_foot)
        div1_node = node.createDivNode(1.0, self.rig.global_ctl + ".sx")
        mult1_node = node.createMulNode(distance1_node + ".distance", div1_node + ".outputX")
        subtract2_node = node.createPlusMinusAverage1D([mult1_node.attr("outputX"), subtract1_node.attr("output1D")], 2)
        div2_node = node.createDivNode(subtract2_node + ".output1D", self.soft_attr_cond)
        mult2_node = node.createMulNode(-1, div2_node + ".outputX")
        power_node = node.createPowNode(self.softSpeed_attr, mult2_node + ".outputX")
        mult3_node = node.createMulNode(self.soft_attr_cond, power_node + ".outputX")
        subtract3_node = node.createPlusMinusAverage1D(
            [plusTotalLength_node.attr("output1D"), mult3_node.attr("outputX")], 2
        )
        cond1_node = node.createConditionNode(
            self.soft_attr_cond, 0, 2, subtract3_node + ".output1D", plusTotalLength_node + ".output1D"
        )
        cond2_node = node.createConditionNode(
            mult1_node + ".outputX", subtract1_node + ".output1D", 2, cond1_node + ".outColorR", mult1_node + ".outputX"
        )
        pm.connectAttr(cond2_node + ".outColorR", self.footSoftIK + ".tz")

        # soft blend
        # position soft blend
        pos_cns = pm.pointConstraint(
            self.footSoftIK,
            self.ik_endpoint_refs["foot"],
            self.softblendLocFoot,
        )
        node.createReverseNode(self.stretch_attr, pos_cns + ".target[0].targetWeight")
        pm.connectAttr(str(self.stretch_attr), pos_cns + ".target[1].targetWeight", f=True)

        # rotation follow
        pm.orientConstraint(
            self.ik_ctl,
            self.softblendLocFoot,
            maintainOffset=False,
        )

        # Foot stretch measures to the effective target: soft/raw foot target
        # plus footOffset local channels. D remains base length outside Foot
        # endpoint.
        distance2_node = node.createDistNode(self.ik3b_stretch_ref, self.footSoftIK)
        mult4_node = node.createMulNode(distance2_node + ".distance", div1_node + ".outputX")
        foot_len_outputs = []
        for i, mulNode in enumerate([multJnt1_node, multJnt2_node, multJnt3_node]):
            div3_node = node.createDivNode(mulNode + ".outputX", plusTotalLength_node + ".output1D")

            mult5_node = node.createMulNode(mult4_node + ".outputX", div3_node + ".outputX")

            mult6_node = node.createMulNode(self.stretch_attr, mult5_node + ".outputX")

            chain3_len_node = node.createPlusMinusAverage1D(
                [mulNode.attr("outputX"), mult6_node.attr("outputX")], 1
            )
            foot_len_outputs.append(chain3_len_node + ".output1D")
            cond_node = node.createConditionNode(
                self.ikEndpoint_att, 1, 0, chain3_len_node + ".output1D", mulNode + ".outputX"
            )
            pm.connectAttr(cond_node + ".outColorR", self.chain3bones[i + 1] + ".tx")

        # softIK 2 bones operators
        applyop.aimCns(
            self.aim_tra2,
            self.ik_endpoint_refs["ankle"],
            axis="zx",
            wupType=4,
            wupVector=[1, 0, 0],
            wupObject=self.root_ctl,
            maintainOffset=False,
        )

        plusTotalLength_node = node.createPlusMinusAverage1D(
            [multJnt1_node.attr("outputX"), multJnt2_node.attr("outputX")]
        )
        subtract1_node = node.createPlusMinusAverage1D([plusTotalLength_node.attr("output1D"), self.soft_attr_cond], 2)
        distance1_node = node.createDistNode(self.ik_endpoint_refs["ankle"], self.aim_tra2)
        div1_node = node.createDivNode(1, self.rig.global_ctl + ".sx")
        mult1_node = node.createMulNode(distance1_node + ".distance", div1_node + ".outputX")
        subtract2_node = node.createPlusMinusAverage1D([mult1_node.attr("outputX"), subtract1_node.attr("output1D")], 2)
        div2_node = node.createDivNode(subtract2_node + ".output1D", self.soft_attr_cond)
        mult2_node = node.createMulNode(-1, div2_node + ".outputX")
        power_node = node.createPowNode(self.softSpeed_attr, mult2_node + ".outputX")
        mult3_node = node.createMulNode(self.soft_attr_cond, power_node + ".outputX")
        subtract3_node = node.createPlusMinusAverage1D(
            [plusTotalLength_node.attr("output1D"), mult3_node.attr("outputX")], 2
        )
        cond1_node = node.createConditionNode(
            self.soft_attr_cond, 0, 2, subtract3_node + ".output1D", plusTotalLength_node + ".output1D"
        )
        cond2_node = node.createConditionNode(
            mult1_node + ".outputX", subtract1_node + ".output1D", 2, cond1_node + ".outColorR", mult1_node + ".outputX"
        )
        pm.connectAttr(cond2_node + ".outColorR", self.ankleSoftIK + ".tz")

        # soft blend
        pos_cns = pm.pointConstraint(
            self.ankleSoftIK,
            self.ik_endpoint_refs["ankle"],
            self.softblendLoc2,
        )
        node.createReverseNode(self.stretch_attr, pos_cns + ".target[0].targetWeight")
        pm.connectAttr(str(self.stretch_attr), pos_cns + ".target[1].targetWeight", f=True)

        pm.orientConstraint(
            self.ik_ctl,
            self.softblendLoc2,
            maintainOffset=False,
        )

        # Ankle stretch measures to the effective target: soft/raw ankle target
        # plus ankleOffset local channels. C and D remain base length outside
        # longer endpoints.
        distance2_node = node.createDistNode(self.ik2b_stretch_ref, self.ankleSoftIK)
        mult4_node = node.createMulNode(distance2_node + ".distance", div1_node + ".outputX")
        ankle_len_outputs = []
        for i, mulNode in enumerate([multJnt1_node, multJnt2_node]):
            div3_node = node.createDivNode(mulNode + ".outputX", plusTotalLength_node + ".output1D")

            mult5_node = node.createMulNode(mult4_node + ".outputX", div3_node + ".outputX")

            mult6_node = node.createMulNode(self.stretch_attr, mult5_node + ".outputX")

            ankle_len_node = node.createPlusMinusAverage1D(
                [mulNode.attr("outputX"), mult6_node.attr("outputX")], 1
            )
            ankle_len_outputs.append(ankle_len_node + ".output1D")

        active_a_len = self._select_endpoint_scalar(ankle_len_outputs[0], foot_len_outputs[0], toe_len_outputs[0])
        active_b_len = self._select_endpoint_scalar(ankle_len_outputs[1], foot_len_outputs[1], toe_len_outputs[1])
        active_c_len = self._select_endpoint_scalar(multJnt3_node + ".outputX", foot_len_outputs[2], toe_len_outputs[2])
        active_d_len = self._select_endpoint_scalar(multJnt4_node + ".outputX", multJnt4_node + ".outputX", toe_len_outputs[3])

        pm.connectAttr(active_a_len, self.chain2bones[1] + ".tx")
        pm.connectAttr(active_b_len, self.chain2bones[2] + ".tx")

        # IK/FK connections
        for i, x in enumerate(self.fk_ctl):
            pm.parentConstraint(x, self.legBonesFK[i], mo=True)

        for i, x in enumerate([self.chain2bones[0], self.chain2bones[1]]):
            pm.parentConstraint(x, self.legBonesIK[i], mo=True)

        pm.parentConstraint(
            self.wik_ctl_02,
            self.legBonesIK[2],
            maintainOffset=True,
            skipTranslate=["x", "y", "z"]
        )
        pm.parentConstraint(
            self.wik_ctl_01,
            self.legBonesIK[3],
            maintainOffset=True,
            skipTranslate=["x", "y", "z"]
        )

        pm.connectAttr(active_b_len, self.legBonesIK[2] + ".tx")
        pm.connectAttr(active_c_len, self.legBonesIK[3] + ".tx")
        pm.connectAttr(active_d_len, self.legBonesIK[4] + ".tx")

        # foot twist roll
        pm.orientConstraint(self.ik_ref, self.legBonesIK[-1], mo=True)

        for i, x in enumerate(self.legBones):
            node.createPairBlend(self.legBonesFK[i], self.legBonesIK[i], self.blend_att, 1, x)

        # Twist references ----------------------------------------

        self.ikhArmRef, self.tmpCrv = applyop.splineIK(
            self.getName("legRollRef"), self.rollRef, parent=self.root, cParent=self.legBones[0]
        )

        initRound = 0.001
        multVal = 1

        multTangent_node = node.createMulNode(self.roundnessKnee_att, multVal)
        add_node = node.createAddNode(multTangent_node + ".outputX", initRound)
        pm.connectAttr(add_node + ".output", str(self.tws1_rot) + ".sx")
        for x in ["translate"]:
            pm.connectAttr(str(self.knee_ctl) + "." + x, str(self.tws1_loc) + "." + x)
        for x in "xy":
            pm.connectAttr(str(self.knee_ctl) + "." + "r" + x, str(self.tws1_loc) + "." + "r" + x)

        multTangent_node = node.createMulNode(self.roundnessAnkle_att, multVal)
        add_node = node.createAddNode(multTangent_node + ".outputX", initRound)
        pm.connectAttr(add_node + ".output", str(self.tws2_rot) + ".sx")
        for x in ["translate"]:
            pm.connectAttr(str(self.ankle_ctl) + "." + x, str(self.tws2_loc) + "." + x)
        for x in "xy":
            pm.connectAttr(str(self.ankle_ctl) + "." + "r" + x, str(self.tws2_loc) + "." + "r" + x)

        multTangent_node = node.createMulNode(self.roundnessFoot_att, multVal)
        add_node = node.createAddNode(multTangent_node + ".outputX", initRound)
        pm.connectAttr(add_node + ".output", str(self.tws3_rot) + ".sx")
        for x in ["translate"]:
            pm.connectAttr(str(self.foot_ctl) + "." + x, str(self.tws3_loc) + "." + x)
        for x in "xy":
            pm.connectAttr(str(self.foot_ctl) + "." + "r" + x, str(self.tws3_loc) + "." + "r" + x)

        # Volume -------------------------------------------
        distA_node = node.createDistNode(self.tws0_loc, self.tws1_loc)
        distB_node = node.createDistNode(self.tws1_loc, self.tws2_loc)
        distC_node = node.createDistNode(self.tws2_loc, self.tws3_loc)
        distD_node = node.createDistNode(self.tws3_loc, self.tws4_loc)
        add_node = node.createAddNode(distA_node + ".distance", distB_node + ".distance")
        add_node2 = node.createAddNode(distC_node + ".distance", add_node + ".output")
        add_node3 = node.createAddNode(distD_node + ".distance", add_node2 + ".output")
        div_node = node.createDivNode(add_node3 + ".output", self.root_ctl.attr("sx"))

        # comp scaling
        dm_node = node.createDecomposeMatrixNode(self.root.attr("worldMatrix"))

        div_node2 = node.createDivNode(div_node + ".outputX", dm_node + ".outputScaleX")

        self.volDriver_att = div_node2 + ".outputX"

        # Flip Offset ----------------------------------------
        pm.connectAttr(str(self.ankleFlipOffset_att), str(self.tws2_loc) + ".rz")
        pm.connectAttr(str(self.kneeFlipOffset_att), str(self.tws1_loc) + ".rz")
        pm.connectAttr(str(self.footFlipOffset_att), str(self.tws3_loc) + ".rz")

        # Divisions ----------------------------------------
        percents = self.division_percents

        for i, div_cns in enumerate(self.div_cns):
            subdiv = 45
            perc = percents[i]

            # Roll
            cts = [
                self.tws0_rot,
                self.tws1_rot,
                self.tws2_rot,
                self.tws3_rot,
                self.tws4_rot,
            ]

            o_node = applyop.gear_rollsplinekine_op(div_cns, cts, perc, subdiv)

            pm.connectAttr(str(self.resample_att), o_node + ".resample")
            pm.connectAttr(str(self.absolute_att), o_node + ".absolute")

            # Squash n Stretch
            o_node = applyop.gear_squashstretch2_op(
                div_cns,
                None,
                pm.getAttr(self.volDriver_att),
                "x"
            )

            pm.connectAttr(str(self.volume_att), o_node + ".blend")
            pm.connectAttr(str(self.volDriver_att), o_node + ".driver")
            pm.connectAttr(str(self.st_att[i]), o_node + ".stretch")
            pm.connectAttr(str(self.sq_att[i]), o_node + ".squash")
        # Visibilities -------------------------------------
        # fk
        fkvis_node = node.createReverseNode(self.blend_att)
        for ctrl in self.fk_ctl:
            for shp in ctrl.getShapes():
                pm.connectAttr(fkvis_node + ".outputX", str(shp) + ".visibility")
        # ik
        for ctrl in [self.ik_ctl, self.wik_ctl_01, self.wik_ctl_02, self.upv_ctl, self.line_ref]:
            for shp in ctrl.getShapes():
                pm.connectAttr(str(self.blend_att), str(shp) + ".visibility")

        # setup leg o_node scale compensate
        pm.connectAttr(self.rig.global_ctl + ".scale", self.setup + ".scale")

        # match IK/FK ref
        for leg_bone, match_off in zip(
            self.legBones,
            [
                self.match_fk0_off,
                self.match_fk1_off,
                self.match_fk2_off,
                self.match_fk3_off,
                self.match_fk4_off,
            ],
        ):
            pm.parentConstraint(leg_bone, match_off, mo=False)

        for name, leg_bone in zip(self.ik_endpoint_names, self.legBones[2:5]):
            pm.parentConstraint(leg_bone, self.match_ik_endpoint_refs[name], mo=True)

        pm.parentConstraint(self.legBones[3], self.match_foot_offset, mo=True)
        pm.parentConstraint(self.legBones[2], self.match_ankle_offset, mo=True)

        ik_mth_cns = pm.parentConstraint(
            self.match_ik_endpoint_refs["ankle"],
            self.match_ik_endpoint_refs["foot"],
            self.match_ik_endpoint_refs["toe"],
            self.match_ik,
            mo=False,
        )
        self._connect_endpoint_condition(0, ik_mth_cns + ".target[0].targetWeight")
        self._connect_endpoint_condition(1, ik_mth_cns + ".target[1].targetWeight")
        self._connect_endpoint_condition(2, ik_mth_cns + ".target[2].targetWeight")


    def verifyAlignmentAccuracy(self, jnts, guides, degree=10.0):
        # type: (Sequence[Vector3], Sequence[Vector3], float) -> bool
        """
        Validate if the joint is in the same direction as the guides.


        Args:
            jnts (List[float]): The joint world position
            guides (List[float]): The guides to validate
            degree (float): The degree of tolerance

        Returns:
            Bool: True if the joint is in the same direction as the guides
        Raises:
            ValueError: If the input lists have different lengths or if degree is negative
        """

        if len(jnts) != len(guides):
            raise ValueError("jnts and guides must have the same number of positions.")

        if len(jnts) < 2:
            raise ValueError("At least 2 positions are required.")

        if degree < 0:
            raise ValueError("degree must be non-negative.")

        for j0, j1, g0, g1 in zip(jnts, jnts[1:], guides, guides[1:]):
            jointVec = om2.MVector(
                j1[0] - j0[0],
                j1[1] - j0[1],
                j1[2] - j0[2],
            )

            guideVec = om2.MVector(
                g1[0] - g0[0],
                g1[1] - g0[1],
                g1[2] - g0[2],
            )

            if jointVec.length() == 0 or guideVec.length() == 0:
                return False

            jointVec.normalize()
            guideVec.normalize()

            angle = math.degrees(jointVec.angle(guideVec))

            if angle > degree:
                return False

        return True

    # =====================================================
    # CONNECTOR
    # =====================================================

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.deform_anchor_drivers["root"]
        self.relatives["knee"] = self.deform_anchor_drivers["knee"]
        self.relatives["ankle"] = self.deform_anchor_drivers["ankle"]
        self.relatives["foot"] = self.deform_anchor_drivers["foot"]
        self.relatives["toe"] = self.deform_anchor_drivers["toe"]
        self.relatives["eff"] = self.deform_anchor_drivers["toe"]

        self.controlRelatives["root"] = self.fk0_ctl
        self.controlRelatives["knee"] = self.fk1_ctl
        self.controlRelatives["ankle"] = self.fk2_ctl
        self.controlRelatives["foot"] = self.ik_ctl
        self.controlRelatives["toe"] = self.ik_ctl
        self.controlRelatives["eff"] = self.fk4_ctl

        self.jointRelatives["root"] = self.joint_indices["root"]
        self.jointRelatives["knee"] = self.joint_indices["knee"]
        self.jointRelatives["ankle"] = self.joint_indices["ankle"]
        self.jointRelatives["foot"] = self.joint_indices["foot"]
        self.jointRelatives["toe"] = self.joint_indices["toe"]
        self.jointRelatives["eff"] = self.joint_indices["end"]

        self.aliasRelatives["eff"] = "tip"

    # standard connection definition.
    def connect_standard(self):
        self.parent.addChild(self.root)

        # Set the Ik Reference
        self.connectRef(self.settings["ikrefarray"], self.ik_cns)
        if self.settings["upvrefarray"]:
            self.connectRef("Auto," + self.settings["upvrefarray"], self.upv_cns, True)
