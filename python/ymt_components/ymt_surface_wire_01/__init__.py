"""mGear shifter components"""
# pylint: disable=import-error,W0201,C0111,C0112
import sys
import maya.cmds as cmds
# import maya.OpenMaya as om1
import maya.api.OpenMaya as om

import pymel.core as pm
from pymel.core import datatypes

from mgear.shifter import component

from mgear.core import (
    transform,
    # curve,
    # applyop,
    # attribute,
    # icon,
    # fcurve,
    # vector,
    # meshNavigation,
    node,
    primitive,
    # utils,
)
from mgear.rigbits import ghost

from mgear.core.transform import (
    getTransform,
    # resetTransform,
    # getTransformLookingAt,
    # getChainTransform2,
    # setMatrixPosition,
)

from mgear.core.primitive import (
    addTransform,
)

import ymt_shifter_utility as ymt_util
import ymt_shifter_utility.curve as curve

if sys.version_info > (3, 0):
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from typing import (
            Optional,  # noqa: F401
            Dict,  # noqa: F401
            List,  # noqa: F401
            Tuple,  # noqa: F401
            Pattern,  # noqa: F401
            Callable,  # noqa: F401
            Any,  # noqa: F401
            Text,  # noqa: F401
            Generator,  # noqa: F401
            Union  # noqa: F401
        )

from logging import (  # noqa:F401 pylint: disable=unused-import, wrong-import-order
    StreamHandler,
    getLogger,
    WARN,
    DEBUG,
    INFO
)

handler = StreamHandler()
handler.setLevel(DEBUG)
logger = getLogger(__name__)
logger.setLevel(INFO)
logger.addHandler(handler)
logger.propagate = False


##########################################################
# COMPONENT
##########################################################
class Component(component.Main):
    """Shifter component Class"""

    # =====================================================
    # OBJECTS
    # =====================================================
    def addObjects(self):
        """Add all the objects needed to create the component."""

        self.WIP = self.options["mode"]

        if self.negate and self.settings["overrideNegate"]:
            self.negate = False
            self.n_factor = 1

        if self.settings["overrideNegate"]:
            self.mirror_conf = [0, 0, 1,
                                1, 1, 0,
                                0, 0, 0]
        else:
            self.mirror_conf = [0, 0, 0,
                                0, 0, 0,
                                0, 0, 0]

        # -------------------------------------------------------
        self.ctlName = "ctl"
        self.detailControllersGroupName = "controllers_detail"  # TODO: extract to settings
        self.primaryControllersGroupName = "controllers_primary"  # TODO: extract to settings
        self.connect_surface_slider = self.settings["isSlidingSurface"]
        self.surfaceKeyable = self.settings["surfaceKeyable"]
        self.sourceKeyable = self.settings["sourceKeyable"]
        # --------------------------------------------------------
        self.num_ctrls = len(self.guide.atra) - 2
        self.ik_ctl = []
        self.ik_npo = []

        self.float_ctls = []
        self.float_npos = []
        self.ghost_npos = []
        self.ghost_ctls = []

        # --------------------------------------------------------
        self.previusTag = self.parentCtlTag

        t = getTransform(self.root)
        self.slider_root = addTransform(self.root, self.getName("sliders"), t)
        self.ctl_root = addTransform(self.root, self.getName("ctls"), t)
        self.crv_root = addTransform(self.root, self.getName("crv_root"), t)

        self.addControllers()
        # self.addWire()

        self.surfRef = self.settings["surfaceReference"]
        if not self.surfRef:
            self.sliding_surface = pm.duplicate(self.guide.getObjects(self.guide.root)["sliding_surface"])[0]
            pm.parent(self.sliding_surface.name(), self.root)
            self.sliding_surface.visibility.set(False)
            pm.makeIdentity(self.sliding_surface, apply=True, t=1,  r=1, s=1, n=0, pn=1)  # type: ignore

        if self.connect_surface_slider:
            ymt_util.setKeyableAttributesDontLockVisibility(self.slider_root, [])

    def addControllers(self):

        self.dummyCurve = curve.addCurve(
            self.crv_root,
            self.getName("dummy"),
            self.guide.apos[1:-1],
            close=False,
            degree=3,
        )

        count = self.settings["numberOfControllers"]
        for index in range(count):
            if index == 0:
                ratio = 0
            else:
                ratio = float(index) / (count - 1)
            position = curve.getPositionByRatio(self.dummyCurve, ratio)
            t = transform.setMatrixPosition(self.guide.atra[0], position)
            npo, ctl = self.addController(index, t)
            self.float_npos.append(npo)
            self.float_ctls.append(ctl)

        cmds.delete(self.dummyCurve.fullPathName())

    def addController(self, index, t):

        if self.settings["neutralpose"]:
            if self.negate:
                scl = [-1, 1, 1]
                t = transform.setMatrixScale(t, scl)

        npo = addTransform(self.ctl_root, self.getName("{}_npo".format(index)), t)
        ctl = self.addCtl(
            npo,
            "surface_{}_ctl".format(index),
            t,
            self.color_ik,
            "square",
            ro=datatypes.Vector([1.5708, 0, 0]),
            po=datatypes.Vector([0, 0, self.size * 0.1]),
            tp=self.previusTag,
            mirrorConf=self.mirror_conf
        )

        if self.settings["addJoints"]:
            self.jnt_pos = []

        return npo, ctl

    def addWire(self, ctls):

        t = getTransform(self.root)
        copyCtls = ctls.copy()
        self.curve = curve.addCnsCurve(
            self.crv_root,
            self.getName("curve"),
            copyCtls,
            degree=3,
            close=False,
            m=t,
        )
        cmds.dgeval(self.curve.name() + ".v", self.curve.name() + ".v")
        self.target = curve.createCurveFromCurve(
            self.curve.fullPathName(),
            self.getName("curve_target"),
            nbPoints=30,
            parent=self.crv_root,
            close=False,
            space=om.MSpace.kObject,
            m=t,
        )
        self.wire = pm.wire(self.target, w=self.curve)[0]

        self.surfaceCurve = curve.createCurveOnSurfaceFromCurve(
            self.target,
            self.sliding_surface,
            self.getName("curve_on_surface")
        )

        posLocal = []
        for tra in self.guide.atra[1:-1]:
            mat = t.inverse() * tra
            posLocal.append((mat[3][0], mat[3][1], mat[3][2]))
        self.rope = curve.addCurve(
            self.crv_root,
            self.getName("rope"),
            posLocal,
            m=t,
            close=False,
            degree=3,
        )
        pa = self.rope.getPointAtParam(0, space=om.MSpace.kWorld)
        pb = self.surfaceCurve.getPointAtParam(0, space=om.MSpace.kWorld)
        dist = (pa - pb).length() * 2.0 + self.size * 3.0
        self.wire3 = pm.wire(self.rope, w=self.surfaceCurve, dropoffDistance=(0, dist))[0]

        for i, (pos, tra) in enumerate(
                zip(self.guide.apos[1:-1],
                    self.guide.atra[1:-1]
                )
        ):

            adj = addTransform(self.ctl_root, self.getName("detail{}_adj".format(str(i))), tra)
            cns = curve.applyPathConstrainLocal(adj, self.rope)
            cmds.setAttr(cns + ".worldUpType", 2)  # object rotation up
            cmds.setAttr(cns + ".worldUpVectorX", 0)
            cmds.setAttr(cns + ".worldUpVectorY", 0)
            cmds.setAttr(cns + ".worldUpVectorZ", 1)
            cmds.connectAttr(self.root.fullPathName() + ".worldMatrix", cns + ".worldUpMatrix")  # object rotation up
            cmds.setAttr(cns + ".frontAxis", 0)  # front axis y
            cmds.setAttr(cns + ".upAxis", 2)  # up axis x
            cmds.setAttr(cns + ".inverseFront", True)

            npo = addTransform(adj, self.getName("detail{}_npo".format(str(i))), tra)

            ctl = self.addCtl(
                npo,
                "detail{}_ctl".format(i),
                tra,
                self.color_fk,
                "sphere",
                ro=datatypes.Vector([1.5708, 0, 0]),
                po=datatypes.Vector([0, 0, self.size * 0.075]),
                tp=self.previusTag,
                mirrorConf=self.mirror_conf
            )
            if self.settings["addJoints"]:
                self.jnt_pos.append([ctl , str(i)])
            if self.settings["ctlGrp"]:
                ctlGrp = self.settings["ctlGrp"]
                self.addToGroup(ctl, ctlGrp, "controllers")

            else:
                ctlGrp = "controllers"
                self.addToGroup(ctl, ctlGrp)

            if ctlGrp not in self.groups.keys():
                self.groups[ctlGrp] = []


    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        pass
        # if not self.settings["ui_host"]:
        #     self.uihost = self.surfaceCtl

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        pass

    def connectRef(self, refArray, cns_obj, upVAttr=None, init_refNames=False):
        """Connect the cns_obj to a multiple object using parentConstraint.

        Args:
            refArray (list of dagNode): List of driver objects
            cns_obj (dagNode): The driven object.
            upVAttr (bool): Set if the ref Array is for IK or Up vector
        """
        if refArray:
            if upVAttr and not init_refNames:
                # we only can perform name validation if the init_refnames are
                # provided in a separated list. This check ensures backwards
                # copatibility
                ref_names = refArray.split(",")
            else:
                ref_names = self.get_valid_ref_list(refArray.split(","))

            if not ref_names:
                # return if the not ref_names list
                return
            elif len(ref_names) == 1:
                ref = self.rig.findRelative(ref_names[0])
                pm.parent(cns_obj, ref)
            else:
                ref = []
                for ref_name in ref_names:
                    ref.append(self.rig.findRelative(ref_name))

                ref.append(cns_obj)
                cns_node = pm.parentConstraint(*ref, maintainOffset=True)
                cns_attr = pm.parentConstraint(
                    cns_node, query=True, weightAliasList=True)
                # check if the ref Array is for IK or Up vector
                try:
                    if upVAttr:
                        oAttr = self.upvref_att
                    else:
                        oAttr = self.ikref_att

                except AttributeError:
                    oAttr = None

                if oAttr:
                    for i, attr in enumerate(cns_attr):
                        node_name = pm.createNode("condition")
                        pm.connectAttr(oAttr, node_name + ".firstTerm")
                        pm.setAttr(node_name + ".secondTerm", i)
                        pm.setAttr(node_name + ".operation", 0)
                        pm.setAttr(node_name + ".colorIfTrueR", 1)
                        pm.setAttr(node_name + ".colorIfFalseR", 0)
                        pm.connectAttr(node_name + ".outColorR", attr)

    def connect_standard(self):
        self.parent.addChild(self.root)
        if self.surfRef:
            ref = self.rig.findComponent(self.surfRef)
            self.sliding_surface = ref.sliding_surface

        if self.connect_surface_slider:
            try:
                self.connect_slide_ghosts()
                self.addWire(self.ghost_ctls)

            except Exception as _:
                import traceback
                traceback.print_exc()

        else:
            try:
                self.connect_rivet()

            except Exception as _:
                import traceback
                traceback.print_exc()

    def connect_slide_ghosts(self):

        for i, (_, ctl) in enumerate(zip(self.float_npos, self.float_ctls)):
            self.connect_slide_ghost(ctl, i)

    def connect_slide_ghost(self, surfaceCtl, index):

        # create ghost controls
        ghostCtl = ghost.createGhostCtl(surfaceCtl, self.slider_root)
        ghostCtl.rename(self.getName("surface_{}_ctl".format(index)))

        if self.settings.get("visHost", False):
            self._visi_off_lock(surfaceCtl)

        oParent = ghostCtl.getParent()
        npoName = "_".join(ghostCtl.name().split("_")[:-1]) + "{}_npo".format(index)
        npo = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))
        npo.addChild(ghostCtl)

        ghostCtl.attr("isCtl") // surfaceCtl.attr("isCtl")
        ghostCtl.attr("translate") // surfaceCtl.attr("translate")
        ghostCtl.attr("rotate") // surfaceCtl.attr("rotate")
        ghostCtl.attr("scale") // surfaceCtl.attr("scale")

        surfaceCtl.rename(self.getName("source_{}_ctl".format(index)))

        ctl = pm.listConnections(ghostCtl, t="transform")[-1]
        t = ctl.getMatrix(worldSpace=True)

        oParent = ghostCtl.getParent()
        npoName = "_".join(ghostCtl.name().split("_")[:-1]) + "_npo"
        npo = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))
        npo.setTransformation(ghostCtl.getMatrix())
        ymt_util.setKeyableAttributesDontLockVisibility(npo, [])

        pm.parent(ghostCtl, npo)

        slider = primitive.addTransform(
                self.sliding_surface.getParent(),
                ctl.name() + "_slideDriven",
                t)

        down, _, up = ymt_util.findPathAtoB(ctl, self.sliding_surface.getParent())
        mul_node = pm.createNode("multMatrix")
        j = k = 0
        for j, d in enumerate(down):
            d.attr("matrix") >> mul_node.attr("matrixIn[{}]".format(j))
        for k, u in enumerate(up):
            u.attr("inverseMatrix") >> mul_node.attr("matrixIn[{}]".format(k + j + 1))

        dm_node = node.createDecomposeMatrixNode(mul_node.attr("matrixSum"))

        cps_node = pm.createNode("closestPointOnSurface")
        dm_node.attr("outputTranslate") >> cps_node.attr("inPosition")
        surfaceShape = self.sliding_surface.getShape()
        surfaceShape.attr("local") >> cps_node.attr("inputSurface")
        cps_node.attr("position") >> slider.attr("translate")

        if self.negate:
            aim = [0, 0, -1]
        else:
            aim = [0, 0, 1]
        pm.normalConstraint(surfaceShape,
                            slider,
                            aimVector=aim,
                            upVector=[0, 1, 0],
                            worldUpType="objectrotation",
                            worldUpVector=[0, 1, 0],
                            worldUpObject=self.root)
        pm.parent(ghostCtl.getParent(), slider)
        self.removeFromControllerGroup(ghostCtl)

        if self.sourceKeyable:
            surfaceCtl.attr("isCtl").set(True)
        else:
            self.removeFromControllerGroup(surfaceCtl)

        # add to group
        if self.settings["ctlGrp"]:
            ctlGrp = self.settings["ctlGrp"]
            self.addToGroup(ghostCtl, ctlGrp, "controllers")
            self.addToGroup(surfaceCtl, ctlGrp, "controllers")

        else:
            ctlGrp = "controllers"
            self.addToGroup(ghostCtl, ctlGrp)
            self.addToGroup(surfaceCtl, ctlGrp)

        if ctlGrp not in self.groups.keys():
            self.groups[ctlGrp] = []

        self.setRelation()  # MUST re-setRelation, swapped ghost and real controls
        self.ghost_npos.append(npo)
        self.ghost_ctls.append(ghostCtl)

    def connect_rivet(self):
        rivets = ymt_util.apply_rivet_constrain_to_selected(self.sliding_surface, self.npo)
        cmds.parent(rivets[0], self.sliding_surface.getParent().fullPath(), relative=True)
        cmds.parentConstraint(rivets[0], self.npo.fullPath(), mo=True)

    # =====================================================
    # CONNECTOR
    # =====================================================
    def addConnection(self):
        self.connections["standard"] = self.connect_standard

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.root
        # self.relatives["ctl"] = self.surfaceCtl

    # =====================================================
    # UTILITY
    # =====================================================
    def _visi_off_lock(self, node):
        """Short cuts."""
        node.visibility.set(False)
        ymt_util.setKeyableAttributesDontLockVisibility(node, [])
        cmds.setAttr("{}.visibility".format(node.name()), l=False)

    def removeFromControllerGroup(self, obj):
        if self.settings["ctlGrp"]:
            ctlGrp = self.settings["ctlGrp"]

        else:
            ctlGrp = "controllers"

        if ctlGrp not in self.groups.keys():
            self.groups[ctlGrp] = []

        try:
            self.groups[ctlGrp].remove(obj)
        except Exception:
            pass

        obj.attr("isCtl").set(False)
        pm.deleteAttr(obj.attr("isCtl"))
        ymt_util.setKeyableAttributesDontLockVisibility(obj, [])
        pm.delete(obj.getShape())


if __name__ == "__main__":
    pass
