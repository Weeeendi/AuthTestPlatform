# coding:utf-8
import time

import serial
import serial.tools.list_ports
from PyQt5.QtCore import QFileInfo, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect, QFileDialog

from qfluentwidgets import FluentIcon, MessageBox, Flyout, InfoBarIcon
from resource.ui.DeviceStateInterface_UI import Ui_DeviceStateInterface_UI


def showMessage(title, content, parent=None):
    MessageBox(title, content, parent).show()


class DataPoint:
    def __init__(self, code, dpid, msg, default_value, desc, name, property):
        self.code = code
        self.id = dpid
        self.msg = msg
        self.default_value = default_value
        self.desc = desc
        self.name = name
        self.property = property

    def __repr__(self):
        return f"DataPoint(code={self.code}, id={self.id}, msg={self.msg}, defaultValue={self.default_value}, desc={self.desc}, name={self.name}, property={self.property})"


class deviceOnline:
    # 构造函数
    def __init__(self, BashBoard, Controller, BMS, IoT):
        self.bashBoardOnline = BashBoard
        self.controllerOnline = Controller
        self.BMSOnline = BMS
        self.IotOnline = IoT


class DeviceStateTask(QThread):
    trigger = pyqtSignal(str, str)
    stateSignal = pyqtSignal(deviceOnline)
    dataPointSignal = pyqtSignal(DataPoint)

    def __init__(self, parent=None):
        super(DeviceStateTask, self).__init__(parent=parent)
        self.trigger.connect(self.parent().light_callback)
        self.stateSignal.connect(self.onStateChange)
        self.state = self.parent().online
        self.page = self.parent().page
        self.running = 1

    def onStateChange(self, deviceOnlineParam):
        self.state = deviceOnlineParam

    def run(self):
        overtimeCnt = 0
        exitFlag = 0

        text = "Waiting for device connection......"
        color = "#f4ea2a"

        while self.running:
            if not self.parent().serialOnline:
                text = "Serial is not Connection"
                color = "#e6e6e6"
                exitFlag = 1

            if (self.state.IotOnline and self.page == 3) or \
                    (self.state.BMSOnline and self.page == 2) or \
                    (self.state.controllerOnline and self.page == 1) or \
                    (self.state.bashBoardOnline and self.page == 0):
                color = "#1afa29"
                text = "Device is connection"
                exitFlag = 1

            if overtimeCnt >= 30:
                exitFlag = 1
                color = "#d81e06"
                text = "Device connection overtime"

            self.trigger.emit(color, text)
            time.sleep(0.1)
            overtimeCnt += 1

            if exitFlag:
                break

            text = "Waiting for device connection " + (overtimeCnt % 7) * "."

        return

    def stop(self):
        self.running = 0


class DeviceStateInterface(Ui_DeviceStateInterface_UI, QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.task = None
        self.page = 0
        self.tabPages = 4
        self.setupUi(self)

        self.online = deviceOnline(0, 0, 0, 0)

        self.serialOnline = 0

        # set the icon of button
        self.Button_UpdateSerial.setIcon(FluentIcon.SYNC)
        # self.PrimaryToolButton_playlog.setIcon(FluentIcon.PLAY)

        # 串口刷新设置
        self.refresh()
        # 设置串口
        self.ser = serial.Serial(timeout=0.5)

        # 组件状态初始化
        self.InitModuleConfig()

    # 组件初始化设置
    def InitModuleConfig(self):

        # 绑定刷新按键
        # self.Button_UpdateSerial.clicked.connect(self.refresh)

        # 绑定页面切换
        self.tabWidget.currentChanged.connect(self.onPageChange)

        # 绑定串口连接
        self.ButtonConnectSerial.clicked.connect(self.serialConnectChange)

        self.tabWidget.setBackgroundRole(0)

        self.setShadowEffect(self.ConnectCard)

        for tab in range(self.tabPages):
            if tab == 0:
                # add shadow effect to card
                self.setShadowEffect(self.DeviceCard)
                self.setShadowEffect(self.SettingCard)

                self.ParamFileToolButton.setIcon(FluentIcon.FOLDER)
                self.FirmFileToolButton.setIcon(FluentIcon.FOLDER)

                self.ParamFileToolButton.clicked.connect(lambda: self.obtainPath(self.ParamFileName))
                self.FirmFileToolButton.clicked.connect(lambda: self.obtainPath(self.FirmFileName))

            else:
                self.setShadowEffect(getattr(self, f"DeviceCard_{tab + 1}"))
                self.setShadowEffect(getattr(self, f"SettingCard_{tab + 1}"))

                getattr(self, f"ParamFileToolButton_{tab + 1}").setIcon(FluentIcon.FOLDER)
                getattr(self, f"FirmFileToolButton_{tab + 1}").setIcon(FluentIcon.FOLDER)
                widget = getattr(self, f"FirmFileName_{tab + 1}")
                getattr(self, f"FirmFileToolButton_{tab + 1}").clicked.connect(self.create_callback(widget))
                widget2 = getattr(self, f"ParamFileName_{tab + 1}")
                getattr(self, f"ParamFileToolButton_{tab + 1}").clicked.connect(self.create_callback(widget2))

        self.tabWidget.setCurrentIndex(self.page)

        self.DeviceTask()

    def create_callback(self, widget):
        def callback():
            self.obtainPath(widget)

        return callback

    def obtainPath(self, fileNameWidget):
        options = QFileDialog.Options()
        filePath, _ = QFileDialog.getOpenFileName(self, "选择文件", None, "File (*.bin);;All Files (*)",
                                                  options=options)
        if filePath:
            fileName = QFileInfo(filePath).filePath()
            fileNameWidget.setText(fileName)
        else:
            return None

    def DeviceTask(self):
        try:
            if self.task.isRunning():
                self.task.stop()
        except Exception as e:
            print(e)
        self.task = DeviceStateTask(self)
        self.task.start()

    def light_callback(self, color, text):
        if self.page == 0:
            self.connStateIcon.setCustomBackgroundColor(QColor(color), QColor(color))
            self.connStateLabel.setText(text)
            self.connStateIcon.setFixedSize(16, 16)
            self.connStateIcon.setIconSize(QSize(16, 16))
        else:
            getattr(self, f"connStateIcon_{self.page + 1}").setCustomBackgroundColor(QColor(color),
                                                                                     QColor(color))
            getattr(self, f"connStateIcon_{self.page + 1}").setFixedSize(16, 16)
            getattr(self, f"connStateIcon_{self.page + 1}").setIconSize(QSize(16, 16))
            getattr(self, f"connStateLabel_{self.page + 1}").setText(text)

    def onPageChange(self):
        self.page = self.tabWidget.currentIndex()
        print("current page is " + str(self.page))
        self.DeviceTask()

    def serialConnectChange(self):
        # 开始/停止按钮-状态切换
        if not self.serialOnline:
            self.initialSerial()

            try:
                self.ser.open()  # 打开串口有可能失败，做try-except异常处理
            except Exception:
                showMessage("提示", "当前无串口或者串口被占用", self.nativeParentWidget())
                return None
            self.serialOnline = 1
            self.ButtonConnectSerial.setText("Disconnect")
        else:
            self.ser.close()
            self.ButtonConnectSerial.setText("Connect")
            self.serialOnline = 0

        self.DeviceTask()


    # 测试项设置状态变更
    def testSetStateChange(self, bool_value):
        # 串口号选择-禁止/使能
        self.ComboBox_Serial.setDisabled(bool_value)
        # 串口刷新按钮
        self.Button_UpdateSerial.setDisabled(bool_value)

        self.UpdateProgressBar.setVal(0)

    def showFlyout(self, title, content, Widget_object):
        Flyout.create(
            icon=InfoBarIcon.ERROR,
            title=title,
            content=content,
            target=Widget_object,
            parent=self,
            isClosable=True
        )

    def initialSerial(self):
        # 默认 115200 波特率，8位数据位，1位停止位，无校验
        self.ser.port = self.ComboBox_Serial.currentText()
        self.ser.baudrate = 115200
        self.ser.bytesize = 8
        self.ser.stopbits = 1
        self.ser.parity = 'N'

    # 重写关闭窗口事件
    def closeEvent(self, event):
        if self.ser.isOpen():
            self.serialThread.quit()
            self.OTAThread.quit()


    def refresh(self):
        # 查询可用的串口
        plist = list(serial.tools.list_ports.comports())

        if len(plist) <= 0:
            print("No used com!")
            # 清空comboBox内容
            self.ComboBox_Serial.clear()
            showMessage("提示", "当前无串口或者串口被占用", self.nativeParentWidget())

        else:
            # 把所有的可用的串口输出到comboBox中去
            self.ComboBox_Serial.clear()
            for i in range(0, len(plist)):
                plist_0 = list(plist[i])
                self.ComboBox_Serial.addItem(str(plist_0[0]))

        print("刷新串口")

    # 作为槽函数于Stream的信号连接, 内部参数于信号发射参数相同
    def onDpDataChanged(self, dpFrame):
        print("receive dp data", dpFrame)

    def updatePercentDate(self):
        pass

    # 自定义槽，处理测试进度条数据
    def dealProgressBarTest(self, xInt, xStr):
        pass

    def dealAuthData(self, authInfo):
        """自定义槽，处理授权信息"""
        # 判断输入是否有效
        if not authInfo:
            return None
        # 清空上次授权信息
        self.AuthRES_TextEdit.clear()
        # 获取光标位置
        cursor = self.AuthRES_TextEdit.textCursor()
        cursor.insertText(authInfo)

    def setShadowEffect(self, card: QWidget):
        shadowEffect = QGraphicsDropShadowEffect(self)
        shadowEffect.setColor(QColor(0, 0, 0, 15))
        shadowEffect.setBlurRadius(10)
        shadowEffect.setOffset(0, 0)
        card.setGraphicsEffect(shadowEffect)
