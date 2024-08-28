# coding:utf-8
import json
import os
import time

import serial
import serial.tools.list_ports
from PyQt5.QtCore import QFileInfo, QSize, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect, QFileDialog, QTabWidget, QVBoxLayout, QHeaderView, \
    QSizePolicy
from serial.serialutil import SerialException

from DeviceStateChk import DeviceStateChkThread, OTAState
from baseLogger import log
from baseUart import BaseUartThread
from myTableWidget import myTableModel
from qfluentwidgets import FluentIcon, MessageBox, Flyout, InfoBarIcon, themeColor, CheckBox, LineEdit, \
    ToolButton, TableWidget
from resource.ui.DeviceStateInterface_UI import Ui_DeviceStateInterface_UI

CONN_OVERTIME = 5 * 10


class deviceOnline:
    # 构造函数
    def __init__(self, DashBoard: int, Controller: int, BMS: int, IoT: int, SubBMS: int):
        self.dashBoardOnline = DashBoard
        self.controllerOnline = Controller
        self.BMSOnline = BMS
        self.IotOnline = IoT
        self.SubBMSOnline = SubBMS

    def clearAll(self):
        attrs = ['dashBoardOnline', 'controllerOnline', 'BMSOnline', 'IotOnline']
        for attr in attrs:
            if hasattr(self, attr):  # 确保对象有这个属性
                setattr(self, attr, 0)

    def decrementAll(self):
        attrs = ['dashBoardOnline', 'controllerOnline', 'BMSOnline', 'IotOnline']
        for attr in attrs:
            if hasattr(self, attr):  # 确保对象有这个属性
                current_value = getattr(self, attr)
                if isinstance(current_value, int) and current_value > 0:  # 确保值是整数
                    setattr(self, attr, current_value - 1)
                # else:
                #     print(f"Cannot decrement {attr}: not an integer")


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


def tranType2Str(data: bytes, typeInt: int) -> (bytes, str):
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
    dataPointSignal = pyqtSignal(DataPoint)
    pageChangeSignal = pyqtSignal(int)
    serialOnlineSignal = pyqtSignal(bool)

    DevList = ["BMS_Dp_Data", "IoT_Dp_Data", "Controller_Dp_Data", "Dashboard_Dp_Data", "SubBMS_Dp_Data"]
    ErrCodeList = ["controller_fault", "dashboard_fault", "bms_fault", "sub_bms_fault", "iot_fault"]

    def __init__(self, parent=None, DpDict=None):
        super(DeviceStateTask, self).__init__(parent=parent)

        self.overtimeCnt = 0
        self.color = "#e6e6e6"
        self.text = "Serial is not Connection"
        self.ChkConnFlag = True
        self.FilterDict = DpDict

        self.pageChangeSignal.connect(self.onPageChange)
        self.serialOnlineSignal.connect(self.onSerialOnline)

        self.overTimeConn = deviceOnline(0, 0, 0, 0, 0)
        self.page = 0
        self.serialOnline = 0
        # 错误字典
        self.errCodeDict = {}
        self.initErrDict()

        self.running = 1

    def initErrDict(self):
        for Dev in self.DevList:
            try:
                group = self.FilterDict[Dev]
                for key in group:
                    if key.get("code") in self.ErrCodeList:
                        self.errCodeDict[key.get("code")] = key.get("id")
            except Exception as e:
                log.logger.error(e)

        with open('resource/config/bitmapTranslation.json', 'r', encoding='utf-8', errors='ignore') as file:
            self.errDict = json.loads(file.read())

    def onPageChange(self, page):
        self.page = page
        self.startCheckConnect()

    def onSerialOnline(self, online):
        self.serialOnline = online

    def addErrDescription(self, dpid, value) -> str:
        strList = ""
        for errCode in self.ErrCodeList:
            if dpid == self.errCodeDict[errCode]:
                for i in range(len(value)):
                    if value[-(i + 1)] == '1':
                        correct_key = f"bit{i}"
                        try:
                            strList = strList + self.errDict[errCode][0][correct_key].get("description", "") + "\n"
                        except KeyError:
                            log.logger.debug("key error")
                            break
                if strList == "":
                    strList = "无故障"
                return strList

        else:
            return value

    def DpProcess(self, data):
        dpid = int(data.dpid)
        value, dptype = tranType2Str(data.value, data.type)  # data.type

        value = self.addErrDescription(dpid, value)

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
            elif group == "Sub_BMS_Dp_Data":
                page = 4
                self.overTimeConn.SubBMSOnline = CONN_OVERTIME

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

            if self.serialOnline:
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

            time.sleep(0.01)

    def stop(self):
        self.running = 0

    def startCheckConnect(self):
        self.ChkConnFlag = True
        self.text = "Waiting for device connection......"
        self.color = "#f4ea2a"
        self.overtimeCnt = 0


class Dp_Row:
    def __init__(self, select, des, hexx):
        self.select = select
        self.des = des
        self.hexx = hexx

    def to_dict(self):
        return {
            "select": self.select,
            "des": self.des,
            "hexx": self.hexx,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(d.get("select"), d.get("des"), d.get("hexx"))


class DP_ListTable(QWidget):
    dataPointSignal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.DpList = []
        self.filename = "resources/user/send_dp_list.json"
        self.totalItems = 0
        self.isProcessingDelete = False
        self.initUI()

    def initUI(self):
        self.LayOut = QVBoxLayout(self)

        # 创建表格
        self.table = TableWidget()

        self.table.setRowCount(2)  # 设置行数
        self.table.setColumnCount(4)  # 设置列数
        # 设置表格头
        self.table.setWordWrap(False)
        self.table.setHorizontalHeaderLabels(['select', 'describe', 'dp date', 'del'])

        checkBox = CheckBox()
        self.table.setCellWidget(self.totalItems, 0, checkBox)

        deslineEdit = LineEdit()
        deslineEdit.setPlaceholderText("描述")
        self.table.setCellWidget(self.totalItems, 1, deslineEdit)

        lineEdit = LineEdit()
        lineEdit.setPlaceholderText("命令内容")
        self.table.setCellWidget(self.totalItems, 2, lineEdit)

        deleteButton = ToolButton(FluentIcon.DELETE)

        deleteButton.setMaximumSize(30, 30)
        self.table.setCellWidget(self.totalItems, 3, deleteButton)
        deleteButton.clicked.connect(self.deleteCommand)

        self.totalItems += 1

        self.addButton = ToolButton(FluentIcon.ADD)
        self.addButton.clicked.connect(self.addCommand)
        self.addButton.setMaximumHeight(30)
        self.table.setSpan(1, 0, 1, 4)
        self.table.setCellWidget(self.totalItems, 0, self.addButton)

        # 让第二列扩展以填充可用空间
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        # 隐藏第一列 (索引为0)
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)

        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.LayOut.addWidget(self.table)


    def addCommand(self, select=False, des='', hexx=''):

        self.table.insertRow(self.totalItems)  # 插入一行
        self.table.setRowCount(self.totalItems + 2)  # 设置列数

        checkBox = CheckBox()
        checkBox.setChecked(select)
        self.table.setCellWidget(self.totalItems, 0, checkBox)

        deslineEdit = LineEdit()
        deslineEdit.setText(des)

        self.table.setCellWidget(self.totalItems, 1, deslineEdit)

        lineEdit = LineEdit()
        lineEdit.setText(hexx)
        self.table.setCellWidget(self.totalItems, 2, lineEdit)

        deleteButton = ToolButton(FluentIcon.DELETE)
        deleteButton.setMaximumSize(30, 30)
        deleteButton.clicked.connect(self.deleteCommand)
        self.table.setCellWidget(self.totalItems, 3, deleteButton)

        self.totalItems += 1

    def saveTheDpList(self):
        dict_list = []

        for row in range(self.totalItems - 1):
            try:
                hexx = self.item(row, 2).text()
                if hexx == "":
                    continue
                select = self.item(row, 0).isChecked()
                des = self.item(row, 1).text()

            except AttributeError:
                log.logger.error("error:dp list not attribute")

            dp_item = Dp_Row(select, des, hexx)
            self.DpList.append(dp_item)

        # 将对象列表转换为字典列表
        for obj in self.DpList:
            if obj.hexx != '':
                dict_list.append(obj.to_dict())
        try:
            # 将字典列表写入JSON文件
            with open(self.filename, "w") as file:
                json.dump(dict_list, file, indent=4)
        except IOError as e:
            print(f"An error occurred while writing to file: {e.strerror}")

    def loadTheDpList(self):

        cls = Dp_Row
        # 读取命令列表
        if os.path.exists(self.filename):
            # 从JSON文件中读取数据
            with open(self.filename, "r") as file:
                dict_list = json.load(file)

            # 将字典列表转换为对象列表
            self.DpList.append(cls.from_dict(d) for d in dict_list)
        else:
            self.DpList = []

    def deleteCommand(self):

        if self.isProcessingDelete:
            return  # 忽略重复的删除请求
        self.isProcessingDelete = True

        try:
            # 删除指定的命令布局
            btn = self.sender()

            btn.disconnect()

            # 获取按钮所在的行
            row = self.table.indexAt(btn.pos()).row()

            log.logger.debug("delete row %d" % row)

            # 遍历该行的每一列，并删除单元格的设置
            for col in range(self.table.columnCount()):
                self.table.setCellWidget(row, col, None)  # 移除单元格的小部件
                # 删除特定行
            if row != -1:  # 确保获取的行号有效
                self.table.removeRow(row)

            # 更新 totalItems 计数以反映当前的行数
            if self.totalItems > 0:
                self.totalItems -= 1

            # 调整行数以删除包含按钮的那一行
            self.table.setRowCount(self.totalItems + 1)
        finally:
            self.isProcessingDelete = False

        self.table.viewport().update()


class DeviceStateInterface(Ui_DeviceStateInterface_UI, QWidget):
    # 开始OTA信号
    updateSignal_Out = pyqtSignal(str, int)
    # 结束OTA信号
    StopUpdateSignal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.revSharkHand = False
        self.OTAstate = OTAState.GoOn
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
                self.ButtonStartOTA.clicked.connect(self.onUpdateButton)
                self.CheckBox_Param.stateChanged.connect(self.onUpdateFileCheckBox)
                self.CheckBox_Firmware.stateChanged.connect(self.onUpdateFileCheckBox)
                setattr(self, f"dpTableView", myTableModel(self.DpDict['Dashboard_Dp_Data']))
                getattr(self, f"DeviceStateLayout").addWidget(getattr(self, f"dpTableView"))

            else:
                self.setShadowEffect(getattr(self, f"DeviceCard_{tab + 1}"))
                self.setShadowEffect(getattr(self, f"SettingCard_{tab + 1}"))

                getattr(self, f"CheckBox_Param_{tab + 1}").stateChanged.connect(self.onUpdateFileCheckBox)
                getattr(self, f"CheckBox_Firmware_{tab + 1}").stateChanged.connect(self.onUpdateFileCheckBox)

                getattr(self, f"ParamFileToolButton_{tab + 1}").setIcon(FluentIcon.FOLDER)
                getattr(self, f"FirmFileToolButton_{tab + 1}").setIcon(FluentIcon.FOLDER)
                widget = getattr(self, f"FirmFileName_{tab + 1}")
                getattr(self, f"FirmFileToolButton_{tab + 1}").clicked.connect(self.create_callback(widget))
                widget2 = getattr(self, f"ParamFileName_{tab + 1}")
                getattr(self, f"ParamFileToolButton_{tab + 1}").clicked.connect(self.create_callback(widget2))
                if tab == 1:
                    groupStr = "Controller_Dp_Data"
                elif tab == 2:
                    groupStr = "BMS_Dp_Data"
                elif tab == 3:
                    groupStr = "IoT_Dp_Data"
                elif tab == 4:
                    groupStr = "SubBMS_Dp_Data"
                else:
                    log.logger.debug('未知错误')
                    return

                setattr(self, f"dpTableView_{tab}", myTableModel(self.DpDict[groupStr]))
                getattr(self, f"DeviceStateLayout_{tab + 1}").addWidget(getattr(self, f"dpTableView_{tab}"))
                getattr(self, f"ButtonStartOTA_{tab + 1}").clicked.connect(self.onUpdateButton)

        for tab in range(self.tabPages):
            self.page = tab
            self.light_callback("#e6e6e6", "Serial is not Connection")
            self.onUpdateFileCheckBox()

        self.page = 0

        # 单独初始化 Dongle 页
        self.FirmFileToolButton_Dongle.setIcon(FluentIcon.FOLDER)
        self.FirmFileToolButton_Dongle.clicked.connect(lambda: self.obtainPath(self.FirmFileName_Dongle))
        self.ButtonStartOTA_Dongle.clicked.connect(self.onUpdateDongle)

        self.DpPCB = DP_ListTable()
        self.DpListLayout.addWidget(self.DpPCB)

        self.tabWidget.setCurrentIndex(self.page)
        # 串口刷新设置
        self.refresh()

        # 启动设备状态检测任务
        self.task = DeviceStateTask(self, self.DpDict)
        self.task.LightTrigger.connect(self.light_callback)
        self.task.dataPointSignal.connect(self.updateDpValueCallback)
        self.task.start()

    def onUpdateDongle(self):
        page = self.tabWidget.currentIndex()

        if self.ButtonStartOTA_Dongle.text() == "Stop":
            self.ButtonStartOTA_Dongle.setText("Software Update")
            self.FirmFileName_Dongle.setDisabled(False)
            self.FirmFileToolButton_Dongle.setDisabled(False)
            self.tabWidget.tabBar().setDisabled(False)
            self.StopUpdateSignal.emit()
        else:
            path = self.FirmFileName_Dongle.text()
            # 判断文件名称是否为空
            if path == "":
                self.showFlyout("提醒", "请先选择升级文件", self.FirmFileName)
                return
            # 判断文件是否存在
            if not os.path.isfile(path):
                self.showFlyout("提醒", "文件不存在,请确认后再次尝试", self.FirmFileName)
                return

            self.updateSignal_Out.emit(path, page)
            self.ButtonStartOTA_Dongle.setText("Stop")
            self.FirmFileName_Dongle.setDisabled(True)
            self.FirmFileToolButton_Dongle.setDisabled(True)
            self.tabWidget.tabBar().setDisabled(True)

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
                    try:
                        param = param['batt_1']
                    except KeyError:
                        log.logger.debug("key error")
                        return
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

    def light_callback(self, color, text):
        if color == "#1afa29":
            state = False
        else:
            state = True

        if self.page == 0:
            self.ButtonStartOTA.setDisabled(state)
            self.connStateIcon.setCustomBackgroundColor(QColor(color), QColor(color))
            self.connStateLabel.setText(text)
            self.connStateIcon.setFixedSize(16, 16)
            self.connStateIcon.setIconSize(QSize(16, 16))
        else:
            try:
                getattr(self, f"ButtonStartOTA_{self.page + 1}").setDisabled(state)
            except AttributeError:
                pass

            getattr(self, f"connStateIcon_{self.page + 1}").setCustomBackgroundColor(QColor(color), QColor(color))
            getattr(self, f"connStateIcon_{self.page + 1}").setFixedSize(16, 16)
            getattr(self, f"connStateIcon_{self.page + 1}").setIconSize(QSize(16, 16))
            getattr(self, f"connStateLabel_{self.page + 1}").setText(text)

    def onPageChange(self):
        page = self.tabWidget.currentIndex()
        if page < self.tabPages:
            self.page = page
        else:
            return

        print("current page is " + str(self.page))
        if self.serialOnline == 1:
            self.light_callback("#e6e6e6", "Serial is not Connection")

        try:
            if self.task.running:
                self.task.pageChangeSignal.emit(self.page)
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
        self.ButtonStartOTA_Dongle.setDisabled(True)

        if hasattr(self, 'serialThread') and self.serialThread.isRunning():
            self.serialThread.quit()  # 假设quit方法可以停止线程
            self.serialThread.wait()  # 等待线程真正退出
        if hasattr(self, 'uartThread') and self.uartThread.isRunning():
            self.uartThread.stop()

        self.light_callback("#e6e6e6", "Serial is not Connection")

    def sharkHandFailed(self):
        # 接收到握手失败
        self.showFlyout("提示", "dongle建立连接失败", self.ButtonConnectSerial)
        self.serialDisconnect()

    def revDongleInfo(self, swVer, hdVer, bootVer, sn):
        """
        接收dongle版本号信息
        """

        try:
            self.HWVersion_Dongle.setText(hdVer)
            self.FirmwareVersion_Dongle.setText(swVer)
            self.BootVersion_Dongle.setText(bootVer)
            self.SN_Dongle.setText(sn)
        except Exception as e:
            log.logger.error("版本号接收出错 %s" % e)

    def serialConnectChange(self):
        # 开始/停止按钮-状态切换
        if not self.serialOnline:
            self.initialSerial()

            try:
                self.ser.open()  # 打开串口有可能失败，做try-except异常处理
            except SerialException:
                showMessage("提示", "当前无串口或者串口被占用", self)
                return None

            # 创建BaseUartThread线程实例,
            self.serialThread = BaseUartThread(self.ser)
            self.uartThread = DeviceStateChkThread()

            # 連接前先嘗試斷開
            try:
                self.serialThread.revData_sinOut.disconnect()
                self.serialThread.error_sinOut.disconnect()

                self.uartThread.DS_uartWrite_sinOut.disconnect()
                self.uartThread.DS_dPRevSignal_sinOut.disconnect()
                self.uartThread.DS_progressBar_sinOut.disconnect()
                self.uartThread.DS_shakeHandSignal_sinOut.disconnect()
                self.uartThread.DS_dongleVersionSignal_sinOut.disconnect()

                self.updateSignal_Out.disconnect()
                self.StopUpdateSignal.disconnect()
            except Exception:
                pass

            # 连接信号
            self.serialThread.revData_sinOut.connect(self.uartThread.uartProc)
            self.serialThread.error_sinOut.connect(self.serialDisconnect)
            self.uartThread.DS_uartWrite_sinOut.connect(self.serialThread.uartWrite)
            self.uartThread.DS_dPRevSignal_sinOut.connect(self.task.DpProcess)
            self.uartThread.DS_progressBar_sinOut.connect(self.onChangeOTAState)
            self.uartThread.DS_shakeHandSignal_sinOut.connect(self.sharkHandFailed)
            self.uartThread.DS_dongleVersionSignal_sinOut.connect(self.revDongleInfo)

            self.updateSignal_Out.connect(self.uartThread.onStartOTA)
            self.StopUpdateSignal.connect(self.uartThread.onStopOTA)

            self.ButtonStartOTA_Dongle.setDisabled(False)

            # 启动BaseUartThread线程实例
            self.serialThread.start()
            self.uartThread.start()

            self.serialOnline = 1
            self.ButtonConnectSerial.setText("Disconnect")

            self.testSetStateChange(True)

        else:
            try:
                self.ser.close()
            except SerialException:
                log.logger.warning("串口已经被关闭")
            self.ButtonConnectSerial.setText("Connect")
            self.serialOnline = 0
            self.testSetStateChange(False)

            self.ButtonStartOTA_Dongle.setDisabled(True)

            if hasattr(self, 'serialThread') and self.serialThread.isRunning():
                self.serialThread.quit()  # 假设quit方法可以停止线程
                self.serialThread.wait()  # 等待线程真正退出
            if hasattr(self, 'uartThread') and self.uartThread.isRunning():
                self.uartThread.stop()

        try:
            if self.task.running:
                self.task.serialOnlineSignal.emit(self.serialOnline)
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

        self.ser.baudrate = 921600
        self.ser.bytesize = 8
        self.ser.stopbits = 1
        self.ser.parity = 'N'

    # 重写关闭窗口事件
    def closeEvent(self, event):
        if self.task.running:
            self.task.stop()
        if self.ser.isOpen():
            self.ser.close()
            self.serialThread.quit()
            self.serialThread.wait()
            self.uartThread.stop()

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

        print("刷新串口")

    def InitDataPointList(self):
        with open('resource/config/dataPointCfg.json', 'r', encoding='utf-8', errors='ignore') as file:
            self.DpDict = json.loads(file.read())

    def onChangeOTAState(self, percent: int, state: OTAState, OTADescription: str):
        if state == OTAState.GoOn:
            color = themeColor()
            self.OTAstate = OTAState.GoOn
        elif state == OTAState.Success:
            color = "green"
            self.OTAstate = OTAState.Success
            # self.onUpdateButton()
        else:
            color = "red"
            self.OTAstate = OTAState.Fail
            # self.onUpdateButton()

        page = self.tabWidget.currentIndex()

        if page == self.tabPages:
            self.OTAStateLabel_Dongle.setText(OTADescription)
            self.OTAStateLabel_Dongle.setTextColor(QColor(color), QColor(color))
            self.UpdateProgressBar_Dongle.setValue(percent)
            if self.OTAstate == OTAState.Success or self.OTAstate == OTAState.Fail:
                self.onUpdateDongle()
        else:
            if self.OTAstate == OTAState.Success or self.OTAstate == OTAState.Fail:
                self.onUpdateButton()

            if self.page == 0:
                self.OTAStateLabel.setText(OTADescription)
                self.OTAStateLabel.setTextColor(QColor(color), QColor(color))
                self.UpdateProgressBar.setValue(percent)
                # self.UpdateProgressBar.setCustomBackgroundColor(QColor(color), QColor(color))

            else:
                try:
                    getattr(self, f"OTAStateLabel_{self.page + 1}").setText(OTADescription)
                    getattr(self, f"OTAStateLabel_{self.page + 1}").setTextColor(QColor(color), QColor(color))
                    getattr(self, f"UpdateProgressBar_{self.page + 1}").setValue(percent)
                    # getattr(self, f"UpdateProgressBar_{self.page + 1}").setCustomBackgroundColor(QColor(color),QColor(color))

                except AttributeError:
                    pass

    def onUpdateFileCheckBox(self):
        """文件选择 Checkbox是否可用"""

        if self.page == 0:
            try:
                for index in range(self.ParamFileLayOut.count()):
                    item = self.ParamFileLayOut.itemAt(index)
                    if item.widget() is not None:
                        if self.CheckBox_Param.isChecked():
                            item.widget().setDisabled(False)
                        else:
                            item.widget().setDisabled(True)
            except AttributeError:
                log.logger.debug("error: not attribute")

            try:

                for index in range(self.FirmFileLayOut.count()):
                    item = self.FirmFileLayOut.itemAt(index)
                    if item.widget() is not None:
                        if self.CheckBox_Firmware.isChecked():
                            item.widget().setDisabled(False)
                        else:
                            item.widget().setDisabled(True)
            except AttributeError:
                log.logger.debug("error: not attribute")

        else:
            try:

                for index in range(getattr(self, f"ParamFileLayOut_{self.page + 1}").count()):
                    item = getattr(self, f"ParamFileLayOut_{self.page + 1}").itemAt(index)
                    if item.widget() is not None:
                        if getattr(self, f"CheckBox_Param_{self.page + 1}").isChecked():
                            item.widget().setDisabled(False)
                        else:
                            item.widget().setDisabled(True)

                for index in range(getattr(self, f"FirmFileLayOut_{self.page + 1}").count()):
                    item = getattr(self, f"FirmFileLayOut_{self.page + 1}").itemAt(index)
                    if item.widget() is not None:
                        if getattr(self, f"CheckBox_Firmware_{self.page + 1}").isChecked():
                            item.widget().setDisabled(False)
                        else:
                            item.widget().setDisabled(True)

            except AttributeError:
                pass

    def onUpdateButton(self):
        """
        點擊開始升級按鈕
        """
        if self.page == 0:
            if self.ButtonStartOTA.text() == "Stop":
                self.ButtonStartOTA.setText("Software Update")
                self.tabWidget.tabBar().setDisabled(False)
                self.FirmFileName.setDisabled(False)
                self.FirmFileToolButton.setDisabled(False)
                self.StopUpdateSignal.emit()

            else:

                path = self.FirmFileName.text()
                # 判断文件名称是否为空
                if path == "":
                    self.showFlyout("提醒", "请填入文件名称", self.FirmFileName)
                    return
                # 判断文件是否存在
                if not os.path.isfile(path):
                    self.showFlyout("提醒", "文件不存在,请确认后再次尝试", self.FirmFileName)
                    return
                self.updateSignal_Out.emit(path, self.page)
                self.ButtonStartOTA.setText("Stop")
                self.tabWidget.tabBar().setDisabled(True)
        else:
            if getattr(self, f"ButtonStartOTA_{self.page + 1}").text() == "Stop":
                getattr(self, f"ButtonStartOTA_{self.page + 1}").setText("Software Update")
                self.tabWidget.tabBar().setDisabled(False)
                self.StopUpdateSignal.emit()
            else:
                path = getattr(self, f"FirmFileName_{self.page + 1}").text()
                # 判断文件名称是否为空
                if path == "":
                    self.showFlyout("提醒", "请先选择文件", getattr(self, f"FirmFileName_{self.page + 1}"))
                    return
                # 判断文件是否存在
                if not os.path.isfile(path):
                    self.showFlyout("提醒", "文件不存在,请确认后再次尝试",
                                    getattr(self, f"FirmFileName_{self.page + 1}"))
                    return

                self.updateSignal_Out.emit(path, self.page)
                getattr(self, f"ButtonStartOTA_{self.page + 1}").setText("Stop")
                self.tabWidget.tabBar().setDisabled(True)

    def setShadowEffect(self, card: QWidget):
        shadowEffect = QGraphicsDropShadowEffect(self)
        shadowEffect.setColor(QColor(0, 0, 0, 15))
        shadowEffect.setBlurRadius(10)
        shadowEffect.setOffset(0, 0)
        card.setGraphicsEffect(shadowEffect)
