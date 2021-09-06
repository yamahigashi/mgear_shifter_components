#############################################
# GLOBAL
#############################################
from functools import partial

# mgear
from mgear.shifter.component.guide import ComponentGuide
import mgear.core.transform as tra
import mgear.core.vector as vec

# Pyside
from mgear.shifter.component.guide import componentMainSettings
import mgear.core.pyqt as gqt
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget
from . import settingsUI as sui
QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()


# guide info
AUTHOR = "Jeremie Passerin, Miquel Campos, Takayoshi Matsumoto"
URL = "www.jeremiepasserin.com, www.miquletd.com, github.com/yamahigashi"
EMAIL = "geerem@hotmail.com, hello@miquel-campos.com, yamahigashi@gmail.com"
VERSION = [0, 0, 1]
TYPE = "ymt_neck_ik_01"
NAME = "neck"
DESCRIPTION = ""


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
        self.save_transform = ["root", "tan0", "eff0", "neck", "head", "eff1"]
        self.save_blade = ["blade"]

    # =====================================================
    #  Add more object to the object definition list.
    # @param self
    def addObjects(self):

        self.root = self.addRoot()
        vTemp = tra.getOffsetPosition(self.root, [0, 1, 0])
        self.neck = self.addLoc("neck", self.root, vTemp)
        # v1 = vec.linearlyInterpolate(self.root.getTranslation(space="world"), self.neck.getTranslation(space="world"), .666)
        v1 = tra.getOffsetPosition(self.root, [0, 1.5, 0])
        self.eff0 = self.addLoc("eff0", self.neck, v1)

        vTemp = tra.getOffsetPosition(self.root, [0, 1.5, 0])
        self.head = self.addLoc("head", self.neck, vTemp)

        vTemp = tra.getOffsetPosition(self.root, [0, 2, 0])
        self.eff1 = self.addLoc("eff1", self.head, vTemp)

        v0 = tra.getOffsetPosition(self.root, [0, 1, 0.0001])
        self.tan0 = self.addLoc("tan0", self.root, v0)

        self.blade = self.addBlade("blade", self.root, self.tan0)

        centers = [self.root, self.neck, self.head]
        self.dispcrv = self.addDispCurve("neck_crv", centers, 3)

        centers = [self.neck, self.eff0]
        self.dispcrv = self.addDispCurve("neck_crv", centers, 1)

        centers = [self.head, self.eff1]
        self.dispcrv = self.addDispCurve("head_crv", centers, 1)

    # =====================================================
    # Add more parameter to the parameter definition list.
    # @param self
    def addParameters(self):

        self.pHeadRefArray = self.addParam("headrefarray", "string", "")
        self.pUseExprespy = self.addParam("useExprespy", "bool", False)

        # Default values
        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam("parentJointIndex", "long", -1, None, None)


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
        self.resize(280, 620)

    def create_componentControls(self):
        return

    def populate_componentControls(self):
        """
        Populate the controls values from the custom attributes of the component.

        """
        # populate tab
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")

        # populate component settings
        headRefArrayItems = self.root.attr("headrefarray").get().split(",")
        for item in headRefArrayItems:
            self.settingsTab.headRefArray_listWidget.addItem(item)

        self.populateCheck(self.settingsTab.useExprespy_checkBox, "useExprespy")

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):

        self.settingsTab.headRefArrayAdd_pushButton.clicked.connect(partial(self.addItem2listWidget, self.settingsTab.headRefArray_listWidget, "headrefarray"))
        self.settingsTab.headRefArrayRemove_pushButton.clicked.connect(partial(self.removeSelectedFromListWidget, self.settingsTab.headRefArray_listWidget, "headrefarray"))
        self.settingsTab.headRefArray_listWidget.installEventFilter(self)

        self.settingsTab.useExprespy_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.useExprespy_checkBox,
                    "useExprespy"))

    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.settingsTab.headRefArray_listWidget:
                self.updateListAttr(sender, "headrefarray")

    def dockCloseEventTriggered(self):
        gqt.deleteInstances(self, MayaQDockWidget)
