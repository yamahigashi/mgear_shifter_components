"""mGear shifter components"""
# pylint: disable=import-error,W0201,C0111,C0112
import sys

import maya.cmds as cmds


from mgear.shifter import component

import ymt_shifter_utility as ymt_util

if sys.version_info > (3, 0):
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from typing import (
            Optional,
            Dict,
            List,
            Tuple,
            Callable,
            Any,
            Text,
            Union
        )
        from re import Pattern
        from collections.abc import Generator
        from pathlib import Path
        from types import ModuleType
        from six.moves import reload_module as reload

from logging import (
    StreamHandler,
    getLogger,
    # WARN,
    DEBUG,
    INFO
)

import importlib
try:
    pm = importlib.import_module("mgear.pymaya")
except ImportError:
    pm = importlib.import_module("pymel.core")

handler = StreamHandler()
handler.setLevel(DEBUG)
logger = getLogger(__name__)
logger.setLevel(INFO)
logger.addHandler(handler)
logger.propagate = False


##########################################################
# COMPONENT
##########################################################
class Component(component.Main):
    """Shifter component Class"""

    # =====================================================
    # OBJECTS
    # =====================================================
    def addObjects(self) -> None:
        """Add all the objects needed to create the component."""

        self.WIP = self.options["mode"]

        # --------------------------------------------------------------------
        guide_surface = self.guide.getObjectByLocalName("sliding_surface")
        self.sliding_surface = pm.duplicate(guide_surface)[0]
        cmds.rename(self.sliding_surface.name(), self.getName("surface"))
        cmds.parent(self.sliding_surface.name(), self.root.name())
        self.sliding_surface.visibility.set(False)
        cmds.makeIdentity(self.sliding_surface.name(), apply=True, t=1,  r=1, s=1, n=0, pn=1)

    def _visi_off_lock(self, obj: object) -> None:
        """Short cuts."""
        obj.visibility.set(False)
        ymt_util.setKeyableAttributesDontLockVisibility(obj, [])
        cmds.setAttr("{}.visibility".format(obj.name()), l=False)

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self) -> None:
        """Create the anim and setupr rig attributes for the component"""
        pass

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self) -> None:
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        pass

    # =====================================================
    # CONNECTOR
    # =====================================================
    def addConnection(self) -> None:
        pass

    def connect_standard(self) -> None:
        self.parent.addChild(self.root)

    def setRelation(self) -> None:
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.root
        self.controlRelatives["root"] = self.root
        self.aliasRelatives["root"] = "ctl"

        self.relatives["surface"] = self.sliding_surface
        self.controlRelatives["surface"] = self.sliding_surface
        self.aliasRelatives["surface"] = "surface"
