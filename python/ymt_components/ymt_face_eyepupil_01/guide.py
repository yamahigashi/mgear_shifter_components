# pylint: disable=import-error,W0201,C0111,C0112
from functools import partial
import os

import maya.cmds as cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from mgear.shifter.component import guide
from mgear.core import pyqt
from mgear.core import string
from mgear.core import dag
from mgear.vendor.Qt import QtWidgets, QtCore
from mgear import shifter
from mgear.core import transform

from mgear.core.primitive import addTransform

from mgear.core import (
    transform,
    curve,
    applyop,
    attribute,
    icon,
    fcurve,
    vector,
    meshNavigation,
    node,
    primitive,
    utils,
)

from . import settingsUI as sui
import pymel.core as pm
# from pymel.core import datatypes

import ymt_shifter_utility as ymt_utility
# from . import chain_guide_initializer

# guide info
AUTHOR = "yamahigashi"
EMAIL = "yamahigashi@gmail.com"
URL = "github.com/yamahigashi"
VERSION = [1, 0, 0]
TYPE = "ymt_face_eyepupil_01"
NAME = "pupil"
DESCRIPTION = ""

##########################################################
# CLASS
##########################################################


class Guide(guide.ComponentGuide):
    """Component Guide Class"""

    compType = TYPE
    compName = NAME
    description = DESCRIPTION

    author = AUTHOR
    url = URL
    email = EMAIL
    version = VERSION

    connectors = ["orientation"]

    # =====================================================
    ##
    # @param self
    def postInit(self):
        self.save_transform = ["root", "sizeRef", "lookat", "sliding_surface"]

    # =====================================================
    # Add more object to the object definition list.
    # @param self
    def addObjects(self):

        self.root = self.addRoot()
        vTemp = transform.getOffsetPosition(self.root, [0, 0, 1])
        self.sizeRef = self.addLoc("sizeRef", self.root, vTemp)
        pm.delete(self.sizeRef.getShapes())
        attribute.lockAttribute(self.sizeRef)
        self.lookat = self.addLoc("lookat", self.root, vTemp)

        v = transform.getTranslation(self.root)
        if not hasattr(self, "sliding_surface") or self.sliding_surface is None:
            self.sliding_surface = self.addSliderSurface("sliding_surface", self.root, v)
        else:
            pm.parent(self.sliding_surface, self.root, absolute=False, relative=True)

    def addSliderSurface(self, name, parent, position=None):
        """pass."""
        if name not in self.tra.keys():
            self.tra[name] = transform.getTransformFromPos(position)

        pm.importFile(os.path.join(os.path.dirname(__file__), "assets", "surface.ma"))
        sliding_surface = pm.PyNode("sliding_surface")
        pm.rename(sliding_surface, self.getName("sliding_surface"))
        # sliding_surface.visibility.set(False)

        sliding_surface.setTransformation(self.tra[name])
        pm.parent(sliding_surface, parent)

        return sliding_surface

    # =====================================================
    # Add more parameter to the parameter definition list.
    # @param self
    def addParameters(self):

        self.pIcon = self.addParam("icon", "string", "cube")

        self.pIkRefArray = self.addParam("ikrefarray", "string", "")

        self.pJoint = self.addParam("joint", "bool", False)
        self.pJoint = self.addParam("uniScale", "bool", False)

        for s in ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"]:
            self.addParam("k_" + s, "bool", True)

        self.pDefault_RotOrder = self.addParam(
            "default_rotorder", "long", 0, 0, 5)
        self.pNeutralRotation = self.addParam("neutralRotation", "bool", True)
        self.pMirrorBehaviour = self.addParam("mirrorBehaviour", "bool", False)
        self.pCtlSize = self.addParam("ctlSize", "double", 1, None, None)
        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam(
            "parentJointIndex", "long", -1, None, None)
        self.pSlidingSurface   = self.addParam("isSlidingSurface", "bool", True)
        self.pSurfaceReference = self.addParam("surfaceReference", "string", "")

    def postDraw(self):
        "Add post guide draw elements to the guide"
        size = pm.xform(self.root, q=True, ws=True, scale=True)[0]
        self.add_ref_axis(self.root,
                          self.root.neutralRotation,
                          inverted=True,
                          width=.5 / size)

    def setFromHierarchy(self, root):
        self.root = root
        self.model = self.root.getParent(generations=-1)
        self.setParamDefValuesFromProperty(self.root)
        self.sliding_surface = pm.PyNode(self.getName("sliding_surface"))
        info = ymt_utility.serialize_nurbs_surface(self.sliding_surface.name())

        super(Guide, self).setFromHierarchy(root)
        pm.delete(self.sliding_surface)
        
        sliding_surface = ymt_utility.deserialize_nurbs_surface(self.getName("sliding_surface"), info)
        self.sliding_surface = pm.PyNode(sliding_surface)
        pm.parent(self.sliding_surface, self.root, absolute=False, relative=True)

    def get_guide_template_dict(self):
        """Override the base class method to add more data to the guide template dict"""
        c_dict = super(Guide, self).get_guide_template_dict()

        self.sliding_surface = pm.PyNode(self.getName("sliding_surface"))
        c_dict["sliding_surface"] = ymt_utility.serialize_nurbs_surface(self.sliding_surface.name())

        return c_dict

    def set_from_dict(self, c_dict):
        """Override the base class method to add more data to the guide template dict"""

        super(Guide, self).set_from_dict(c_dict)
        try:
            if self.sliding_surface is not None:
                pm.delete(self.sliding_surface)
        except AttributeError:
            pass

        sliding_surface = ymt_utility.deserialize_nurbs_surface(self.getName("sliding_surface"), c_dict["sliding_surface"])
        self.sliding_surface = pm.PyNode(sliding_surface)


##########################################################
# Setting Page
##########################################################


class settingsTab(QtWidgets.QDialog, sui.Ui_Form):
    """The Component settings UI"""

    def __init__(self, parent=None):
        super(settingsTab, self).__init__(parent)
        self.setupUi(self)


class componentSettings(MayaQWidgetDockableMixin, guide.componentMainSettings):
    """Create the component setting window"""

    def __init__(self, parent=None):
        self.toolName = TYPE
        # Delete old instances of the componet settings window.
        pyqt.deleteInstances(self, MayaQDockWidget)
        self.iconsList = ['arrow',
                          'circle',
                          'compas',
                          'cross',
                          'crossarrow',
                          'cube',
                          'cubewithpeak',
                          'cylinder',
                          'diamond',
                          'flower',
                          'null',
                          'pyramid',
                          'sphere',
                          'square']

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
        self.resize(280, 520)

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

        self.populateCheck(self.settingsTab.joint_checkBox, "joint")
        self.populateCheck(self.settingsTab.uniScale_checkBox, "uniScale")
        self.populateCheck(self.settingsTab.neutralRotation_checkBox,
                           "neutralRotation")
        self.populateCheck(self.settingsTab.mirrorBehaviour_checkBox,
                           "mirrorBehaviour")
        self.settingsTab.ctlSize_doubleSpinBox.setValue(
            self.root.attr("ctlSize").get())
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

        self.settingsTab.ro_comboBox.setCurrentIndex(
            self.root.attr("default_rotorder").get())

        ikRefArrayItems = self.root.attr("ikrefarray").get().split(",")
        for item in ikRefArrayItems:
            self.settingsTab.ikRefArray_listWidget.addItem(item)

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
        self.populateCheck(self.settingsTab.isSlidingSurface,"isSlidingSurface")
        surfaceReference = self.root.attr("surfaceReference").get()
        self.settingsTab.surfaceReference_listWidget.addItem(surfaceReference)

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):

        self.settingsTab.joint_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.joint_checkBox,
                    "joint"))
        self.settingsTab.uniScale_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.uniScale_checkBox,
                    "uniScale"))
        self.settingsTab.neutralRotation_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.neutralRotation_checkBox,
                    "neutralRotation"))
        self.settingsTab.mirrorBehaviour_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.mirrorBehaviour_checkBox,
                    "mirrorBehaviour"))
        self.settingsTab.ctlSize_doubleSpinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.ctlSize_doubleSpinBox,
                    "ctlSize"))
        self.settingsTab.controlShape_comboBox.currentIndexChanged.connect(
            partial(self.updateControlShape,
                    self.settingsTab.controlShape_comboBox,
                    self.iconsList, "icon"))

        self.settingsTab.tx_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.tx_checkBox, "k_tx"))
        self.settingsTab.ty_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.ty_checkBox, "k_ty"))
        self.settingsTab.tz_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.tz_checkBox, "k_tz"))
        self.settingsTab.rx_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.rx_checkBox, "k_rx"))
        self.settingsTab.ry_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.ry_checkBox, "k_ry"))
        self.settingsTab.rz_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.rz_checkBox, "k_rz"))
        self.settingsTab.ro_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.ro_checkBox, "k_ro"))
        self.settingsTab.sx_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.sx_checkBox, "k_sx"))
        self.settingsTab.sy_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.sy_checkBox, "k_sy"))
        self.settingsTab.sz_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.sz_checkBox, "k_sz"))

        self.settingsTab.ro_comboBox.currentIndexChanged.connect(
            partial(self.updateComboBox,
                    self.settingsTab.ro_comboBox,
                    "default_rotorder"))

        self.settingsTab.ikRefArrayAdd_pushButton.clicked.connect(
            partial(self.addItem2listWidget,
                    self.settingsTab.ikRefArray_listWidget,
                    "ikrefarray"))
        self.settingsTab.ikRefArrayRemove_pushButton.clicked.connect(
            partial(self.removeSelectedFromListWidget,
                    self.settingsTab.ikRefArray_listWidget,
                    "ikrefarray"))
        self.settingsTab.ikRefArray_listWidget.installEventFilter(self)

        self.mainSettingsTab.connector_comboBox.currentIndexChanged.connect(
            partial(self.updateConnector,
                    self.mainSettingsTab.connector_comboBox,
                    self.connector_items))

        self.settingsTab.isSlidingSurface.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.isSlidingSurface,
                    "isSlidingSurface"))

        self.settingsTab.surfaceReferenceAdd_pushButton.clicked.connect(
            partial(
                self.addItem2listWidget,
                self.settingsTab.surfaceReference_listWidget,
                "surfaceReference"
            )
        )

        self.settingsTab.surfaceReferenceRemove_pushButton.clicked.connect(
            partial(
                self.removeSelectedFromListWidget,
                self.settingsTab.surfaceReference_listWidget,
                "surfaceReference"
            )
        )

    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.settingsTab.ikRefArray_listWidget:
                self.updateListAttr(sender, "ikrefarray")
            return True
        else:
            return QtWidgets.QDialog.eventFilter(self, sender, event)

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
