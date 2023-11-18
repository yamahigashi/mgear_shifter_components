# -*- coding: utf-8 -*-
import maya.cmds as cmds
import pymel.core as pm

from mgear import rigbits
import mgear.shifter.custom_step as cstp
try:
    import skeleposerEditor as editor  # type: ignore
except ImportError:
    raise ImportError(
        "skeleposerEditor not found. Please install it from "
        "https://github.com/azagoruyko/skeleposer"
    )
import ymt_shifter_utility as ymt_utility


class CustomShifterStep(cstp.customShifterMainStep):

    def __init__(self):
        self.name = "Add Skeleposer"

    def run(self, stepDict):
        # type: (dict) -> None

        cmds.loadPlugin("skeleposer.mll")

        self.rig = stepDict["mgearRun"]
        self.insert_adj_node()
        self.add_skeleposer_node()

    def insert_adj_node(self):
        # type: () -> None
        """Insert an adjust node for skeleposer."""

        self.adj_nodes = []

        for ctrl in self.get_controllers():
            try:
                npo = ymt_util.addNPOPreservingMatrixConnections(pm.PyNode(ctrl))[0]  # type: pm.PyNode
            except RuntimeError:
                print("addNPO failed for {}".format(ctrl))
                continue

            self.insert_add_node(npo, pm.PyNode(ctrl))

            new_name = ctrl.split("|")[-1].replace("_ctl", "_adj")
            if cmds.objExists(new_name):
                print("already exists: {}".format(new_name))

            new_node = cmds.rename(npo.fullPath(), new_name)
            self.adj_nodes.append(new_node)

    def add_skeleposer_node(self):
        # type: () -> None
        """Add a skeleposer node to the rig and register joints."""

        name = self.rig.model.name() + "_skeleposer"

        try:
            poser = editor.Skeleposer(cmds.createNode("skeleposer", name=name))
        except RuntimeError:
            print("Failed to create skeleposer node")
            return

        try:
            joints = [pm.PyNode(jnt) for jnt in self.adj_nodes]
            poser.addJoints(joints)
        except RuntimeError:
            print("Failed to add joints to skeleposer")
            return

    def get_controllers(self):
        # type: () -> list[str]
        """Get all controllers from the rig using rig sets."""

        res = []
        grp_name = self.rig.model.name() + "_controllers_grp"
        members = cmds.sets(grp_name, q=True) or []  # type: any

        for elem in members:
            if "_ctl" in elem and cmds.nodeType(elem) == "transform":
                res.append(elem)

        return res

    def insert_add_node(self, adj, ctl):
        # type: (pm.PyNode, pm.PyNode) -> None
        """Insert an add node between from the controller to the other node.

        If there is an attribute that is directly connected from the controller,
        it is necessary to add the adj node and pass it.
        """

        def __inner(attr_name, adj, ctl, dst):
            add_node = pm.createNode("addDoubleLinear")
            add_node.input1.set(0.0)
            add_node.input2.set(0.0)

            ctl.attr(attr_name) >> add_node.input1
            adj.attr(attr_name) >> add_node.input2
            add_node.output >> dst

        for attr in ("translate", "rotate", "scale"):
            for axis in ("X", "Y", "Z"):
                attr_name = attr + axis

                connections = cmds.listConnections(
                    "{}.{}".format(ctl.fullPath(), attr_name),
                    s=False,
                    d=True,
                    p=True
                )

                if not connections:
                    continue

                # FIXME
                for conn in connections:
                    print("insert add node: {}{} -> {}".format(ctl, attr_name, conn))
                    __inner(attr_name, adj, ctl, conn)
