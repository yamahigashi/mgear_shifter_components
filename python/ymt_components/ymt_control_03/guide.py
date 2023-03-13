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

#############################################
# GLOBAL
#############################################
from functools import partial

# pyMel
import pymel.core as pm
import pymel.core.datatypes as dt

# mgear
from mgear.shifter.component.guide import ComponentGuide

#Pyside
from mgear.shifter.component.guide import componentMainSettings
import mgear.core.pyqt as gqt
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget
import maya.OpenMayaUI as omui
QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()
import settingsUI as sui


# guide info
AUTHOR = "Jeremie Passerin, Miquel Campos"
URL = "www.jeremiepasserin.com, www.miquel-campos.com"
EMAIL = "geerem@hotmail.com, hello@miquel-campos.com"
VERSION = [1,0,1]
TYPE = "ymt_control_03"
NAME = "control"
DESCRIPTION = "Simple controler with space switch and Rot order selection. \nThis component can use the root rotation to place  the control orientation"
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

    # =====================================================
    ##
    # @param self
    def postInit(self):
        self.save_transform = ["root"]

    # =====================================================
    ## Add more object to the object definition list.
    # @param self
    def addObjects(self):

        self.root = self.addRoot()


    # =====================================================
    ## Add more parameter to the parameter definition list.
    # @param self
    def addParameters(self):

        self.pIcon = self.addParam("icon", "string", "cube")

        self.pIkRefArray = self.addParam("ikrefarray",  "string", "")
        self.pRotRefArray = self.addParam("rotrefarray",  "string", "")

        self.pJoint = self.addParam("joint", "bool", False)
        self.pJoint = self.addParam("uniScale", "bool", True)

        for s in ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"]:
            self.addParam("k_" + s, "bool", True)

        self.pDefault_RotOrder = self.addParam("default_rotorder", "long", 0, 0, 5)
        self.pNeutralRotation = self.addParam("neutralRotation", "bool", True)
        self.pCtlSize = self.addParam("ctlSize", "double", 1, None, None)
        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam("parentJointIndex", "long", -1, None, None)

        self.pCtlOffsetSclX = self.addParam("ctlOffsetSclX", "double", 1, -360, 360)
        self.pCtlOffsetSclY = self.addParam("ctlOffsetSclY", "double", 1, -360, 360)
        self.pCtlOffsetSclZ = self.addParam("ctlOffsetSclZ", "double", 1, -360, 360)

        self.pCtlOffsetRotX = self.addParam("ctlOffsetRotX", "double", 0, -360, 360)
        self.pCtlOffsetRotY = self.addParam("ctlOffsetRotY", "double", 0, -360, 360)
        self.pCtlOffsetRotZ = self.addParam("ctlOffsetRotZ", "double", 0, -360, 360)

        self.pCtlOffsetPosX = self.addParam("ctlOffsetPosX", "double", 0, -999, 999)
        self.pCtlOffsetPosY = self.addParam("ctlOffsetPosY", "double", 0, -999, 999)
        self.pCtlOffsetPosZ = self.addParam("ctlOffsetPosZ", "double", 0, -999, 999)

        return

##########################################################
# Setting Page
##########################################################

class settingsTab(QtWidgets.QDialog, sui.Ui_Form):

    def __init__(self, parent=None):
        super(settingsTab, self).__init__(parent)
        self.setupUi(self)


class componentSettings(MayaQWidgetDockableMixin, componentMainSettings):

    def __init__(self, parent = None):
        self.toolName = TYPE
        # Delete old instances of the componet settings window.
        gqt.deleteInstances(self, MayaQDockWidget)
        self.iconsList = ['arrow', 'circle', 'compas', 'cross', 'crossarrow', 'cube', 'cubewithpeak', 'cylinder', 'diamond', 'flower', 'null', 'pyramid', 'sphere', 'square']

        super(self.__class__, self).__init__(parent = parent)
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
        self.resize(280, 520)

    def create_componentControls(self):
        return
        

    def populate_componentControls(self):
        """
        Populate the controls values from the custom attributes of the component.

        """
        #populate tab
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")

        #populate component settings

        self.populateCheck(self.settingsTab.joint_checkBox, "joint")
        self.populateCheck(self.settingsTab.uniScale_checkBox, "uniScale")
        self.populateCheck(self.settingsTab.neutralRotation_checkBox, "neutralRotation")
        self.settingsTab.ctlSize_doubleSpinBox.setValue(self.root.attr("ctlSize").get())
        self.settingsTab.ctlOffsetPosX_doubleSpinBox.setValue(self.root.attr("ctlOffsetPosX").get())
        self.settingsTab.ctlOffsetPosY_doubleSpinBox.setValue(self.root.attr("ctlOffsetPosY").get())
        self.settingsTab.ctlOffsetPosZ_doubleSpinBox.setValue(self.root.attr("ctlOffsetPosZ").get())
        self.settingsTab.ctlOffsetSclX_doubleSpinBox.setValue(self.root.attr("ctlOffsetSclX").get())
        self.settingsTab.ctlOffsetSclY_doubleSpinBox.setValue(self.root.attr("ctlOffsetSclY").get())
        self.settingsTab.ctlOffsetSclZ_doubleSpinBox.setValue(self.root.attr("ctlOffsetSclZ").get())
        self.settingsTab.ctlOffsetRotX_doubleSpinBox.setValue(self.root.attr("ctlOffsetRotX").get())
        self.settingsTab.ctlOffsetRotY_doubleSpinBox.setValue(self.root.attr("ctlOffsetRotY").get())
        self.settingsTab.ctlOffsetRotZ_doubleSpinBox.setValue(self.root.attr("ctlOffsetRotZ").get())
        sideIndex = self.iconsList.index(self.root.attr("icon").get())
        self.settingsTab.controlShape_comboBox.setCurrentIndex(sideIndex)

        self.populateCheck(self.settingsTab.tx_checkBox, "k_tx")
        self.populateCheck(self.settingsTab.ty_checkBox, "k_ty")
        self.populateCheck(self.settingsTab.tz_checkBox, "k_tz")
        self.populateCheck(self.settingsTab.rx_checkBox, "k_rx")
        self.populateCheck(self.settingsTab.ry_checkBox, "k_ry")
        self.populateCheck(self.settingsTab.rz_checkBox, "k_rz")
        self.populateCheck(self.settingsTab.ro_checkBox, "k_ro")
        self.populateCheck(self.settingsTab.sx_checkBox, "k_sx")
        self.populateCheck(self.settingsTab.sy_checkBox, "k_sy")
        self.populateCheck(self.settingsTab.sz_checkBox, "k_sz")

        self.settingsTab.ro_comboBox.setCurrentIndex(self.root.attr("default_rotorder").get())

        ikRefArray = self.root.attr("ikrefarray").get() or ""
        ikRefArrayItems = ikRefArray.split(",")
        for item in ikRefArrayItems:
            self.settingsTab.ikRefArray_listWidget.addItem(item)

        rotRefArray = self.root.attr("rotrefarray").get() or ""
        rotRefArrayItems = rotRefArray.split(",")
        for item in rotRefArrayItems:
            self.settingsTab.rotRefArray_listWidget.addItem(item)



    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):

        self.settingsTab.joint_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.joint_checkBox, "joint"))
        self.settingsTab.uniScale_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.uniScale_checkBox, "uniScale"))
        self.settingsTab.neutralRotation_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.neutralRotation_checkBox, "neutralRotation"))
        self.settingsTab.ctlSize_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlSize_doubleSpinBox, "ctlSize"))
        self.settingsTab.controlShape_comboBox.currentIndexChanged.connect(partial(self.updateControlShape, self.settingsTab.controlShape_comboBox, self.iconsList, "icon"))

        self.settingsTab.ctlOffsetSclX_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetSclX_doubleSpinBox, "ctlOffsetSclX"))
        self.settingsTab.ctlOffsetSclY_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetSclY_doubleSpinBox, "ctlOffsetSclY"))
        self.settingsTab.ctlOffsetSclZ_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetSclZ_doubleSpinBox, "ctlOffsetSclZ"))

        self.settingsTab.ctlOffsetRotX_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetRotX_doubleSpinBox, "ctlOffsetRotX"))
        self.settingsTab.ctlOffsetRotY_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetRotY_doubleSpinBox, "ctlOffsetRotY"))
        self.settingsTab.ctlOffsetRotZ_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetRotZ_doubleSpinBox, "ctlOffsetRotZ"))

        self.settingsTab.ctlOffsetPosX_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetPosX_doubleSpinBox, "ctlOffsetPosX"))
        self.settingsTab.ctlOffsetPosY_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetPosY_doubleSpinBox, "ctlOffsetPosY"))
        self.settingsTab.ctlOffsetPosZ_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetPosZ_doubleSpinBox, "ctlOffsetPosZ"))

        self.settingsTab.tx_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.tx_checkBox, "k_tx"))
        self.settingsTab.ty_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.ty_checkBox, "k_ty"))
        self.settingsTab.tz_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.tz_checkBox, "k_tz"))
        self.settingsTab.rx_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.rx_checkBox, "k_rx"))
        self.settingsTab.ry_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.ry_checkBox, "k_ry"))
        self.settingsTab.rz_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.rz_checkBox, "k_rz"))
        self.settingsTab.ro_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.ro_checkBox, "k_ro"))
        self.settingsTab.sx_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.sx_checkBox, "k_sx"))
        self.settingsTab.sy_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.sy_checkBox, "k_sy"))
        self.settingsTab.sz_checkBox.stateChanged.connect(partial(self.updateCheck, self.settingsTab.sz_checkBox, "k_sz"))

        self.settingsTab.ro_comboBox.currentIndexChanged.connect(partial(self.updateComboBox, self.settingsTab.ro_comboBox, "default_rotorder"))

        self.settingsTab.ikRefArrayAdd_pushButton.clicked.connect(partial(self.addItem2listWidget, self.settingsTab.ikRefArray_listWidget, "ikrefarray"))
        self.settingsTab.ikRefArrayRemove_pushButton.clicked.connect(partial(self.removeSelectedFromListWidget, self.settingsTab.ikRefArray_listWidget, "ikrefarray"))
        self.settingsTab.ikRefArray_listWidget.installEventFilter(self)

        self.settingsTab.rotRefArrayAdd_pushButton.clicked.connect(partial(self.addItem2listWidget, self.settingsTab.rotRefArray_listWidget, "rotrefarray"))
        self.settingsTab.rotRefArrayRemove_pushButton.clicked.connect(partial(self.removeSelectedFromListWidget, self.settingsTab.rotRefArray_listWidget, "rotrefarray"))
        self.settingsTab.rotRefArray_listWidget.installEventFilter(self)

    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.settingsTab.ikRefArray_listWidget:
                self.updateListAttr(sender, "ikrefarray")

            if sender == self.settingsTab.rotRefArray_listWidget:
                self.updateListAttr(sender, "rotrefarray")


    def dockCloseEventTriggered(self):
        gqt.deleteInstances(self, MayaQDockWidget)

    
