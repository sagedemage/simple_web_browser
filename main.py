from cefpython3 import cefpython as cef
import ctypes
import os
import platform
import sys
from pathlib import Path
import PySide6
from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

WindowUtils = cef.WindowUtils()

os_name = platform.system()
WINDOWS = (os_name == "Windows")

WIDTH = 800
HEIGHT = 600

def main():
    check_versions()
    sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
    settings = {}

    cef.Initialize(settings)
    app = CefApplication(sys.argv)
    window_title = "Simple Web Broswer"
    main_window = MainWindow(title=window_title)
    main_window.show()
    main_window.activateWindow()
    main_window.raise_()
    app.exec()
    if not cef.GetAppSetting("external_message_pump"):
        app.stopTimer()
    del main_window
    del app
    cef.Shutdown()


def check_versions():
    print("[qt.py] CEF Python {ver}".format(ver=cef.__version__))
    print("[qt.py] Python {ver} {arch}".format(
            ver=platform.python_version(), arch=platform.architecture()[0]))
    print("[qt.py] PySide2 {v1} (qt {v2})".format(
              v1=PySide6.__version__, v2=QtCore.__version__))

class MainWindow(QtWidgets.QMainWindow):
        def __init__(self, title: str):
            super(MainWindow, self).__init__(None)
            self.cef_widget = None
            self.navigation_bar = None
            self.setWindowTitle(title)
            self.setFocusPolicy(QtCore.Qt.StrongFocus)
            self.setupLayout()
        
        def setupLayout(self):
            self.resize(WIDTH, HEIGHT)
            self.cef_widget = CefWidget(self)
            self.navigation_bar = NavigationBar(self.cef_widget)

            layout = QtWidgets.QGridLayout()
            layout.addWidget(self.navigation_bar, 0, 0)
            layout.addWidget(self.cef_widget, 1, 0)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.setRowStretch(0, 0)
            layout.setRowStretch(1, 1)

            frame = QtWidgets.QFrame()
            frame.setLayout(layout)
            self.setCentralWidget(frame)

            if WINDOWS:
                self.show()
            else:
                raise RuntimeError(f"Error: {os_name} not supported.")

            self.cef_widget.embedBroswer()

        def closeEvent(self, event):
             if self.cef_widget.browser:
                self.cef_widget.browser.CloseBrowser(True)
                self.clear_browser_references()
        
        def clear_browser_references(self):
             self.cef_widget.browser = None

class CefWidget(QtWidgets.QWidget):
    def __init__(self, parent: MainWindow):
        super(CefWidget, self).__init__(parent)
        self.parent: MainWindow = parent
        self.browser = None
        self.show()
    
    def focusInEvent(self, event):
        if cef.GetAppSetting("debug"):
            print("[qt.py] CefWidget.focusInEvent")
        if self.browser:
            if WINDOWS:
                WindowUtils.OnSetFocus(self.getHandle(), 0, 0, 0)
            else:
                raise RuntimeError(f"Error: {os_name} not supported.")
            self.browser.SetFocus(True)
    
    def focusOutEvent(self, event):
        if cef.GetAppSetting("debug"):
            print("[qt.py] CefWidget.focusOutEvent")
        if self.browser:
            self.browser.SetFocus(False)
    
    def embedBroswer(self):
        window_info = cef.WindowInfo()
        rect = [0, 0, self.width(), self.height()]
        window_info.SetAsChild(self.getHandle(), rect)
        self.browser = cef.CreateBrowserSync(window_info,
                                             url="https://www.google.com/")
        self.browser.SetClientHandler(LoadHandler(self.parent.navigation_bar))
        self.browser.SetClientHandler(FocusHandler(self))
    
    def getHandle(self):
        try:
            return int(self.winId())
        except:
            if sys.version_info[0] == 3:
                # Python 3
                ctypes.pythonapi.PyCapsule_GetPointer.restype = (
                    ctypes.c_void_p)
                ctypes.pythonapi.PyCapsule_GetPointer.argtypes = (
                    [ctypes.py_object])
                return ctypes.pythonapi.PyCapsule_GetPointer(
                    self.winId(), None)
            else:
                print(f"Python version {sys.version_info[0]} not supported!")
                return None
    
    def moveEvent(self, _):
        self.x = 0
        self.y = 0
        if self.browser:
            if WINDOWS:
                WindowUtils.OnSize(self.getHandle(), 0, 0, 0)
            else:
                raise RuntimeError(f"Error: {os_name} not supported.")
            self.browser.NotifyMoveOrResizeStarted()
    
    def resizeEvent(self, event):
        if self.browser:
            if WINDOWS:
                WindowUtils.OnSize(self.getHandle(), 0, 0, 0)
            else:
                raise RuntimeError(f"Error: {os_name} not supported.")
            self.browser.NotifyMoveOrResizeStarted()

class CefApplication(QtWidgets.QApplication):
    def __init__(self, args):
        super(CefApplication, self).__init__(args)
        if not cef.GetAppSetting("external_message_pump"):
            self.timer = self.createTimer()
        self.setupIcon("logo")
    
    def createTimer(self):
        timer = QtCore.QTimer()
        timer.timeout.connect(self.onTimer)
        timer.start(10)
        return timer
    
    def onTimer(self):
        cef.MessageLoopWork()
    
    def stopTimer(self):
        # Stop the timer after Qt's message loop has ended
        self.timer.stop()
    
    def setupIcon(self, name):
        icon_file = Path("resources/{0}.png".format(name))

        if icon_file.exists():
            icon_file_name = str(icon_file)
            icon = QtGui.QIcon(icon_file_name)
            self.setWindowIcon(icon)

class FocusHandler(object):
    def __init__(self, cef_widget: CefWidget):
        self.cef_widget = cef_widget
    
    def OnTakeFocus(self, **_):
        if cef.GetAppSetting("debug"):
            print("[qt.py] FocusHandler.OnTakeFocus")
    
    def OnSetFocus(self, **_):
        if cef.GetAppSetting("debug"):
            print("[qt.py] FocusHandler.OnSetFocus")
    
    def OnGotFocus(self, browser, **_):
        if cef.GetAppSetting("debug"):
            print("[qt.py] FocusHandler.OnGotFocus")
        self.cef_widget.setFocus()

class NavigationBar(QtWidgets.QFrame):
    def __init__(self, cef_widget: CefWidget):
        super(NavigationBar, self).__init__()
        self.cef_widget = cef_widget

        # Init layout
        layout = QtWidgets.QGridLayout()
        margins = QtCore.QMargins(left=0, top=0, right=0, bottom=0)
        layout.setContentsMargins(margins)
        layout.setHorizontalSpacing(0)
        layout.setVerticalSpacing(0)

        # Back button
        self.back = self.createButton("back")
        self.back.clicked.connect(self.onBack)
        layout.addWidget(self.back, 0, 0)

        # Forward button
        self.forward = self.createButton("forward")
        self.forward.clicked.connect(self.onForward)
        layout.addWidget(self.forward, 0, 1)

        # Reload button
        self.reload = self.createButton("reload")
        self.reload.clicked.connect(self.onReload)
        layout.addWidget(self.reload, 0, 2)

        # Url input
        self.url = QtWidgets.QLineEdit("")
        self.url.returnPressed.connect(self.onGoUrl)
        self.url.setMinimumHeight(28)
        self.url.setMaximumHeight(28)

        point_size = 12
        font_family = "Helvetica"
        font = self.url.font()
        font.setPointSize(point_size)
        font.setFamily(font_family)
        self.url.setFont(font)
        layout.addWidget(self.url, 0, 3)

        empty_widget = QtWidgets.QWidget()
        empty_widget.setMinimumWidth(20)
        empty_widget.setMaximumWidth(20)
        layout.addWidget(empty_widget, 0, 4)

        # Layout
        self.setLayout(layout)
        self.updateState()
    
    def onBack(self):
        if self.cef_widget.browser:
            self.cef_widget.browser.GoBack()
    
    def onForward(self):
        if self.cef_widget.browser:
            self.cef_widget.browser.GoForward()
    
    def onReload(self):
        if self.cef_widget.browser:
            self.cef_widget.browser.Reload()
    
    def onGoUrl(self):
        if self.cef_widget.browser:
            self.cef_widget.browser.LoadUrl(self.url.text())
    
    def updateState(self):
        browser = self.cef_widget.browser
        if not browser:
            self.back.setEnabled(False)
            self.forward.setEnabled(False)
            self.reload.setEnabled(False)
            self.url.setEnabled(False)
            return
        self.back.setEnabled(browser.CanGoBack())
        self.forward.setEnabled(browser.CanGoForward())
        self.reload.setEnabled(True)
        self.url.setEnabled(True)
        self.url.setText(browser.GetUrl())
    
    def createButton(self, name):
        resources = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                 "resources")
        pixmap = QtGui.QPixmap(os.path.join(resources, "{0}.png".format(name)))
        icon = QtGui.QIcon(pixmap)
        button = QtWidgets.QPushButton()
        button.setIcon(icon)
        button.setIconSize(pixmap.rect().size())
        return button

class LoadHandler(object):
    def __init__(self, navigation_bar: NavigationBar):
        self.initial_app_loading = True
        self.navigation_bar = navigation_bar
    
    def OnLoadingStateChange(self, **_):
        self.navigation_bar.updateState()
    
    def OnLoadStart(self, browser, **_):
        self.navigation_bar.url.setText(browser.GetUrl())
        if self.initial_app_loading:
            self.navigation_bar.cef_widget.setFocus()
            self.initial_app_loading = False

if __name__ == '__main__':
    main()