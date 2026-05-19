"""Feather ribbon component for ymt_birdwing_3jnt_01."""

from __future__ import annotations

import math
import importlib
from contextlib import suppress
from typing import TYPE_CHECKING, Optional, TypedDict, Union

import maya.cmds as cmds

try:
    pm = importlib.import_module("mgear.pymaya")
except ImportError:
    pm = importlib.import_module("pymel.core")
try:
    datatypes = importlib.import_module("mgear.pymaya.datatypes")
except ImportError:
    datatypes = importlib.import_module("pymel.core.datatypes")

from mgear.core import attribute, vector, primitive, transform
from mgear.shifter import component

import ymt_shifter_utility as ymt_util

from . import detail_config

if TYPE_CHECKING:
    from typing import Protocol

    from ymt_shifter_utility.type_protocols import MatrixLike, PymelNode, VectorLike, WorldPoint

    class BladeLike(Protocol):
        z: VectorLike

    class ParentWingGuideLike(Protocol):
        apos: list[VectorLike]
        blades: dict[str, BladeLike]


MAYA_2025_API_VERSION = 20250000
PARENT_COMPONENT_TYPE = "ymt_birdwing_3jnt_01"
ROTATE_ORDER_XYZ = 0


class DetailSpec(TypedDict):
    row: str
    section: int
    col: int
    anchor_layer: int
    depth: float
    u: float
    v: float
    span: int
    local: float
    position: VectorLike


class DriverEntry(TypedDict):
    kind: str
    index: int
    weight: float


class SurfaceSample(TypedDict):
    position: VectorLike
    span: int
    local: float
    depth: float
    distance: float
    anchor_distances: list[float]
    span_lengths: list[float]


class WeightedRotationSource(TypedDict):
    decomposer: str
    weight: float


class Component(component.Main):
    """Shifter component class."""

    placement_modes = ("surface", "fixed")
    anchor_names = ("root", "elbow", "wrist", "hand")
    anchor_end_names = ("rootEnd", "elbowEnd", "wristEnd", "handEnd")
    surface_curl_max_weight = 0.65
    surface_segment_subdivisions = 4

    def addObjects(self) -> None:
        """Add controls, optional ribbon surface, and detail feather outputs."""
        self.WIP = self.options["mode"]
        self.ctl_size = self.size * float(self.settings["ctlSize"]) * 0.15
        self.placement_mode = self._parse_placement_mode(self.settings["placementMode"])
        self.row_names = self._parse_row_names(self.settings["rowNames"])
        self.row_counts = self._parse_row_counts(self.settings["rowCounts"], self.row_names)
        self.row_u_ranges = self._parse_row_u_ranges(self.settings["rowURanges"], self.row_names)
        if "detailColumnDepths" not in self.settings:
            raise RuntimeError("ymt_feather_ribbon_01 requires the detailColumnDepths setting.")
        self.detail_column_depths_by_row = self._parse_detail_column_depths_by_row(
            self.settings["detailColumnDepths"],
            self.row_names,
        )
        self.anchor_positions = self._get_anchor_positions()
        self.anchor_end_positions = self._get_anchor_end_positions()
        self.anchor_segment_lengths = self._get_anchor_segment_lengths()
        self.anchor_total_length = sum(self.anchor_segment_lengths)
        self.span_axis = self._get_parent_span_axis()
        self.wing_normal = self._get_parent_blade_normal()
        self.depth_segments = self._collect_depth_segments()
        self.depth_segment_centers = self._collect_depth_segment_centers()
        self.surface_depths = self._collect_surface_depths()

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
        self.anchor_endpoint_refs = []
        self._add_anchor_controls()

        self.curl_npos = []
        self.curl_offset_npos = []
        self.curl_ctls = []
        self.curl_deforms = []
        self._add_curl_controls()

        self.detail_specs = self._collect_detail_specs()
        self.detail_npos = []
        self.detail_driver_specs = []
        self.detail_driver_npos = []
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
        source_refs = refs["refs"]
        pm.pointConstraint(source_refs["root"], self.anchor_npos[0][0], mo=True)
        cns = pm.orientConstraint(source_refs["root_ctl"], self.anchor_npos[0][0], mo=True)
        pm.setAttr(cns.attr("interpType"), 0)  # no-flip
        self._connect_anchor_root_space(source_refs, "elbow", self.anchor_npos[1][0])
        self._connect_anchor_root_space(source_refs, "wrist", self.anchor_npos[2][0])
        pm.parentConstraint(source_refs["hand"], self.anchor_npos[3][0], mo=True)
        self._connect_curl_rotations(source_refs)

    def _add_anchor_controls(self) -> None:
        for anchor_index, name in enumerate(self.anchor_names):
            parent = self.driver_root
            tag_parent = self.parentCtlTag
            anchor_npos = []
            anchor_ctls = []
            for layer_index, (start_depth, end_depth) in enumerate(self.depth_segments):
                start_position = self._anchor_position_from_depth(anchor_index, start_depth)
                end_position = self._anchor_position_from_depth(anchor_index, end_depth)
                matrix = self._anchor_control_matrix(start_position, end_position)

                npo = primitive.addTransform(parent, self.getName("feather_%s_%02d_npo" % (name, layer_index)), matrix)
                length = vector.getDistance(start_position, end_position)
                ctl = self.addCtl(
                    npo,
                    "feather_%s_%02d_ctl" % (name, layer_index),
                    matrix,
                    self.color_fk,
                    "cube",
                    w=self.ctl_size * 0.3,
                    h=self.ctl_size * 0.05,
                    d=length * 0.8,
                    po=datatypes.Vector(0.0, self.ctl_size * 0.3, length * -0.45),
                    tp=tag_parent,
                )
                attribute.setKeyableAttributes(ctl)
                attribute.setInvertMirror(ctl, ["tx", "ty", "tz"])

                anchor_npos.append(npo)
                anchor_ctls.append(ctl)
                parent = ctl
                tag_parent = ctl
            endpoint_matrix = transform.getTransformFromPos(
                self._anchor_position_from_depth(anchor_index, 1.0)
            )
            endpoint_ref = primitive.addTransform(
                parent,
                self.getName("feather_%s_endpoint_ref" % name),
                endpoint_matrix,
            )
            ymt_util.setKeyableAttributesDontLockVisibility(endpoint_ref, [])
            self.anchor_npos.append(anchor_npos)
            self.anchor_ctls.append(anchor_ctls)
            self.anchor_endpoint_refs.append(endpoint_ref)

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
                w=self.ctl_size * 0.4,
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
        controls_by_feather_part: dict[tuple[str, int, int], PymelNode] = {}
        matrices_by_feather_part = self._detail_chain_matrices(self.detail_specs)
        for spec in self.detail_specs:
            detail_name = self._detail_name(spec)
            section = int(spec["section"])
            col = int(spec["col"])
            matrix = matrices_by_feather_part[(str(spec["row"]), section, col)]
            if col == 0:
                parent = self.detail_root
                tag_parent = self.curl_ctls[min(spec["span"], len(self.curl_ctls) - 1)]
            else:
                previous_key = (str(spec["row"]), section, col - 1)
                if previous_key not in controls_by_feather_part:
                    raise RuntimeError(
                        "ymt_feather_ribbon_01 detail FK chain is missing previous feather part: %s_%s_%s."
                        % previous_key
                    )
                parent = controls_by_feather_part[previous_key]
                tag_parent = parent
            npo = primitive.addTransform(
                parent,
                self.getName("%s_npo" % detail_name),
                matrix
            )
            ctl_parent = npo
            if col == 0:
                ctl_parent = primitive.addTransform(
                    npo,
                    self.getName("%s_aim_npo" % detail_name),
                    matrix
                )
            ctl = self.addCtl(
                ctl_parent,
                "%s_ctl" % detail_name,
                matrix,
                self.color_fk,
                "circle",
                w=self.ctl_size * 0.5,
                ro=datatypes.Vector(math.radians(90), math.radians(90.0), 0.0),
                tp=tag_parent,
            )
            attribute.setKeyableAttributes(ctl)
            attribute.setInvertMirror(ctl, ["tx", "ty", "tz"])
            self.detail_npos.append(npo)
            controls_by_feather_part[(str(spec["row"]), section, col)] = ctl
            if col == 0:
                self.detail_driver_specs.append(spec)
                self.detail_driver_npos.append(npo)
                self.detail_aim_npos.append(ctl_parent)
            self.detail_ctls.append(ctl)
            if self.settings["addJoints"]:
                self.jnt_pos.append([ctl, detail_name])

    def _detail_chain_matrices(self, specs: list[DetailSpec]) -> dict[tuple[str, int, int], MatrixLike]:
        specs_by_key = self._detail_specs_by_key(specs)
        matrices = {}
        for key, spec in specs_by_key.items():
            row, section, col = key
            next_spec = specs_by_key.get((row, section, col + 1))
            previous_spec = specs_by_key.get((row, section, col - 1))
            if next_spec is not None:
                matrices[key] = self._detail_chain_matrix(spec["position"], next_spec["position"])
            elif previous_spec is not None:
                matrices[key] = self._detail_chain_matrix(previous_spec["position"], spec["position"], spec["position"])
            else:
                matrices[key] = self._single_detail_chain_matrix(spec)
        return matrices

    def _detail_specs_by_key(self, specs: list[DetailSpec]) -> dict[tuple[str, int, int], DetailSpec]:
        return {
            (str(spec["row"]), int(spec["section"]), int(spec["col"])): spec
            for spec in specs
        }

    def _detail_chain_matrix(
        self,
        start_position: VectorLike,
        end_position: VectorLike,
        matrix_position: Optional[VectorLike] = None,  # noqa: UP045
    ) -> MatrixLike:
        position = matrix_position if matrix_position is not None else start_position
        if vector.getDistance(start_position, end_position) < 0.001:
            return transform.getTransformFromPos(position)
        matrix = transform.getTransformLookingAt(
            start_position,
            end_position,
            self.wing_normal,
            axis="xy",
            negate=False,
        )
        return transform.setMatrixPosition(matrix, position)

    def _single_detail_chain_matrix(self, spec: DetailSpec) -> MatrixLike:
        span = min(int(spec["span"]), len(self.anchor_segment_lengths) - 1)
        local = float(spec["local"])
        start = self._position_from_span_local(span, local)
        end = self._position_from_anchor_end_span_local(span, local)
        if vector.getDistance(start, end) < 0.001:
            raise RuntimeError(
                "ymt_feather_ribbon_01 requires non-zero detail column depth length for detail chain: %s."
                % self._detail_name(spec)
            )
        return self._detail_chain_matrix(start, end, spec["position"])

    def _add_surface(self) -> None:
        surface_u_values = self._surface_u_values()
        surface_depths = self._surface_depths()
        surface = cmds.nurbsPlane(
            n=self.getName("ribbonSurface"),
            ch=False,
            d=1,
            u=len(surface_u_values) - 1,
            v=len(surface_depths) - 1,
        )[0]
        surface_shape = self._surface_shape_name(surface)
        for u_index, u in enumerate(surface_u_values):
            for v_index, depth in enumerate(surface_depths):
                cmds.xform(
                    "%s.cv[%s][%s]" % (surface_shape, u_index, v_index),
                    ws=True,
                    t=self._point_tuple(self._position_from_u_and_depth(u, depth)),
                )
        self.sliding_surface = pm.PyNode(surface)
        pm.parent(self.sliding_surface, self.no_transform)
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
        surface_depths = self._surface_depths()
        self._validate_surface_topology(u_count, v_count, surface_u_values, surface_depths)
        influence_names = self._skin_influence_names(skin)
        influence_by_node = self._skin_influence_names_by_node(skin)
        with suppress(RuntimeError):
            cmds.setAttr(skin + ".normalizeWeights", 0)

        for u_index in range(u_count):
            for v_index in range(v_count):
                component = "%s.cv[%s][%s]" % (surface_shape, u_index, v_index)
                sample = self._surface_sample_from_component(component)
                weights = dict.fromkeys(influence_names, 0.0)
                for joint, weight in self._surface_weight_entries(sample):
                    influence = influence_by_node[self._node_name(joint)]
                    weights[influence] += weight
                total = sum(weights.values())
                if total <= 0.0:
                    raise RuntimeError("ymt_feather_ribbon_01 generated zero total skin weight for %s." % component)
                normalized = [(name, weight / total) for name, weight in weights.items()]
                cmds.skinPercent(skin, component, transformValue=normalized, normalize=False)

        with suppress(RuntimeError):
            cmds.setAttr(skin + ".normalizeWeights", 1)
            cmds.skinCluster(skin, edit=True, forceNormalizeWeights=True)
        self._validate_surface_skin_weights(
            skin, surface_shape, surface_u_values, v_count, surface_depths, influence_by_node
        )

    def _validate_surface_skin_weights(
        self,
        skin: str,
        surface_shape: str,
        surface_u_values: list[float],
        v_count: int,
        surface_depths: list[float],
        influence_by_node: dict[str, str],
    ) -> None:
        v_index = max(range(v_count), key=lambda index: abs(surface_depths[index]))
        for index, joint in enumerate(self.curl_surface_skin_joints):
            u = self._curl_u(index)
            u_index = min(
                range(len(surface_u_values)),
                key=lambda index: abs(surface_u_values[index] - u),
            )
            component = "%s.cv[%s][%s]" % (surface_shape, u_index, v_index)
            sample = self._surface_sample_from_component(component)
            expected_entries = dict(self._surface_curl_weight_entries(sample))
            expected = expected_entries.get(joint, 0.0)
            if expected <= 0.05:
                continue
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
        surface_depths: list[float],
    ) -> None:
        if u_count != len(surface_u_values):
            raise RuntimeError(
                "ymt_feather_ribbon_01 ribbon surface requires %s U CVs for fixed anchor/curl columns, got %s."
                % (len(surface_u_values), u_count)
            )
        if v_count != len(surface_depths):
            raise RuntimeError(
                "ymt_feather_ribbon_01 ribbon surface requires %s V CVs for fixed depth rows, got %s."
                % (len(surface_depths), v_count)
            )

    def _surface_shape_name(self, surface: str) -> str:
        shapes = cmds.listRelatives(surface, shapes=True, fullPath=True) or []
        if not shapes:
            raise RuntimeError("ymt_feather_ribbon_01 could not find the ribbon surface shape.")
        return shapes[0]

    def _surface_sample_from_component(self, component: str) -> SurfaceSample:
        position = self._to_vector(cmds.xform(component, query=True, worldSpace=True, translation=True))
        return self._surface_sample_from_position(position)

    def _surface_sample_from_position(self, position: VectorLike) -> SurfaceSample:
        best_sample = None
        best_distance = None
        for span in range(len(self.anchor_segment_lengths)):
            sample = self._surface_sample_from_position_on_span(position, span)
            distance = (position - sample["position"]).length()
            if best_distance is None or distance < best_distance:
                best_sample = sample
                best_distance = distance
        if best_sample is None:
            raise RuntimeError("ymt_feather_ribbon_01 could not resolve a surface sample from CV position.")
        return best_sample

    def _surface_sample_from_position_on_span(self, position: VectorLike, span: int) -> SurfaceSample:
        low = 0.0
        high = 1.0
        for _ in range(12):
            first = low + ((high - low) / 3.0)
            second = high - ((high - low) / 3.0)
            first_distance = self._surface_projection_distance_on_span(position, span, first)
            second_distance = self._surface_projection_distance_on_span(position, span, second)
            if first_distance < second_distance:
                high = second
            else:
                low = first
        local = (low + high) * 0.5
        base_position = self._position_from_span_local(span, local)
        end_position = self._position_from_anchor_end_span_local(span, local)
        depth = self._clamped_depth_from_position(position, base_position, end_position)
        sample_position = base_position + ((end_position - base_position) * depth)
        span_lengths = self._surface_span_lengths_from_sample_depth(depth)
        anchor_distances = self._anchor_distances_from_span_lengths(span_lengths)
        distance = anchor_distances[span] + (span_lengths[span] * local)
        return {
            "position": sample_position,
            "span": span,
            "local": local,
            "depth": depth,
            "distance": distance,
            "anchor_distances": anchor_distances,
            "span_lengths": span_lengths,
        }

    def _surface_projection_distance_on_span(self, position: VectorLike, span: int, local: float) -> float:
        base_position = self._position_from_span_local(span, local)
        end_position = self._position_from_anchor_end_span_local(span, local)
        depth = self._clamped_depth_from_position(position, base_position, end_position)
        projected = base_position + ((end_position - base_position) * depth)
        return (position - projected).length()

    def _surface_span_lengths_from_sample_depth(self, depth: float) -> list[float]:
        lengths = []
        for span in range(len(self.anchor_segment_lengths)):
            start = self._anchor_position_from_depth(span, depth)
            end = self._anchor_position_from_depth(span + 1, depth)
            length = (end - start).length()
            if length < 0.001:
                raise RuntimeError(
                    "ymt_feather_ribbon_01 requires non-zero surface segment %s at depth %.3f." % (span, depth)
                )
            lengths.append(length)
        return lengths

    def _anchor_distances_from_span_lengths(self, span_lengths: list[float]) -> list[float]:
        distances = [0.0]
        total = 0.0
        for length in span_lengths:
            total += length
            distances.append(total)
        return distances

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

    def _surface_weight_entries(self, sample: SurfaceSample) -> list[tuple[PymelNode, float]]:
        curl_strength = self._surface_curl_weight_for_sample(sample)
        anchor_weight = max(0.0, 1.0 - curl_strength)
        entries = [(joint, weight * anchor_weight) for joint, weight in self._surface_anchor_weight_entries(sample)]
        entries.extend(self._surface_curl_weight_entries(sample, curl_strength))
        return entries

    def _surface_anchor_weight_entries(self, sample: SurfaceSample) -> list[tuple[PymelNode, float]]:
        anchor_entries = self._anchor_weight_entries_for_surface_sample(sample)
        layer_entries = self._anchor_layer_weight_entries_for_depth(sample["depth"])
        entries = []
        for anchor_index, anchor_value in anchor_entries:
            for layer_index, layer_value in layer_entries:
                joint = self.anchor_surface_skin_joints[anchor_index][layer_index]
                entries.append((joint, anchor_value * layer_value))
        return entries

    def _surface_curl_weight_entries(
        self,
        sample: SurfaceSample,
        curl_weight: Optional[float] = None,  # noqa: UP045
    ) -> list[tuple[PymelNode, float]]:
        if not self.curl_surface_skin_joints:
            raise RuntimeError("ymt_feather_ribbon_01 curl surface skin joints were not properly initialized.")
        if curl_weight is None:
            curl_weight = self._surface_curl_weight_for_sample(sample)
        if curl_weight <= 0.0:
            return []
        raw_weights = self._surface_curl_raw_weights_for_sample(sample)
        raw_total = sum(raw_weights)
        if raw_total <= 0.0:
            return []
        return [
            (joint, curl_weight * (raw_weight / raw_total))
            for joint, raw_weight in zip(self.curl_surface_skin_joints, raw_weights)
            if raw_weight > 0.0
        ]

    def _surface_curl_weight_for_sample(self, sample: SurfaceSample) -> float:
        max_depth = self._max_surface_depth()
        if max_depth <= 0.0:
            return 0.0
        segment_weight = min(1.0, sum(self._surface_curl_raw_weights_for_sample(sample)))
        depth_weight = max(0.0, min(1.0, sample["depth"] / max_depth))
        return max(0.0, min(1.0, depth_weight * segment_weight * self.surface_curl_max_weight))

    def _surface_curl_raw_weights_for_sample(self, sample: SurfaceSample) -> list[float]:
        count = len(self.curl_surface_skin_joints)
        centers = [
            sample["anchor_distances"][index] + (sample["span_lengths"][index] * 0.5)
            for index in range(count)
        ]
        return [
            self._surface_curl_raw_weight_for_center(sample["distance"], center, centers, index)
            for index, center in enumerate(centers)
        ]

    def _curl_raw_weights_for_u(self, u: float, count: int) -> list[float]:
        centers = [self._curl_u(index) for index in range(count)]
        return [self._surface_curl_raw_weight_for_center(u, center, centers, index) for index, center in enumerate(centers)]

    def _curl_weight_entries_for_u(self, u: float, count: int) -> list[tuple[int, float]]:
        raw_weights = self._curl_raw_weights_for_u(u, count)
        total = sum(raw_weights)
        if total <= 0.0:
            if count <= 0:
                return []
            nearest = min(range(count), key=lambda index: abs(u - self._curl_u(index)))
            return [(nearest, 1.0)]
        return [(index, weight / total) for index, weight in enumerate(raw_weights) if weight > 0.0]

    def _surface_curl_raw_weight_for_center(
        self,
        u: float,
        center: float,
        centers: list[float],
        index: int,
    ) -> float:
        radius = self._surface_curl_weight_radius(centers, index)
        if radius <= 0.0:
            return 1.0 if abs(u - center) <= 0.001 else 0.0
        t = max(0.0, min(1.0, abs(u - center) / radius))
        return 1.0 - self._smootherstep(t)

    def _surface_curl_weight_radius(self, centers: list[float], index: int) -> float:
        distances = []
        if index > 0:
            distances.append(abs(centers[index] - centers[index - 1]))
        if index < len(centers) - 1:
            distances.append(abs(centers[index + 1] - centers[index]))
        return max(distances) if distances else 0.0

    def _smootherstep(self, value: float) -> float:
        t = max(0.0, min(1.0, value))
        return t * t * t * (t * ((t * 6.0) - 15.0) + 10.0)

    def _max_surface_depth(self) -> float:
        return max(self.surface_depths)

    def _anchor_weight_entries_for_u(self, u: float) -> list[tuple[int, float]]:
        span, local = self._span_local_from_u(u)
        return self._anchor_weight_entries_from_span_local(span, local)

    def _anchor_weight_entries_for_surface_sample(self, sample: SurfaceSample) -> list[tuple[int, float]]:
        anchor_distances = sample["anchor_distances"]
        distance = sample["distance"]
        nearest = min(range(len(anchor_distances)), key=lambda index: abs(anchor_distances[index] - distance))
        start = max(0, nearest - 1)
        end = min(len(anchor_distances) - 1, nearest + 1)
        raw_entries = []
        for index in range(start, end + 1):
            radius = self._anchor_weight_radius(anchor_distances, index)
            if radius <= 0.0:
                weight = 1.0 if abs(distance - anchor_distances[index]) <= 0.001 else 0.0
            else:
                normalized_distance = abs(distance - anchor_distances[index]) / radius
                weight = max(0.0, 1.0 - self._smootherstep(normalized_distance))
            if weight > 0.0:
                raw_entries.append((index, weight))
        total = sum(weight for _, weight in raw_entries)
        if total <= 0.0:
            return [(nearest, 1.0)]
        return [(index, weight / total) for index, weight in raw_entries]

    def _anchor_weight_radius(self, anchor_distances: list[float], index: int) -> float:
        distances = []
        if index > 0:
            distances.append(anchor_distances[index] - anchor_distances[index - 1])
        if index < len(anchor_distances) - 1:
            distances.append(anchor_distances[index + 1] - anchor_distances[index])
        return max(distances) if distances else 0.0

    def _anchor_weight_entries_from_span_local(self, span: int, local: float) -> list[tuple[int, float]]:
        start_anchor = min(span, len(self.anchor_names) - 1)
        end_anchor = min(span + 1, len(self.anchor_names) - 1)
        if local <= 0.001 or start_anchor == end_anchor:
            return [(start_anchor, 1.0)]
        if local >= 0.999:
            return [(end_anchor, 1.0)]
        return [(start_anchor, 1.0 - local), (end_anchor, local)]

    def _anchor_layer_weight_entries_for_depth(self, depth: float) -> list[tuple[int, float]]:
        centers = self.depth_segment_centers
        if not centers:
            raise RuntimeError("ymt_feather_ribbon_01 requires at least one depth segment center.")
        if len(centers) == 1 or depth <= centers[0]:
            return [(0, 1.0)]
        if depth >= centers[-1]:
            return [(len(centers) - 1, 1.0)]
        for index, (start, end) in enumerate(zip(centers[:-1], centers[1:])):
            if start <= depth <= end:
                width = end - start
                if width <= 0.0:
                    return [(index, 1.0)]
                weight = (depth - start) / width
                return [(index, 1.0 - weight), (index + 1, weight)]
        return [(self._anchor_layer_from_depth(depth), 1.0)]

    def _connect_surface_rivets(self) -> None:
        for npo in self.detail_driver_npos:
            rivets = ymt_util.apply_rivet_constrain_to_selected(self.sliding_surface, npo)
            rivet = pm.PyNode(rivets[0])
            pm.parent(rivet, self.no_transform, relative=True)
            pm.pointConstraint(rivet, npo, mo=True)
            ymt_util.setKeyableAttributesDontLockVisibility(rivet, [])

    def _connect_curl_spaces(self) -> None:
        for segment_index, npo in enumerate(self.curl_npos):
            self._connect_curl_translate_matrix(segment_index, npo)

    def _connect_curl_rotations(self, refs: dict[str, PymelNode]) -> None:
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
            self.anchor_endpoint_refs[segment_index],
            self.anchor_endpoint_refs[segment_index + 1],
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
        start_ref: PymelNode,
        end_ref: PymelNode,
    ) -> None:
        constraint = cmds.orientConstraint(
            self._node_name(start_ref),
            self._node_name(end_ref),
            self._node_name(npo),
            maintainOffset=True,
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

    def _create_weighted_world_translate_node(
        self,
        entries: list[tuple[PymelNode, float]],
        name: str,
    ) -> str:
        if not entries:
            raise RuntimeError("ymt_feather_ribbon_01 requires at least one weighted translate source.")
        add_node = cmds.createNode("plusMinusAverage", name=self.getName(name + "_pma"))
        cmds.setAttr(add_node + ".operation", 1)
        for index, (source, weight) in enumerate(entries):
            decompose = self._create_decompose_matrix(
                self._node_name(source) + ".worldMatrix[0]",
                self.getName("%s_%02d_dm" % (name, index)),
            )
            mult = cmds.createNode("multiplyDivide", name=self.getName("%s_%02d_md" % (name, index)))
            cmds.connectAttr(decompose + ".outputTranslate", mult + ".input1", force=True)
            cmds.setAttr(mult + ".input2X", weight)
            cmds.setAttr(mult + ".input2Y", weight)
            cmds.setAttr(mult + ".input2Z", weight)
            cmds.connectAttr(mult + ".output", add_node + ".input3D[%s]" % index, force=True)
        return add_node + ".output3D"

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

        for spec, npo in zip(self.detail_driver_specs, self.detail_driver_npos):
            entries = self._driver_entries_for_spec(spec)
            layer_entries = self._anchor_layer_weight_entries_for_depth(spec["depth"])
            compose = self._compose_weighted_rotation_sources(
                [
                    {
                        "decomposer": decomposers_by_anchor[entry["index"]][layer_index],
                        "weight": float(entry["weight"]) * layer_weight,
                    }
                    for entry in entries
                    for layer_index, layer_weight in layer_entries
                ]
            )
            rotate_attr = self._create_initial_offset_rotate_node(
                npo,
                compose + ".outRotate",
                "%s_detailRotate" % self._detail_name(spec),
            )
            cmds.connectAttr(rotate_attr, self._node_name(npo) + ".rotate", force=True)

    def _connect_curl_aims(self) -> None:
        aim_up = self._create_detail_chain_aim_up()
        specs_by_key = self._detail_specs_by_key(self.detail_specs)
        targets_by_chain: dict[tuple[str, int], PymelNode] = {}
        for spec, aim_npo in zip(self.detail_driver_specs, self.detail_aim_npos):
            chain_key = (str(spec["row"]), int(spec["section"]))
            if chain_key not in targets_by_chain:
                aim_u = self._detail_chain_aim_u(spec, specs_by_key)
                curl_entries = self._curl_weight_entries_for_u(aim_u, len(self.curl_ctls))
                targets_by_chain[chain_key] = self._create_detail_chain_aim_target(spec, aim_npo, curl_entries)
            cmds.aimConstraint(
                self._node_name(targets_by_chain[chain_key]),
                self._node_name(aim_npo),
                maintainOffset=True,
                aimVector=(1, 0, 0),
                upVector=(0, 1, 0),
                worldUpType="objectrotation",
                worldUpObject=self._node_name(aim_up),
                worldUpVector=(0, 1, 0),
            )

    def _create_detail_chain_aim_target(
        self,
        spec: DetailSpec,
        aim_npo: PymelNode,
        curl_entries: list[tuple[int, float]],
    ) -> PymelNode:
        aim_target = primitive.addTransform(
            self.no_transform,
            self.getName("%s_chainAimTarget" % self._detail_name(spec)),
            transform.getTransform(aim_npo),
        )
        translate_attr = self._create_weighted_world_translate_node(
            [(self.curl_ctls[index], weight) for index, weight in curl_entries],
            self._detail_name(spec) + "_chainAimTargetTranslate",
        )
        cmds.connectAttr(translate_attr, self._node_name(aim_target) + ".translate", force=True)
        ymt_util.setKeyableAttributesDontLockVisibility(aim_target, [])
        return aim_target

    def _create_detail_chain_aim_up(self) -> PymelNode:
        aim_up = primitive.addTransform(
            self.no_transform,
            self.getName("detailChainAimUp"),
            transform.getTransform(self.detail_root),
        )
        ymt_util.setKeyableAttributesDontLockVisibility(aim_up, [])
        return aim_up

    def _detail_chain_aim_u(
        self,
        spec: DetailSpec,
        specs_by_key: dict[tuple[str, int, int], DetailSpec],
    ) -> float:
        row = str(spec["row"])
        section = int(spec["section"])
        col = int(spec["col"])
        next_spec = specs_by_key.get((row, section, col + 1))
        if next_spec is None:
            return float(spec["u"])
        return (float(spec["u"]) + float(next_spec["u"])) * 0.5

    def _connect_anchor_root_space(self, refs: dict[str, PymelNode], anchor_name: str, npo: PymelNode) -> None:
        self._ensure_rotation_driver_plugin()
        rotation_parent = self._create_anchor_rotation_parent(anchor_name, refs[anchor_name], npo)
        entries = self._anchor_root_space_entries(anchor_name)
        sources: list[WeightedRotationSource] = []

        for source_name, weight in entries:
            proxy = primitive.addTransform(
                rotation_parent,
                self.getName("feather_%s_%s_rotProxy" % (anchor_name, source_name)),
                transform.getTransform(npo),
            )
            constraint = pm.orientConstraint(refs[source_name], proxy, mo=True)
            pm.setAttr(constraint.attr("interpType"), 0)  # no-flip
            ymt_util.setKeyableAttributesDontLockVisibility(proxy, [])
            sources.append(
                {
                    "decomposer": self._create_decompose_rotate(
                        proxy,
                        self.getName("feather_%s_%s_decomposeRotate" % (anchor_name, source_name)),
                    ),
                    "weight": weight,
                }
            )
        compose = self._compose_weighted_rotation_sources(sources, include_bend_v=False)
        cmds.connectAttr(compose + ".outRotate", self._node_name(npo) + ".rotate", force=True)

    def _create_anchor_rotation_parent(
        self,
        anchor_name: str,
        driven_ref: PymelNode,
        npo: PymelNode,
    ) -> PymelNode:
        parent = npo.getParent()
        if parent is None:
            raise RuntimeError("ymt_feather_ribbon_01 anchor rotation parent requires a parented npo: %s." % npo)
        rotation_parent = primitive.addTransform(
            parent,
            self.getName("feather_%s_rotParent" % anchor_name),
            transform.getTransform(npo),
        )
        pm.parent(npo, rotation_parent)
        pm.pointConstraint(driven_ref, rotation_parent, mo=True)
        constraint = pm.orientConstraint(driven_ref, rotation_parent, mo=True)
        pm.setAttr(constraint.attr("interpType"), 0)  # no-flip
        ymt_util.setKeyableAttributesDontLockVisibility(rotation_parent, [])
        return rotation_parent

    def _anchor_root_space_entries(self, anchor_name: str) -> list[tuple[str, float]]:
        if anchor_name == "elbow":
            return [("root_ctl", 0.25), ("elbow", 0.5), ("wrist", 0.25)]
        if anchor_name == "wrist":
            return [("elbow", 0.25), ("wrist", 0.5), ("hand", 0.25)]
        raise RuntimeError("ymt_feather_ribbon_01 unsupported anchor root-space blend: %s." % anchor_name)

    def _driver_entries_for_spec(self, spec: DetailSpec) -> list[DriverEntry]:
        span = int(spec["span"])
        local = float(spec["local"])
        entries: list[DriverEntry] = [
            {"kind": "anchor", "index": span, "weight": 1.0 - local},
            {"kind": "anchor", "index": min(span + 1, len(self.anchor_names) - 1), "weight": local},
        ]
        return entries

    def _compose_weighted_rotation_sources(
        self,
        sources: list[WeightedRotationSource],
        include_bend_v: bool = True,
    ) -> str:
        sum_attrs = []
        output_attrs = ["outRoll", "outBendH"]
        if include_bend_v:
            output_attrs.append("outBendV")
        for output_attr in output_attrs:
            add_node = cmds.createNode("plusMinusAverage")
            cmds.setAttr(add_node + ".operation", 1)
            for index, source in enumerate(sources):
                mult = cmds.createNode(self._multiply_node_type())
                cmds.connectAttr(source["decomposer"] + "." + output_attr, mult + ".input1")
                cmds.setAttr(mult + ".input2", source["weight"])
                cmds.connectAttr(mult + ".output", add_node + ".input1D[%s]" % index)
            sum_attrs.append(add_node + ".output1D")

        compose = cmds.createNode("composeRotate")
        cmds.setAttr(compose + ".rotateOrder", ROTATE_ORDER_XYZ)
        cmds.connectAttr(sum_attrs[0], compose + ".roll")
        cmds.connectAttr(sum_attrs[1], compose + ".bendH")
        if include_bend_v:
            cmds.connectAttr(sum_attrs[2], compose + ".bendV")
        return compose

    def _create_decompose_rotate(self, source: PymelNode, name: str) -> str:
        node = cmds.createNode("decomposeRotate", name=name)
        cmds.setAttr(node + ".rotateOrder", ROTATE_ORDER_XYZ)
        cmds.connectAttr(self._node_name(source) + ".rotate", node + ".rotate", force=True)
        return node

    def _create_initial_offset_rotate_node(self, npo: PymelNode, driver_rotate_attr: str, name: str) -> str:
        npo_name = self._node_name(npo)
        initial_rotate = cmds.getAttr(npo_name + ".rotate")[0]

        initial_compose = cmds.createNode("composeMatrix", name=self.getName(name + "_initial_cm"))
        cmds.setAttr(initial_compose + ".inputRotate", *initial_rotate)
        cmds.setAttr(initial_compose + ".inputRotateOrder", ROTATE_ORDER_XYZ)

        driver_compose = cmds.createNode("composeMatrix", name=self.getName(name + "_driver_cm"))
        cmds.connectAttr(driver_rotate_attr, driver_compose + ".inputRotate", force=True)
        cmds.setAttr(driver_compose + ".inputRotateOrder", ROTATE_ORDER_XYZ)

        mult = cmds.createNode("multMatrix", name=self.getName(name + "_mm"))
        cmds.connectAttr(driver_compose + ".outputMatrix", mult + ".matrixIn[0]", force=True)
        cmds.connectAttr(initial_compose + ".outputMatrix", mult + ".matrixIn[1]", force=True)

        decompose = cmds.createNode("decomposeMatrix", name=self.getName(name + "_dm"))
        cmds.connectAttr(mult + ".matrixSum", decompose + ".inputMatrix", force=True)
        cmds.setAttr(decompose + ".inputRotateOrder", ROTATE_ORDER_XYZ)
        return decompose + ".outputRotate"

    def _multiply_node_type(self) -> str:
        if int(cmds.about(apiVersion=True)) >= MAYA_2025_API_VERSION:
            return "multDL"
        return "multDoubleLinear"

    def _node_name(self, node: Union[PymelNode, str]) -> str:  # noqa: UP007
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

    def _to_vector(self, value: WorldPoint) -> VectorLike:
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
                for col, depth in enumerate(self.detail_column_depths_by_row[row_index]):
                    position = self._position_from_u_and_depth(u, depth)
                    spec = self._detail_spec(
                        row_name,
                        section,
                        col,
                        self._anchor_layer_from_depth(depth),
                        depth,
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
            row, section, col = parsed
            position = self._to_vector(transform.getPositionFromMatrix(matrix))
            span, local, base_position = self._closest_span_local_from_position(position)
            end_position = self._position_from_anchor_end_span_local(span, local)
            depth = self._depth_from_position_in_anchor_depth_space(position, base_position, end_position)
            u = self._u_from_span_local(span, local)
            v = self._v_from_row_name(row)
            specs.append(
                self._detail_spec(
                    row,
                    section,
                    col,
                    self._anchor_layer_from_depth(depth),
                    depth,
                    u,
                    v,
                    position,
                )
            )
        return sorted(specs, key=lambda item: (str(item["row"]), int(item["section"]), int(item["col"])))

    def _detail_spec(
        self,
        row: str,
        section: int,
        col: int,
        anchor_layer: int,
        depth: float,
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
            "depth": depth,
            "u": max(0.0, min(1.0, u)),
            "v": max(0.0, min(1.0, v)),
            "span": min(span, len(self.anchor_names) - 2),
            "local": local,
            "position": position,
        }

    def _position_from_u_and_depth(self, u: float, depth: float) -> VectorLike:
        span, local = self._span_local_from_u(u)
        start = self._anchor_position_from_depth(span, depth)
        end = self._anchor_position_from_depth(span + 1, depth)
        return start + ((end - start) * local)

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

    def _position_from_anchor_end_span_local(self, span: int, local: float) -> VectorLike:
        start = self.anchor_end_positions[span]
        end = self.anchor_end_positions[span + 1]
        return start + ((end - start) * local)

    def _get_anchor_end_positions(self) -> list[VectorLike]:
        positions = []
        for name in self.anchor_end_names:
            matrix = self.guide.tra.get(name)
            if matrix is None:
                raise RuntimeError("ymt_feather_ribbon_01 requires the %s guide locator." % name)
            positions.append(self._to_vector(transform.getPositionFromMatrix(matrix)))
        if len(positions) != len(self.anchor_names):
            raise RuntimeError("ymt_feather_ribbon_01 requires one anchor end locator per anchor.")
        return positions

    def _collect_depth_segments(self) -> list[tuple[float, float]]:
        detail_column_depths = {depth for depths in self.detail_column_depths_by_row for depth in depths}
        if not detail_column_depths:
            raise RuntimeError("ymt_feather_ribbon_01 requires at least one detail column depth.")
        boundaries = sorted({0.0, 1.0}.union(detail_column_depths))
        segments = [(start, end) for start, end in zip(boundaries[:-1], boundaries[1:]) if end - start > 0.001]
        if not segments:
            raise RuntimeError("ymt_feather_ribbon_01 requires a non-zero detail column depth range.")
        return segments

    def _collect_surface_depths(self) -> list[float]:
        if not self.depth_segments:
            raise RuntimeError("ymt_feather_ribbon_01 ribbon surface requires at least one depth segment.")
        base_subdivisions = max(int(self.surface_segment_subdivisions), 1)
        segment_widths = [end - start for start, end in self.depth_segments]
        average_width = sum(segment_widths) / float(len(segment_widths))
        target_step = average_width / float(base_subdivisions)
        if target_step <= 0.0:
            raise RuntimeError("ymt_feather_ribbon_01 ribbon surface requires non-zero anchor depth segment width.")

        depths = [self.depth_segments[0][0]]
        for start, end in self.depth_segments:
            subdivisions = max(1, math.ceil((end - start) / target_step))
            for step in range(1, subdivisions + 1):
                ratio = step / float(subdivisions)
                depths.append(start + ((end - start) * ratio))
        if len(depths) < 2:
            raise RuntimeError("ymt_feather_ribbon_01 ribbon surface requires at least two V depth rows.")
        return depths

    def _collect_depth_segment_centers(self) -> list[float]:
        if not self.depth_segments:
            raise RuntimeError("ymt_feather_ribbon_01 requires at least one depth segment.")
        return [(start + end) * 0.5 for start, end in self.depth_segments]

    def _anchor_layer_from_depth(self, depth: float) -> int:
        if not self.depth_segments:
            raise RuntimeError("ymt_feather_ribbon_01 requires at least one depth segment.")
        for index, (start, end) in enumerate(self.depth_segments):
            if start <= depth <= end:
                return index
        if depth < self.depth_segments[0][0]:
            return 0
        return len(self.depth_segments) - 1

    def _depth_from_position_in_anchor_depth_space(
        self,
        position: VectorLike,
        base_position: VectorLike,
        end_position: VectorLike,
    ) -> float:
        # Depth values are measured in the anchor -> anchorEnd basis.
        # 0.0 is the anchor line, and 1.0 is the anchorEnd reference line.
        depth = self._depth_ratio_from_position(position, base_position, end_position)
        if not -0.001 <= depth <= 1.001:
            raise RuntimeError(
                "ymt_feather_ribbon_01 detail guide is outside the anchor -> anchorEnd depth range: %.3f." % depth
            )
        return max(0.0, min(1.0, depth))

    def _clamped_depth_from_position(
        self,
        position: VectorLike,
        base_position: VectorLike,
        end_position: VectorLike,
    ) -> float:
        return max(0.0, min(1.0, self._depth_ratio_from_position(position, base_position, end_position)))

    def _depth_ratio_from_position(
        self,
        position: VectorLike,
        base_position: VectorLike,
        end_position: VectorLike,
    ) -> float:
        depth_axis = end_position - base_position
        length_squared = depth_axis * depth_axis
        if length_squared < 0.000001:
            raise RuntimeError("ymt_feather_ribbon_01 requires non-zero anchorEnd depth length.")
        return ((position - base_position) * depth_axis) / length_squared

    def _anchor_control_matrix(self, start_position: VectorLike, end_position: VectorLike) -> MatrixLike:
        if vector.getDistance(start_position, end_position) < 0.001:
            raise RuntimeError("ymt_feather_ribbon_01 requires non-zero anchor control depth length.")
        return transform.getTransformLookingAt(
            start_position,
            end_position,
            self.wing_normal,
            axis="-zy",
            negate=False,
        )

    def _anchor_position_from_depth(self, anchor_index: int, depth: float) -> VectorLike:
        # detailColumnDepths uses this same anchor -> anchorEnd basis.
        if not 0.0 <= depth <= 1.0:
            raise RuntimeError("ymt_feather_ribbon_01 detail column depth must be between 0 and 1: %.3f." % depth)
        base_position = self.anchor_positions[anchor_index]
        end_position = self.anchor_end_positions[anchor_index]
        return base_position + ((end_position - base_position) * depth)

    def _curl_guide_position(self, index: int) -> VectorLike:
        guide_matrix = self.guide.tra.get("curl%s" % index)
        if guide_matrix is None:
            raise RuntimeError("ymt_feather_ribbon_01 requires the curl%s guide locator." % index)
        return self._to_vector(transform.getPositionFromMatrix(guide_matrix))

    def _curl_ctl_position(self, index: int) -> VectorLike:
        return self._curl_guide_position(index)

    def _curl_offset_matrix(self, index: int) -> MatrixLike:
        curl_position = self._curl_ctl_position(index)
        return transform.setMatrixPosition(
            self._curl_orientation_matrix(index, curl_position),
            curl_position,
        )

    def _curl_basis_matrix(self, index: int) -> MatrixLike:
        lower_midpoint = self._midpoint(
            self._anchor_position_from_depth(index, 1.0),
            self._anchor_position_from_depth(index + 1, 1.0),
        )
        return transform.setMatrixPosition(self._curl_orientation_matrix(index), lower_midpoint)

    def _curl_orientation_matrix(self, index: int, tip_position: Optional[VectorLike] = None) -> MatrixLike:  # noqa: UP045
        root_position = self._curl_root_position(index)
        if tip_position is None:
            tip_position = self._curl_ctl_position(index)
        else:
            tip_position = self._to_vector(tip_position)

        root_to_tip = tip_position - root_position
        if root_to_tip.length() < 0.001:
            raise RuntimeError("ymt_feather_ribbon_01 requires curl tip position away from the feather root.")

        return transform.getTransformLookingAt(
            tip_position,
            root_position,
            self.wing_normal,
            axis="-zy",
            negate=False,
        )

    def _curl_root_position(self, index: int) -> VectorLike:
        return self._base_position_from_u(self._curl_u(index))

    def _midpoint(self, a: VectorLike, b: VectorLike) -> VectorLike:
        return a + ((b - a) * 0.5)

    def _curl_u(self, index: int) -> float:
        return (index + 0.5) / max(len(self.anchor_positions) - 1, 1)

    def _surface_u_values(self) -> list[float]:
        base_subdivisions = max(int(self.surface_segment_subdivisions), 1)
        surface_segment_lengths = self._surface_segment_lengths()
        average_length = sum(surface_segment_lengths) / max(len(surface_segment_lengths), 1)
        target_step = average_length / float(base_subdivisions)
        if target_step <= 0.0:
            raise RuntimeError("ymt_feather_ribbon_01 ribbon surface requires non-zero anchor segment length.")
        values = []
        for span, segment_length in enumerate(surface_segment_lengths):
            subdivisions = max(1, math.ceil(segment_length / target_step))
            for step in range(subdivisions):
                values.append(self._u_from_span_local(span, step / float(subdivisions)))
        values.append(1.0)
        return values

    def _surface_segment_lengths(self) -> list[float]:
        lengths = []
        for span, upper_length in enumerate(self.anchor_segment_lengths):
            lower_start = self.anchor_end_positions[span]
            lower_end = self.anchor_end_positions[span + 1]
            lower_length = (lower_end - lower_start).length()
            if lower_length < 0.001:
                raise RuntimeError("ymt_feather_ribbon_01 requires non-zero lower surface segment %s." % span)
            lengths.append(max(upper_length, lower_length))
        return lengths

    def _surface_depths(self) -> list[float]:
        if len(self.surface_depths) < 2:
            raise RuntimeError("ymt_feather_ribbon_01 ribbon surface requires at least two V depth rows.")
        return list(self.surface_depths)

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

    def _get_parent_guide_anchor_positions(self) -> Optional[list[VectorLike]]:  # noqa: UP045
        parent_guide = self._get_parent_wing_guide()
        guide_positions = getattr(parent_guide, "apos", None)
        if guide_positions is None or len(guide_positions) < len(self.anchor_names):
            return None
        return list(guide_positions[: len(self.anchor_names)])

    def _get_parent_wing_guide(self) -> Optional[ParentWingGuideLike]:  # noqa: UP045
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

    def _parse_detail_guide_name(self, local_name: str) -> Optional[tuple[str, int, int]]:  # noqa: UP045
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

    def _parse_detail_column_depths_by_row(self, value: str, row_names: list[str]) -> list[list[float]]:
        return detail_config.parse_detail_column_depths_by_row(value, row_names)
