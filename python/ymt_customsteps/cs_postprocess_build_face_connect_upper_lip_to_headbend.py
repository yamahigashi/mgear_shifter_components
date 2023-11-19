# -*- coding: utf-8 -*-
import maya.cmds as cmds
import pymel.core as pm

from mgear import rigbits
import mgear.shifter.custom_step as cstp
import ymt_shifter_utility as ymt_util


class CustomShifterStep(cstp.customShifterMainStep):
    """Custom Shifter Step Class for connecting upper lip to headbend2."""

    def __init__(self):
        self.name = "Connect upper lip to headbend"
        self.defaultConfig = {
            "src": "headBend_C2_ctl",
            "old": "headBend_C3_ctl",
            "dst": "mouth_C0_jawUpper_npo",
            "slider": "mouthSlide_C0_ctl",
        }

    def run(self, stepDict):
        # type: (dict) -> None

        self.rig = stepDict["mgearRun"]
        self.config = stepDict.get("cs_connect_lip_to_headbend", self.defaultConfig)

        src = self.config.get("src")
        dst = self.config.get("dst")

        self.connect_to_bend2(src, dst)
        self.reconnect_slider_matrix()

    def connect_to_bend2(self, src, dst):
        npo = ymt_util.addNPOPreservingMatrixConnections(pm.PyNode(dst))[0]  # type: pm.PyNode
        cns = cmds.parentConstraint(src, npo.fullPath(), mo=True)[0]
        cmds.setAttr("{}.interpType".format(cns), 0)  # no flip

    def reconnect_slider_matrix(self):
        """Reconnects the constraints using a local matrices,

        due to the original constraints being broken by the disconnecting.
        """
        old = self.config.get("old")
        dst = self.config.get("dst")
        slider = self.config.get("slider")

        # first, search the multMatrix node of the old constraint
        connections = cmds.listConnections(
            "{}.matrix".format(old),  # type: ignore
            s=False,
            d=True
        )

        for c in connections:
            sources = cmds.listConnections(
                "{}.matrixIn".format(c),  # type: ignore
                s=True,
                d=False
            )

            if slider not in sources:
                continue

            start = sources[0]
            end = sources[-1]

            upper_paths, _, _ = ymt_util.findPathAtoB(start, end)

            for i, (s, u) in enumerate(zip(sources, upper_paths)):
                print(f"check{i}: {s}, {u}")
                if s != u:
                    cmds.connectAttr(u + ".matrix", c + ".matrixIn[{}]".format(i), force=True)
