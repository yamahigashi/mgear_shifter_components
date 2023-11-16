"""mGear shifter components"""
# pylint: disable=import-error,W0201,C0111,C0112
import sys
import maya.cmds as cmds

import pymel.core as pm
from pymel.core import datatypes

from mgear.shifter import component

from mgear.core import (
    transform,
    # curve,
    node,
    primitive,
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
    # WARN,
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
        self.icon = "circle"
        self.icon = "square"
        self.icon = "sphere"  # TODO: extract to settings
        # --------------------------------------------------------
        self.ik_ctl = []
        self.ik_npo = []

        # --------------------------------------------------------
        self.previusTag = self.parentCtlTag
        if self.settings["neutralpose"]:
            t = transform.getTransformFromPos(self.guide.pos["root"])
            if self.negate:
                scl = [-1, 1, 1]
                t = transform.setMatrixScale(t, scl)

        else:
            t = self.guide.tra["root"]
            t = transform.setMatrixScale(t)

        self.npo = addTransform(self.root, self.getName("npo"), t)
        self.surfaceCtl = self.addCtl(
            self.npo,
            "surface_ctl",
            t,
            self.color_ik,
            self.icon,
            ro=datatypes.Vector([1.5708, 0, 0]),
            w=self.size,
            h=self.size,
            d=self.size,
        )
        if self.settings["addJoints"]:
            self.jnt_pos = [[self.surfaceCtl , "0"]]

        self.surfRef = self.settings["surfaceReference"]
        if not self.surfRef:
            self.sliding_surface = pm.duplicate(self.guide.getObjects(self.guide.root)["sliding_surface"])[0]
            pm.parent(self.sliding_surface.name(), self.root)
            self.sliding_surface.visibility.set(False)
            pm.makeIdentity(self.sliding_surface, apply=True, t=1,  r=1, s=1, n=0, pn=1)

        if self.connect_surface_slider:
            bt = getTransform(self.root)
            self.slider_root = addTransform(self.root, self.getName("sliders"), bt)
            ymt_util.setKeyableAttributesDontLockVisibility(self.slider_root, [])

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""

        if not self.settings["ui_host"]:
            self.uihost = self.surfaceCtl

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
                self.connect_slide_ghost()

            except Exception as _:
                import traceback
                traceback.print_exc()

        else:
            try:
                self.connect_rivet()

            except Exception as _:
                import traceback
                traceback.print_exc()

    def connect_slide_ghost(self):

        # create ghost controls
        self.ghostCtl = ghost.createGhostCtl(self.surfaceCtl, self.slider_root)
        # self.ghostCtl.rename(self.getName("surface_ctl"))

        if self.settings.get("visHost", False):
            self._visi_off_lock(self.surfaceCtl)

        oParent = self.ghostCtl.getParent()
        npoName = "_".join(self.ghostCtl.name().split("_")[:-1]) + "_npo"
        npo = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))
        npo.addChild(self.ghostCtl)

        self.ghostCtl.attr("isCtl") // self.surfaceCtl.attr("isCtl")
        self.ghostCtl.attr("translate") // self.surfaceCtl.attr("translate")
        self.ghostCtl.attr("rotate") // self.surfaceCtl.attr("rotate")
        self.ghostCtl.attr("scale") // self.surfaceCtl.attr("scale")

        self.surfaceCtl.rename(self.getName("source_ctl"))

        ctl = pm.listConnections(self.ghostCtl, t="transform")[-1]
        t = ctl.getMatrix(worldSpace=True)

        oParent = self.ghostCtl.getParent()
        npoName = "_".join(self.ghostCtl.name().split("_")[:-1]) + "_npo"
        npo = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))
        npo.setTransformation(self.ghostCtl.getMatrix())
        if self.negate:
            npo.attr("sz").set(-1)
        pm.parent(self.ghostCtl, npo, absolute=True)
        self.ghostCtl.attr("sz").set(1)

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
        pm.parent(self.ghostCtl.getParent(), slider, absolute=True)
        if self.settings["addJoints"]:
            self.jnt_pos = [[self.ghostCtl, "0"]]

        if self.surfaceKeyable:
            self.ghostCtl.attr("isCtl").set(True)
        else:
            self.removeFromControllerGroup(self.ghostCtl)

        if self.sourceKeyable:
            self.surfaceCtl.attr("isCtl").set(True)
        else:
            self.removeFromControllerGroup(self.surfaceCtl)

        # add to group
        if self.settings["ctlGrp"]:
            ctlGrp = self.settings["ctlGrp"]
            self.addToGroup(self.ghostCtl, ctlGrp, "controllers")
            self.addToGroup(self.surfaceCtl, ctlGrp, "controllers")

        else:
            ctlGrp = "controllers"
            self.addToGroup(self.ghostCtl, ctlGrp)
            self.addToGroup(self.surfaceCtl, ctlGrp)

        if ctlGrp not in self.groups.keys():
            self.groups[ctlGrp] = []

        ymt_util.setKeyableAttributesDontLockVisibility(npo, [])
        self.setRelation()  # MUST re-setRelation, swapped ghost and real controls

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
        self.relatives["ctl"] = self.surfaceCtl

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
        pm.delete(pm.listRelatives(obj, shapes=True))


if __name__ == "__main__":
    pass
