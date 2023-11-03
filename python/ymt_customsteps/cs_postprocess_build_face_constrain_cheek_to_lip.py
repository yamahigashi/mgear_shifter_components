# -*- coding: utf-8 -*-
import maya.cmds as cmds
import pymel.core as pm

from mgear import rigbits
import mgear.shifter.custom_step as cstp


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

    def run(self, stepDict):
        # type: (dict) -> None

        self.rig = stepDict["mgearRun"]
        self.config = stepDict.get("cs_connect_cheek_to_lip_config", self.defaultConfig)

        for entry in self.config:
            src = entry["src"]
            dst = entry["dst"]
            rates = entry["rates"]
            addNpo = entry.get("addNpo", True)

            self.connect(src, dst, rates, addNpo=addNpo)

    def connect(self, src, dst, rates, addNpo=True):

        dst_node = pm.PyNode(dst)
        parent = dst_node.getParent()

        if addNpo:
            parent = rigbits.addNPO(dst_node)[0]  # type: pm.PyNode

        cns = cmds.parentConstraint(src, parent.fullPath(), mo=True)[0]  # type: str
        cmds.setAttr("{}.interpType".format(cns), 2)  # shortest

        # if already has been constrained, adding to the existing constraint
        counts = len(cmds.parentConstraint(cns, q=True, weightAliasList=True))
        offset = counts - len(rates)

        for i, rate in enumerate(rates):
            cmds.setAttr("{}.{}W{}".format(cns, src[i], i + offset), rate)
