# pylint: disable=import-error,W0201,C0111,C0112
from functools import partial

from mgear.shifter.component import guide
from mgear.core import (
    pyqt,
    string,
    # dag,
    attribute,
    transform,
)
from mgear.vendor.Qt import QtWidgets, QtCore
from mgear import shifter

# from mgear.core.primitive import addTransform


from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui
import pymel.core as pm
from pymel.core import datatypes

from . import chain_guide_initializer

# guide info
AUTHOR = "yamahigashi"
EMAIL = "yamahigashi@gmail.com"
URL = "github.com/yamahigashi"
VERSION = [1, 0, 0]
TYPE = "ymt_surface_wire_01"
NAME = "surfaceWire"
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

    connectors = ["surface"]

    def postInit(self):
        """Initialize the position for the guide"""

        self.save_transform = ["root", "#_loc", "tan"]
        self.save_blade = ["blade"]
        self.addMinMax("#_loc", 1, -1)

    def addObjects(self):
        """Add the Guide Root, blade and locators"""

        self.root = self.addRoot()
        self.locs = self.addLocMulti("#_loc", self.root)

        v = transform.getOffsetPosition(self.locs[0], [0, 0.1, 0.0001])
        self.tan = self.addLoc("tan", self.root, v)
        self.blade = self.addBlade("blade", self.root, self.tan)

        centers = [self.root]
        centers.extend(self.locs)
        self.dispcrv = self.addDispCurve("crv", centers)
        self.addDispCurve("crvRef", centers, 3)

    def addParameters(self):
        """Add the configurations settings"""

        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pNeutralPose = self.addParam("neutralpose", "bool", False)
        self.pOverrideNegate = self.addParam("overrideNegate", "bool", False)
        self.pSlidingSurface   = self.addParam("isSlidingSurface", "bool", True)
        self.pSurfaceReference = self.addParam("surfaceReference", "string", "")
        self.pParentJointIndex = self.addParam("parentJointIndex", "long", -1, None, None)
        self.pAddJoints = self.addParam("addJoints", "bool", True)
        self.pSourceKeyable = self.addParam("sourceKeyable", "bool", True)
        self.pSurfaceKeyable = self.addParam("surfaceKeyable", "bool", True)
        self.pNumberOfControllers = self.addParam("numberOfControllers", "long", 3, 2, None)
        self.pCtlSize = self.addParam("ctlSize", "double", 1, None, None)
        self.pIcon = self.addParam("icon", "string", "cube")

    def modalPositions(self):
        """Launch a modal dialog to set position of the guide."""
        self.sections_number = None
        self.dir_axis = None
        self.spacing = None

        for name in self.save_transform:

            if "#" in name:

                print(name)

                init_window = chain_guide_initializer.exec_window()
                if init_window:
                    self.sections_number = init_window.sections_number
                    self.dir_axis = init_window.dir_axis
                    self.spacing = init_window.spacing

                # None the action is cancel
                else:
                    return False

                if self.sections_number:
                    if self.dir_axis == 0:  # X
                        offVec = datatypes.Vector(self.spacing, 0, 0)
                    elif self.dir_axis == 3:  # -X
                        offVec = datatypes.Vector(self.spacing * -1, 0, 0)
                    elif self.dir_axis == 1:  # Y
                        offVec = datatypes.Vector(0, self.spacing, 0)
                    elif self.dir_axis == 4:  # -Y
                        offVec = datatypes.Vector(0, self.spacing * -1, 0)
                    elif self.dir_axis == 2:  # Z
                        offVec = datatypes.Vector(0, 0, self.spacing)
                    elif self.dir_axis == 5:  # -Z
                        offVec = datatypes.Vector(0, 0, self.spacing * -1)

                    newPosition = datatypes.Vector(0, 0, 0)
                    for i in range(self.sections_number):
                        newPosition = offVec + newPosition
                        localName = string.replaceSharpWithPadding(name, i)
                        self.tra[localName] = transform.getTransformFromPos(
                            newPosition)
        return True


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
        self.iconsList = [
            "arrow",
            "circle",
            "compas",
            "cross",
            "crossarrow",
            "cube",
            "cubewithpeak",
            "cylinder",
            "diamond",
            "flower",
            "null",
            "pyramid",
            "sphere",
            "square"
        ]

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

        # populate component settings
        self.populateCheck(self.settingsTab.overrideNegate_checkBox, "overrideNegate")
        self.populateCheck(self.settingsTab.addJoints_checkBox, "addJoints")
        self.populateCheck(self.settingsTab.sourceKeyable_checkBox, "sourceKeyable")
        self.populateCheck(self.settingsTab.surfaceKeyable_checkBox, "surfaceKeyable")

        try:
            self.root.attr("isSlidingSurface").get()
        except Exception:
            self.root.pSlidingSurface = self.root.addParam("isSlidingSurface", "bool", True)
        self.populateCheck(self.settingsTab.isSlidingSurface,"isSlidingSurface")

        try:
            surfaceReference = self.root.attr("surfaceReference").get()
        except Exception:
            surfaceReference = ""
            self.root.pSurfaceReference = self.root.addParam("surfaceReference", "string", "")
        self.settingsTab.surfaceReference_listWidget.addItem(surfaceReference)

        self.settingsTab.ctlNum_doubleSpinBox.setValue(self.root.attr("numberOfControllers").get())
        self.settingsTab.ctlSize_doubleSpinBox.setValue(self.root.attr("ctlSize").get())
        sideIndex = self.iconsList.index(self.root.attr("icon").get())
        self.settingsTab.controlShape_comboBox.setCurrentIndex(sideIndex)

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

        # populate component settings
        self.mainSettingsTab.connector_comboBox.currentIndexChanged.connect(
            partial(self.updateConnector,
                    self.mainSettingsTab.connector_comboBox,
                    self.connector_items))

        self.settingsTab.overrideNegate_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.overrideNegate_checkBox,
                    "overrideNegate"))

        self.settingsTab.addJoints_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.addJoints_checkBox,
                    "addJoints"))

        self.settingsTab.sourceKeyable_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.sourceKeyable_checkBox,
                    "sourceKeyable"))

        self.settingsTab.surfaceKeyable_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.surfaceKeyable_checkBox,
                    "surfaceKeyable"))

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

        self.settingsTab.ctlNum_doubleSpinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.ctlNum_doubleSpinBox,
                    "numberOfControllers"))

        self.settingsTab.ctlSize_doubleSpinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.ctlSize_doubleSpinBox,
                    "ctlSize"))
        self.settingsTab.controlShape_comboBox.currentIndexChanged.connect(
            partial(self.updateControlShape,
                    self.settingsTab.controlShape_comboBox,
                    self.iconsList, "icon"))

    def updateMasterChain(self, lEdit, targetAttr):
        oType = pm.nodetypes.Transform

        oSel = pm.selected()
        compatible = [TYPE]
        if oSel:
            if oSel[0] == self.root:
                pm.displayWarning("Self root can not be Master. Cycle Warning")
            else:
                if (isinstance(oSel[0], oType)
                        and oSel[0].hasAttr("comp_type")
                        and oSel[0].attr("comp_type").get() in compatible):
                    # check master chain FK segments
                    self_len = self._get_chain_segments_length(self.root)
                    master_len = self._get_chain_segments_length(oSel[0])

                    if master_len >= self_len:
                        comp_name = oSel[0].name().replace("_root", "")
                        lEdit.setText(comp_name)
                        self.root.attr(targetAttr).set(lEdit.text())
                    else:
                        pm.displayWarning(
                            "Invalid Master: {} ".format(oSel[0]) +
                            "Current chain has: {} sections".format(self_len) +
                            " But Master chain has" +
                            " less sections: {}".format(str(master_len)))
                else:
                    pm.displayWarning("The selected element is not a "
                                      "chain root or compatible chain")
                    pm.displayWarning("Complatible chain componentes"
                                      " are: {}".format(str(compatible)))
        else:
            pm.displayWarning("Nothing selected.")
            if lEdit.text():
                lEdit.clear()
                self.root.attr(targetAttr).set("")
                pm.displayWarning("The previous Master Chain have been "
                                  "cleared")

    def _get_chain_segments_length(self, chain_root):
        module = shifter.importComponentGuide(chain_root.comp_type.get())
        componentGuide = getattr(module, "Guide")
        comp_guide = componentGuide()
        comp_guide.setFromHierarchy(chain_root)
        return len(comp_guide.pos)

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
