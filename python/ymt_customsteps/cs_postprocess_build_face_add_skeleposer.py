# -*- coding: utf-8 -*-
import maya.cmds as cmds
try:
    import mgear.pymaya as pm
except ImportError:
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

        cmds.loadPlugin("skeleposer.mll", quiet=True)

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
        self.adj_to_ctrl = {}

        for uuid in self.get_controller_uuids():
            ctrl = cmds.ls(uuid, long=True)[0]
            if "isCtl" not in cmds.listAttr(ctrl):
                continue

            try:
                npo = ymt_util.addNPOPreservingMatrixConnections(pm.PyNode(ctrl))[0]  # type: pm.PyNode
            except RuntimeError as e:
                print("addNPO failed for {}".format(ctrl))
                print(e)
                continue

            # The hierarchy has changed, so get it again
            ctrl = cmds.ls(uuid, long=True)[0]

            new_name = ctrl.split("|")[-1].replace("_ctl", "_adj")
            new_full_path = "|".join(ctrl.split("|")[:-1] + [new_name])
            if cmds.objExists(new_full_path):
                print("already exists: {}".format(new_name))
                continue

            cmds.rename(npo.fullPath(), new_name)

            adj_uuid = cmds.ls(npo.getName(), uuid=True)[0]
            self.adj_node_uuids.append(adj_uuid)
            self.adj_to_ctrl[adj_uuid] = uuid

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

        for adj_uuid, ctrl_uuid in self.adj_to_ctrl.items():
            adj = cmds.ls(adj_uuid, long=True)[0]
            ctrl = cmds.ls(ctrl_uuid, long=True)[0]
            for a in ("t", "r", "s"):
                if is_all_axis_connected_or_locked(ctrl, a):
                    conns = cmds.listConnections(adj + "." + a, source=True, destination=False, plugs=True) or []
                    for conn in conns:
                        cmds.disconnectAttr(conn, adj + "." + a)
                    val = 1.0 if a == "s" else 0.0
                    cmds.setAttr(adj + "." + a + "x", val)
                    cmds.setAttr(adj + "." + a + "x", lock=True)
                    cmds.setAttr(adj + "." + a + "y", val)
                    cmds.setAttr(adj + "." + a + "y", lock=True)
                    cmds.setAttr(adj + "." + a + "z", val)
                    cmds.setAttr(adj + "." + a + "z", lock=True)

                    cmds.setAttr(adj + "." + a, lock=True)

    def get_controller_uuids(self):
        # type: () -> list[str]
        """Get all controllers from the rig using rig sets."""

        res = []

        def _recursive_get_children(sets_name):
            members = cmds.sets(sets_name, q=True) or []  # type: any
            for elem in members:
                if "_ctl" in elem and cmds.nodeType(elem) == "transform":
                    uuid = cmds.ls(elem, uuid=True)[0]
                    res.append(uuid)

                if cmds.nodeType(elem) == "objectSet":
                    _recursive_get_children(elem)

        grp_name = self.rig_name + "_controllers_grp"
        _recursive_get_children(grp_name)

        return list(set(res))


def is_connected_or_locked(node, attr):
    # type: (str, str) -> bool
    """Check if the attribute is connected or locked."""

    if not cmds.objExists(node):
        print("Node does not exist: {}".format(node))
        return False

    # long name is not supported...
    node = cmds.ls(node)[0]

    if cmds.connectionInfo(node + "." + attr, isDestination=True):
        return True
    if cmds.getAttr(node + "." + attr, lock=True):
        return True

    return False
    

def is_all_axis_connected_or_locked(node, attr):
    # type: (str, str) -> bool
    """Check if the attribute is connected or locked."""

    if not cmds.objExists(node):
        print("Node does not exist: {}".format(node))
        return False

    for axis in ["x", "y", "z"]:
        if not is_connected_or_locked(node, attr + axis):
            return False

    return True
