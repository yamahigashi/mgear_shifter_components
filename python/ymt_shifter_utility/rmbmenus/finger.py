# -*- coding: utf-8 -*-
"""Module for hook right mouse button using rmbmenuhook."""
"""https://github.com/bohdon/maya-workflowtools/tree/main/src/workflowtools/scripts/rmbmenuhook"""
import re
import sys
import six
from functools import partial

from maya import (
    mel,
    cmds,
)

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

    def check_name(obj):
        if "finger" in obj:
            return True

    comp_name = [
        "chain_01",
    ]

    EVENT_FILTER_FUNCTIONS = [
        check_name
    ]
  
    def build_specialized(self, targets):
        # self.menu is the parent marking menu that menuItems should be attached to
        cmds.setParent(self.menu, menu=True)
        cmds.menuItem(l="Select Row", rp='NW', command=partial(self.select_row, targets))
        cmds.menuItem(l="Select Col", rp='N', command=partial(self.select_col, targets))
        cmds.menuItem(l="Select All", rp='NE', command=partial(self.select_all, targets))

        cmds.setParent(self.menu, menu=True)
        # cmds.menuItem(l="Reset Foot AUX", rp='SE', command=partial(self.reset_foot_aux, targets))

    def __sel(self, targets):

        if len(targets) < 1:
            return

        cmds.select(cl=True)

        mel.eval("""select -r {};""".format(targets[0]))
        if len(targets) > 1:
            for t in targets[1:]:
                # cmds.select(t, toggle=True)
                mel.eval("""select -tgl {};""".format(t))

    def select_row(self, targets, flag):
        # type: (List[Text], bool) -> None

        controllers = self.get_same_row_controllers(targets)
        self.__sel(controllers)

    def select_col(self, targets, flag):
        # type: (List[Text], bool) -> None

        controllers = self.get_same_col_controllers(targets)
        self.__sel(controllers)

    def select_all(self, targets, flag):
        # type: (List[Text], bool) -> None

        controllers = self.get_same_col_controllers(targets)
        controllers = self.get_same_row_controllers(controllers)
        self.__sel(controllers)

    def get_same_row_controllers(self, targets):
        # type: (List[Text]) -> List[Text]

        def __inner__(obj):
            namespace = ":".join(obj.split(":")[:-1])
            base_name = obj.split(":")[-1]
            match = re.search("finger_(?P<side>[a-zA-Z])[0-9]+?_fk(?P<row_num>[0-9]+?)_", base_name)
            if not match:
                raise Exception("no match row number %s", obj)

            row_num = match.group("row_num")
            side = match.group("side")
            controllers = cmds.ls("{}:finger_{}*_fk{}*".format(namespace, side, row_num)) or []

            return controllers

        res = []
        for target in targets:
            res.extend(__inner__(target))

        return res

    def get_same_col_controllers(self, targets):
        # type: (List[Text]) -> List[Text]

        def __inner__(obj):
            namespace = ":".join(obj.split(":")[:-1])
            base_name = obj.split(":")[-1]
            match = re.search("finger_(?P<side>[a-zA-Z])(?P<col_num>[0-9]+?)_fk(?P<row_num>[0-9]+?)_", base_name)
            if not match:
                raise Exception("no match row number %s", obj)

            col_num = match.group("col_num")
            side = match.group("side")
            controllers = cmds.ls("{}:finger_{}{}_fk*".format(namespace, side, col_num)) or []

            return controllers

        res = []
        for target in targets:
            res.extend(__inner__(target))

        return res
