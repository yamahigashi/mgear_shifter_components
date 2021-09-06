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
from mgear.shifter.component.guide import ComponentGuide
import mgear.core.transform as tra


#Pyside
from mgear.shifter.component.guide import componentMainSettings
import mgear.core.pyqt as gqt
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget
import maya.OpenMayaUI as omui
QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()
from . import settingsUI as sui

# guide info
AUTHOR = "Jeremie Passerin, Miquel Campos"
URL = "www.jeremiepasserin.com, www.miquletd.com"
EMAIL = "geerem@hotmail.com, hello@miquel-campos.com"
VERSION = [1,0,0]
TYPE = "ymt_shoulder_01"
NAME = "shoulder"
DESCRIPTION = "Simple shoulder with space switch for\n the arm, and Orbit layer for the arm "

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
        self.save_transform = ["root", "tip"]
        self.save_blade = ["blade"]

    # =====================================================
    ## Add more object to the object definition list.
    # @param self
    def addObjects(self):

        self.root = self.addRoot()
        vTemp = tra.getOffsetPosition( self.root, [2,0,0])
        self.loc = self.addLoc("tip", self.root, vTemp)
        self.blade = self.addBlade("blade", self.root, self.loc)

        centers = [self.root, self.loc]
        self.dispcrv = self.addDispCurve("crv", centers)



    # =====================================================
    ## Add more parameter to the parameter definition list.
    # @param self
    def addParameters(self):

        self.pRefArray  = self.addParam("refArray", "string", "")
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
        self.resize(280, 350)

    def create_componentControls(self):
        return
        

    def populate_componentControls(self):
        """
        Populate the controls values from the custom attributes of the component.

        """
        #populate tab
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")

        #populate component settings
        refArrayItems = self.root.attr("refArray").get().split(",")
        for item in refArrayItems:
            self.settingsTab.refArray_listWidget.addItem(item)

        self.settingsTab.ctlOffsetPosX_doubleSpinBox.setValue(self.root.attr("ctlOffsetPosX").get())
        self.settingsTab.ctlOffsetPosY_doubleSpinBox.setValue(self.root.attr("ctlOffsetPosY").get())
        self.settingsTab.ctlOffsetPosZ_doubleSpinBox.setValue(self.root.attr("ctlOffsetPosZ").get())
        self.settingsTab.ctlOffsetSclX_doubleSpinBox.setValue(self.root.attr("ctlOffsetSclX").get())
        self.settingsTab.ctlOffsetSclY_doubleSpinBox.setValue(self.root.attr("ctlOffsetSclY").get())
        self.settingsTab.ctlOffsetSclZ_doubleSpinBox.setValue(self.root.attr("ctlOffsetSclZ").get())
        self.settingsTab.ctlOffsetRotX_doubleSpinBox.setValue(self.root.attr("ctlOffsetRotX").get())
        self.settingsTab.ctlOffsetRotY_doubleSpinBox.setValue(self.root.attr("ctlOffsetRotY").get())
        self.settingsTab.ctlOffsetRotZ_doubleSpinBox.setValue(self.root.attr("ctlOffsetRotZ").get())

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):

        self.settingsTab.refArrayAdd_pushButton.clicked.connect(partial(self.addItem2listWidget, self.settingsTab.refArray_listWidget, "refArray"))
        self.settingsTab.refArrayRemove_pushButton.clicked.connect(partial(self.removeSelectedFromListWidget, self.settingsTab.refArray_listWidget, "refArray"))
        self.settingsTab.refArray_listWidget.installEventFilter(self)

        self.settingsTab.ctlOffsetSclX_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetSclX_doubleSpinBox, "ctlOffsetSclX"))
        self.settingsTab.ctlOffsetSclY_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetSclY_doubleSpinBox, "ctlOffsetSclY"))
        self.settingsTab.ctlOffsetSclZ_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetSclZ_doubleSpinBox, "ctlOffsetSclZ"))

        self.settingsTab.ctlOffsetRotX_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetRotX_doubleSpinBox, "ctlOffsetRotX"))
        self.settingsTab.ctlOffsetRotY_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetRotY_doubleSpinBox, "ctlOffsetRotY"))
        self.settingsTab.ctlOffsetRotZ_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetRotZ_doubleSpinBox, "ctlOffsetRotZ"))

        self.settingsTab.ctlOffsetPosX_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetPosX_doubleSpinBox, "ctlOffsetPosX"))
        self.settingsTab.ctlOffsetPosY_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetPosY_doubleSpinBox, "ctlOffsetPosY"))
        self.settingsTab.ctlOffsetPosZ_doubleSpinBox.valueChanged.connect(partial(self.updateSpinBox, self.settingsTab.ctlOffsetPosZ_doubleSpinBox, "ctlOffsetPosZ"))


    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.settingsTab.refArray_listWidget:
                self.updateListAttr(sender, "refArray")




    def dockCloseEventTriggered(self):
        gqt.deleteInstances(self, MayaQDockWidget)
