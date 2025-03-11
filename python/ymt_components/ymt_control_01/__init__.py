"""Component Control 01 module"""
import math
from mgear.shifter import component
from mgear.core import attribute, transform, primitive

try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm

import ymt_shifter_utility as ymt_util

#############################################
# COMPONENT
#############################################


class Component(component.Main):
    """Shifter component Class"""

    # =====================================================
    # OBJECTS
    # =====================================================
    def _needToMirror(self):
        if self.settings["mirrorBehaviour"] and self.negate:
            return True

        if self.negate and (
            self.settings["mirrorAxisX"] or
            self.settings["mirrorAxisY"] or
            self.settings["mirrorAxisZ"]
        ):
            return True

        return False

    def addObjects(self):
        """Add all the objects needed to create the component."""

        if self.settings["neutralRotation"]:
            t = transform.getTransformFromPos(self.guide.pos["root"])
        else:
            t = self.guide.tra["root"]
            if self._needToMirror():
                scl = [1, 1, 1]
                scl[0] = -1 if self.settings["mirrorAxisX"] else 1
                scl[1] = -1 if self.settings["mirrorAxisY"] else 1
                scl[2] = -1 if self.settings["mirrorAxisZ"] else 1
                t = transform.setMatrixScale(t, scl)

                rx = self.settings["mirrorAxisX"] * math.pi
                ry = self.settings["mirrorAxisY"] * math.pi
                rz = self.settings["mirrorAxisZ"] * math.pi
                # t = pm.datatypes.TransformationMatrix(t)
                # t.addRotation((rx, ry, rz), 'XYZ', 'object')

            else:
                scl = [1, 1, 1]
                t = transform.setMatrixScale(t, scl)

        self.ik_cns = primitive.addTransform(
            self.root, self.getName("ik_cns"), t)

        self.ctl = self.addCtl(self.ik_cns,
                               "ctl",
                               t,
                               self.color_ik,
                               self.settings["icon"],
                               w=self.settings["ctlSize"] * self.size,
                               h=self.settings["ctlSize"] * self.size,
                               d=self.settings["ctlSize"] * self.size,
                               tp=self.parentCtlTag)

        # we need to set the rotation order before lock any rotation axis
        if self.settings["k_ro"]:
            rotOderList = ["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"]
            attribute.setRotOrder(
                self.ctl, rotOderList[self.settings["default_rotorder"]])

        params = [s for s in
                  ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"]
                  if self.settings["k_" + s]]
        ymt_util.setKeyableAttributesDontLockVisibility(self.ctl, params)

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
        return

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.ctl
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
