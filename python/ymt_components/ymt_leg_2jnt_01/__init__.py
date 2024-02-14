"""Component Leg 2 joints 01 module"""

import pymel.core as pm
from pymel.core import datatypes

from mgear.shifter import component
import mgear.shifter_classic_components.leg_2jnt_01 as leg_2jnt_01

from mgear.core import node, fcurve, applyop, vector, icon
from mgear.core import attribute, transform, primitive

#############################################
# COMPONENT
#############################################


class Component(leg_2jnt_01.Component):
    """Shifter component Class"""

    # =====================================================
    # OBJECTS
    # =====================================================
    def addObjects(self):
        """Add all the objects needed to create the component."""

        self.WIP = self.options["mode"]

        self.normal = self.getNormalFromPos(self.guide.apos)

        self.length0 = vector.getDistance(
            self.guide.apos[0], self.guide.apos[1])
        self.length1 = vector.getDistance(
            self.guide.apos[1], self.guide.apos[2])
        self.length2 = vector.getDistance(
            self.guide.apos[2], self.guide.apos[3])

        # 1 bone chain for upv ref
        self.legChainUpvRef = primitive.add2DChain(
            self.root,
            self.getName("legUpvRef%s_jnt"),
            [self.guide.apos[0], self.guide.apos[2]],
            self.normal,
            False,
            self.WIP)

        self.legChainUpvRef[1].setAttr(
            "jointOrientZ",
            self.legChainUpvRef[1].getAttr("jointOrientZ") * -1)

        # extra neutral pose
        t = transform.getTransformFromPos(self.guide.apos[0])

        self.root_npo = primitive.addTransform(self.root,
                                               self.getName("root_npo"),
                                               t)
        self.root_ctl = self.addCtl(self.root_npo,
                                    "root_ctl",
                                    t,
                                    self.color_fk,
                                    "circle",
                                    w=self.length0 / 6,
                                    tp=self.parentCtlTag)

        # FK Controlers -----------------------------------
        t = transform.getTransformLookingAt(self.guide.apos[0],
                                            self.guide.apos[1],
                                            self.normal,
                                            "xz",
                                            self.negate)
        self.fk0_npo = primitive.addTransform(self.root_ctl,
                                              self.getName("fk0_npo"),
                                              t)
        po_vec = datatypes.Vector(.5 * self.length0 * self.n_factor, 0, 0)
        self.fk0_ctl = self.addCtl(self.fk0_npo,
                                   "fk0_ctl",
                                   t,
                                   self.color_fk,
                                   "cube",
                                   w=self.length0,
                                   h=self.size * .1,
                                   d=self.size * .1,
                                   po=po_vec,
                                   tp=self.root_ctl)
        attribute.setKeyableAttributes(
            self.fk0_ctl, ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx"])

        t = transform.getTransformLookingAt(self.guide.apos[1],
                                            self.guide.apos[2],
                                            self.normal,
                                            "xz",
                                            self.negate)

        self.fk1_npo = primitive.addTransform(
            self.fk0_ctl, self.getName("fk1_npo"), t)

        po_vec = datatypes.Vector(.5 * self.length1 * self.n_factor, 0, 0)
        self.fk1_ctl = self.addCtl(self.fk1_npo,
                                   "fk1_ctl",
                                   t,
                                   self.color_fk,
                                   "cube",
                                   w=self.length1,
                                   h=self.size * .1,
                                   d=self.size * .1,
                                   po=po_vec,
                                   tp=self.fk0_ctl)

        attribute.setKeyableAttributes(
            self.fk1_ctl, ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx"])

        t = transform.getTransformLookingAt(self.guide.apos[2],
                                            self.guide.apos[3],
                                            self.normal,
                                            "xz",
                                            self.negate)
        if self.settings["mirrorMid"] and self.negate:
            scl = [1, 1, -1]
        else:
            scl = [1, 1, 1]
        t = transform.setMatrixScale(t, scl)

        self.fk2_npo = primitive.addTransform(
            self.fk1_ctl, self.getName("fk2_npo"), t)

        po_vec = datatypes.Vector(.5 * self.length2 * self.n_factor, 0, 0)
        self.fk2_ctl = self.addCtl(self.fk2_npo,
                                   "fk2_ctl",
                                   t,
                                   self.color_fk,
                                   "cube",
                                   w=self.length2,
                                   h=self.size * .1,
                                   d=self.size * .1,
                                   po=po_vec,
                                   tp=self.fk1_ctl)
        attribute.setKeyableAttributes(self.fk2_ctl)

        self.fk_ctl = [self.fk0_ctl, self.fk1_ctl, self.fk2_ctl]

        for x in self.fk_ctl:
            attribute.setInvertMirror(x, ["tx", "ty", "tz"])

        # IK Controlers -----------------------------------

        self.ik_cns = primitive.addTransformFromPos(self.root_ctl,
                                                    self.getName("ik_cns"),
                                                    self.guide.pos["ankle"])

        self.ikcns_ctl = self.addCtl(
            self.ik_cns,
            "ikcns_ctl",
            transform.getTransformFromPos(self.guide.pos["ankle"]),
            self.color_ik,
            "null",
            w=self.size * .12,
            tp=self.root_ctl)
        attribute.setInvertMirror(self.ikcns_ctl, ["tx"])

        m = transform.getTransformLookingAt(self.guide.pos["ankle"],
                                            self.guide.pos["eff"],
                                            self.x_axis,
                                            "zx",
                                            False)

        self.ik_ctl = self.addCtl(
            self.ikcns_ctl,
            "ik_ctl",
            transform.getTransformFromPos(self.guide.pos["ankle"]),
            self.color_ik,
            "cube",
            w=self.size * .12,
            h=self.size * .12,
            d=self.size * .12)
        if self.settings["mirrorMid"] and self.negate:
                self.ik_cns.sx.set(-1)
                self.ik_ctl.rz.set(self.ik_ctl.rz.get() * -1)
        else:
            attribute.setInvertMirror(self.ik_ctl, ["tx", "ry", "rz"])
        attribute.setKeyableAttributes(self.ik_ctl)
        attribute.setRotOrder(self.ik_ctl, "XZY")
        attribute.setInvertMirror(self.ik_ctl, ["tx", "ry", "rz"])

        # upv
        v = self.guide.apos[2] - self.guide.apos[0]
        v = self.normal ^ v
        v.normalize()
        v *= self.size * .5
        v += self.guide.apos[1]

        self.upv_cns = primitive.addTransformFromPos(self.ik_ctl,
                                                     self.getName("upv_cns"),
                                                     v)

        self.upv_ctl = self.addCtl(
            self.upv_cns,
            "upv_ctl",
            transform.getTransform(self.upv_cns),
            self.color_ik,
            "diamond",
            w=self.size * .12,
            tp=self.root_ctl)

        self.add_controller_tag(self.ik_ctl, self.upv_ctl)
        if self.settings["mirrorMid"]:
            if self.negate:
                self.upv_cns.rz.set(180)
                self.upv_cns.sy.set(-1)
        else:
            attribute.setInvertMirror(self.upv_ctl, ["tx"])
        attribute.setKeyableAttributes(self.upv_ctl, self.t_params)

        # References --------------------------------------
        self.ik_ref = primitive.addTransform(
            self.ik_ctl,
            self.getName("ik_ref"),
            transform.getTransform(self.ik_ctl))
        self.fk_ref = primitive.addTransform(
            self.fk_ctl[2],
            self.getName("fk_ref"),
            transform.getTransform(self.ik_ctl))

        # Chain --------------------------------------------
        # The outputs of the ikfk2bone solver
        self.bone0 = primitive.addLocator(
            self.root_ctl,
            self.getName("0_bone"),
            transform.getTransform(self.fk_ctl[0]))

        self.bone0_shp = self.bone0.getShape()
        self.bone0_shp.setAttr("localPositionX", self.n_factor * .5)
        self.bone0_shp.setAttr("localScale", .5, 0, 0)
        self.bone0.setAttr("sx", self.length0)
        self.bone0.setAttr("visibility", False)

        self.bone1 = primitive.addLocator(
            self.root_ctl,
            self.getName("1_bone"),
            transform.getTransform(self.fk_ctl[1]))
        self.bone1_shp = self.bone1.getShape()
        self.bone1_shp.setAttr("localPositionX", self.n_factor * .5)
        self.bone1_shp.setAttr("localScale", .5, 0, 0)
        self.bone1.setAttr("sx", self.length1)
        self.bone1.setAttr("visibility", False)

        self.ctrn_loc = primitive.addTransformFromPos(self.root_ctl,
                                                      self.getName("ctrn_loc"),
                                                      self.guide.apos[1])
        self.eff_loc = primitive.addTransformFromPos(self.root_ctl,
                                                     self.getName("eff_loc"),
                                                     self.guide.apos[2])

        # tws_ref
        t = transform.getRotationFromAxis(
            datatypes.Vector(0, -1, 0), self.normal, "xz", self.negate)
        t = transform.setMatrixPosition(t, self.guide.pos["ankle"])

        # addind an npo parent transform to fix flip in Maya 2018.2
        self.tws_npo = primitive.addTransform(
            self.eff_loc, self.getName("tws_npo"), t)

        self.tws_ref = primitive.addTransform(
            self.tws_npo, self.getName("tws_ref"), t)

        # Mid Controler ------------------------------------
        t = transform.getTransform(self.ctrn_loc)
        self.mid_cns = primitive.addTransform(
            self.ctrn_loc, self.getName("mid_cns"), t)
        self.mid_ctl = self.addCtl(self.mid_cns,
                                   "mid_ctl",
                                   t,
                                   self.color_ik,
                                   "sphere",
                                   w=self.size * .2,
                                   tp=self.root_ctl)

        attribute.setKeyableAttributes(self.mid_ctl,
                                       params=["tx", "ty", "tz",
                                               "ro", "rx", "ry", "rz",
                                               "sx"])

        if self.settings["mirrorMid"]:
            if self.negate:
                self.mid_cns.rz.set(180)
                self.mid_cns.sz.set(-1)
        else:
            attribute.setInvertMirror(self.mid_ctl, ["tx", "ty", "tz"])

        # Twist references ---------------------------------
        x = datatypes.Vector(0, -1, 0)
        x = x * transform.getTransform(self.eff_loc)
        z = datatypes.Vector(self.normal.x, self.normal.y, self.normal.z)
        z = z * transform.getTransform(self.eff_loc)

        m = transform.getRotationFromAxis(x, z, "xz", self.negate)
        m = transform.setMatrixPosition(
            m, transform.getTranslation(self.ik_ctl))

        self.rollRef = primitive.add2DChain(self.root,
                                            self.getName("rollChain"),
                                            self.guide.apos[:2],
                                            self.normal,
                                            self.negate,
                                            self.WIP)

        self.tws0_loc = primitive.addTransform(
            self.rollRef[0],
            self.getName("tws0_loc"),
            transform.getTransform(self.fk_ctl[0]))

        self.tws0_rot = primitive.addTransform(
            self.tws0_loc,
            self.getName("tws0_rot"),
            transform.getTransform(self.fk_ctl[0]))

        self.tws1_loc = primitive.addTransform(
            self.ctrn_loc,
            self.getName("tws1_loc"),
            transform.getTransform(self.ctrn_loc))

        self.tws1_rot = primitive.addTransform(
            self.tws1_loc,
            self.getName("tws1_rot"),
            transform.getTransform(self.ctrn_loc))

        self.tws2_loc = primitive.addTransform(
            self.root_ctl,
            self.getName("tws2_loc"),
            transform.getTransform(self.tws_ref))

        self.tws2_rot = primitive.addTransform(
            self.tws2_loc,
            self.getName("tws2_rot"),
            transform.getTransform(self.tws_ref))

        self.tws2_rot.setAttr("sx", .001)

        # Divisions ----------------------------------------
        # We have at least one division at the start, the end and one for
        # the elbow. + 2 for knee angle control
        if self.settings["supportJoints"]:
            ej = 2
        else:
            ej = 0

        self.divisions = self.settings["div0"] + self.settings["div1"] + 3 + ej

        self.div_cns = []

        if self.settings["extraTweak"]:
            tagP = self.parentCtlTag
            self.tweak_ctl = []

        for i in range(self.divisions):

            div_cns = primitive.addTransform(self.root_ctl,
                                             self.getName("div%s_loc" % i))

            self.div_cns.append(div_cns)

            if self.settings["extraTweak"]:
                t = transform.getTransform(div_cns)
                tweak_ctl = self.addCtl(div_cns,
                                        "tweak%s_ctl" % i,
                                        t,
                                        self.color_fk,
                                        "square",
                                        w=self.size * .15,
                                        d=self.size * .15,
                                        ro=datatypes.Vector([0, 0, 1.5708]),
                                        tp=tagP)
                attribute.setKeyableAttributes(tweak_ctl)

                tagP = tweak_ctl
                self.tweak_ctl.append(tweak_ctl)
                self.jnt_pos.append([tweak_ctl, i, None, False])
            else:
                self.jnt_pos.append([div_cns, i])

        # End reference ------------------------------------
        # To help the deformation on the ankle
        self.end_ref = primitive.addTransform(self.tws2_rot,
                                              self.getName("end_ref"), m)
        self.jnt_pos.append([self.end_ref, 'end'])

        # match IK FK references
        self.match_fk0_off = self.add_match_ref(self.fk_ctl[1],
                                                self.root,
                                                "matchFk0_npo",
                                                False)

        self.match_fk0 = self.add_match_ref(self.fk_ctl[0],
                                            self.match_fk0_off,
                                            "fk0_mth")

        self.match_fk1_off = self.add_match_ref(self.fk_ctl[2],
                                                self.root,
                                                "matchFk1_npo",
                                                False)

        self.match_fk1 = self.add_match_ref(self.fk_ctl[1],
                                            self.match_fk1_off,
                                            "fk1_mth")

        self.match_fk2 = self.add_match_ref(self.fk_ctl[2],
                                            self.ik_ctl,
                                            "fk2_mth")

        self.match_ik = self.add_match_ref(self.ik_ctl,
                                           self.fk2_ctl,
                                           "ik_mth")

        self.match_ikUpv = self.add_match_ref(self.upv_ctl,
                                              self.fk0_ctl,
                                              "upv_mth")

        # add visual reference
        self.line_ref = icon.connection_display_curve(
            self.getName("visalRef"), [self.upv_ctl, self.mid_ctl])
