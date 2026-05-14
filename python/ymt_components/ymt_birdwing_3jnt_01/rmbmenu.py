"""Module for hook right mouse button using rmbmenuhook."""

# https://github.com/bohdon/maya-workflowtools/tree/main/src/workflowtools/scripts/rmbmenuhook
import os
import re
from functools import partial
from logging import DEBUG, INFO, WARN, StreamHandler, getLogger
from typing import Optional, TypedDict, cast

import maya.cmds as cmds
from mgear.core import transform

from ymt_components import rmbmenu
from ymt_shifter_utility import control_util
from . import control

###############################################################################
handler = StreamHandler()
handler.setLevel(DEBUG)

logger = getLogger(__name__)
logger.setLevel(WARN)
logger.setLevel(DEBUG)
logger.setLevel(INFO)
logger.addHandler(handler)
logger.propagate = False
# =============================================================================


##############################################################################


class IkFkControls(TypedDict):
    ik: Optional[str]
    upv: Optional[str]
    ik_rot: Optional[str]
    hand_ik_rot: Optional[str]
    hand_ik: Optional[str]
    fks: list[str]


def _collect_ikfk_controls(all_controllers: list[str]) -> IkFkControls:
    controls: IkFkControls = {
        "ik": None,
        "upv": None,
        "ik_rot": None,
        "hand_ik_rot": None,
        "hand_ik": None,
        "fks": [],
    }

    for controller in all_controllers:
        if re.search("fk[0-9]", controller):
            controls["fks"].append(controller)

        if "hand_ik_ctl" in controller:
            controls["hand_ik"] = controller
        elif "handIkRot_ctl" in controller:
            controls["hand_ik_rot"] = controller
        elif "ikRot_ctl" in controller:
            controls["ik_rot"] = controller
        elif "ik_ctl" in controller:
            controls["ik"] = controller

        if "upv_ctl" in controller:
            controls["upv"] = controller

    controls["fks"].sort()
    return controls


def _validate_ikfk_controls(controls: IkFkControls, ui_host: object) -> None:
    missing = [
        name
        for name, value in [
            ("ik_ctl", controls["ik"]),
            ("upv_ctl", controls["upv"]),
            ("ikRot_ctl", controls["ik_rot"]),
            ("hand_ik_ctl", controls["hand_ik"]),
            ("handIkRot_ctl", controls["hand_ik_rot"]),
            ("ui host", ui_host),
            ("fk controls", controls["fks"]),
        ]
        if not value
    ]
    if missing:
        raise ValueError("Missing required ymt_birdwing_3jnt_01 controls: {}".format(", ".join(missing)))


class ShifterMarkingMenu(rmbmenu.ShifterMarkingMenu):
    comp_name = os.path.basename(os.path.dirname(__file__))

    def build_specialized(self, targets: list[str]) -> None:
        # self.menu is the parent marking menu that menuItems should be attached to
        cmds.setParent(self.menu, m=True)

        # choices = control.get_head_ref_choices(root)
        space_switch = cmds.menuItem(l="Space Switch", rp="W", subMenu=True)

        # for i, choice in enumerate(choices):
        #     cmds.menuItem(
        #         l="Switch Head Ref to {}".format(choice),
        #         parent=space_switch,
        #         command=partial(self.space_switch_head, targets, i, False),
        #     )

        cmds.menuItem(
            l="Switch IKFK",
            rp="NW",
            parent=space_switch,
            command=partial(self.space_switch_ikfk, targets, False),
        )
        cmds.menuItem(
            l="Transfer IKFK",
            rp="SW",
            parent=space_switch,
            command=partial(self.space_switch_ikfk, targets, True),
        )

        cmds.setParent(self.menu, menu=True)
        cmds.menuItem(l="Reset FK", rp="SE", command=partial(self.reset_fk, targets))

    def reset_fk(self, targets: list[str], _flag: object) -> None:
        root = control_util.get_component_root(targets[0])
        if not root:
            raise ValueError("could not found root")

        controllers = control_util.get_component_controllers(root)
        fk_controllers = [x for x in controllers if "fk" in x]

        import pymel.core as pm

        for target in fk_controllers:
            node = pm.PyNode(target)
            transform.resetTransform(node)

    def space_switch_ikfk(self, targets: list[str], transfer: bool, _flag: object) -> None:
        current_namespace = ":".join(targets[0].split(":")[:-1])
        root = control_util.get_component_root(targets[0])
        if not root:
            raise Exception("could not found root")
        ikfk_attr = "wing_blend"
        uiHost_name = control_util.get_ui_host(targets[0])
        all_controllers = control_util.get_component_controllers(root)
        controls = _collect_ikfk_controls(all_controllers)
        _validate_ikfk_controls(controls, uiHost_name)

        ik = cast("str", controls["ik"])
        upv = cast("str", controls["upv"])
        ik_rot = cast("str", controls["ik_rot"])
        hand_ik = cast("str", controls["hand_ik"])
        hand_ik_rot = cast("str", controls["hand_ik_rot"])
        fks = controls["fks"]
        uiHost_name = cast("str", uiHost_name)

        if transfer:
            control.IkFkTransfer.showUI(None, ikfk_attr, uiHost_name, fks, ik, upv, hand_ik, ik_rot, hand_ik_rot)
        else:
            control.ikFkMatch(current_namespace, ikfk_attr, uiHost_name, fks, ik, upv, hand_ik, ik_rot, hand_ik_rot)
