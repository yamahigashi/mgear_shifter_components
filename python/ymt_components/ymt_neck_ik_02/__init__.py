import sys
import six
import textwrap

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import pymel.core as pm
import pymel.core.datatypes as dt


# mgear
import mgear
from mgear.shifter.component import MainComponent

import mgear.core.primitive as pri
import mgear.core.transform as tra
import mgear.core.attribute as att
import mgear.core.vector as vec

if sys.version_info >= (3, 0):  # pylint: disable=using-constant-test
    # For type annotation
    from typing import Optional, Dict, List, Tuple, Pattern, Callable, Any, Text  # NOQA
    import pathlib  # noqa


EXPRESPY_NODE_ID = om2.MTypeId(0x00070004)  # type: ignore


##########################################################
# COMPONENT
##########################################################
class Component(MainComponent):

    def addNeckBones(self, positions, upv0, upv1):

        root_t = tra.getTransform(self.root)
        neck_t = tra.getTransformLookingAt(positions[0], upv0, self.normal, "yx", self.negate)
        head_t = tra.getTransformLookingAt(positions[-1], upv1, self.normal, "yx", self.negate)
        head_pos = positions[-1]

        self.neck_cnss = []
        self.neck_ctls = []
        self.neck_npos = []
        self.neck_refs = []

        for i, pos in enumerate(positions[:-1]):

            t = tra.setMatrixPosition(root_t, pos)
            cns = pri.addTransform(self.root, self.getName("neck{}_cns".format(i)), t)

            t = tra.setMatrixPosition(neck_t, pos)
            npo = pri.addTransform(cns, self.getName("neck{}_npo".format(i)), t)

            w = self.size * 0.5
            ctl = self.addCtl(npo, "fk{}_ctl".format(i), t, self.color_ik, "cube", w=w)
            att.setKeyableAttributes(ctl)
            att.setRotOrder(ctl, "ZXY")
            att.setInvertMirror(ctl, ["tx", "ry", "rz"])

            if i < len(positions) - 2:
                next_t = tra.setMatrixPosition(neck_t, positions[i + 1])
                pos_ref = pri.addTransform(ctl, self.getName("pos{}_ref".format(i)), next_t)
            else:
                pos_ref = pri.addTransform(ctl, self.getName("pos{}_ref".format(i)), head_t)

            self.jnt_pos.append([ctl, i])
            self.neck_cnss.append(cns)
            self.neck_ctls.append(ctl)
            self.neck_npos.append(npo)
            self.neck_refs.append(pos_ref)

        t = tra.getTransformLookingAt(head_pos, upv1, self.normal, "yx", self.negate)
        self.head_pos_ref = pri.addTransform(self.neck_ctls[-1], self.getName("head_pos_ref"), t)

    # Add all the objects needed to create the component.
    # @param self
    def addObjects(self):

        self.normal = self.guide.blades["blade"].z * -1.

        tan_pos = self.guide.apos[1]
        eff0_pos = self.guide.apos[2]
        eff1_pos = self.guide.apos[3]
        neck_pos = self.guide.apos[4]
        head_pos = self.guide.apos[-1]
        jnts_pos = self.guide.apos[4:]

        self.division = len(jnts_pos)
        self.addNeckBones(jnts_pos, eff0_pos, eff1_pos)

        # Head ---------------------------------------------
        t = tra.getTransform(self.root)
        t = tra.setMatrixPosition(t, head_pos)
        self.head_cns = pri.addTransform(self.root, self.getName("head_cns"), t)

        t = tra.getTransformLookingAt(head_pos, eff1_pos, self.normal, "yx", self.negate)
        self.head_npo = pri.addTransform(self.head_cns, self.getName("head_npo"), t)

        dist = vec.getDistance(head_pos, eff1_pos)
        w = self.size * 0.5
        h = dist
        d = self.size * 0.5
        po = dt.Vector(0, dist * 0.5, 0)

        self.head_ctl = self.addCtl(self.head_npo, "head_ctl", t, self.color_fk, "compas", w=w, h=h, d=d, po=po)
        att.setRotOrder(self.head_ctl, "ZXY")
        att.setInvertMirror(self.head_ctl, ["tx", "ry", "rz"])

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

        self.relatives["head"] = self.head_ctl
        self.relatives["eff1"] = self.head_ctl

        self.jointRelatives["root"] = 0
        self.jointRelatives["eff0"] = 0
        self.jointRelatives["tan2"] = len(self.jnt_pos) - 1
        self.jointRelatives["neck"] = len(self.jnt_pos) - 1
        self.jointRelatives["head"] = len(self.jnt_pos) - 1
        self.jointRelatives["eff1"] = len(self.jnt_pos) - 1

        for i, ctl in enumerate(self.neck_ctls):
            self.relatives["neck{}".format(i)] = ctl
            self.relatives["%s_loc" % i] = ctl
            self.controlRelatives["%s_loc" % i] = ctl

            self.jointRelatives["%s_loc" % (i)] = (i + 2)
            self.aliasRelatives["%s_ctl" % (i)] = (i + 2)

    def connect_standard(self):

        self.parent.addChild(self.root)

        # TODO: by settings gui
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

    def connect_spaghetti_head_position(self, i, next_cns):

        npo = self.neck_npos[i]
        cns = self.neck_cnss[i]
        ctl = self.neck_ctls[i]
        ref = self.neck_refs[i]

        # Neck position
        mult = pm.createNode("multMatrix")
        pm.connectAttr("{}.matrix".format(ref), "{}.matrixIn[0]".format(mult))
        pm.connectAttr("{}.matrix".format(ctl), "{}.matrixIn[1]".format(mult))
        pm.setAttr("{}.matrixIn[2]".format(mult), *cmds.getAttr("{}.matrix".format(npo)), type="matrix")
        pm.setAttr("{}.matrixIn[3]".format(mult), *cmds.getAttr("{}.matrix".format(npo)), type="matrix")

        decomp = pm.createNode("decomposeMatrix")
        pm.connectAttr("{}.matrixSum".format(mult), "{}.inputMatrix".format(decomp))
        # pm.connectAttr("{}.outputTranslate".format(decomp), "{}.translate".format(self.head_cns))

        cond = pm.createNode("condition")
        pm.connectAttr(self.neckref_att, "{}.firstTerm".format(cond))
        pm.setAttr("{}.secondTerm".format(cond), 0)
        pm.setAttr("{}.operation".format(cond), 0)
        pm.connectAttr("{}.outputTranslate".format(decomp), "{}.colorIfTrue".format(cond))
        pm.connectAttr("{}.outColor".format(cond), "{}.translate".format(next_cns))

        return cond

    def connect_spaghetti_head_rotation(self, i, head_ref_cond):

        npo = self.neck_npos[i]
        cns = self.neck_cnss[i]
        ctl = self.neck_ctls[i]
        ref = self.neck_refs[i]

        # Neck Rotation
        cond = pm.createNode("condition")
        pm.connectAttr(self.neckref_att, "{}.firstTerm".format(cond))
        pm.setAttr("{}.secondTerm".format(cond), 0)
        pm.setAttr("{}.operation".format(cond), 0)
        pm.setAttr("{}.colorIfTrueR".format(cond), 0)
        pm.setAttr("{}.colorIfTrueG".format(cond), 0)
        pm.setAttr("{}.colorIfTrueB".format(cond), 0)

        mult = pm.createNode("multMatrix")
        comp = pm.createNode("composeMatrix")
        pm.connectAttr("{}.outColorR".format(head_ref_cond), "{}.inputRotateX".format(comp))
        pm.connectAttr("{}.outColorG".format(head_ref_cond), "{}.inputRotateY".format(comp))
        pm.connectAttr("{}.outColorB".format(head_ref_cond), "{}.inputRotateZ".format(comp))
        pm.connectAttr("{}.matrix".format(self.head_ctl), "{}.matrixIn[0]".format(mult))
        pm.connectAttr("{}.outputMatrix".format(comp), "{}.matrixIn[1]".format(mult))

        toQuat = pm.createNode("eulerToQuat")
        decomp = pm.createNode("decomposeMatrix")
        pm.connectAttr("{}.matrixSum".format(mult), "{}.inputMatrix".format(decomp))
        pm.connectAttr("{}.outputRotate".format(decomp), "{}.inputRotate".format(toQuat))

        mult = pm.createNode("multDoubleLinear")
        slerp = pm.createNode("quatSlerp")
        pm.connectAttr(self.neckrate_att, "{}.input1".format(mult))
        pm.setAttr("{}.input2".format(mult), (1. - (1. / (self.division) * (i + 1))))
        pm.connectAttr("{}.outputQuat".format(toQuat), "{}.input1Quat".format(slerp))
        pm.connectAttr("{}.output".format(mult), "{}.inputT".format(slerp))
        pm.setAttr("{}.input2QuatX".format(slerp), 0.)
        pm.setAttr("{}.input2QuatY".format(slerp), 0.)
        pm.setAttr("{}.input2QuatZ".format(slerp), 0.)
        pm.setAttr("{}.input2QuatW".format(slerp), 1.)

        toEul = pm.createNode("quatToEuler")
        pm.connectAttr("{}.outputQuat".format(slerp), "{}.inputQuat".format(toEul))
        pm.connectAttr("{}.outputRotateX".format(toEul), "{}.colorIfFalseR".format(cond))
        pm.connectAttr("{}.outputRotateY".format(toEul), "{}.colorIfFalseG".format(cond))
        pm.connectAttr("{}.outputRotateZ".format(toEul), "{}.colorIfFalseB".format(cond))

        pm.connectAttr("{}.outColor".format(cond), "{}.rotate".format(cns))

        return cond, slerp

    def connect_spaghetti_head_position2(self, i, prev_mult, slerp, pos_cond):

        npo = self.neck_npos[i]
        cns = self.neck_cnss[i]
        ctl = self.neck_ctls[i]
        ref = self.neck_refs[i]

        comp = pm.createNode("composeMatrix")
        pm.connectAttr("{}.outputQuat".format(slerp), "{}.inputQuat".format(comp))
        pm.setAttr("{}.useEulerRotation".format(comp), False)
        pm.setAttr("{}.inputTranslateX".format(comp), cmds.getAttr("{}.translateX".format(cns)))
        pm.setAttr("{}.inputTranslateY".format(comp), cmds.getAttr("{}.translateY".format(cns)))
        pm.setAttr("{}.inputTranslateZ".format(comp), cmds.getAttr("{}.translateZ".format(cns)))
        inv = pm.createNode("inverseMatrix")
        pm.connectAttr("{}.outputMatrix".format(comp), "{}.inputMatrix".format(inv))

        mult = pm.createNode("multMatrix")

        if i > 0:
            pm.connectAttr("{}.inverseMatrix".format(cns), "{}.matrixIn[0]".format(mult))
            pm.connectAttr("{}.inverseMatrix".format(npo), "{}.matrixIn[2]".format(mult))
            pm.connectAttr("{}.inverseMatrix".format(ctl), "{}.matrixIn[3]".format(mult))
            pm.connectAttr("{}.inverseMatrix".format(ref), "{}.matrixIn[4]".format(mult))

        else:
            pm.connectAttr("{}.outputMatrix".format(inv), "{}.matrixIn[0]".format(mult))
            pm.connectAttr("{}.inverseMatrix".format(npo), "{}.matrixIn[1]".format(mult))
            pm.connectAttr("{}.inverseMatrix".format(ctl), "{}.matrixIn[2]".format(mult))
            pm.connectAttr("{}.inverseMatrix".format(ref), "{}.matrixIn[3]".format(mult))

        inv = pm.createNode("inverseMatrix")
        pm.connectAttr("{}.matrixSum".format(mult), "{}.inputMatrix".format(inv))
        decomp = pm.createNode("decomposeMatrix")
        pm.connectAttr("{}.outputMatrix".format(inv), "{}.inputMatrix".format(decomp))

        pm.connectAttr("{}.outputTranslate".format(decomp), "{}.colorIfFalse".format(pos_cond))

        return mult

    def connect_with_nodespaghetti(self):

        neck_ref_cond_positions = []
        for i in range(self.division - 1):
            cns = self.neck_cnss[i]
            if i < (self.division - 2):
                next_cns = self.neck_cnss[i + 1]
            else:
                next_cns = self.head_cns

            cond = self.connect_spaghetti_head_position(i, next_cns)
            neck_ref_cond_positions.append(cond)

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

        neck_ref_cond_rotations = []
        neck_slerps = []
        for i in range(self.division - 1):
            cond, slerp = self.connect_spaghetti_head_rotation(i, head_ref_cond)
            neck_ref_cond_rotations.append(cond)
            neck_slerps.append(slerp)

        # Head pos2
        mult = None
        for i in range(self.division - 1):

            slerp = neck_slerps[i]
            pos_cond = neck_ref_cond_positions[i]

            mult = self.connect_spaghetti_head_position2(i, mult, slerp, pos_cond)

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
