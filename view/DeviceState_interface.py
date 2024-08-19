# coding:utf-8
import json
import time

import serial
import serial.tools.list_ports
from PyQt5.QtCore import QFileInfo, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect, QFileDialog, QTabWidget
from serial.serialutil import SerialException

from DeviceStateChk import DeviceStateChkThread, deviceOnline
from baseLogger import log
from baseUart import BaseUartThread
from myTableWidget import myTableModel
from qfluentwidgets import FluentIcon, MessageBox, Flyout, InfoBarIcon
from resource.ui.DeviceStateInterface_UI import Ui_DeviceStateInterface_UI

CONN_OVERTIME = 5 * 10


def showMessage(title, content, parent=None):
    MessageBox(title, content, parent).show()


class DataPoint:
    def __init__(self, dpid, msgtype, type, value, page):
        self.id = dpid
        self.msg = msgtype
        self.type = type
        self.value = value
        self.page = page


def find_category_by_id(data, target_id):
    # 遍历数据中的每一个大类别
    for category, items in data.items():
        # 在每个大类别中遍历每个项目
        for item in items:
            # 检查当前项目的id是否匹配目标id
            if item.get("id") == target_id:
                return category  # 返回匹配的组别名称


class Queue:
    def __init__(self):
        self.items = []

    def is_empty(self):
        return not bool(self.items)

    def enqueue(self, item):
        self.items.append(item)

    def dequeue(self):
        if self.is_empty():
            return None
        return self.items.pop(0)

    def peek(self):
        if self.is_empty():
            return None
        return self.items[0]

    def size(self):
        return len(self.items)


def tranType2Str(data: bytes, typeInt: int):
    if typeInt == 0:
        # 假设0表示的是原始的十六进制表示
        data = data.hex()
        return data, "raw"
    elif typeInt == 1:
        # 假设1表示的是布尔值，这里假设数据长度为1字节
        if len(data) > 0:
            return bool(data[0]), "bool"
        else:
            return None, "bool"
    elif typeInt == 2:
        # 假设2表示的是某种值，可能是整数，这里假设为整数
        if data:
            return int.from_bytes(data, byteorder='big'), "value"
        else:
            return None, "value"
    elif typeInt == 3:
        # 假设3表示的是ASCII编码的字符串
        try:
            data = data.decode('ascii')
            return data, "string"
        except UnicodeDecodeError:
            return None, "string"

    elif typeInt == 4:
        # 假设4表示的是枚举值，作为整数返回
        if data:
            return int.from_bytes(data, byteorder='big'), "enum"
        else:
            return None, "enum"
    elif typeInt == 5:
        # 假设5表示的是位图，转换为二进制（bin）字符串
        bits = bin(int.from_bytes(data, byteorder='big'))[2:]  # 从'int'转为二进制字符串表示
        # 补充前导零，使长度为8的倍数
        bits = bits.zfill(8 * ((len(bits) + 7) // 8))
        return bits, "bitmap"
    else:
        # 未知类型
        return "unknown", "unknown"


class DeviceStateTask(QThread):
    LightTrigger = pyqtSignal(str, str)
    stateSignal = pyqtSignal(deviceOnline)
    dataPointSignal = pyqtSignal(DataPoint)

    def __init__(self, parent=None):
        super(DeviceStateTask, self).__init__(parent=parent)

        self.color = "#e6e6e6"
        self.text = "Serial is not Connection"
        self.ChkConnFlag = True
        self.FilterDict = self.parent().DpDict

        self.LightTrigger.connect(self.parent().light_callback)
        self.dataPointSignal.connect(self.parent().updateDpValueCallback)

        self.overTimeConn = deviceOnline(0, 0, 0, 0)
        self.page = self.parent().page
        self.running = 1

        self.dpDateRevList = Queue()
        # 創建串口線程

    def DpProcess(self, data):
        dpid = int(data.dpid)
        value, dptype = tranType2Str(data.value, data.type)  # data.type

        if value is None or value == "unknown":
            log.logger.warning("error msg, dpid:%s,type:%s,value:%s" % (dpid, dptype, str(value)))
            return

        group = find_category_by_id(self.FilterDict, dpid)

        if group is not None:
            if group == "Dashboard_Dp_Data":
                page = 0
                self.overTimeConn.dashBoardOnline = CONN_OVERTIME
            elif group == "Controller_Dp_Data":
                page = 1
                self.overTimeConn.controllerOnline = CONN_OVERTIME
            elif group == "BMS_Dp_Data":
                page = 2
                self.overTimeConn.BMSOnline = CONN_OVERTIME
            elif group == "IOT_Dp_Data":
                page = 3
                self.overTimeConn.IotOnline = CONN_OVERTIME
            else:
                return

            items = self.FilterDict[group]

            for item in items:
                if item.get("id") == dpid:
                    dp = DataPoint(dpid, item.get('msg'), dptype, value, page)
                    self.dataPointSignal.emit(dp)
                    return

        log.logger.warning("error msg, dpid:%s,type:%s,value:%s" % (dpid, dptype, str(value)))

    def run(self):
        self.overtimeCnt = 0
        text = "Serial is not Connection"
        color = "#e6e6e6"
        #         # self.LightTrigger.emit(self.color, self.text)

        while self.running:

            if self.parent().serialOnline:

                if (self.overTimeConn.IotOnline > 0 and self.page == 3) or \
                        (self.overTimeConn.BMSOnline > 0 and self.page == 2) or \
                        (self.overTimeConn.controllerOnline > 0 and self.page == 1) or \
                        (self.overTimeConn.dashBoardOnline > 0 and self.page == 0):
                    color = "#1afa29"
                    text = "Device is connection"
                    self.ChkConnFlag = False
                    self.LightTrigger.emit(self.color, self.text)

                elif self.ChkConnFlag:
                    self.overtimeCnt += 1

                    # if exitFlag:
                    # self.DpProcess(41,"string","{\"soft_ver\":\"1.0.0\",\"hard_ver\":\"1.0.0\",\"sn\":\"1233445857\"}")
                    # self.DpProcess(22,"value","50")
                    # break

                    text = "Waiting for device connection " + (self.overtimeCnt % 7) * "."
                    color = "#f4ea2a"
                    time.sleep(0.1)

                    if self.overtimeCnt >= 30:
                        self.ChkConnFlag = False
                        color = "#d81e06"
                        text = "Device connection overtime"
            else:
                color = "#e6e6e6"
                text = "Serial is not Connection"
                self.overTimeConn.clearAll()

            if text != self.text or color != self.color:
                self.text = text
                self.color = color
                self.LightTrigger.emit(self.color, self.text)

            # self.overTimeConn.decrementAll()
            page = self.parent().page
            if page != self.page:
                self.page = page
                self.ChkConnFlag = True
            time.sleep(0.01)

    def stop(self):
        self.running = 0

    def startCheckConnect(self):
        self.ChkConnFlag = True
        self.text = "Waiting for device connection......"
        self.color = "#f4ea2a"
        self.overtimeCnt = 0


class DeviceStateInterface(Ui_DeviceStateInterface_UI, QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.DpDict = None
        self.task = None
        self.page = 0
        self.tabPages = 5
        self.setupUi(self)
        self.serialOnline = 0

        # set the icon of button
        self.Button_UpdateSerial.setIcon(FluentIcon.SYNC)
        # self.PrimaryToolButton_playlog.setIcon(FluentIcon.PLAY)

        # 设置串口
        self.ser = serial.Serial(timeout=0.5)

        # 初始化dp列表
        self.InitDataPointList()
        # 组件状态初始化
        self.InitModuleConfig()

    # 组件初始化设置
    def InitModuleConfig(self):

        # 绑定刷新按键
        # self.Button_UpdateSerial.clicked.connect(self.refresh)

        # 设置标签栏样式
        self.tabWidget.setTabPosition(QTabWidget.North)  # 设置选项卡位置在顶部
        self.tabWidget.setTabShape(QTabWidget.Rounded)  # 设置选项卡的形状为圆角
        self.tabWidget.setFont(QFont('Microsoft YaHei Light', pointSize=15))
        # 绑定页面切换
        self.tabWidget.currentChanged.connect(self.onPageChange)
        # 通过样式表设置选项卡的大小
        self.tabWidget.setStyleSheet("QTabBar::tab { width: 150px; }")
        self.tabWidget.setStyleSheet("QTabBar::tab:selected { color: white; background-color: black;}")
        # 绑定串口连接
        self.ButtonConnectSerial.clicked.connect(self.serialConnectChange)
        # 绑定刷新串口
        self.Button_UpdateSerial.clicked.connect(self.refresh)

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

                setattr(self, f"dpTableView", myTableModel(self.DpDict['Dashboard_Dp_Data']))
                getattr(self, f"DeviceStateLayout").addWidget(getattr(self, f"dpTableView"))

            else:
                self.setShadowEffect(getattr(self, f"DeviceCard_{tab + 1}"))
                self.setShadowEffect(getattr(self, f"SettingCard_{tab + 1}"))

                getattr(self, f"ParamFileToolButton_{tab + 1}").setIcon(FluentIcon.FOLDER)
                getattr(self, f"FirmFileToolButton_{tab + 1}").setIcon(FluentIcon.FOLDER)
                widget = getattr(self, f"FirmFileName_{tab + 1}")
                getattr(self, f"FirmFileToolButton_{tab + 1}").clicked.connect(self.create_callback(widget))
                widget2 = getattr(self, f"ParamFileName_{tab + 1}")
                getattr(self, f"ParamFileToolButton_{tab + 1}").clicked.connect(self.create_callback(widget2))
                if tab == 1:
                    groupStr = "Controller_Dp_Data"
                if tab == 2:
                    groupStr = "BMS_Dp_Data"
                if tab == 3:
                    groupStr = "IoT_Dp_Data"
                if tab == 4:
                    groupStr = "SubBMS_Dp_Data"

                setattr(self, f"dpTableView_{tab}", myTableModel(self.DpDict[groupStr]))
                getattr(self, f"DeviceStateLayout_{tab + 1}").addWidget(getattr(self, f"dpTableView_{tab}"))

        for tab in range(self.tabPages):
            self.page = tab
            self.light_callback("#e6e6e6", "Serial is not Connection")

        self.page = 0

        self.tabWidget.setCurrentIndex(self.page)
        # 串口刷新设置
        self.refresh()
        self.DeviceTask()

    def updateDpValueCallback(self, DpParam):

        if DpParam.msg == 'ver':
            try:
                param = json.loads(DpParam.value)
            except Exception as e:
                log.logging.error(e)
                return
            if DpParam.page == 0:
                getattr(self, f"HWVersion").setText(param.get('hard_ver', ''))
                getattr(self, f"FirmwareVersion").setText(param.get('soft_ver', ''))
                getattr(self, f"SN").setText(param.get('sn', ''))
            else:
                if DpParam.page == 2:
                    param = param['batt_1']
                getattr(self, f"HWVersion_{DpParam.page + 1}").setText(param.get('hard_ver', ''))
                getattr(self, f"FirmwareVersion_{DpParam.page + 1}").setText(param.get('soft_ver', ''))
                getattr(self, f"SN_{DpParam.page + 1}").setText(param.get('sn', ''))

        elif DpParam.msg == 'data':
            getattr(self, f"dpTableView_{DpParam.page}").updateData(DpParam.id, DpParam.type, DpParam.value)

        else:
            log.logger.debug("未知消息")

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
        if self.serialOnline == 1:
            self.light_callback("#e6e6e6", "Serial is not Connection")

        try:
            if self.task.running:
                self.task.startCheckConnect()
                return
        except Exception as e:
            log.logger.error(e)
            pass

    def serialDisconnect(self):
        try:
            self.ser.close()
        except SerialException:
            log.logger.warning("串口已经被关闭")
        self.ButtonConnectSerial.setText("Connect")
        self.serialOnline = 0
        self.testSetStateChange(False)

        if hasattr(self, 'serialThread') and self.serialThread.isRunning():
            self.serialThread.quit()  # 假设quit方法可以停止线程
            self.serialThread.wait()  # 等待线程真正退出
        if hasattr(self, 'uartThread') and self.uartThread.isRunning():
            self.uartThread.stop()

    def serialConnectChange(self):
        # 开始/停止按钮-状态切换
        if not self.serialOnline:
            self.initialSerial()


            try:
                self.ser.open()  # 打开串口有可能失败，做try-except异常处理
            except SerialException:
                showMessage("提示", "当前无串口或者串口被占用", self)
                return None

            self.serialOnline = 1
            self.ButtonConnectSerial.setText("Disconnect")

            # 创建BaseUartThread线程实例,
            self.serialThread = BaseUartThread(self.ser)
            self.uartThread = DeviceStateChkThread()

            self.serialThread.revData_sinOut.connect(self.uartThread.uartProc)
            self.serialThread.error_sinOut.connect(self.serialDisconnect)
            self.uartThread.DS_uartWrite_sinOut.connect(self.serialThread.uartWrite)
            self.uartThread.DS_dPRevSignal_sinOut.connect(self.task.DpProcess)

            # 启动BaseUartThread线程实例
            self.serialThread.start()
            self.uartThread.start()
            self.testSetStateChange(True)

        else:
            try:
                self.ser.close()
            except SerialException:
                log.logger.warning("串口已经被关闭")
            self.ButtonConnectSerial.setText("Connect")
            self.serialOnline = 0
            self.testSetStateChange(False)

            if hasattr(self, 'serialThread') and self.serialThread.isRunning():
                self.serialThread.quit()  # 假设quit方法可以停止线程
                self.serialThread.wait()  # 等待线程真正退出
            if hasattr(self, 'uartThread') and self.uartThread.isRunning():
                self.uartThread.stop()

        try:
            # 确保之前的线程已经停止


            if self.task.running:
                self.task.startCheckConnect()
                return
        except Exception as e:
            log.logger.error(e)
            pass

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
        text = self.ComboBox_Serial.currentText()

        for i in range(len(text)):
            if text[i] == ')':
                text = text[:i + 1]
                break

        for port in serial.tools.list_ports.comports():
            if port.description == text:
                self.ser.port = port.device
                break

        self.ser.baudrate = 115200
        self.ser.bytesize = 8
        self.ser.stopbits = 1
        self.ser.parity = 'N'

    # 重写关闭窗口事件
    def closeEvent(self, event):
        if self.ser.isOpen():
            self.serialThread.quit()
            self.uartThread.quit()

    def refresh(self):
        # 查询可用的串口
        plist = serial.tools.list_ports.comports()

        if len(plist) <= 0:
            print("No used com!")
            # 清空comboBox内容
            self.ComboBox_Serial.clear()
            showMessage("提示", "当前无串口或者串口被占用", self)
            self.serialOnline = 0

        else:
            # 把所有的可用的串口输出到comboBox中去
            self.ComboBox_Serial.clear()
            port_status = ""
            for port in plist:
                try:
                    ser = serial.Serial(port.device)
                    ser.close()
                    port_status = "Available"

                except serial.SerialException:
                    port_status = "Busy"
                self.ComboBox_Serial.addItem(port.description + " - " + port_status)

        self.DeviceTask()
        print("刷新串口")

    def InitDataPointList(self):
        with open('resource/config/dataPointCfg.json', 'r', encoding='utf-8', errors='ignore') as file:
            self.DpDict = json.loads(file.read())

    def updatePercentDate(self):
        pass

    def setShadowEffect(self, card: QWidget):
        shadowEffect = QGraphicsDropShadowEffect(self)
        shadowEffect.setColor(QColor(0, 0, 0, 15))
        shadowEffect.setBlurRadius(10)
        shadowEffect.setOffset(0, 0)
        card.setGraphicsEffect(shadowEffect)
