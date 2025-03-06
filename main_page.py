# coding:utf-8
import json
import sys
import os

from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication
from qframelesswindow import TitleBar, AcrylicWindow

from qfluentwidgets import FluentIcon as FIF, SplashScreen, NavigationAvatarWidget, SplitTitleBar, MessageBox
from qfluentwidgets import NavigationItemPosition, FluentTranslator, setThemeColor, \
    FluentWindow
from view.DeviceState_interface import DeviceStateInterface
from view.Login_page import Ui_Form

# 导入版本管理模块
try:
    # 确保当前目录在sys.path中
    current_dir = os.path.abspath('.')
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    from version_manager import get_version_string
    APP_VERSION = get_version_string()
except ImportError:
    APP_VERSION = "V24.1.0.20"  # 默认版本号与version.json保持一致

# from baseLogger import log

def save_credentials(username, password, enable_remember):
    # 加密密码
    # hashed_password = self.hash_password(password)

    # 构造存储的数据结构
    credentials = {
        'username': username,
        'password': password,
        'remember_ps': enable_remember
    }

    # 将数据写入文件（或者数据库中）
    try:
        with open('resources/user/credentials.json', 'w') as file:
            json.dump(credentials, file)
    except FileNotFoundError:
        with open('resources/user/credentials.json', 'x') as file:
            json.dump(credentials, file)


class LoginWindow(AcrylicWindow, Ui_Form):
    login_succeed_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # setTheme(Theme.DARK)
        setThemeColor("#28afe9")

        self.initWindow()

        self.setTitleBar(SplitTitleBar(self))
        self.titleBar.raise_()

        self.label.setScaledContents(False)
        # self.version = "v23111.0.0"
        # self.setWindowTitle('云迹物联授权及产测工具_' + self.version)
        # self.setWindowIcon(QIcon("resources/logo.png"))
        self.resize(1000, 650)

        self.windowEffect.setMicaEffect(self.winId(), isDarkMode=False)
        self.setStyleSheet("LoginWindow{background: rgba(242, 242, 242, 0.8)}")
        self.titleBar.titleLabel.setStyleSheet("""
            QLabel{
                background: transparent;
                font: 13px 'Segoe UI';
                padding: 0 4px;
                color: white
            }
        """)

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        # 若有保存的密码，则直接登录
        self.read_credentials()
        self.pushButton_Login.clicked.connect(self.login_process)

    # def hash_password(self, password):
    #     # 使用SHA-256进行密码加密
    #     sha256 = hashlib.sha256()
    #     sha256.update(password.encode('utf-8'))
    #     return sha256.hexdigest()
    #
    # def decode_hash_password(self, hashed_password):
    #     # 使用SHA-256进行密码加密
    #     sha256 = hashlib.sha256()
    #     sha256.update(hashed_password.encode('utf-8'))
    #     return sha256.hexdigest()

    def read_credentials(self):

        try:
            with open('resources/user/credentials.json', 'r') as file:
                stored_credentials = json.load(file)
        except FileNotFoundError:
            print("没有存储的用户信息")
            return False

        if stored_credentials.get('remember_ps'):
            self.checkBox_RememberPS.setChecked(True)
            # 获取存储的用户名和密码
            # password = stored_credentials.get('password')

            self.lineEdit_UserName.setText(stored_credentials.get('username'))
            self.LineEdit_Password.setText(stored_credentials.get('password'))
        else:
            print("user not remember password")

    def check_credentials(self, username, password):
        # 读取存储的数据
        with open('resources/user/credentials.json', 'r') as file:
            stored_credentials = json.load(file)

        # 获取存储的用户名和密码
        stored_username = stored_credentials.get('username')
        stored_password = stored_credentials.get('password')

        # 加密输入的密码进行比较
        hashed_password = self.hash_password(password)

        # 检查用户名和密码是否匹配
        if stored_username == username and stored_password == hashed_password:
            return True
        else:
            return False

    def login_process(self):
        print('login pressed')
        userName = self.lineEdit_UserName.text()
        passWord = self.LineEdit_Password.text()
        if userName == 'Auther' and passWord == '123456':
            self.login_succeed_signal.emit()
            if self.checkBox_RememberPS.isChecked():
                save_credentials(self.lineEdit_UserName.text(), self.LineEdit_Password.text(), True)
            else:
                save_credentials("", "", False)
            # 隐藏登录页
            self.close()
        else:
            MessageBox("提示","用户名或密码错误，请重试",self).show()


    def show_win_slot(self):
        self.raise_()
        self.show()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        pixmap = QPixmap("resources/background.jpg").scaled(
            self.label.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.label.setPixmap(pixmap)

    def initWindow(self):
        self.resize(1000, 650)
        self.setWindowIcon(QIcon("resources/logo.png"))
        # self.version = "v23111.0.0"
        # self.setWindowTitle('云迹物联授权及产测工具_' + self.version)
        # self.setWindowFlag(Qt.WindowTitleHint, False)
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


class CostumerTitleBar(TitleBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.minBtn.setVisible(False)
        self.maxBtn.setVisible(False)
        self.closeBtn.setVisible(False)


class Window(FluentWindow):
    """ 主界面 """

    login_goback_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.close_cnt = 1;
        # self.initWindow()
        self.resize(1000, 700)
        self.setWindowIcon(QIcon("resources/logo.png"))
        self.setWindowTitle('云迹物联离线检测工具_' + self.version)
        self.version = APP_VERSION  # 使用从version_manager获取的版本号

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        setThemeColor("#28afe9")
        # 创建子界面
        # self.settingInterface = SettingInterface(self)
        # self.homeInterface = AuthTestInterface(self)
        # self.recordInterface = ChartRecordInterface(self)
        self.deviceInterface = DeviceStateInterface(self)
        # self.albumInterface = Widget('Album Interface', self)
        # self.albumInterface1 = Widget('Album Interface 1', self)

        # create splash screen
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setTitleBar(CostumerTitleBar(self))
        self.splashScreen.setIconSize(QSize(106, 106))
        self.splashScreen.raise_()
        QApplication.processEvents()

        self.initNavigation()

        self.timer = QTimer(self)
        self.timer.start(1500)
        self.timer.timeout.connect(self.stop_waiting)

    def stop_waiting(self):
        self.splashScreen.finish()
        self.timer.stop()

    def show_win_slot(self):
        self.raise_()
        self.show()
        # self.initNavigation()

    def initNavigation(self):
        # self.addSubInterface(self.homeInterface, FIF.HOME, 'Authorization&Test')

        # self.addSubInterface(self.recordInterface, FIF.SEARCH, 'Record')
        self.addSubInterface(self.deviceInterface, FIF.DEVELOPER_TOOLS, "Device detection")
        # self.addSubInterface(self.albumInterface, FIF.ALBUM, 'Albums', NavigationItemPosition.SCROLL)
        # self.addSubInterface(self.albumInterface1, FIF.ALBUM, 'Album 1', parent=self.albumInterface)
        self.navigationInterface.addSeparator()

        self.navigationInterface.addWidget(
            routeKey='avatar',
            widget=NavigationAvatarWidget('Account', QPixmap('resources/logo.png'), self),
            onClick=self.account_set,
            position=NavigationItemPosition.BOTTOM
        )

        # self.addSubInterface(self.albumInterface1, FIF.ALBUM, 'Album 1', parent=self.albumInterface)

        # self.addSubInterface(self.settingInterface, FIF.SETTING, 'Operations Notice', NavigationItemPosition.BOTTOM)

    def account_set(self):
        msgbox = MessageBox('提醒', "是否要退出当前账号？", self)
        msgbox.yesButton.setText("退出")
        msgbox.cancelButton.setText("取消")

        if msgbox.exec():
            self.close()
            self.login_goback_signal.emit()

    def initWindow(self):
        self.resize(980, 900)
        self.setWindowIcon(QIcon("resources/logo.png"))
        self.version = "v23111.0.0"
        self.setWindowTitle('云迹物联授权及产测工具_' + self.version)
        # self.setFont(QFont('Microsoft YaHei', pointSize=16))

        QApplication.processEvents()

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
    MainWin = Window()
    LoginWin = LoginWindow()

    # signal slot
    LoginWin.login_succeed_signal.connect(MainWin.show_win_slot)
    MainWin.login_goback_signal.connect(LoginWin.show_win_slot)


    def cleanup():
        LoginWin.login_succeed_signal.disconnect()
        MainWin.login_goback_signal.disconnect()
        print("Cleaning up before quit")

    app.aboutToQuit.connect(cleanup)
    LoginWin.show()
    # MainWin.show()

    # setTheme(Theme.DARK)
    sys.exit(app.exec())
