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
# from . import control

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
        cmds.menuItem(l="Reset FK", rp='SE', command=partial(self.reset_fk, targets))
        # cmds.menuItem(l="Select IKs", rp='N', command=partial(self.select_ik, targets))
        cmds.menuItem(l="Select IK0", rp='NE', command=partial(self.select_ik0, targets))
        cmds.menuItem(l="Select IK1", rp='NW', command=partial(self.select_ik1, targets))

    def reset_fk(self, targets, flag):
        # type: (List[Text], bool) -> None

        root = control_util.get_component_root(targets[0])
        controllers = control_util.get_component_controllers(root)
        controllers = [x for x in controllers if "fk" in x]

        import pymel.core as pm
        for target in controllers:
            node = pm.PyNode(target)
            transform.resetTransform(node)

    def select_ik(self, targets, flag):
        # type: (List[Text], bool) -> None

        root = control_util.get_component_root(targets[0])
        controllers = control_util.get_component_controllers(root)
        controllers = [x for x in controllers if "ik" in x]

        cmds.select(cl=True)
        for target in controllers:
            cmds.select(target, add=True)

    def select_ik0(self, targets, flag):
        # type: (List[Text], bool) -> None

        root = control_util.get_component_root(targets[0])
        controllers = control_util.get_component_controllers(root)
        controllers = [x for x in controllers if "ik0" in x]

        cmds.select(cl=True)
        for target in controllers:
            cmds.select(target, add=True)

    def select_ik1(self, targets, flag):
        # type: (List[Text], bool) -> None

        root = control_util.get_component_root(targets[0])
        controllers = control_util.get_component_controllers(root)
        controllers = [x for x in controllers if "ik1" in x]

        cmds.select(cl=True)
        for target in controllers:
            cmds.select(target, add=True)
