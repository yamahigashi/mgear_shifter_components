# pylint: disable=import-error,W0201,C0111,C0112
import os
from functools import partial

from mgear.shifter.component import guide
from mgear.core import pyqt
from mgear.core import string
# from mgear.core import dag
from mgear.vendor.Qt import QtWidgets, QtCore
from mgear import shifter
from mgear.core import transform

# from mgear.core.transform import getTransform
# from mgear.core.transform import getTransformLookingAt
# from mgear.core.transform import getChainTransform2
# from mgear.core.transform import setMatrixPosition
# from mgear.core.primitive import addTransform


from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui
import pymel.core as pm
from pymel.core import datatypes

import ymt_shifter_utility as ymt_utility
from . import chain_guide_initializer

# guide info
AUTHOR = "yamahigashi"
EMAIL = "yamahigashi@gmail.com"
URL = "github.com/yamahigashi"
VERSION = [1, 0, 0]
TYPE = "ymt_face_liparound_01"
NAME = "aroundlip"
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

    connectors = ["mouth_01", "lip_01"]

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

    def postInit(self):
        """Initialize the position for the guide"""

        #                     [0       1                  2        -1
        self.save_transform = ["root", "sliding_surface", "#_loc", "tan"]
        self.save_blade = ["blade"]
        self.addMinMax("#_loc", 1, -1)

    def addObjects(self):
        """Add the Guide Root, blade and locators"""

        self.root = self.addRoot()
        self.locs = self.addLocMulti("#_loc", self.root)

        centers = []
        centers.extend(self.locs)
        self.dispcrv = self.addDispCurve("crv", centers)
        self.addDispCurve("crvRef", centers, 3)

        centers = []
        centers.extend(self.locs)
        self.dispcrv = self.addDispCurve("crv", centers)
        self.addDispCurve("crvRef", centers, 3)

        v = transform.getOffsetPosition(self.root, [0, 0.0000001, 2.5])
        self.tan = self.addLoc("tan", self.root, v)
        self.blade = self.addBlade("blade", self.root, self.tan)

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

    def addParameters(self):
        """Add the configurations settings"""

        self.pNeutralPose = self.addParam("neutralpose", "bool", False)
        self.pOverrideNegate = self.addParam("overrideNegate", "bool", False)

        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam("parentJointIndex", "long", -1, None, None)
        self.pSlidingSurface   = self.addParam("isSlidingSurface", "bool", True)
        self.pSurfaceReference = self.addParam("surfaceReference", "string", "")
        self.pCheekLeftReference = self.addParam("cheekLeftReference", "string", "")
        self.pCheekRightReference = self.addParam("cheekRightReference", "string", "")

    def modalPositions(self):
        """Launch a modal dialog to set position of the guide."""
        self.sections_number = None
        self.dir_axis = None
        self.spacing = None

        for name in self.save_transform:

            if "#" in name:

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
        self.settingsTab.surfaceReference_lineEdit.setText(surfaceReference)

        cheekLeftReference = self.root.attr("cheekLeftReference").get()
        self.settingsTab.cheekLeft_lineEdit.setText(cheekLeftReference)

        cheekRightReference = self.root.attr("cheekRightReference").get()
        self.settingsTab.cheekRight_lineEdit.setText(cheekRightReference)

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):

        self.settingsTab.overrideNegate_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.overrideNegate_checkBox,
                    "overrideNegate"))

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
                self.addReference,
                self.settingsTab.surfaceReference_lineEdit,
                "surfaceReference"
            )
        )

        self.settingsTab.surfaceReferenceRemove_pushButton.clicked.connect(
            partial(
                self.removeReference,
                self.settingsTab.surfaceReference_lineEdit,
                "surfaceReference"
            )
        )

        self.settingsTab.cheekLeftAdd_pushButton.clicked.connect(
            partial(
                self.addReference,
                self.settingsTab.cheekLeft_lineEdit,
                "cheekLeftReference"
            )
        )

        self.settingsTab.cheekLeftRemove_pushButton.clicked.connect(
            partial(
                self.removeReference,
                self.settingsTab.cheekLeft_lineEdit,
                "cheekLeftReference"
            )
        )

        self.settingsTab.cheekRightAdd_pushButton.clicked.connect(
            partial(
                self.addReference,
                self.settingsTab.cheekRight_lineEdit.setText,
                "cheekRightReference"
            )
        )

        self.settingsTab.cheekRightRemove_pushButton.clicked.connect(
            partial(
                self.removeReference,
                self.settingsTab.cheekRight_lineEdit,
                "cheekRightReference"
            )
        )

    def addReference(self, lineEdit, targetAttr):
        oSel = pm.selected()
        compatible = ["nurbsSurface"]

        def __findRoot(oNode):
            if oNode.hasAttr("isGearGuide"):
                return oNode

            if oNode.getParent():
                return __findRoot(oNode.getParent())
            else:
                raise Exception("Root not found")

        if oSel:
            if (isinstance(oSel[0], pm.nodetypes.Transform)
                    and oSel[0].getShape()
                    and oSel[0].getShape().nodeType() in compatible):

                root = __findRoot(oSel[0])
                lineEdit.setText(root.name())
                self.root.attr(targetAttr).set(root.name())

            elif (isinstance(oSel[0], pm.nodetypes.Transform)
                  and oSel[0].hasAttr("isGearGuide")
            ):
                root = oSel[0]
                lineEdit.setText(root.name())
                self.root.attr(targetAttr).set(root.name())

            else:
                pm.displayWarning("Select a nurbsSurface")

    def removeReference(self, lineEdit, targetAttr):
        lineEdit.clear()
        self.root.attr(targetAttr).set("")

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
