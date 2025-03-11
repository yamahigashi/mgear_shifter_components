from mgear.synoptic.tabs import MainSynopticTab
from mgear.vendor.Qt import QtWidgets, QtCore
try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm

from mgear.synoptic import utils
from . import widget


##################################################
# SYNOPTIC TAB WIDGET
##################################################


class SynopticTab(MainSynopticTab, widget.Ui_baker):

    description = "Control_List"
    name = "Control_List"

    # ============================================
    # INIT
    def __init__(self, parent=None):
        super(SynopticTab, self).__init__(self, parent)

    def selAll_clicked(self):
        # type: () -> None
        model = utils.getModel(self)
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        selAll(model, modifiers)


def selAll(model, modifiers):
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
