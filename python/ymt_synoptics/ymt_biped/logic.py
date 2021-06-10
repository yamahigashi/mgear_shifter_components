# import re

import maya.cmds as cmds
import pymel.core as pm

import mgear
from mgear.vendor.Qt import QtCore, QtWidgets
from mgear.core import attribute
from mgear.core import pyqt
import mgear.core.anim_utils as anim_utils
import mgear.synoptic.utils as syn_utils
import mgear.core.utils as utils
import gml_maya.decorator as deco

if False:
    # For type annotation
    from typing import Optional, Dict, List, Tuple, Pattern, Callable, Any, Text  # NOQA



def hoge(rig, button, group_name=None):

    if button == QtCore.Qt.RightButton:
        hide_all()
    elif button == QtCore.Qt.MiddleButton:
        show_all()
    else:
        toggle(rig, group_name)


def hide_all():

    rig_models = [item for item in pm.ls(transforms=True) if item.hasAttr("is_rig")]

    for _rig in rig_models:
        cmds.setAttr("{}.ctl_vis".format(_rig.name()), 0)


def show_all():

    rig_models = [item for item in pm.ls(transforms=True) if item.hasAttr("is_rig")]

    for _rig in rig_models:
        cmds.setAttr("{}.ctl_vis".format(_rig.name()), 1)


def toggle(rig, group_name=None):

    ns = ":".join(rig.name().split(":")[:-1])
    group_items = []

    if group_name:
        print(group_name)
        if isinstance(group_name, list):
            for gn in group_name:
                set_fullpath = "{}:{}".format(ns, gn)
                if cmds.ls(set_fullpath):
                    group_items.extend(cmds.sets(set_fullpath, q=True) or [])
        else:
            set_fullpath = "{}:{}".format(ns, group_name)
            if cmds.ls(set_fullpath):
                group_items = cmds.sets(set_fullpath, q=True)

    if group_items:
        for item in group_items:
            visible = cmds.getAttr("{}.visibility".format(item))
            try:
                cmds.setAttr("{}.visibility".format(item), lock=False)
            except RuntimeError:
                pass
            try:
                cmds.setAttr("{}.visibility".format(item), not visible)
            except RuntimeError:
                pass

    else:
        current = cmds.getAttr("{}.ctl_vis".format(rig.name()))
        cmds.setAttr("{}.ctl_vis".format(rig.name()), abs(current - 1))
