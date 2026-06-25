import os
from contextlib import suppress
from types import ModuleType
from typing import Optional

import pymel.core as pm

from maya.app.general.mayaMixin import MayaQDockWidget
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

import mgear
from mgear.core import pyqt
from mgear.vendor.Qt import QtGui, QtCore, QtWidgets
import mgear.core.utils


SYNOPTIC_WIDGET_NAME = "synoptic_view"
SYNOPTIC_ENV_KEY = "MGEAR_SYNOPTIC_PATH"

SYNOPTIC_DIRECTORIES = mgear.core.utils.gatherCustomModuleDirectories(
    SYNOPTIC_ENV_KEY,
    os.path.join(os.path.dirname(__file__), "tabs"))


##################################################
# OPEN
##################################################
def open(*_args: QtCore.QObject) -> None:
    # open the synoptic dialog, without clean old instances
    pyqt.showDialog(Synoptic, False)


def importTab(tabName: str) -> ModuleType:
    """Import Synoptic Tab

    Args:
        tabName (Str): Synoptic tab name

    Returns:
        module: Synoptic tab module
    """
    import ymt_synoptics.synoptic as syn
    dirs = syn.SYNOPTIC_DIRECTORIES
    defFmt = "ymt_synoptics.synoptic.tabs.{}"
    customFmt = "{0}"

    module = mgear.core.utils.importFromStandardOrCustomDirectories(
        dirs, defFmt, customFmt, tabName)
    return module


##################################################
# SYNOPTIC
##################################################
class Synoptic(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    """Synoptic Main class"""

    default_height = 790
    default_width = 325
    margin = 15 * 2

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        self.toolName = SYNOPTIC_WIDGET_NAME
        # Delete old instances of the componet settings window.
        pyqt.deleteInstances(self, MayaQDockWidget)
        super(Synoptic, self).__init__(parent)
        self.create_widgets()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    def closeEvent(self, evnt: QtCore.QEvent) -> None:
        """oon close, kill all callbacks

        Args:
            evnt (Qt.QEvent): Close event called
        """

        # self.cbManager.removeAllManagedCB()
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, SynopticTabWrapper):
                synTab, resultBool = tab.searchMainSynopticTab()
                if resultBool and hasattr(synTab, "cbManager"):
                    synTab.cbManager.removeAllManagedCB()
            tab.close()
        self.tabs.clear()
        super(Synoptic, self).closeEvent(evnt)

    def create_widgets(self) -> None:
        self.setupUi()

        # Connect Signal
        self.refresh_button.clicked.connect(self.updateModelList)
        self.model_list.currentIndexChanged.connect(self.updateTabs)

        # Initialise
        self.updateModelList()

    def setupUi(self) -> None:
        # Widgets
        self.setObjectName(SYNOPTIC_WIDGET_NAME)
        self.resize(560, 775)

        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QtCore.QSize(0, 0))

        self.gridLayout_2 = QtWidgets.QGridLayout(self)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setObjectName("gridLayout_2")

        self.mainContainer = QtWidgets.QGroupBox(self)

        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)

        sizePolicy.setHeightForWidth(
            self.mainContainer.sizePolicy().hasHeightForWidth())

        self.mainContainer.setSizePolicy(sizePolicy)
        self.mainContainer.setMinimumSize(QtCore.QSize(0, 0))
        self.mainContainer.setObjectName("mainContainer")

        self.gridLayout_3 = QtWidgets.QGridLayout(self.mainContainer)
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_3.setObjectName("gridLayout_3")

        # header boxies
        self.hbox = QtWidgets.QHBoxLayout()
        self.hbox.setContentsMargins(5, 5, 5, 5)
        self.hbox.setObjectName("hbox")

        self.model_list = QtWidgets.QComboBox(self.mainContainer)
        self.model_list.setObjectName("model_list")
        self.model_list.setMinimumSize(QtCore.QSize(0, 23))

        self.refresh_button = QtWidgets.QPushButton(self.mainContainer)
        self.refresh_button.setObjectName("refresh_button")
        self.refresh_button.setText("Refresh")

        self.hbox.addWidget(self.model_list)
        self.hbox.addWidget(self.refresh_button)
        self.gridLayout_3.addLayout(self.hbox, 0, 0, 1, 1)

        # synoptic main area
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.scrollArea = QtWidgets.QScrollArea(self.mainContainer)

        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(
            self.scrollArea.sizePolicy().hasHeightForWidth())

        self.scrollArea.setSizePolicy(sizePolicy)
        self.scrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.scrollArea.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded)

        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setAlignment(QtCore.Qt.AlignCenter)
        self.scrollArea.setObjectName("scrollArea")

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setSizePolicy(sizePolicy)
        self.tabs.setObjectName("tabs")

        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(
            self.tabs.sizePolicy().hasHeightForWidth())

        self.tabs.setSizePolicy(sizePolicy)
        self.tabs.setObjectName("synoptic_tab")
        self.scrollArea.setWidget(self.tabs)

        self.gridLayout.addWidget(self.scrollArea, 0, 0, 1, 1)
        self.gridLayout_3.addLayout(self.gridLayout, 2, 0, 1, 1)
        self.gridLayout_2.addWidget(self.mainContainer, 0, 0, 1, 1)

    # Singal Methods =============================
    def updateModelList(self) -> None:
        # avoiding unnecessary firing currentIndexChanged event before
        # finish to model_list
        with suppress(RuntimeError):
            self.model_list.currentIndexChanged.disconnect()

        rig_models = [item for item in pm.ls(transforms=True)
                      if item.hasAttr("is_rig")]

        self.model_list.clear()
        for item in rig_models:
            self.model_list.addItem(item.name(), item.name())

        # restore event and update tabs for reflecting self.model_list
        self.model_list.currentIndexChanged.connect(self.updateTabs)
        self.updateTabs()

    def updateTabs(self) -> None:

        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, SynopticTabWrapper):
                synTab, resultBool = tab.searchMainSynopticTab()
                if resultBool and hasattr(synTab, "cbManager"):
                    synTab.cbManager.removeAllManagedCB()
            tab.close()
        self.tabs.clear()

        currentModelName = self.model_list.currentText()
        currentModels = pm.ls(currentModelName)
        if not currentModels:
            return

        tab_names = currentModels[0].getAttr("synoptic").split(",")

        max_h = 0
        max_w = 0
        for i, tab_name in enumerate(tab_names):
            try:
                if tab_name:
                    # instantiate SynopticTab widget
                    module = importTab(tab_name)
                    synoptic_tab = module.SynopticTab()

                    # set minimum size for auto fit (stretch) scroll area
                    if synoptic_tab.minimumHeight() == 0:
                        synoptic_tab.setMinimumHeight(synoptic_tab.height())
                    if synoptic_tab.minimumWidth() == 0:
                        synoptic_tab.setMinimumWidth(synoptic_tab.width())

                    # store tab size for set container size later
                    h = synoptic_tab.minimumHeight()
                    w = synoptic_tab.minimumWidth()

                    max_h = h if max_h < h else max_h
                    max_w = w if max_w < w else max_w

                    tab = self.wrapTabContents(synoptic_tab)
                    self.tabs.insertTab(i, tab, tab_name)

                else:
                    mes = "No synoptic tabs for %s" % \
                          self.model_list.currentText()

                    pm.displayWarning(mes)

            except Exception as e:
                import traceback
                traceback.print_exc()

                mes = "Synoptic tab: %s Loading fail {0}\n{1}".format(
                    tab_name, e)

                pm.displayError(mes)

        max_h = self.default_height if max_h == 0 else max_h
        max_w = self.default_width if max_w == 0 else max_w
        header_space = 45
        self.resize(max_w + self.margin, max_h + self.margin + header_space)

    def wrapTabContents(self, synoptic_tab: QtWidgets.QWidget) -> QtWidgets.QWidget:

        # horizontal layout:
        #     spacer >>  SynopticTab << spacer

        wrapperWidget = SynopticTabWrapper()
        wrapperWidget.setGeometry(QtCore.QRect(0, 0, 10, 10))
        wrapperWidget.setObjectName("wrapperWidget")

        horizontalLayout = QtWidgets.QHBoxLayout(wrapperWidget)
        horizontalLayout.setContentsMargins(0, 0, 0, 0)
        horizontalLayout.setObjectName("horizontalLayout")

        spacer_left = QtWidgets.QSpacerItem(0,
                                            0,
                                            QtWidgets.QSizePolicy.Expanding,
                                            QtWidgets.QSizePolicy.Minimum)

        spacer_right = QtWidgets.QSpacerItem(0,
                                             0,
                                             QtWidgets.QSizePolicy.Expanding,
                                             QtWidgets.QSizePolicy.Minimum)

        wrapperWidget.setSpacerLeft(spacer_left)
        wrapperWidget.setSynopticTab(synoptic_tab)

        horizontalLayout.addItem(spacer_left)
        horizontalLayout.addWidget(synoptic_tab)
        horizontalLayout.addItem(spacer_right)

        horizontalLayout.setStretch(0, 1)
        horizontalLayout.setStretch(1, 0)
        horizontalLayout.setStretch(2, 1)

        return wrapperWidget


class SynopticTabWrapper(QtWidgets.QWidget):
    """Class for handling mouse rubberband Selection

    Class for handling mouse rubberband within spacer and synoptic tab that
    is children of.
    """

    zoom_step = 1.1
    zoom_minimum = 0.5
    zoom_maximum = 3.0

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:

        super(SynopticTabWrapper, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.rubberband = QtWidgets.QRubberBand(
            QtWidgets.QRubberBand.Rectangle, self)

        self.offset = QtCore.QPoint()
        self._zoom = 1.0
        self._zoom_target = None
        self._zoom_target_size = None
        self._zoom_geometries = {}
        self._zoom_minimum_sizes = {}
        self._zoom_maximum_sizes = {}
        self._zoom_fonts = {}
        self._zoom_icon_sizes = {}
        self._zoom_layout_margins = {}
        self._zoom_layout_spacings = {}
        self._zoom_event_filter_widgets = []
        self._pan_active = False
        self._pan_moved = False
        self._pan_watched = None
        self._pan_press_pos = QtCore.QPoint()
        self._pan_press_global_pos = QtCore.QPoint()
        self._pan_hbar_value = 0
        self._pan_vbar_value = 0
        self._forwarding_pan_click = False
        self._installZoomEventFilter(self)

    def setSpacerLeft(self, spacer: QtWidgets.QSpacerItem) -> None:

        # QSpacerItem can't be traversed from its parent widget
        self.spacer = spacer

    def setSynopticTab(self, synoptic_tab: QtWidgets.QWidget) -> None:

        self._zoom_target = synoptic_tab
        self._installZoomEventFilter(synoptic_tab)

    # ------------------------------------------------------------------------
    # utility for ctrl + mouse wheel zoom
    # ------------------------------------------------------------------------
    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:

        if self._forwarding_pan_click:
            return False

        if event.type() == QtCore.QEvent.Wheel and self._isZoomWheelEvent(event):
            self._zoomWheelEvent(event)
            return True

        if event.type() == QtCore.QEvent.MouseButtonPress and self._isPanPressEvent(event):
            self._startPan(watched, event)
            return True

        if event.type() == QtCore.QEvent.MouseMove and self._isPanMoveEvent(event):
            self._panMoveEvent(event)
            return True

        if event.type() == QtCore.QEvent.MouseButtonRelease and self._isPanReleaseEvent(event):
            self._panReleaseEvent(event)
            return True

        return super(SynopticTabWrapper, self).eventFilter(watched, event)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:

        if self._isZoomWheelEvent(event):
            self._zoomWheelEvent(event)
            return

        super(SynopticTabWrapper, self).wheelEvent(event)

    # ------------------------------------------------------------------------
    # utility for middle mouse drag panning
    # ------------------------------------------------------------------------
    def _isPanPressEvent(self, event: QtGui.QMouseEvent) -> bool:

        return event.button() == QtCore.Qt.MiddleButton

    def _isPanMoveEvent(self, event: QtGui.QMouseEvent) -> bool:

        return (
            self._pan_active
            and bool(int(event.buttons()) & int(QtCore.Qt.MiddleButton))
        )

    def _isPanReleaseEvent(self, event: QtGui.QMouseEvent) -> bool:

        return self._pan_active and event.button() == QtCore.Qt.MiddleButton

    def _startPan(self, watched: QtCore.QObject, event: QtGui.QMouseEvent) -> None:

        scroll_area = self._getScrollArea()
        if scroll_area is None:
            event.ignore()
            return

        self._pan_active = True
        self._pan_moved = False
        self._pan_watched = watched
        self._pan_press_pos = QtCore.QPoint(self._eventPos(event))
        self._pan_press_global_pos = QtCore.QPoint(self._eventGlobalPos(event))
        self._pan_hbar_value = scroll_area.horizontalScrollBar().value()
        self._pan_vbar_value = scroll_area.verticalScrollBar().value()
        event.accept()

    def _panMoveEvent(self, event: QtGui.QMouseEvent) -> None:

        scroll_area = self._getScrollArea()
        if scroll_area is None:
            event.ignore()
            return

        delta = self._eventGlobalPos(event) - self._pan_press_global_pos
        if not self._pan_moved:
            if delta.manhattanLength() < QtWidgets.QApplication.startDragDistance():
                event.accept()
                return
            self._pan_moved = True
            self.setCursor(QtCore.Qt.ClosedHandCursor)

        scroll_area.horizontalScrollBar().setValue(self._pan_hbar_value - delta.x())
        scroll_area.verticalScrollBar().setValue(self._pan_vbar_value - delta.y())
        event.accept()

    def _panReleaseEvent(self, event: QtGui.QMouseEvent) -> None:

        pan_moved = self._pan_moved
        watched = self._pan_watched
        self._pan_active = False
        self._pan_moved = False
        self._pan_watched = None

        if pan_moved:
            self.unsetCursor()
        elif isinstance(watched, QtWidgets.QWidget):
            self._forwardMiddleClick(watched, event)

        event.accept()

    def _forwardMiddleClick(
            self,
            widget: QtWidgets.QWidget,
            release_event: QtGui.QMouseEvent) -> None:

        release_global_pos = self._eventGlobalPos(release_event)
        release_pos = widget.mapFromGlobal(release_global_pos)
        press_event = self._makeMouseEvent(
            QtCore.QEvent.MouseButtonPress,
            self._pan_press_pos,
            self._pan_press_global_pos,
            QtCore.Qt.MiddleButton,
            QtCore.Qt.MiddleButton,
            release_event.modifiers())
        forwarded_release_event = self._makeMouseEvent(
            QtCore.QEvent.MouseButtonRelease,
            release_pos,
            release_global_pos,
            QtCore.Qt.MiddleButton,
            QtCore.Qt.NoButton,
            release_event.modifiers())

        self._forwarding_pan_click = True
        try:
            QtWidgets.QApplication.sendEvent(widget, press_event)
            QtWidgets.QApplication.sendEvent(widget, forwarded_release_event)
        finally:
            self._forwarding_pan_click = False

    def _eventPos(self, event: QtGui.QMouseEvent) -> QtCore.QPoint:

        if hasattr(event, "pos"):
            return event.pos()

        return event.position().toPoint()

    def _eventGlobalPos(self, event: QtGui.QMouseEvent) -> QtCore.QPoint:

        if hasattr(event, "globalPos"):
            return event.globalPos()

        return event.globalPosition().toPoint()

    def _makeMouseEvent(
            self,
            event_type: int,
            pos: QtCore.QPoint,
            global_pos: QtCore.QPoint,
            button: int,
            buttons: int,
            modifiers: int) -> QtGui.QMouseEvent:

        try:
            return QtGui.QMouseEvent(
                event_type,
                pos,
                global_pos,
                button,
                buttons,
                modifiers)
        except TypeError:
            pos_f = QtCore.QPointF(pos)
            global_pos_f = QtCore.QPointF(global_pos)

        try:
            return QtGui.QMouseEvent(
                event_type,
                pos_f,
                global_pos_f,
                button,
                buttons,
                modifiers)
        except TypeError:
            return QtGui.QMouseEvent(
                event_type,
                pos_f,
                pos_f,
                global_pos_f,
                button,
                buttons,
                modifiers)

    def _getScrollArea(self) -> Optional[QtWidgets.QScrollArea]:

        parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, QtWidgets.QScrollArea):
                return parent
            parent = parent.parentWidget()

        return None

    def _isZoomWheelEvent(self, event: QtGui.QWheelEvent) -> bool:

        return bool(int(event.modifiers()) & int(QtCore.Qt.ControlModifier))

    def _zoomWheelEvent(self, event: QtGui.QWheelEvent) -> None:

        delta = self._wheelDelta(event)
        if delta == 0:
            event.ignore()
            return

        steps = delta / 120.0
        self.setZoom(self._zoom * (self.zoom_step ** steps))
        event.accept()

    def _wheelDelta(self, event: QtGui.QWheelEvent) -> int:

        if hasattr(event, "angleDelta"):
            angle_delta = event.angleDelta()
            if not angle_delta.isNull():
                return angle_delta.y()

        if hasattr(event, "pixelDelta"):
            pixel_delta = event.pixelDelta()
            if not pixel_delta.isNull():
                return pixel_delta.y()

        if hasattr(event, "delta"):
            return event.delta()

        return 0

    def setZoom(self, zoom: float) -> None:

        zoom = max(self.zoom_minimum, min(self.zoom_maximum, zoom))
        if abs(zoom - self._zoom) < 0.001:
            return

        synoptic_tab = self._getZoomTarget()
        if synoptic_tab is None:
            return

        self._ensureZoomCache(synoptic_tab)
        self._zoom = zoom
        self._applyZoom(synoptic_tab, zoom)

    def _getZoomTarget(self) -> QtWidgets.QWidget:

        if self._zoom_target is not None:
            return self._zoom_target

        synoptic_tab, _ = self.searchMainSynopticTab()
        return synoptic_tab

    def _ensureZoomCache(self, synoptic_tab: QtWidgets.QWidget) -> None:

        if self._zoom_target_size is not None:
            return

        target_size = synoptic_tab.size()
        minimum_size = synoptic_tab.minimumSize()
        self._zoom_target_size = QtCore.QSize(
            max(target_size.width(), minimum_size.width()),
            max(target_size.height(), minimum_size.height()))

        self._cacheZoomWidget(synoptic_tab)

    def _cacheZoomWidget(self, widget: QtWidgets.QWidget) -> None:

        for child in self._iterChildWidgets(widget):
            self._zoom_geometries[child] = QtCore.QRect(child.geometry())
            self._zoom_minimum_sizes[child] = QtCore.QSize(child.minimumSize())
            self._zoom_maximum_sizes[child] = QtCore.QSize(child.maximumSize())
            self._zoom_fonts[child] = QtGui.QFont(child.font())

            if hasattr(child, "iconSize"):
                self._zoom_icon_sizes[child] = QtCore.QSize(child.iconSize())

            pixmap = child.pixmap() if isinstance(child, QtWidgets.QLabel) else None
            if pixmap is not None and not pixmap.isNull():
                child.setScaledContents(True)

            layout = child.layout()
            if layout:
                self._cacheZoomLayout(layout)

            self._cacheZoomWidget(child)

    def _cacheZoomLayout(self, layout: QtWidgets.QLayout) -> None:

        margins = layout.contentsMargins()
        self._zoom_layout_margins[layout] = QtCore.QMargins(
            margins.left(),
            margins.top(),
            margins.right(),
            margins.bottom())
        self._zoom_layout_spacings[layout] = layout.spacing()

        for index in range(layout.count()):
            item = layout.itemAt(index)
            child_layout = item.layout()
            if child_layout:
                self._cacheZoomLayout(child_layout)

    def _applyZoom(self, synoptic_tab: QtWidgets.QWidget, zoom: float) -> None:

        synoptic_tab.setFixedSize(self._scaleSize(self._zoom_target_size, zoom))

        for widget, geometry in self._zoom_geometries.items():
            parent = widget.parentWidget()
            if parent is not None and parent.layout() is None:
                widget.setGeometry(self._scaleRect(geometry, zoom))

            self._applyWidgetZoom(widget, zoom)

        for layout, margins in self._zoom_layout_margins.items():
            layout.setContentsMargins(
                self._scaleValue(margins.left(), zoom),
                self._scaleValue(margins.top(), zoom),
                self._scaleValue(margins.right(), zoom),
                self._scaleValue(margins.bottom(), zoom))

        for layout, spacing in self._zoom_layout_spacings.items():
            if spacing >= 0:
                layout.setSpacing(self._scaleValue(spacing, zoom))

        if hasattr(synoptic_tab, "_buttonGeometry"):
            synoptic_tab._buttonGeometry.clear()

        synoptic_tab.updateGeometry()
        self.updateGeometry()

    def _applyWidgetZoom(self, widget: QtWidgets.QWidget, zoom: float) -> None:

        minimum_size = self._zoom_minimum_sizes.get(widget)
        if minimum_size and (minimum_size.width() > 0 or minimum_size.height() > 0):
            widget.setMinimumSize(self._scaleSize(minimum_size, zoom))

        maximum_size = self._zoom_maximum_sizes.get(widget)
        if maximum_size and not self._isDefaultMaximumSize(maximum_size):
            widget.setMaximumSize(self._scaleSize(maximum_size, zoom))

        font = self._zoom_fonts.get(widget)
        if font is not None:
            widget.setFont(self._scaleFont(font, zoom))

        icon_size = self._zoom_icon_sizes.get(widget)
        if icon_size:
            widget.setIconSize(self._scaleSize(icon_size, zoom))

    def _scaleFont(self, font: QtGui.QFont, zoom: float) -> QtGui.QFont:

        scaled_font = QtGui.QFont(font)
        point_size = font.pointSizeF()
        if point_size > 0:
            scaled_font.setPointSizeF(max(1.0, point_size * zoom))
            return scaled_font

        pixel_size = font.pixelSize()
        if pixel_size > 0:
            scaled_font.setPixelSize(max(1, self._scaleValue(pixel_size, zoom)))

        return scaled_font

    def _isDefaultMaximumSize(self, size: QtCore.QSize) -> bool:

        return size.width() >= 16777215 and size.height() >= 16777215

    def _scaleRect(self, rect: QtCore.QRect, zoom: float) -> QtCore.QRect:

        return QtCore.QRect(
            self._scaleValue(rect.x(), zoom),
            self._scaleValue(rect.y(), zoom),
            self._scaleValue(rect.width(), zoom),
            self._scaleValue(rect.height(), zoom))

    def _scaleSize(self, size: QtCore.QSize, zoom: float) -> QtCore.QSize:

        return QtCore.QSize(
            max(1, self._scaleValue(size.width(), zoom)),
            max(1, self._scaleValue(size.height(), zoom)))

    def _scaleValue(self, value: int, zoom: float) -> int:

        return round(value * zoom)

    def _iterChildWidgets(self, widget: QtWidgets.QWidget) -> list[QtWidgets.QWidget]:

        return [child for child in widget.children()
                if isinstance(child, QtWidgets.QWidget)]

    def _installZoomEventFilter(self, widget: QtWidgets.QWidget) -> None:

        if widget in self._zoom_event_filter_widgets:
            return

        widget.installEventFilter(self)
        self._zoom_event_filter_widgets.append(widget)

        for child in self._iterChildWidgets(widget):
            self._installZoomEventFilter(child)

    # ------------------------------------------------------------------------
    # utility for mouse event
    # ------------------------------------------------------------------------
    def searchMainSynopticTab(self) -> "tuple[Optional[QtWidgets.QWidget], bool]":

        # avoiding cyclic import, declaration here not top of code
        from ymt_synoptics.synoptic.tabs import MainSynopticTab
        for kid in self.children():
            if isinstance(kid, MainSynopticTab):
                return kid, True

            if "SynopticTab" in str(type(kid)):
                return kid, False

        else:
            mes = "synoptic tab not found"
            mgear.log(mes, mgear.sev_warning)
            return None, False

    def calculateOffset(self) -> QtCore.QPoint:

        w = self.spacer.geometry().width()
        return QtCore.QPoint(w * -1, 0)

    def offsetEvent(self, event: QtGui.QMouseEvent) -> QtGui.QMouseEvent:

        offsetev = self._makeMouseEvent(
            event.type(),
            self._eventPos(event) + self.offset,
            self._eventGlobalPos(event),
            event.button(),
            event.buttons(),
            event.modifiers()
        )

        return offsetev

    # ------------------------------------------------------------------------
    # mouse events
    # ------------------------------------------------------------------------
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:

        self.syn_w, self.syn_wid_is_mainsyntab = self.searchMainSynopticTab()
        self.offset = self.calculateOffset()
        self.origin = self._eventPos(event)

        self.rubberband.setGeometry(QtCore.QRect(self.origin, QtCore.QSize()))
        self.rubberband.show()

        if self.syn_wid_is_mainsyntab:
            self.syn_w.mousePressEvent_(self.offsetEvent(event))
        else:
            self.syn_w.mousePressEvent(self.offsetEvent(event))

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        self.syn_w, self.syn_wid_is_mainsyntab = self.searchMainSynopticTab()

        if self.rubberband.isVisible():

            self.rubberband.setGeometry(
                QtCore.QRect(self.origin, self._eventPos(event)).normalized())

        if self.syn_wid_is_mainsyntab:
            self.syn_w.mouseMoveEvent_(self.offsetEvent(event))
        else:
            self.syn_w.mouseMoveEvent(self.offsetEvent(event))

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:

        if self.rubberband.isVisible():
            self.rubberband.hide()

            if self.syn_wid_is_mainsyntab:
                self.syn_w.mouseReleaseEvent_(self.offsetEvent(event))
            else:
                self.syn_w.mouseReleaseEvent(self.offsetEvent(event))
