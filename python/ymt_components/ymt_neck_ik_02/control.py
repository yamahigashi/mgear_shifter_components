# import re
import sys
import six
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
from ymt_shifter_utility import control_util
from ymt_shifter_utility.control_util import get_ui_host
try:
    import gml_maya.node as node_utils
except ImportError:
    import gml_maya.util.node_util as node_utils

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


def get_head_ref_choices(root):
    # type: (Text) -> List[Text]

    uihost = control_util.get_ui_host(root)
    choices = control_util.get_attribute_choices(uihost, "neck_headref")
    return choices


def switch_head_ref(root, choice_index):
    # type: (Text, Text) -> None
    ns = ":".join(root.split(":")[:-1])
    host = control_util.get_ui_host(root)
    choices = get_head_ref_choices(root)
    controllers = control_util.get_component_controllers(root)

    anim_utils.changeSpace_with_namespace(
        ns,
        host,
        "neck_headref",
        choice_index,
        controllers + controllers  # the changeSpace can not handle well cyclic controllers
    )
