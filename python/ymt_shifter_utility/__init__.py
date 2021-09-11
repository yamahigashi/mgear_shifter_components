# -*- coding: utf-8 -*-
import sys

from Qt import QtWidgets


import mgear.shifter.component as component
import mgear.synoptic as synoptic

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
)

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


def collect_synoptic_windows(parent=None):
    synoptics = []
    active_window = None
    for w in QtWidgets.QApplication.topLevelWidgets():
        if not w.isVisible():
            continue
        if parent and w == parent:
            continue
        if not w.children():
            continue
        if w.isActiveWindow():
            active_window = w
            continue

        if not isinstance(w, synoptic.Synoptic):
            continue

        if not w.windowTitle() and w.height() < 20:
            # workaround for Maya2019 outliner bug.
            continue

        synoptics.append(w)

    return synoptics


def show():
    wins = collect_synoptic_windows()
    for w in wins:
        w.showNormal()


def hide():
    wins = collect_synoptic_windows()
    for w in wins:
        w.showNormal()
        w.showMinimized()


def setKeyableAttributesDontLockVisibility(nodes, params=None):

    if not params:
        params = ["tx", "ty", "tz",
                  "ro", "rx", "ry", "rz",
                  "sx", "sy", "sz"]

    attribute.setKeyableAttributes(nodes, params)

    if not isinstance(nodes, list):
        nodes = [nodes]
        for n in nodes:
            n.setAttr("v", lock=False)


def getFullPath(start, routes=None):
    # type: (pm.nt.transform, List[pm.nt.transform]) -> List[pm.nt.transform]
    if not routes:
        routes = []

    if not start.getParent():
        return routes + [start, ]

    else:
        return getFullPath(start.getParent(), routes + [start, ])


def findPathAtoB(a, b):
    # type: (pm.nt.transform, pm.nt.transform) -> Tuple[List[pm.nt.transform], pm.nt.transform, List[pm.nt.transform]]
    """Returns route of A to B in formed Tuple[down(to root), turning point, up(to leaf)]"""
    # aPath = ["x", "a", "b", "c"]
    # bPath = ["b", "c"]
    # down [x, a]
    # turn b
    # up []

    aPath = getFullPath(a)
    bPath = getFullPath(b)

    return _findPathAtoB(aPath, bPath)


def _findPathAtoB(aPath, bPath):
    # type: (List, List) -> Tuple[List, Any, List]
    """Returns route of A to B in formed Tuple[down(to root), turning point, up(to leaf)]

    >>> aPath = ["x", "a", "b", "c"]
    >>> bPath = ["b", "c"]
    >>> d, c, u = _findPathAtoB(aPath, bPath)
    >>> d == ["x", "a"]
    True
    >>> c == "b"
    True
    >>> u == []
    True

    """
    down = []
    up = []
    sharedNode = None

    for u in aPath:
        if u in bPath:
            sharedNode = u
            break

        down.append(u)

    idx = bPath.index(sharedNode)
    up = list(reversed(bPath[:(idx)]))

    return down, sharedNode, up


def addCtlMetadata(self, ctl):
    # type: (component.Main, pm.datatypes.Transform) -> None

    name = ctl.name()

    attribute.addAttribute(ctl, "isCtl", "bool", keyable=False)
    attribute.addAttribute(ctl, "uiHost", "string", keyable=False)
    ctl.addAttr("uiHost_cnx", at='message', multi=False)
    # set the control Role for complex components. If the component is
    # of type control_01 or world_ctl the control role will default to None
    # since is only one control the role is not needed
    attribute.addAttribute(
        ctl, "ctl_role", "string", keyable=False, value=name)

    # mgear name. This keep track of the default shifter name. This naming
    # system ensure that each control has a unique id. Tools like mirror or
    # flip pose can use it to track symmetrical controls
    attribute.addAttribute(ctl,
                           "shifter_name",
                           "string",
                           keyable=False,
                           value=self.getName(name) + "_ctl")
    attribute.addAttribute(
        ctl, "side_label", "string", keyable=False, value=self.side)
    attribute.addAttribute(ctl,
                           "L_custom_side_label",
                           "string",
                           keyable=False,
                           value=self.options["side_left_name"])
    attribute.addAttribute(ctl,
                           "R_custom_side_label",
                           "string",
                           keyable=False,
                           value=self.options["side_right_name"])
    attribute.addAttribute(ctl,
                           "C_custom_side_label",
                           "string",
                           keyable=False,
                           value=self.options["side_center_name"])
