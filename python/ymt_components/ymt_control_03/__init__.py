# MGEAR is under the terms of the MIT License

# Copyright (c) 2016 Jeremie Passerin, Miquel Campos

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Author:     Jeremie Passerin      geerem@hotmail.com  www.jeremiepasserin.com
# Author:     Miquel Campos         hello@miquel-campos.com  www.miquel-campos.com
# Date:       2016 / 10 / 10

#############################################
# GLOBAL
#############################################
import math

import pymel.core as pm
import pymel.core.datatypes as dt
import maya.api.OpenMaya as om
import maya.cmds as cmds

# mgear
from mgear.shifter.component import MainComponent

import mgear.core.utils as utils
import mgear.core.primitive as pri
import mgear.core.transform as tra
import mgear.core.attribute as att


#############################################
# COMPONENT
#############################################
class Component(MainComponent):

    def addObjects(self):
        size = self.size * 100

        if self.settings["neutralRotation"]:
            t = tra.getTransformFromPos(self.guide.pos["root"])
        else:
            t = self.guide.tra["root"]
            t = tra.setMatrixScale(t)

        self.root.setMatrix(t)
        self.ik_cns = pri.addTransform(self.root, self.getName("ik_cns"), t)

        icon = self.settings["icon"]
        po = dt.Vector(self.settings["ctlOffsetPosX"], self.settings["ctlOffsetPosY"], self.settings["ctlOffsetPosZ"])
        so = dt.Vector(self.settings["ctlOffsetSclX"], self.settings["ctlOffsetSclY"], self.settings["ctlOffsetSclZ"])
        ro = [self.settings["ctlOffsetRotX"], self.settings["ctlOffsetRotY"], self.settings["ctlOffsetRotZ"]]
        ro = [math.radians(ro[0]), math.radians(ro[1]), math.radians(ro[2])]
        ro = om.MEulerRotation(ro[0], ro[1], ro[2], om.MEulerRotation.kXYZ)

        self.ctl = self.addCtl(self.ik_cns, "ctl", t, self.color_ik, icon, h=(size*so.y), w=(size*so.x), d=(size*so.z), po=po, ro=ro)

        params = [ s for s in ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"] if self.settings["k_"+s] ]
        att.setKeyableAttributes(self.ctl, params)

        if self.settings["joint"]:
            self.jnt_pos.append([self.ctl, 0, None, self.settings["uniScale"]])

        if self.settings["k_ro"]:
            rotOderList = ["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"]
            att.setRotOrder(self.ctl, rotOderList[self.settings["default_rotorder"]])

        att.setInvertMirror(self.ctl, ["tx", "ry", "rz"])

    def addAttributes(self):
        # Ref
        if self.settings["ikrefarray"]:
            ref_names = self.settings["ikrefarray"].split(",")
            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam("ikref", "Ik Ref", 0, self.settings["ikrefarray"].split(","))

        if self.settings["rotrefarray"]:
            ref_names = self.settings["rotrefarray"].split(",")
            if len(ref_names) > 1:
                self.rotref_att = self.addAnimEnumParam("rotref", "Rot Ref", 0, self.settings["rotrefarray"].split(","))

    def addOperators(self):
        return

    def connect_orientCns(self):
        """
        Connection definition using orientation constraint.
        """

        refArray = self.settings["rotrefarray"]

        if refArray:
            ref_names = refArray.split(",")
            if len(ref_names) == 1:
                ref = self.rig.findRelative(ref_names[0])
                pm.parent(self.ik_cns, ref)
            else:
                ref = []
                for ref_name in ref_names:
                    ref.append(self.rig.findRelative(ref_name))

                ref.append(self.ik_cns)
                cns_node = pm.parentConstraint(*ref, maintainOffset=True, skipTranslate=("x", "y", "z"))
                cns_attr = pm.parentConstraint(cns_node, query=True, weightAliasList=True)

                for i, attr in enumerate(cns_attr):
                    if i == 0:
                        pm.setAttr(attr, 1.0)
                    else:
                        pm.setAttr(attr, 0.0)
                    node_name = pm.createNode("condition")
                    cmds.connectAttr(str(self.rotref_att), node_name + ".firstTerm")
                    pm.setAttr(node_name + ".secondTerm", i)
                    pm.setAttr(node_name + ".operation", 0)
                    pm.setAttr(node_name + ".colorIfTrueR", 1)
                    pm.setAttr(node_name + ".colorIfFalseR", 0)
                    cmds.connectAttr(node_name + ".outColorR", str(attr))

    # =====================================================
    # CONNECTOR
    # =====================================================
    # Set the relation beetween object from guide to rig.\n
    # @param self
    def setRelation(self):
        self.relatives["root"] = self.ctl
        if self.settings["joint"]:
            self.jointRelatives["root"] = 0

    # @param self
    def addConnection(self):
        self.connections["standard"] = self.connect_standard
        self.connections["orientation"] = self.connect_orientation

    # standard connection definition.
    # @param self
    def connect_standard(self):
        self.connect_standardWithSimpleIkRef()
        self.connect_orientCns()

    def connect_orientation(self):
        self.connect_orientCns()
