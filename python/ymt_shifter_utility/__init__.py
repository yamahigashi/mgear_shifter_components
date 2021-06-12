# -*- coding: utf-8 -*-
from Qt import QtWidgets
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


def setKeyableAttributesDontLockVisibility(nodes,
                                           params=["tx", "ty", "tz",
                                                   "ro", "rx", "ry", "rz",
                                                   "sx", "sy", "sz"]):

    attribute.setKeyableAttributes(nodes, params)

    if not isinstance(nodes, list):
        nodes = [nodes]
        for n in nodes:
            n.setAttr("v", lock=False)
