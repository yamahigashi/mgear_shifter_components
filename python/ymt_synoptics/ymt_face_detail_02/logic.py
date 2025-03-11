# import re

import maya.cmds as cmds
try:
    import mgear.pymaya as pm
except ImportError:
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



def hoge(rig, button):

    if button == QtCore.Qt.RightButton:
        hide_all()
    elif button == QtCore.Qt.MiddleButton:
        show_all()
    else:
        toggle(rig)


def hide_all():

    rig_models = [item for item in pm.ls(transforms=True) if item.hasAttr("is_rig")]

    for _rig in rig_models:
        cmds.setAttr("{}.ctl_vis".format(_rig.name()), 0)


def show_all():

    rig_models = [item for item in pm.ls(transforms=True) if item.hasAttr("is_rig")]

    for _rig in rig_models:
        cmds.setAttr("{}.ctl_vis".format(_rig.name()), 1)


def toggle(rig):

    current = cmds.getAttr("{}.ctl_vis".format(rig.name()))
    cmds.setAttr("{}.ctl_vis".format(rig.name()), abs(current - 1))
