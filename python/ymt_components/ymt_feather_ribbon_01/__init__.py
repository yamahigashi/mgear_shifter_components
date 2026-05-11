"""Feather ribbon component for ymt_birdwing_3jnt_01."""

from __future__ import annotations

import importlib
import math
import re
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

if TYPE_CHECKING:
    from ymt_shifter_utility.type_protocols import PymelNode, VectorLike


DETAIL_GUIDE_PATTERNS = (
    re.compile(r"^detail_(?P<row>[A-Za-z][A-Za-z0-9]*)_(?P<col>\d+)_loc$"),
    re.compile(r"^_loc(?P<row>\d+)_(?P<col>\d+)$"),
    re.compile(r"^(?P<row>\d+)_(?P<col>\d+)_loc$"),
)
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

    def addObjects(self) -> None:
        """Add controls, optional ribbon surface, and detail feather outputs."""
        self.WIP = self.options["mode"]
        self.ctl_size = self.size * float(self.settings["ctlSize"]) * 0.15
        self.placement_mode = self.placement_modes[int(self.settings["placementMode"])]
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
        self.lower_axis = self._get_parent_chain_lower_axis()
        self.anchor_offsets = self._collect_anchor_offsets()

        self.driver_root = primitive.addTransform(self.root, self.getName("drivers"), transform.getTransform(self.root))
        self.detail_root = primitive.addTransform(self.root, self.getName("details"), transform.getTransform(self.root))
        self.no_transform = primitive.addTransform(
            self.root, self.getName("noTransform"), transform.getTransform(self.root)
        )
        self.no_transform.attr("inheritsTransform").set(False)
        self.no_transform.attr("visibility").set(False)
        ymt_util.setKeyableAttributesDontLockVisibility([self.driver_root, self.detail_root, self.no_transform], [])

        self.anchor_npos = []
        self.anchor_ctls = []
        self._add_anchor_controls()

        self.curl_npos = []
        self.curl_ctls = []
        self._add_curl_controls()

        self.detail_specs = self._collect_detail_specs()
        self.detail_npos = []
        self.detail_aim_npos = []
        self.detail_ctls = []
        self._add_detail_controls()

        self.sliding_surface = None
        self.surface_skin_joints = []
        if self.placement_mode == "surface":
            self._add_surface()

    def addAttributes(self) -> None:
        """Create animator attributes."""
        self.curlBlend_att = self.addAnimParam("curlBlend", "Curl Blend", "double", 1.0, 0.0, 1.0)
        self.driverBlend_att = self.addAnimParam("driverBlend", "Driver Blend", "double", 1.0, 0.0, 1.0)

    def addOperators(self) -> None:
        """Connect driver rotations and optional rivets."""
        self._ensure_rotation_driver_plugin()
        self._connect_curl_spaces()
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
        pm.orientConstraint(refs["root_ctl"], self.anchor_npos[0][0], mo=True)
        for anchor_name, anchor_npos in zip(self.anchor_names[1:], self.anchor_npos[1:]):
            pm.parentConstraint(refs[anchor_name], anchor_npos[0], mo=True)

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
            matrix = self._curl_matrix(index)
            npo = primitive.addTransform(self.driver_root, self.getName("curl%s_npo" % index), matrix)
            ctl = self.addCtl(
                npo,
                "curl%s_ctl" % index,
                matrix,
                self.color_ik,
                "sphere",
                w=self.ctl_size,
                tp=self.anchor_ctls[min(index + 1, len(self.anchor_ctls) - 1)][0],
            )
            attribute.setKeyableAttributes(ctl, ["tx", "ty", "tz"])
            attribute.setInvertMirror(ctl, ["tx", "ty", "tz"])
            self.curl_npos.append(npo)
            self.curl_ctls.append(ctl)

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
        upper_points = self.anchor_positions
        lower_points = [
            self._position_from_u_and_offset(u, self._max_lower_edge_offset_at_u(u)) for u in self._anchor_u_values()
        ]
        upper_curve = cmds.curve(
            n=self.getName("ribbonUpper_crv"), d=3, p=[self._point_tuple(point) for point in upper_points]
        )
        lower_curve = cmds.curve(
            n=self.getName("ribbonLower_crv"), d=3, p=[self._point_tuple(point) for point in lower_points]
        )
        surface = cmds.loft(
            upper_curve,
            lower_curve,
            n=self.getName("ribbonSurface"),
            ch=False,
            u=True,
            c=False,
            ar=True,
            d=3,
            ss=max(1, len(self.row_names)),
            rn=False,
            po=0,
            rsn=True,
        )[0]
        cmds.delete(upper_curve, lower_curve)
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

    def _add_surface_skin_joints(self) -> None:
        for ctl in self._surface_skin_ctls():
            joint = primitive.addJoint(
                ctl,
                self.getName("%s_surfaceSkin_jnt" % self._node_name(ctl).replace(self.getName(""), "")),
                transform.getTransform(ctl),
                vis=False,
            )
            ymt_util.setKeyableAttributesDontLockVisibility(joint, [])
            self.surface_skin_joints.append(joint)

    def _connect_surface_rivets(self) -> None:
        for npo in self.detail_npos:
            rivets = ymt_util.apply_rivet_constrain_to_selected(self.sliding_surface, npo)
            rivet = pm.PyNode(rivets[0])
            pm.parent(rivet, self.no_transform, relative=True)
            pm.pointConstraint(rivet, npo, mo=True)
            ymt_util.setKeyableAttributesDontLockVisibility(rivet, [])

    def _connect_curl_spaces(self) -> None:
        for segment_index, npo in enumerate(self.curl_npos):
            targets = []
            for layer_index in range(len(self.anchor_offsets)):
                targets.append(self.anchor_ctls[segment_index][layer_index])
                targets.append(self.anchor_ctls[segment_index + 1][layer_index])
            pm.pointConstraint(*targets, npo, mo=True)
            pm.orientConstraint(
                self.anchor_ctls[segment_index][0],
                self.anchor_ctls[segment_index + 1][0],
                npo,
                mo=True,
            )

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
            cmds.aimConstraint(
                self._node_name(curl_ctl),
                self._node_name(aim_npo),
                maintainOffset=True,
                aimVector=(1, 0, 0),
                upVector=(0, 1, 0),
                worldUpType="objectrotation",
                worldUpObject=self._node_name(self.driver_root),
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

    def _flat_anchor_ctls(self) -> list[object]:
        return [ctl for anchor_ctls in self.anchor_ctls for ctl in anchor_ctls]

    def _surface_skin_ctls(self) -> list[object]:
        return self._flat_anchor_ctls() + list(self.curl_ctls)

    def _detail_name(self, spec: DetailSpec) -> str:
        if spec["section"] < 0:
            return "%s_%02d" % (spec["row"], spec["col"])
        return "%s_%02d_%02d" % (spec["row"], spec["section"], spec["col"])

    def _point_tuple(self, point: VectorLike) -> tuple[float, float, float]:
        return (point[0], point[1], point[2])

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
            position = transform.getPositionFromMatrix(matrix)
            u = self._u_from_position(position)
            v = self._v_from_row_name(row)
            specs.append(
                self._detail_spec(
                    row,
                    -1,
                    col,
                    self._anchor_layer_from_position(position, u),
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
        span_float = max(0.0, min(0.999, u)) * (len(self.anchor_names) - 1)
        span = math.floor(span_float)
        local = span_float - span
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
        points = self.anchor_positions
        span_float = max(0.0, min(0.999, u)) * (len(points) - 1)
        span = math.floor(span_float)
        local = span_float - span
        return points[span] + ((points[span + 1] - points[span]) * local)

    def _collect_anchor_offsets(self) -> list[float]:
        offsets = sorted({offset for profile in self.lower_edge_profiles for offset in profile})
        if not offsets:
            raise RuntimeError("ymt_feather_ribbon_01 requires at least one lower edge offset.")
        return offsets

    def _anchor_layer_from_offset(self, offset: float) -> int:
        if not self.anchor_offsets:
            raise RuntimeError("ymt_feather_ribbon_01 requires at least one anchor offset layer.")
        return min(range(len(self.anchor_offsets)), key=lambda index: abs(self.anchor_offsets[index] - offset))

    def _anchor_layer_from_position(self, position: VectorLike, u: float) -> int:
        return self._anchor_layer_from_offset(self._offset_from_position(position, u))

    def _offset_from_position(self, position: VectorLike, u: float) -> float:
        return max(0.0, ((position - self._base_position_from_u(u)) * self.lower_axis) / self.size)

    def _anchor_layer_position(self, layer_index: int, anchor_index: int) -> VectorLike:
        offset = self.anchor_offsets[layer_index]
        return self.anchor_positions[anchor_index] + (self.lower_axis * offset * self.size)

    def _curl_matrix(self, index: int) -> object:
        matrix = self._curl_basis_matrix(index)
        guide_matrix = self.guide.tra.get("curl%s" % index)
        if guide_matrix is None:
            return matrix
        return transform.setMatrixPosition(
            matrix,
            transform.getPositionFromMatrix(guide_matrix),
        )

    def _curl_basis_matrix(self, index: int) -> object:
        matrix = transform.getTransformLookingAt(
            self.anchor_positions[index],
            self.anchor_positions[index + 1],
            self.lower_axis,
            axis="xy",
            negate=False,
        )
        return transform.setMatrixPosition(matrix, self._curl_position(index))

    def _curl_position(self, index: int) -> VectorLike:
        u = (index + 0.5) / max(len(self.anchor_positions) - 1, 1)
        offset = self._max_lower_edge_offset_at_u(u)
        return self._position_from_u_and_offset(u, offset)

    def _anchor_u_values(self) -> list[float]:
        point_count = max(len(self.anchor_positions) - 1, 1)
        return [index / point_count for index in range(len(self.anchor_positions))]

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

    def _u_from_position(self, position: VectorLike) -> float:
        root = self.anchor_positions[0]
        hand = self.anchor_positions[-1]
        axis = hand - root
        length = max(axis.length(), 0.001)
        axis.normalize()
        return max(0.0, min(1.0, ((position - root) * axis) / length))

    def _v_from_row_name(self, row: str) -> float:
        if row in self.row_names:
            return (self.row_names.index(row) + 0.5) / max(len(self.row_names), 1)
        if row.isdigit():
            return (int(row) + 0.5) / max(len(self.row_names), 1)
        return 0.5

    def _get_anchor_positions(self) -> list[VectorLike]:
        positions = self._get_parent_guide_anchor_positions()
        if positions is None:
            raise RuntimeError(
                "ymt_feather_ribbon_01 requires parent ymt_birdwing_3jnt_01 guide apos: root, elbow, wrist, eff."
            )
        return positions

    def _get_parent_chain_lower_axis(self) -> VectorLike:
        root, elbow, wrist, hand = self.anchor_positions
        tangent = hand - root
        tangent_length = tangent.length()
        if tangent_length < 0.001:
            raise RuntimeError("ymt_feather_ribbon_01 requires a valid parent wing root-to-eff guide axis.")
        tangent.normalize()

        lower_axis = self._point_plane_offset_axis(elbow, root, tangent)
        lower_axis += self._point_plane_offset_axis(wrist, root, tangent)
        if lower_axis.length() < 0.001:
            raise RuntimeError("ymt_feather_ribbon_01 requires a non-flat parent wing chain plane.")
        return lower_axis.normal()

    def _point_plane_offset_axis(self, point: VectorLike, root: VectorLike, tangent: VectorLike) -> VectorLike:
        offset = point - root
        projected = tangent * (offset * tangent)
        return offset - projected

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

    def _get_parent_feather_refs(self) -> Optional[dict[str, object]]:  # noqa: UP045
        parent_comp = getattr(self, "parent_comp", None)
        if parent_comp is None or not hasattr(parent_comp, "get_feather_ribbon_refs"):
            return None
        return parent_comp.get_feather_ribbon_refs()

    def _get_world_position(self, node: object) -> VectorLike:
        get_translation = getattr(node, "getTranslation", None)
        if callable(get_translation):
            return get_translation(space="world")
        return datatypes.Vector(cmds.xform(str(node), q=True, ws=True, t=True))

    def _parse_detail_guide_name(self, local_name: str) -> Optional[tuple[str, int]]:  # noqa: UP045
        for pattern in DETAIL_GUIDE_PATTERNS:
            match = pattern.match(local_name)
            if match:
                return match.group("row"), int(match.group("col"))
        return None

    def _ensure_rotation_driver_plugin(self) -> None:
        if cmds.pluginInfo("rotationDriver", query=True, loaded=True):
            return
        try:
            cmds.loadPlugin("rotationDriver")
        except RuntimeError as exc:
            raise RuntimeError("ymt_feather_ribbon_01 requires the rotationDriver plugin.") from exc

    def _parse_row_names(self, value: str) -> list[str]:
        names = [item.strip() for item in value.split(",") if item.strip()]
        return names or ["primary", "secondary", "tertial"]

    def _parse_row_counts(self, value: str, row_names: list[str]) -> list[int]:
        raw_counts = [item.strip() for item in value.split(",") if item.strip()]
        counts = []
        for item in raw_counts:
            try:
                counts.append(max(1, int(item)))
            except ValueError:
                counts.append(1)
        while len(counts) < len(row_names):
            counts.append(counts[-1] if counts else 1)
        return counts[: len(row_names)]

    def _parse_row_u_ranges(self, value: str, row_names: list[str]) -> list[tuple[float, float]]:
        ranges = []
        for item in [part.strip() for part in value.split(",") if part.strip()]:
            try:
                start, end = item.split(":", 1)
                ranges.append((float(start), float(end)))
            except ValueError:
                ranges.append((0.0, 1.0))
        while len(ranges) < len(row_names):
            ranges.append((0.0, 1.0))
        return ranges[: len(row_names)]

    def _parse_lower_edge_profiles(self, value: str, row_names: list[str]) -> list[list[float]]:
        if not value.strip():
            raise RuntimeError("ymt_feather_ribbon_01 lowerEdgeOffsets cannot be empty.")

        named_profiles = {}
        unnamed_profiles = []
        for item in self._split_lower_edge_profile_rows(value):
            name, _, raw_profile = item.partition(":")
            if raw_profile:
                profile = self._parse_float_list(raw_profile)
                if not profile:
                    raise RuntimeError("ymt_feather_ribbon_01 lowerEdgeOffsets row '%s' has no numeric values." % name)
                named_profiles[name.strip()] = profile
            else:
                profile = self._parse_float_list(name)
                if not profile:
                    raise RuntimeError("ymt_feather_ribbon_01 lowerEdgeOffsets contains a row with no numeric values.")
                unnamed_profiles.append(profile)

        profiles = []
        for index, row_name in enumerate(row_names):
            if row_name in named_profiles:
                profile = named_profiles[row_name]
            elif index < len(unnamed_profiles):
                profile = unnamed_profiles[index]
            else:
                raise RuntimeError(
                    "ymt_feather_ribbon_01 lowerEdgeOffsets is missing a profile for row '%s'." % row_name
                )
            profiles.append(profile)
        return profiles

    def _split_lower_edge_profile_rows(self, value: str) -> list[str]:
        rows = []
        for line in value.replace(";", "\n").splitlines():
            item = line.strip()
            if item:
                rows.append(item)
        return rows

    def _parse_float_list(self, value: str) -> list[float]:
        values = []
        for item in [part.strip() for part in value.split(",") if part.strip()]:
            try:
                values.append(max(0.0, float(item)))
            except ValueError:
                continue
        return values
