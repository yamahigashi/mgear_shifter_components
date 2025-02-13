# -*- coding: utf-8 -*-
import maya.cmds as cmds
try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm

from mgear import rigbits
import mgear.shifter.custom_step as cstp


class CustomShifterStep(cstp.customShifterMainStep):

    def __init__(self):
        self.name = "Sknning Surface"

    def run(self, stepDict):
        # type: (dict) -> None

        self.rig = stepDict["mgearRun"]

        src = "forehead_C0_ctl"
        brows = [
            ("eyebrow_L0_main_ctl", "eyebrow_L0_in_npo"),
            ("eyebrow_R0_main_ctl", "eyebrow_R0_in_npo"),
        ]

        for main, npo in brows:
            cns1 = cmds.parentConstraint(main, npo, maintainOffset=True)[0]
            cns2 = cmds.parentConstraint(src, npo, maintainOffset=True)[0]
            cmds.setAttr(cns1 + f".{main}W0", 0.75)
            cmds.setAttr(cns2 + f".{src}W1", 0.25)
