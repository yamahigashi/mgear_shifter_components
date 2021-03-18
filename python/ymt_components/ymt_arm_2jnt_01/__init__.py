##########################################################
# GLOBAL
##########################################################
import math

# Maya
import pymel.core as pm
import pymel.core.datatypes as dt

# import maya.OpenMaya as om

# mgear
from mgear.shifter.component import MainComponent

import mgear.core.primitive as pri
import mgear.core.transform as tra
import mgear.core.attribute as att
import mgear.core.node as nod
# import mgear.core.icon as ico
import mgear.core.vector as vec
# import mgear.core.utils as utils


##########################################################
# COMPONENT
##########################################################
class Component(MainComponent):

    def _add_fk(self, i, parent, t, tOld):

        dist = vec.getDistance(self.guide.apos[i], self.guide.apos[i + 1])
        if self.settings["neutralpose"] or not tOld:
            tnpo = t
        else:
            tnpo = tra.setMatrixPosition(tOld, tra.getPositionFromMatrix(t))

        fk_npo = pri.addTransform(parent, self.getName("fk%s_npo" % i), tnpo)
        fk_ctl = self.addCtl(
            fk_npo,
            "fk%s_ctl" % i,
            t,
            self.color_fk,
            "cube",
            w=dist,
            h=self.size * .1,
            d=self.size * .1,
            po=dt.Vector(dist * .5 * self.n_factor, 0, 0)
        )
        self.fk_npo.append(fk_npo)
        self.fk_ctl.append(fk_ctl)

        return fk_ctl

    def addObjects(self):

        self.WIP = self.options["mode"]
        self.normal = self.guide.blades["blade"].z * -1
        self.binormal = self.guide.blades["blade"].x

        # FK controllers ------------------------------------
        self.fk_npo = []
        self.fk_ctl = []
        t = self.guide.tra["root"]
        self.fk_cns = pri.addTransform(self.root, self.getName("fk_cns"), t)

        parent = self.fk_cns
        tOld = False

        for i, t in enumerate(tra.getChainTransform(self.guide.apos, self.normal, self.negate)):
            parent = self._add_fk(i, parent, t, tOld)

        # IK controllers ------------------------------------
        normal = vec.getTransposedVector(self.normal, [self.guide.apos[0], self.guide.apos[1]], [self.guide.apos[-3], self.guide.apos[-2]])

        if self.negate:
            t = tra.getTransformLookingAt(self.guide.apos[-3], self.guide.apos[-2], normal, "xy", self.negate)
            t = tra.setMatrixPosition(t, self.guide.apos[-2])
        else:
            t = tra.getTransformLookingAt(self.guide.apos[-3], self.guide.apos[-2], normal, "x-y", self.negate)
            t = tra.setMatrixPosition(t, self.guide.apos[-2])

        self.ik_cns = pri.addTransform(self.root, self.getName("ik_cns"), t)
        self.ik_ctl = self.addCtl(self.ik_cns, "ik_ctl", t, self.color_ik, "cube", w=self.size * .15, h=self.size * .15, d=self.size * .15)
        self.ikRot_npo = pri.addTransform(self.root, self.getName("ikRot_npo"), t)
        self.ikRot_cns = pri.addTransform(self.ikRot_npo, self.getName("ikRot_cns"), t)
        self.ikRot_ctl = self.addCtl(self.ikRot_cns, "ikRot_ctl", t, self.color_fk, "flower", w=self.size * .35, h=self.size * .35, d=self.size * .35, ro=dt.Vector(0, math.radians(90), 0))

        v = self.guide.apos[-2] - self.guide.apos[0]
        v = v ^ self.normal
        v.normalize()
        v *= self.size
        v += self.guide.apos[1]
        self.upv_cns = pri.addTransformFromPos(self.root, self.getName("upv_cns"), v)

        self.upv_ctl = self.addCtl(self.upv_cns, "upv_ctl", tra.getTransform(self.upv_cns), self.color_ik, "diamond", w=self.size * .1)

        # Chain
        self.chain = pri.add2DChain(self.root, self.getName("chain"), self.guide.apos[0:-1], self.normal, self.negate)
        self.chain[0].attr("visibility").set(self.WIP)

        # Chain of deformers -------------------------------
        self.loc = []
        parent = self.root
        for i, t in enumerate(tra.getChainTransform(self.guide.apos, self.normal, self.negate)):
            loc = pri.addTransform(parent, self.getName("%s_loc" % i), t)

            self.loc.append(loc)
            self.jnt_pos.append([loc, i])
            parent = loc

        # End reference ------------------------------------
        self.end_ref = pri.addTransform(self.chain[-1], self.getName("end_ref"), t)
        self.jnt_pos.append([self.loc[-1], 'end'])

        # References --------------------------------------
        self.ik_ref = pri.addTransform(self.ik_ctl, self.getName("ik_ref"), tra.getTransform(self.ik_ctl))
        self.fk_ref = pri.addTransform(self.fk_ctl[2], self.getName("fk_ref"), tra.getTransform(self.ik_ctl))

        self.ctrn_loc = pri.addTransformFromPos(self.root, self.getName("ctrn_loc"), self.guide.apos[1])
        self.eff_loc = pri.addTransformFromPos(self.root, self.getName("eff_loc"), self.guide.apos[2])

        # match IK FK references
        self.match_ik = pri.addTransform(self.fk_ctl[2], self.getName("ik_mth"), tra.getTransform(self.ik_ctl))
        mid = (len(self.fk_ctl) - 1) / 2
        self.match_ikUpv = pri.addTransform(self.fk_ctl[mid], self.getName("upv_mth"), tra.getTransform(self.upv_ctl))

        if True or self.settings["ikTR"]:
            reference = self.ikRot_ctl
            self.match_ikRot = pri.addTransform(
                self.fk_ctl[-1],
                self.getName("ikRot_mth"),
                tra.getTransform(self.ikRot_ctl))
        else:
            reference = self.ik_ctl

        self.match_fk0_off = pri.addTransform(self.root, self.getName("matchFk0_npo"), tra.getTransform(self.fk_ctl[1]))
        self.match_fk0 = pri.addTransform(self.match_fk0_off, self.getName("fk0_mth"), tra.getTransform(self.fk_ctl[0]))

        self.match_fk1_off = pri.addTransform(self.root, self.getName("matchFk1_npo"), tra.getTransform(self.fk_ctl[2]))
        self.match_fk1 = pri.addTransform(self.match_fk1_off, self.getName("fk1_mth"), tra.getTransform(self.fk_ctl[1]))

        # self.match_fk2_off = pri.addTransform(self.root, self.getName("matchFk2_npo"), tra.getTransform(self.fk_ctl[2]))
        # self.match_fk2 = pri.addTransform(self.match_fk2_off, self.getName("fk2_mth"), tra.getTransform(self.fk_ctl[1]))
        self.match_fk2 = pri.addTransform(reference, self.getName("fk2_mth"), tra.getTransform(self.fk_ctl[2]))

        # 1 bone chain for upv ref
        self.armChainUpvRef = pri.add2DChain(
            self.root,
            self.getName("armUpvRef%s_jnt"),
            [self.guide.apos[0], self.guide.apos[2]],
            self.normal,
            False,
            self.WIP)

        self.armChainUpvRef[1].setAttr(
            "jointOrientZ",
            self.armChainUpvRef[1].getAttr("jointOrientZ") * -1)

    # =====================================================
    # PROPERTY
    # =====================================================
    def addAttributes(self):
        self.settings["upvrefarray"] = self.settings["ikrefarray"]

        # Anim -------------------------------------------
        self.blend_att = self.addAnimParam("blend", "Fk/Ik Blend", "double", self.settings["blend"], 0, 1)
        self.rot_space_att = self.addAnimEnumParam("rot_space", "Wrist Rotation Parent", 0, ["local", "world"])

        # Ref
        if self.settings["ikrefarray"]:
            ref_names = self.settings["ikrefarray"].split(",")
            if len(ref_names) > 1:
                self.ikref_att = self.addAnimEnumParam("ikref", "Arm IK Ref", 0, self.settings["ikrefarray"].split(","))

            ref_names = self.settings["upvrefarray"].split(",")
            ref_names = ["Auto", "Hand IK"] + ref_names
            if len(ref_names) > 1:
                self.upvref_att = self.addAnimEnumParam("upvref", "Arm UpV Ref", 0, ref_names)

        self.roll_att = self.addAnimParam("roll", "Roll", "double", 0, -180, 180)
    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):

        # Visibilities -------------------------------------
        # fk
        fkvis_node = nod.createReverseNode(self.blend_att)
        rotspace_rev_node = nod.createReverseNode(self.rot_space_att)

        for fk_ctl in self.fk_ctl:
            for shp in fk_ctl.getShapes():
                pm.connectAttr(fkvis_node + ".outputX", shp.attr("visibility"))

        # ik
        for shp in self.upv_ctl.getShapes():
            pm.connectAttr(self.blend_att, shp.attr("visibility"))

        for shp in self.ik_ctl.getShapes():
            pm.connectAttr(self.blend_att, shp.attr("visibility"))

        for shp in self.ikRot_ctl.getShapes():
            pm.connectAttr(rotspace_rev_node + ".outputX", shp.attr("visibility"))

        # IK Chain -----------------------------------------
        self.ikh = pri.addIkHandle(self.root, self.getName("ikh"), self.chain)
        self.ikh.attr("visibility").set(False)

        # Constraint and up vector
        pm.pointConstraint(self.ik_ctl, self.ikh, maintainOffset=False)
        pm.poleVectorConstraint(self.upv_ctl, self.ikh)

        # Chain of deformers -------------------------------
        for i, loc in enumerate(self.loc):

            rev_node = nod.createReverseNode(self.blend_att)

            # orientation
            if i == len(self.loc) - 1:
                cns = pm.parentConstraint(self.fk_ctl[i], self.chain[i], loc, maintainOffset=True, skipRotate=['x', 'y', 'z'])
            else:
                    cns = pm.parentConstraint(self.fk_ctl[i], self.chain[i], loc, maintainOffset=True)

            weight_att = pm.parentConstraint(cns, query=True, weightAliasList=True)
            pm.connectAttr(rev_node + ".outputX", weight_att[0])
            pm.connectAttr(self.blend_att, weight_att[1])

            # scaling
            blend_node = pm.createNode("blendColors")
            pm.connectAttr(self.chain[i].attr("scale"), blend_node + ".color1")
            pm.connectAttr(self.fk_ctl[i].attr("scale"), blend_node + ".color2")
            pm.connectAttr(self.blend_att, blend_node + ".blender")
            pm.connectAttr(blend_node + ".output",  loc + ".scale")

        # wrist rotation parent space switcher
        cns = pm.parentConstraint(self.loc[-2], self.ikRot_cns, maintainOffset=True, skipRotate=['x', 'y', 'z'])
        cns = pm.parentConstraint(self.loc[-2], self.ik_ctl, self.ikRot_cns, maintainOffset=True, skipTranslate=['x', 'y', 'z'])
        weight_att = pm.parentConstraint(cns, query=True, weightAliasList=True)
        pm.connectAttr(rotspace_rev_node + ".outputX", weight_att[0])
        pm.connectAttr(self.rot_space_att, weight_att[1])

        # wrist position switcher
        cns = pm.parentConstraint(self.fk_ctl[-1], self.end_ref, self.loc[-1], maintainOffset=True, skipTranslate=['x', 'y', 'z'])
        weight_att = pm.parentConstraint(cns, query=True, weightAliasList=True)
        pm.connectAttr(rev_node + ".outputX", weight_att[0])
        pm.connectAttr(self.blend_att, weight_att[1])

        pm.parentConstraint(self.ikRot_ctl, self.end_ref, maintainOffset=True, skipTranslate=['x', 'y', 'z'])

        # match IK/FK ref
        pm.parentConstraint(self.chain[0], self.match_fk0_off, mo=True)
        pm.parentConstraint(self.chain[1], self.match_fk1_off, mo=True)
        pm.parentConstraint(self.chain[2], self.match_fk2, mo=True, skipRotate=("x", "y", "z"))
        pm.parentConstraint(self.ikRot_ctl, self.match_fk2, mo=True, skipTranslate=("x", "y", "z"))

        #
        for x in self.fk_ctl:
            att.setInvertMirror(x, ["tx", "ty", "tz"])

        att.setInvertMirror(self.ik_ctl, ["tx", "ry", "rz"])
        att.setInvertMirror(self.upv_ctl, ["tx"])
        att.setInvertMirror(self.ikRot_ctl, ["ry", "rz"])

        # 1 bone chain Upv ref ===========================
        self.ikHandleUpvRef = pri.addIkHandle(
            self.root,
            self.getName("ikHandleArmChainUpvRef"),
            self.armChainUpvRef,
            "ikSCsolver")
        pm.pointConstraint(self.ik_ctl, self.ikHandleUpvRef)
        pm.parentConstraint(self.armChainUpvRef[0],
                            self.ik_ctl,
                            self.upv_cns,
                            mo=True)

    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):

        self.relatives["root"] = self.loc[0]
        self.jointRelatives["root"] = 0

        self.relatives["elbow"] = self.loc[1]
        self.jointRelatives["elbow"] = 1

        self.relatives["wrist"] = self.loc[2]
        self.jointRelatives["wrist"] = 2

        self.relatives["eff"] = self.loc[2]
        self.jointRelatives["eff"] = 2

    # @param self
    def addConnection(self):
        self.connections["standard"] = self.connect_standard
        self.connections["orientation"] = self.connect_orientation
        self.connections["parent"] = self.connect_parent
        self.connections["ymt_shoulder_01"] = self.connect_ymt_shoulder

    def connect_orientation(self):
        self.connect_orientCns()

    def connect_parent(self):
        self.connect_standardWithSimpleIkRef()

    def connect_standard(self):
        # self.connect_standardWithIkRef()
        """Standard IK Connection

        Standard connection definition with ik and upv references.

        """
        self.parent.addChild(self.root)

        # Set the Ik Reference
        self.connectRef(self.settings["ikrefarray"], self.ik_cns)
        self.connectRef(self.settings["ikrefarray"], self.upv_cns, True)

    def postConnect(self):
        """Post connection actions."""

        # lock parameters
        xform_attrs = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]
        att.lockAttribute(self.fk_cns, xform_attrs)
        att.lockAttribute(self.ik_cns, xform_attrs)
        att.lockAttribute(self.ikRot_cns, xform_attrs)

        # self.fk_cns.setAttr("visibility", False)
        # self.ik_cns.setAttr("visibility", False)
        # self.ikRot_cns.setAttr("visibility", False)
        for npo in self.fk_npo:
            att.lockAttribute(npo, xform_attrs)
            # npo.setAttr("visibility", False)

        for chain in self.chain:
            chain.setAttr("visibility", False)
        att.setKeyableAttributes(self.ikRot_ctl, ["rx", "ry", "rz"])

    def connect_ymt_shoulder(self):
        self.connect_standard()

        # If the parent component hasn't been generated we skip the connection
        if self.parent_comp is None:
            return

        # IK dummy Chain -----------------------------------------
        self.parent_comp.connect_arm(self)

        return
