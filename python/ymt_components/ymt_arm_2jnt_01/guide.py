# MGEAR is under the terms of the MIT License

# Copyright (c) 2016 Jeremie Passerin, Miquel Campos

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Author:     Jeremie Passerin      geerem@hotmail.com  www.jeremiepasserin.com
# Author:     Miquel Campos         hello@miquel-campos.com  www.miquel-campos.com
# Date:       2016 / 10 / 10

##########################################################
# GLOBAL
##########################################################

from functools import partial

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget
# import maya.OpenMayaUI as omui

try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm as pm

# mgear
from mgear.shifter.component.guide import ComponentGuide
from mgear.shifter.component.guide import componentMainSettings
from mgear.core import (
    pyqt as gqt,
    transform as tra,
    attribute as att
)

from . import settingsUI as sui

QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()


##########################################################
# guide info
AUTHOR = "Jeremie Passerin, Miquel Campos, Takayoshi MATSUMOTO"
URL = "www.jeremiepasserin.com, www.miquel-campos.com"
EMAIL = "geerem@hotmail.com, hello@miquel-campos.com, matsumoto@goshow.co.jp"
VERSION = [0, 2, 0]
TYPE = "ymt_arm_2jnt_01"
NAME = "arm"
DESCRIPTION = "Simple IK/FK chain, With IK space switch"


##########################################################
# CLASS
##########################################################
class Guide(ComponentGuide):

    compType = TYPE
    compName = NAME
    description = DESCRIPTION

    author = AUTHOR
    url = URL
    email = EMAIL
    version = VERSION

    connectors = ["ymt_shoulder_01"]

    # =====================================================
    def postInit(self):
        # type: () -> None
        # pylint: disable=attribute-defined-outside-init
        self.save_transform = ["root", "elbow", "wrist", "eff"]
        self.save_blade = ["blade"]

    # =====================================================
    def addObjects(self):
        # type: () -> None
        """Add more object to the object definition list.
        # @param self
        """
        # pylint: disable=attribute-defined-outside-init

        self.root = self.addRoot()

        vTemp = tra.getOffsetPosition(self.root, [2.5, 0, -.01])
        self.elbow = self.addLoc("elbow", self.root, vTemp)

        vTemp = tra.getOffsetPosition(self.root, [6, 0, 0])
        self.wrist = self.addLoc("wrist", self.elbow, vTemp)

        vTemp = tra.getOffsetPosition(self.root, [7, 0, 0])
        self.eff = self.addLoc("eff", self.wrist, vTemp)

        self.blade = self.addBlade("blade", self.root, self.elbow)
        att.unlockAttribute(self.blade, ["rx"])
        self.dispcrv = self.addDispCurve("crv", [self.root, self.elbow, self.wrist, self.eff])

    # =====================================================
    def addParameters(self):
        # type: () -> None
        """Add more parameter to the parameter definition list."""
        # pylint: disable=attribute-defined-outside-init

        # self.pType       = self.addParam("mode", "long", 0, 0)
        self.pBlend       = self.addParam("blend", "double", 1, 0, 1)
        # self.pBladeOffset = self.addParam("bladeOffset",  "float", 0, 0)
        self.pNeutralPose       = self.addParam("neutralpose", "bool", False)
        self.pIkRefArray  = self.addParam("ikrefarray",  "string", "")

        self.pUseIndex       = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam("parentJointIndex", "long", -1, None, None)

        # TODO: if have IK or IK/FK lock the axis position to force 2D Planar IK solver
        # Create a a method to lock and unlock while changing options in the PYSIDE component Settings


##########################################################
# Setting Page
##########################################################

class settingsTab(QtWidgets.QDialog, sui.Ui_Form):

    def __init__(self, parent=None):
        super(settingsTab, self).__init__(parent)
        self.setupUi(self)


class componentSettings(MayaQWidgetDockableMixin, componentMainSettings):

    def __init__(self, parent=None):
        self.toolName = TYPE
        # Delete old instances of the componet settings window.
        gqt.deleteInstances(self, MayaQDockWidget)

        super(self.__class__, self).__init__(parent=parent)
        self.settingsTab = settingsTab()

        self.setup_componentSettingWindow()
        self.create_componentControls()
        self.populate_componentControls()
        self.create_componentLayout()
        self.create_componentConnections()

    def setup_componentSettingWindow(self):
        self.mayaMainWindow = gqt.maya_main_window()

        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle(TYPE)
        self.resize(280, 350)

    def create_componentControls(self):
        return

    def populate_componentControls(self):
        """
        Populate the controls values from the custom attributes of the component.

        """
        #populate tab
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")

        # populate connections in main settings
        for cnx in Guide.connectors:
            self.mainSettingsTab.connector_comboBox.addItem(cnx)

        cBox = self.mainSettingsTab.connector_comboBox
        self.connector_items = [cBox.itemText(i) for i in range(cBox.count())]
        currentConnector = self.root.attr("connector").get()
        if currentConnector not in self.connector_items:
            self.mainSettingsTab.connector_comboBox.addItem(currentConnector)
            self.connector_items.append(currentConnector)
            pm.displayWarning("The current connector: %s, is not a valid "
                              "connector for this component. "
                              "Build will Fail!!")
        comboIndex = self.connector_items.index(currentConnector)
        self.mainSettingsTab.connector_comboBox.setCurrentIndex(comboIndex)

        #populate component settings
        self.settingsTab.ikfk_slider.setValue(int(self.root.attr("blend").get()*100))
        self.settingsTab.ikfk_spinBox.setValue(int(self.root.attr("blend").get()*100))
        if self.root.attr("neutralpose").get():
            self.settingsTab.neutralPose_checkBox.setCheckState(QtCore.Qt.Checked)
        else:
            self.settingsTab.neutralPose_checkBox.setCheckState(QtCore.Qt.Unchecked)

        ikRefArrayItems = self.root.attr("ikrefarray").get().split(",")
        for item in ikRefArrayItems:
            self.settingsTab.ikRefArray_listWidget.addItem(item)


    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):

        self.settingsTab.ikfk_slider.valueChanged.connect(partial(self.updateSlider, self.settingsTab.ikfk_slider, "blend"))
        self.settingsTab.ikfk_spinBox.valueChanged.connect(partial(self.updateSlider, self.settingsTab.ikfk_spinBox, "blend"))
        self.settingsTab.neutralPose_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.neutralPose_checkBox, "neutralpose"))

        self.settingsTab.ikRefArrayAdd_pushButton.clicked.connect(partial(self.addItem2listWidget, self.settingsTab.ikRefArray_listWidget, "ikrefarray"))
        self.settingsTab.ikRefArrayRemove_pushButton.clicked.connect(partial(self.removeSelectedFromListWidget, self.settingsTab.ikRefArray_listWidget, "ikrefarray"))
        self.settingsTab.ikRefArray_listWidget.installEventFilter(self)

        self.mainSettingsTab.connector_comboBox.currentIndexChanged.connect(
            partial(self.updateConnector,
                    self.mainSettingsTab.connector_comboBox,
                    self.connector_items))

    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.settingsTab.ikRefArray_listWidget:
                self.updateListAttr(sender, "ikrefarray")


    def dockCloseEventTriggered(self):
        gqt.deleteInstances(self, MayaQDockWidget)
