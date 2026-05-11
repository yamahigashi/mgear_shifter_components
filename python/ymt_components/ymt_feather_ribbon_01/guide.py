"""Guide for ymt_feather_ribbon_01."""

from __future__ import annotations

from functools import partial
from typing import ClassVar

import importlib

try:
    pm = importlib.import_module("mgear.pymaya")
except ImportError:
    pm = importlib.import_module("pymel.core")

from maya.app.general.mayaMixin import MayaQDockWidget, MayaQWidgetDockableMixin
from mgear.core import pyqt, transform
from mgear.shifter.component import guide
from mgear.vendor.Qt import QtCore, QtWidgets

from . import settingsUI as sui


AUTHOR = "yamahigashi"
URL = "yamahigashi.dev"
EMAIL = "yamahigashi@gmail.com"
VERSION = [1, 0, 0]
TYPE = "ymt_feather_ribbon_01"
NAME = "featherRibbon"
DESCRIPTION = "Feather ribbon detail driver for ymt_birdwing_3jnt_01."


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
            "curl0",
            "curl1",
            "curl2",
            "#_loc",
        ]
        self.addMinMax("#_loc", 1, -1)

    def addObjects(self) -> None:
        self.root = self.addRoot()
        self.curl0 = self.addLoc("curl0", self.root, transform.getOffsetPosition(self.root, [1.5, 0.0, -5.0]))
        self.curl1 = self.addLoc("curl1", self.root, transform.getOffsetPosition(self.root, [4.5, 0.0, -5.0]))
        self.curl2 = self.addLoc("curl2", self.root, transform.getOffsetPosition(self.root, [7.0, 0.0, -5.0]))
        self.locs = self.addLocMulti("#_loc", self.root)

        centers = [self.root, self.curl0, self.curl1, self.curl2]
        self.dispcrv = self.addDispCurve("crv", centers)

    def addParameters(self) -> None:
        self.pPlacementMode = self.addEnumParam("placementMode", ["surface", "fixed"], 0)
        self.pRowNames = self.addParam("rowNames", "string", "primary,secondary,tertial")
        self.pRowCounts = self.addParam("rowCounts", "string", "10,13,3")
        self.pRowURanges = self.addParam("rowURanges", "string", "0.55:1.0,0.1:0.85,0.0:0.25")
        self.pLowerEdgeOffsets = self.addParam(
            "lowerEdgeOffsets",
            "string",
            "primary: 0.2\nsecondary: 0.375\ntertial: 0.55",
        )
        self.pCtlSize = self.addParam("ctlSize", "double", 1, 0.001, None)
        self.pAddJoints = self.addParam("addJoints", "bool", True)
        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam("parentJointIndex", "long", -1, None, None)


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
        self.resize(320, 430)

    def create_componentControls(self) -> None:
        return

    def populate_componentControls(self) -> None:
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")
        self.settingsTab.placementMode_comboBox.setCurrentIndex(self.root.attr("placementMode").get())
        self.settingsTab.rowNames_lineEdit.setText(self.root.attr("rowNames").get())
        self.settingsTab.rowCounts_lineEdit.setText(self.root.attr("rowCounts").get())
        self.settingsTab.rowURanges_lineEdit.setText(self.root.attr("rowURanges").get())
        if self.root.hasAttr("lowerEdgeOffsets"):
            self.settingsTab.lowerEdgeOffsets_plainTextEdit.setPlainText(self.root.attr("lowerEdgeOffsets").get())
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
        self.settingsTab.rowNames_lineEdit.editingFinished.connect(
            partial(self.update_line_edit, self.settingsTab.rowNames_lineEdit, "rowNames")
        )
        self.settingsTab.rowCounts_lineEdit.editingFinished.connect(
            partial(self.update_line_edit, self.settingsTab.rowCounts_lineEdit, "rowCounts")
        )
        self.settingsTab.rowURanges_lineEdit.editingFinished.connect(
            partial(self.update_line_edit, self.settingsTab.rowURanges_lineEdit, "rowURanges")
        )
        self.settingsTab.lowerEdgeOffsets_plainTextEdit.textChanged.connect(
            partial(self.update_plain_text_edit, self.settingsTab.lowerEdgeOffsets_plainTextEdit, "lowerEdgeOffsets")
        )
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

    def update_line_edit(self, line_edit: QtWidgets.QLineEdit, target_attr: str) -> None:
        self.root.attr(target_attr).set(line_edit.text())

    def update_plain_text_edit(self, plain_text_edit: QtWidgets.QPlainTextEdit, target_attr: str) -> None:
        if self.root.hasAttr(target_attr):
            self.root.attr(target_attr).set(plain_text_edit.toPlainText())
