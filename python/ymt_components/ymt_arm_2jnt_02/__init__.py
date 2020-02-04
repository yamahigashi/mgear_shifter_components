##########################################################
# GLOBAL
##########################################################

# Maya
import pymel.core as pm

# import maya.OpenMaya as om

# mgear
import mgear.shifter_classic_components.arm_2jnt_04 as arm_2jnt_04

import mgear.core.primitive as pri
import mgear.core.transform as tra


##########################################################
# COMPONENT
##########################################################
class Component(arm_2jnt_04.Component):

    def addObjects(self):
        super(Component, self).addObjects()
        t = tra.getTransform(self.root)
        self.fk0_cns = pri.addTransform(self.root,
                                        self.getName("fk0_cns"),
                                        t)
        self.fk0_cns.addChild(self.fk0_npo)

    def addAttributes(self):
        super(Component, self).addAttributes()

        ref_names = self.get_valid_alias_list(self.settings.get("fkrefarray", "").split(","))
        ref_names.insert(0, "self")
        if not self.settings["fkrefarray"]:
            self.fkref_att = self.addAnimEnumParam("fkref", "Fk Ref", 0, ref_names)
        else:
            self.fkref_att = self.addAnimEnumParam("fkref", "Fk Ref", 1, ref_names)

    def addConnection(self):
        self.connections["standard"] = self.connect_standard
        self.connections["ymt_shoulder_01"] = self.connect_ymt_shoulder

    def connect_standard(self):
        """standard connection definition for the component"""

        if self.settings["ikTR"]:
            self.parent.addChild(self.root)
            self.connectRef(self.settings["ikrefarray"], self.ik_cns)
            self.connectRef(self.settings["upvrefarray"], self.upv_cns, True)

            init_refNames = ["lower_arm", "ik_ctl"]
            self.connectRef2(self.settings["ikrefarray"],
                             self.ikRot_cns,
                             self.ikRotRef_att,
                             [self.ikRot_npo, self.ik_ctl],
                             True,
                             init_refNames)
        else:
            self.connect_standardWithIkRef()

        if self.settings["pinrefarray"]:
            self.connectRef2(self.settings["pinrefarray"],
                             self.mid_cns,
                             self.pin_att,
                             [self.ctrn_loc],
                             False,
                             ["Auto"])

    def connect_ymt_shoulder(self):
        self.connect_standard()

        # If the parent component hasn't been generated we skip the connection
        if self.parent_comp is None:
            return

        # IK dummy Chain -----------------------------------------
        self.parent_comp.connect_arm(self)

        return

    def postConnect(self):

        fk_ref_cond = pm.createNode("condition")
        pm.connectAttr(self.fkref_att, "{}.firstTerm".format(fk_ref_cond))
        pm.setAttr("{}.secondTerm".format(fk_ref_cond), 0)
        pm.setAttr("{}.operation".format(fk_ref_cond), 0)
        pm.setAttr("{}.colorIfTrueR".format(fk_ref_cond), 0)
        pm.setAttr("{}.colorIfTrueG".format(fk_ref_cond), 0)
        pm.setAttr("{}.colorIfTrueB".format(fk_ref_cond), 0)
        pm.setAttr("{}.colorIfFalseR".format(fk_ref_cond), 0)
        pm.setAttr("{}.colorIfFalseG".format(fk_ref_cond), 0)
        pm.setAttr("{}.colorIfFalseB".format(fk_ref_cond), 0)

        pm.connectAttr("{}.outColorR".format(fk_ref_cond), "{}.rotateX".format(self.fk0_cns))
        pm.connectAttr("{}.outColorG".format(fk_ref_cond), "{}.rotateY".format(self.fk0_cns))
        pm.connectAttr("{}.outColorB".format(fk_ref_cond), "{}.rotateZ".format(self.fk0_cns))

        if self.settings["fkrefarray"]:

            ref_names = self.settings["fkrefarray"].split(",")
            for i, ref_name in enumerate(ref_names):

                _head_ref_cond = pm.createNode("condition")
                pm.connectAttr("{}.outColorR".format(_head_ref_cond), "{}.colorIfFalseR".format(fk_ref_cond))
                pm.connectAttr("{}.outColorG".format(_head_ref_cond), "{}.colorIfFalseG".format(fk_ref_cond))
                pm.connectAttr("{}.outColorB".format(_head_ref_cond), "{}.colorIfFalseB".format(fk_ref_cond))
                fk_ref_cond = _head_ref_cond

                pm.connectAttr(self.fkref_att, "{}.firstTerm".format(_head_ref_cond))
                pm.setAttr("{}.secondTerm".format(_head_ref_cond), i + 1)
                pm.setAttr("{}.operation".format(_head_ref_cond), 0)

                src = self.rig.findRelative(ref_name)

                down, _, up = findPathAtoB(src, self.root)
                mult = pm.createNode("multMatrix")

                for i, d in enumerate(down):
                    pm.connectAttr("{}.matrix".format(d), "{}.matrixIn[{}]".format(mult, i))

                for j, u in enumerate(up):
                    pm.connectAttr("{}.inverseMatrix".format(u), "{}.matrixIn[{}]".format(mult, i + j + 1))

                decomp = pm.createNode("decomposeMatrix")
                pm.connectAttr("{}.matrixSum".format(mult), "{}.inputMatrix".format(decomp))
                pm.connectAttr("{}.outputRotateX".format(decomp), "{}.colorIfTrueR".format(fk_ref_cond))
                pm.connectAttr("{}.outputRotateY".format(decomp), "{}.colorIfTrueG".format(fk_ref_cond))
                pm.connectAttr("{}.outputRotateZ".format(decomp), "{}.colorIfTrueB".format(fk_ref_cond))


# TODO: extract to common logic
def getFullPath(start, routes=None):
    # type: (pm.nt.transform, List[pm.nt.transform]) -> List[pm.nt.transform]
    if not routes:
        routes = []

    if not start.getParent():
        return routes

    else:
        return getFullPath(start.getParent(), routes + [start, ])


def findPathAtoB(a, b):
    # type: (pm.nt.transform, pm.nt.transform) -> Tuple[List[pm.nt.transform], pm.nt.transform, List[pm.nt.transform]]
    """Returns route of A to B in formed Tuple[down(to root), turning point, up(to leaf)]"""
    # aPath = ["x", "a", "b", "c"]
    # bPath = ["b", "c"]
    # down [x, a]
    # turn b
    # up []

    aPath = getFullPath(a)
    bPath = getFullPath(b)

    return _findPathAtoB(aPath, bPath)


def _findPathAtoB(aPath, bPath):
    # type: (List, List) -> Tuple[List, Any, List]
    """Returns route of A to B in formed Tuple[down(to root), turning point, up(to leaf)]

    >>> aPath = ["x", "a", "b", "c"]
    >>> bPath = ["b", "c"]
    >>> d, c, u = _findPathAtoB(aPath, bPath)
    >>> d == ["x", "a"]
    True
    >>> c == "b"
    True
    >>> u == []
    True

    """
    down = []
    up = []
    sharedNode = None

    for u in aPath:
        if u in bPath:
            sharedNode = u
            break

        down.append(u)

    idx = bPath.index(sharedNode)
    up = list(reversed(bPath[:(idx)]))

    return down, sharedNode, up
