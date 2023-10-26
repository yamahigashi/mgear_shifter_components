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
        self.deformers = [
            "headBend_C0_0_jnt",
            "headBend_C1_0_jnt",
            "eye_L0_base_jnt",
            "eye_R0_base_jnt",
            "headBend_C2_0_jnt",
            "headBend_C3_0_jnt",
            "mouth_C0_jaw_jnt",
            "nose_C0_0_jnt",
            "forehead_C0_0_jnt",
            # "zygoma_L0_0_jnt",
            # "zygoma_R0_0_jnt",
        ]
        self.surfaces = self.find_surfaces()
        self.skinning()

    def find_surfaces(self):
        # type: () -> list[str]

        # surfaces = []
        print(self.rig)

        return cmds.ls("surface_C0_surface")

    def skinning(self):
        # type: () -> None

        cmds.select(self.deformers)
        self.skin = cmds.skinCluster(
            self.deformers,
            self.surfaces,
            toSelectedBones=True,
            # skinMethod=1,
            bindMethod=1,
            smoothWeights=0.5,
        )


        # cmds.deformer(type="deltaMush")
