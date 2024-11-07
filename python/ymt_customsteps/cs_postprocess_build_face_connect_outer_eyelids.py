# -*- coding: utf-8 -*-
import maya.cmds as cmds
import pymel.core as pm

from mgear import rigbits
from mgear.core.transform import (
    getTransform,
)
import mgear.shifter.custom_step as cstp
import ymt_shifter_utility as ymt_utility
import ymt_shifter_utility.curve as curve


class CustomShifterStep(cstp.customShifterMainStep):
    """Custom Shifter Step Class for outer eyelid lines blending eyebrow and blink curves.

    This script needs config dictionary to run.
    Here is a sample config dictionary:

        stepDict["cs_outer_eyelids_config"] = {
            "parent": "headBend_C1_ik_cns",
            "npos_left": [
                "eyelidline_L0_npo",
                "eyelidline_L1_npo",
                "eyelidline_L2_npo",
                "eyelidline_L3_npo",
                "eyelidline_L4_npo"
            ],
            "npos_right": [
                "eyelidline_R0_npo",
                "eyelidline_R1_npo",
                "eyelidline_R2_npo",
                "eyelidline_R3_npo",
                "eyelidline_R4_npo"
            ],
            "brow_crv_left": "eyebrow_L0_mainCtl_crv",
            "brow_crv_right": "eyebrow_R0_mainCtl_crv",
            "blink_crv_left": "eye_L0_upblink_crv",
            "blink_crv_right": "eye_R0_upblink_crv",
        }
    """

    def __init__(self):
        self.name = "Outer Eyelids Connect"

    def run(self, stepDict):
        # type: (dict) -> None

        self.rig = stepDict["mgearRun"]
        self.stepDict = stepDict
        self.config = stepDict["cs_outer_eyelids_config"]
        self.parent = self.config["parent"]

        # left
        brow_crv = self.get_brow_crv(left=True)
        blink_crv = self.get_blink_crv(left=True)
        eyelids, dummy_start, dummy_end = self.get_npos(left=True)
        dest_crv = self.blendShape("eyelidline_L0_", brow_crv, blink_crv, eyelids)
        for npo in eyelids:
            curve.applyPathConstrainLocal(npo, dest_crv)

        cmds.delete(dummy_start)
        cmds.delete(dummy_end)

        # right
        brow_crv = self.get_brow_crv(left=False)
        blink_crv = self.get_blink_crv(left=False)
        eyelids, dummy_start, dummy_end = self.get_npos(left=False)
        dest_crv = self.blendShape("eyelidline_R0_", brow_crv, blink_crv, eyelids, False)
        for npo in eyelids:
            curve.applyPathConstrainLocal(npo, dest_crv)
        cmds.delete(dummy_start)
        cmds.delete(dummy_end)

    def blendShape(self, name, brow_crv, blink_crv, eyelids, left=True):

        if left:
            sortingAxis = "x"
        else:
            sortingAxis = "-x"

        t = getTransform(pm.PyNode(self.parent))
        edges, dummy_plane = ymt_utility.create_dummy_edges_from_objects(eyelids)
        tmp = curve.createCurveFromEdges(edges, name + "eyelid_crv", sortingAxis=sortingAxis, m=t)

        # TODO: extract number of CVs, fixed to 30 for now.
        dest = curve.createCurveFromCurve(tmp, name + "eyelid_crv2", 30, m=t)
        target1 = curve.createCurveFromCurve(brow_crv, name + "brow_crv", 30, m=t).fullPath()
        cmds.wire(target1, w=brow_crv, n=name + "wire")
        bs = pm.blendShape(target1, blink_crv, dest.fullPath())
        cmds.setAttr(bs[0] + "." + target1.split("|")[-1], 0.16)
        cmds.setAttr(bs[0] + "." + blink_crv, 0.25)
        cmds.delete(dummy_plane.getPath().fullPathName())

        cmds.parent(tmp.fullPath(), self.parent)
        cmds.parent(dest.fullPath(), self.parent)
        cmds.parent(target1, self.parent)

        cmds.hide(target1.split("|")[-1])
        cmds.hide(tmp.fullPath())
        cmds.hide(dest.fullPath())

        return dest

    def get_npos(self, left=True):
        # type: (bool) -> Tuple[list[str], str, str]
        if left:
            npos = self.config.get("npos_left", None)
        else:
            npos = self.config.get("npos_right", None)

        if not npos:
            raise Exception("No npos found for left outer eyelids")

        # extend npos
        centroid = ymt_utility.get_centroid_from_objects(npos)
        left = cmds.xform(npos[0], q=True, ws=True, t=True)
        right = cmds.xform(npos[-1], q=True, ws=True, t=True)
        start_position = [
            left[0] - (centroid[0] - left[0]) * 0.6,  # type: ignore
            left[1] - (centroid[1] - left[1]) * 0.8,  # type: ignore 
            left[2] - (centroid[2] - left[2]) * 0.6  # type: ignore
        ]
        end_position = [
            right[0] + (right[0] - centroid[0]) * 0.6,  # type: ignore
            right[1] + (right[1] - centroid[1]) * 0.8,  # type: ignore
            right[2] + (right[2] - centroid[2]) * 0.6  # type: ignore
        ]

        dummy_start = cmds.spaceLocator(n="dummy_start")[0]
        dummy_end = cmds.spaceLocator(n="dummy_end")[0]
        cmds.xform(dummy_start, ws=True, t=start_position)
        cmds.xform(dummy_end, ws=True, t=end_position)

        npos.insert(0, dummy_start)
        npos.append(dummy_end)

        return npos, dummy_start, dummy_end

    def get_brow_crv(self, left=True):
        # type: (bool) -> str

        if left:
            crv = self.config.get("brow_crv_left", None)
        else:
            crv = self.config.get("brow_crv_right", None)

        if not crv:
            raise Exception("No brow curve found for left outer eyelids")

        return crv

    def get_blink_crv(self, left=True):
        # type: (bool) -> str

        if left:
            crv = self.config.get("blink_crv_left", None)
        else:
            crv = self.config.get("blink_crv_right", None)

        if not crv:
            raise Exception("No blink curve found for left outer eyelids")

        return crv
