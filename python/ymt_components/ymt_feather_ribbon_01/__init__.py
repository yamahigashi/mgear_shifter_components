"""Feather ribbon component for ymt_birdwing_3jnt_01."""

from __future__ import annotations

import importlib
from contextlib import suppress
from typing import TYPE_CHECKING, Optional, TypedDict

import maya.cmds as cmds

try:
    pm = importlib.import_module("mgear.pymaya")
except ImportError:
    pm = importlib.import_module("pymel.core")
try:
    datatypes = importlib.import_module("mgear.pymaya.datatypes")
except ImportError:
    datatypes = importlib.import_module("pymel.core.datatypes")

from mgear.core import attribute, primitive, transform
from mgear.shifter import component

import ymt_shifter_utility as ymt_util

from . import detail_config

if TYPE_CHECKING:
    from ymt_shifter_utility.type_protocols import PymelNode, VectorLike


MAYA_2025_API_VERSION = 20250000
PARENT_COMPONENT_TYPE = "ymt_birdwing_3jnt_01"


class DetailSpec(TypedDict):
    row: str
    section: int
    col: int
    anchor_layer: int
    u: float
    v: float
    span: int
    local: float
    position: VectorLike


class DriverEntry(TypedDict):
    kind: str
    index: int
    weight: float


class Component(component.Main):
    """Shifter component class."""

    placement_modes = ("surface", "fixed")
    anchor_names = ("root", "elbow", "wrist", "hand")
    surface_segment_subdivisions = 4

    def addObjects(self) -> None:
        """Add controls, optional ribbon surface, and detail feather outputs."""
        self.WIP = self.options["mode"]
        self.ctl_size = self.size * float(self.settings["ctlSize"]) * 0.15
        self.placement_mode = self._parse_placement_mode(self.settings["placementMode"])
        self.row_names = self._parse_row_names(self.settings["rowNames"])
        self.row_counts = self._parse_row_counts(self.settings["rowCounts"], self.row_names)
        self.row_u_ranges = self._parse_row_u_ranges(self.settings["rowURanges"], self.row_names)
        if "lowerEdgeOffsets" not in self.settings:
            raise RuntimeError("ymt_feather_ribbon_01 requires the lowerEdgeOffsets setting.")
        self.lower_edge_profiles = self._parse_lower_edge_profiles(
            self.settings["lowerEdgeOffsets"],
            self.row_names,
        )
        self.anchor_positions = self._get_anchor_positions()
        self.anchor_segment_lengths = self._get_anchor_segment_lengths()
        self.anchor_total_length = sum(self.anchor_segment_lengths)
        self.span_axis = self._get_parent_span_axis()
        self.wing_normal = self._get_parent_blade_normal()
        self.lower_axis = self._get_parent_blade_lower_axis()
        self.anchor_offsets = self._collect_anchor_offsets()

        self.driver_root = primitive.addTransform(self.root, self.getName("drivers"), transform.getTransform(self.root))
        self.detail_root = primitive.addTransform(self.root, self.getName("details"), transform.getTransform(self.root))
        self.no_transform = primitive.addTransform(
            self.root, self.getName("noTransform"), transform.getTransform(self.root)
        )
        self.no_transform.attr("inheritsTransform").set(False)
        ymt_util.setKeyableAttributesDontLockVisibility([self.driver_root, self.detail_root, self.no_transform], [])
        self.no_transform.attr("visibility").set(False)

        self.anchor_npos = []
        self.anchor_ctls = []
        self._add_anchor_controls()

        self.curl_npos = []
        self.curl_offset_npos = []
        self.curl_ctls = []
        self.curl_deforms = []
        self._add_curl_controls()

        self.detail_specs = self._collect_detail_specs()
        self.detail_npos = []
        self.detail_aim_npos = []
        self.detail_ctls = []
        self._add_detail_controls()

        self.sliding_surface = None
        self.surface_skin_joints = []
        self.anchor_surface_skin_joints = []
        self.curl_surface_skin_joints = []
        if self.placement_mode == "surface":
            self._add_surface()

    def addOperators(self) -> None:
        """Connect driver rotations and optional rivets."""
        self._ensure_rotation_driver_plugin()
        self._connect_curl_spaces()
        self._connect_curl_deforms()
        self._connect_detail_rotations()
        self._connect_curl_aims()
        if self.placement_mode == "surface":
            self._connect_surface_rivets()

    def setRelation(self) -> None:
        """Set guide-to-rig relations."""
        self.relatives["root"] = self.anchor_ctls[0][0]
        self.controlRelatives["root"] = self.anchor_ctls[0][0]
        self.aliasRelatives["root"] = "featherRoot"

        for index, ctl in enumerate(self.detail_ctls):
            name = "detail%s" % index
            self.relatives[name] = ctl
            self.controlRelatives[name] = ctl
            self.aliasRelatives[name] = name

    def addConnection(self) -> None:
        self.connections["standard"] = self.connect_standard
        self.connections["ymt_birdwing_3jnt_01"] = self.connect_ymt_birdwing_3jnt_01

    def connect_standard(self) -> None:
        self.parent.addChild(self.root)

    def connect_ymt_birdwing_3jnt_01(self) -> None:
        self.connect_standard()
        parent_comp = getattr(self, "parent_comp", None)
        if parent_comp is None or not hasattr(parent_comp, "get_feather_ribbon_refs"):
            raise RuntimeError("ymt_feather_ribbon_01 requires a ymt_birdwing_3jnt_01 parent component.")

        refs = parent_comp.get_feather_ribbon_refs()
        pm.pointConstraint(refs["root"], self.anchor_npos[0][0], mo=True)
        cns = pm.orientConstraint(refs["root_ctl"], self.anchor_npos[0][0], mo=True)
        pm.setAttr(cns.attr("interpType"), 0)  # no-flip
        for anchor_name, anchor_npos in zip(self.anchor_names[1:], self.anchor_npos[1:]):
            pm.parentConstraint(refs[anchor_name], anchor_npos[0], mo=True)
        self._connect_curl_rotations(refs)

    def _add_anchor_controls(self) -> None:
        for anchor_index, name in enumerate(self.anchor_names):
            parent = self.driver_root
            tag_parent = self.parentCtlTag
            anchor_npos = []
            anchor_ctls = []
            for layer_index, _offset in enumerate(self.anchor_offsets):
                matrix = transform.getTransformFromPos(self._anchor_layer_position(layer_index, anchor_index))
                npo = primitive.addTransform(parent, self.getName("feather_%s_%02d_npo" % (name, layer_index)), matrix)
                ctl = self.addCtl(
                    npo,
                    "feather_%s_%02d_ctl" % (name, layer_index),
                    matrix,
                    self.color_fk,
                    "cube",
                    w=self.ctl_size * 1.6,
                    h=self.ctl_size,
                    d=self.ctl_size,
                    tp=tag_parent,
                )
                attribute.setKeyableAttributes(ctl)
                attribute.setInvertMirror(ctl, ["tx", "ty", "tz"])
                anchor_npos.append(npo)
                anchor_ctls.append(ctl)
                parent = ctl
                tag_parent = ctl
            self.anchor_npos.append(anchor_npos)
            self.anchor_ctls.append(anchor_ctls)

    def _add_curl_controls(self) -> None:
        for index in range(3):
            basis_matrix = self._curl_basis_matrix(index)
            offset_matrix = self._curl_offset_matrix(index)
            npo = primitive.addTransform(self.driver_root, self.getName("curl%s_npo" % index), basis_matrix)
            offset_npo = primitive.addTransform(npo, self.getName("curl%s_offset_npo" % index), offset_matrix)
            ctl = self.addCtl(
                offset_npo,
                "curl%s_ctl" % index,
                offset_matrix,
                self.color_ik,
                "sphere",
                w=self.ctl_size,
                tp=self.anchor_ctls[min(index + 1, len(self.anchor_ctls) - 1)][0],
            )
            deform = primitive.addTransform(offset_npo, self.getName("curl%s_deform" % index), offset_matrix)
            attribute.setKeyableAttributes(ctl, ["tx", "ty", "tz"])
            attribute.setInvertMirror(ctl, ["tx", "ty", "tz"])
            self.curl_npos.append(npo)
            self.curl_offset_npos.append(offset_npo)
            self.curl_ctls.append(ctl)
            self.curl_deforms.append(deform)

    def _add_detail_controls(self) -> None:
        for spec in self.detail_specs:
            detail_name = self._detail_name(spec)
            matrix = transform.getTransformFromPos(spec["position"])
            npo = primitive.addTransform(self.detail_root, self.getName("%s_npo" % detail_name), matrix)
            aim_npo = primitive.addTransform(npo, self.getName("%s_aim_npo" % detail_name), matrix)
            ctl = self.addCtl(
                aim_npo,
                "%s_ctl" % detail_name,
                matrix,
                self.color_fk,
                "sphere",
                w=self.ctl_size,
                tp=self.curl_ctls[min(spec["span"], len(self.curl_ctls) - 1)],
            )
            attribute.setKeyableAttributes(ctl)
            attribute.setInvertMirror(ctl, ["tx", "ty", "tz"])
            self.detail_npos.append(npo)
            self.detail_aim_npos.append(aim_npo)
            self.detail_ctls.append(ctl)
            if self.settings["addJoints"]:
                self.jnt_pos.append([ctl, detail_name])

    def _add_surface(self) -> None:
        surface_u_values = self._surface_u_values()
        surface_offsets = self._surface_offsets()
        surface = cmds.nurbsPlane(
            n=self.getName("ribbonSurface"),
            ch=False,
            d=1,
            u=len(surface_u_values) - 1,
            v=len(surface_offsets) - 1,
        )[0]
        surface_shape = self._surface_shape_name(surface)
        for u_index, u in enumerate(surface_u_values):
            for v_index, offset in enumerate(surface_offsets):
                cmds.xform(
                    "%s.cv[%s][%s]" % (surface_shape, u_index, v_index),
                    ws=True,
                    t=self._point_tuple(self._position_from_u_and_offset(u, offset)),
                )
        self.sliding_surface = pm.PyNode(surface)
        pm.parent(self.sliding_surface, self.no_transform)
        # self.sliding_surface.attr("visibility").set(False)
        ymt_util.setKeyableAttributesDontLockVisibility(self.sliding_surface, [])

        self._add_surface_skin_joints()
        influence_names = [self._node_name(joint) for joint in self.surface_skin_joints]
        skin = cmds.skinCluster(
            *influence_names,
            self._node_name(self.sliding_surface),
            tsb=True,
            n=self.getName("ribbonSurface_skinCluster"),
        )[0]
        self.surface_skin_cluster = pm.PyNode(skin)
        self._set_surface_skin_weights(skin)

    def _add_surface_skin_joints(self) -> None:
        self.anchor_surface_skin_joints = []
        self.curl_surface_skin_joints = []
        for anchor_ctls in self.anchor_ctls:
            anchor_joints = []
            for ctl in anchor_ctls:
                joint = self._add_surface_skin_joint(ctl)
                anchor_joints.append(joint)
                self.surface_skin_joints.append(joint)
            self.anchor_surface_skin_joints.append(anchor_joints)

        for deform in self.curl_deforms:
            joint = self._add_surface_skin_joint(deform)
            self.curl_surface_skin_joints.append(joint)
            self.surface_skin_joints.append(joint)

    def _add_surface_skin_joint(self, ctl: PymelNode) -> PymelNode:
        joint = primitive.addJoint(
            ctl,
            self.getName("%s_surfaceSkin_jnt" % self._node_name(ctl).replace(self.getName(""), "")),
            transform.getTransform(ctl),
            vis=False,
        )
        ymt_util.setKeyableAttributesDontLockVisibility(joint, [])
        return joint

    def _set_surface_skin_weights(self, skin: str) -> None:
        surface = self._node_name(self.sliding_surface)
        surface_shape = self._surface_shape_name(surface)
        u_count, v_count = self._surface_cv_counts(surface)
        surface_u_values = self._surface_u_values()
        surface_offsets = self._surface_offsets()
        self._validate_surface_topology(u_count, v_count, surface_u_values, surface_offsets)
        influence_names = self._skin_influence_names(skin)
        influence_by_node = self._skin_influence_names_by_node(skin)
        with suppress(RuntimeError):
            cmds.setAttr(skin + ".normalizeWeights", 0)

        for u_index in range(u_count):
            u = surface_u_values[u_index]
            for v_index in range(v_count):
                offset = surface_offsets[v_index]
                component = "%s.cv[%s][%s]" % (surface_shape, u_index, v_index)
                weights = dict.fromkeys(influence_names, 0.0)
                for joint, weight in self._surface_anchor_weight_entries(offset, u):
                    weights[influence_by_node[self._node_name(joint)]] = weight
                curl_joint, curl_weight = self._surface_curl_weight_entry(u, offset)
                weights[influence_by_node[self._node_name(curl_joint)]] = curl_weight
                total = sum(weights.values())
                if total <= 0.0:
                    raise RuntimeError("ymt_feather_ribbon_01 generated zero total skin weight for %s." % component)
                normalized = [(name, weight / total) for name, weight in weights.items()]
                cmds.skinPercent(skin, component, transformValue=normalized, normalize=False)

        with suppress(RuntimeError):
            cmds.setAttr(skin + ".normalizeWeights", 1)
            cmds.skinCluster(skin, edit=True, forceNormalizeWeights=True)
        self._validate_surface_skin_weights(
            skin, surface_shape, surface_u_values, v_count, surface_offsets, influence_by_node
        )

    def _validate_surface_skin_weights(
        self,
        skin: str,
        surface_shape: str,
        surface_u_values: list[float],
        v_count: int,
        surface_offsets: list[float],
        influence_by_node: dict[str, str],
    ) -> None:
        v_index = max(v_count - 1, 0)
        offset = surface_offsets[v_index]
        for segment_index, joint in enumerate(self.curl_surface_skin_joints):
            u = self._u_from_span_local(segment_index, 0.5)
            u_index = min(
                range(len(surface_u_values)),
                key=lambda index: abs(surface_u_values[index] - u),
            )
            expected = self._surface_curl_weight_for_u(surface_u_values[u_index], offset)
            if expected <= 0.05:
                continue
            component = "%s.cv[%s][%s]" % (surface_shape, u_index, v_index)
            influence = influence_by_node[self._node_name(joint)]
            actual = cmds.skinPercent(skin, component, query=True, transform=influence)
            if isinstance(actual, (list, tuple)):
                actual = actual[0] if actual else 0.0
            if float(actual) < expected * 0.5:
                raise RuntimeError(
                    "ymt_feather_ribbon_01 failed to assign curl skin weight: "
                    "%s expected %.3f on %s, got %.3f." % (influence, expected, component, float(actual))
                )

    def _surface_cv_counts(self, surface: str) -> tuple[int, int]:
        shape = self._surface_shape_name(surface)
        return (
            int(cmds.getAttr(shape + ".spansU")) + int(cmds.getAttr(shape + ".degreeU")),
            int(cmds.getAttr(shape + ".spansV")) + int(cmds.getAttr(shape + ".degreeV")),
        )

    def _validate_surface_topology(
        self,
        u_count: int,
        v_count: int,
        surface_u_values: list[float],
        surface_offsets: list[float],
    ) -> None:
        if u_count != len(surface_u_values):
            raise RuntimeError(
                "ymt_feather_ribbon_01 ribbon surface requires %s U CVs for fixed anchor/curl columns, got %s."
                % (len(surface_u_values), u_count)
            )
        if v_count != len(surface_offsets):
            raise RuntimeError(
                "ymt_feather_ribbon_01 ribbon surface requires %s V CVs for fixed offset rows, got %s."
                % (len(surface_offsets), v_count)
            )

    def _surface_shape_name(self, surface: str) -> str:
        shapes = cmds.listRelatives(surface, shapes=True, fullPath=True) or []
        if not shapes:
            raise RuntimeError("ymt_feather_ribbon_01 could not find the ribbon surface shape.")
        return shapes[0]

    def _skin_influence_names(self, skin: str) -> list[str]:
        return [self._node_name(influence) for influence in cmds.skinCluster(skin, query=True, influence=True)]

    def _skin_influence_names_by_node(self, skin: str) -> dict[str, str]:
        mapping = {}
        for influence in cmds.skinCluster(skin, query=True, influence=True):
            influence_name = self._node_name(influence)
            long_names = cmds.ls(influence_name, long=True) or []
            names = {influence_name}
            names.update(long_names)
            for long_name in long_names:
                names.update(cmds.ls(long_name, shortNames=True) or [])
            for name in names:
                mapping[name] = influence_name
        for joint in self.surface_skin_joints:
            joint_name = self._node_name(joint)
            if joint_name not in mapping:
                long_names = cmds.ls(joint_name, long=True) or []
                for long_name in long_names:
                    if long_name in mapping:
                        mapping[joint_name] = mapping[long_name]
                        break
            if joint_name not in mapping:
                raise RuntimeError("ymt_feather_ribbon_01 could not resolve skin influence for '%s'." % joint_name)
        return mapping

    def _surface_anchor_weight_entries(self, offset: float, u: float) -> list[tuple[PymelNode, float]]:
        anchor_entries = self._anchor_weight_entries_for_u(u)
        layer_entries = self._anchor_layer_weight_entries_for_offset(offset)
        curl_weight = self._surface_curl_weight_for_u(u, offset)
        anchor_weight = max(0.0, 1.0 - curl_weight)
        entries = []
        for anchor_index, anchor_value in anchor_entries:
            for layer_index, layer_value in layer_entries:
                joint = self.anchor_surface_skin_joints[anchor_index][layer_index]
                entries.append((joint, anchor_value * layer_value * anchor_weight))
        return entries

    def _surface_curl_weight_entry(self, u: float, offset: float) -> tuple[PymelNode, float]:
        if not self.curl_surface_skin_joints:
            raise RuntimeError("ymt_feather_ribbon_01 curl surface skin joints were not properly initialized.")
        span, _local = self._span_local_from_u(u)
        segment_index = min(max(span, 0), len(self.curl_surface_skin_joints) - 1)
        return self.curl_surface_skin_joints[segment_index], self._surface_curl_weight_for_u(u, offset)

    def _surface_curl_weight_for_u(self, u: float, offset: float) -> float:
        max_offset = max(self.anchor_offsets)
        if max_offset <= 0.0:
            return 0.0
        _span, local = self._span_local_from_u(u)
        segment_weight = 1.0 - abs((local * 2.0) - 1.0)
        offset_weight = max(0.0, min(1.0, offset / max_offset))
        return max(0.0, min(1.0, offset_weight * segment_weight * 0.65))

    def _anchor_weight_entries_for_u(self, u: float) -> list[tuple[int, float]]:
        span, local = self._span_local_from_u(u)
        start_anchor = min(span, len(self.anchor_names) - 1)
        end_anchor = min(span + 1, len(self.anchor_names) - 1)
        if local <= 0.001 or start_anchor == end_anchor:
            return [(start_anchor, 1.0)]
        if local >= 0.999:
            return [(end_anchor, 1.0)]
        return [(start_anchor, 1.0 - local), (end_anchor, local)]

    def _anchor_layer_weight_entries_for_offset(self, offset: float) -> list[tuple[int, float]]:
        if len(self.anchor_offsets) == 1:
            return [(0, 1.0)]
        if offset <= self.anchor_offsets[0]:
            return [(0, 1.0)]
        for index, start in enumerate(self.anchor_offsets[:-1]):
            end = self.anchor_offsets[index + 1]
            if start <= offset <= end:
                ratio = (offset - start) / max(end - start, 0.001)
                return [(index, 1.0 - ratio), (index + 1, ratio)]
        return [(len(self.anchor_offsets) - 1, 1.0)]

    def _connect_surface_rivets(self) -> None:
        for npo in self.detail_npos:
            rivets = ymt_util.apply_rivet_constrain_to_selected(self.sliding_surface, npo)
            rivet = pm.PyNode(rivets[0])
            pm.parent(rivet, self.no_transform, relative=True)
            pm.pointConstraint(rivet, npo, mo=True)
            ymt_util.setKeyableAttributesDontLockVisibility(rivet, [])

    def _connect_curl_spaces(self) -> None:
        for segment_index, npo in enumerate(self.curl_npos):
            self._connect_curl_translate_matrix(segment_index, npo)

    def _connect_curl_rotations(self, refs: dict[str, object]) -> None:
        for segment_index, npo in enumerate(self.curl_npos):
            start_name = self.anchor_names[segment_index]
            end_name = self.anchor_names[segment_index + 1]
            self._connect_curl_rotation_blend(segment_index, npo, refs[start_name], refs[end_name])

    def _connect_curl_deforms(self) -> None:
        for ctl, deform in zip(self.curl_ctls, self.curl_deforms):
            for axis in "XYZ":
                cmds.connectAttr(
                    "%s.translate%s" % (self._node_name(ctl), axis),
                    "%s.translate%s" % (self._node_name(deform), axis),
                    force=True,
                )

    def _connect_curl_translate_matrix(self, segment_index: int, npo: PymelNode) -> None:
        lower_midpoint = self._create_midpoint_translate_node(
            self.anchor_ctls[segment_index][-1],
            self.anchor_ctls[segment_index + 1][-1],
            "curl%sLowerMid" % segment_index,
        )
        translate_matrix = self._create_compose_translate_node(
            lower_midpoint + ".output3D",
            "curl%sTranslateMatrix" % segment_index,
        )

        local_translate_matrix = cmds.createNode(
            "multMatrix", name=self.getName("curl%s_translateLocalMatrix" % segment_index)
        )
        cmds.connectAttr(translate_matrix + ".outputMatrix", local_translate_matrix + ".matrixIn[0]", force=True)
        cmds.connectAttr(
            self._node_name(npo) + ".parentInverseMatrix[0]",
            local_translate_matrix + ".matrixIn[1]",
            force=True,
        )

        translate_decompose = cmds.createNode(
            "decomposeMatrix", name=self.getName("curl%s_translateDecomposeMatrix" % segment_index)
        )
        cmds.connectAttr(local_translate_matrix + ".matrixSum", translate_decompose + ".inputMatrix", force=True)
        cmds.connectAttr(translate_decompose + ".outputTranslate", self._node_name(npo) + ".translate", force=True)

    def _connect_curl_rotation_blend(
        self,
        segment_index: int,
        npo: PymelNode,
        start_ref: object,
        end_ref: object,
    ) -> None:
        constraint = cmds.orientConstraint(
            self._node_name(start_ref),
            self._node_name(end_ref),
            self._node_name(npo),
            maintainOffset=False,
            name=self.getName("curl%s_rotate_orientCns" % segment_index),
        )[0]
        cmds.setAttr(constraint + ".interpType", 0)  # no-flip
        aliases = cmds.orientConstraint(constraint, query=True, weightAliasList=True) or []
        if len(aliases) != 2:
            raise RuntimeError(
                f"ymt_feather_ribbon_01 failed to create curl rotation anchor blend. Constraint: {constraint}, aliases: {aliases}"
            )
        cmds.setAttr("%s.%s" % (constraint, aliases[0]), 0.5)
        cmds.setAttr("%s.%s" % (constraint, aliases[1]), 0.5)

    def _create_midpoint_translate_node(self, a: PymelNode, b: PymelNode, name: str) -> str:
        decompose_a = self._create_decompose_matrix(self._node_name(a) + ".worldMatrix[0]", self.getName(name + "A_dm"))
        decompose_b = self._create_decompose_matrix(self._node_name(b) + ".worldMatrix[0]", self.getName(name + "B_dm"))
        midpoint = cmds.createNode("plusMinusAverage", name=self.getName(name + "_pma"))
        cmds.setAttr(midpoint + ".operation", 3)
        cmds.connectAttr(decompose_a + ".outputTranslate", midpoint + ".input3D[0]", force=True)
        cmds.connectAttr(decompose_b + ".outputTranslate", midpoint + ".input3D[1]", force=True)
        return midpoint

    def _create_compose_translate_node(self, translate_attr: str, name: str) -> str:
        compose = cmds.createNode("composeMatrix", name=self.getName(name + "_cm"))
        cmds.connectAttr(translate_attr, compose + ".inputTranslate", force=True)
        return compose

    def _create_decompose_matrix(self, matrix_attr: str, name: str) -> str:
        decompose = cmds.createNode("decomposeMatrix", name=name)
        cmds.connectAttr(matrix_attr, decompose + ".inputMatrix", force=True)
        return decompose

    def _connect_detail_rotations(self) -> None:
        decomposers_by_anchor = [
            [self._create_decompose_rotate(ctl, self._node_name(ctl) + "_decomposeRotate") for ctl in anchor_ctls]
            for anchor_ctls in self.anchor_ctls
        ]

        for spec, npo in zip(self.detail_specs, self.detail_npos):
            entries = self._driver_entries_for_spec(spec)
            anchor_decomposers = [
                decomposers_by_anchor[anchor_index][spec["anchor_layer"]]
                for anchor_index in range(len(self.anchor_names))
            ]
            compose = self._compose_weighted_rotation(entries, anchor_decomposers)
            cmds.connectAttr(compose + ".outRotate", self._node_name(npo) + ".rotate", force=True)

    def _connect_curl_aims(self) -> None:
        for spec, aim_npo in zip(self.detail_specs, self.detail_aim_npos):
            curl_ctl = self.curl_ctls[min(int(spec["span"]), len(self.curl_ctls) - 1)]
            curl_npo = self.curl_npos[min(int(spec["span"]), len(self.curl_npos) - 1)]
            cmds.aimConstraint(
                self._node_name(curl_ctl),
                self._node_name(aim_npo),
                maintainOffset=True,
                aimVector=(1, 0, 0),
                upVector=(0, 1, 0),
                worldUpType="objectrotation",
                worldUpObject=self._node_name(curl_npo),
                worldUpVector=(0, 1, 0),
            )

    def _driver_entries_for_spec(self, spec: DetailSpec) -> list[DriverEntry]:
        span = int(spec["span"])
        local = float(spec["local"])
        entries: list[DriverEntry] = [
            {"kind": "anchor", "index": span, "weight": 1.0 - local},
            {"kind": "anchor", "index": min(span + 1, len(self.anchor_names) - 1), "weight": local},
        ]
        return entries

    def _compose_weighted_rotation(
        self,
        entries: list[DriverEntry],
        anchor_decomposers: list[str],
    ) -> str:
        sum_attrs = []
        for output_attr in ["outRoll", "outBendH", "outBendV"]:
            add_node = cmds.createNode("plusMinusAverage")
            cmds.setAttr(add_node + ".operation", 1)
            for index, entry in enumerate(entries):
                source = anchor_decomposers[entry["index"]]
                mult = cmds.createNode(self._multiply_node_type())
                cmds.connectAttr(source + "." + output_attr, mult + ".input1")
                cmds.setAttr(mult + ".input2", float(entry["weight"]))
                cmds.connectAttr(mult + ".output", add_node + ".input1D[%s]" % index)
            sum_attrs.append(add_node + ".output1D")

        compose = cmds.createNode("composeRotate")
        cmds.connectAttr(sum_attrs[0], compose + ".roll")
        cmds.connectAttr(sum_attrs[1], compose + ".bendH")
        cmds.connectAttr(sum_attrs[2], compose + ".bendV")
        return compose

    def _create_decompose_rotate(self, source: PymelNode, name: str) -> str:
        node = cmds.createNode("decomposeRotate", name=name)
        cmds.connectAttr(self._node_name(source) + ".rotate", node + ".rotate", force=True)
        return node

    def _multiply_node_type(self) -> str:
        if int(cmds.about(apiVersion=True)) >= MAYA_2025_API_VERSION:
            return "multDL"
        return "multDoubleLinear"

    def _node_name(self, node: object) -> str:
        name_method = getattr(node, "name", None)
        if callable(name_method):
            return name_method()
        return str(node)

    def _detail_name(self, spec: DetailSpec) -> str:
        if spec["section"] < 0:
            return "%s_%02d" % (spec["row"], spec["col"])
        return "%s_%02d_%02d" % (spec["row"], spec["section"], spec["col"])

    def _point_tuple(self, point: VectorLike) -> tuple[float, float, float]:
        return (point[0], point[1], point[2])

    def _to_vector(self, value: object) -> VectorLike:
        if hasattr(value, "length") and hasattr(value, "normal"):
            return value
        return datatypes.Vector(value)

    def _collect_detail_specs(self) -> list[DetailSpec]:
        guide_specs = self._collect_detail_guide_specs()
        if guide_specs:
            return guide_specs

        specs = []
        for row_index, row_name in enumerate(self.row_names):
            section_count = self.row_counts[row_index]
            u_start, u_end = self.row_u_ranges[row_index]
            v = (row_index + 0.5) / max(len(self.row_names), 1)
            for section in range(section_count):
                ratio = (section + 0.5) / max(section_count, 1)
                u = u_start + ((u_end - u_start) * ratio)
                for col, offset in enumerate(self.lower_edge_profiles[row_index]):
                    position = self._position_from_u_and_offset(u, offset)
                    spec = self._detail_spec(
                        row_name,
                        section,
                        col,
                        self._anchor_layer_from_offset(offset),
                        u,
                        v,
                        position,
                    )
                    specs.append(spec)
        return specs

    def _collect_detail_guide_specs(self) -> list[DetailSpec]:
        specs = []
        for local_name, matrix in self.guide.tra.items():
            parsed = self._parse_detail_guide_name(local_name)
            if parsed is None:
                continue
            row, col = parsed
            position = self._to_vector(transform.getPositionFromMatrix(matrix))
            span, local, base_position = self._closest_span_local_from_position(position)
            u = self._u_from_span_local(span, local)
            v = self._v_from_row_name(row)
            specs.append(
                self._detail_spec(
                    row,
                    -1,
                    col,
                    self._anchor_layer_from_position(position, base_position),
                    u,
                    v,
                    position,
                )
            )
        return sorted(specs, key=lambda item: (str(item["row"]), int(item["col"])))

    def _detail_spec(
        self,
        row: str,
        section: int,
        col: int,
        anchor_layer: int,
        u: float,
        v: float,
        position: VectorLike,
    ) -> DetailSpec:
        span, local = self._span_local_from_u(u)
        return {
            "row": row,
            "section": section,
            "col": col,
            "anchor_layer": anchor_layer,
            "u": max(0.0, min(1.0, u)),
            "v": max(0.0, min(1.0, v)),
            "span": min(span, len(self.anchor_names) - 2),
            "local": local,
            "position": position,
        }

    def _position_from_u_and_offset(self, u: float, offset: float) -> VectorLike:
        return self._base_position_from_u(u) + (self.lower_axis * offset * self.size)

    def _base_position_from_u(self, u: float) -> VectorLike:
        span, local = self._span_local_from_u(u)
        return self._position_from_span_local(span, local)

    def _span_local_from_u(self, u: float) -> tuple[int, float]:
        clamped_u = max(0.0, min(1.0, u))
        distance = clamped_u * self.anchor_total_length
        traversed = 0.0
        for span, segment_length in enumerate(self.anchor_segment_lengths):
            if distance <= traversed + segment_length or span == len(self.anchor_segment_lengths) - 1:
                local = (distance - traversed) / segment_length
                return span, max(0.0, min(1.0, local))
            traversed += segment_length
        return len(self.anchor_segment_lengths) - 1, 1.0

    def _u_from_span_local(self, span: int, local: float) -> float:
        distance = sum(self.anchor_segment_lengths[:span]) + (self.anchor_segment_lengths[span] * local)
        return max(0.0, min(1.0, distance / self.anchor_total_length))

    def _position_from_span_local(self, span: int, local: float) -> VectorLike:
        start = self.anchor_positions[span]
        end = self.anchor_positions[span + 1]
        return start + ((end - start) * local)

    def _collect_anchor_offsets(self) -> list[float]:
        lower_offsets = {offset for profile in self.lower_edge_profiles for offset in profile}
        if not lower_offsets:
            raise RuntimeError("ymt_feather_ribbon_01 requires at least one lower edge offset.")
        return sorted({0.0}.union(lower_offsets))

    def _anchor_layer_from_offset(self, offset: float) -> int:
        if not self.anchor_offsets:
            raise RuntimeError("ymt_feather_ribbon_01 requires at least one anchor offset layer.")
        return min(range(len(self.anchor_offsets)), key=lambda index: abs(self.anchor_offsets[index] - offset))

    def _anchor_layer_from_position(self, position: VectorLike, base_position: VectorLike) -> int:
        return self._anchor_layer_from_offset(self._offset_from_position(position, base_position))

    def _offset_from_position(self, position: VectorLike, base_position: VectorLike) -> float:
        offset = ((position - base_position) * self.lower_axis) / self.size
        if offset < -0.001:
            raise RuntimeError(
                "ymt_feather_ribbon_01 detail guide locator is on the opposite side of the parent wing blade."
            )
        return offset

    def _anchor_layer_position(self, layer_index: int, anchor_index: int) -> VectorLike:
        offset = self.anchor_offsets[layer_index]
        return self.anchor_positions[anchor_index] + (self.lower_axis * offset * self.size)

    def _curl_ctl_position(self, index: int) -> VectorLike:
        guide_matrix = self.guide.tra.get("curl%s" % index)
        if guide_matrix is not None:
            return transform.getPositionFromMatrix(guide_matrix)
        return self._curl_position(index)

    def _curl_offset_matrix(self, index: int) -> object:
        return transform.setMatrixPosition(self._curl_basis_matrix(index), self._curl_ctl_position(index))

    def _curl_basis_matrix(self, index: int) -> object:
        lower_midpoint = self._midpoint(
            self._anchor_layer_position(len(self.anchor_offsets) - 1, index),
            self._anchor_layer_position(len(self.anchor_offsets) - 1, index + 1),
        )
        matrix = transform.getTransformLookingAt(
            lower_midpoint,
            lower_midpoint + self.span_axis,
            self.wing_normal,
            axis="xy",
            negate=False,
        )
        return transform.setMatrixPosition(matrix, lower_midpoint)

    def _midpoint(self, a: VectorLike, b: VectorLike) -> VectorLike:
        return a + ((b - a) * 0.5)

    def _curl_position(self, index: int) -> VectorLike:
        u = (index + 0.5) / max(len(self.anchor_positions) - 1, 1)
        offset = self._max_lower_edge_offset_at_u(u)
        return self._position_from_u_and_offset(u, offset)

    def _surface_u_values(self) -> list[float]:
        subdivisions = max(int(self.surface_segment_subdivisions), 1)
        values = []
        for span in range(len(self.anchor_segment_lengths)):
            for step in range(subdivisions):
                values.append(self._u_from_span_local(span, step / float(subdivisions)))
        values.append(1.0)
        return values

    def _surface_offsets(self) -> list[float]:
        if len(self.anchor_offsets) < 2:
            raise RuntimeError("ymt_feather_ribbon_01 ribbon surface requires at least two V offset rows.")
        return list(self.anchor_offsets)

    def _max_lower_edge_offset_at_u(self, u: float) -> float:
        offsets = []
        for row_index, (u_start, u_end) in enumerate(self.row_u_ranges):
            if min(u_start, u_end) <= u <= max(u_start, u_end):
                offsets.extend(self.lower_edge_profiles[row_index])
        if not offsets:
            for profile in self.lower_edge_profiles:
                offsets.extend(profile)
        if not offsets:
            raise RuntimeError("ymt_feather_ribbon_01 requires at least one lower edge offset profile.")
        return max(offsets)

    def _closest_span_local_from_position(self, position: VectorLike) -> tuple[int, float, VectorLike]:
        best_span = 0
        best_local = 0.0
        best_position = self.anchor_positions[0]
        best_distance = None
        for span, segment_length in enumerate(self.anchor_segment_lengths):
            start = self.anchor_positions[span]
            end = self.anchor_positions[span + 1]
            axis = (end - start).normal()
            local_distance = (position - start) * axis
            local = max(0.0, min(1.0, local_distance / segment_length))
            candidate = self._position_from_span_local(span, local)
            distance = (position - candidate).length()
            if best_distance is None or distance < best_distance:
                best_span = span
                best_local = local
                best_position = candidate
                best_distance = distance
        return best_span, best_local, best_position

    def _v_from_row_name(self, row: str) -> float:
        if row in self.row_names:
            return (self.row_names.index(row) + 0.5) / max(len(self.row_names), 1)
        if row.isdigit():
            row_index = int(row)
            if 0 <= row_index < len(self.row_names):
                return (row_index + 0.5) / max(len(self.row_names), 1)
        raise RuntimeError("ymt_feather_ribbon_01 detail guide row is not defined in rowNames: %s." % row)

    def _get_anchor_positions(self) -> list[VectorLike]:
        positions = self._get_parent_guide_anchor_positions()
        if positions is None:
            raise RuntimeError(
                "ymt_feather_ribbon_01 requires parent ymt_birdwing_3jnt_01 guide apos: root, elbow, wrist, eff."
            )
        return positions

    def _get_anchor_segment_lengths(self) -> list[float]:
        lengths = []
        for index, (start, end) in enumerate(zip(self.anchor_positions[:-1], self.anchor_positions[1:])):
            length = (end - start).length()
            if length < 0.001:
                raise RuntimeError("ymt_feather_ribbon_01 requires non-zero parent wing guide segment %s." % index)
            lengths.append(length)
        if len(lengths) != len(self.anchor_names) - 1:
            raise RuntimeError("ymt_feather_ribbon_01 requires a complete parent wing guide chain.")
        return lengths

    def _get_parent_span_axis(self) -> VectorLike:
        root = self.anchor_positions[0]
        hand = self.anchor_positions[-1]
        tangent = hand - root
        tangent_length = tangent.length()
        if tangent_length < 0.001:
            raise RuntimeError("ymt_feather_ribbon_01 requires a valid parent wing root-to-eff guide axis.")
        return tangent.normal()

    def _get_parent_blade_normal(self) -> VectorLike:
        parent_guide = self._get_parent_wing_guide()
        blades = getattr(parent_guide, "blades", None)
        blade = blades.get("blade") if blades is not None else None
        if blade is None:
            raise RuntimeError("ymt_feather_ribbon_01 requires parent ymt_birdwing_3jnt_01 guide blade.")

        normal = blade.z * -1
        if normal.length() < 0.001:
            raise RuntimeError("ymt_feather_ribbon_01 requires a valid parent wing blade normal.")
        return normal.normal()

    def _get_parent_blade_lower_axis(self) -> VectorLike:
        lower_axis = self.wing_normal ^ self.span_axis
        if lower_axis.length() < 0.001:
            raise RuntimeError(
                "ymt_feather_ribbon_01 parent wing blade normal cannot be parallel to the root-to-eff axis."
            )
        return lower_axis.normal()

    def _get_parent_guide_anchor_positions(self) -> Optional[list[VectorLike]]:  # noqa: UP045
        parent_guide = self._get_parent_wing_guide()
        guide_positions = getattr(parent_guide, "apos", None)
        if guide_positions is None or len(guide_positions) < len(self.anchor_names):
            return None
        return list(guide_positions[: len(self.anchor_names)])

    def _get_parent_wing_guide(self) -> Optional[object]:  # noqa: UP045
        parent_guide = getattr(self.guide, "parentComponent", None)
        if parent_guide is not None and getattr(parent_guide, "compType", None) == PARENT_COMPONENT_TYPE:
            return parent_guide

        candidates = []
        rig_guides = getattr(self.rig, "guides", {})
        for guide in rig_guides.values():
            if getattr(guide, "compType", None) != PARENT_COMPONENT_TYPE:
                continue
            if guide.values.get("comp_side") != self.guide.values.get("comp_side"):
                continue
            if guide.values.get("comp_index") != self.guide.values.get("comp_index"):
                continue
            candidates.append(guide)

        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            names = ", ".join(guide.fullName for guide in candidates)
            raise RuntimeError("ymt_feather_ribbon_01 found multiple parent wing guide candidates: %s." % names)
        return None

    def _parse_detail_guide_name(self, local_name: str) -> Optional[tuple[str, int]]:  # noqa: UP045
        return detail_config.parse_detail_guide_name(local_name)

    def _ensure_rotation_driver_plugin(self) -> None:
        if cmds.pluginInfo("rotationDriver", query=True, loaded=True):
            return
        try:
            cmds.loadPlugin("rotationDriver")
        except RuntimeError as exc:
            raise RuntimeError("ymt_feather_ribbon_01 requires the rotationDriver plugin.") from exc

    def _parse_placement_mode(self, value: str) -> str:
        try:
            index = int(value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("ymt_feather_ribbon_01 placementMode must be an integer enum index.") from exc
        if index < 0 or index >= len(self.placement_modes):
            raise RuntimeError("ymt_feather_ribbon_01 placementMode index is out of range: %s." % index)
        return self.placement_modes[index]

    def _parse_row_names(self, value: str) -> list[str]:
        return detail_config.parse_row_names(value)

    def _parse_row_counts(self, value: str, row_names: list[str]) -> list[int]:
        return detail_config.parse_row_counts(value, row_names)

    def _parse_row_u_ranges(self, value: str, row_names: list[str]) -> list[tuple[float, float]]:
        return detail_config.parse_row_u_ranges(value, row_names)

    def _parse_lower_edge_profiles(self, value: str, row_names: list[str]) -> list[list[float]]:
        return detail_config.parse_lower_edge_profiles(value, row_names)

    def _collect_lower_edge_profiles(self, value: str) -> tuple[dict[str, list[float]], list[list[float]]]:
        return detail_config.collect_lower_edge_profiles(value)

    def _validate_lower_edge_profile_rows(
        self,
        named_profiles: dict[str, list[float]],
        unnamed_profiles: list[list[float]],
        row_names: list[str],
    ) -> None:
        detail_config.validate_lower_edge_profile_rows(named_profiles, unnamed_profiles, row_names)

    def _split_lower_edge_profile_rows(self, value: str) -> list[str]:
        return detail_config.split_lower_edge_profile_rows(value)

    def _parse_float_list(self, value: str) -> list[float]:
        return detail_config.parse_float_list(value)
