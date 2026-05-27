"""Guide for ymt_birdtail_01."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, ClassVar

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

if TYPE_CHECKING:
    from ymt_shifter_utility.type_protocols import PymelNode, VectorLike


AUTHOR = "yamahigashi"
URL = "yamahigashi.dev"
EMAIL = "yamahigashi@gmail.com"
VERSION = [1, 0, 0]
TYPE = "ymt_birdtail_01"
NAME = "birdtail"
DESCRIPTION = "Bird tail feather detail component."
DetailSettings = tuple[
    list[str],
    list[int],
    list[list[float]],
    list[float],
    list[float],
    list[float],
    list[float],
    list[float],
]


class Guide(guide.ComponentGuide):
    """Component guide class."""

    compType = TYPE
    compName = NAME
    description = DESCRIPTION

    author = AUTHOR
    url = URL
    email = EMAIL
    version = VERSION

    connectors: ClassVar[list[str]] = ["standard"]

    def postInit(self) -> None:
        self.save_transform = ["root", "centerEnd", "leftEnd", "rightEnd", "curlLeft", "curlRight"]

    def addObjects(self) -> None:
        self.root = self.addRoot()
        self.centerEnd = self.addLoc("centerEnd", self.root, transform.getOffsetPosition(self.root, [0.0, 0.0, -5.0]))
        self.leftEnd = self.addLoc("leftEnd", self.root, transform.getOffsetPosition(self.root, [3.0, 0.0, -4.0]))
        self.rightEnd = self.addLoc("rightEnd", self.root, transform.getOffsetPosition(self.root, [-3.0, 0.0, -4.0]))
        self.curlLeft = self.addLoc("curlLeft", self.root, transform.getOffsetPosition(self.root, [1.5, 1.0, -4.5]))
        self.curlRight = self.addLoc("curlRight", self.root, transform.getOffsetPosition(self.root, [-1.5, 1.0, -4.5]))
        self.detail_locs = self._add_detail_locators_from_template()

        self.center_dispcrv = self.addDispCurve("centerCrv", [self.root, self.centerEnd])
        self.left_dispcrv = self.addDispCurve("leftCrv", [self.root, self.leftEnd])
        self.right_dispcrv = self.addDispCurve("rightCrv", [self.root, self.rightEnd])
        self.curl_dispcrv = self.addDispCurve("curlCrv", [self.curlLeft, self.curlRight])

    def addParameters(self) -> None:
        self.pSolverMode = self.addEnumParam(
            "solverMode",
            ["Simple Matrix Connection", "NURBS Ribbon with Curl"],
            0,
        )
        self.pGroupNames = self.addParam("groupNames", "string", "primary,secondary")
        self.pGroupRowCounts = self.addParam("groupRowCounts", "string", "7,5")
        self.pGroupColumnDepths = self.addParam(
            "groupColumnDepths",
            "string",
            "primary: 0.25, 0.55, 0.85\nsecondary: 0.3, 0.65, 0.9",
        )
        self.pGroupLengthScales = self.addParam("groupLengthScales", "string", "1,0.72")
        self.pGroupWidthScales = self.addParam("groupWidthScales", "string", "1,0.82")
        self.pGroupStackOffsets = self.addParam("groupStackOffsets", "string", "0,0.25")
        self.pGroupMainInfluenceScales = self.addParam("groupMainInfluenceScales", "string", "1,0.65")
        self.pGroupCurlInfluenceScales = self.addParam("groupCurlInfluenceScales", "string", "1,0.65")
        self.pDetailCurlRotMults = self.addParam("detailCurlRotMults", "string", "1,1,1")
        self.pSurfaceCurlMaxWeight = self.addParam("surfaceCurlMaxWeight", "double", 0.65, 0.0, 1.0)
        self.pSurfaceCurlEdgeScale = self.addParam("surfaceCurlEdgeScale", "double", 0.0, 0.0, 1.0)
        self.pCtlSize = self.addParam("ctlSize", "double", 1, 0.001, None)
        self.pAddJoints = self.addParam("addJoints", "bool", True)
        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam("parentJointIndex", "long", -1, None, None)

    def setFromHierarchy(self, root: PymelNode) -> None:
        super(Guide, self).setFromHierarchy(root)
        self._collect_detail_guides()

    def _add_detail_locators_from_template(self) -> list[PymelNode]:
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

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super(settingsTab, self).__init__(parent)
        self.setupUi(self)


class componentSettings(MayaQWidgetDockableMixin, guide.componentMainSettings):
    """Create the component setting window."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
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
        self.resize(540, 620)

    def create_componentControls(self) -> None:
        return

    def populate_componentControls(self) -> None:
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")
        self.settingsTab.solverMode_comboBox.setCurrentIndex(self.root.attr("solverMode").get())
        self.settingsTab.ctlSize_doubleSpinBox.setValue(self.root.attr("ctlSize").get())
        self.settingsTab.surfaceCurlMaxWeight_doubleSpinBox.setValue(self.root.attr("surfaceCurlMaxWeight").get())
        self.settingsTab.surfaceCurlEdgeScale_doubleSpinBox.setValue(self.root.attr("surfaceCurlEdgeScale").get())
        self.settingsTab.detailCurlRotMults_lineEdit.setText(self.root.attr("detailCurlRotMults").get())
        self.populateCheck(self.settingsTab.addJoints_checkBox, "addJoints")
        self.populate_group_table()

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
        self.settingsTab.solverMode_comboBox.currentIndexChanged.connect(
            partial(self.updateComboBox, self.settingsTab.solverMode_comboBox, "solverMode")
        )
        self.settingsTab.ctlSize_doubleSpinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.ctlSize_doubleSpinBox, "ctlSize")
        )
        self.settingsTab.surfaceCurlMaxWeight_doubleSpinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.surfaceCurlMaxWeight_doubleSpinBox, "surfaceCurlMaxWeight")
        )
        self.settingsTab.surfaceCurlEdgeScale_doubleSpinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.surfaceCurlEdgeScale_doubleSpinBox, "surfaceCurlEdgeScale")
        )
        self.settingsTab.detailCurlRotMults_lineEdit.editingFinished.connect(self.update_detail_curl_rot_mults_setting)
        self.settingsTab.addJoints_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.addJoints_checkBox, "addJoints")
        )
        self.settingsTab.groupTableWidget.cellChanged.connect(self.update_group_table_settings)
        self.settingsTab.addGroup_pushButton.clicked.connect(self.add_group_table_item)
        self.settingsTab.removeGroup_pushButton.clicked.connect(self.remove_selected_group_table_item)
        self.settingsTab.generateLocators_pushButton.clicked.connect(self.rebuild_detail_locators)
        self.mainSettingsTab.connector_comboBox.currentIndexChanged.connect(
            partial(self.updateConnector, self.mainSettingsTab.connector_comboBox, self.connector_items)
        )

    def dockCloseEventTriggered(self) -> None:
        pyqt.deleteInstances(self, MayaQDockWidget)

    def populate_group_table(self) -> None:
        table = self.settingsTab.groupTableWidget
        table.blockSignals(True)
        table.setRowCount(0)
        try:
            settings = self._detail_settings_from_root()
        except RuntimeError as exc:
            pm.displayWarning(str(exc))
            table.blockSignals(False)
            return
        (
            group_names,
            row_counts,
            depths_by_group,
            length_scales,
            width_scales,
            stack_offsets,
            main_influences,
            curl_influences,
        ) = settings
        for group_settings in zip(
            group_names,
            row_counts,
            depths_by_group,
            length_scales,
            width_scales,
            stack_offsets,
            main_influences,
            curl_influences,
        ):
            self._append_group_table_item(*group_settings)
        table.blockSignals(False)

    def add_group_table_item(self) -> None:
        table = self.settingsTab.groupTableWidget
        group_index = table.rowCount()
        table.blockSignals(True)
        self._append_group_table_item("group%s" % group_index, 1, [0.3, 0.65, 0.9], 1.0, 1.0, 0.0, 1.0, 1.0)
        table.blockSignals(False)
        self.update_group_table_settings()

    def remove_selected_group_table_item(self) -> None:
        table = self.settingsTab.groupTableWidget
        rows = sorted({index.row() for index in table.selectedIndexes()}, reverse=True)
        if not rows and table.rowCount():
            rows = [table.rowCount() - 1]
        for row in rows:
            table.removeRow(row)
        self.update_group_table_settings()

    def _append_group_table_item(
        self,
        group_name: str,
        row_count: int,
        depths: list[float],
        length_scale: float,
        width_scale: float,
        stack_offset: float,
        main_influence: float,
        curl_influence: float,
    ) -> None:
        table = self.settingsTab.groupTableWidget
        row = table.rowCount()
        table.insertRow(row)
        values = [
            group_name,
            str(row_count),
            ", ".join(detail_config.format_float(depth) for depth in depths),
            detail_config.format_float(length_scale),
            detail_config.format_float(width_scale),
            detail_config.format_float(stack_offset),
            detail_config.format_float(main_influence),
            detail_config.format_float(curl_influence),
        ]
        for column, value in enumerate(values):
            table.setItem(row, column, QtWidgets.QTableWidgetItem(value))

    def update_group_table_settings(self, *_args: int) -> None:
        try:
            settings = self._detail_settings_from_table()
        except RuntimeError as exc:
            pm.displayWarning(str(exc))
            return
        (
            group_names,
            row_counts,
            depths_by_group,
            length_scales,
            width_scales,
            stack_offsets,
            main_influences,
            curl_influences,
        ) = settings
        self.root.attr("groupNames").set(",".join(group_names))
        self.root.attr("groupRowCounts").set(",".join(str(count) for count in row_counts))
        self.root.attr("groupColumnDepths").set(detail_config.format_group_column_depths(group_names, depths_by_group))
        self.root.attr("groupLengthScales").set(",".join(detail_config.format_float(value) for value in length_scales))
        self.root.attr("groupWidthScales").set(",".join(detail_config.format_float(value) for value in width_scales))
        self.root.attr("groupStackOffsets").set(",".join(detail_config.format_float(value) for value in stack_offsets))
        self.root.attr("groupMainInfluenceScales").set(
            ",".join(detail_config.format_float(value) for value in main_influences)
        )
        self.root.attr("groupCurlInfluenceScales").set(
            ",".join(detail_config.format_float(value) for value in curl_influences)
        )

    def update_detail_curl_rot_mults_setting(self) -> None:
        try:
            group_names = detail_config.parse_group_names(self.root.attr("groupNames").get())
            depths_by_group = detail_config.parse_group_column_depths(self.root.attr("groupColumnDepths").get(), group_names)
            column_count = max(len(depths) for depths in depths_by_group)
            values = detail_config.parse_detail_curl_rot_multipliers(
                self.settingsTab.detailCurlRotMults_lineEdit.text(), column_count
            )
        except RuntimeError as exc:
            pm.displayWarning(str(exc))
            self.settingsTab.detailCurlRotMults_lineEdit.setText(self.root.attr("detailCurlRotMults").get())
            return
        formatted = detail_config.format_detail_curl_rot_multipliers(values)
        self.root.attr("detailCurlRotMults").set(formatted)
        self.settingsTab.detailCurlRotMults_lineEdit.setText(formatted)

    def _detail_settings_from_root(self) -> DetailSettings:
        group_names = detail_config.parse_group_names(self.root.attr("groupNames").get())
        row_counts = detail_config.parse_group_row_counts(self.root.attr("groupRowCounts").get(), group_names)
        depths_by_group = detail_config.parse_group_column_depths(self.root.attr("groupColumnDepths").get(), group_names)
        length_scales = detail_config.parse_group_scalar_values(
            self.root.attr("groupLengthScales").get(), group_names, "groupLengthScales"
        )
        width_scales = detail_config.parse_group_scalar_values(
            self.root.attr("groupWidthScales").get(), group_names, "groupWidthScales"
        )
        stack_offsets = detail_config.parse_group_scalar_values(
            self.root.attr("groupStackOffsets").get(), group_names, "groupStackOffsets"
        )
        main_influences = detail_config.parse_group_main_influence_scales(
            self.root.attr("groupMainInfluenceScales").get(), group_names
        )
        curl_influences = detail_config.parse_group_curl_influence_scales(
            self.root.attr("groupCurlInfluenceScales").get(), group_names
        )
        return (
            group_names,
            row_counts,
            depths_by_group,
            length_scales,
            width_scales,
            stack_offsets,
            main_influences,
            curl_influences,
        )

    def _detail_settings_from_table(self) -> DetailSettings:
        table = self.settingsTab.groupTableWidget
        group_names = []
        row_counts = []
        depths_by_group = []
        length_scales = []
        width_scales = []
        stack_offsets = []
        main_influences = []
        curl_influences = []
        for row in range(table.rowCount()):
            group_names.append(self._table_text(row, 0))
            try:
                row_counts.append(int(self._table_text(row, 1)))
                depths_by_group.append(detail_config.parse_column_depth_list(self._table_text(row, 2)))
                length_scales.append(float(self._table_text(row, 3)))
                width_scales.append(float(self._table_text(row, 4)))
                stack_offsets.append(float(self._table_text(row, 5)))
                main_influences.append(float(self._table_text(row, 6)))
                curl_influences.append(float(self._table_text(row, 7)))
            except ValueError as exc:
                raise RuntimeError("ymt_birdtail_01 group table contains malformed numeric values.") from exc

        group_names = detail_config.parse_group_names(",".join(group_names))
        detail_config.parse_group_row_counts(",".join(str(count) for count in row_counts), group_names)
        detail_config.parse_group_column_depths(
            detail_config.format_group_column_depths(group_names, depths_by_group), group_names
        )
        detail_config.parse_group_main_influence_scales(
            ",".join(detail_config.format_float(value) for value in main_influences), group_names
        )
        detail_config.parse_group_curl_influence_scales(
            ",".join(detail_config.format_float(value) for value in curl_influences), group_names
        )
        return (
            group_names,
            row_counts,
            depths_by_group,
            length_scales,
            width_scales,
            stack_offsets,
            main_influences,
            curl_influences,
        )

    def _table_text(self, row: int, column: int) -> str:
        item = self.settingsTab.groupTableWidget.item(row, column)
        if item is None:
            return ""
        return item.text().strip()

    def rebuild_detail_locators(self) -> None:
        try:
            settings = self._detail_settings_from_table()
            root_position = self._guide_position("root")
            center_position = self._guide_position("centerEnd")
            left_position = self._guide_position("leftEnd")
            right_position = self._guide_position("rightEnd")
        except RuntimeError as exc:
            pm.displayWarning(str(exc))
            return

        self._delete_existing_detail_locators()
        created = []
        (
            group_names,
            row_counts,
            depths_by_group,
            length_scales,
            width_scales,
            stack_offsets,
            _main_influences,
            _curl_influences,
        ) = settings
        for group_index, group_name in enumerate(group_names):
            for row in range(row_counts[group_index]):
                ratio = (row + 0.5) / max(row_counts[group_index], 1)
                endpoint = self._fan_endpoint(center_position, left_position, right_position, ratio)
                endpoint = center_position + ((endpoint - center_position) * width_scales[group_index])
                endpoint = root_position + ((endpoint - root_position) * length_scales[group_index])
                stack_vector = self._local_stack_vector(stack_offsets[group_index])
                for col, depth in enumerate(depths_by_group[group_index]):
                    local_name = "%s_%d_%d_loc" % (group_name, row, col)
                    position = root_position + ((endpoint - root_position) * depth) + stack_vector
                    created.append(self._create_detail_locator(local_name, position))
        pm.select(created or self.root)
        pm.displayInfo("Rebuilt %s ymt_birdtail_01 detail locators." % len(created))

    def _guide_position(self, local_name: str) -> VectorLike:
        prefix = self.root.name().replace("_root", "")
        node_name = "%s_%s" % (prefix, local_name)
        if not pm.objExists(node_name):
            raise RuntimeError("ymt_birdtail_01 guide is missing %s." % local_name)
        return datatypes.Vector(pm.xform(pm.PyNode(node_name), q=True, ws=True, t=True))

    def _fan_endpoint(
        self,
        center_position: VectorLike,
        left_position: VectorLike,
        right_position: VectorLike,
        ratio: float,
    ) -> VectorLike:
        if ratio <= 0.5:
            local = ratio * 2.0
            return left_position + ((center_position - left_position) * local)
        local = (ratio - 0.5) * 2.0
        return center_position + ((right_position - center_position) * local)

    def _local_stack_vector(self, stack_offset: float) -> VectorLike:
        root_position = self._guide_position("root")
        stacked_position = transform.getOffsetPosition(self.root, [0.0, stack_offset, 0.0])
        return datatypes.Vector(stacked_position) - root_position

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

    def _create_detail_locator(self, local_name: str, position: VectorLike) -> PymelNode:
        prefix = self.root.name().replace("_root", "")
        created = pm.spaceLocator(name="%s_%s" % (prefix, local_name))
        node = created[0] if isinstance(created, (list, tuple)) else created
        node = pm.PyNode(node)
        node.setTranslation(position, space="world")
        pm.parent(node, self.root)
        return node
