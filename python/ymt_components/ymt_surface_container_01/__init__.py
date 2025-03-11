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
            Optional,  # noqa: F401
            Dict,  # noqa: F401
            List,  # noqa: F401
            Tuple,  # noqa: F401
            Pattern,  # noqa: F401
            Callable,  # noqa: F401
            Any,  # noqa: F401
            Text,  # noqa: F401
            Generator,  # noqa: F401
            Union  # noqa: F401
        )
        from pathlib import Path  # NOQA: F401, F811 pylint: disable=unused-import,reimported
        from types import ModuleType  # NOQA: F401 pylint: disable=unused-import
        from six.moves import reload_module as reload  # NOQA: F401 pylint: disable=unused-import

from logging import (  # noqa:F401 pylint: disable=unused-import, wrong-import-order
    StreamHandler,
    getLogger,
    # WARN,
    DEBUG,
    INFO
)

try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm

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
    def addObjects(self):
        """Add all the objects needed to create the component."""

        self.WIP = self.options["mode"]

        # --------------------------------------------------------------------
        guide_objects = self.guide.getObjects(self.guide.root)
        guide_surface = guide_objects["sliding_surface"]
        self.sliding_surface = pm.duplicate(guide_surface)[0]
        cmds.rename(self.sliding_surface.name(), self.getName("surface"))
        cmds.parent(self.sliding_surface.name(), self.root.name())
        self.sliding_surface.visibility.set(False)
        cmds.makeIdentity(self.sliding_surface.name(), apply=True, t=1,  r=1, s=1, n=0, pn=1)

    def _visi_off_lock(self, obj):
        """Short cuts."""
        obj.visibility.set(False)
        ymt_util.setKeyableAttributesDontLockVisibility(obj, [])
        cmds.setAttr("{}.visibility".format(obj.name()), l=False)

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Create the anim and setupr rig attributes for the component"""
        pass

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        pass

    # =====================================================
    # CONNECTOR
    # =====================================================
    def addConnection(self):
        pass

    def connect_standard(self):
        self.parent.addChild(self.root)

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        self.relatives["root"] = self.root
        self.controlRelatives["root"] = self.root
        self.aliasRelatives["root"] = "ctl"

        self.relatives["surface"] = self.sliding_surface
        self.controlRelatives["surface"] = self.sliding_surface
        self.aliasRelatives["surface"] = "surface"
