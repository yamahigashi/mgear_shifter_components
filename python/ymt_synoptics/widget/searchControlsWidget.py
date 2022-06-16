import sys
from maya import cmds
from mgear.vendor.Qt import QtWidgets
from mgear.synoptic import utils

from logging import getLogger, WARN, DEBUG, INFO  # noqa

if sys.version_info >= (3, 0):  # pylint: disable=using-constant-test
    # For type annotation
    from typing import Optional, Dict, List, Tuple, Pattern, Callable, Any, Text, Generator  # NOQA
    try:
        from _sre import SRE_Pattern
    except ImportError:
        pass


logger = getLogger(__name__)
logger.setLevel(INFO)


def getControlsFromSets(desiredSet, listToPopulate):
    """Crawl set and retrieve anything that is not another set

    Args:
        desiredSet (string): name of set to crawl
        listToPopulate (list): where to append found nodes
    """
    for child in cmds.sets(desiredSet, q=True):
        if cmds.nodeType(child) == "objectSet":
            getControlsFromSets(child, listToPopulate)
        else:
            listToPopulate.append(child)


def getBaseNames(nodes):
    """strip the nameSpace off of the list of provided nodes

    Args:
        nodes (list): of nodes with a namespace

    Returns:
        list: of nodes without namespaces
    """
    baseNodeNames = [utils.stripNamespace(x) for x in nodes]
    return baseNodeNames


def getMatching(token, toQuery):
    """use the token to search a list of strings, return all matching token

    Args:
        token (string): "l0"
        toQuery (list): of strings to check

    Returns:
        list: of matchings strings
    """
    matching = [q for q in toQuery
                if token.lower() in q.lower()]
    return matching


def getTokens(userInput):
    """splits up the userInput via commas, strips spaces

    Args:
        userInput (string): comma seperated search tokens, filters

    Returns:
        list: of all tokens that were seperated via comma
    """
    allTokens = userInput.replace(" ", "").split(',')
    return allTokens


class ControlListerUI(QtWidgets.QWidget):
    """widget for listing all controls under a namespace"""

    def __init__(self, parent=None):
        super(ControlListerUI, self).__init__(parent)
        # self.parent = parent
        # self.model = model
        self.model = None
        self.modelControls = []
        self.namespace = None
        self.gui()
        self.connectSignals()

    def connectSignals(self):
        """connect widgets/signals to the functions
        """
        self.searchLineEdit.textChanged.connect(self.queryNames)
        self.resultWidget.itemSelectionChanged.connect(self.specificSelection)
        self.selectAllButton.clicked.connect(self.selectAllResults)

    def displayResults(self, resultsToDisplay):
        """clear and display the provided list

        Args:
            resultsToDisplay (list): of results to display
        """
        self.resultWidget.clear()
        self.resultWidget.addItems(resultsToDisplay)

    def getNodeWithNameSpace(self, node):
        """In the future this will need to change to allow for set name prefix

        Args:
            node (string): name of the node

        Returns:
            string: name of node with namespace
        """
        if self.namespace.endswith(":"):
            ns = ""
        else:
            ns = "{0}:".format(self.namespace)
        return "{0}{1}".format(ns, node)

    def queryNames(self, userInput):
        """Take the userInput and query against all controls
        remove duplicates and sort

        Args:
            userInput (string): from UI
        """
        searchResults = set()
        # userInput = userInput.toString()
        allTokens = getTokens(userInput)
        [searchResults.update(getMatching(token, self.modelControls))
         for token in allTokens]
        searchResults = sorted(searchResults)
        self.displayResults(searchResults)

    def setControlsToQuery(self):
        """Query the controls set in the scene from the scene.
        TODO: Open this up to select multiple areas for query
        """
        setControls = []
        controlerSet = "{0}{1}".format(self.model, utils.CTRL_GRP_SUFFIX)
        if cmds.objExists(controlerSet):
            getControlsFromSets(controlerSet, setControls)
        baseControlNames = set(getBaseNames(setControls))
        self.modelControls = list(baseControlNames)

    def selectAllResults(self):
        """Select all items in results widget
        """
        self.resultWidget.clearSelection()
        self.resultWidget.selectAll()

    def specificSelection(self, *args):
        """When something is selected on the results widget, select it in core

        Args:
            *args: unised signal information
        """
        selectionList = []
        for item in self.resultWidget.selectedItems():
            selectionList.append(self.getNodeWithNameSpace(item.text()))
        cmds.select(selectionList)

    def refresh(self):
        """refresh the ui
        """
        self.model = utils.getModel(self)
        self.namespace = utils.getNamespace(self.model)
        self.searchLineEdit.clear()
        self.resultWidget.clear()
        self.setControlsToQuery()
        self.queryNames("")

    def gui(self):
        """set the widget layout and content
        """
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mainLayout)
        #  -------------------------------------------------------------------
        self.searchLineEdit = QtWidgets.QLineEdit()
        self.searchLineEdit.setPlaceholderText("Filter via ',' seperated...")
        self.selectAllButton = QtWidgets.QPushButton('Select All')
        self.mainLayout.addWidget(self.searchLineEdit)
        self.mainLayout.addWidget(self.selectAllButton)
        #  -------------------------------------------------------------------
        self.resultWidget = QtWidgets.QListWidget()
        self.resultWidget.setSpacing(4)
        self.resultWidget.setAlternatingRowColors(True)
        selMode = QtWidgets.QAbstractItemView.ExtendedSelection
        self.resultWidget.setSelectionMode(selMode)

        self.mainLayout.addWidget(self.resultWidget)

    def showEvent(self, event):  # @UnusedVariable
        self.refresh()


class toggleMeshesBase(QtWidgets.QPushButton):
    """Toggle Controllers visibility."""

    controller_groups = {
        # "mesh_name": ["controller_nodes"],
        "hair":   [],
        "cloth":  [],
        "weapon": [],
    }

    def __init__(self, *args, **kwargs):
        # type: (*str, **str) -> None
        super(toggleMeshesBase, self).__init__(*args, **kwargs)

    def mousePressEvent(self, event):
        # type: (QtCore.QEvent) -> None

        objects = None
        try:
            objects = str(self.property("group_name")).split(",")
        except Exception as e:
            logger.error(e)
            objects = None

        logger.info("objects %s", objects)
        if not objects:
            self.hide_all()
        else:
            if not objects[0]:
                self.hide_all()
            else:
                self.toggle(objects)

    def hide_all(self):
        logger.info("hide")
        for s in self.controller_groups:
            logger.info(s)
            self.setVis(s, False)

    def show(self, names):
        # type: (List[Text]) -> None

        for name in names:
            self.setVis(name, True)

    def setVis(self, name, visibility):
        # type: (Text, bool) -> None

        meshes = cmds.ls(name, recursive=True, type="transform")
        logger.info(meshes)
        if not meshes:
            return

        for mesh in meshes:
            if not cmds.listRelatives(mesh, children=True, type="mesh"):
                logger.info("has no mesh %s", mesh)
                continue
            logger.info(mesh)
            try:
                cmds.setAttr("{}.visibility".format(mesh), visibility)
            except RuntimeError:
                logger.error("could not set visibility %s", mesh)

        roots = self.controller_groups.get(name) or []
        try:
            for root in roots:
                nodes = cmds.ls(root, recursive=True)
                if nodes:
                    cmds.setAttr("{}.visibility".format(nodes[0]), visibility)

        except RuntimeError:
            logger.error("could not find %s", roots)

    def toggle(self, names):
        # type: (List[Text]) -> None

        for name in names:
            meshes = cmds.ls(name, recursive=True, type="transform")
            if not meshes:
                continue
            if not cmds.listRelatives(meshes, children=True, type="mesh"):
                continue

            for mesh in meshes:
                if not cmds.listRelatives(mesh, children=True, type="mesh"):
                    continue
                current = cmds.getAttr("{}.visibility".format(mesh))
                break

            try:
                self.setVis(name, not current)  # type: ignore  # possibly unbound
            except ValueError:
                self.setVis(name, True)
