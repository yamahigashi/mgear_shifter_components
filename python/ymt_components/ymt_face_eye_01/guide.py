# pylint: disable=import-error,W0201,C0111,C0112
from functools import partial
from maya import cmds

from mgear.shifter.component import guide
from mgear.core import pyqt
from mgear.core import string
from mgear.core import dag
from mgear.vendor.Qt import QtWidgets, QtCore
from mgear import shifter
from mgear.core import (
    transform,
    vector
)
from mgear.core.primitive import addTransform


from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui

try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm

try:
    from mgear.pymaya import datatypes
except ImportError:
    from pymel.core import datatypes

from . import chain_guide_initializer

# guide info
AUTHOR = "yamahigashi"
EMAIL = "yamahigashi@gmail.com"
URL = "github.com/yamahigashi"
VERSION = [1, 0, 0]
TYPE = "ymt_face_eye_01"
NAME = "eye"
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

    connectors = ["pupil_01"]

    def postInit(self):
        """Initialize the position for the guide"""

        self.save_transform = ["root", "eyeballPivot", "eyelidPivot", "#_uploc", "#_lowloc", "inloc", "outloc", "uploc", "lowloc", "front"]
        self.save_blade = ["blade"]
        self.addMinMax("#_uploc", 1, -1)
        self.addMinMax("#_lowloc", 1, -1)

    def postDraw(self):
        pass

    def addObjects(self):
        """Add the Guide Root, blade and locators"""

        self.root = self.addRoot()
        self.uplocs = self.addLocMulti("#_uploc", self.root)
        self.lowlocs = self.addLocMulti("#_lowloc", self.root)

        v = transform.getOffsetPosition(self.root, [-1, 0.0, 0.0])
        self.inPos = self.addLoc("inloc", self.root, v)

        v = transform.getOffsetPosition(self.root, [1., 0.0, 0.0])
        self.outPos = self.addLoc("outloc", self.root, v)

        v = transform.getOffsetPosition(self.root, [0., 1.0, 0.0])
        self.upPos = self.addLoc("uploc", self.root, v)

        v = transform.getOffsetPosition(self.root, [0., -1.0, 0.0])
        self.lowPos = self.addLoc("lowloc", self.root, v)

        centers = [self.inPos]
        centers.extend(self.uplocs)
        centers.append(self.outPos)
        self.dispcrv = self.addDispCurve("upCrv", centers)
        self.addDispCurve("upCrvRef", centers, 3)

        centers = [self.inPos]
        centers.extend(self.lowlocs)
        centers.append(self.outPos)
        self.dispcrv = self.addDispCurve("lowCrv", centers)
        self.addDispCurve("lowCrvRef", centers, 3)

        v = transform.getTranslation(self.root)
        self.eyelidPivot = self.addEyeMesh("eyelidPivot", self.root, v)
        self.eyeballPivot = self.addEyeMesh("eyeballPivot", self.root, v)

        v = transform.getOffsetPosition(self.root, [0, 0.0000001, 2.5])
        self.front = self.addLoc("front", self.root, v)
        self.blade = self.addBlade("blade", self.root, self.front)

    def addEyeMesh(self, name, parent, position=None):
        """Add a loc object to the guide.

        This mehod can initialize the object or draw it.
        Loc object is a simple null to define a position or a tranformation in
        the guide.

        Args:
            name (str): Local name of the element.
            parent (dagNode): The parent of the element.
            position (vector): The default position of the element.

        Returns:
            dagNode: The locator object.

        """
        t = transform.getTransform(self.root)
        if name not in self.tra.keys():
            t = transform.setMatrixPosition(t, position)
            self.tra[name] = t
        tra = self.tra[name]

        eyeMeshName = cmds.polySphere(
            name=self.getName(name),
            subdivisionsX=30,
            subdivisionsY=45,
            radius=0.5)[0]

        eyeMesh = pm.PyNode(eyeMeshName)
        eyeMesh.setTransformation(tra)
        pm.parent(eyeMesh, parent)

        return eyeMesh

    def addParameters(self):
        """Add the configurations settings"""

        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pNeutralPose = self.addParam("neutralpose", "bool", False)
        self.pOverrideNegate = self.addParam("overrideNegate", "bool", False)
        self.pSlidingSurface   = self.addParam("isSlidingSurface", "bool", True)
        self.pSurfaceReference = self.addParam("surfaceReference", "string", "")
        self.pParentJointIndex = self.addParam("parentJointIndex", "long", -1, None, None)
        self.pAddJoints = self.addParam("addJoints", "bool", True)

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

    def set_from_dict(self, c_dict):
        """Override for compatibility"""

        # eyelidPivot is Former known as "pivotAndSizeRef"
        eyeMeshPos = c_dict.get("pos", {}).get("pivotAndSizeRef")
        eyeMeshTra = c_dict.get("tra", {}).get("pivotAndSizeRef")
        if eyeMeshPos:
            c_dict["pos"]["eyelidPivot"] = eyeMeshPos
        if eyeMeshTra:
            c_dict["tra"]["eyelidPivot"] = eyeMeshTra

        # front is Former known as "tan"
        frontPos = c_dict.get("pos", {}).get("tan")
        frontTra = c_dict.get("tra", {}).get("tan")
        if frontPos:
            c_dict["pos"]["eyelidPivot"] = frontPos
        if frontTra:
            c_dict["tra"]["eyelidPivot"] = frontTra

        super(Guide, self).set_from_dict(c_dict)

    def setFromHierarchy(self, root):
        """For compatibility between the old guide"""

        super(Guide, self).setFromHierarchy(root)

        # eyelidPivot is Former known as "pivotAndSizeRef"
        self.eyelidPivot = dag.findChild(root, self.getName("pivotAndSizeRef"))
        if self.eyelidPivot:
            self.tra["eyelidPivot"] = transform.getTransform(self.eyelidPivot)
            self.eyelidPivot.rename(self.getName("eyelidPivot"))

        # front is Former known as "tan"
        self.front = dag.findChild(root, self.getName("tan"))
        if self.front:
            self.tra["front"] = transform.getTransform(self.front)
            self.front.rename(self.getName("front"))

        # eyeballPivot does not exist in the old guide
        node = dag.findChild(root, self.getName("eyeballPivot"))
        if not node:
            v = transform.getTranslation(self.root)
            self.eyeballPivot = self.addEyeMesh("eyeballPivot", self.root, v)


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
        self.populateCheck(self.settingsTab.overrideNegate_checkBox, "overrideNegate")
        self.populateCheck(self.settingsTab.addJoints_checkBox, "addJoints")

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
