# coding:utf-8
import codecs
import json
import re
import time

import serial
import serial.tools.list_ports
from PyQt5.QtCore import pyqtSignal, QDateTime
from PyQt5.QtGui import QColor, QTextCursor, QTextCharFormat
from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect

import baseUtils
from baseLogger import log
from basePrinter import BasePrinterThread
from baseUart import BaseUartThread
from qfluentwidgets import FluentIcon, MessageBox, Flyout, InfoBarIcon, themeColor
from resources.ui.AuthTestInterface_UI import Ui_AuthTestInterface_UI
from userTest import UserTestThread


def showMessage(title, content, parent=None):
    MessageBox(title, content, parent).show()


class AuthTestInterface(Ui_AuthTestInterface_UI, QWidget):
    # 自定义信号，用来发送测试发送区内容
    testSend_sinOut = pyqtSignal(str)
    # 自定义信号，用来发送输入的硬件唯一标识码
    deviceId_sinOut = pyqtSignal(str)
    # 自定义信号,用来显示授权信息
    authInfo_sinOut = pyqtSignal(str)
    # 自定义信号,用来接收测试配置信息
    testConfigInfo_sinIn = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.Area = None
        self.PID = None

        self.setupUi(self)

        self.regUrl = ''
        # Flag of StartButton
        self.testStart = 0

        # Authkey BLE MAC or IMEI
        self.AuthParam = ''

        # Auth Url
        self.regUrl = ''

        # 808 address
        self.hostAddr = ''

        # 808 port
        self.hostPort = 0

        # Tag Print Times
        self.printerCnt = 1

        # Deivece Type
        self.DeviceType = ''

        # set the icon of button
        self.Button_UpdateSerial.setIcon(FluentIcon.SYNC)
        # self.PrimaryToolButton_playlog.setIcon(FluentIcon.PLAY)

        self.gridLayout.setSpacing(5)
        # add shadow effect to card
        self.setShadowEffect(self.SettingCard)
        self.setShadowEffect(self.progressCard)
        self.setShadowEffect(self.LogViewerCard)

        # 串口刷新设置
        self.refresh()
        # 设置串口
        self.ser = serial.Serial(timeout=0.5)

        # 组件状态初始化
        self.InitModuleConfig()

    # 组件初始化设置
    def InitModuleConfig(self):
        # 待测设备参数

        # 区域选择
        self.AreaComboBox.addItems(['中国(CN)', '美国(US)', '欧洲(EU)'])

        self.success = 0
        self.fail = 0

        # 创建BaseUtils实例
        self.util = baseUtils.BaseUtils()

        # 默认使能配网参数授权
        self.CheckBox_AuthTest.setChecked(True)

        # 默认使能工厂生产测试
        self.CheckBox_FuncTest.setChecked(True)

        # 默认使能打印机
        self.CheckBox_EnablePrinter.setChecked(False)

        # 绑定刷新按键
        self.Button_UpdateSerial.clicked.connect(self.refresh)

        # 绑定开始测试按键
        self.ButtonStartTest.clicked.connect(self.startTest)

        # 初始化进度条
        self.progressTestBar.setStrokeWidth(8)

        # 绑定清除日志按键
        self.Button_Clear.setIcon(FluentIcon.BROOM)
        self.Button_Clear.clicked.connect(self.LogBoswer.clear)

        # 绑定更新设置
        self.testConfigInfo_sinIn.connect(self.updateSetting)

        # Test
        # self.ProuductIdLineEdit.setText('YJ00048odi')

        # 初始化成功率统计接口
        self.SuccessCnt.setText(str(self.success))

        self.FailCnt.setText(str(self.fail))

        self.BodyLabelLinence.hide()
        self.LicenseLineEdit.hide()

    def updateSetting(self):
        # 创建打印机打印次数变量,默认为1,可以通过外部ini文件
        configPath = baseUtils.resource_path('resources\\config\\sysConfig.json')

        with open(configPath, 'r', encoding='utf-8', errors='ignore') as file:
            sysItemsData = json.loads(file.read())
            # 确保sysItemsData是一个字典
            if isinstance(sysItemsData, dict):
                self.printerCnt = sysItemsData.get("tag_print_times", 1)

                # 使用正则表达式匹配以 http 开头的 URL
                url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
                match = re.search(url_pattern, sysItemsData.get("reg_url", 'http://iot-dev.vehiclink.com'))
                self.regUrl = match.group()
                self.AuthParam = sysItemsData.get("current_auth_param", "MAC")
                self.hostAddr = sysItemsData.get("host", 'tracker.us.navixy.com')
                self.hostPort = int(sysItemsData.get("port", '47694'))
                self.DeviceType = sysItemsData.get("current_device_type", "BLE")

    def setProcessBarColor(self, value: int, color: str):
        """设置进度条"""
        self.progressTestBar.setColor(color)
        if self.progressTestBar.maximum() < value:
            self.progressTestBar.setVal(self.progressTestBar.maximum())
        else:
            self.progressTestBar.setVal(value)

    # 测试项设置状态变更
    def testSetStateChange(self, bool_value):
        # 串口号选择-禁止/使能
        self.ComboBox_Serial.setDisabled(bool_value)
        # 串口刷新按钮
        self.Button_UpdateSerial.setDisabled(bool_value)
        # PID输入-禁止/使能
        self.ProuductIdLineEdit.setDisabled(bool_value)
        # License 输入-禁止/使能
        self.LicenseLineEdit.setDisabled(bool_value)
        # 区域选择-禁止/使能
        self.AreaComboBox.setDisabled(bool_value)
        # 配网参数授权-禁止/使能
        self.CheckBox_AuthTest.setDisabled(bool_value)
        # 生产测试-禁止/使能
        self.CheckBox_FuncTest.setDisabled(bool_value)
        # 打印机-禁止/使能
        self.CheckBox_EnablePrinter.setDisabled(bool_value)
        self.progressTestBar.setVal(0)
        self.processTestText.setText('等待开始')
        # 开始/停止按钮-状态切换
        if bool_value:
            self.ButtonStartTest.setText("停止")
        else:
            self.ButtonStartTest.setText("开始")

    def showFlyout(self, title, content, Widget_object):
        Flyout.create(
            icon=InfoBarIcon.ERROR,
            title=title,
            content=content,
            target=Widget_object,
            parent=self,
            isClosable=True
        )

    def initialSerial(self, baudrate):
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

        # self.ser.port = self.ComboBox_Serial.currentText()
        self.ser.baudrate = baudrate
        self.ser.bytesize = 8
        self.ser.stopbits = 1
        self.ser.parity = 'N'

    # 重写关闭窗口事件
    def closeEvent(self, event):
        if self.ser.isOpen():
            self.serialThread.quit()
            self.testThread.quit()
            self.printerThread.quit()

    def enableLogPrint(self):
        try:  # 如果之前已建立连接，先断开，防止重复连接
            # self.testSend_sinOut.disconnect()
            self.LogBoswer.hide()
        except:
            pass

        if self.LogSwitchButton.isChecked() and self.button.isHidden():
            # self.testSend_sinOut.connect(self.serialThread.uartWrite)
            self.LogBoswer.show()

    def startTest(self):
        if self.CheckBox_AuthTest.isChecked() or self.CheckBox_FuncTest.isChecked():
            if not self.testStart:

                # 载入设置
                self.updateSetting()

                self.initialSerial(921600)
                # 获取PID
                self.PID = self.ProuductIdLineEdit.text()
                # 获取区域
                self.Area = self.AreaComboBox.currentText()

                # 检查PID输入是否为10字节
                if len(self.PID) == 10:
                    # 检查PID前两个字节是否为"YJ"
                    if self.PID[0:2] == "YJ":
                        # 尝试打开串口，并建立串口线程、授权线程、测试线程
                        try:
                            self.ser.open()  # 打开串口有可能失败，做try-except异常处理
                            # 发送复位命令
                            data = "66AABB000000CB"
                            tmp = codecs.decode(data, "hex_codec")

                            # 发送重启指令 不用回复
                            while not self.ser.isOpen():
                                pass

                            for i in range(3):
                                self.ser.write(tmp)
                                # 等待
                                time.sleep(0.1)

                            self.initialSerial(115200)

                        except Exception as e:
                            print(str(e));
                            self.testStart = False
                            showMessage("提示", "当前无串口或者串口被占用", self)
                            return None

                        else:
                            self.testSetStateChange(True)
                            # 测试开始标志位置位
                            self.testStart = True
                            # 清空通讯交互区窗口
                            self.LogBoswer.clear()
                            # 清空授权结果区窗口
                            self.AuthRES_TextEdit.clear()

                            ###############################################################################
                            # 创建BaseUartThread线程实例,
                            self.serialThread = BaseUartThread(self.ser)
                            # 自定义信号与槽连接，处理串口接受数据，由BaseUartThread线程发送到main主线程
                            self.serialThread.revData_sinOut.connect(self.dealRevData)

                            # 自定义信号与槽连接，用于发送测试发送区内容，由主线程发送到BaseUartThread线程
                            try:  # 如果之前已建立连接，先断开，防止重复连接
                                self.testSend_sinOut.disconnect()
                            except:
                                pass
                            self.testSend_sinOut.connect(self.serialThread.uartWrite)
                            # 启动BaseUartThread线程
                            self.serialThread.start()

                            ###############################################################################
                            # 创建UserTestThread线程实例
                            try:
                                if self.DeviceType == '4G':
                                    self.testThread = UserTestThread(self.ser, self.PID,
                                                                     self.CheckBox_AuthTest.isChecked(),
                                                                     self.Area,
                                                                     self.AuthParam,
                                                                     self.DeviceType,
                                                                     self.CheckBox_FuncTest.isChecked(),
                                                                     self.regUrl,
                                                                     self.hostAddr,
                                                                     self.hostPort)
                                else:
                                    self.testThread = UserTestThread(self.ser, self.PID,
                                                                     self.CheckBox_AuthTest.isChecked(),
                                                                     self.Area,
                                                                     self.AuthParam,
                                                                     self.DeviceType,
                                                                     self.CheckBox_FuncTest.isChecked(),
                                                                     self.regUrl)
                            except Exception as e:
                                self.testStart = False
                                self.testSetStateChange(False)
                                self.ser.close()
                                showMessage("提示", "测试线程创建失败,请检查配置文件", self)
                                return None

                            # 自定义信号与槽连接，写串口数据，由UserTestThread线程发送到BaseUartThread线程
                            self.testThread.uartWrite_sinOut.connect(self.serialThread.uartWrite)
                            # 自定义信号与槽连接，写串口数据，由UserTestThread线程发送到main主线程线程
                            self.testThread.uartWrite_sinOut.connect(self.dealSendData)
                            # 自定义信号与槽连接，接受串口接受数据，由BaseUartThread线程发送到UserTestThread线程
                            self.serialThread.revData_sinOut.connect(self.testThread.uartProc)
                            # 自定义信号与槽连接，进度条数据，由UserTestThread线程发送到main主线程线程
                            self.testThread.progressBar_sinOut.connect(self.dealProgressBar)
                            # 自定义信号与槽连接，完整授权信息，由UserTestThread线程发送到main主线程
                            self.testThread.authInfo_sinOut.connect(self.dealAuthData)

                            # 启动UserTestThread线程
                            self.testThread.start()

                            # 判断打印机是否使能
                            if self.CheckBox_EnablePrinter.isChecked():
                                log.logger.info("打印机初始化中，请稍等...")
                                # 如果使能，创建打印机线程
                                self.printerThread = BasePrinterThread(self.ser, self.printerCnt)
                                # 自定义信号与槽连接，打印信息及授权信息传递，由UserTestThread线程发送到BasePrinterThread线程
                                self.testThread.printMsg_sinOut.connect(self.printerThread.insertMsg)

                                # 启动BasePrinterThread线程
                                self.printerThread.start()
                                # log.logger.info("打印机初始化成功！")
                    else:
                        self.testStart = False
                        showMessage('提示', 'PID错误：非YJ开头', self)
                        return None
                else:
                    self.testStart = False
                    showMessage('提示', 'PID错误：PID为空或者长度错误', self)
                    return None
            else:  # 停止授权，测试
                self.testStart = False
                try:
                    self.ser.close()  # 关闭串口有可能失败，做try-except异常处理
                except ValueError:
                    showMessage(self, '提示', '关闭串口失败', self)
                    return None

                self.testSetStateChange(False)
                print('Test stop!')
        else:
            self.showFlyout("提示", "上述两种测试至少选择一种", self.ButtonStartTest)

    # 自定义槽，处理串口接受数据
    def dealRevData(self, xStr):
        # 判断输入xStr是否有效
        if not xStr:
            return None
        # print("main", "dealRevData", xStr, len(xStr))
        # 发送到通讯交互区进行显示
        if self.LogSwitchButton.isChecked():
            self.dispContent("receive", xStr)

    # 自定义槽，处理串口发送数据
    def dealSendData(self, xStr):
        # 判断输入xStr是否有效
        if not xStr:
            return None

        # print("main", "dealSendData", xStr, len(xStr))
        # 发送到通讯交互区进行显示
        if self.LogSwitchButton.isChecked():
            self.dispContent("write", xStr)

    def refresh(self):
        """刷新串口"""

        # 查询可用的串口
        plist = serial.tools.list_ports.comports()

        if len(plist) <= 0:
            print("No used com!")
            # 清空comboBox内容
            self.ComboBox_Serial.clear()
            showMessage("提示", "当前无串口或者串口被占用", self)

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

        # 作为槽函数于Stream的信号连接, 内部参数于信号发射参数相同

    def onLoggingChanged(self, text):
        # print("main.write", text)
        cursor = self.LogBoswer.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.LogBoswer.setTextCursor(cursor)
        self.LogBoswer.ensureCursorVisible()

    # 更新时间
    def updateTime(self):
        # 获取现在的时间
        self.time = QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss dddd')

    def updatePassDate(self):
        self.SuccessCnt.setText(str(self.success))
        self.FailCnt.setText(str(self.fail))
        try:
            self.PassPrecents.setText(str('%.1f' % float(self.success / (self.success + self.fail) * 100)) + '%')
        except ZeroDivisionError:
            self.PassPrecents.setText('0%')

    def dealProgressBar(self, xInt, state, DescribeStr):
        """自定义槽，处理测试进度条数据"""
        if state:
            # 如果是正常状态，更新进度
            self.setProcessBarColor(xInt, themeColor())
            if xInt == 100:
                self.success += 1
                self.setProcessBarColor(xInt, "green")

        else:
            self.fail += 1
            self.setProcessBarColor(self.progressTestBar.getVal(), "red")

        self.processTestText.setText(DescribeStr)
        self.updatePassDate()

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

    def dispContent(self, sourceObject, argvStr):
        """接受输入的硬件唯一标识码，并做自定义信号发送
          显示收发数据"""
        # 获取现在的时间
        time = QDateTime.currentDateTime()
        timeplay = time.toString('[hh:mm:ss.zzz]')
        # 获取光标位置
        cursor = self.LogBoswer.textCursor()
        # 创建字体格式
        char_format = QTextCharFormat()

        if sourceObject == "receive":  # 串口接受数据显示
            argvStrHead = "PC收:"
            # 设置字体颜色为橙色
            char_format.setForeground(QColor("#f28e2b"))

        elif sourceObject == "write":  # 串口发送数据显示
            argvStrHead = "PC发:"
            # # 设置字体颜色为蓝色
            char_format.setForeground(QColor("#4e79a7"))

        else:
            print("revData_display error")
            return

        argvStr = self.util.byteToHexString(self.util.HexStringToByte(argvStr))

        # 设置字符格式
        cursor.setCharFormat(char_format)

        # 追加显示通讯数据
        cursor.insertText(timeplay + argvStrHead + argvStr + '\n')
        # 移动光标到底部
        self.LogBoswer.moveCursor(self.LogBoswer.textCursor().End)

    """
    def InputDeviceId(self):
        # 必须是测试中，才处理
        if self.testStart:

            text = self.AuthParam

            # 如果是‘BLE MAC’，长度必须是12个字符串
            if self.ComboBox_AuthParam.currentText() == 'BLE MAC':
                if len(text) == 12:
                    log.logger.debug('BLE MAC：' + text)
                    # 发射自定义信号
                    self.deviceId_sinOut.emit(text)
                else:  # 如果不符合BLE MAC地址长度，则提示
                    showMessage("警告", "BLE MAC地址格式错误!", self.nativeParentWidget())
            else:
                if len(text) == 15 or len(text) == 17:
                    log.logger.info('4G IMEI：' + text)
                    # 发射自定义信号
                    self.deviceId_sinOut.emit(text)
                else:  # 如果不符合BLE MAC地址长度，则提示
                    showMessage("警告", "4G IMEI地址格式错误!", self.nativeParentWidget())
    
    """

    def setShadowEffect(self, card: QWidget):
        shadowEffect = QGraphicsDropShadowEffect(self)
        shadowEffect.setColor(QColor(0, 0, 0, 15))
        shadowEffect.setBlurRadius(10)
        shadowEffect.setOffset(0, 0)
        card.setGraphicsEffect(shadowEffect)
