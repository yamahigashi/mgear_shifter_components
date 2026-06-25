import os

import importlib
try:
    pm = importlib.import_module("mgear.pymaya")
except ImportError:
    pm = importlib.import_module("pymel.core")

from ymt_synoptics.synoptic.tabs import MainSynopticTab
from mgear.vendor.Qt import QtWidgets, QtCore

from ymt_synoptics.synoptic import utils
from . import widget


##################################################
# SYNOPTIC TAB WIDGET
##################################################


class SynopticTab(MainSynopticTab, widget.Ui_biped_body):

    description = "biped"
    name = "biped"
    bgPath = os.path.join(os.path.dirname(__file__), "background.bmp")

    buttons = [
        {"name": "selRight"},
        {"name": "selLeft"},
        {"name": "keyRight"},
        {"name": "keyLeft"},
    ]

    # ============================================
    # INIT
    def __init__(self, parent: object=None) -> None:
        super(SynopticTab, self).__init__(self, parent)
        self.cbManager.selectionChangedCB(self.name, self.selectChanged)

    # ============================================
    # BUTTONS
    def selAll_clicked(self) -> None:
        model = utils.getModel(self)
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        selAll(model, modifiers)

    def selRight_clicked(self) -> None:
        model = utils.getModel(self)
        # i : num of fingers, j : finger length
        object_names = ["finger_R%s_fk%s_ctl" % (i, j)
                        for i in range(4) for j in range(3)]
        thumb_names = ["thumb_R0_fk%s_ctl" % j for j in range(3)]
        object_names.extend(thumb_names)
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        utils.selectObj(model, object_names, None, modifiers)

    def selLeft_clicked(self) -> None:
        model = utils.getModel(self)
        # i : num of fingers, j : finger length
        object_names = ["finger_L%s_fk%s_ctl" % (i, j)
                        for i in range(4) for j in range(3)]
        thumb_names = ["thumb_L0_fk%s_ctl" % j for j in range(3)]
        object_names.extend(thumb_names)
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        utils.selectObj(model, object_names, None, modifiers)

    def keyRight_clicked(self) -> None:
        model = utils.getModel(self)
        # i : num of fingers, j : finger length
        object_names = ["finger_R%s_fk%s_ctl" % (i, j)
                        for i in range(4) for j in range(3)]
        thumb_names = ["thumb_R0_fk%s_ctl" % j for j in range(3)]
        object_names.extend(thumb_names)
        utils.keyObj(model, object_names)

    def keyLeft_clicked(self) -> None:
        model = utils.getModel(self)
        # i : num of fingers, j : finger length
        object_names = ["finger_L%s_fk%s_ctl" % (i, j)
                        for i in range(4) for j in range(3)]
        thumb_names = ["thumb_L0_fk%s_ctl" % j for j in range(3)]
        object_names.extend(thumb_names)
        utils.keyObj(model, object_names)


def selAll(model: object, modifiers: object) -> None:
    """Select all controlers

    Args:
        model (PyNode): Rig top node
    """

    rig_models = [item for item in pm.ls(transforms=True)
                  if item.hasAttr("is_rig")]

    controlers = utils.getControlers(model)
    if modifiers == QtCore.Qt.ShiftModifier:  # shift
        pm.select(controlers, toggle=True)
    elif modifiers == QtCore.Qt.ControlModifier:  # shift
        pm.select(cl=True)
        rig_models = [item for item in pm.ls(transforms=True)
                      if item.hasAttr("is_rig")]
        for model in rig_models:
            controlers = utils.getControlers(model)
            pm.select(controlers, toggle=True)
    else:
        pm.select(controlers)
