"""Guide for ymt_feather_ribbon_01."""

from __future__ import annotations

from functools import partial
from typing import Any, ClassVar

import importlib

try:
    pm = importlib.import_module("mgear.pymaya")
except ImportError:
    pm = importlib.import_module("pymel.core")
try:
    datatypes = importlib.import_module("mgear.pymaya.datatypes")
except ImportError:
    datatypes = importlib.import_module("pymel.core.datatypes")

from maya.app.general.mayaMixin import MayaQDockWidget, MayaQWidgetDockableMixin
from mgear.core import pyqt, transform
from mgear.shifter.component import guide
from mgear.vendor.Qt import QtCore, QtWidgets

from . import detail_config
from . import settingsUI as sui


AUTHOR = "yamahigashi"
URL = "yamahigashi.dev"
EMAIL = "yamahigashi@gmail.com"
VERSION = [1, 0, 0]
TYPE = "ymt_feather_ribbon_01"
NAME = "feather"
DESCRIPTION = "Feather ribbon detail driver for ymt_birdwing_3jnt_01."
PARENT_COMPONENT_TYPE = "ymt_birdwing_3jnt_01"
PARENT_ANCHOR_NAMES = ("root", "elbow", "wrist", "eff")


class Guide(guide.ComponentGuide):
    """Component guide class."""

    compType = TYPE
    compName = NAME
    description = DESCRIPTION

    author = AUTHOR
    url = URL
    email = EMAIL
    version = VERSION

    connectors: ClassVar[list[str]] = ["ymt_birdwing_3jnt_01"]

    def postInit(self) -> None:
        self.save_transform = [
            "root",
            "rootEnd",
            "elbowEnd",
            "wristEnd",
            "handEnd",
            "curl0",
            "curl1",
            "curl2",
        ]

    def addObjects(self) -> None:
        self.root = self.addRoot()
        self.rootEnd = self.addLoc("rootEnd", self.root, transform.getOffsetPosition(self.root, [0.0, 0.0, -5.0]))
        self.elbowEnd = self.addLoc("elbowEnd", self.root, transform.getOffsetPosition(self.root, [3.0, 0.0, -5.0]))
        self.wristEnd = self.addLoc("wristEnd", self.root, transform.getOffsetPosition(self.root, [6.0, 0.0, -5.0]))
        self.handEnd = self.addLoc("handEnd", self.root, transform.getOffsetPosition(self.root, [13.0, 0.0, -1.0]))
        self.curl0 = self.addLoc("curl0", self.root, transform.getOffsetPosition(self.root, [1.5, 0.0, -5.0]))
        self.curl1 = self.addLoc("curl1", self.root, transform.getOffsetPosition(self.root, [4.5, 0.0, -5.0]))
        self.curl2 = self.addLoc("curl2", self.root, transform.getOffsetPosition(self.root, [10.0, 0.0, -4.0]))
        self.detail_locs = self._add_detail_locators_from_template()

        centers = [self.root, self.curl0, self.curl1, self.curl2]
        self.dispcrv = self.addDispCurve("crv", centers)
        self.end_dispcrv = self.addDispCurve("endCrv", [self.rootEnd, self.elbowEnd, self.wristEnd, self.handEnd])

    def addParameters(self) -> None:
        self.pPlacementMode = self.addEnumParam("placementMode", ["surface", "fixed"], 0)
        self.pRowNames = self.addParam("rowNames", "string", "primary,secondary,tertial")
        self.pRowCounts = self.addParam("rowCounts", "string", "10,13,3")
        self.pRowURanges = self.addParam("rowURanges", "string", "0.55:1.0,0.1:0.85,0.0:0.25")
        self.pDetailColumnDepths = self.addParam(
            "detailColumnDepths",
            "string",
            "primary: 0.2\nsecondary: 0.375\ntertial: 0.55",
        )
        self.pDetailCurlRotMults = self.addParam("detailCurlRotMults", "string", "1")
        self.pCtlSize = self.addParam("ctlSize", "double", 1, 0.001, None)
        self.pAddJoints = self.addParam("addJoints", "bool", True)
        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam("parentJointIndex", "long", -1, None, None)

    def setFromHierarchy(self, root: Any) -> None:
        super(Guide, self).setFromHierarchy(root)
        self._collect_detail_guides()

    def _add_detail_locators_from_template(self) -> list[Any]:
        locators = []
        for local_name in self._serialized_detail_locator_names():
            position = transform.getPositionFromMatrix(self.tra[local_name])
            locators.append(self.addLoc(local_name, self.root, position))
        return locators

    def _serialized_detail_locator_names(self) -> list[str]:
        names = [local_name for local_name in self.tra if detail_config.is_detail_guide_name(local_name)]
        return sorted(names, key=self._detail_locator_sort_key)

    def _collect_detail_guides(self) -> None:
        prefix = self.fullName + "_"
        children = pm.listRelatives(self.model, ad=True, typ="transform") or []
        detail_nodes = []
        for node in children:
            node_name = node.name().split("|")[-1]
            if not node_name.startswith(prefix):
                continue
            local_name = node_name[len(prefix) :]
            if not detail_config.is_detail_guide_name(local_name):
                continue
            if local_name in self.tra:
                continue
            detail_nodes.append((local_name, node))
        for local_name, node in sorted(detail_nodes, key=lambda item: self._detail_locator_sort_key(item[0])):
            matrix = node.getMatrix(worldSpace=True)
            position = node.getTranslation(space="world")
            self.tra[local_name] = matrix
            self.atra.append(matrix)
            self.pos[local_name] = position
            self.apos.append(position)

    def _detail_locator_sort_key(self, local_name: str) -> tuple[str, int, int]:
        parsed = detail_config.parse_detail_guide_name(local_name)
        if parsed is None:
            return (local_name, 0, 0)
        return parsed


class settingsTab(QtWidgets.QDialog, sui.Ui_Form):
    """The component settings UI."""

    def __init__(self, parent: object = None) -> None:
        super(settingsTab, self).__init__(parent)
        self.setupUi(self)


class componentSettings(MayaQWidgetDockableMixin, guide.componentMainSettings):
    """Create the component setting window."""

    def __init__(self, parent: object = None) -> None:
        self.toolName = TYPE
        pyqt.deleteInstances(self, MayaQDockWidget)
        super(self.__class__, self).__init__(parent=parent)
        self.settingsTab = settingsTab()

        self.setup_componentSettingWindow()
        self.create_componentControls()
        self.populate_componentControls()
        self.create_componentLayout()
        self.create_componentConnections()

    def setup_componentSettingWindow(self) -> None:
        self.mayaMainWindow = pyqt.maya_main_window()
        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle(TYPE)
        self.resize(460, 590)

    def create_componentControls(self) -> None:
        return

    def populate_componentControls(self) -> None:
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")
        self.settingsTab.placementMode_comboBox.setCurrentIndex(self.root.attr("placementMode").get())
        self.populate_row_table()
        self._sync_detail_curl_rot_mult_count(self._detail_column_count_from_root())
        self.settingsTab.ctlSize_doubleSpinBox.setValue(self.root.attr("ctlSize").get())
        self.populateCheck(self.settingsTab.addJoints_checkBox, "addJoints")

        self.c_box = self.mainSettingsTab.connector_comboBox
        for cnx in Guide.connectors:
            self.c_box.addItem(cnx)
        self.connector_items = [self.c_box.itemText(i) for i in range(self.c_box.count())]
        current_connector = self.root.attr("connector").get()
        if current_connector not in self.connector_items:
            self.c_box.addItem(current_connector)
            self.connector_items.append(current_connector)
            pm.displayWarning("The current connector: %s is not valid for this component." % current_connector)
        self.c_box.setCurrentIndex(self.connector_items.index(current_connector))

    def create_componentLayout(self) -> None:
        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)
        self.setLayout(self.settings_layout)

    def create_componentConnections(self) -> None:
        self.settingsTab.placementMode_comboBox.currentIndexChanged.connect(
            partial(self.updateComboBox, self.settingsTab.placementMode_comboBox, "placementMode")
        )
        self.settingsTab.rowTableWidget.cellChanged.connect(self.update_row_table_settings)
        self.settingsTab.addRow_pushButton.clicked.connect(self.add_row_table_item)
        self.settingsTab.removeRow_pushButton.clicked.connect(self.remove_selected_row_table_item)
        self.settingsTab.generateLocators_pushButton.clicked.connect(self.rebuild_detail_locators)
        self.settingsTab.detailCurlRotMults_lineEdit.editingFinished.connect(self.update_detail_curl_rot_mults_setting)
        self.settingsTab.ctlSize_doubleSpinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.ctlSize_doubleSpinBox, "ctlSize")
        )
        self.settingsTab.addJoints_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.addJoints_checkBox, "addJoints")
        )
        self.mainSettingsTab.connector_comboBox.currentIndexChanged.connect(
            partial(self.updateConnector, self.mainSettingsTab.connector_comboBox, self.connector_items)
        )

    def dockCloseEventTriggered(self) -> None:
        pyqt.deleteInstances(self, MayaQDockWidget)

    def populate_row_table(self) -> None:
        table = self.settingsTab.rowTableWidget
        table.blockSignals(True)
        table.setRowCount(0)
        try:
            row_names, row_counts, row_u_ranges, detail_column_depths_by_row = self._detail_settings_from_root()
        except RuntimeError as exc:
            pm.displayWarning(str(exc))
            table.blockSignals(False)
            return
        for row_name, count, u_range, depths in zip(row_names, row_counts, row_u_ranges, detail_column_depths_by_row):
            self._append_row_table_item(row_name, count, u_range[0], u_range[1], depths)
        table.blockSignals(False)

    def add_row_table_item(self) -> None:
        table = self.settingsTab.rowTableWidget
        row = table.rowCount()
        table.blockSignals(True)
        self._append_row_table_item("row%s" % row, 1, 0.0, 1.0, [0.2])
        table.blockSignals(False)
        self.update_row_table_settings()

    def remove_selected_row_table_item(self) -> None:
        table = self.settingsTab.rowTableWidget
        rows = sorted({index.row() for index in table.selectedIndexes()}, reverse=True)
        if not rows and table.rowCount():
            rows = [table.rowCount() - 1]
        for row in rows:
            table.removeRow(row)
        self.update_row_table_settings()

    def _append_row_table_item(
        self,
        row_name: str,
        count: int,
        u_start: float,
        u_end: float,
        depths: list[float],
    ) -> None:
        table = self.settingsTab.rowTableWidget
        row = table.rowCount()
        table.insertRow(row)
        values = [
            row_name,
            str(count),
            detail_config.format_float(u_start),
            detail_config.format_float(u_end),
            ", ".join(detail_config.format_float(depth) for depth in depths),
        ]
        for column, value in enumerate(values):
            table.setItem(row, column, QtWidgets.QTableWidgetItem(value))

    def update_row_table_settings(self, *_args: object) -> None:
        try:
            row_names, row_counts, row_u_ranges, detail_column_depths_by_row = self._detail_settings_from_table()
        except RuntimeError as exc:
            pm.displayWarning(str(exc))
            return
        self.root.attr("rowNames").set(",".join(row_names))
        self.root.attr("rowCounts").set(",".join(str(count) for count in row_counts))
        self.root.attr("rowURanges").set(
            ",".join(
                "%s:%s" % (detail_config.format_float(u_start), detail_config.format_float(u_end))
                for u_start, u_end in row_u_ranges
            )
        )
        self.root.attr("detailColumnDepths").set(
            detail_config.format_detail_column_depths_by_row(row_names, detail_column_depths_by_row)
        )
        self._sync_detail_curl_rot_mult_count(max(len(depths) for depths in detail_column_depths_by_row))

    def update_detail_curl_rot_mults_setting(self) -> None:
        try:
            _, _, _, detail_column_depths_by_row = self._detail_settings_from_table()
            values = detail_config.parse_detail_curl_rot_multipliers(
                self.settingsTab.detailCurlRotMults_lineEdit.text(),
                max(len(depths) for depths in detail_column_depths_by_row),
            )
        except RuntimeError as exc:
            pm.displayWarning(str(exc))
            self.settingsTab.detailCurlRotMults_lineEdit.setText(self._detail_curl_rot_mults_setting())
            return
        self._set_detail_curl_rot_mults_setting(detail_config.format_detail_curl_rot_multipliers(values))
        self.settingsTab.detailCurlRotMults_lineEdit.setText(self._detail_curl_rot_mults_setting())

    def _sync_detail_curl_rot_mult_count(self, column_count: int) -> None:
        values = detail_config.normalize_detail_curl_rot_multipliers(
            self._detail_curl_rot_mults_setting(),
            column_count,
        )
        formatted = detail_config.format_detail_curl_rot_multipliers(values)
        self._set_detail_curl_rot_mults_setting(formatted)
        self.settingsTab.detailCurlRotMults_lineEdit.setText(formatted)

    def _detail_curl_rot_mults_setting(self) -> str:
        if self.root.hasAttr("detailCurlRotMults"):
            return self.root.attr("detailCurlRotMults").get()
        return ""

    def _set_detail_curl_rot_mults_setting(self, value: str) -> None:
        if not self.root.hasAttr("detailCurlRotMults"):
            self.root.addAttr("detailCurlRotMults", dataType="string")
        self.root.attr("detailCurlRotMults").set(value)

    def _detail_column_count_from_root(self) -> int:
        try:
            _, _, _, detail_column_depths_by_row = self._detail_settings_from_root()
        except RuntimeError:
            return 1
        return max(len(depths) for depths in detail_column_depths_by_row)

    def _detail_settings_from_root(self) -> tuple[list[str], list[int], list[tuple[float, float]], list[list[float]]]:
        row_names = detail_config.parse_row_names(self.root.attr("rowNames").get())
        row_counts = detail_config.parse_row_counts(self.root.attr("rowCounts").get(), row_names)
        row_u_ranges = detail_config.parse_row_u_ranges(self.root.attr("rowURanges").get(), row_names)
        if not self.root.hasAttr("detailColumnDepths"):
            raise RuntimeError("ymt_feather_ribbon_01 requires the detailColumnDepths setting.")
        detail_column_depths_by_row = detail_config.parse_detail_column_depths_by_row(
            self.root.attr("detailColumnDepths").get(), row_names
        )
        return row_names, row_counts, row_u_ranges, detail_column_depths_by_row

    def _detail_settings_from_table(self) -> tuple[list[str], list[int], list[tuple[float, float]], list[list[float]]]:
        table = self.settingsTab.rowTableWidget
        row_names = []
        row_counts = []
        row_u_ranges = []
        detail_column_depths_by_row = []
        for row in range(table.rowCount()):
            row_name = self._table_text(row, 0)
            if not row_name:
                raise RuntimeError("ymt_feather_ribbon_01 row name cannot be empty.")
            row_names.append(row_name)
            try:
                row_counts.append(int(self._table_text(row, 1)))
                row_u_ranges.append((float(self._table_text(row, 2)), float(self._table_text(row, 3))))
            except ValueError as exc:
                raise RuntimeError("ymt_feather_ribbon_01 row table contains a non-numeric count or U range.") from exc
            detail_column_depths_by_row.append(detail_config.parse_detail_column_depth_list(self._table_text(row, 4)))
        row_names = detail_config.parse_row_names(",".join(row_names))
        detail_config.validate_detail_row_names(row_names)
        detail_config.parse_row_counts(",".join(str(count) for count in row_counts), row_names)
        detail_config.parse_row_u_ranges(
            ",".join("%s:%s" % (u_start, u_end) for u_start, u_end in row_u_ranges),
            row_names,
        )
        detail_config.parse_detail_column_depths_by_row(
            detail_config.format_detail_column_depths_by_row(row_names, detail_column_depths_by_row), row_names
        )
        return row_names, row_counts, row_u_ranges, detail_column_depths_by_row

    def _table_text(self, row: int, column: int) -> str:
        item = self.settingsTab.rowTableWidget.item(row, column)
        if item is None:
            return ""
        return item.text().strip()

    def rebuild_detail_locators(self) -> None:
        try:
            row_names, row_counts, row_u_ranges, detail_column_depths_by_row = self._detail_settings_from_table()
            parent_root = self._find_parent_wing_root()
            anchor_positions = self._parent_anchor_positions(parent_root)
            anchor_end_positions = self._anchor_end_positions()
        except RuntimeError as exc:
            pm.displayWarning(str(exc))
            return

        self._delete_existing_detail_locators()
        created = []
        for row_index, row_name in enumerate(row_names):
            section_count = row_counts[row_index]
            u_start, u_end = row_u_ranges[row_index]
            for section in range(section_count):
                ratio = (section + 0.5) / max(section_count, 1)
                u = u_start + ((u_end - u_start) * ratio)
                span, local = self._span_local_from_u(anchor_positions, u)
                base_position = self._position_from_span_local(anchor_positions, span, local)
                end_position = self._position_from_span_local(anchor_end_positions, span, local)
                for col, depth in enumerate(detail_column_depths_by_row[row_index]):
                    local_name = "%s_%d_%d_loc" % (row_name, section, col)
                    position = base_position + ((end_position - base_position) * depth)
                    created.append(self._create_detail_locator(local_name, position))
        pm.select(created or self.root)
        pm.displayInfo("Rebuilt %s ymt_feather_ribbon_01 detail locators." % len(created))

    def _find_parent_wing_root(self) -> Any:
        side = self.root.attr("comp_side").get()
        index = self.root.attr("comp_index").get()
        candidates = []
        for node in pm.ls(type="transform"):
            if not node.hasAttr("comp_type") or node.attr("comp_type").get() != PARENT_COMPONENT_TYPE:
                continue
            if node.attr("comp_side").get() != side or node.attr("comp_index").get() != index:
                continue
            candidates.append(node)
        if len(candidates) == 1:
            return candidates[0]
        if candidates:
            raise RuntimeError("ymt_feather_ribbon_01 found multiple parent wing guide candidates.")
        raise RuntimeError("ymt_feather_ribbon_01 requires a matching ymt_birdwing_3jnt_01 guide.")

    def _parent_anchor_positions(self, parent_root: Any) -> list[Any]:
        prefix = parent_root.name().replace("_root", "")
        positions = []
        for name in PARENT_ANCHOR_NAMES:
            node_name = "%s_%s" % (prefix, name)
            if not pm.objExists(node_name):
                raise RuntimeError("ymt_feather_ribbon_01 parent wing guide is missing %s." % name)
            node = pm.PyNode(node_name)
            positions.append(datatypes.Vector(pm.xform(node, q=True, ws=True, t=True)))
        return positions

    def _anchor_end_positions(self) -> list[Any]:
        prefix = self.root.name().replace("_root", "")
        positions = []
        for name in ("rootEnd", "elbowEnd", "wristEnd", "handEnd"):
            node_name = "%s_%s" % (prefix, name)
            if not pm.objExists(node_name):
                raise RuntimeError("ymt_feather_ribbon_01 guide is missing %s." % name)
            node = pm.PyNode(node_name)
            positions.append(datatypes.Vector(pm.xform(node, q=True, ws=True, t=True)))
        return positions

    def _span_local_from_u(self, anchor_positions: list[Any], u: float) -> tuple[int, float]:
        segment_lengths = [(end - start).length() for start, end in zip(anchor_positions[:-1], anchor_positions[1:])]
        total_length = sum(segment_lengths)
        if total_length < 0.001:
            raise RuntimeError("ymt_feather_ribbon_01 requires non-zero parent wing guide length.")
        distance = max(0.0, min(1.0, u)) * total_length
        traversed = 0.0
        for index, segment_length in enumerate(segment_lengths):
            if distance <= traversed + segment_length or index == len(segment_lengths) - 1:
                local = (distance - traversed) / segment_length
                return index, max(0.0, min(1.0, local))
            traversed += segment_length
        return len(segment_lengths) - 1, 1.0

    def _position_from_span_local(self, positions: list[Any], span: int, local: float) -> Any:
        return positions[span] + ((positions[span + 1] - positions[span]) * local)

    def _delete_existing_detail_locators(self) -> None:
        prefix = self.root.name().replace("_root", "")
        nodes = []
        for node in pm.listRelatives(self.root.getParent(generations=-1), ad=True, typ="transform") or []:
            node_name = node.name().split("|")[-1]
            if not node_name.startswith(prefix + "_"):
                continue
            local_name = node_name[len(prefix) + 1 :]
            if detail_config.is_detail_guide_name(local_name):
                nodes.append(node)
        if nodes:
            pm.delete(nodes)

    def _create_detail_locator(self, local_name: str, position: Any) -> Any:
        prefix = self.root.name().replace("_root", "")
        created = pm.spaceLocator(name="%s_%s" % (prefix, local_name))
        node = created[0] if isinstance(created, (list, tuple)) else created
        node = pm.PyNode(node)
        node.setTranslation(position, space="world")
        pm.parent(node, self.root)
        return node
