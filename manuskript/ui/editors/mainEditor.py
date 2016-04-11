#!/usr/bin/env python
# --!-- coding: utf8 --!--
import locale

from PyQt5.QtCore import QModelIndex, QRect, QPoint
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QIcon
from PyQt5.QtWidgets import QWidget, qApp

from manuskript import settings
from manuskript.enums import Outline
from manuskript.functions import AUC, mainWindow, drawProgress
from manuskript.ui import style
from manuskript.ui.editors.editorWidget import editorWidget
from manuskript.ui.editors.fullScreenEditor import fullScreenEditor
from manuskript.ui.editors.mainEditor_ui import Ui_mainEditor

locale.setlocale(locale.LC_ALL, '')


class mainEditor(QWidget, Ui_mainEditor):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setupUi(self)
        self._updating = False

        self.mw = mainWindow()

        # Connections --------------------------------------------------------

        self.sldCorkSizeFactor.valueChanged.connect(
                self.setCorkSizeFactor, AUC)
        self.btnRedacFolderCork.toggled.connect(
                self.sldCorkSizeFactor.setVisible, AUC
        )
        self.btnRedacFolderText.clicked.connect(
                lambda v: self.setFolderView("text"), AUC)
        self.btnRedacFolderCork.clicked.connect(
                lambda v: self.setFolderView("cork"), AUC)
        self.btnRedacFolderOutline.clicked.connect(
                lambda v: self.setFolderView("outline"), AUC)

        self.btnRedacFullscreen.clicked.connect(
                self.showFullScreen, AUC)

        # self.tab.setDocumentMode(False)

        # Bug in Qt < 5.5: doesn't always load icons from custom theme.
        # Cf. https://github.com/qtproject/qtbase/commit/a8621a3f85e64f1252a80ae81a6e22554f7b3f44
        # Since those are important, we provide fallback.
        self.btnRedacFolderCork.setIcon(QIcon.fromTheme("view-cards",
                                                        QIcon("../icons/NumixMsk/256x256/actions/view-cards.svg")))
        self.btnRedacFolderOutline.setIcon(QIcon.fromTheme("view-outline",
                                                           QIcon("../icons/NumixMsk/256x256/actions/view-outline.svg")))
        self.btnRedacFolderText.setIcon(QIcon.fromTheme("view-text",
                                                        QIcon("../icons/NumixMsk/256x256/actions/view-text.svg")))

        for btn in [self.btnRedacFolderCork, self.btnRedacFolderText, self.btnRedacFolderOutline]:
            btn.setToolTip(btn.text())
            btn.setText("")

    ###############################################################################
    # TABS
    ###############################################################################

    def currentTabWidget(self):
        """Returns the tabSplitter that has focus."""
        ts = self.tabSplitter
        while ts:
            if ts.focusTab == 1:
                return ts.tab
            else:
                ts = ts.secondTab

    def currentEditor(self, tabWidget=None):
        if tabWidget is None:
            tabWidget = self.currentTabWidget()
        return tabWidget.currentWidget()
        # return self.tab.currentWidget()

    def tabChanged(self, index=QModelIndex()):
        if self.currentEditor():
            index = self.currentEditor().currentIndex
            view = self.currentEditor().folderView
            self.updateFolderViewButtons(view)
        else:
            index = QModelIndex()

        self.updateMainTreeView(index)

        self.updateStats()
        self.updateThingsVisible(index)

    def updateMainTreeView(self, index):
        self._updating = True
        self.mw.treeRedacOutline.setCurrentIndex(index)
        self._updating = False

    def closeAllTabs(self):
        for ts in self.allTabSplitters():
            while(ts.tab.count()):
                ts.closeTab(0)

        for ts in reversed(self.allTabSplitters()):
            ts.closeSplit()

    def allTabs(self, tabWidget=None):
        """Returns all the tabs from the given tabWidget. If tabWidget is None, from the current tabWidget."""
        if tabWidget is None:
            tabWidget = self.currentTabWidget()
        return [tabWidget.widget(i) for i in range(tabWidget.count())]

    def allAllTabs(self):
        """Returns a list of all tabs, from all tabWidgets."""
        r = []
        for ts in self.allTabSplitters():
            r.extend(self.allTabs(ts.tab))
        return r

    def allTabSplitters(self):
        r = []
        ts = self.tabSplitter
        while ts:
            r.append(ts)
            ts = ts.secondTab
        return r


    ###############################################################################
    # SELECTION AND UPDATES
    ###############################################################################

    def selectionChanged(self):
        if self._updating:
            return

        if len(self.mw.treeRedacOutline.selectionModel().
               selection().indexes()) == 0:
            idx = QModelIndex()
        else:
            idx = self.mw.treeRedacOutline.currentIndex()

        self.setCurrentModelIndex(idx)
        self.updateThingsVisible(idx)

    def openIndexes(self, indexes, newTab=False):
        for i in indexes:
            self.setCurrentModelIndex(i, newTab)

    def setCurrentModelIndex(self, index, newTab=False, tabWidget=None):

        title = self.getIndexTitle(index)

        if tabWidget is None:
            tabWidget = self.currentTabWidget()

        # Checking if tab is already openned
        for w in self.allTabs(tabWidget):
            if w.currentIndex == index:
                tabWidget.setCurrentWidget(w)
                return

        if qApp.keyboardModifiers() & Qt.ControlModifier:
            newTab = True

        if newTab or not self.currentTabWidget().count():
            editor = editorWidget(self)
            editor.setCurrentModelIndex(index)
            tabWidget.addTab(editor, title)
            tabWidget.setCurrentIndex(self.currentTabWidget().count() - 1)
        else:
            self.currentEditor(tabWidget).setCurrentModelIndex(index)
            tabWidget.setTabText(tabWidget.currentIndex(), title)

    def updateTargets(self):
        """Updates all tabSplitter that are targets. This is called from editorWidget."""
        index = self.sender().currentIndex()

        for ts in self.allTabSplitters():
            if ts.isTarget:
                self.updateMainTreeView(index)
                self.setCurrentModelIndex(index, tabWidget=ts.tab)
                self.updateThingsVisible(index)

    def getIndexTitle(self, index):
        if not index.isValid():
            title = self.tr("Root")
        else:
            title = index.internalPointer().title()

        return title

    ###############################################################################
    # UI
    ###############################################################################

    def updateThingsVisible(self, index):
        if index.isValid():
            visible = index.internalPointer().isFolder()
        else:
            visible = True

        # Hides / show textFormat
        self.textFormat.updateFromIndex(index)

        self.btnRedacFolderText.setVisible(visible)
        self.btnRedacFolderCork.setVisible(visible)
        self.btnRedacFolderOutline.setVisible(visible)
        self.sldCorkSizeFactor.setVisible(visible and self.btnRedacFolderCork.isChecked())
        self.btnRedacFullscreen.setVisible(not visible)

    def updateFolderViewButtons(self, view):
        if view == "text":
            self.btnRedacFolderText.setChecked(True)
        elif view == "cork":
            self.btnRedacFolderCork.setChecked(True)
        elif view == "outline":
            self.btnRedacFolderOutline.setChecked(True)

    def updateStats(self):

        if not self.currentEditor():
            return

        index = self.currentEditor().currentIndex
        if index.isValid():
            item = index.internalPointer()
        else:
            item = self.mw.mdlOutline.rootItem

        if not item:
            item = self.mw.mdlOutline.rootItem

        wc = item.data(Outline.wordCount.value)
        goal = item.data(Outline.goal.value)
        progress = item.data(Outline.goalPercentage.value)
        # mw = qApp.activeWindow()

        if not wc:
            wc = 0
        if goal:
            self.lblRedacProgress.show()
            rect = self.lblRedacProgress.geometry()
            rect = QRect(QPoint(0, 0), rect.size())
            self.px = QPixmap(rect.size())
            self.px.fill(Qt.transparent)
            p = QPainter(self.px)
            drawProgress(p, rect, progress, 2)
            del p
            self.lblRedacProgress.setPixmap(self.px)
            self.lblRedacWC.setText(self.tr("{} words / {}").format(
                    locale.format("%d", wc, grouping=True),
                    locale.format("%d", goal, grouping=True)))
        else:
            self.lblRedacProgress.hide()
            self.lblRedacWC.setText(self.tr("{} words").format(
                    locale.format("%d", wc, grouping=True)))

    ###############################################################################
    # VIEWS
    ###############################################################################

    def setFolderView(self, view):
        if self.currentEditor():
            self.currentEditor().setFolderView(view)

    def setCorkSizeFactor(self, val):
        for w in self.allAllTabs():
            w.setCorkSizeFactor(val)
        settings.corkSizeFactor = val

    def updateCorkView(self):
        for w in self.allAllTabs():
            w.corkView.viewport().update()

    def updateCorkBackground(self):
        for w in self.allAllTabs():
            w.corkView.updateBackground()

    def updateTreeView(self):
        for w in self.allAllTabs():
            w.outlineView.viewport().update()

    def showFullScreen(self):
        if self.currentEditor():
            self._fullScreen = fullScreenEditor(self.currentEditor().currentIndex)

    ###############################################################################
    # DICT AND STUFF LIKE THAT
    ###############################################################################

    def setDict(self, dict):
        print(dict)
        for w in self.allAllTabs():
            w.setDict(dict)

    def toggleSpellcheck(self, val):
        for w in self.allAllTabs():
            w.toggleSpellcheck(val)
