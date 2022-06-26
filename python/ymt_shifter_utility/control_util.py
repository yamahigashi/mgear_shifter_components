# -*- coding: utf-8 -*-
"""Module for utility functions for manipulate mGear shifter controllers."""

import os
import re
import math
import sys
import abc
import six
# import itertools
from functools import partial

import maya.cmds as cmds
import maya.OpenMaya as om1
import maya.api.OpenMaya as om

from Qt import QtWidgets

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

from mgear.core.transform import (
    getTransform,
    setMatrixPosition,
    getTransformLookingAt,
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

handler = StreamHandler()
handler.setLevel(DEBUG)

logger = getLogger(__name__)
logger.setLevel(WARN)
logger.setLevel(DEBUG)
logger.setLevel(INFO)
logger.addHandler(handler)
logger.propagate = False

###############################################################################


def is_mgear_controller(obj):
    # type: (Text) -> bool
    return "isCtl" in cmds.listAttr(obj)


def get_component_type(obj):
    # type: (Text) -> Optional[Text]
    """Returns selected object's component type name."""

    if "compRoot" not in cmds.listAttr(obj):
        return None

    root = cmds.listConnections("{}.compRoot".format(obj), s=True, d=False) or []  # type: ignore
    if not root or len(root) == 0:
        logger.debug("could not find component root")
        return None

    comp_type = cmds.getAttr("{}.componentType".format(root[0]))
    return comp_type


def get_ui_host(obj):
    # type: (Text) -> Optional[Text]
    """Returns selected object's uiHost."""

    if "componentType" in cmds.listAttr(obj):
        connections = cmds.listConnections("{}.compCtl".format(obj), s=True, d=False) or []  # type: ignore
        connections = cmds.listConnections("{}.message".format(connections[0]), s=False, d=True, plugs=True) or []  # type: ignore

    else:
        connections = cmds.listConnections("{}.message".format(obj), s=False, d=True, plugs=True) or []  # type: ignore

    connections = [x for x in connections if "ctl_cnx" in x]

    if not connections:
        logger.warning("could not found uihost for %s", obj)
        return None

    if len(connections) > 1:
        logger.warning("multiple uihost found")

    return ".".join(connections[0].split(".")[:-1])


def get_component_root(obj):
    # type: (Text) -> Optional[Text]

    if obj.endswith("root"):
        roots = [obj]
    else:
        roots = cmds.listConnections("{}.compRoot".format(obj), s=True, d=False) or []

    if not roots or len(roots) == 0:
        logger.debug("could not find component roots")
        return None

    if len(roots) > 1:
        logger.warning("multiple root found %s for object(%s)", roots, obj)

    return roots[0]


def get_component_controllers(obj):
    # type: (Text) -> List[Text]

    root = get_component_root(obj)
    connections = cmds.listConnections("{}.compCtl".format(root), s=True, d=False)

    if not connections:
        logger.warning("no controller found for %s", obj)
        return []

    return connections


def get_attribute_choices(node, attr):
    # type: (Text, Text) -> List[Text]

    """Returns enum attribute's choices."""
    if not cmds.listAttr("{}.{}".format(node, attr)):
        logger.warning("%s has no attribute named %s", node, attr)
        return []

    res = cmds.attributeQuery(attr, node=node, listEnum=True)  # type: ignore
    if not res:
        logger.warning("%s attribute %s has no choises", node, attr)
        return []

    return res[0].split(":")  # type: ignore
