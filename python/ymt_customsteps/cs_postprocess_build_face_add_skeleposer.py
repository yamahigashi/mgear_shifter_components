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
import ymt_shifter_utility as ymt_util


class CustomShifterStep(cstp.customShifterMainStep):

    def __init__(self):
        self.name = "Add Skeleposer"

    def run(self, stepDict):
        # type: (dict) -> None

        cmds.loadPlugin("skeleposer.mll")

        rig = stepDict.get("mgearRun")
        if rig is None:
            self.rig_name = cmds.ls(sl=True)[0]
        else:
            self.rig_name = rig.model.name()

        self.insert_adj_nodes()
        self.add_skeleposer_node()

    def insert_adj_nodes(self):
        # type: () -> None
        """Insert an adjust node for skeleposer."""

        self.adj_node_uuids = []

        for uuid in self.get_controller_uuids():
            ctrl = cmds.ls(uuid, long=True)[0]
            try:
                npo = ymt_util.addNPOPreservingMatrixConnections(ctrl)[0]  # type: pm.PyNode
            except RuntimeError as e:
                print("addNPO failed for {}".format(ctrl))
                print(e)
                continue

            # The hierarchy has changed, so get it again
            ctrl = cmds.ls(uuid, long=True)[0]
            # self.insert_add_node(npo, pm.PyNode(ctrl))

            new_name = ctrl.split("|")[-1].replace("_ctl", "_adj")
            new_full_path = "|".join(ctrl.split("|")[:-1] + [new_name])
            if cmds.objExists(new_full_path):
                print("already exists: {}".format(new_name))
                continue

            cmds.rename(npo.fullPath(), new_name)
            uuid = cmds.ls(npo.getName(), uuid=True)[0]
            self.adj_node_uuids.append(uuid)

    def add_skeleposer_node(self):
        # type: () -> None
        """Add a skeleposer node to the rig and register joints."""

        name = self.rig_name + "_skeleposer"

        try:
            poser = editor.Skeleposer(cmds.createNode("skeleposer", name=name))
        except RuntimeError:
            print("Failed to create skeleposer node")
            return

        try:
            joints = [pm.PyNode(cmds.ls(jnt, uuid=True)[0]) for jnt in self.adj_node_uuids]
            poser.addJoints(joints)
        except RuntimeError:
            print("Failed to add joints to skeleposer")
            return

    def get_controller_uuids(self):
        # type: () -> list[str]
        """Get all controllers from the rig using rig sets."""

        res = []
        grp_name = self.rig_name + "_controllers_grp"
        members = cmds.sets(grp_name, q=True) or []  # type: any

        for elem in members:
            if "_ctl" in elem and cmds.nodeType(elem) == "transform":
                uuid = cmds.ls(elem, uuid=True)[0]
                res.append(uuid)

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
