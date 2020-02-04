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
# pyMel
import pymel.core as pm

# mgear
import mgear.shifter_classic_components.arm_2jnt_04.guide as arm_2jnt_04

from mgear.shifter.component.guide import componentMainSettings
from mgear.core import pyqt
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget
from mgear.vendor.Qt import QtWidgets, QtCore
import settingsUI as sui


# guide info
AUTHOR = "Jeremie Passerin, Miquel Campos, Takayoshi MATSUMOTO"
URL = "www.jeremiepasserin.com, www.miquel-campos.com"
EMAIL = "geerem@hotmail.com, hello@miquel-campos.com, yamahigashi@gmail.com"
VERSION = [0, 2, 0]
TYPE = "ymt_arm_2jnt_02"
NAME = "arm"
DESCRIPTION = "Simple IK/FK chain, With IK space switch"


##########################################################
# CLASS
##########################################################
class Guide(arm_2jnt_04.Guide):

    compType = TYPE
    compName = NAME
    description = DESCRIPTION

    author = AUTHOR
    url = URL
    email = EMAIL
    version = VERSION

    connectors = ["ymt_shoulder_01"]

    def addParameters(self):
        super(Guide, self).addParameters()

        self.pFkRefArray = self.addParam("fkrefarray", "string", "")
        self.pSmoothStep = self.addParam("smoothStep", "bool", False)


class settingsTab(QtWidgets.QDialog, sui.Ui_Form):
    """The Component settings UI"""

    def __init__(self, parent=None):
        super(settingsTab, self).__init__(parent)
        self.setupUi(self)


class componentSettings(MayaQWidgetDockableMixin, componentMainSettings):
    """Create the component setting window"""

    def __init__(self, parent=None):
        self.toolName = TYPE
        # Delete old instances of the componet settings window.
        pyqt.deleteInstances(self, MayaQDockWidget)

        super(self.__class__, self).__init__(parent=parent)
        self.settingsTab = settingsTab()

        self.setup_componentSettingWindow()
        self.create_componentControls()
        self.populate_componentControls()
        self.create_componentLayout()
        self.create_componentConnections()

    def setup_componentSettingWindow(self):
        self.mayaMainWindow = pyqt.maya_main_window()

        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle(TYPE)
        self.resize(280, 780)

    def create_componentControls(self):
        return

    def populate_componentControls(self):
        """Populate Controls

        Populate the controls values from the custom attributes of the
        component.

        """
        # populate tab
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")

        # populate component settings
        self.settingsTab.ikfk_slider.setValue(
            int(self.root.attr("blend").get() * 100))
        self.settingsTab.ikfk_spinBox.setValue(
            int(self.root.attr("blend").get() * 100))
        self.settingsTab.maxStretch_spinBox.setValue(
            self.root.attr("maxstretch").get())
        self.settingsTab.elbowThickness_spinBox.setValue(
            self.root.attr("elbowThickness").get())
        self.populateCheck(self.settingsTab.ikTR_checkBox, "ikTR")
        self.populateCheck(self.settingsTab.supportJoints_checkBox,
                           "supportJoints")
        self.populateCheck(
            self.settingsTab.guideOrientWrist_checkBox, "guideOrientWrist"
        )
        self.populateCheck(self.settingsTab.mirrorMid_checkBox, "mirrorMid")
        self.populateCheck(self.settingsTab.mirrorIK_checkBox, "mirrorIK")
        self.populateCheck(self.settingsTab.extraTweak_checkBox, "extraTweak")
        self.populateCheck(self.settingsTab.smoothStep_checkBox, "smoothStep")
        self.settingsTab.div0_spinBox.setValue(self.root.attr("div0").get())
        self.settingsTab.div1_spinBox.setValue(self.root.attr("div1").get())

        ikRefArrayItems = self.root.attr("ikrefarray").get().split(",")
        for item in ikRefArrayItems:
            self.settingsTab.ikRefArray_listWidget.addItem(item)

        upvRefArrayItems = self.root.attr("upvrefarray").get().split(",")
        for item in upvRefArrayItems:
            self.settingsTab.upvRefArray_listWidget.addItem(item)

        pinRefArrayItems = self.root.attr("pinrefarray").get().split(",")
        for item in pinRefArrayItems:
            self.settingsTab.pinRefArray_listWidget.addItem(item)

        fkRefArrayItems = self.root.attr("fkrefarray").get().split(",")
        for item in fkRefArrayItems:
            self.settingsTab.fkRefArray_listWidget.addItem(item)

        # populate connections in main settings
        self.c_box = self.mainSettingsTab.connector_comboBox
        for cnx in Guide.connectors:
            self.c_box.addItem(cnx)
        self.connector_items = [self.c_box.itemText(i) for i in
                                range(self.c_box.count())]

        currentConnector = self.root.attr("connector").get()
        if currentConnector not in self.connector_items:
            self.c_box.addItem(currentConnector)
            self.connector_items.append(currentConnector)
            pm.displayWarning(
                "The current connector: %s, is not a valid connector for this"
                " component. Build will Fail!!")
        comboIndex = self.connector_items.index(currentConnector)
        self.c_box.setCurrentIndex(comboIndex)

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):

        self.settingsTab.ikfk_slider.valueChanged.connect(
            partial(self.updateSlider, self.settingsTab.ikfk_slider, "blend"))

        self.settingsTab.ikfk_spinBox.valueChanged.connect(
            partial(self.updateSlider, self.settingsTab.ikfk_spinBox, "blend"))

        self.settingsTab.maxStretch_spinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.maxStretch_spinBox, "maxstretch"))
        self.settingsTab.elbowThickness_spinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.elbowThickness_spinBox, "elbowThickness"))

        self.settingsTab.div0_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.div0_spinBox, "div0"))

        self.settingsTab.div1_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.div1_spinBox, "div1"))

        self.settingsTab.squashStretchProfile_pushButton.clicked.connect(
            self.setProfile)

        self.settingsTab.ikTR_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.ikTR_checkBox, "ikTR"))

        self.settingsTab.supportJoints_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.supportJoints_checkBox,
                    "supportJoints"))

        self.settingsTab.guideOrientWrist_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.guideOrientWrist_checkBox,
                    "guideOrientWrist"))

        self.settingsTab.mirrorMid_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.mirrorMid_checkBox, "mirrorMid"))

        self.settingsTab.extraTweak_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.extraTweak_checkBox, "extraTweak"))

        self.settingsTab.smoothStep_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.smoothStep_checkBox, "smoothStep"))

        self.settingsTab.mirrorIK_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.mirrorIK_checkBox,
                    "mirrorIK"))

        self.settingsTab.ikRefArrayAdd_pushButton.clicked.connect(
            partial(self.addItem2listWidget,
                    self.settingsTab.ikRefArray_listWidget,
                    "ikrefarray"))

        self.settingsTab.ikRefArrayRemove_pushButton.clicked.connect(
            partial(self.removeSelectedFromListWidget,
                    self.settingsTab.ikRefArray_listWidget,
                    "ikrefarray"))

        self.settingsTab.ikRefArray_copyRef_pushButton.clicked.connect(
            partial(self.copyFromListWidget,
                    self.settingsTab.upvRefArray_listWidget,
                    self.settingsTab.ikRefArray_listWidget,
                    "ikrefarray"))

        self.settingsTab.ikRefArray_listWidget.installEventFilter(self)

        self.settingsTab.upvRefArrayAdd_pushButton.clicked.connect(
            partial(self.addItem2listWidget,
                    self.settingsTab.upvRefArray_listWidget,
                    "upvrefarray"))

        self.settingsTab.upvRefArrayRemove_pushButton.clicked.connect(
            partial(self.removeSelectedFromListWidget,
                    self.settingsTab.upvRefArray_listWidget,
                    "upvrefarray"))

        self.settingsTab.upvRefArray_copyRef_pushButton.clicked.connect(
            partial(self.copyFromListWidget,
                    self.settingsTab.ikRefArray_listWidget,
                    self.settingsTab.upvRefArray_listWidget,
                    "upvrefarray"))

        self.settingsTab.upvRefArray_listWidget.installEventFilter(self)

        self.settingsTab.pinRefArrayAdd_pushButton.clicked.connect(
            partial(self.addItem2listWidget,
                    self.settingsTab.pinRefArray_listWidget,
                    "pinrefarray"))

        self.settingsTab.pinRefArrayRemove_pushButton.clicked.connect(
            partial(self.removeSelectedFromListWidget,
                    self.settingsTab.pinRefArray_listWidget,
                    "pinrefarray"))

        self.settingsTab.pinRefArray_copyRef_pushButton.clicked.connect(
            partial(self.copyFromListWidget,
                    self.settingsTab.ikRefArray_listWidget,
                    self.settingsTab.pinRefArray_listWidget,
                    "pinrefarray"))

        self.settingsTab.pinRefArray_listWidget.installEventFilter(self)

        self.settingsTab.fkRefArrayAdd_pushButton.clicked.connect(
            partial(self.addItem2listWidget,
                    self.settingsTab.fkRefArray_listWidget,
                    "fkrefarray"))

        self.settingsTab.fkRefArrayRemove_pushButton.clicked.connect(
            partial(self.removeSelectedFromListWidget,
                    self.settingsTab.fkRefArray_listWidget,
                    "fkrefarray"))

        self.settingsTab.fkRefArray_copyRef_pushButton.clicked.connect(
            partial(self.copyFromListWidget,
                    self.settingsTab.ikRefArray_listWidget,
                    self.settingsTab.fkRefArray_listWidget,
                    "fkrefarray"))

        self.settingsTab.fkRefArray_listWidget.installEventFilter(self)

        self.mainSettingsTab.connector_comboBox.currentIndexChanged.connect(
            partial(self.updateConnector,
                    self.mainSettingsTab.connector_comboBox,
                    self.connector_items))

    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.settingsTab.ikRefArray_listWidget:
                self.updateListAttr(sender, "ikrefarray")
            elif sender == self.settingsTab.upvRefArray_listWidget:
                self.updateListAttr(sender, "upvrefarray")
            elif sender == self.settingsTab.pinRefArray_listWidget:
                self.updateListAttr(sender, "pinrefarray")
            elif sender == self.settingsTab.fkRefArray_listWidget:
                self.updateListAttr(sender, "fkrefarray")
            return True
        else:
            return QtWidgets.QDialog.eventFilter(self, sender, event)

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
