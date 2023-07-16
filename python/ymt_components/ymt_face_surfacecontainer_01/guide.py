# pylint: disable=import-error,W0201,C0111,C0112
import os

from mgear.shifter.component import guide
from mgear.core import pyqt
from mgear.vendor.Qt import QtWidgets, QtCore
from mgear.core import transform


from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui
import pymel.core as pm

import ymt_shifter_utility as ymt_utility

# guide info
AUTHOR = "yamahigashi"
EMAIL = "yamahigashi@gmail.com"
URL = "github.com/yamahigashi"
VERSION = [1, 0, 0]
TYPE = "ymt_face_surfacecontainer_01"
NAME = "surface"
DESCRIPTION = "Container for nurbs surface"

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
        try:  # noqa: FURB107
            if self.sliding_surface is not None:
                pm.delete(self.sliding_surface)
        except AttributeError:
            pass

        sliding_surface = ymt_utility.deserialize_nurbs_surface(self.getName("sliding_surface"), c_dict["sliding_surface"])
        self.sliding_surface = pm.PyNode(sliding_surface)

    def postInit(self):
        """Initialize the position for the guide"""

        self.save_transform = ["root", "sliding_surface"]

    def addObjects(self):
        """Add the Guide Root, blade and locators"""

        self.root = self.addRoot()

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

        sliding_surface.setTransformation(self.tra[name])
        pm.parent(sliding_surface, parent)

        return sliding_surface

    def addParameters(self):
        """Add the configurations settings"""

        self.pUseIndex         = self.addParam("useIndex",         "bool", False)
        self.pNeutralPose      = self.addParam("neutralpose",      "bool", False)
        self.pParentJointIndex = self.addParam("parentJointIndex", "long", -1, None, None)


##########################################################
# Setting Page
##########################################################
class settingsTab(QtWidgets.QDialog, sui.Ui_Form):

    def __init__(self, parent=None):
        super(settingsTab, self).__init__(parent)
        self.setupUi(self)


class componentSettings(MayaQWidgetDockableMixin, guide.componentMainSettings):

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
        self.resize(280, 350)

    def create_componentControls(self):
        pass

    def populate_componentControls(self):
        """Populate Controls

        Populate the controls values from the custom attributes of the
        component.

        """
        # populate tab
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):
        pass

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
