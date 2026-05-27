"""Bird tail feather component."""

from __future__ import annotations

import importlib
import math
from typing import TYPE_CHECKING, cast

import maya.cmds as cmds


try:
    pm = importlib.import_module("mgear.pymaya")
except ImportError:
    pm = importlib.import_module("pymel.core")
try:
    datatypes = importlib.import_module("mgear.pymaya.datatypes")
except ImportError:
    datatypes = importlib.import_module("pymel.core.datatypes")

from mgear.core import primitive, transform
from mgear.shifter import component

import ymt_shifter_utility as ymt_util

from . import detail_config

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ymt_shifter_utility.type_protocols import MatrixLike, PlugLike, PymelNode, VectorLike


DetailKey = tuple[str, int, int]
MAYA_2024_API_VERSION = 20240000
ROTATE_ORDER_XYZ = 0
MAIN_SIDES = ("L", "C", "R")
CURL_SIDES = ("L", "R")
SOLVER_SIMPLE_MATRIX_CONNECTION = "simpleMatrixConnection"
SOLVER_NURBS_RIBBON_WITH_CURL = "nurbsRibbonWithCurl"


class Component(component.Main):
    """Shifter component class."""

    solver_modes: tuple[str, str] = (SOLVER_SIMPLE_MATRIX_CONNECTION, SOLVER_NURBS_RIBBON_WITH_CURL)

    def addObjects(self) -> None:
        """Add main C/L/R controls, detail controls, and optional ribbon surfaces."""
        self.WIP: bool = self.options["mode"]
        self.ctl_size: float = self.size * float(self.settings["ctlSize"]) * 0.2
        self.solver_mode: str = self._parse_solver_mode(self.settings["solverMode"])
        self.group_names: list[str] = detail_config.parse_group_names(self.settings["groupNames"])
        self.group_row_counts: list[int] = detail_config.parse_group_row_counts(
            self.settings["groupRowCounts"], self.group_names
        )
        self.group_column_depths: list[list[float]] = detail_config.parse_group_column_depths(
            self.settings["groupColumnDepths"], self.group_names
        )
        self.group_main_influence_scales: list[float] = detail_config.parse_group_main_influence_scales(
            self.settings["groupMainInfluenceScales"], self.group_names
        )
        self.group_curl_influence_scales: list[float] = detail_config.parse_group_curl_influence_scales(
            self.settings["groupCurlInfluenceScales"], self.group_names
        )
        self.surface_curl_max_weight: float = float(self.settings["surfaceCurlMaxWeight"])
        self.surface_curl_edge_scale: float = float(self.settings["surfaceCurlEdgeScale"])
        self.detail_curl_rot_multipliers: list[float] = detail_config.normalize_detail_curl_rot_multipliers(
            self.settings["detailCurlRotMults"],
            max(len(depths) for depths in self.group_column_depths),
        )
        self.tail_normal: VectorLike = self._tail_normal()

        self.main_root: PymelNode = primitive.addTransform(
            self.root, self.getName("main"), transform.getTransform(self.root)
        )
        self.detail_root: PymelNode = primitive.addTransform(
            self.root, self.getName("details"), transform.getTransform(self.root)
        )
        self.no_transform: PymelNode = primitive.addTransform(
            self.root, self.getName("noTransform"), transform.getTransform(self.root)
        )
        self.no_transform.attr("visibility").set(False)
        ymt_util.setKeyableAttributesDontLockVisibility([self.main_root, self.detail_root, self.no_transform], [])

        self.main_depths: list[float] = self._main_control_depths()
        self.main_ctls: dict[tuple[str, int], PymelNode] = {}
        self._add_main_controls()

        self.detail_specs: list[tuple[str, int, int, VectorLike]] = self._collect_detail_specs()
        self.detail_ctls: dict[DetailKey, PymelNode] = {}
        if self.solver_mode == SOLVER_NURBS_RIBBON_WITH_CURL:
            self._add_ribbon_objects()
        else:
            self._add_expression_objects()

    def addOperators(self) -> None:
        """Connect selected solver operators."""
        if self.solver_mode == SOLVER_NURBS_RIBBON_WITH_CURL:
            self._connect_ribbon_operators()
        else:
            self._connect_main_control_drivers()

    def addAttributes(self) -> None:
        """Add animator-facing group influence attributes."""
        self.group_main_influence_attrs: dict[str, PlugLike] = {}
        self.group_curl_influence_attrs: dict[str, PlugLike] = {}
        for group, default_value in zip(self.group_names, self.group_main_influence_scales):
            self.group_main_influence_attrs[group] = self.addAnimParam(
                "%sMainInfluence" % group,
                "%s Main Influence" % self._display_group_name(group),
                "double",
                default_value,
                0.0,
                2.0,
            )
        for group, default_value in zip(self.group_names, self.group_curl_influence_scales):
            self.group_curl_influence_attrs[group] = self.addAnimParam(
                "%sCurlInfluence" % group,
                "%s Curl Influence" % self._display_group_name(group),
                "double",
                default_value,
                0.0,
                2.0,
            )
        if self.solver_mode == SOLVER_NURBS_RIBBON_WITH_CURL:
            self.detail_curl_rot_mult_attrs: list[PlugLike] = [
                self.addAnimParam(
                    "detailCurlRotMult%s" % col,
                    "Detail Curl Rot Mult %s" % col,
                    "double",
                    self.detail_curl_rot_multipliers[col],
                    0.0,
                    2.0,
                )
                for col in range(len(self.detail_curl_rot_multipliers))
            ]

    def setRelation(self) -> None:
        """Set guide-to-rig relations."""
        self.relatives["root"] = self.main_ctls[("C", 0)]
        self.controlRelatives["root"] = self.main_ctls[("C", 0)]
        self.aliasRelatives["root"] = "tailRoot"

        for index, (group, row, col, _position) in enumerate(self.detail_specs):
            key = (group, row, col)
            name = "%s_%s_%s" % key
            ctl = self.detail_ctls[key]
            self.relatives[name] = ctl
            self.controlRelatives[name] = ctl
            self.aliasRelatives[name] = name
            self.jointRelatives[name] = index

    def addConnection(self) -> None:
        self.connections["standard"] = self.connect_standard

    def connect_standard(self) -> None:
        self.parent.addChild(self.root)

    def _add_expression_objects(self) -> None:
        self.detail_npos: dict[DetailKey, PymelNode] = {}
        self.detail_pos_offs: dict[DetailKey, PymelNode] = {}
        self.detail_rot_offs: dict[DetailKey, PymelNode] = {}
        self._add_detail_controls()

    def _add_ribbon_objects(self) -> None:
        self._validate_ribbon_runtime_requirements()
        self.ribbon_surfaces: dict[str, PymelNode] = {}
        self.ribbon_surface_shapes: dict[str, str] = {}
        self.main_surface_skin_joints: dict[tuple[str, int], PymelNode] = {}
        self.curl_npos: dict[str, PymelNode] = {}
        self.curl_offset_npos: dict[str, PymelNode] = {}
        self.curl_ctls: dict[str, PymelNode] = {}
        self.group_curl_deforms: dict[tuple[str, str], PymelNode] = {}
        self.group_curl_surface_skin_joints: dict[tuple[str, str], PymelNode] = {}
        self.detail_rivet_refs: dict[DetailKey, PymelNode] = {}
        self.detail_aim_refs: dict[DetailKey, PymelNode] = {}
        self.detail_chain_npos: dict[DetailKey, PymelNode] = {}
        self.detail_aim_npos: dict[DetailKey, PymelNode] = {}
        self.detail_curl_npos: dict[DetailKey, PymelNode] = {}
        self._add_ribbon_curl_controls()
        self._add_ribbon_detail_controls()
        self._add_ribbon_surfaces()

    def _parse_solver_mode(self, value: str | int) -> str:
        try:
            index = int(value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("ymt_birdtail_01 solverMode must be an enum index.") from exc
        if index < 0 or index >= len(self.solver_modes):
            raise RuntimeError("ymt_birdtail_01 solverMode index is out of range: %s." % index)
        return self.solver_modes[index]

    def _add_main_controls(self) -> None:
        side_specs = [
            ("C", "centerEnd", "circle"),
            ("L", "leftEnd", "cube"),
            ("R", "rightEnd", "cube"),
        ]
        root_position = self.guide.pos["root"]
        for side, guide_name, icon in side_specs:
            parent = self.main_root
            tag_parent = self.parentCtlTag
            endpoint = self.guide.pos[guide_name]
            for col, depth in enumerate(self.main_depths):
                position = root_position + ((endpoint - root_position) * depth)
                matrix = self._radial_transform(position, endpoint)
                with ymt_util.overrideNamingAttributeTemporary(self, side=side):
                    npo = primitive.addTransform(parent, self.getName("tail_main_%02d_npo" % col), matrix)
                    ctl = self.addCtl(
                        npo,
                        "tail_main_%02d_ctl" % col,
                        matrix,
                        self._side_color(side, "fk"),
                        icon,
                        w=self.ctl_size * 2.0,
                        d=self.ctl_size * 1.0,
                        h=self.ctl_size * 0.3,
                        po=datatypes.Vector(self.ctl_size, 0.0, 0.0),
                        tp=tag_parent,
                    )
                ymt_util.setKeyableAttributesDontLockVisibility(ctl, ["tx", "ty", "tz", "rx", "ry", "rz"])
                self.main_ctls[(side, col)] = ctl
                parent = ctl
                tag_parent = ctl

    def _main_control_depths(self) -> list[float]:
        column_count = max(len(depths) for depths in self.group_column_depths)
        if column_count == 1:
            return [0.0]
        return [float(col) / float(column_count - 1) for col in range(column_count)]

    def _tail_normal(self) -> VectorLike:
        root_position = self.guide.pos["root"]
        left_vector = self.guide.pos["leftEnd"] - root_position
        right_vector = self.guide.pos["rightEnd"] - root_position
        normal = left_vector ^ right_vector
        if normal.length() < 0.001:
            center_vector = self.guide.pos["centerEnd"] - root_position
            normal = left_vector ^ center_vector
        if normal.length() < 0.001:
            normal = datatypes.Vector(0.0, 1.0, 0.0)
        normal.normalize()
        return normal

    def _collect_detail_specs(self) -> list[tuple[str, int, int, VectorLike]]:
        specs = []
        for local_name, position in self.guide.pos.items():
            parsed = detail_config.parse_detail_guide_name(local_name)
            if parsed is None:
                continue
            group, row, col = parsed
            specs.append((group, row, col, position))
        if not specs:
            raise RuntimeError("ymt_birdtail_01 requires generated detail guide locators.")
        sorted_specs = sorted(specs, key=lambda item: (item[0], item[1], item[2]))
        self._validate_detail_specs(sorted_specs)
        return sorted_specs

    def _validate_detail_specs(self, specs: list[tuple[str, int, int, VectorLike]]) -> None:
        found_keys = {(group, row, col) for group, row, col, _position in specs}
        expected_keys = set()
        column_counts_by_group = {
            group_name: len(depths) for group_name, depths in zip(self.group_names, self.group_column_depths)
        }
        row_counts_by_group = dict(zip(self.group_names, self.group_row_counts))
        for group, row, col, _position in specs:
            if group not in row_counts_by_group:
                raise RuntimeError("ymt_birdtail_01 detail guide references unknown group: %s." % group)
            if row >= row_counts_by_group[group]:
                raise RuntimeError("ymt_birdtail_01 detail guide row is out of range: %s_%s_%s." % (group, row, col))
            if col >= column_counts_by_group[group]:
                raise RuntimeError("ymt_birdtail_01 detail guide col is out of range: %s_%s_%s." % (group, row, col))
        for group_name in self.group_names:
            for row in range(row_counts_by_group[group_name]):
                for col in range(column_counts_by_group[group_name]):
                    expected_keys.add((group_name, row, col))
        missing_keys = sorted(expected_keys.difference(found_keys))
        if missing_keys:
            missing_name = "%s_%s_%s_loc" % missing_keys[0]
            raise RuntimeError("ymt_birdtail_01 detail guide is missing %s." % missing_name)

    def _add_detail_controls(self) -> None:
        for group, row, col, position in self.detail_specs:
            key = (group, row, col)
            matrix = self._detail_transform(position)
            node_name = "%s_%02d_%02d" % key
            if col == 0:
                parent = self.detail_root
            else:
                parent = self.detail_ctls[(group, row, col - 1)]
            npo = primitive.addTransform(parent, self.getName(node_name + "_npo"), matrix)
            pos_off = primitive.addTransform(npo, self.getName(node_name + "_pos_off"), matrix)
            rot_off = primitive.addTransform(pos_off, self.getName(node_name + "_rot_off"), matrix)
            ctl = self.addCtl(
                rot_off,
                node_name + "_ctl",
                matrix,
                self._detail_color(group, self._dominant_main_side_for_row(group, row)),
                "circle",
                w=self.ctl_size,
                d=self.ctl_size,
                ro=datatypes.Vector(math.radians(90.0), math.radians(90.0), 0.0),
                tp=self.parentCtlTag if col == 0 else self.detail_ctls[(group, row, col - 1)],
            )
            ymt_util.setKeyableAttributesDontLockVisibility(ctl, ["tx", "ty", "tz", "rx", "ry", "rz"])
            self.detail_npos[key] = npo
            self.detail_pos_offs[key] = pos_off
            self.detail_rot_offs[key] = rot_off
            self.detail_ctls[key] = ctl

        if self.settings["addJoints"]:
            self._add_detail_joint_positions()

    def _add_detail_joint_positions(self) -> None:
        grouped_keys = sorted({(group, row) for group, row, _col, _position in self.detail_specs})
        for group, row in grouped_keys:
            keys = sorted(
                [key for key in self.detail_ctls if key[0] == group and key[1] == row],
                key=lambda item: item[2],
            )
            for index, key in enumerate(keys):
                joint_name = "%s_%02d_%02d" % key
                if index == 0:
                    self.jnt_pos.append([self.detail_ctls[key], joint_name, "parent_relative_jnt", False])
                else:
                    self.jnt_pos.append([self.detail_ctls[key], joint_name, None, False])

    def _add_ribbon_curl_controls(self) -> None:
        side_specs = [
            ("L", "curlLeft", "leftEnd"),
            ("R", "curlRight", "rightEnd"),
        ]
        for side, guide_name, fallback_name in side_specs:
            position = self.guide.pos.get(guide_name, self.guide.pos[fallback_name])
            matrix = self._radial_transform(position, self.guide.pos["root"])
            with ymt_util.overrideNamingAttributeTemporary(self, side=side):
                npo = primitive.addTransform(self.main_root, self.getName("tail_curl_npo"), matrix)
                offset_npo = primitive.addTransform(npo, self.getName("tail_curl_offset_npo"), matrix)
                ctl = self.addCtl(
                    offset_npo,
                    "tail_curl_ctl",
                    matrix,
                    self._side_color(side, "ik"),
                    "sphere",
                    w=self.ctl_size * 1.2,
                    tp=self.main_ctls[(side, min(len(self.main_depths) - 1, max(0, len(self.main_depths) // 2)))],
                )
            ymt_util.setKeyableAttributesDontLockVisibility(ctl, ["tx", "ty", "tz", "rx", "ry", "rz"])
            self.curl_npos[side] = npo
            self.curl_offset_npos[side] = offset_npo
            self.curl_ctls[side] = ctl

    def _add_ribbon_detail_controls(self) -> None:
        for group, row, col, position in self.detail_specs:
            key = (group, row, col)
            matrix = self._ribbon_detail_transform(group, row, col, position)
            node_name = "%s_%02d_%02d" % key
            rivet_ref = primitive.addTransform(self.no_transform, self.getName(node_name + "_rivet_ref"), matrix)
            aim_ref = primitive.addTransform(rivet_ref, self.getName(node_name + "_aim_ref"), matrix)
            ymt_util.setKeyableAttributesDontLockVisibility(rivet_ref, ["tx", "ty", "tz"])
            ymt_util.setKeyableAttributesDontLockVisibility(aim_ref, ["tx", "ty", "tz", "rx", "ry", "rz"])

            if col == 0:
                chain_parent = self.detail_root
                tag_parent = self.curl_ctls[self._dominant_side_for_row(group, row)]
            else:
                previous_key = (group, row, col - 1)
                chain_parent = self.detail_ctls[previous_key]
                tag_parent = self.detail_ctls[previous_key]

            chain_npo = primitive.addTransform(chain_parent, self.getName(node_name + "_chain_npo"), matrix)
            aim_npo = primitive.addTransform(chain_npo, self.getName(node_name + "_aim_npo"), matrix)
            curl_npo = primitive.addTransform(aim_npo, self.getName(node_name + "_curl_npo"), matrix)
            ctl = self.addCtl(
                curl_npo,
                node_name + "_ctl",
                matrix,
                self._detail_color(group, self._dominant_main_side_for_row(group, row)),
                "square",
                w=self.ctl_size,
                d=self.ctl_size,
                tp=tag_parent,
            )
            ymt_util.setKeyableAttributesDontLockVisibility(ctl, ["tx", "ty", "tz", "rx", "ry", "rz"])
            self.detail_rivet_refs[key] = rivet_ref
            self.detail_aim_refs[key] = aim_ref
            self.detail_chain_npos[key] = chain_npo
            self.detail_aim_npos[key] = aim_npo
            self.detail_curl_npos[key] = curl_npo
            self.detail_ctls[key] = ctl

        if self.settings["addJoints"]:
            self._add_detail_joint_positions()

    def _add_ribbon_surfaces(self) -> None:
        self._add_main_surface_skin_joints()
        for group in self.group_names:
            self._add_group_curl_deforms(group)
            surface = self._create_group_ribbon_surface(group)
            self.ribbon_surfaces[group] = surface
            self.ribbon_surface_shapes[group] = self._surface_shape_name(self._node_name(surface))
            self._skin_group_ribbon_surface(group, surface)

    def _add_main_surface_skin_joints(self) -> None:
        for key, ctl in self.main_ctls.items():
            joint = primitive.addJoint(
                ctl,
                self.getName("%s_%02d_surfaceSkin_jnt" % key),
                transform.getTransform(ctl),
                vis=False,
            )
            ymt_util.setKeyableAttributesDontLockVisibility(joint, [])
            self.main_surface_skin_joints[key] = joint

    def _add_group_curl_deforms(self, group: str) -> None:
        for side in CURL_SIDES:
            matrix = transform.getTransform(self.curl_ctls[side])
            deform = primitive.addTransform(
                self.curl_offset_npos[side],
                self.getName("%s_%s_curl_deform" % (group, side)),
                matrix,
            )
            joint = primitive.addJoint(
                deform,
                self.getName("%s_%s_curl_surfaceSkin_jnt" % (group, side)),
                matrix,
                vis=False,
            )
            ymt_util.setKeyableAttributesDontLockVisibility([deform, joint], [])
            self.group_curl_deforms[(group, side)] = deform
            self.group_curl_surface_skin_joints[(group, side)] = joint

    def _create_group_ribbon_surface(self, group: str) -> PymelNode:
        row_count = self._group_row_count(group)
        col_count = self._group_column_count(group)
        if row_count < 2 or col_count < 2:
            raise RuntimeError("ymt_birdtail_01 ribbon mode requires at least 2 rows and 2 columns for %s." % group)
        surface = cmds.nurbsPlane(
            n=self.getName("%s_ribbonSurface" % group),
            ch=False,
            d=1,
            u=row_count - 1,
            v=col_count - 1,
        )[0]
        cmds.xform(surface, ws=True, t=self._point_tuple(self.guide.pos["root"]))
        shape = self._surface_shape_name(surface)
        specs_by_key = {(spec_group, row, col): position for spec_group, row, col, position in self.detail_specs}
        for row in range(row_count):
            for col in range(col_count):
                key = (group, row, col)
                if key not in specs_by_key:
                    raise RuntimeError("ymt_birdtail_01 ribbon surface is missing detail guide %s_%s_%s." % key)
                cmds.xform(
                    "%s.cv[%s][%s]" % (shape, row, col),
                    ws=True,
                    t=self._point_tuple(specs_by_key[key]),
                )
        surface_node = pm.PyNode(surface)
        pm.parent(surface_node, self.no_transform)
        surface_node.attr("visibility").set(self.WIP)
        return surface_node

    def _skin_group_ribbon_surface(self, group: str, surface: PymelNode) -> None:
        influence_nodes = list(self.main_surface_skin_joints.values())
        influence_nodes.extend(self.group_curl_surface_skin_joints[(group, side)] for side in CURL_SIDES)
        skin = cmds.skinCluster(
            *[self._node_name(node) for node in influence_nodes],
            self._node_name(surface),
            tsb=True,
            n=self.getName("%s_ribbonSurface_skinCluster" % group),
        )[0]
        self._set_local_relative_space_mode(skin)
        self._set_group_ribbon_surface_skin_weights(group, skin)

    def _set_group_ribbon_surface_skin_weights(self, group: str, skin: str) -> None:
        shape = self.ribbon_surface_shapes[group]
        row_count = self._group_row_count(group)
        col_count = self._group_column_count(group)
        cmds.setAttr(skin + ".normalizeWeights", 0)
        for row in range(row_count):
            row_ratio = self._surface_row_ratio(row, row_count)
            main_weights = self._main_control_weights(row_ratio)
            curl_weights = self._curl_control_weights(row_ratio)
            curl_envelope = self._curl_fan_envelope(row_ratio)
            for col in range(col_count):
                depth = self._group_column_depth(group, col)
                curl_strength = max(0.0, min(1.0, depth * self.surface_curl_max_weight * curl_envelope))
                main_strength = max(0.0, 1.0 - curl_strength)
                entries = []
                main_col = min(col, len(self.main_depths) - 1)
                for side, weight in zip(MAIN_SIDES, main_weights):
                    entries.append(
                        (self._node_name(self.main_surface_skin_joints[(side, main_col)]), weight * main_strength)
                    )
                for side, weight in zip(CURL_SIDES, curl_weights):
                    entries.append(
                        (
                            self._node_name(self.group_curl_surface_skin_joints[(group, side)]),
                            weight * curl_strength,
                        )
                    )
                component = "%s.cv[%s][%s]" % (shape, row, col)
                cmds.skinPercent(skin, component, transformValue=entries, normalize=False)
        cmds.setAttr(skin + ".normalizeWeights", 1)
        cmds.skinCluster(skin, edit=True, forceNormalizeWeights=True)

    def _ribbon_detail_transform(self, group: str, row: int, col: int, position: VectorLike) -> MatrixLike:
        next_position = self._detail_position((group, row, col + 1))
        if next_position is not None:
            return self._radial_transform(position, next_position)
        previous_position = self._detail_position((group, row, col - 1))
        if previous_position is not None:
            return self._radial_transform(position, position + (position - previous_position))
        return self._detail_transform(position)

    def _detail_position(self, key: DetailKey) -> VectorLike | None:
        for group, row, col, position in self.detail_specs:
            if key == (group, row, col):
                return position
        return None

    def _connect_ribbon_operators(self) -> None:
        self._validate_ribbon_runtime_requirements()
        self._ensure_rotation_driver_plugin()
        self._connect_group_curl_deforms()
        self._connect_surface_rivets()
        self._connect_ribbon_detail_chain_roots()
        self._connect_ribbon_detail_aim_refs()
        self._connect_ribbon_detail_aim_rotations()
        self._connect_ribbon_detail_curl_rotations()

    def _connect_group_curl_deforms(self) -> None:
        for group in self.group_names:
            influence_attr = self.group_curl_influence_attrs[group]
            for side in CURL_SIDES:
                translate_attr = self._create_scaled_vector_output(
                    self._node_name(self.curl_ctls[side]) + ".translate",
                    influence_attr,
                    "%s_%s_curlTranslateInfluence" % (group, side),
                )
                cmds.connectAttr(translate_attr, self._node_name(self.group_curl_deforms[(group, side)]) + ".translate", force=True)

    def _connect_surface_rivets(self) -> None:
        for group, row, col, _position in self.detail_specs:
            key = (group, row, col)
            ref = self.detail_rivet_refs[key]
            surface = self.ribbon_surfaces[group]
            rivets = ymt_util.apply_rivet_constrain_to_selected(surface, ref)
            rivet = pm.PyNode(rivets[0])
            for rivet_name in rivets:
                uv_pins = (
                    cmds.listConnections(
                        rivet_name + ".offsetParentMatrix",
                        source=True,
                        destination=False,
                        type="uvPin",
                    )
                    or []
                )
                if not uv_pins:
                    raise RuntimeError("ymt_birdtail_01 could not find uvPin driving rivet: %s." % rivet_name)
                if len(uv_pins) > 1:
                    raise RuntimeError("ymt_birdtail_01 found multiple uvPins driving rivet: %s." % rivet_name)
                cmds.setAttr(uv_pins[0] + ".normalAxis", 1)
                cmds.setAttr(uv_pins[0] + ".tangentAxis", 0)
                self._set_local_relative_space_mode(uv_pins[0])
            pm.parent(rivet, self.no_transform, relative=True)
            pm.pointConstraint(rivet, ref, mo=True)
            ymt_util.setKeyableAttributesDontLockVisibility(rivet, [])

    def _connect_ribbon_detail_chain_roots(self) -> None:
        for group, row, col, _position in self.detail_specs:
            if col != 0:
                continue
            key = (group, row, col)
            pm.pointConstraint(self.detail_rivet_refs[key], self.detail_chain_npos[key], mo=True)

    def _connect_ribbon_detail_aim_refs(self) -> None:
        for group, row, col, _position in self.detail_specs:
            key = (group, row, col)
            next_key = (group, row, col + 1)
            if next_key in self.detail_rivet_refs:
                cmds.aimConstraint(
                    self._node_name(self.detail_rivet_refs[next_key]),
                    self._node_name(self.detail_aim_refs[key]),
                    maintainOffset=True,
                    aimVector=(1, 0, 0),
                    upVector=(0, 1, 0),
                    worldUpType="objectrotation",
                    worldUpObject=self._node_name(self.root),
                    worldUpVector=(0, 1, 0),
                )
                continue
            previous_key = (group, row, col - 1)
            if previous_key in self.detail_aim_refs:
                constraint = pm.orientConstraint(self.detail_aim_refs[previous_key], self.detail_aim_refs[key], mo=False)
                pm.setAttr(constraint.attr("interpType"), 0)

    def _connect_ribbon_detail_aim_rotations(self) -> None:
        for group, row, col, _position in self.detail_specs:
            key = (group, row, col)
            previous_key = (group, row, col - 1)
            previous_ref = self.detail_aim_refs.get(previous_key)
            rotate_attr = self._create_local_offset_rotation_node(
                self.detail_aim_refs[key],
                self.detail_aim_npos[key],
                "%s_%02d_%02d_detailAimApply" % key,
                previous_ref,
            )
            cmds.connectAttr(rotate_attr, self._node_name(self.detail_aim_npos[key]) + ".rotate", force=True)

    def _connect_ribbon_detail_curl_rotations(self) -> None:
        decomposers = {
            side: self._create_decompose_rotate(self.curl_ctls[side], self.getName("curl%s_detailDecomposeRotate" % side))
            for side in CURL_SIDES
        }
        for group, row, col, _position in self.detail_specs:
            key = (group, row, col)
            row_ratio = self._surface_row_ratio(row, self._group_row_count(group))
            curl_envelope = self._curl_fan_envelope(row_ratio)
            weights = tuple(weight * curl_envelope for weight in self._curl_control_weights(row_ratio))
            compose = self._compose_weighted_detail_curl_rotation_sources(
                [(decomposers[side], weight) for side, weight in zip(CURL_SIDES, weights) if weight > 0.0]
            )
            scaled_rotate_attr = self._create_scaled_rotate_node(
                compose + ".outRotate",
                self.detail_curl_rot_mult_attrs[min(col, len(self.detail_curl_rot_mult_attrs) - 1)],
                "%s_%02d_%02d_detailCurlRotateMult" % key,
            )
            rotate_attr = self._create_initial_offset_rotate_node(
                self.detail_curl_npos[key],
                scaled_rotate_attr,
                "%s_%02d_%02d_detailCurlRotate" % key,
            )
            cmds.connectAttr(rotate_attr, self._node_name(self.detail_curl_npos[key]) + ".rotate", force=True)

    def _compose_weighted_detail_curl_rotation_sources(self, sources: list[tuple[str, float]]) -> str:
        output_attrs = [("outBendV", -1.0), ("outBendH", -1.0), ("outRoll", -1.0)]
        sum_attrs = []
        for output_attr, sign in output_attrs:
            add_node = cmds.createNode("plusMinusAverage")
            cmds.setAttr(add_node + ".operation", 1)
            for index, source in enumerate(sources):
                decomposer, weight = source
                mult = cmds.createNode(self._multiply_node_type())
                cmds.connectAttr(decomposer + "." + output_attr, mult + ".input1")
                cmds.setAttr(mult + ".input2", weight * sign)
                cmds.connectAttr(mult + ".output", add_node + ".input1D[%s]" % index)
            sum_attrs.append(add_node + ".output1D")
        compose = cmds.createNode("composeRotate")
        cmds.setAttr(compose + ".rotateOrder", ROTATE_ORDER_XYZ)
        cmds.connectAttr(sum_attrs[0], compose + ".roll")
        cmds.connectAttr(sum_attrs[1], compose + ".bendH")
        cmds.connectAttr(sum_attrs[2], compose + ".bendV")
        return compose

    def _create_decompose_rotate(self, source: PymelNode, name: str) -> str:
        decompose_node = cmds.createNode("decomposeRotate", name=name)
        cmds.setAttr(decompose_node + ".rotateOrder", ROTATE_ORDER_XYZ)
        cmds.connectAttr(self._node_name(source) + ".rotate", decompose_node + ".rotate", force=True)
        return decompose_node

    def _create_scaled_rotate_node(self, rotate_attr: str, multiplier_attr: PlugLike, name: str) -> str:
        return self._create_scaled_vector_output(rotate_attr, multiplier_attr, name)

    def _create_local_offset_rotation_node(
        self,
        source: PymelNode,
        driven: PymelNode,
        name: str,
        previous_source: PymelNode | None = None,
    ) -> str:
        source_initial_matrix = source.getMatrix()
        driven_initial_matrix = driven.getMatrix()
        driver_initial_matrix = source_initial_matrix
        if previous_source is not None:
            previous_initial_matrix = previous_source.getMatrix()
            driver_initial_matrix = cast("MatrixLike", source_initial_matrix * previous_initial_matrix.inverse())
        offset_matrix = cast("MatrixLike", driver_initial_matrix.inverse() * driven_initial_matrix)
        mult = cmds.createNode("multMatrix", name=self.getName(name + "_mm"))
        cmds.connectAttr(self._node_name(source) + ".matrix", mult + ".matrixIn[0]", force=True)
        offset_index = 1
        if previous_source is not None:
            cmds.connectAttr(self._node_name(previous_source) + ".inverseMatrix", mult + ".matrixIn[1]", force=True)
            offset_index = 2
        cmds.setAttr(mult + ".matrixIn[%s]" % offset_index, *self._matrix_values(offset_matrix), type="matrix")
        decompose = cmds.createNode("decomposeMatrix", name=self.getName(name + "_dm"))
        cmds.connectAttr(mult + ".matrixSum", decompose + ".inputMatrix", force=True)
        cmds.setAttr(decompose + ".inputRotateOrder", ROTATE_ORDER_XYZ)
        return decompose + ".outputRotate"

    def _create_initial_offset_rotate_node(self, npo: PymelNode, driver_rotate_attr: str, name: str) -> str:
        initial_rotate = cmds.getAttr(self._node_name(npo) + ".rotate")[0]
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

    def _validate_ribbon_runtime_requirements(self) -> None:
        if int(cmds.about(apiVersion=True)) < MAYA_2024_API_VERSION:
            raise RuntimeError("ymt_birdtail_01 ribbon mode requires Maya 2024 or newer.")
        self._ensure_rotation_driver_plugin()

    def _ensure_rotation_driver_plugin(self) -> None:
        if cmds.pluginInfo("rotationDriver", query=True, loaded=True):
            return
        try:
            cmds.loadPlugin("rotationDriver")
        except RuntimeError as exc:
            raise RuntimeError("ymt_birdtail_01 ribbon mode requires the rotationDriver plugin.") from exc

    def _set_local_relative_space_mode(self, node: PymelNode | str) -> None:
        node_name = self._node_name(node)
        attr = node_name + ".relativeSpaceMode"
        if not cmds.objExists(attr):
            raise RuntimeError("ymt_birdtail_01 node does not support relativeSpaceMode: %s." % node_name)
        cmds.setAttr(attr, 1)


    def _detail_transform(self, position: VectorLike) -> MatrixLike:
        root_position = self.guide.pos["root"]
        direction = position - root_position
        if direction.length() < 0.001:
            return self._radial_transform(position, self.guide.pos["centerEnd"])
        return self._radial_transform(position, position + direction)

    def _radial_transform(self, position: VectorLike, target: VectorLike) -> MatrixLike:
        root_position = self.guide.pos["root"]
        direction = target - position
        if direction.length() < 0.001:
            direction = target - root_position
        if direction.length() < 0.001:
            return transform.getTransformFromPos(position)
        return transform.getTransformLookingAt(
            position,
            position + direction,
            self.tail_normal,
            "xz",
            self.negate,
        )

    def _connect_main_control_drivers(self) -> None:
        for group, row, col, _position in self.detail_specs:
            row_count = self._group_row_count(group)
            ratio = (row + 0.5) / max(row_count, 1)
            weights = self._main_control_weights(ratio)
            main_col = min(col, len(self.main_depths) - 1)
            decompose = self._create_blended_main_local_decompose(
                group,
                row,
                col,
                main_col,
                weights,
            )
            translate_attr, rotate_attr = self._create_group_scaled_main_outputs(group, row, col, decompose)
            key = (group, row, col)
            pm.connectAttr(translate_attr, self.detail_pos_offs[key] + ".translate", force=True)
            pm.connectAttr(rotate_attr, self.detail_rot_offs[key] + ".rotate", force=True)

    def _create_blended_main_local_decompose(
        self,
        group: str,
        row: int,
        col: int,
        main_col: int,
        weights: tuple[float, float, float],
    ) -> str:
        blend = cmds.createNode("wtAddMatrix", name=self.getName("%s_%02d_%02d_mainLocal_wam" % (group, row, col)))
        for index, side in enumerate(MAIN_SIDES):
            delta = self._create_main_local_delta_matrix(side, main_col, "%s_%02d_%02d_%s" % (group, row, col, side))
            cmds.connectAttr(delta, blend + ".wtMatrix[%s].matrixIn" % index, force=True)
            cmds.setAttr(blend + ".wtMatrix[%s].weightIn" % index, weights[index])

        decompose = cmds.createNode("decomposeMatrix", name=self.getName("%s_%02d_%02d_mainLocal_dm" % (group, row, col)))
        cmds.connectAttr(blend + ".matrixSum", decompose + ".inputMatrix", force=True)
        cmds.setAttr(decompose + ".inputRotateOrder", 0)
        return decompose

    def _create_group_scaled_main_outputs(self, group: str, row: int, col: int, decompose: str) -> tuple[str, str]:
        influence_attr = self.group_main_influence_attrs[group]
        translate = self._create_scaled_vector_output(
            decompose + ".outputTranslate",
            influence_attr,
            "%s_%02d_%02d_mainTranslateInfluence" % (group, row, col),
        )
        rotate = self._create_scaled_vector_output(
            decompose + ".outputRotate",
            influence_attr,
            "%s_%02d_%02d_mainRotateInfluence" % (group, row, col),
        )
        return translate, rotate

    def _create_scaled_vector_output(self, source_attr: str, influence_attr: PlugLike, name: str) -> str:
        multiply = cmds.createNode("multiplyDivide", name=self.getName(name + "_md"))
        cmds.setAttr(multiply + ".operation", 1)
        cmds.connectAttr(source_attr, multiply + ".input1", force=True)
        for axis in "XYZ":
            cmds.connectAttr(str(influence_attr), multiply + ".input2" + axis, force=True)
        return multiply + ".output"

    def _create_main_local_delta_matrix(self, side: str, main_col: int, name: str) -> str:
        ctl = self.main_ctls[(side, main_col)]
        rest_inverse = ctl.getMatrix().inverse()
        mult = cmds.createNode("multMatrix", name=self.getName(name + "_localDelta_mm"))
        cmds.connectAttr(ctl.name() + ".matrix", mult + ".matrixIn[0]", force=True)
        cmds.setAttr(mult + ".matrixIn[1]", *self._matrix_values(rest_inverse), type="matrix")
        return mult + ".matrixSum"

    def _matrix_values(self, matrix: MatrixLike) -> tuple[float, ...]:
        matrix_get = getattr(matrix, "get", None)
        if callable(matrix_get):
            values = matrix_get()
        else:
            values = matrix
        first_value = values[0]
        if isinstance(first_value, (int, float)):
            flat_values = cast("Sequence[float]", values)
            return tuple(float(flat_values[index]) for index in range(16))
        nested_values = cast("Sequence[Sequence[float]]", values)
        return tuple(float(nested_values[row][column]) for row in range(4) for column in range(4))

    def _group_row_count(self, group: str) -> int:
        for group_name, row_count in zip(self.group_names, self.group_row_counts):
            if group_name == group:
                return row_count
        raise RuntimeError("ymt_birdtail_01 detail guide references unknown group: %s." % group)

    def _group_column_count(self, group: str) -> int:
        for group_name, depths in zip(self.group_names, self.group_column_depths):
            if group_name == group:
                return len(depths)
        raise RuntimeError("ymt_birdtail_01 detail guide references unknown group: %s." % group)

    def _group_column_depth(self, group: str, col: int) -> float:
        for group_name, depths in zip(self.group_names, self.group_column_depths):
            if group_name == group:
                return depths[col]
        raise RuntimeError("ymt_birdtail_01 detail guide references unknown group: %s." % group)

    def _surface_row_ratio(self, row: int, row_count: int) -> float:
        if row_count <= 1:
            return 0.5
        return float(row) / float(row_count - 1)

    def _dominant_side_for_row(self, group: str, row: int) -> str:
        row_ratio = self._surface_row_ratio(row, self._group_row_count(group))
        weights = self._curl_control_weights(row_ratio)
        return max(zip(CURL_SIDES, weights), key=lambda item: item[1])[0]

    def _dominant_main_side_for_row(self, group: str, row: int) -> str:
        row_ratio = self._surface_row_ratio(row, self._group_row_count(group))
        weights = self._main_control_weights(row_ratio)
        return max(zip(MAIN_SIDES, weights), key=lambda item: item[1])[0]

    def _side_color(self, side: str, mode: str) -> int | Sequence[float]:
        if mode not in ("fk", "ik"):
            raise RuntimeError("ymt_birdtail_01 color mode must be fk or ik: %s." % mode)
        if side not in MAIN_SIDES:
            raise RuntimeError("ymt_birdtail_01 color side must be one of C/L/R: %s." % side)

        if cast("bool", self.settings["Override_Color"]):
            if cast("bool", self.settings["Use_RGB_Color"]):
                return cast("Sequence[float]", self.settings["RGB_%s" % mode])
            return cast("int", self.settings["color_%s" % mode])

        if cast("bool", self.options["Use_RGB_Color"]):
            return cast("Sequence[float]", self.options["%s_RGB_%s" % (side, mode)])
        return cast("int", self.options["%s_color_%s" % (side, mode)])

    def _detail_color(self, group: str, side: str) -> int | Sequence[float]:
        color = self._side_color(side, "ik")
        group_index = self._group_index(group)
        if group_index == 0:
            return color
        return self._scale_color_value(color, 0.9**group_index)

    def _group_index(self, group: str) -> int:
        try:
            return self.group_names.index(group)
        except ValueError as exc:
            raise RuntimeError("ymt_birdtail_01 detail references unknown group: %s." % group) from exc

    def _scale_color_value(self, color: int | Sequence[float], scale: float) -> Sequence[float]:
        if isinstance(color, int):
            return self._scale_rgb_color(cast("Sequence[float]", cmds.colorIndex(color, query=True)), scale)
        return self._scale_rgb_color(color, scale)

    def _scale_rgb_color(self, color: Sequence[float], scale: float) -> Sequence[float]:
        return tuple(max(0.0, min(1.0, channel * scale)) for channel in color[:3])

    def _main_control_weights(self, ratio: float) -> tuple[float, float, float]:
        center = max(0.0, 1.0 - abs(ratio - 0.5) * 2.0)
        left = max(0.0, 1.0 - ratio * 2.0)
        right = max(0.0, ratio * 2.0 - 1.0)
        total = max(left + center + right, 0.001)
        return left / total, center / total, right / total

    def _curl_control_weights(self, ratio: float) -> tuple[float, float]:
        clamped_ratio = max(0.0, min(1.0, ratio))
        return 1.0 - clamped_ratio, clamped_ratio

    def _curl_fan_envelope(self, ratio: float) -> float:
        clamped_ratio = max(0.0, min(1.0, ratio))
        center_distance = abs(clamped_ratio - 0.5) * 2.0
        centered_ratio = max(0.0, 1.0 - center_distance)
        center_envelope = centered_ratio * centered_ratio * centered_ratio * (
            centered_ratio * (centered_ratio * 6.0 - 15.0) + 10.0
        )
        edge_scale = max(0.0, min(1.0, self.surface_curl_edge_scale))
        return edge_scale + (1.0 - edge_scale) * center_envelope

    def _display_group_name(self, group: str) -> str:
        return group[:1].upper() + group[1:]

    def _surface_shape_name(self, surface: str) -> str:
        shapes = cmds.listRelatives(surface, shapes=True, fullPath=True) or []
        if not shapes:
            raise RuntimeError("ymt_birdtail_01 could not find ribbon surface shape: %s." % surface)
        return shapes[0]

    def _point_tuple(self, point: VectorLike) -> tuple[float, float, float]:
        return point[0], point[1], point[2]

    def _multiply_node_type(self) -> str:
        if int(cmds.about(apiVersion=True)) >= 20260000:
            return "multDL"
        return "multDoubleLinear"

    def _node_name(self, node: PymelNode | str) -> str:
        if isinstance(node, str):
            return node
        return node.name()
