# pylint: disable=import-error,W0201,C0111,C0112
from functools import partial

from mgear.shifter.component import guide
from mgear.core import pyqt
from mgear.core import string
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

import settingsUI as sui
import pymel.core as pm
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

    def postInit(self):
        """Initialize the position for the guide"""

        self.save_transform = ["root", "#_uploc", "#_lowloc", "inloc", "outloc", "uploc", "lowloc", "tan"]
        self.save_blade = ["blade"]
        self.addMinMax("#_uploc", 1, -1)
        self.addMinMax("#_lowloc", 1, -1)

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
        self.dispcrv = self.addDispCurve("crv", centers)
        self.addDispCurve("crvRef", centers, 3)

        centers = [self.inPos]
        centers.extend(self.lowlocs)
        centers.append(self.outPos)
        self.dispcrv = self.addDispCurve("crv", centers)
        self.addDispCurve("crvRef", centers, 3)

        v = transform.getTranslation(self.root)
        self.eyeMesh = pm.polySphere(
            name=self.getName("eyeMesh"),
            subdivisionsX=30,
            subdivisionsY=45,
            radius=0.5)[0]
        pm.parent(self.eyeMesh, self.root)

        v = transform.getOffsetPosition(self.root, [0, 0.0000001, 2.5])
        self.tan = self.addLoc("tan", self.root, v)
        self.blade = self.addBlade("blade", self.eyeMesh, self.tan)

    def addParameters(self):
        """Add the configurations settings"""

        self.pNeutralPose = self.addParam("neutralpose", "bool", False)
        self.pOverrideNegate = self.addParam("overrideNegate", "bool", False)
        self.pikNb = self.addParam("ikNb", "long", 3, 2)

        self.pIk0RefArray = self.addParam("ik0refarray", "string", "")
        self.pIk1RefArray = self.addParam("ik1refarray", "string", "")
        self.pSplitHip = self.addParam("isPlanetaryIkBindToGlobal", "bool", True)
        self.pAimTip = self.addParam("isUpvectorAimToTip", "bool", False)
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

        self.divisions = self.root.ikNb.get()

        return self.divisions

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
        self.populateCheck(self.settingsTab.overrideNegate_checkBox,
                           "overrideNegate")

        ik0RefArrayItems = self.root.attr("ik0refarray").get().split(",")
        for item in ik0RefArrayItems:
            self.settingsTab.ik0RefArray_listWidget.addItem(item)

        ik1RefArrayItems = self.root.attr("ik1refarray").get().split(",")
        for item in ik1RefArrayItems:
            self.settingsTab.ik1RefArray_listWidget.addItem(item)

        self.settingsTab.ikNb_spinBox.setValue(
            self.root.attr("ikNb").get())
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
        self.populateCheck(self.settingsTab.isGlobalMaster_checkBox,
                           "isGlobalMaster")
        self.populateCheck(self.settingsTab.isBoundFkToCurve_checkBox,
                           "isBoundFkToCurve")
        self.populateCheck(self.settingsTab.isPlanetaryIkBindToGlobal_checkBox,
                           "isPlanetaryIkBindToGlobal")
        self.populateCheck(self.settingsTab.isUpvectorAimToTip_checkBox,
                           "isUpvectorAimToTip")
        self.settingsTab.masterLocal_lineEdit.setText(
            self.root.attr("masterChainLocal").get())
        self.settingsTab.masterGlobal_lineEdit.setText(
            self.root.attr("masterChainGlobal").get())
        self.settingsTab.cnxOffset_spinBox.setValue(
            self.root.attr("cnxOffset").get())

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
        self.settingsTab.ikNb_spinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.ikNb_spinBox,
                    "ikNb"))

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

        self.settingsTab.masterLocal_pushButton.clicked.connect(
            partial(self.updateMasterChain,
                    self.settingsTab.masterLocal_lineEdit,
                    "masterChainLocal"))

        self.settingsTab.masterGlobal_pushButton.clicked.connect(
            partial(self.updateMasterChain,
                    self.settingsTab.masterGlobal_lineEdit,
                    "masterChainGlobal"))

        self.settingsTab.cnxOffset_spinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.cnxOffset_spinBox,
                    "cnxOffset"))

        self.settingsTab.isGlobalMaster_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.isGlobalMaster_checkBox,
                    "isGlobalMaster"))

        self.settingsTab.isBoundFkToCurve_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.isBoundFkToCurve_checkBox,
                    "isBoundFkToCurve"))

        self.settingsTab.isPlanetaryIkBindToGlobal_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.isPlanetaryIkBindToGlobal_checkBox,
                    "isPlanetaryIkBindToGlobal"))

        self.settingsTab.isUpvectorAimToTip_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.isUpvectorAimToTip_checkBox,
                    "isUpvectorAimToTip"))

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
