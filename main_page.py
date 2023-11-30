# coding:utf-8
import sys

from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QFrame
from qframelesswindow import TitleBar

from qfluentwidgets import FluentIcon as FIF, SplashScreen, NavigationAvatarWidget
from qfluentwidgets import NavigationItemPosition, FluentTranslator, setThemeColor, \
    FluentWindow, SubtitleLabel, setFont
from view.AuthTest_interface import AuthTestInterface
from view.settingConf_interface import SettingInterface
from view.ChartRecord_interface import ChartRecordInterface


# from baseLogger import log

class Widget(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.label = SubtitleLabel(text, self)
        self.hBoxLayout = QHBoxLayout(self)

        setFont(self.label, 24)
        self.label.setAlignment(Qt.AlignCenter)
        self.hBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)

        # 必须给子界面设置全局唯一的对象名
        self.setObjectName(text.replace(' ', '-'))


class CostumerTitleBar(TitleBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.minBtn.setVisible(False)
        self.maxBtn.setVisible(False)
        self.closeBtn.setVisible(False)


class Window(FluentWindow):
    """ 主界面 """

    def __init__(self):
        super().__init__()

        self.initWindow()

        setThemeColor("#28afe9")  # 创建子界面
        self.homeInterface = AuthTestInterface(self)
        self.settingInterface = SettingInterface(self)
        self.recordInterface = ChartRecordInterface(self)
        self.albumInterface = Widget('Album Interface', self)
        self.albumInterface1 = Widget('Album Interface 1', self)

        self.initNavigation()

    def initNavigation(self):
        self.addSubInterface(self.homeInterface, FIF.HOME, 'Home')

        self.navigationInterface.addSeparator()

        self.addSubInterface(self.recordInterface, FIF.SEARCH, 'Record')
        self.addSubInterface(self.albumInterface, FIF.ALBUM, 'Albums', NavigationItemPosition.SCROLL)
        self.addSubInterface(self.albumInterface1, FIF.ALBUM, 'Album 1', parent=self.albumInterface)

        self.navigationInterface.addWidget(
            routeKey='avatar',
            widget=NavigationAvatarWidget('wendy', 'resource/logo.png'),
            onClick=None,
            position=NavigationItemPosition.BOTTOM
        )
        self.addSubInterface(self.settingInterface, FIF.SETTING, 'Settings', NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(980, 900)
        self.setWindowIcon(QIcon("resource/logo.png"))
        self.version = "v23111.0.0"
        self.setWindowTitle('云迹物联授权及产测工具_' + self.version)
        # self.setFont(QFont('Microsoft YaHei', pointSize=16))

        # create splash screen
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setTitleBar(CostumerTitleBar(self))
        self.splashScreen.setIconSize(QSize(106, 106))
        self.splashScreen.raise_()

        QApplication.processEvents()

        self.timer = QTimer(self)
        self.timer.start(1500)
        self.timer.timeout.connect(self.stop_waiting)

    def stop_waiting(self):
        self.splashScreen.finish()
        self.timer.stop()


if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)

    # internationalization
    translate = FluentTranslator()
    app.installTranslator(translate)
    w = Window()
    w.show()
    # setTheme(Theme.DARK)
    app.exec()
