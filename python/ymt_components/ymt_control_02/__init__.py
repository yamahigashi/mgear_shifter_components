"""Component Scale Control 01 module"""

import maya.cmds as cmds

from mgear.shifter import component

from mgear.core import (
    attribute,
    transform,
    primitive
)

import ymt_shifter_utility as shifter_util


#############################################
# COMPONENT
#############################################


class Component(component.Main):
    """Shifter component Class"""

    # =====================================================
    # OBJECTS
    # =====================================================

    def initialHierarchy(self):
        """
        Create the inital structure for the rig.

        """
        # Root
        self.root = shifter_util.addJointTransformFromPos(
            self.model, self.getName("root"), self.guide.pos["root"])
        self.addToGroup(self.root, names=["componentsRoots"])

        # infos
        attribute.addAttribute(self.root, "componentType",    "string", self.guide.compType)
        attribute.addAttribute(self.root, "componentName",    "string", self.guide.compName)
        attribute.addAttribute(self.root, "componentVersion", "string", str(self.guide.version)[1:-1])
        attribute.addAttribute(self.root, "componentAuthor",  "string", self.guide.author)
        attribute.addAttribute(self.root, "componentURL",     "string", self.guide.url)
        attribute.addAttribute(self.root, "componentEmail",   "string", self.guide.email)

        # joint --------------------------------
        if self.options["joint_rig"]:
            self.component_jnt_org = primitive.addTransform(self.rig.jnt_org, self.getName("jnt_org"))
            # The initial assigment of the active jnt and the parent relative
            # jnt is the same, later will be updated base in the user options
            self.active_jnt = self.component_jnt_org
            self.parent_relative_jnt = self.component_jnt_org

        return

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

        # self.ik_cns = shifter_util.addJointTransform(self.root, self.getName("ik_cns"), t)

        self.ctl = shifter_util.addJointCtl(
            self,
            self.root,
            # self.ik_cns,
            "ctl",
            t,
            self.color_ik,
            self.settings["icon"],
            w=self.settings["ctlSize"] * self.size,
            h=self.settings["ctlSize"] * self.size,
            d=self.settings["ctlSize"] * self.size,
            tp=self.parentCtlTag,
            guide_loc_ref="root")

        # we need to set the rotation order before lock any rotation axis
        if self.settings["k_ro"]:
            rotOderList = ["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"]
            attribute.setRotOrder(
                self.ctl, rotOderList[self.settings["default_rotorder"]])

        params = [s for s in
                  ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"]
                  if self.settings["k_" + s]]
        attribute.setKeyableAttributes(self.ctl, params)

        # nodes
        self.scale_node = cmds.createNode("multiplyDivide")
        self.scale_node = cmds.createNode("multiplyDivide")

        self.scale_joint = shifter_util.addJointTransform(self.root, self.getName("scale_joint"), t)

        if self.settings["joint"]:
            self.jnt_pos.append([self.ctl, 0, None, self.settings["uniScale"]])

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
        # nodes
        cmds.connectAttr("{}.scale".format(self.ctl.name()), "{}.input1".format(self.scale_node))
        cmds.setAttr("{}.input2X".format(self.scale_node), 1.0)
        cmds.setAttr("{}.input2Y".format(self.scale_node), 1.0)
        cmds.setAttr("{}.input2Z".format(self.scale_node), 1.0)

        cmds.connectAttr("{}.output".format(self.scale_node), "{}.scale".format(self.scale_joint))
        cmds.connectAttr("{}.rotate".format(self.ctl.name()), "{}.rotate".format(self.scale_joint))

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.ctl
        self.relatives["scale_node"] = self.scale_node
        self.relatives["scale_joint"] = self.scale_joint
        self.controlRelatives["root"] = self.ctl
        if self.settings["joint"]:
            self.jointRelatives["root"] = 0

        self.aliasRelatives["root"] = "ctl"

    def addConnection(self):
        """Add more connection definition to the set"""
        self.connections["standard"] = self.connect_standard
        self.connections["orientation"] = self.connect_orientation

    def connect_standard(self):
        """standard connection definition for the component"""
        self.connect_standardWithSimpleIkRef()

    def connect_orientation(self):
        """Orient connection definition for the component"""
        self.connect_orientCns()

    def postConnect(self):
        if self.parent_comp is not None:
            # self.parent
            parent_scale_node = self.parent_comp.getRelation("scale_node")
            parent_scale_joint = self.parent_comp.getRelation("scale_joint")

            if parent_scale_node:
                cmds.connectAttr("{}.output".format(parent_scale_node), "{}.input2".format(self.scale_node))
                cmds.connectAttr("{}.output".format(parent_scale_node), "{}.scale".format(self.root.name()))

            else:
                cmds.connectAttr("{}.scale".format(self.parent.name()), "{}.input2".format(self.scale_node))
                cmds.connectAttr("{}.scale".format(self.parent.name()), "{}.scale".format(self.root.name()))

            if parent_scale_joint:
                parent_scale_joint.addChild(self.scale_joint)
                # cmds.parentConstraint(self.scale_joint.name(), self.root.name(), maintainOffset=True, skipRotate=("x", "y", "z"))
            else:
                self.parent.addChild(self.scale_joint)
