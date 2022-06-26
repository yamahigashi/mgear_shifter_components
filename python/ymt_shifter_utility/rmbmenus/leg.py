# -*- coding: utf-8 -*-
"""Module for hook right mouse button using rmbmenuhook."""
"""https://github.com/bohdon/maya-workflowtools/tree/main/src/workflowtools/scripts/rmbmenuhook"""
import re
import sys
import six
from functools import partial

import maya.cmds as cmds

# from Qt import QtWidgets
from mgear.core import (
    transform,
)

import mgear.core.anim_utils as anim_utils
import mgear.synoptic.utils as syn_utils

from ymt_components import rmbmenu
from ymt_synoptics.ymt_biped import control
from ymt_shifter_utility import control_util

from logging import (  # noqa:F401 pylint: disable=unused-import, wrong-import-order
    StreamHandler,
    getLogger,
    WARN,
    DEBUG,
    INFO
)

if sys.version_info >= (3, 0):  # pylint: disable=using-constant-test  # pylint: disable=using-constant-test, wrong-import-order
    # For type annotation
    from typing import (  # NOQA: F401 pylint: disable=unused-import
        Optional,
        Dict,
        List,
        Tuple,
        Pattern,
        Callable,
        Any,
        Text,
        Generator,
        Union
    )
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

    comp_name = [
        "leg_2jnt_01",
        "leg_2jnt_02",
        "leg_2jnt_freeTangents_01",
        "leg_3jnt_01",
        "leg_ms_2jnt_01",
        "ymt_foot_bk_01",
        "ymt_foot_bk_02",
        "ymt_foot_bk_03",
    ]

    EVENT_FILTER_FUNCTIONS = [
    ]
  
    def build_specialized(self, targets):
        # self.menu is the parent marking menu that menuItems should be attached to
        cmds.setParent(self.menu, menu=True)

        space_switch = cmds.menuItem(l='Space Switch', rp='W', subMenu=True)
        cmds.menuItem(l='Switch IKFK', rp='NW', parent=space_switch, command=partial(self.space_switch_ikfk, targets, False))
        cmds.menuItem(l='Transfer IKFK', rp='SW', parent=space_switch, command=partial(self.space_switch_ikfk, targets, True))

        cmds.setParent(self.menu, menu=True)
        cmds.menuItem(l="Reset Foot AUX", rp='SE', command=partial(self.reset_foot_aux, targets))

    def reset_foot_aux(self, targets, flag):
        # type: (List[Text], bool) -> None
        aux_controllers = self.get_foot_aux_controllers(targets)

        import pymel.core as pm
        for target in aux_controllers:
            node = pm.PyNode(target)
            transform.resetTransform(node)

    def get_foot_aux_controllers(self, targets):
        # type: (List[Text]) -> List[Text]

        for t in targets:
            if "leg" in t:
                leg_root = control_util.get_component_root(t)
                foot_root = leg_root.replace("leg", "foot")
                break
            
            if "foot" in t:
                foot_root = control_util.get_component_root(t)
                break

        else:
            raise Exception("foot component could not determined")

        controllers = control_util.get_component_controllers(foot_root)
        return controllers

    def get_leg_root(self, targets):
        # type: (List[Text]) -> Text
        for target in targets:
            root = control_util.get_component_root(target)
            if "leg" in root:
                return target

            elif "foot" in root:
                candidate = root.replace("foot", "leg")
                candidate = cmds.ls(candidate)
                if candidate and len(candidate) == 1:
                    return candidate[0]

        raise Exception("could not found the leg controller")

    def space_switch_ikfk(self, targets, transfer, flag):

        current_namespace = ":".join(targets[0].split(":")[:-1])
        leg_root = self.get_leg_root(targets)
        ikfk_attr = "leg_blend"
        uiHost_name = control_util.get_ui_host(targets[0])
        leg_controllers = control_util.get_component_controllers(leg_root)

        ik = None
        upv = None
        ikRot = None
        fks = []

        for c in leg_controllers:
            if re.search("fk[0-9]", c):
                fks.append(c)

            if "ik_ctl" in c:
                ik = c

            if "upv_ctl" in c:
                upv = c

            if "ikRot" in c:
                ikRot = c

        if transfer:
            control.IkFkTransfer.showUI(None, ikfk_attr, uiHost_name, fks, ik, upv, ikRot)
        else:
            control.ikFkMatch(current_namespace, ikfk_attr, uiHost_name, fks, ik, upv, ikRot)
