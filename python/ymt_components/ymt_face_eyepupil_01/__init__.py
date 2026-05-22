"""mGear shifter components"""
# pylint: disable=import-error,W0201,C0111,C0112
from __future__ import annotations

import importlib
from typing import List, TYPE_CHECKING

import maya.cmds as cmds

try:
    pm = importlib.import_module("mgear.pymaya")
    dt = importlib.import_module("mgear.pymaya.datatypes")
except ImportError:
    pm = importlib.import_module("pymel.core")
    dt = importlib.import_module("pymel.core.datatypes")

from mgear.shifter import component

from mgear.core import (
    transform,
    attribute,
    node,
    primitive,
)

import ymt_shifter_utility as ymt_util

if TYPE_CHECKING:
    from ymt_shifter_utility.type_protocols import MatrixLike, PlugLike, PymelNode, VectorLike

from logging import (
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
    def addToSubGroup(self, obj: PymelNode, group_name: str) -> None:

        if self.settings["ctlGrp"]:
            ctlGrp = self.settings["ctlGrp"]
        else:
            ctlGrp = "controllers"

        self.addToGroup(obj, group_name, parentGrp=ctlGrp)

    def addObjects(self) -> None:
        """Add all the objects needed to create the component."""

        if self.settings["neutralRotation"]:
            t: MatrixLike = transform.getTransformFromPos(self.guide.pos["root"])
        else:
            t = self.guide.tra["root"]
            if self.settings["mirrorBehaviour"] and self.negate:
                scl: List[int] = [1, 1, -1]
            else:
                scl = [1, 1, 1]
            t = transform.setMatrixScale(t, scl)

        self.initialDist: float = self.size * .2
        self.detailControllersGroupName: str = "controllers_detail"  # TODO: extract to settings
        self.primaryControllersGroupName: str = "controllers_primary"  # TODO: extract to settings
        self.connect_surface_slider: bool = self.settings["isSlidingSurface"]

        pivot_t: MatrixLike = self.guide.tra["sliding_surface"]
        self.lookat_cns: PymelNode = primitive.addTransform(self.root, self.getName("lookat_cns"), pivot_t)
        self.ctl: PymelNode = self.addCtl(self.lookat_cns,
                               "ctl",
                               t,
                               self.color_ik,
                               self.settings["icon"],
                               w=self.settings["ctlSize"] * self.size * 0.05,
                               h=self.settings["ctlSize"] * self.size * 0.05,
                               d=self.settings["ctlSize"] * self.size * 0.05 * 0.05,
                               tp=self.parentCtlTag)
        self.addToSubGroup(self.ctl, self.primaryControllersGroupName)

        self.aim_cns: PymelNode = primitive.addTransform(self.root, self.getName("aim_cns"), t)
        if self.settings["joint"]:
            self.jnt_pos.append([self.aim_cns, "aim"])

        diff: VectorLike = self.guide.apos[2] - self.guide.apos[0]
        base_pos: VectorLike = transform.getPositionFromMatrix(t)
        base_pos = dt.Vector(base_pos[0], base_pos[1], base_pos[2])
        offset: VectorLike = diff.normal() * self.initialDist + base_pos
        offset_mat: MatrixLike = transform.setMatrixPosition(t, offset)
        self.proj_cns: PymelNode = primitive.addTransform(self.aim_cns, self.getName("proj_cns"), offset_mat)

        pos: VectorLike = self.guide.pos["lookat"]
        t = transform.setMatrixPosition(t, pos)
        self.ik_cns: PymelNode = primitive.addTransform(self.root, self.getName("ik_cns"), t)
        self.lookat: PymelNode = self.addCtl(self.ik_cns,
                                  "lookat_ctl",
                                  t,
                                  self.color_ik,
                                  "circle",
                                  w=self.settings["ctlSize"] * self.size * 0.18,
                                  h=self.settings["ctlSize"] * self.size * 0.18,
                                  d=self.settings["ctlSize"] * self.size * 0.18,
                                  ro= dt.Vector([1.5708, 0.0, 0.0]),
                                  tp=self.parentCtlTag)

        self.addToSubGroup(self.lookat, self.primaryControllersGroupName)

        # we need to set the rotation order before lock any rotation axis
        if self.settings["k_ro"]:
            rotOderList: List[str] = ["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"]
            attribute.setRotOrder(
                self.ctl, rotOderList[self.settings["default_rotorder"]])

        params: List[str] = [s for s in
                  ("tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz")
                  if self.settings["k_" + s]]
        ymt_util.setKeyableAttributesDontLockVisibility(self.ctl, params)

        if self.settings["joint"]:
            self.jnt_pos.append([self.ctl, 0, None, self.settings["uniScale"]])

        self.surfRef: str = self.settings["surfaceReference"]
        if not self.surfRef:
            guide_surface: PymelNode = self.guide.getObjectByLocalName("sliding_surface")
            self.sliding_surface: PymelNode = pm.duplicate(guide_surface)[0]
            pm.parent(self.sliding_surface, self.root)
            self.sliding_surface.visibility.set(False)
            pm.makeIdentity(self.sliding_surface, apply=True, t=1,  r=1, s=1, n=0, pn=1)

    def addAttributes(self) -> None:
        # Ref
        if self.settings["ikrefarray"]:
            ref_names: List[str] = self.get_valid_alias_list(
                self.settings["ikrefarray"].split(","))
            if len(ref_names) > 1:
                self.ikref_att: PlugLike = self.addAnimEnumParam(
                    "ikref",
                    "Ik Ref",
                    0,
                    ref_names)

    def addOperators(self) -> None:
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
    def setRelation(self) -> None:
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.ctl
        self.relatives["lookat"] = self.lookat
        self.controlRelatives["root"] = self.ctl
        if self.settings["joint"]:
            self.jointRelatives["root"] = 0

        self.aliasRelatives["root"] = "ctl"

    def addConnection(self) -> None:
        """Add more connection definition to the set"""
        self.connections["standard"] = self.connect_standard

    def connect_standard(self) -> None:
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
                    arrow: PymelNode = self.parent_comp.arrow_ctl
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

    def connect_ctl_to_aim(self) -> None:
        """Connect the control to the aim cns"""

        parentGuide = self.guide.parentComponent
        if parentGuide is not None and "face_eye" in parentGuide.compType:
            arrow: PymelNode = self.parent_comp.arrow_ctl
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


    def connect_slide_ghost(self) -> None:

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


def ghostSliderForPupil(ctl: PymelNode, ghostCtl: PymelNode, surface: PymelNode, sliderParent: PymelNode) -> None:
    """Modify the ghost control behaviour to slide on top of a surface

    Args:
        ghostControls (dagNode): The ghost control
        surface (Surface): The NURBS surface
        sliderParent (dagNode): The parent for the slider.
    """

    surfaceShape: PymelNode = surface.getShape()

    t: MatrixLike = ctl.getMatrix(worldSpace=True)

    oParent: PymelNode = ghostCtl.getParent()
    npoName: str = "_".join(ghostCtl.name().split("_")[:-1]) + "_npo"
    oTra: PymelNode = pm.PyNode(pm.createNode("transform", n=npoName, p=oParent, ss=True))
    oTra.setTransformation(ghostCtl.getMatrix())
    pm.parent(ghostCtl, oTra)

    slider: PymelNode = primitive.addTransform(sliderParent, ctl.name() + "_slideDriven", t)

    down: List[PymelNode]
    up: List[PymelNode]
    down, _, up = ymt_util.findPathAtoB(ctl, sliderParent)
    mul_node: PymelNode = pm.createNode("multMatrix")
    j: int = 0
    k: int = 0
    for j, d in enumerate(down):
        d.attr("matrix") >> mul_node.attr("matrixIn[{}]".format(j))
    for k, u in enumerate(up):
        u.attr("inverseMatrix") >> mul_node.attr("matrixIn[{}]".format(k + j + 1))

    dm_node: PymelNode = node.createDecomposeMatrixNode(mul_node.attr("matrixSum"))

    cps_node: PymelNode = pm.createNode("closestPointOnSurface")
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
