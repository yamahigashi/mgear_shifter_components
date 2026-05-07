"""Guide for ymt_birdwing_3jnt_01."""

from functools import partial

from maya import cmds

try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm

from maya.app.general.mayaMixin import MayaQDockWidget, MayaQWidgetDockableMixin
from mgear.core import attribute, pyqt, transform
from mgear.shifter.component import guide
from mgear.vendor.Qt import QtCore, QtWidgets

from . import settingsUI as sui


AUTHOR = "yamahigashi"
URL = "yamahigashi.dev"
EMAIL = "yamahigashi@gmail.com"
VERSION = [1, 0, 0]
TYPE = "ymt_birdwing_3jnt_01"
NAME = "wing"
DESCRIPTION = "Three-section bird/dragon wing with layered 2-bone and hand look-at IK."


class Guide(guide.ComponentGuide):
    """Component guide class."""

    compType = TYPE
    compName = NAME
    description = DESCRIPTION

    author = AUTHOR
    url = URL
    email = EMAIL
    version = VERSION

    connectors = ["ymt_shoulder_01"]

    def postInit(self):
        self.save_transform = ["root", "elbow", "wrist", "eff", "upv"]
        self.save_blade = ["blade"]

    def addObjects(self):
        self.root = self.addRoot()
        elbow_pos = transform.getOffsetPosition(self.root, [3, 0, -0.2])
        self.elbow = self.addLoc("elbow", self.root, elbow_pos)
        wrist_pos = transform.getOffsetPosition(self.root, [6, 0, 0])
        self.wrist = self.addLoc("wrist", self.elbow, wrist_pos)
        eff_pos = transform.getOffsetPosition(self.root, [7.5, 0, 0.6])
        self.eff = self.addLoc("eff", self.wrist, eff_pos)
        self.blade = self.addBlade("blade", self.root, self.elbow)
        cmds.setAttr(self.blade + ".bladeRollOffset", -90.0)
        attribute.unlockAttribute(self.blade, ["rx"])
        upv_pos = transform.getOffsetPosition(self.root, [3, 0, 3])
        self.upv = self.addLoc("upv", self.root, upv_pos)
        self.dispcrv = self.addDispCurve("crv", [self.root, self.elbow, self.wrist, self.eff])

    def addParameters(self):
        self.pBlend = self.addParam("blend", "double", 1, 0, 1)
        self.pIkRefArray = self.addParam("ikrefarray", "string", "")
        self.pUpvRefArray = self.addParam("upvrefarray", "string", "")
        self.pIKSolver = self.addEnumParam("ikSolver", ["IK Spring", "IK Rotation Plane"], 0)
        self.pIKOrient = self.addParam("ikOri", "bool", True)

        self.pDiv0 = self.addParam("div0", "long", 2, 0, None)
        self.pDiv1 = self.addParam("div1", "long", 2, 0, None)
        self.pDiv2 = self.addParam("div2", "long", 2, 0, None)

        self.pSt_profile = self.addFCurveParam(
            "st_profile", [[0, 0], [0.33, -1], [0.66, -1], [1, 0]]
        )
        self.pSq_profile = self.addFCurveParam(
            "sq_profile", [[0, 0], [0.33, 1], [0.66, 1], [1, 0]]
        )

        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam("parentJointIndex", "long", -1, None, None)

    def get_divisions(self):
        self.divisions = self.root.div0.get() + self.root.div1.get() + self.root.div2.get()
        return self.divisions


class settingsTab(QtWidgets.QDialog, sui.Ui_Form):
    """The component settings UI."""

    def __init__(self, parent=None):
        super(settingsTab, self).__init__(parent)
        self.setupUi(self)


class componentSettings(MayaQWidgetDockableMixin, guide.componentMainSettings):
    """Create the component setting window."""

    def __init__(self, parent=None):
        self.toolName = TYPE
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
        self.resize(280, 620)

    def create_componentControls(self):
        return

    def populate_componentControls(self):
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")
        self.settingsTab.ikfk_slider.setValue(int(self.root.attr("blend").get() * 100))
        self.settingsTab.ikfk_spinBox.setValue(int(self.root.attr("blend").get() * 100))
        self.settingsTab.ikSolver_comboBox.setCurrentIndex(self.root.attr("ikSolver").get())
        self.populateCheck(self.settingsTab.neutralRotation_checkBox, "ikOri")
        self.settingsTab.div0_spinBox.setValue(self.root.attr("div0").get())
        self.settingsTab.div1_spinBox.setValue(self.root.attr("div1").get())
        self.settingsTab.div2_spinBox.setValue(self.root.attr("div2").get())

        for item in self.root.attr("ikrefarray").get().split(","):
            self.settingsTab.ikRefArray_listWidget.addItem(item)
        for item in self.root.attr("upvrefarray").get().split(","):
            self.settingsTab.upvRefArray_listWidget.addItem(item)

        self.c_box = self.mainSettingsTab.connector_comboBox
        for cnx in Guide.connectors:
            self.c_box.addItem(cnx)
        self.connector_items = [self.c_box.itemText(i) for i in range(self.c_box.count())]

        current_connector = self.root.attr("connector").get()
        if current_connector not in self.connector_items:
            self.c_box.addItem(current_connector)
            self.connector_items.append(current_connector)
            pm.displayWarning(
                "The current connector: %s, is not a valid connector for this component. Build will Fail!!"
                % current_connector
            )
        self.c_box.setCurrentIndex(self.connector_items.index(current_connector))

    def create_componentLayout(self):
        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)
        self.setLayout(self.settings_layout)

    def create_componentConnections(self):
        self.settingsTab.ikfk_slider.valueChanged.connect(
            partial(self.updateSlider, self.settingsTab.ikfk_slider, "blend")
        )
        self.settingsTab.ikfk_spinBox.valueChanged.connect(
            partial(self.updateSlider, self.settingsTab.ikfk_spinBox, "blend")
        )
        self.settingsTab.ikSolver_comboBox.currentIndexChanged.connect(
            partial(self.updateComboBox, self.settingsTab.ikSolver_comboBox, "ikSolver")
        )
        self.settingsTab.neutralRotation_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.neutralRotation_checkBox, "ikOri")
        )
        self.settingsTab.div0_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.div0_spinBox, "div0")
        )
        self.settingsTab.div1_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.div1_spinBox, "div1")
        )
        self.settingsTab.div2_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.div2_spinBox, "div2")
        )
        self.settingsTab.squashStretchProfile_pushButton.clicked.connect(self.setProfile)

        self.settingsTab.ikRefArrayAdd_pushButton.clicked.connect(
            partial(self.addItem2listWidget, self.settingsTab.ikRefArray_listWidget, "ikrefarray")
        )
        self.settingsTab.ikRefArrayRemove_pushButton.clicked.connect(
            partial(self.removeSelectedFromListWidget, self.settingsTab.ikRefArray_listWidget, "ikrefarray")
        )
        self.settingsTab.ikRefArray_copyRef_pushButton.clicked.connect(
            partial(
                self.copyFromListWidget,
                self.settingsTab.upvRefArray_listWidget,
                self.settingsTab.ikRefArray_listWidget,
                "ikrefarray",
            )
        )
        self.settingsTab.ikRefArray_listWidget.installEventFilter(self)

        self.settingsTab.upvRefArrayAdd_pushButton.clicked.connect(
            partial(self.addItem2listWidget, self.settingsTab.upvRefArray_listWidget, "upvrefarray")
        )
        self.settingsTab.upvRefArrayRemove_pushButton.clicked.connect(
            partial(self.removeSelectedFromListWidget, self.settingsTab.upvRefArray_listWidget, "upvrefarray")
        )
        self.settingsTab.upvRefArray_copyRef_pushButton.clicked.connect(
            partial(
                self.copyFromListWidget,
                self.settingsTab.ikRefArray_listWidget,
                self.settingsTab.upvRefArray_listWidget,
                "upvrefarray",
            )
        )
        self.settingsTab.upvRefArray_listWidget.installEventFilter(self)

        self.mainSettingsTab.connector_comboBox.currentIndexChanged.connect(
            partial(self.updateConnector, self.mainSettingsTab.connector_comboBox, self.connector_items)
        )

    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.settingsTab.ikRefArray_listWidget:
                self.updateListAttr(sender, "ikrefarray")
            elif sender == self.settingsTab.upvRefArray_listWidget:
                self.updateListAttr(sender, "upvrefarray")
            return True
        return QtWidgets.QDialog.eventFilter(self, sender, event)

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
