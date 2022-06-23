##################################################
# GLOBAL
##################################################
import re
import traceback

import maya.cmds as cmds
import pymel.core as pm

import mgear
import mgear.core.pyqt as gqt

import mgear.core.transform as tra
import mgear.synoptic.utils as syn_uti
# import mgear.core.synoptic.widgets as syn_widget

QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()


class AbstractControllerButton(QtWidgets.QPushButton):

    def __init__(self, *args, **kwargs):
        super(AbstractControllerButton, self).__init__(*args, **kwargs)
        self.root = None
        self.side = "C"
        self.name = None
        self.index = 0
        self.lookupControllers()

    def lookupControllers(self):

        for prop in self.dynamicPropertyNames():
            print("setattr {}, {}".format(prop, self.property(prop)))
            setattr(self, prop, self.property(prop))

        # FIXME:
        for attr in ["ik", "fk0", "fks", "ik_ctl", "ikRot", "upv"]:
            _prop = self.property(attr)
            if _prop:
                _m = re.search(r"([LRC])(\d+)", _prop)
                if _m:
                    self.name = _prop.split("_")[0]
                    self.side = str(_m.groups(1))
                    self.index = int(_m.groups(2))
                    break

    def isControllerSetup(self):
        return False

    def getName(self, name, side=None):
        """Return the name for component element

        Args:
            name (str): The name to concatenate to component name. (Optional)
            side (str): The side (Optional).

        Returns:
            str: The name.

        """
        if side is None:
            side = self.side

        name = str(name)

        return "_".join([self.name, side + str(self.index), name])
