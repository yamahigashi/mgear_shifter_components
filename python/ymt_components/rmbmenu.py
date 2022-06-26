# -*- coding: utf-8 -*-
"""Module for hook right mouse button using rmbmenuhook.
ref: https://github.com/bohdon/maya-workflowtools/tree/main/src/workflowtools/scripts/rmbmenuhook"""

import os
import re
import math
import sys
import abc
import six
# import itertools
from functools import partial

from maya import (
    cmds,
    mel,
)

import maya.OpenMaya as om1
import maya.api.OpenMaya as om

from Qt import (
    QtWidgets,
    QtCore,
)

from mgear import shifter
import mgear.shifter.component as component
import mgear.synoptic as synoptic

from mgear.core import (
    attribute,
    node,
    icon,
    # fcurve,
    vector,
)

from mgear.core.primitive import addTransform
# from mgear.shifter import naming

from mgear.core import (
    transform,
    curve,
    applyop,
    attribute,
    icon,
    fcurve,
    vector,
    meshNavigation,
    node,
    primitive,
    utils,
    anim_utils,
)

import rmbmenuhook

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

PY2 = sys.version_info[0] == 2
__MENU_CLASSES__ = {}  # type: Dict[Text, Tuple[ShifterMarkingMenu, int]]

handler = StreamHandler()
handler.setLevel(DEBUG)

logger = getLogger(__name__)
logger.setLevel(WARN)
logger.setLevel(DEBUG)
logger.setLevel(INFO)
logger.addHandler(handler)
logger.propagate = False

###############################################################################


def initialize():
    rmbmenuhook.enable()
    comp_list = shifter.getComponentDirectories()

    modules = get_modules(comp_list)
    load_modules(modules)

    import ymt_shifter_utility.rmbmenus.leg as leg
    reload(leg)
    add_to_menu("leg", leg.ShifterMarkingMenu, 20)


def add_to_menu(name, klass, priority):
    # type: (Text, ShifterMarkingMenu, int) -> None

    if name in list(__MENU_CLASSES__.keys()):
        # already loaded
        return

    __MENU_CLASSES__[name] = (klass, priority)
    rmbmenuhook.registerMenu(name, klass, priority)


def get_modules(component_directory):
    # type: (Dict[Text, List[Text]]) -> List[Text]
    comp_list = []

    trackLoadComponent = []
    for path, comps in component_directory.items():
        cmds.progressWindow(title='Loading Components',
                          progress=0,
                          max=len(comps))
        for comp_name in comps:
            cmds.progressWindow(e=True, step=1, status='\nLoading: %s' % comp_name)

            if comp_name == "__init__.py":
                continue

            elif comp_name in trackLoadComponent:
                logger.warning(
                    "Custom component name: %s, already in default "
                    "components. Names should be unique. This component is"
                    " not loaded" % comp_name)
                continue

            else:
                trackLoadComponent.append(comp_name)

            # check existence
            if not os.path.exists(os.path.join(path, comp_name, "__init__.py")):
                continue

            if not os.path.exists(os.path.join(path, comp_name, "rmbmenu.py")):
                continue

            comp_list.append(comp_name)

    cmds.progressWindow(e=True, endProgress=True)
    return comp_list


def load_modules(component_list):
    # type: (List[Text]) -> None

    for comp_name in component_list:
        if comp_name in list(__MENU_CLASSES__.keys()):
            # already loaded
            continue

        try:
            dirs = shifter.getComponentDirectories()
            defFmt = "mgear.core.shifter.component.{}.rmbmenu"
            customFmt = "{}.rmbmenu"

            module = utils.importFromStandardOrCustomDirectories(
                dirs, defFmt, customFmt, comp_name
            )
            six.moves.reload_module(module)  # type: ignore

        except Exception as e:
            import traceback
            logger.warning("%s can't be load. Error at import", comp_name)
            logger.error(e)
            logger.error(traceback.format_exc())
            continue

        if not getattr(module, "ShifterMarkingMenu"):
            logger.warning("module %s has no ShifterMarkingMenu class.", comp_name)
            continue

        add_to_menu(comp_name, module.ShifterMarkingMenu, 10)

    add_to_menu("__DEFAULT__", DefaultShifterMarkingMenu, 0)


@six.add_metaclass(abc.ABCMeta)
class ShifterMarkingMenu(rmbmenuhook.Menu):
    """The abstract base class to show RMB menu for mGrear shifter controllers."""

    comp_name = "" # type: Union[Text, List[Text]]  # must declared in each specialized class
    # comp_name = os.path.basename(os.path.dirname(__file__))

    object = None  # type: Optional[Text]  # the selected object when invoked the menu
    EVENT_FILTER_FUNCTIONS = []  # type: List[Callable]


    def shouldBuild(self):

        if not self.object:
            return False

        if not self.is_mgear_controller(self.object):
            return False

        if not self.is_mycomponent_controller(self.object):
            return False

        if not self.is_match_additional_conditians(self.object):
            return False

        return True

    def is_mgear_controller(self, obj):
        # type: (Text) -> bool
        return control_util.is_mgear_controller(obj)

    def is_mycomponent_controller(self, obj):
        # type: (Text) -> bool
        """Returns whether the selected object belongs to my component."""

        incoming = control_util.get_component_type(obj)

        if isinstance(self.comp_name, list):
            return incoming in self.comp_name
        else:
            return incoming == self.comp_name

    def is_match_additional_conditians(self, obj):
        # type: (Text) -> bool

        for func in self.EVENT_FILTER_FUNCTIONS:
            if not func(self.object):
                return False

        return True

    def build(self):
        targets = self.get_targets()
        self.build_default(targets)
        self.build_specialized(targets)

    def build_default(self, targets):
        cmds.setParent(self.menu, m=True)
        cmds.menuItem(label="Reset", radialPosition='S', command=partial(self.reset_transform, targets))
        cmds.menuItem(label="Select Controllers", radialPosition='N', command=partial(self.select_controllers, targets))

    def get_targets(self):
        # type: () -> List[Text]

        sel = cmds.ls(sl=True)
        if sel:
            return sel

        if not self.object:
            return []

        return [self.object]

    def reset_transform(self, targets, flag):
        # type: (List[Text], bool) -> None
        """Reset tragets transforms.

        If control-key is pressed when the command is executed,
        the flag to reset is set according to the current tool mode.
        Move , Rotate or Scale tool."""

        s = True
        r = True
        t = True

        if is_key_modifiers_pressed(QtCore.Qt.ControlModifier):
            tool_context = mel.eval("currentCtx;")
            if tool_context and "move" in tool_context.lower():
                r, s = False, False
            elif tool_context and "rotate" in tool_context.lower():
                t, s = False, False
            elif tool_context and "scale" in tool_context.lower():
                r, t = False, False

        if cmds.ls(sl=True):
            targets = cmds.ls(sl=True)

        import pymel.core as pm
        for target in targets:
            node = pm.PyNode(target)
            transform.resetTransform(node, t=t, r=r, s=s)

    def select_controllers(self, targets, flag):
        # type: (List[Text], bool) -> None

        all_controllers = []
        for target in targets:
            controllers = control_util.get_component_controllers(target)
            all_controllers.extend(controllers)

        cmds.select(all_controllers)

    @abc.abstractmethod
    def build_specialized(self, targets):
        pass


def is_key_modifiers_pressed(key):
    # type: (QtCore.Qt.KeyboardModifier) -> bool

    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == key


class DefaultShifterMarkingMenu(ShifterMarkingMenu):
    """To Show default MenuItems for modules without dedicated class."""

    comp_name = "__DEFAULT__"

    def shouldBuild(self):
        return self.is_mgear_controller(self.object)
  
    def build_specialized(self, targets):
        self.build_default(targets)
