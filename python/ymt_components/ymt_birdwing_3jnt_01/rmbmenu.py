"""Module for hook right mouse button using rmbmenuhook."""

# https://github.com/bohdon/maya-workflowtools/tree/main/src/workflowtools/scripts/rmbmenuhook
import os
import re
from functools import partial
from logging import DEBUG, INFO, WARN, StreamHandler, getLogger

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
        controllers = control_util.get_component_controllers(root)
        fk_controllers = [x for x in controllers if "fk" in x]

        import pymel.core as pm

        for target in fk_controllers:
            node = pm.PyNode(target)
            transform.resetTransform(node)

    def space_switch_head(self, targets: list[str], choice_index: int, transfer: bool, _flag: object) -> None:
        print(targets, choice_index, transfer)
        root = control_util.get_component_root(targets[0])

        try:
            control.switch_head_ref(root, choice_index)
        except Exception:
            import traceback

            traceback.print_exc()

    def space_switch_ikfk(self, targets: list[str], transfer: bool, _flag: object) -> None:
        current_namespace = ":".join(targets[0].split(":")[:-1])
        root = control_util.get_component_root(targets[0])
        if not root:
            raise Exception("could not found root")
        ikfk_attr = "wing_blend"
        uiHost_name = control_util.get_ui_host(targets[0])
        all_controllers = control_util.get_component_controllers(root)

        ik = None
        upv = None
        palm = None
        hand_ik = None
        fks = []

        for c in all_controllers:
            if re.search("fk[0-9]", c):
                fks.append(c)

            if "hand_ik_ctl" in c:
                hand_ik = c

            elif "palm_ctl" in c:
                palm = c

            elif "ik_ctl" in c:
                ik = c

            if "upv_ctl" in c:
                upv = c

        fks.sort()

        if transfer:
            control.IkFkTransfer.showUI(None, ikfk_attr, uiHost_name, fks, ik, upv, hand_ik, palm)
        else:
            control.ikFkMatch(current_namespace, ikfk_attr, uiHost_name, fks, ik, upv, hand_ik, palm)
