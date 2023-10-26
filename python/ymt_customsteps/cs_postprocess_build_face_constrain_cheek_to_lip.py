# -*- coding: utf-8 -*-
import maya.cmds as cmds
import pymel.core as pm

from mgear import rigbits
import mgear.shifter.custom_step as cstp


class CustomShifterStep(cstp.customShifterMainStep):

    def __init__(self):
        self.name = "Sknning Surface"

    def run(self, stepDict):
        # type: (dict) -> None

        self.rig = stepDict["mgearRun"]
        src = [
            "cheek_L2_surface_ctl",
            "cheek_L3_surface_ctl",
            "lip_C0_lip_L0_corner_ctl",
        ]
        dst = "aroundlip_C0_aroundlip_L0_outer_ctl"
        npo = rigbits.addNPO(pm.PyNode(dst))[0]  # type: pm.PyNode
        cmds.parentConstraint(src, npo.fullPath(), mo=True)

        src = [
            "cheek_R2_surface_ctl",
            "cheek_R3_surface_ctl",
            "lip_C0_lip_R0_corner_ctl",
        ]
        dst = "aroundlip_C0_aroundlip_R0_outer_ctl"
        npo = rigbits.addNPO(pm.PyNode(dst))[0]  # type: pm.PyNode
        cmds.parentConstraint(src, npo.fullPath(), mo=True)
