# -*- coding: utf-8 -*-
"""Module for hook right mouse button using rmbmenuhook."""
"""https://github.com/bohdon/maya-workflowtools/tree/main/src/workflowtools/scripts/rmbmenuhook"""
import os
import re
import sys
import six
from functools import partial

import maya.cmds as cmds

from mgear.core import (
    transform,
)

from ymt_components import rmbmenu
from ymt_shifter_utility import control_util
from . import control

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

    comp_name = os.path.basename(os.path.dirname(__file__))
  
    def build_specialized(self, targets):
        # self.menu is the parent marking menu that menuItems should be attached to
        cmds.setParent(self.menu, m=True)

        root = control_util.get_component_root(targets[0])
        # choices = control.get_head_ref_choices(root)
        space_switch = cmds.menuItem(l='Space Switch', rp='W', subMenu=True)

        # for i, choice in enumerate(choices):
        #     cmds.menuItem(l="Switch Head Ref to {}".format(choice), parent=space_switch, command=partial(self.space_switch_head, targets, i, False))

        cmds.menuItem(l='Switch IKFK', rp='NW', parent=space_switch, command=partial(self.space_switch_ikfk, targets, False))
        cmds.menuItem(l='Transfer IKFK', rp='SW', parent=space_switch, command=partial(self.space_switch_ikfk, targets, True))

        cmds.setParent(self.menu, menu=True)
        cmds.menuItem(l="Reset FK", rp='SE', command=partial(self.reset_fk, targets))

    def reset_fk(self, targets, flag):
        # type: (List[Text], bool) -> None

        root = control_util.get_component_root(targets[0])
        controllers = control_util.get_component_controllers(root)
        fk_controllers = [x for x in controllers if "fk" in x]

        import pymel.core as pm
        for target in fk_controllers:
            node = pm.PyNode(target)
            transform.resetTransform(node)

    def space_switch_head(self, targets, choice_index, transfer, flag):
        print(targets, choice_index, transfer)
        root = control_util.get_component_root(targets[0])

        try:
            control.switch_head_ref(root, choice_index)
        except:
            import traceback
            traceback.print_exc()

    def space_switch_ikfk(self, targets, transfer, flag):

        current_namespace = ":".join(targets[0].split(":")[:-1])
        root = control_util.get_component_root(targets[0])
        if not root:
            raise Exception("could not found root")
        ikfk_attr = "arm_blend"
        uiHost_name = control_util.get_ui_host(targets[0])
        all_controllers = control_util.get_component_controllers(root)

        ik = None
        upv = None
        ikRot = None
        fks = []

        for c in all_controllers:
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
