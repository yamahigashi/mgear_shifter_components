import importlib
try:
    pm = importlib.import_module("mgear.pymaya")
except ImportError:
    pm = importlib.import_module("pymel.core")
import mgear


def install() -> None:
    """Install synotic menu
    """
    pm.setParent(mgear.menu_id, menu=True)
    pm.menuItem(divider=True)
    pm.menuItem(label="Synoptic (Legacy Picker)",
                command=str_open_synoptic)


str_open_synoptic = """
from mgear import synoptic
synoptic.open()
"""
