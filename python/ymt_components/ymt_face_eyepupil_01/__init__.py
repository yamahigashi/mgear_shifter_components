"""mGear shifter components"""
# pylint: disable=import-error,W0201,C0111,C0112
import sys
import maya.cmds as cmds

try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm

from mgear.shifter import component

from mgear.core import (
    transform,
    attribute,
    node,
    primitive,
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


#############################################
# COMPONENT
#############################################
class Component(component.Main):
    """Shifter component Class"""

    # =====================================================
    # OBJECTS
    # =====================================================
    def addToSubGroup(self, obj, group_name):

        if self.settings["ctlGrp"]:
            ctlGrp = self.settings["ctlGrp"]
        else:
            ctlGrp = "controllers"

        self.addToGroup(obj, group_name, parentGrp=ctlGrp)

    def addObjects(self):
        """Add all the objects needed to create the component."""

        if self.settings["neutralRotation"]:
            t = transform.getTransformFromPos(self.guide.pos["root"])
        else:
            t = self.guide.tra["root"]
            if self.settings["mirrorBehaviour"] and self.negate:
                scl = [1, 1, -1]
            else:
                scl = [1, 1, 1]
            t = transform.setMatrixScale(t, scl)

        self.initialDist = self.size * .2
        self.detailControllersGroupName = "controllers_detail"  # TODO: extract to settings
        self.primaryControllersGroupName = "controllers_primary"  # TODO: extract to settings
        self.connect_surface_slider = self.settings["isSlidingSurface"]

        pivot_t = self.guide.tra["sliding_surface"]
        self.lookat_cns = primitive.addTransform(self.root, self.getName("lookat_cns"), pivot_t)
        self.ctl = self.addCtl(self.lookat_cns,
                               "ctl",
                               t,
                               self.color_ik,
                               self.settings["icon"],
                               w=self.settings["ctlSize"],
                               h=self.settings["ctlSize"],
                               d=self.settings["ctlSize"] * 0.05,
                               tp=self.parentCtlTag)
        self.addToSubGroup(self.ctl, self.primaryControllersGroupName)

        self.aim_cns = primitive.addTransform(self.root, self.getName("aim_cns"), t)
        if self.settings["joint"]:
            self.jnt_pos.append([self.aim_cns, "aim"])

        diff = self.guide.apos[2] - self.guide.apos[0]
        offset = diff.normal() * self.initialDist + t.translate
        offset_mat = transform.setMatrixPosition(t, offset)
        self.proj_cns = primitive.addTransform(self.aim_cns, self.getName("proj_cns"), offset_mat)

        t = self.guide.tra["lookat"]
        self.ik_cns = primitive.addTransform(self.root, self.getName("ik_cns"), t)
        self.lookat = self.addCtl(self.ik_cns,
                                  "lookat_ctl",
                                  t,
                                  self.color_ik,
                                  "circle",
                                  w=self.settings["ctlSize"],
                                  h=self.settings["ctlSize"],
                                  d=self.settings["ctlSize"],
                                  tp=self.parentCtlTag)

        self.addToSubGroup(self.lookat, self.primaryControllersGroupName)

        # we need to set the rotation order before lock any rotation axis
        if self.settings["k_ro"]:
            rotOderList = ["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"]
            attribute.setRotOrder(
                self.ctl, rotOderList[self.settings["default_rotorder"]])

        params = [s for s in
                  ("tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz")
                  if self.settings["k_" + s]]
        ymt_util.setKeyableAttributesDontLockVisibility(self.ctl, params)

        if self.settings["joint"]:
            self.jnt_pos.append([self.ctl, 0, None, self.settings["uniScale"]])

        self.surfRef = self.settings["surfaceReference"]
        if not self.surfRef:
            self.sliding_surface = pm.duplicate(self.guide.getObjects(self.guide.root)["sliding_surface"])[0]
            pm.parent(self.sliding_surface, self.root)
            self.sliding_surface.visibility.set(False)
            pm.makeIdentity(self.sliding_surface, apply=True, t=1,  r=1, s=1, n=0, pn=1)

    def addAttributes(self):
        # Ref
        if self.settings["ikrefarray"]:
            ref_names = self.get_valid_alias_list(
                self.settings["ikrefarray"].split(","))
            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam(
                    "ikref",
                    "Ik Ref",
                    0,
                    ref_names)

    def addOperators(self):
        cmds.aimConstraint(
                self.lookat.name(),
                self.aim_cns.name(),
                aim=[0, 0, 1],
                u=[0, 1, 0],
                wut="objectrotation",
                wuo=self.root.name()
        )

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.ctl
        self.relatives["lookat"] = self.lookat
        self.controlRelatives["root"] = self.ctl
        if self.settings["joint"]:
            self.jointRelatives["root"] = 0

        self.aliasRelatives["root"] = "ctl"

    def addConnection(self):
        """Add more connection definition to the set"""
        self.connections["standard"] = self.connect_standard

    def connect_standard(self):
        """standard connection definition for the component"""

        self.connect_standardWithSimpleIkRef()
        if self.surfRef:
            ref = self.rig.findComponent(self.surfRef)
            self.sliding_surface = ref.sliding_surface

        if self.connect_surface_slider:
            try:
                self.connect_slide_ghost()
                parentGuide = self.guide.parentComponent
                if parentGuide is not None and "face_eye" in parentGuide.compType:
                    arrow = self.parent_comp.arrow_ctl
                    cmds.parentConstraint(
                        arrow.name(),
                        self.proj_cns.name(),
                        mo=True
                    )

            except Exception:
                import traceback
                traceback.print_exc()
        else:
            try:
                self.connect_ctl_to_aim()
            except Exception:
                import traceback
                traceback.print_exc()

        ymt_util.setKeyableAttributesDontLockVisibility(self.proj_cns, [])
        ymt_util.setKeyableAttributesDontLockVisibility(self.aim_cns, [])

    def connect_ctl_to_aim(self):
        """Connect the control to the aim cns"""

        parentGuide = self.guide.parentComponent
        if parentGuide is not None and "face_eye" in parentGuide.compType:
            arrow = self.parent_comp.arrow_ctl
            cmds.parentConstraint(
                arrow.name(),
                self.lookat_cns.name(),
                mo=True
            )

        else:
            cmds.parentConstraint(
                self.aim_cns.name(),
                self.lookat_cns.name(),
                mo=True,
                skipTranslate=["x", "y", "z"]
            )
 

    def connect_slide_ghost(self):

        # slide system
        try:
            ghostSliderForPupil(
                self.proj_cns,
                self.ctl,
                self.sliding_surface,
                self.sliding_surface.getParent()
            )
        except:
            import traceback as tb
            tb.print_exc()
            raise


def ghostSliderForPupil(ctl, ghostCtl, surface, sliderParent):
    """Modify the ghost control behaviour to slide on top of a surface

    Args:
        ghostControls (dagNode): The ghost control
        surface (Surface): The NURBS surface
        sliderParent (dagNode): The parent for the slider.
    """

    surfaceShape = surface.getShape()

    t = ctl.getMatrix(worldSpace=True)

    oParent = ghostCtl.getParent()
    npoName = "_".join(ghostCtl.name().split("_")[:-1]) + "_npo"
    oTra = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))
    oTra.setTransformation(ghostCtl.getMatrix())
    pm.parent(ghostCtl, oTra)

    slider = primitive.addTransform(sliderParent, ctl.name() + "_slideDriven", t)

    down, _, up = ymt_util.findPathAtoB(ctl, sliderParent)
    mul_node = pm.createNode("multMatrix")
    j = k = 0
    for j, d in enumerate(down):
        d.attr("matrix") >> mul_node.attr("matrixIn[{}]".format(j))
    for k, u in enumerate(up):
        u.attr("inverseMatrix") >> mul_node.attr("matrixIn[{}]".format(k + j + 1))

    dm_node = node.createDecomposeMatrixNode(mul_node.attr("matrixSum"))

    cps_node = pm.createNode("closestPointOnSurface")
    dm_node.attr("outputTranslate") >> cps_node.attr("inPosition")
    surfaceShape.attr("local") >> cps_node.attr("inputSurface")
    cps_node.attr("position") >> slider.attr("translate")

    pm.normalConstraint(surfaceShape,
                        slider,
                        aimVector=[0, 0, 1],
                        upVector=[0, 1, 0],
                        worldUpType="objectrotation",
                        worldUpVector=[0, 1, 0],
                        worldUpObject=sliderParent)

    pm.parent(ghostCtl.getParent(), slider)
    ymt_util.setKeyableAttributesDontLockVisibility(slider, [])
    ymt_util.setKeyableAttributesDontLockVisibility(oTra, [])
