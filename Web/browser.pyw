#!/usr/bin/python3

import sys
import urllib.parse
from threading import Thread
import ctypes
import ctypes.util
import platform
import os
import time

from PyQt5 import QtCore, QtGui, QtWidgets, QtWebEngineWidgets, QtNetwork
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox
from bs4 import BeautifulSoup # This is more Pythonic than using JavaScript, and sometimes safer.
import validators

import adblocker
import historylogger

TEXT_MATCHES_NEXT = ["next page", "next", ">", ">>"]
TEXT_MATCHES_PREVIOUS = ["previous page", "prev", "<", "<<"]

ICON_CORRESPONDANTS = {
    "go-previous": ["go-previous", "back.png"],
    "go-next": ["go-next", "forward.png"],
    "process-stop": ["process-stop", "cancel_load.png"],
    "view-refresh": ["view-refresh", "reload.png"],
    "highlight-locbar": [None, None],
    "tab-new": ["tab-new", "new_tab.png"],
    "close-tab": [None, None],
    "view-history": ["view-history", "history.png"],
    "adblock": ["adblock_active.png", "adblock_active.png"],
    "private": ["private_no.png", "private_no.png"],
    "edit-download": ["edit-download", "download.png"],
    "dialog-ok-apply": ["dialog-ok-apply", "download-done.png"]
}

class MainWindow(QtWidgets.QMainWindow):
    """This class represents a main window for the browser."""

    fullscreen = False
    file_seperator = "/"

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.adblocker = adblocker.AdBlocker()
        self.hlogger = historylogger.HistoryLogger()
        self._setup()

    def _setup(self):

        """On windows, set appid to set taskbar icon"""

        if platform.system() == 'Windows':
            print("Windows detected, Setting app id")
            myappid = u'jagudev.web.browser.1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            file_seperator = "\\"

        """Initialize the browser layout."""
        self.resize(1000, 800)

        # Create toolbar.
        self.toolbar = QtWidgets.QToolBar("Main Toolbar", self)
        self.toolbar.setMovable(False)
        self.toolbar.setContextMenuPolicy(Qt.CustomContextMenu)
        self.addToolBar(self.toolbar)

        # We use the fact that True = 1 and False = 0 to our advantage to map the icons using this variable
        is_on_windows = (platform.system() == 'Windows')

        # Create navigation actions using:
        # _add_title_action(self, icon, icon_is_theme, shortcut, connect)
        self.back_action = self._add_title_action(ICON_CORRESPONDANTS["go-previous"][is_on_windows],
                                                  is_on_windows,
                                                  "Alt+Left",
                                                  self.back)
        self.toolbar.addAction(self.back_action)

        self.forward_action = self._add_title_action(ICON_CORRESPONDANTS["go-next"][is_on_windows],
                                                     is_on_windows,
                                                     "Alt+Right",
                                                     self.forward)
        self.toolbar.addAction(self.forward_action)

        self.stop_action = self._add_title_action(ICON_CORRESPONDANTS["process-stop"][is_on_windows],
                                                  is_on_windows,
                                                  "Esc",
                                                  self.stop)
        self.stop_action.triggered.connect(self._update_location_bar)
        self.toolbar.addAction(self.stop_action)

        self.reload_action = self._add_title_action(ICON_CORRESPONDANTS["view-refresh"][is_on_windows],
                                                    is_on_windows,
                                                    ["Ctrl+R", "F5"],
                                                    self.reload)
        self.toolbar.addAction(self.reload_action)

        # Create location bar.
        self.location_bar = QtWidgets.QLineEdit(self)
        self.location_bar.returnPressed.connect(self.load_url)
        self.toolbar.addWidget(self.location_bar)

        # Create action that highlights location bar.
        self.open_action = self._add_title_action(ICON_CORRESPONDANTS["highlight-locbar"][is_on_windows],
                                                  is_on_windows,
                                                  ["Ctrl+L", "Alt+D", "F6"],
                                                  self.location_bar.setFocus)
        self.open_action.triggered.connect(self.location_bar.selectAll)
        self.addAction(self.open_action)

        # Create tab actions.
        self.new_tab_action = self._add_title_action(ICON_CORRESPONDANTS["tab-new"][is_on_windows],
                                                    is_on_windows,
                                                    "Ctrl+T",
                                                    self.new_tab)
        self.toolbar.addAction(self.new_tab_action)

        self.close_tab_action = self._add_title_action(ICON_CORRESPONDANTS["close-tab"][is_on_windows],
                                                       is_on_windows,
                                                       "Ctrl+W",
                                                       self.close_tab)
        self.addAction(self.close_tab_action)

        # Create history button
        self.history_action = self._add_title_action(ICON_CORRESPONDANTS["view-history"][is_on_windows],
                                                     is_on_windows,
                                                     ["Ctrl+H", "Ctrl+Shift+H"],
                                                     self.show_history)
        self.toolbar.addAction(self.history_action)

        # Create AdBlock-Toggle
        self.adblock_action = self._add_title_action(ICON_CORRESPONDANTS["adblock"][is_on_windows],
                                                     is_on_windows,
                                                     "Ctrl+Shift+A",
                                                     self.toggle_adblock)
        self.toolbar.addAction(self.adblock_action)

        # Create Private Mode-Toggle
        self.private_action = self._add_title_action(ICON_CORRESPONDANTS["private"][is_on_windows],
                                                     is_on_windows,
                                                     ["Ctrl+Shift+P", "Ctrl+Shift+N"],
                                                     self.toggle_private)
        self.toolbar.addAction(self.private_action)

        # Create Download Thing, but don't add it
        self.download_action = self._add_title_action(ICON_CORRESPONDANTS["edit-download"][is_on_windows],
                                                     is_on_windows,
                                                     ["Ctrl+Shift+P", "Ctrl+Shift+N"],
                                                     self.toggle_private)
        self.download_action.setIcon(QtGui.QIcon.fromTheme("edit-download"))

        # Create tab widget.
        self.tab_widget = QtWidgets.QTabWidget(self)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self._update_tab_titles)
        self.tab_widget.currentChanged.connect(self._update_location_bar)
        self.setCentralWidget(self.tab_widget)

        # Start off by making a new tab.
        self.new_tab()

    # Internal stuff. Don't call these, please.

    def _update_location_bar(self):
        """Update the text in the location bar and log url to the history."""

        webview = self.tab_widget.currentWidget()
        if isinstance(webview, QtWebEngineWidgets.QWebEngineView):
            url = webview.url().toString()
            self.location_bar.setText(url)
            self.hlogger.log_url(url)

    def _update_tab_titles(self):
        """Update all the tab titles."""

        # Iterate through all tabs.
        for index in range(0, self.tab_widget.count()):
            webview = self.tab_widget.widget(index)

            if self.tab_widget.count() > 1:
                self.tab_widget.setTabsClosable(True)
            else:
                self.tab_widget.setTabsClosable(False)

            if not isinstance(webview, QtWebEngineWidgets.QWebEngineView):
                continue

            # Truncate to 32 characters. If the title is an empty string then it's Untitled.
            title = webview.title()[:32] if len(webview.title()) > 0 else "(Untitled)"
            self.tab_widget.setTabText(index, title)

            # Get the website icon
            url = webview.url()
            surl = url.toString()
            self.get_icon_from_url(url, index)

            # Are we on the current tab? Then set the window title.
            if webview == self.tab_widget.currentWidget():
                if webview.title() == "":
                    self.setWindowTitle("(Untitled) - Web")
                else:
                    self.setWindowTitle(webview.title() + " - Web")

    def _add_title_action(self, icon, icon_is_file, shortcut, connect):
        """Create an action for the title bar and returns it."""

        ret_action = QtWidgets.QAction(self)
        if icon is not None:
            if icon_is_file:
                ret_action.setIcon(QtGui.QIcon(icon))
            else:
                ret_action.setIcon(QtGui.QIcon.fromTheme(icon))
        if type(shortcut) is list:
            ret_action.setShortcuts(shortcut)
        elif shortcut is None:
            print("No shortcuts added.")
        else:
            ret_action.setShortcut(shortcut)
        ret_action.triggered.connect(connect)
        return ret_action

    def _icon_from_string(self, icon_name):
        iswin = platform.system() == 'Windows'
        name_str = ICON_CORRESPONDANTS[icon_name][iswin]
        if iswin:
            return QtGui.QIcon(name_str)
        else:
            return QtGui.QIcon.fromTheme(name_str)

    # Icon stuff

    def get_icon_from_url(self, url, index):
        """Method to get the icon from an url"""

        iurl = QtCore.QUrl.fromUserInput(url.scheme() + "://" + url.host() + "/favicon.ico")
        print("Trying to fetch icon from " + url.scheme() + "://" + url.host() + "/favicon.ico")

        manager = QtNetwork.QNetworkAccessManager(self)
        manager.finished.connect(lambda reply: self.set_icon_from_reply(reply, index))
        manager.get(QtNetwork.QNetworkRequest(iurl))

    def set_icon_from_reply(self, reply, index):
        """Method to set the icon for a tab to the icon we've fetched"""

        p = QtGui.QPixmap()
        p.loadFromData(reply.readAll(), format="ico")
        self.tab_widget.setTabIcon(index, QtGui.QIcon(p))

    # Fullscreen request handler

    def on_fullscreen_request(self, request):
        request.accept()
        if (not self.fullscreen):
            self.showFullScreen()
        else:
            self.showNormal()
        self.fullscreen = not self.fullscreen

    # Download stuff

    def download_item(self, item):
        sizeVal = str(int(item.totalBytes() / 1024 / 1024)) + " MB" if item.totalBytes() != -1 else "Unknown"
        download_allowed = QMessageBox.question(self,
                                                'Download - Web',
                                                "Do you want to download this file:\n" + item.path().split(self.file_seperator).pop() + "\nSize: " + sizeVal + "?",
                                                QMessageBox.Save | QMessageBox.Cancel, QMessageBox.Save)
        if download_allowed == QMessageBox.Save:
            self.download_action.setIcon(self._icon_from_string("edit-download"))
            self.toolbar.addAction(self.download_action)
            item.finished.connect(self.notify_download_finish)
            item.accept()
            print('Downloading to ', item.path())
        else:
            item.cancel()
            print('Download cancelled.')

    def notify_download_finish(self):
        self.download_action.setIcon(self._icon_from_string("dialog-ok-apply"))
        self.toolbar.repaint()
        Thread(target=self.return_from_download_finish_notify_state).start()

    def return_from_download_finish_notify_state(self):
        time.sleep(3)
        self.toolbar.removeAction(self.download_action)

    # Browser features

    def show_history(self):
        """Show a history window"""
        self.historywindow = historylogger.HistoryWindow()

    def toggle_adblock(self):
        if self.adblocker.active:
            self.adblocker.set_active(False)
            self.adblock_action.setIcon(QtGui.QIcon("adblock_inactive.png"))
        else:
            self.adblocker.set_active(True)
            self.adblock_action.setIcon(QtGui.QIcon("adblock_active.png"))

    def toggle_private(self):
        self.hlogger.set_private_mode_enabled(not self.hlogger.is_private_mode_enabled())
        if self.hlogger.is_private_mode_enabled():
            self.private_action.setIcon(QtGui.QIcon("private.png"))
            QMessageBox.about(self, "Web HistoryLogger", "Private mode has been enabled.\nIn private mode, your browsing history isn't going to be logged to the history file.")
        else:
            self.private_action.setIcon(QtGui.QIcon("private_no.png"))
            QMessageBox.about(self, "Web HistoryLogger", "Private mode has been disabled.")

    # Navigation actions.

    def load_url(self):
        """Load the URL listed in the location bar."""

        webview = self.tab_widget.currentWidget()
        if isinstance(webview, QtWebEngineWidgets.QWebEngineView):
            if not QtCore.QUrl.fromUserInput(self.location_bar.text()).scheme() == "file":
                if not QtCore.QUrl.fromUserInput(self.location_bar.text()).scheme() == "web":
                    if not len(self.location_bar.text().split(" ")) > 1:
                        if "." in self.location_bar.text():
                            url = QtCore.QUrl.fromUserInput(self.location_bar.text())
                            self.hlogger.log_url(url.toString())
                            webview.load(url)
                        else:
                            self.load_searx_results(self.location_bar.text())
                    else:
                        self.load_searx_results(self.location_bar.text())
                else:
                    self.handle_internal_query(QtCore.QUrl.fromUserInput(self.location_bar.text()).host())
            else:
                url = QtCore.QUrl.fromUserInput(self.location_bar.text())
                self.hlogger.log_url(url.toString())
                webview.load(url)

    def load_searx_results(self, query):
        """Search on Searx for query"""

        webview = self.tab_widget.currentWidget()
        if isinstance(webview, QtWebEngineWidgets.QWebEngineView):
            url = QtCore.QUrl("https://searx.win/?q=" + query)
            self.hlogger.log_url(url.toString())
            webview.load(url)

    def handle_internal_query(self, query):
        """Handle a query which start with 'web://'."""

        # If the query was 'web://history' open a history dialog.
        if query == "history":
            self.historywindow = historylogger.HistoryWindow()

    def load_homepage(self):
        """Load the SearX search engine homepage"""

        webview = self.tab_widget.currentWidget()
        if isinstance(webview, QtWebEngineWidgets.QWebEngineView):
            url = QtCore.QUrl.fromUserInput("searx.win")
            self.hlogger.log_url(url.toString())
            webview.load(url)

    def back(self):
        """Go back in history by one."""

        webview = self.tab_widget.currentWidget()
        if isinstance(webview, QtWebEngineWidgets.QWebEngineView):
            webview.back()

    def forward(self):
        """Go forward in history by one."""

        webview = self.tab_widget.currentWidget()
        if isinstance(webview, QtWebEngineWidgets.QWebEngineView):
            webview.forward()

    def previous(self):
        """Attempt to go to the previous page."""

        webview = self.tab_widget.currentWidget()
        if isinstance(webview, QtWebEngineWidgets.QWebEngineView):
            webview.page().toHtml(lambda html: self.go_by(html, "prev", TEXT_MATCHES_PREVIOUS))

    def next(self):
        """Attempt to go to the next page."""

        webview = self.tab_widget.currentWidget()

        if isinstance(webview, QtWebEngineWidgets.QWebEngineView):
            webview.page().toHtml(lambda html: self.go_by(html, "next", TEXT_MATCHES_NEXT))

    def go_by(self, html:str, relationship:str, text_matches:list=[]):
        """
        From an HTML string, parse out a link based on class, rel, or id.

        * html - A string that contains HTML data to be parsed.
        * relationship - The relationship that the link has relative to the current page.
        * text_matches (optional) - A list of substrings to be checked against in link innerHTML.
        """

        webview = self.tab_widget.currentWidget()
        if not isinstance(webview, QtWebEngineWidgets.QWebEngineView):
            return

        # Create a BeautifulSoup object.
        soup = BeautifulSoup(html)
        anchors = soup.find_all("a", href=True)

        # The to-be-determined URL.
        url = None

        # Check attributes for the desired relationship.
        for anchor in anchors:
            for attribute in ("class", "rel", "id"):
                if anchor.has_attr(attribute) and relationship in anchor[attribute]:
                    url = anchor["href"]
                    break
            if url:
                break

        # As a fallback, check text strings within the link itself.
        if not url:
            for anchor in anchors:
                for substring in text_matches:
                    if substring in anchor.text.lower():
                        url = anchor["href"]
                        break

        # Everything has failed, exit function.
        if not url:
            return

        # If the URL doesn't seem to be valid, it's probably a relative URL, so use urllib.parse.
        if not validators.url(url):
            url = urllib.parse.urljoin(webview.url().toString(), url)

        print("go-by: " + url)
        self.hlogger.log_url(url)

        # Load the URL.
        webview.load(QtCore.QUrl(url))

    def stop(self):
        """Stop the current page load."""

        webview = self.tab_widget.currentWidget()
        if isinstance(webview, QtWebEngineWidgets.QWebEngineView):
            webview.stop()

    def reload(self):
        """Reload the current page."""

        webview = self.tab_widget.currentWidget()
        if isinstance(webview, QtWebEngineWidgets.QWebEngineView):
            webview.reload()

    # Tab actions.

    def new_tab(self):
        """Create a browser tab."""

        webview = QtWebEngineWidgets.QWebEngineView(self)

        webview.titleChanged.connect(self._update_tab_titles)
        webview.urlChanged.connect(self._update_location_bar)

        # Assign ad blocker and history logger.
        webview.page().profile().setRequestInterceptor(self.adblocker)

        # Add fullscreen support
        webview.settings().setAttribute(QtWebEngineWidgets.QWebEngineSettings.FullScreenSupportEnabled, True)
        webview.page().fullScreenRequested.connect(lambda request: self.on_fullscreen_request(request))

        # Add file Download Support
        webview.page().profile().downloadRequested.connect(lambda item: self.download_item(item))

        self.tab_widget.addTab(webview, "New Tab")
        self.setWindowTitle("New Tab - Web")
        self.tab_widget.setCurrentIndex(self.tab_widget.count()-1)
        self.load_homepage()

    def close_tab(self, index=None):
        """Close a browser tab."""

        if type(index) is not int:
            index = self.tab_widget.currentIndex()

        webview = self.tab_widget.widget(index)

        if webview:
            self.tab_widget.removeTab(index)
            webview.deleteLater()



def main(argv):
    if platform.system() != 'Windows':
        ctypes.CDLL(ctypes.util.find_library("GL"), mode=ctypes.RTLD_GLOBAL)

    app = QtWidgets.QApplication(argv)

    app.setApplicationName("Web")
    app.setWindowIcon(QtGui.QIcon('web.png'))

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main(sys.argv)
