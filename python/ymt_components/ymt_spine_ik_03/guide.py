from functools import partial

from mgear.shifter.component import guide
from mgear.core import pyqt
from mgear.core import transform
from mgear.core import string
from mgear.vendor.Qt import QtWidgets, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

import pymel.core as pm
from pymel.core import datatypes
from mgear import shifter

from . import settingsUI as sui
from . import chain_guide_initializer

# guide info
AUTHOR = "yamahigashi"
EMAIL = "yamahigashi@gmail.com"
URL = "github.com/yamahigashi"
VERSION = [1, 0, 0]
TYPE = "ymt_spine_ik_03"
NAME = "spine"
DESCRIPTION = "IK chain with a spline driven joints. And variable number of \
FK controls. \nIK is master, FK Slave. With stack for IK and FK controls \n\
 WARNING: This component stack only support one level stack. This will avoid \
 complex connections and keep the component a little lighter. If the master \
 has more inputs will not move the slave of the slave. Only the direct slave"

ORIGINAL_AUTHOR = "anima inc."
ORIGINAL_URL = "www.studioanima.co.jp"
ORIGINAL_TYPE = "spine_ik_02"
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

        self.pNeutralPose = self.addParam("neutralpose", "bool", False)
        self.pOverrideNegate = self.addParam("overrideNegate", "bool", False)
        self.pfkNb = self.addParam("fkNb", "long", 3, 2)
        self.psurplusFkNb = self.addParam("surplusFkNb", "long", 3, 0)

        self.pIk0RefArray = self.addParam("ik0refarray", "string", "")
        self.pIk1RefArray = self.addParam("ik1refarray", "string", "")
        self.pSplitHip = self.addParam("isSplitHip", "bool", True)
        self.pPosition = self.addParam("position", "double", 0, 0, 1)
        self.pMaxStretch = self.addParam("maxstretch", "double", 1, 1)
        self.pMaxSquash = self.addParam("maxsquash", "double", 1, 0, 1)
        self.pSoftness = self.addParam("softness", "double", 0, 0, 1)
        self.pIsGlobalMaster = self.addParam("addJoints", "bool", True)
        self.pAddJoints = self.addParam("isGlobalMaster", "bool", False)
        self.pBoundFk = self.addParam("isBoundFkToCurve", "bool", True)
        self.pMasterChain = self.addParam("masterChainLocal", "string", "")
        self.pMasterChain = self.addParam("masterChainGlobal", "string", "")
        self.pCnxOffset = self.addParam("cnxOffset", "long", 0, 0)
        # FCurves
        self.pSt_profile = self.addFCurveParam(
            "st_profile", [[0, 0], [.5, -1], [1, 0]])

        self.pSq_profile = self.addFCurveParam(
            "sq_profile", [[0, 0], [.5, 1], [1, 0]])

        self.pIk_profile = self.addFCurveParam(
            "ik_profile", [[0, 0], [.5, .5], [1, 1]])

        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam(
            "parentJointIndex", "long", -1, None, None)

    def get_divisions(self):
        """ Returns correct segments divisions """

        self.divisions = self.root.fkNb.get()

        return self.divisions

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
        return

    def populate_componentControls(self):
        """Populate Controls

        Populate the controls values from the custom attributes of the
        component.

        """
        # populate tab
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")

        # populate component settings
        self.populateCheck(self.settingsTab.overrideNegate_checkBox,
                           "overrideNegate")

        ik0RefArrayItems = self.root.attr("ik0refarray").get().split(",")
        for item in ik0RefArrayItems:
            self.settingsTab.ik0RefArray_listWidget.addItem(item)

        ik1RefArrayItems = self.root.attr("ik1refarray").get().split(",")
        for item in ik1RefArrayItems:
            self.settingsTab.ik1RefArray_listWidget.addItem(item)

        self.settingsTab.fkNb_spinBox.setValue(
            self.root.attr("fkNb").get())
        self.settingsTab.surplusFkNb_spinBox.setValue(
            self.root.attr("surplusFkNb").get())

        self.settingsTab.softness_slider.setValue(
            int(self.root.attr("softness").get() * 100))
        self.settingsTab.position_spinBox.setValue(
            int(self.root.attr("position").get() * 100))
        self.settingsTab.position_slider.setValue(
            int(self.root.attr("position").get() * 100))
        self.settingsTab.softness_spinBox.setValue(
            int(self.root.attr("softness").get() * 100))

        self.settingsTab.maxStretch_spinBox.setValue(
            self.root.attr("maxstretch").get())
        self.settingsTab.maxSquash_spinBox.setValue(
            self.root.attr("maxsquash").get())

        self.populateCheck(self.settingsTab.addJoints_checkBox,
                           "addJoints")
        self.populateCheck(self.settingsTab.isSplitHip_checkBox,
                           "isSplitHip")

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
        self.settingsTab.fkNb_spinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.fkNb_spinBox,
                    "fkNb"))
        # surplusFbNb_spinBox
        self.settingsTab.surplusFkNb_spinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.surplusFkNb_spinBox,
                    "surplusFkNb"))

        self.settingsTab.ik0RefArrayAdd_pushButton.clicked.connect(
            partial(self.addItem2listWidget,
                    self.settingsTab.ik0RefArray_listWidget,
                    "ik0refarray"))
        self.settingsTab.ik0RefArrayRemove_pushButton.clicked.connect(
            partial(self.removeSelectedFromListWidget,
                    self.settingsTab.ik0RefArray_listWidget,
                    "ik0refarray"))

        self.settingsTab.ik1RefArrayAdd_pushButton.clicked.connect(
            partial(self.addItem2listWidget,
                    self.settingsTab.ik1RefArray_listWidget,
                    "ik1refarray"))
        self.settingsTab.ik1RefArrayRemove_pushButton.clicked.connect(
            partial(self.removeSelectedFromListWidget,
                    self.settingsTab.ik1RefArray_listWidget,
                    "ik1refarray"))

        self.settingsTab.softness_slider.valueChanged.connect(
            partial(self.updateSlider,
                    self.settingsTab.softness_slider,
                    "softness"))
        self.settingsTab.softness_spinBox.valueChanged.connect(
            partial(self.updateSlider,
                    self.settingsTab.softness_spinBox,
                    "softness"))
        self.settingsTab.position_slider.valueChanged.connect(
            partial(self.updateSlider,
                    self.settingsTab.position_slider,
                    "position"))
        self.settingsTab.position_spinBox.valueChanged.connect(
            partial(self.updateSlider,
                    self.settingsTab.position_spinBox,
                    "position"))
        self.settingsTab.maxStretch_spinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.maxStretch_spinBox,
                    "maxstretch"))
        self.settingsTab.maxSquash_spinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.maxSquash_spinBox,
                    "maxsquash"))

        self.settingsTab.addJoints_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.addJoints_checkBox,
                    "addJoints"))

        self.settingsTab.isSplitHip_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.isSplitHip_checkBox,
                    "isSplitHip"))

        self.settingsTab.ikProfile_pushButton.clicked.connect(
            self.setProfile)

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


if __name__ == "__main__":
    import ymt_spine_ik_01.guide as g
    reload(g)
