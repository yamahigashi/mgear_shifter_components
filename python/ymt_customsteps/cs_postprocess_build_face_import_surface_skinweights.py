# -*- coding: utf-8 -*-
import os
import maya.cmds as cmds
import pymel.core as pm
import mgear.core.skin as skin

from mgear import rigbits
import mgear.shifter.custom_step as cstp


class CustomShifterStep(cstp.customShifterMainStep):

    def __init__(self):
        self.name = "Sknning Surface"

    def run(self, stepDict):
        # type: (dict) -> None

        self.rig = stepDict["mgearRun"]
        self.skin_file = self.get_skin_file()
        skin.importSkinPack(self.skin_file)

    def get_skin_file(self):
        # type: () -> str

        rig_name = self.rig.options["rig_name"]
        file_name = f"{rig_name}_surface_C0_surface.gSkinPack"
        # file_name = f"face_surface_C0_surface.gSkinPack"

        p = cmds.workspace(expandName=f"conf/{file_name}")
        if not os.path.exists(p):
            raise Exception("Workspace path does not exist: {}".format(p))

        return p
