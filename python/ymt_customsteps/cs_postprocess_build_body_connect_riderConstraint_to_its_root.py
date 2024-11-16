# -*- coding: utf-8 -*-
import maya.cmds as cmds

import mgear.shifter.custom_step as cstp


class CustomShifterStep(cstp.customShifterMainStep):
    """Connect riderConstraint global spread to its root global scale."""

    def __init__(self):
        self.name = "Connect riderConstraint to its root"

    def run(self, stepDict):
        # type: (dict) -> None

        constraints = cmds.ls(type="riderConstraint")
        if not constraints:
            return

        for constraint in constraints:
            self.connect_rider_constraint(constraint)

    def connect_rider_constraint(self, constraint):
        print("Connect riderConstraint to its root: {}".format(constraint))
        nodes = cmds.listConnections(constraint, source=True, destination=False, type="transform") or []
        if not nodes:
            return

        nodes = [x.split("_twistSpline")[0] for x in nodes if "twistSpline" in x]
        nodes = list(set(nodes))

        if not nodes:
            return

        root = nodes[0] + "_root"
        decomp = cmds.createNode("decomposeMatrix", name=constraint + "_decomposeMatrix")
        cmds.connectAttr(root + ".worldMatrix[0]", decomp + ".inputMatrix", force=True)
        cmds.connectAttr(decomp + ".outputScaleY", constraint + ".globalSpread", force=True)
