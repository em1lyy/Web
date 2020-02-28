import os.path
import platform
import ctypes

from tkinter import Tk

from PyQt5 import QtWebEngineCore
from PyQt5 import QtCore, QtGui, QtWidgets, QtWebEngineWidgets, QtNetwork
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt

history = []

with open("history") as fobject:
    lines = fobject.read().splitlines()
    for line in lines:
        url = line.split()
        if len(url) > 0:
            url = url[-1]
            history.append(url)
    del lines
    print(history)

class HistoryLogger():
    """This is an history-logging thing."""
    
    private_mode = False
    
    def log_url(self, url):
        if not self.private_mode:
            with open("history", "a") as historyfile:
                historyfile.write(url + "\n")
                history.append(url)
    
    def set_private_mode_enabled(self, privmode):
        self.private_mode = privmode
    
    def is_private_mode_enabled(self):
        return self.private_mode
    
    def get_history(self):
        return self.history

class HistoryWindow(QtWidgets.QDialog):
    """This is a window to display the history."""
    
    def __init__(self):

        super(HistoryWindow, self).__init__()
        self._setup()
    
    def _setup(self):
        
        """On windows, set appid to set taskbar icon"""
        
        if platform.system() == 'Windows':
            print("Windows detected, Setting app id")
            myappid = u'jagudev.web.browser.1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
        self.history_list = QtWidgets.QListWidget()
        self.history_list.itemDoubleClicked.connect(self.on_doubleclick)
        for entry in history:
            self.history_list.addItem(entry)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.history_list)
        self.show()
        # self.history_list.show()
    
    def on_doubleclick(self, item):
        print("Dubleclick on an item!")
        r = Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(self.history_list.currentItem().text())
        r.update()
        r.destroy()
        QMessageBox.about(self, "Web HistoryManager", "History entry copied to clipboard.")
