# -*- coding: utf-8 -*-
import maya.cmds as cmds
try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm

from mgear import rigbits
import mgear.shifter.custom_step as cstp
import ymt_shifter_utility as ymt_util


class CustomShifterStep(cstp.customShifterMainStep):
    """Custom Shifter Step Class for connecting cheek to lip.
    This script needs config dictionary to run.
    Here is a sample config dictionary:

        stepDict["cs_connect_cheek_to_lip_config"] = [
            {
                "src": [
                    "cheek_L2_surface_ctl",
                    "cheek_L3_surface_ctl",
                    "lip_C0_lip_L0_corner_ctl",
                ],
                "dst": "aroundlip_C0_aroundlip_L0_outer_ctl",
                "rates": [0.25, 0.25, 1.0],
            },
            {
                "src": [
                    "cheek_R2_surface_ctl",
                    "cheek_R3_surface_ctl",
                    "lip_C0_lip_R0_corner_ctl",
                ],
                "dst": "aroundlip_C0_aroundlip_R0_outer_ctl",
                "rates": [0.25, 0.25, 1.0],
            },
            {
                "src": [
                    "nose_C0_ctl",
                    "lip_C0_lip_C0_upper_ctl",
                ],
                "dst": "aroundlip_C0_aroundlip_C0_upcenter_ctl",
                "rates": [0.15, 0.85],
            },
            {
                "src": [
                    "mouthCorner_L0_ctl_ghost",
                ],
                "dst": "cheek_L3_surface_ctl",
                "rates": [0.62],
                "addNpo": False
            },
            {
                "src": [
                    "mouthCorner_R0_ctl_ghost",
                ],
                "dst": "cheek_R3_surface_ctl",
                "rates": [0.62],
                "addNpo": False
            },
            {
                "src": [
                    "mouthCorner_L0_ctl_ghost",
                ],
                "dst": "cheek_L2_surface_ctl",
                "rates": [0.33],
                "addNpo": False
            },
            {
                "src": [
                    "mouthCorner_R0_ctl_ghost",
                ],
                "dst": "cheek_R2_surface_ctl",
                "rates": [0.33],
                "addNpo": False
            },
            {
                "src": [
                    "eye_L0_lowEyelid_crvdetail2_ctl",
                    "eye_L0_lowEyelid_crvdetail3_ctl",
                    "eye_L0_lowEyelid_crvdetail4_ctl",
                ],
                "dst": "cheek_L0_surface_ctl",
                "rates": [0.07, 0.1, 0.05],
                "addNpo": False
            },
            {
                "src": [
                    "eye_R0_lowEyelid_crvdetail2_ctl",
                    "eye_R0_lowEyelid_crvdetail3_ctl",
                    "eye_R0_lowEyelid_crvdetail4_ctl",
                ],
                "dst": "cheek_R0_surface_ctl",
                "rates": [0.07, 0.1, 0.05],
                "addNpo": False
            },
            {
                "src": [
                    "eye_L0_lowEyelid_crvdetail2_ctl",
                    "eye_L0_lowEyelid_crvdetail3_ctl",
                    "eye_L0_lowEyelid_crvdetail4_ctl",
                ],
                "dst": "cheek_L1_surface_ctl",
                "rates": [0.05, 0.1, 0.07],
                "addNpo": False
            },
            {
                "src": [
                    "eye_R0_lowEyelid_crvdetail2_ctl",
                    "eye_R0_lowEyelid_crvdetail3_ctl",
                    "eye_R0_lowEyelid_crvdetail4_ctl",
                ],
                "dst": "cheek_R1_surface_ctl",
                "rates": [0.05, 0.1, 0.07],
                "addNpo": False
            },
        ]
    """

    def __init__(self):
        self.name = "Sknning Surface"
        self.defaultConfig = [
            {
                "src": [
                    "nose_C0_ctl",
                    "mouth_C0_lipup_ctl",
                    "mouthSlide_C0_ctl",
                    "aroundlip_C0_rope"
                ],
                "dst": "aroundlip_C0_upcenter_ctl",
                "rates": [0.10, 0.50, 0.05, 0.35],
                "mode": "addNpo",
            },
            # {
            #     "src": [
            #         "mouth_C0_liplow_ctl",
            #         "mouthSlide_C0_ctl",
            #         "mouthSlide_C0_ctl_slideDriven",
            #     ],
            #     "dst": "aroundlip_C0_lowcenter_ctl",
            #     "rates": [0.80, 0.10, 0.10],
            #     "mode": "addNpo",
            # },
            {
                "src": [
                    "eye_L0_lowEyelid_crvdetail2_ctl",
                    "eye_L0_lowEyelid_crvdetail3_ctl",
                    "eye_L0_lowEyelid_crvdetail4_ctl",
                ],
                "dst": "cheek_L1_surface_ctl",
                "rates": [0.05, 0.1, 0.07],
                "mode": "parent",
            },
            {
                "src": [
                    "eye_R0_lowEyelid_crvdetail2_ctl",
                    "eye_R0_lowEyelid_crvdetail3_ctl",
                    "eye_R0_lowEyelid_crvdetail4_ctl",
                ],
                "dst": "cheek_R1_surface_ctl",
                "rates": [0.05, 0.1, 0.07],
                "mode": "parent",
            },
            {
                "src": [
                    "eye_L0_lowEyelid_crvdetail3_ctl",
                    "surfaceWire_L0_ctls",
                ],
                "dst": "surfaceWire_L0_0_ctl",
                "rates": [0.5, 0.5],
                "mode": "self",
            },
            {
                "src": [
                    "lip_L0_2_crvdetail_ctl",
                    "aroundlip_L0_2_crvdetail_ctl",
                    "aroundlip_L0_3_crvdetail_ctl",
                ],
                "dst": "surfaceWire_L0_2_ctl",
                "rates": [0.3, 0.35, 0.35],
                "mode": "self",
            },
            {
                "src": [
                    "eye_R0_lowEyelid_crvdetail3_ctl",
                    "surfaceWire_R0_ctls",
                ],
                "dst": "surfaceWire_R0_0_ctl",
                "rates": [0.5, 0.5],
                "mode": "self",
            },
            {
                "src": [
                    "lip_R0_2_crvdetail_ctl",
                    "aroundlip_R0_2_crvdetail_ctl",
                    "aroundlip_R0_3_crvdetail_ctl",
                ],
                "dst": "surfaceWire_R0_2_ctl",
                "rates": [0.3, 0.35, 0.35],
                "mode": "self",
            },
        ]

    def run(self, stepDict):
        # type: (dict) -> None

        self.rig = stepDict["mgearRun"]
        self.config = stepDict.get("cs_connect_cheek_to_lip_config", self.defaultConfig)

        for entry in self.config:
            src = entry["src"]
            dst = entry["dst"]
            rates = entry["rates"]
            mode = entry.get("mode", "addNpo")

            skip = False
            for s in src:
                if not cmds.objExists(s):
                    print("Source object not found: {}".format(s))
                    skip = True
            if skip:
                continue

            if not cmds.objExists(dst):
                print("Destination object not found: {}".format(dst))
                continue

            self.connect(src, dst, rates, mode=mode)

    def connect(self, src, dst, rates, mode="addNpo"):

        dst_node = pm.PyNode(dst)

        if mode == "self":
            target = dst_node
        elif mode == "parent":
            target = dst_node.getParent()
        elif mode == "addNpo":
            target = ymt_util.addNPOPreservingMatrixConnections(dst_node)[0]  # type: pm.PyNode
        else:
            raise ValueError("Invalid mode: {}".format(mode))

        lockedTx = cmds.getAttr(target.longName() + ".tx", lock=True)
        lockedTy = cmds.getAttr(target.longName() + ".ty", lock=True)
        lockedTz = cmds.getAttr(target.longName() + ".tz", lock=True)
        lockedRx = cmds.getAttr(target.longName() + ".rx", lock=True)
        lockedRy = cmds.getAttr(target.longName() + ".ry", lock=True)
        lockedRz = cmds.getAttr(target.longName() + ".rz", lock=True)
        cmds.setAttr(target.longName() + ".tx", lock=False)
        cmds.setAttr(target.longName() + ".ty", lock=False)
        cmds.setAttr(target.longName() + ".tz", lock=False)
        cmds.setAttr(target.longName() + ".rx", lock=False)
        cmds.setAttr(target.longName() + ".ry", lock=False)
        cmds.setAttr(target.longName() + ".rz", lock=False)
        cns = cmds.parentConstraint(src, target.longName(), mo=True)[0]  # type: str
        cmds.setAttr("{}.interpType".format(cns), 2)  # shortest
        cmds.setAttr(target.longName() + ".tx", lock=lockedTx)
        cmds.setAttr(target.longName() + ".ty", lock=lockedTy)
        cmds.setAttr(target.longName() + ".tz", lock=lockedTz)
        cmds.setAttr(target.longName() + ".rx", lock=lockedRx)
        cmds.setAttr(target.longName() + ".ry", lock=lockedRy)
        cmds.setAttr(target.longName() + ".rz", lock=lockedRz)

        # if already has been constrained, adding to the existing constraint
        counts = len(cmds.parentConstraint(cns, q=True, weightAliasList=True))
        offset = counts - len(rates)

        for i, rate in enumerate(rates):
            cmds.setAttr("{}.{}W{}".format(cns, src[i], i + offset), rate)
