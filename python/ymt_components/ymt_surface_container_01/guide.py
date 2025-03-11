# pylint: disable=import-error,W0201,C0111,C0112
from mgear.shifter.component import guide
from mgear.core import pyqt
from mgear.vendor.Qt import QtWidgets, QtCore  # type: ignore
from mgear.core import transform


from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm

import ymt_shifter_utility as ymt_utility

# guide info
AUTHOR = "yamahigashi"
EMAIL = "yamahigashi@gmail.com"
URL = "github.com/yamahigashi"
VERSION = [1, 0, 0]
TYPE = "ymt_surface_container_01"
NAME = "surface"
DESCRIPTION = "Container for nurbs surface"

##########################################################
# CLASS
##########################################################


DEFAULT_NURBS_SURFACE_DICT = {
    "degreeU": 3,
    "degreeV": 3,
    "patchU": 8,
    "patchV": 8,
    "localRotatePivot": [0.0, 0.0, 0.0],
    "localScalePivot": [0.0, 0.0, 0.0],
    "rotate": [0.0, 0.0, 0.0],
    "scale": [1.0, 1.0, 1.0],
    "translate": [0.0, 0.0, 0.0],
    "controlVertices": {
        "cv[0][0]": (-3.8764117591170804, -4.845707090643011, -2.4043301149835),
        "cv[0][1]": (-4.578653695806078, -4.368165453088264, -2.4043301149835),
        "cv[0][2]": (-5.279762682862577, -3.729085695837711, -2.4043301149835),
        "cv[0][3]": (-6.190636223340407, -2.5664316648070518, -2.4043301149835),
        "cv[0][4]": (-7.068077337521133, -0.6913147232855832, -2.4043301149835),
        "cv[0][5]": (-7.473218037782605, 0.47244806128087424, -2.4043301149835),
        "cv[0][6]": (-7.796248719768645, 2.099082780951517, -2.4043301149835),
        "cv[0][7]": (-7.83988603887825, 4.990406903084048, -2.4043301149835),
        "cv[0][8]": (-7.776668025668137, 7.163878790093229, -2.4043301149835),
        "cv[0][9]": (-7.158293280666546, 8.8535928515621, -2.346114575606874),
        "cv[0][10]": (-6.249000000000002, 10.203307677065267, -2.4043301149835),
        "cv[1][0]": (-3.355407570366424, -5.415328960329075, -1.9420955138139122),
        "cv[1][1]": (-5.4542798480177055, -4.154954905203383, -1.1837406864317426),
        "cv[1][2]": (-5.187387615224929, -4.597621383109187, -0.0744443992141055),
        "cv[1][3]": (-6.456205978549349, -2.929208497639839, -0.4617249199328138),
        "cv[1][4]": (-6.982860048082144, -1.2252652033820193, 0.16202828407501788),
        "cv[1][5]": (-7.518667136211985, 0.17857911168449125, 0.17389087072931075),
        "cv[1][6]": (-7.9409239804476295, 1.9852958714566669, 0.1807362004858527),
        "cv[1][7]": (-8.237786605017, 4.870022118560473, 0.04580086604194944),
        "cv[1][8]": (-7.722744674670805, 7.051085518480287, -0.17640080841985828),
        "cv[1][9]": (-7.046251910977262, 9.279682477250057, -0.42281349075163277),
        "cv[1][10]": (-6.107020826294718, 10.489544257415321, -0.5786635775192681),
        "cv[2][0]": (-3.001055386059739, -5.794616911306775, -1.5659812102505724),
        "cv[2][1]": (-3.545909221017565, -5.936555565555292, -0.3558140068347876),
        "cv[2][2]": (-4.6547712955238705, -4.825390279356327, 0.841016624357421),
        "cv[2][3]": (-5.611935397667425, -3.7118269638757404, 1.6526251523327642),
        "cv[2][4]": (-6.649269439827862, -1.8244628619618835, 2.275178725336923),
        "cv[2][5]": (-7.021499850043355, -0.34751744844754884, 2.5102929658018414),
        "cv[2][6]": (-7.13467140489314, 1.6321894184690229, 2.5469104322034313),
        "cv[2][7]": (-7.114836449421, 4.715634395720804, 2.4783563715544346),
        "cv[2][8]": (-7.643709053540295, 7.035038342221543, 2.307561164398866),
        "cv[2][9]": (-6.725922624189952, 9.359237694318393, 1.3898419949940921),
        "cv[2][10]": (-5.593469424410378, 10.466066192262051, 0.9455772774188378),
        "cv[3][0]": (-2.13859037845174, -6.19740019695189, -1.2268671280954333),
        "cv[3][1]": (-2.6922705052157783, -6.178733313130236, 0.025328753519111347),
        "cv[3][2]": (-3.636268829806034, -5.789894882163785, 2.479212980501247),
        "cv[3][3]": (-3.969045885291708, -4.661752977368375, 3.720393152668557),
        "cv[3][4]": (-4.4712733972762795, -2.8080154845805985, 4.612424281628126),
        "cv[3][5]": (-4.829457278864034, -0.8745448090061162, 5.008563091612502),
        "cv[3][6]": (-4.7498315248338265, 1.2012769937092116, 4.888223985603481),
        "cv[3][7]": (-5.001657305697561, 4.487292323260299, 4.785589864459405),
        "cv[3][8]": (-4.849261364050674, 6.708214196934655, 4.824157965573362),
        "cv[3][9]": (-4.609819609669222, 9.287430218080733, 4.678996095216938),
        "cv[3][10]": (-3.8274241461135574, 10.539378970748743, 3.047692121338625),
        "cv[4][0]": (-1.1199791320896957, -6.725581692887082, -0.7585797803919869),
        "cv[4][1]": (-1.4044237994797488, -6.669428268971272, 0.4340253356789081),
        "cv[4][2]": (-2.3003357039464687, -6.537432040237242, 3.470509973920564),
        "cv[4][3]": (-2.1905433681782176, -5.472379865091687, 4.626405620093146),
        "cv[4][4]": (-2.3505154055534394, -3.224613220877105, 5.556068099301574),
        "cv[4][5]": (-2.3676894961354895, -1.0727037054635535, 5.791279424898764),
        "cv[4][6]": (-2.4589817390594075, 1.0743684906743487, 5.774918829621083),
        "cv[4][7]": (-2.3738971822352726, 4.381745615828318, 5.925878572373323),
        "cv[4][8]": (-2.4039715077517627, 6.6267963610508005, 6.2324008498908645),
        "cv[4][9]": (-2.1922159104427346, 9.323993217397776, 5.659475502842283),
        "cv[4][10]": (-1.9941976179319023, 10.593927461803347, 3.679498016800446),
        "cv[5][0]": (2.220446049250313e-16, -6.979577079470997, -0.39811311509322933),
        "cv[5][1]": (2.220446049250313e-16, -6.675048181303955, 0.6687931509204266),
        "cv[5][2]": (2.220446049250313e-16, -8.064007624620803, 4.976699469948713),
        "cv[5][3]": (2.220446049250313e-16, -5.907539538272779, 5.226839002888138),
        "cv[5][4]": (2.220446049250313e-16, -3.373921974710093, 5.866918570832643),
        "cv[5][5]": (2.220446049250313e-16, -1.2176319252671057, 6.687057369000433),
        "cv[5][6]": (2.220446049250313e-16, 0.9707495632396071, 6.132349205223249),
        "cv[5][7]": (1.1102230246251565e-16, 4.377059544066832, 6.17948356164686),
        "cv[5][8]": (2.220446049250313e-16, 6.608995600016044, 6.642599398811411),
        "cv[5][9]": (2.220446049250313e-16, 9.430028197145859, 6.111093895592336),
        "cv[5][10]": (0.0, 10.627963333440938, 3.736939279515835),
        "cv[6][0]": (1.1174592422928047, -6.729784894855877, -0.7452707009175628),
        "cv[6][1]": (1.401899384432803, -6.674159443900381, 0.44649266202936744),
        "cv[6][2]": (2.2996268249973726, -6.53728683796971, 3.47311719426859),
        "cv[6][3]": (2.1905433681782176, -5.472379865091687, 4.626405620093147),
        "cv[6][4]": (2.3505154055534385, -3.224613220877103, 5.556068099301578),
        "cv[6][5]": (2.3676894961354895, -1.0727037054635538, 5.791279424898767),
        "cv[6][6]": (2.4589817390594066, 1.0743684906743491, 5.77491882962108),
        "cv[6][7]": (2.3738971822352717, 4.3817456158283195, 5.9258785723733265),
        "cv[6][8]": (2.403971507751762, 6.626796361050799, 6.232400849890865),
        "cv[6][9]": (2.1922159104427363, 9.323993217397774, 5.659475502842283),
        "cv[6][10]": (1.9768894834844504, 10.59889522561524, 3.659061476235288),
        "cv[7][0]": (2.1354590972830243, -6.198712239503162, -1.2105836373216752),
        "cv[7][1]": (2.6895120717391308, -6.179440010983597, 0.04055350818350234),
        "cv[7][2]": (3.6332343655099884, -5.792954091276105, 2.49118801330851),
        "cv[7][3]": (3.9690458852917088, -4.6617529773683755, 3.720393152668554),
        "cv[7][4]": (4.4712733972762795, -2.8080154845805954, 4.612424281628133),
        "cv[7][5]": (4.829457278864032, -0.8745448090061153, 5.0085630916125075),
        "cv[7][6]": (4.7498315248338265, 1.2012769937092136, 4.8882239856034895),
        "cv[7][7]": (5.001657305697563, 4.4872923232602995, 4.785589864459405),
        "cv[7][8]": (4.849261364050674, 6.708214196934655, 4.824157965573362),
        "cv[7][9]": (4.609819609669222, 9.28743021808073, 4.678996095216942),
        "cv[7][10]": (3.8274241461135565, 10.539378970748743, 3.0476921213386268),
        "cv[8][0]": (2.997611902923148, -5.798389151321014, -1.547297035941054),
        "cv[8][1]": (3.541796497845656, -5.943994978107896, -0.33131421516920867),
        "cv[8][2]": (4.652545445371864, -4.82592715602046, 0.8409840664817096),
        "cv[8][3]": (5.611935397667425, -3.7118269638757377, 1.6526251523327637),
        "cv[8][4]": (6.649269439827862, -1.8244628619618837, 2.2751787253369193),
        "cv[8][5]": (7.021499850043357, -0.34751744844754806, 2.5102929658018436),
        "cv[8][6]": (7.134671404893142, 1.6321894184690209, 2.5469104322034264),
        "cv[8][7]": (7.114836449421002, 4.715634395720803, 2.478356371554433),
        "cv[8][8]": (7.643709053540295, 7.035038342221542, 2.3075611643988645),
        "cv[8][9]": (6.725922624189952, 9.35923769431839, 1.3898419949940908),
        "cv[8][10]": (5.565469424410379, 10.46606619226205, 0.9455772774188347),
        "cv[9][0]": (3.35185299088125, -5.418445976680785, -1.9420955138139122),
        "cv[9][1]": (5.4542798480177055, -4.154954905203382, -1.1837406864317421),
        "cv[9][2]": (5.187387615224929, -4.597621383109214, -0.07444439921411106),
        "cv[9][3]": (6.456205978549345, -2.929208497639838, -0.4617249199328173),
        "cv[9][4]": (6.982860048082142, -1.2252652033820215, 0.16202828407501293),
        "cv[9][5]": (7.518667136211986, 0.17857911168449114, 0.17389087072930726),
        "cv[9][6]": (7.940923980447631, 1.98529587145667, 0.1807362004858486),
        "cv[9][7]": (8.237786605017, 4.87002211856047, 0.045800866041947774),
        "cv[9][8]": (7.722744674670805, 7.051085518480285, -0.17640080841985628),
        "cv[9][9]": (7.046251910977264, 9.279682477250056, -0.4228134907516343),
        "cv[9][10]": (6.107020826294718, 10.489544257415321, -0.5786635775192681),
        "cv[10][0]": (3.8544791154176368, -4.836567497003668, -2.4043301149835),
        "cv[10][1]": (4.52659276483123, -4.358127973696003, -2.4043301149835),
        "cv[10][2]": (5.218065926275139, -3.7204556323465705, -2.4043301149835),
        "cv[10][3]": (6.114559196121904, -2.576538363621035, -2.4043301149835),
        "cv[10][4]": (6.984695328834407, -0.6993732635877287, -2.4043301149835),
        "cv[10][5]": (7.405421898646583, 0.5213238680847947, -2.4043301149835),
        "cv[10][6]": (7.721560048522409, 2.0930031129518616, -2.4043301149835),
        "cv[10][7]": (7.763443500959497, 5.003746425168381, -2.4043301149835),
        "cv[10][8]": (7.776668025668137, 7.163878790093229, -2.4043301149835),
        "cv[10][9]": (7.158293280666546, 8.853592851562098, -2.346114575606874),
        "cv[10][10]": (6.249000000000002, 10.203307677065265, -2.4043301149835)
    }
}


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

        sliding_surface = pm.PyNode(ymt_utility.deserialize_nurbs_surface(
                self.getName("sliding_surface"),
                str(DEFAULT_NURBS_SURFACE_DICT)
        ))

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
class settingsTab(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(settingsTab, self).__init__(parent)


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
        pass

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):
        pass

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
