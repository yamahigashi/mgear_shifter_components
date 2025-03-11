import textwrap

import maya.cmds as cmds
import maya.api.OpenMaya as om2
try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm
import pymel.core.datatypes as dt


# mgear
import mgear
from mgear.shifter.component import MainComponent

import mgear.core.primitive as pri
import mgear.core.transform as tra
import mgear.core.attribute as att
import mgear.core.vector as vec


if False:
    # For type annotation
    from typing import Module, Dict, List, Tuple, Pattern, Callable, Any, Text, Optional  # type: ignore  # NOQA


EXPRESPY_NODE_ID = om2.MTypeId(0x00070004)


##########################################################
# COMPONENT
##########################################################
class Component(MainComponent):

    # Add all the objects needed to create the component.
    # @param self
    def addObjects(self):

        self.normal = self.guide.blades["blade"].z * -1.

        # Ik Controlers ------------------------------------
        t = tra.getTransform(self.root)
        t = tra.setMatrixPosition(t, self.guide.pos["neck"])
        self.neck_cns = pri.addTransform(self.root, self.getName("neck_cns"), t)

        t = tra.getTransformLookingAt(self.guide.pos["neck"], self.guide.pos["eff0"], self.normal, "yx", self.negate)
        t = tra.setMatrixPosition(t, self.guide.pos["neck"])
        self.neck_npo = pri.addTransform(self.neck_cns, self.getName("neck_npo"), t)
        self.neck_off = pri.addTransform(self.neck_npo, self.getName("neck_off"), t)

        # Size
        dist = vec.getDistance(self.guide.pos["head"], self.guide.pos["eff1"])
        w = self.size * 0.5
        h = dist
        d = self.size * 0.5
        po = dt.Vector(0, dist * 0.5, 0)

        # for compatibility reason, this name is not neck_ctl, but ik_ctl
        self.neck_ctl = self.addCtl(self.neck_off, "ik_ctl", t, self.color_fk, "cube", w=w, h=h, d=d, po=po)
        att.setKeyableAttributes(self.neck_ctl)
        att.setRotOrder(self.neck_ctl, "ZXY")
        self.jnt_pos.append([self.neck_ctl, 0])

        t = tra.getTransformLookingAt(self.guide.pos["head"], self.guide.pos["eff1"], self.normal, "yx", self.negate)
        self.head_pos_ref = pri.addTransform(self.neck_ctl, self.getName("head_pos_ref"), t)

        # TODO: Division -----------------------------------------

        # Head ---------------------------------------------
        t = tra.getTransform(self.root)
        t = tra.setMatrixPosition(t, self.guide.pos["head"])
        self.head_cns = pri.addTransform(self.root, self.getName("head_cns"), t)

        t = tra.getTransformLookingAt(self.guide.pos["head"], self.guide.pos["eff1"], self.normal, "yx", self.negate)
        self.head_npo = pri.addTransform(self.head_cns, self.getName("head_npo"), t)
        self.head_off = pri.addTransform(self.head_npo, self.getName("head_off"), t)

        self.head_ctl = self.addCtl(self.head_off, "head_ctl", t, self.color_ik, "compas", w=w, h=h, d=d, po=po)
        att.setRotOrder(self.head_ctl, "ZXY")
        att.setInvertMirror(self.neck_ctl, ["tx", "ry", "rz"])
        att.setInvertMirror(self.head_ctl, ["tx", "ry", "rz"])

        if self.settings["headFk"]:
            self.head_fk = self.addCtl(self.head_ctl, "head_fk", t, self.color_fk, "cube", w=w, h=h, d=d, po=po)
            self.jnt_pos.append([self.head_fk, "head"])
        else:
            self.jnt_pos.append([self.head_ctl, "head"])

    # =====================================================
    # PROPERTY
    # =====================================================
    # Add parameters to the anim and setup properties to control the component.
    # @param self
    def addAttributes(self):
        # Anim -------------------------------------------
        ref_names = ["self", "head"]
        self.neckref_att = self.addAnimEnumParam("neck_ref", "Neck Ref", 1, ref_names)
        self.neckrate_att = self.addAnimParam("neck_rate", "Neck Rate", "double", 0.5, 0, 1)  # TODO: setting

        if self.settings["headrefarray"]:
            ref_names = self.settings["headrefarray"].split(",")
            ref_names.insert(0, "self")
            self.headref_att = self.addAnimEnumParam("headref", "Head Ref", 1, ref_names)
        else:
            self.headref_att = self.addAnimEnumParam("headref", "Head Ref", 0, ["self"])

    # =====================================================
    # OPERATORS
    # =====================================================
    # Apply operators, constraints, expressions to the hierarchy.\n
    # In order to keep the code clean and easier to debug,
    # we shouldn't create any new object in this method.
    # @param self
    def addOperators(self):
        pass

    # =====================================================
    # CONNECTOR
    # =====================================================
    # Set the relation beetween object from guide to rig.\n
    # @param self
    def setRelation(self):
        self.relatives["root"] = self.root
        self.relatives["eff0"] = self.root
        self.relatives["tan2"] = self.head_ctl
        self.relatives["neck"] = self.neck_ctl
        self.relatives["head"] = self.head_ctl
        self.relatives["eff1"] = self.head_ctl

        self.jointRelatives["root"] = 0
        self.jointRelatives["eff0"] = 0
        self.jointRelatives["tan2"] = len(self.jnt_pos) - 1
        self.jointRelatives["neck"] = len(self.jnt_pos) - 1
        self.jointRelatives["head"] = len(self.jnt_pos) - 1
        self.jointRelatives["eff1"] = len(self.jnt_pos) - 1

    def connect_standard(self):

        self.parent.addChild(self.root)

        # TODO: by settings gui
        print(self.settings)
        if self.settings["useExprespy"]:
            try:
                self.connect_with_exprespy()
            except Exception:
                print("exprespy failed")
        else:
            self.connect_with_nodespaghetti()

    def connect_with_exprespy(self):
        if not cmds.pluginInfo("exprespy", q=True, loaded=True):
            cmds.loadPlugin("exprespy.mll", quiet=True)
            mgear.log("load plugin exprespy.mll")

        exprespy_template = textwrap.dedent("""
            import maya.api.OpenMaya as om

            neck_ref = {self.neckref_att}    # 0: self, 1: head
            head_ref = {self.headref_att}    # 0: self, (1: body, 2: local etc...)

            neck_base_pos = {self.neck_cns}.translate  # FIXME: CONSTANT
            head_ref_pos = {self.head_pos_ref}.translate  # FIXME: CONSTANT

            res_head_rot = om.MEulerRotation()
            res_neck_rot = om.MEulerRotation()
            res_head_pos = head_ref_pos

            if head_ref == 0:
                res_head_rot.setValue({self.neck_ctl}.rotate, {self.neck_ctl}.rotateOrder)
                m = api.MMatrix()
        """.format(**locals()))

        exprespy_head_ref_switch_template = textwrap.dedent("""
            elif head_ref == {i}:
                # {ref_name}
                m = {mat_formula}

                res_head_rot = api.MTransformationMatrix(m).rotation(False)
        """)

        exprespy_head_result_assignment_template = textwrap.dedent("""
            if neck_ref == 0:
                tmp = om.MTransformationMatrix()
                tmp.setTranslation(neck_base_pos, om.MSpace.kObject)
                tmp2 = om.MTransformationMatrix(tmp.asMatrixInverse() * {self.neck_npo}.inverseMatrix * {self.neck_ctl}.inverseMatrix * {self.head_pos_ref}.inverseMatrix )
                res_head_pos = tmp2.translation(om.MSpace.kObject) * -1.
            else:
                neck_quat = api.MTransformationMatrix({self.head_ctl}.matrix * m).rotation(True)
                identity = api.MQuaternion()
                res_neck_rot = api.MQuaternion.slerp(identity, neck_quat, {self.neckrate_att}).asEulerRotation()

                tmp = om.MTransformationMatrix()
                tmp.setTranslation(neck_base_pos, om.MSpace.kObject)
                tmp.setRotation(res_neck_rot)
                tmp2 = om.MTransformationMatrix(tmp.asMatrixInverse() * {self.neck_npo}.inverseMatrix * {self.neck_ctl}.inverseMatrix * {self.head_pos_ref}.inverseMatrix )
                res_head_pos = tmp2.translation(om.MSpace.kObject) * -1.

            res_head_rot.reorderIt({self.head_cns}.rotateOrder)
            {self.neck_cns}.rotate = res_neck_rot
            {self.head_cns}.translate = res_head_pos
            {self.head_cns}.rotate = res_head_rot
        """)

        exprespy_code = exprespy_template

        if self.settings["headrefarray"]:
            ref_names = self.settings["headrefarray"].split(",")
            for i, ref_name in enumerate(ref_names):
                src = self.rig.findRelative(ref_name)

                down, _, up = findPathAtoB(src, self.root)
                down_mat = " * ".join(["{}.matrix".format(x.name()) for x in down])
                up_mat = " * ".join(["{}.inverseMatrix".format(x.name()) for x in up])
                if down:
                    mat = "{} * {}".format(down_mat, up_mat)
                else:
                    mat = "{}".format(up_mat)

                interpoleted = exprespy_head_ref_switch_template.format(**{
                    "i": i + 1,
                    "ref_name": ref_name,
                    "mat_formula": mat,
                })
                exprespy_code += interpoleted

        exprespy_code += exprespy_head_result_assignment_template.format(**locals())

        exprespy_node = om2.MFnDependencyNode()
        name = self.getName("exprespy_node")
        exprespy_node = exprespy_node.create(EXPRESPY_NODE_ID, name)
        exprespy_node = om2.MFnDependencyNode(exprespy_node)
        self.exprespy_node_name = exprespy_node.name()
        cmds.setAttr("{}.code".format(self.exprespy_node_name), exprespy_code, type="string")
        import exprespy.cmd
        exprespy.cmd.setCode(self.exprespy_node_name, exprespy_code, raw=False)

    def connect_with_nodespaghetti(self):

        # Head position
        mult = pm.createNode("multMatrix")
        pm.connectAttr("{}.matrix".format(self.head_pos_ref), "{}.matrixIn[0]".format(mult))
        pm.connectAttr("{}.matrix".format(self.neck_ctl), "{}.matrixIn[1]".format(mult))
        pm.setAttr("{}.matrixIn[2]".format(mult), *cmds.getAttr("{}.matrix".format(self.neck_npo)), type="matrix")
        pm.setAttr("{}.matrixIn[3]".format(mult), *cmds.getAttr("{}.matrix".format(self.neck_cns)), type="matrix")
        decomp = pm.createNode("decomposeMatrix")
        pm.connectAttr("{}.matrixSum".format(mult), "{}.inputMatrix".format(decomp))
        # pm.connectAttr("{}.outputTranslate".format(decomp), "{}.translate".format(self.head_cns))

        neck_ref_cond_pos = pm.createNode("condition")
        pm.connectAttr(self.neckref_att, "{}.firstTerm".format(neck_ref_cond_pos))
        pm.setAttr("{}.secondTerm".format(neck_ref_cond_pos), 0)
        pm.setAttr("{}.operation".format(neck_ref_cond_pos), 0)
        pm.connectAttr("{}.outputTranslate".format(decomp), "{}.colorIfTrue".format(neck_ref_cond_pos))
        pm.connectAttr("{}.outColor".format(neck_ref_cond_pos), "{}.translate".format(self.head_off))

        # Head ref switch
        head_ref_cond = pm.createNode("condition")
        pm.connectAttr(self.headref_att, "{}.firstTerm".format(head_ref_cond))
        pm.setAttr("{}.secondTerm".format(head_ref_cond), 0)
        pm.setAttr("{}.operation".format(head_ref_cond), 0)
        pm.setAttr("{}.colorIfTrueR".format(head_ref_cond), 0)
        pm.setAttr("{}.colorIfTrueG".format(head_ref_cond), 0)
        pm.setAttr("{}.colorIfTrueB".format(head_ref_cond), 0)
        pm.setAttr("{}.colorIfFalseR".format(head_ref_cond), 0)
        pm.setAttr("{}.colorIfFalseG".format(head_ref_cond), 0)
        pm.setAttr("{}.colorIfFalseB".format(head_ref_cond), 0)

        pm.connectAttr("{}.outColorR".format(head_ref_cond), "{}.rotateX".format(self.head_cns))
        pm.connectAttr("{}.outColorG".format(head_ref_cond), "{}.rotateY".format(self.head_cns))
        pm.connectAttr("{}.outColorB".format(head_ref_cond), "{}.rotateZ".format(self.head_cns))

        # Neck rotation
        neck_ref_cond = pm.createNode("condition")
        pm.connectAttr(self.neckref_att, "{}.firstTerm".format(neck_ref_cond))
        pm.setAttr("{}.secondTerm".format(neck_ref_cond), 0)
        pm.setAttr("{}.operation".format(neck_ref_cond), 0)
        pm.setAttr("{}.colorIfTrueR".format(neck_ref_cond), 0)
        pm.setAttr("{}.colorIfTrueG".format(neck_ref_cond), 0)
        pm.setAttr("{}.colorIfTrueB".format(neck_ref_cond), 0)

        mult = pm.createNode("multMatrix")
        comp = pm.createNode("composeMatrix")
        comp_off = pm.createNode("composeMatrix")
        inv_off = pm.createNode("inverseMatrix")
        pm.connectAttr("{}.outColorR".format(head_ref_cond),     "{}.inputRotateX".format(comp))
        pm.connectAttr("{}.outColorG".format(head_ref_cond),     "{}.inputRotateY".format(comp))
        pm.connectAttr("{}.outColorB".format(head_ref_cond),     "{}.inputRotateZ".format(comp))
        pm.connectAttr("{}.matrix".format(self.head_ctl),        "{}.matrixIn[0]".format(mult))
        pm.connectAttr("{}.matrix".format(self.head_npo),        "{}.matrixIn[1]".format(mult))
        pm.connectAttr("{}.inverseMatrix".format(self.neck_npo), "{}.matrixIn[2]".format(mult))
        pm.connectAttr("{}.outputMatrix".format(comp),           "{}.matrixIn[3]".format(mult))
        pm.connectAttr("{}.outputMatrix".format(comp_off),       "{}.inputMatrix".format(inv_off))
        pm.connectAttr("{}.outputMatrix".format(inv_off),        "{}.matrixIn[4]".format(mult))
        pm.connectAttr("{}.outputMatrix".format(inv_off),        "{}.matrixIn[5]".format(mult))

        toQuat = pm.createNode("eulerToQuat")
        decomp = pm.createNode("decomposeMatrix")
        pm.connectAttr("{}.matrixSum".format(mult), "{}.inputMatrix".format(decomp))
        pm.connectAttr("{}.outputRotate".format(decomp), "{}.inputRotate".format(toQuat))

        slerp = pm.createNode("quatSlerp")
        pm.connectAttr("{}.outputQuat".format(toQuat), "{}.input1Quat".format(slerp))
        pm.connectAttr(self.neckrate_att, "{}.inputT".format(slerp))
        pm.setAttr("{}.input2QuatX".format(slerp), 0.)
        pm.setAttr("{}.input2QuatY".format(slerp), 0.)
        pm.setAttr("{}.input2QuatZ".format(slerp), 0.)
        pm.setAttr("{}.input2QuatW".format(slerp), 1.)

        toEul = pm.createNode("quatToEuler")
        pm.connectAttr("{}.outputQuat".format(slerp), "{}.inputQuat".format(toEul))
        pm.connectAttr("{}.outputRotateX".format(toEul), "{}.colorIfFalseR".format(neck_ref_cond))
        pm.connectAttr("{}.outputRotateY".format(toEul), "{}.colorIfFalseG".format(neck_ref_cond))
        pm.connectAttr("{}.outputRotateZ".format(toEul), "{}.colorIfFalseB".format(neck_ref_cond))

        pm.connectAttr("{}.outColor".format(neck_ref_cond), "{}.rotate".format(self.neck_off))

        # Head pos2
        comp = pm.createNode("composeMatrix")
        pm.connectAttr("{}.outputQuat".format(slerp), "{}.inputQuat".format(comp))
        pm.setAttr("{}.useEulerRotation".format(comp), False)
        pm.setAttr("{}.inputTranslateX".format(comp), cmds.getAttr("{}.translateX".format(self.neck_cns)))
        pm.setAttr("{}.inputTranslateY".format(comp), cmds.getAttr("{}.translateY".format(self.neck_cns)))
        pm.setAttr("{}.inputTranslateZ".format(comp), cmds.getAttr("{}.translateZ".format(self.neck_cns)))

        mult = pm.createNode("multMatrix")
        pm.connectAttr("{}.matrix".format(self.head_pos_ref),    "{}.matrixIn[0]".format(mult))
        pm.connectAttr("{}.matrix".format(self.neck_ctl),        "{}.matrixIn[1]".format(mult))
        pm.connectAttr("{}.outputMatrix".format(comp),           "{}.matrixIn[2]".format(mult))
        pm.connectAttr("{}.matrix".format(self.neck_npo),        "{}.matrixIn[3]".format(mult))
        pm.connectAttr("{}.inverseMatrix".format(self.head_cns), "{}.matrixIn[4]".format(mult))
        pm.connectAttr("{}.inverseMatrix".format(self.head_npo), "{}.matrixIn[5]".format(mult))

        decomp = pm.createNode("decomposeMatrix")
        pm.connectAttr("{}.matrixSum".format(mult), "{}.inputMatrix".format(decomp))

        pm.connectAttr("{}.outputTranslate".format(decomp), "{}.colorIfFalse".format(neck_ref_cond_pos))

        if self.settings["headrefarray"]:

            ref_names = self.settings["headrefarray"].split(",")
            for i, ref_name in enumerate(ref_names):

                _head_ref_cond = pm.createNode("condition")
                pm.connectAttr("{}.outColorR".format(_head_ref_cond), "{}.colorIfFalseR".format(head_ref_cond))
                pm.connectAttr("{}.outColorG".format(_head_ref_cond), "{}.colorIfFalseG".format(head_ref_cond))
                pm.connectAttr("{}.outColorB".format(_head_ref_cond), "{}.colorIfFalseB".format(head_ref_cond))
                head_ref_cond = _head_ref_cond

                pm.connectAttr(self.headref_att, "{}.firstTerm".format(_head_ref_cond))
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
                pm.connectAttr("{}.outputRotateX".format(decomp), "{}.colorIfTrueR".format(head_ref_cond))
                pm.connectAttr("{}.outputRotateY".format(decomp), "{}.colorIfTrueG".format(head_ref_cond))
                pm.connectAttr("{}.outputRotateZ".format(decomp), "{}.colorIfTrueB".format(head_ref_cond))

        pm.setAttr("{}.inputRotateX".format(comp_off), cmds.getAttr("{}.rx".format(self.neck_off)))
        pm.setAttr("{}.inputRotateY".format(comp_off), cmds.getAttr("{}.ry".format(self.neck_off)))
        pm.setAttr("{}.inputRotateZ".format(comp_off), cmds.getAttr("{}.rz".format(self.neck_off)))


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
