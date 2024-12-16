import codecs
import json
import time
import traceback
from enum import Enum

import requests
from PyQt5.QtCore import QThread, QDateTime, Qt, pyqtSignal

import baseUtils
from baseLogger import log


# 测试状态
class testStatus(Enum):
    S_ENTER = 0  # 进入测试
    S_GET_PRODINFO = 1  # 获取产品信息
    S_GET_DEV_SN = 2  # 获取设备唯一标识信息
    S_AUTH_LOAD = 3  # 烧录授权
    S_AUTH_QUERY = 4  # 查询授权
    S_TEST = 5  # 测试
    S_END = 6  # 结束测试


# 测试模型
class ItemTestModel:
    def __init__(self, funcName, dspName, cmd, data: str, rev_dict: dict, interval: int, retry: int):
        # 测试参数
        self.funcName = funcName  # 测试函数名称
        self.dspName = dspName  # 测试名称
        self.cmd = cmd  # 测试命令
        self.data = data  # 测试数据
        self.interval = interval  # 测试间隔
        self.retry = retry  # 重试次数

        # 测试结果
        self.result = False  # 用于记录测试结果
        self.rev_dict = rev_dict  # 测试返回数据
        self.testTime = ''  # 用于记录测试时间

    def getTestResult(self):
        return self.result


class UserTestThread(QThread):
    # 自定义信号，用来发送串口write数据
    uartWrite_sinOut = pyqtSignal(str)
    # 自定义信号，用来发送打印信息及授权信息
    printMsg_sinOut = pyqtSignal(str, str, str, str)
    # 自定义信号，用来界面显示完整的授权信息
    authInfo_sinOut = pyqtSignal(str)
    # 自定义信号，用来发送进度条数据及进度描述
    progressBar_sinOut = pyqtSignal(int, bool, str)

    # 自定义信号，用来发送测试退出
    testExit_sinOut = pyqtSignal()

    def __init__(self, Ser, PID, Auth, Area, AuthParam, DevType, FactoryTest, regUrl, hostAddr='', hostPort=''):
        super(UserTestThread, self).__init__()
        # 创建BaseUtils实例
        self.util = baseUtils.BaseUtils()
        self.AuthTestFlag = False
        # 接受主函数传递的参数
        self.Ser = Ser
        self.PID = PID
        self.hostAddr = hostAddr
        self.hostPort = hostPort
        self.Auth = Auth
        self.Area = Area
        self.AuthParam = AuthParam
        self.FactoryTest = FactoryTest
        self.regUrl = regUrl
        # 创建设备类型
        self.deviceType = DevType  # 设备类型
        # 创建串口读到的数据缓冲区
        self.readBuf = ''
        # 创建硬件唯一标识码，BLE MAC/4G IMEI
        self.nodeId = ''
        # 创建设备注册接口token
        self.tokenText = ''
        # 创建设备deviceIotId
        self.deviceIotId = ''
        # 创建设备密钥
        self.deviceSecret = ''
        # 创建小型状态机，主状态
        self.stateMachine = testStatus.S_ENTER
        # 创建小型状态机，子状态
        self.stateMachineSub = ''

        # 定义发送互斥标志位，除了FF00是循环发送查询，其他指令只发一次，返回错误或者超时，直接判错，True可以发送，False不能发送
        self.sendMutexFlag = True
        # 创建 test 项成员表
        self.testProcessor = []
        # 创建 命令 成员表
        self.cmdProcessor = []
        # 创建测试项索引
        self.testIndex = 0
        # 测试命令数量,从文件中进行读取
        self.TestItemsNum = 0

        # 授权命令数量,授权相关命令不通过文件配置 包含:设备产品信息查询，设备唯一标识查询，烧录授权命令，查询授权命令
        self.AuthItemsNum = 4

        # 当前授权通过命令数量
        self.CurrentPassItemsNum = 0

        # 授权测试开始时间戳
        self.startStamp = 0
        # 授权测试结束时间戳
        self.endStamp = 0
        # 测试时间间隔
        self.testInterval = 0
        # 测试重试次数
        self.retryCnt = 0

        # ICCID信息
        self.ICCID = ''
        # IMEI信息
        self.IMEI = ''

        # GPS有用星数
        self.gpsUStarNum = 0

        # csv记录列表
        self.regInfoDict = {}

        # 创建顺序状态机列表
        self.stateList = []
        # 创建列表索引
        self.listIndex = 0

        # 创建测试协议cmd字典
        self.cmdInsideProcessor = {
            bytes.fromhex("FF00"): self.cmd_FF00,
            bytes.fromhex("FF01"): self.cmd_FF01,
            bytes.fromhex("AA00"): self.cmd_AA00,
            bytes.fromhex("AA01"): self.cmd_AA01,
            bytes.fromhex("AA02"): self.cmd_AA02,
            bytes.fromhex("AA03"): self.cmd_AA03,
            bytes.fromhex("AA04"): self.cmd_AA04,
            bytes.fromhex("AA05"): self.cmd_AA05,
            bytes.fromhex("AA06"): self.cmd_AA06,
        }

        if self.FactoryTest:
            try:
                self._init_param_from_json()

            except Exception as e:
                print(f"初始化失败: {e}")
                self = None
                raise  # 重新抛出异常，这样调用者就可以捕获并处理它
        print("创建UserTestThread线程")

    # 从json 子结构创建测试项
    def _init_obj_json(self, jsondate):
        TestItems = jsondate.get("TestItems", [])
        for item in TestItems:
            funcName = item.get("funName", "")
            name = item.get("dspName", "")
            cmd = item.get("cmd", "")
            state = item.get("enable", False)
            data = item.get("data", "")
            rev_str = item.get("rev_dict", "")
            rev_dict = {}
            if rev_str != '':
                rev_dict = json.loads(rev_str)

            interval = item.get("interval(ms)", 0)
            process = item.get("process", "")
            retry = item.get("retry", 0)

            if state and funcName != '' and name != '' and cmd != '' and interval != 0 and process != '':
                if process == "ALL" or (self.deviceType == '4G' and process == "4G"):
                    testCell = ItemTestModel(funcName, name, cmd, data, rev_dict, interval, retry)
                    self.testProcessor.append(testCell)
                    self.cmdProcessor.append(bytes.fromhex(cmd))

        # 测试命令数量
        self.TestItemsNum = len(self.testProcessor)

    # 从json加载配置
    def _init_param_from_json(self):
        configPath = baseUtils.resource_path("resources\\config\\userConfig.json")
        with open(configPath, 'r', encoding='utf-8', errors='ignore') as file:
            jsonData = json.load(file)
            if isinstance(jsonData, dict):
                self._init_obj_json(jsonData)
            else:
                print("userConfig.json is not a dictionary.")
                return False

    # 计算测试进度
    def testPercentCal(self):
        # 总测试项目包含开始测试命令
        if self.FactoryTest and self.Auth:
            ret = int((self.CurrentPassItemsNum * 100) / (self.TestItemsNum + self.AuthItemsNum + 1))
        elif self.FactoryTest:
            ret = int(self.CurrentPassItemsNum * 100 / (self.TestItemsNum + 1))
        else:
            ret = int(self.CurrentPassItemsNum * 100 / (self.AuthItemsNum + 1))

        if ret == 100:
            self.AuthTestFlag = True

        return ret

    # 发送测试指令
    def userTestSend(self, testCmd: str, testLen: int, testData=''):
        # 发送数据组包
        lenStr = testLen.to_bytes(2, byteorder='big', signed=False).hex()
        dataTmp = "66AA" + testCmd + str(lenStr) + testData
        # print("userTestSend", dataTmp, type(dataTmp))
        tmp = self.util.uchar_checksum(dataTmp)
        dataTmp = dataTmp + tmp
        # 发送串口写信号
        self.uartWrite_sinOut.emit(dataTmp)

    # 解析进入产测模式指令FF00
    def cmd_FF00(self, hexx):
        # print("userTest.cmd_FF00", hexx)
        log.logger.debug("cmd_FF00接受数据：%s" % hexx)

        # 如果在'state_enterTest'状态
        if self.stateMachine == testStatus.S_ENTER:
            self.CurrentPassItemsNum = 0

            # b"example"  --->  "example",转换成字符串
            authtmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            try:
                authtmp = json.loads(authtmp_str)
            except Exception as e:
                log.logger.error('[userTest]FF00返回json异常，%s' % e)
                return

            if authtmp.get('ret', False):
                # 进入产测模式成功
                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('待测设备已接入!')

                # 通过项目计数
                self.CurrentPassItemsNum += 1
                self.progressBar_sinOut.emit(self.testPercentCal(), True, "待测设备已接入")
                # 清零周期次数变量
                self.retryCnt = 0

                # 初始化授权与测试信息
                self.nodeId = ''
                self.deviceIotId = ''
                self.deviceSecret = ''
                self.ICCID = ''
                self.IMEI = ''

                # 获取开始时间戳
                self.startStamp = time.time()

            else:
                # 进入产测模式失败
                self.listIndex = 0
                self.stateMachine = self.stateList[self.listIndex]
                self.progressBar_sinOut.emit(self.testPercentCal(), False, "进入产测失败")
                log.logger.info('进入产测失败!')

            # 初始化发送互斥标志位
            self.sendMutexFlag = True
        else:
            log.logger.debug('FF00错误应答，未在对应状态！')

        # # 等待1s
        # time.sleep(1)

    # 解析退出产测模式指令FF01
    def cmd_FF01(self, hexx):
        # print("userTest.cmd_FF01", hexx)
        log.logger.debug("cmd_FF01接受数据：%s" % hexx)

        # 如果在'state_quitTest'状态
        if self.stateMachine == testStatus.S_END:
            # b"example"  --->  "example",转换成字符串
            authtmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            try:
                authtmp = json.loads(authtmp_str)
            except Exception as e:
                log.logger.error('[userTest]FF01 返回结果json异常，%s' % e)
                return

            if authtmp.get('ret', False):
                # 退出产测模式成功
                self.listIndex = 0
                self.stateMachine = self.stateList[self.listIndex]

                log.logger.info('待测设备退出产测模式!')

                # 获取结束时间戳
                self.endStamp = time.time()
                # self.testInterval = self.endStamp - self.startStamp
                self.testInterval = '{:.2f}'.format(self.endStamp - self.startStamp)

                # log.logger.info("本次耗费时间(秒)：%.02f", self.testInterval)
                log.logger.info("本次耗费时间(秒)：%s", self.testInterval)

                # 记录授权信息
                now = QDateTime.currentDateTime()
                self.regInfoDict['TIME'] = now.toString(Qt.ISODate)
                self.regInfoDict['PID'] = self.PID
                self.regInfoDict['AREA'] = self.Area
                self.regInfoDict['DID'] = self.deviceIotId
                if self.AuthTestFlag:
                    self.regInfoDict['RESULT'] = 'PASS'
                else:
                    self.regInfoDict['RESULT'] = 'FAIL'

                if self.deviceType == "BLE":
                    self.regInfoDict['MAC'] = self.nodeId
                    text = ('regInfo:\r\n' + 'IoTID:' + self.deviceIotId + '\r\n' +
                            'AREA:' + self.Area + '\r\n' +
                            'MAC:' + self.nodeId + '\r\n')
                elif self.deviceType == "BLE&4G":
                    self.regInfoDict['MAC'] = self.nodeId
                    self.regInfoDict['DSECRET'] = self.deviceSecret
                    self.regInfoDict['IMEI'] = self.IMEI
                    self.regInfoDict['ICCID'] = self.ICCID
                    text = ('regInfo:\r\n' + 'IoTID:' + self.deviceIotId + '\r\n' +
                            'AREA:' + self.Area + '\r\n' +
                            'MAC:' + self.nodeId + '\r\n' +
                            'DSECRET:' + str(self.deviceSecret) + '\r\n' +
                            'IMEI:' + str(self.IMEI) + '\r\n' +
                            'ICCID:' + str(self.ICCID) + '\r\n')
                else:
                    self.regInfoDict['IMEI'] = self.IMEI
                    self.regInfoDict['ICCID'] = self.ICCID
                    self.regInfoDict['HOST'] = self.hostAddr
                    self.regInfoDict['PORT'] = self.hostPort
                    text = ('regInfo:\r\n' + 'IoTID:' + self.deviceIotId + '\r\n' +
                            'AREA:' + self.Area + '\r\n' +
                            'HOSTADDR:' + self.hostAddr + '\r\n' +
                            'HOSTPORT:' + str(self.hostPort) + '\r\n' +
                            'IMEI:' + self.IMEI + '\r\n' +
                            'ICCID:' + str(self.ICCID) + '\r\n')



                filedsName = []
                # 记录测试结果
                if self.FactoryTest:
                    for item in self.testProcessor:
                        self.regInfoDict[item.dspName] = item.result
                        if item.rev_dict != {}:
                            for key, value in item.rev_dict.items():
                                self.regInfoDict[key] = value

                self.regInfoDict['TIME_CONS(s)'] = self.testInterval

                for key, value in self.regInfoDict.items():
                    filedsName.append(key)

                try:
                    self.util.addToRegList(self.regInfoDict, filedsName,self.deviceType != "BLE")
                except Exception as e:
                    log.logger.error('[userTest]addToRegList异常，%s' % e)

                log.logger.info('**************************************************')

                # 发送打印标签及授权信息
                if self.AuthTestFlag:
                    # 发送完整的授权信息
                    self.authInfo_sinOut.emit(text)

                    if self.deviceType == "BLE" or self.deviceType == "BLE&4G":
                        self.printMsg_sinOut.emit(self.nodeId, self.Area, self.deviceIotId, self.PID)
                    else:
                        self.printMsg_sinOut.emit(self.IMEI, self.Area, self.deviceIotId, self.PID)

                # 清零周期次数变量
                self.retryCnt = 0
                # 初始化发送互斥标志位
                self.sendMutexFlag = True

                # 产测完成退出
                self.testExit_sinOut.emit()
                # 等待设备退出
                time.sleep(0.2)

        else:
            log.logger.warning('FF01错误应答，未在对应状态！')


    def cmd_AA00(self, hexx):
        log.logger.debug("cmd_AA00接受数据：%s" % hexx)

        # 如果在 S_GET_PRODINFO 状态
        if self.stateMachine == testStatus.S_GET_PRODINFO:

            tmp = ''
            # b"example"  --->  "example",转换成字符串
            tmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            try:
                tmp = json.loads(tmp_str)
            except Exception as e:
                log.logger.error('[userTest]返回结果json异常，%s' % e)

            if tmp.get('productId', '') != self.PID:
                # 查询设备产品信息不成功，请重试
                self.listIndex = -1
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('查询设备产品信息PID出错！')

                # 发送进度条信息
                self.progressBar_sinOut.emit(self.testPercentCal(), False, "查询设备产品信息PID与配置不符")
                # 清零周期次数变量
                self.retryCnt = 0
                return

            if tmp.get('devType', '') != self.deviceType:
                self.listIndex = -1
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('设备类型和配置不符！')

                # 发送进度条信息
                self.progressBar_sinOut.emit(self.testPercentCal(), False, "查询设备类型与配置不符")
                # 清零周期次数变量
                self.retryCnt = 0
                return

            self.listIndex = self.listIndex + 1
            self.stateMachine = self.stateList[self.listIndex]
            # 通过项目计数
            self.CurrentPassItemsNum += 1
            self.progressBar_sinOut.emit(self.testPercentCal(), True, "查询产品信息完成")

            # 清零周期次数变量
            self.retryCnt = 0
            # 初始化发送互斥标志位
            self.sendMutexFlag = True

        else:
            log.logger.warning('AA02错误应答，未在对应状态！')

    def cmd_AA01(self, hexx):
        # print("userTest.cmd_AA02", hexx)
        log.logger.debug("cmd_AA01接受数据：%s" % hexx)

        # 如果在 S_GET_PRODINFO 状态
        if self.stateMachine == testStatus.S_GET_DEV_SN:

            tmp = ''
            # b"example"  --->  "example",转换成字符串
            tmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            try:
                tmp = json.loads(tmp_str)
            except Exception as e:
                log.logger.error('[userTest]返回结果json异常，%s' % e)

            if len(tmp.get('MAC', '')) == 12:
                self.nodeId = tmp.get('MAC')
                log.logger.info("已查询nodeId:" + self.nodeId)

                if self.dealHttpDeviceAuth(self.nodeId):
                    self.listIndex = self.listIndex + 1
                    self.stateMachine = self.stateList[self.listIndex]
                    log.logger.info('设备唯一码查询成功！')

                    # 发送进度条信息
                    self.CurrentPassItemsNum += 1
                    self.progressBar_sinOut.emit(self.testPercentCal(), True, "设备唯一码查询成功")

                else:
                    log.logger.info('设备MAC查询出错！')
                    # 发送进度条信息
                    self.progressBar_sinOut.emit(self.testPercentCal(), False, "设备MAC查询出错")

            else:
                # 查询MAC失败，请重试
                log.logger.error('查询MAC长度异常')

            # 初始化发送互斥标志位
            self.retryCnt = 0
            self.sendMutexFlag = True

        else:
            log.logger.warning('AA01错误应答，未在对应状态！')

    def cmd_AA02(self, hexx):
        log.logger.debug("cmd_AA02接受数据：%s" % hexx)

        # 如果在 S_GET_DEV_SN 状态
        if self.stateMachine == testStatus.S_GET_DEV_SN or self.deviceType == "BLE&4G":

            tmp = ''
            # b"example"  --->  "example",转换成字符串
            tmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            try:
                tmp = json.loads(tmp_str)
            except Exception as e:
                log.logger.error('[userTest]返回结果json异常，%s' % e)

            if len(tmp.get('iccid', '')) > 0 and len(tmp.get('IMEI', '')) > 0:

                self.IMEI = str(tmp['IMEI']) + '\t'
                self.ICCID = str(tmp['iccid']) + '\t'

                if self.deviceType == "4G":
                    self.listIndex = self.listIndex + 1
                    self.stateMachine = self.stateList[self.listIndex]
                    # 通过项目计数
                    self.CurrentPassItemsNum += 1
                    self.progressBar_sinOut.emit(self.testPercentCal(), True, "查询设备蜂窝信息正确")
                    log.logger.info('查询设备蜂窝信息正确！')

                else:
                    log.logger.info('仅查询设备IMEI和ICCID 为记录')
                # 重试次数清零
                self.retryCnt = 0

            else:
                if self.deviceType == "4G":
                    self.retryCnt = self.retryCnt + 1
                log.logger.debug('查询设备蜂窝信息失败')

            # 初始化发送互斥标志位
            self.sendMutexFlag = True

        else:
            log.logger.warning('AA02错误应答，未在对应状态！')

    # 解析设备入网信息烧录AA03
    def cmd_AA03(self, hexx):
        log.logger.debug("cmd_AA03接受数据：%s" % hexx)

        # 如果在'S_AUTH_LOAD'状态
        if self.stateMachine == testStatus.S_AUTH_LOAD:

            tmp = ''
            # b"example"  --->  "example",转换成字符串
            tmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            try:
                tmp = json.loads(tmp_str)
            except Exception as e:
                log.logger.error('[userTest]返回结果json异常，%s' % e)

            if tmp.get('ret', False):
                # 授权信息烧录成功
                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('设备授权信息烧录完毕！')

                # 发送进度条信息
                self.CurrentPassItemsNum += 1
                self.progressBar_sinOut.emit(self.testPercentCal(), True, "设备授权烧录成功")
                self.retryCnt = 0
            else:
                # 授权信息烧录不成功，请重试
                log.logger.info('设备授权信息烧录出错！')

            # 初始化发送互斥标志位
            self.sendMutexFlag = True
        else:
            log.logger.warning('AA00错误应答，未在对应状态！')

    # 解析入网信息查询指令AA04
    def cmd_AA04(self, hexx):
        log.logger.debug("cmd_AA04接受数据：%s" % hexx)

        # 如果在'state_authQuery'状态
        if self.stateMachine == testStatus.S_AUTH_QUERY:

            tmp = ''
            # b"example"  --->  "example",转换成字符串
            tmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            try:
                tmp = json.loads(tmp_str)
            except Exception as e:
                log.logger.error('[userTest]返回结果json异常，%s' % e)

            if tmp.get('deviceIotId', '') == self.deviceIotId and tmp.get('deviceSecret', '') == self.deviceSecret:
                # 查询设备烧录授权信息正确
                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('查询待测设备烧录的授权信息正确！')

                # 发送进度条信息
                self.CurrentPassItemsNum += 1
                self.progressBar_sinOut.emit(self.testPercentCal(), True, '授权信息查询成功')
                # 清零周期次数变量
                self.retryCnt = 0
            else:
                # 查询设备烧录授权信息不正确
                log.logger.error('查询设备烧录授权信息不正确!')

            # 初始化发送互斥标志位
            self.sendMutexFlag = True
        else:
            log.logger.warning('AA01错误应答，未在对应状态！')

    # 解析设备蓝牙信息查询 AA01
    def cmd_AA05(self, hexx):
        log.logger.debug("cmd_AA05接受数据：%s" % hexx)

        # 如果在 S_AUTH_LOAD 状态
        if self.stateMachine == testStatus.S_AUTH_LOAD:
            tmp = ''
            try:
                # b"example"  --->  "example",转换成字符串
                tmp_str = self.util.BytesToStr(hexx)
                # 加载成json格式
                tmp = json.loads(tmp_str)
            except Exception as e:
                log.logger.error('[userTest]返回结果json异常，%s' % e)
                return

            if tmp.get('ret', False):
                # 授权信息烧录成功
                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('设备授权信息烧录成功！')

                # 发送进度条信息
                self.CurrentPassItemsNum += 1
                self.progressBar_sinOut.emit(self.testPercentCal(), True, "设备授权信息烧录成功")
                # 清零周期次数变量
                self.retryCnt = 0
            else:
                log.logger.info('LET待测设备授权信息烧录失败！')

            # 初始化发送互斥标志位
            self.sendMutexFlag = True

        else:
            log.logger.warning('AA05错误应答，未在对应状态！')

    # 解析授权查询指令AA03
    def cmd_AA06(self, hexx):
        log.logger.debug("cmd_AA06接受数据：%s" % hexx)

        # 如果在'S_AUTH_QUERY'状态
        if self.stateMachine == testStatus.S_AUTH_QUERY:

            tmp = ''
            # b"example"  --->  "example",转换成字符串
            tmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            try:
                tmp = json.loads(tmp_str)
            except Exception as e:
                log.logger.error('[userTest]返回结果json异常，%s' % e)

            if (tmp.get('deviceIotId', "") == self.deviceIotId and tmp.get('hostAddr', '') == self.hostAddr and
                    tmp.get('hostPort', "") == self.hostPort):
                # 查询设备烧录授权信息正确
                self.deviceIotId = tmp.get('deviceIotId') + '\t'
                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('查询LET待测设备烧录的授权信息正确！')
                # 清零周期次数变量
                self.retryCnt = 0
                # 发送进度条信息
                self.CurrentPassItemsNum += 1
                self.progressBar_sinOut.emit(self.testPercentCal(), True, "查询LET待测设备烧录的授权信息正确")
            else:
                # 查询设备烧录授权信息不正确
                log.logger.error('查询LET设备烧录授权信息不正确!')

            # 初始化发送互斥标志位
            self.sendMutexFlag = True
        else:
            log.logger.warning('AA06错误应答，未在对应状态！')

    # 解析用户测试指令
    def cmd_testItem(self, cmd, hexx):
        strcmd = cmd.hex()
        log.logger.debug(f"cmd {strcmd} 接受数据：{hexx}")

        # 如果在测试项状态 并且 回复命令等于当前测试命令
        if self.stateMachine == testStatus.S_TEST and strcmd == self.testProcessor[self.testIndex].cmd:

            tmp = ''
            # b"example"  --->  "example",转换成字符串
            tmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            try:
                tmp = json.loads(tmp_str)
            except Exception as e:
                log.logger.error('[userTest]返回结果json异常，%s' % e)

            name = self.testProcessor[self.testIndex].dspName
            rev_dict = self.testProcessor[self.testIndex].rev_dict
            index = self.testIndex
            try:
                if tmp.get('ret', False):
                    # 设备返回成功
                    log.logger.info('测试[%s]成功！' % name)

                    # 记录测试结果
                    self.testProcessor[index].result = True

                    if rev_dict != {}:
                        try:
                            for key in rev_dict.keys():
                                ret = tmp.get(key, '')
                                self.testProcessor[index].rev_dict[key] = ret
                        except Exception:
                            # 设备返回失败
                            self.listIndex = -1
                            self.stateMachine = self.stateList[self.listIndex]
                            log.logger.info('[%s]命令字段返回异常！' % name)
                            self.progressBar_sinOut.emit(self.testPercentCal(), False, "[%s]命令字段返回异常" % name)
                            # 重试次数清零
                            self.retryCnt = 0
                            # 初始化发送互斥标志位
                            self.sendMutexFlag = True
                            return

                    self.testIndex += 1
                    if self.testIndex == self.TestItemsNum:
                        # 测试全部结束
                        self.listIndex += 1
                        self.stateMachine = self.stateList[self.listIndex]
                        log.logger.info('测试全部结束，测试成功')

                    # 清零周期次数变量
                    self.retryCnt = 0

                    # 发送进度条信息
                    self.CurrentPassItemsNum += 1
                    self.progressBar_sinOut.emit(self.testPercentCal(), True, "[%s]成功" % name)

                else:
                    # 设备返回失败
                    log.logger.info('测试[%s]出错！' % name)

            except AttributeError:
                # 设备返回失败
                log.logger.info('[%s]命令字段返回异常！' % name)

            # 初始化发送互斥标志位
            self.sendMutexFlag = True

        else:
            log.logger.warning('cmd %s 错误应答，未在对应状态！' % cmd)

    # 按照帧结构解析处理一条完整的帧数据
    def uartParse(self, data):
        # 判断输入data是否有效
        if not data:
            return None
        # 打印即将处理的数据
        print("userTest.uartParse", data, len(data))
        # log.logger.debug("userTest.uartParse", str(data), len(data))

        # 判断起始标志
        headIdx = data.find(bytes.fromhex("66AA"))
        # print("userTest.uartParse", "headidx", headidx)
        # 如果没有找到起始标志，返回等待数据完整
        if headIdx < 0:
            # print("userTest.uartParse", "parse no head error")
            log.logger.debug("userTest.uartParse parse no head error")
            return True, ''
        # 当索引值大于等于总体数据长度，需要再等多一些字节数据
        if len(data) <= headIdx:
            log.logger.debug("userTest.uartParse parse wait cnt bytes")
            return False, data

        # 可能存在断包情况，获取不到cnt信息
        try:
            # 获取数据长度
            cnt = data[headIdx + 4] * 256 + data[headIdx + 5]
            # print("userTest.uartParse", "cnt", cnt)
        except:
            log.logger.debug("userTest.uartParse no cnt info")
            return False, data

        # 等待数据帧完整
        if len(data) < headIdx + cnt + 7:
            log.logger.debug("userTest.uartParse parse wait complete")
            return False, data

        # 校验数据
        dataCheckSum = data[headIdx + cnt + 6]
        checkTmp = self.util.uchar_byte_checksum(data[headIdx:headIdx + cnt + 6])
        # 如果校验失败
        if dataCheckSum != checkTmp:
            # print("userTest.uartParse", "parse checksum error", dataCheckSum, checkTmp)
            log.logger.debug("userTest.uartParse data checksum fail!")
            return False, data[headIdx + cnt + 7:]

        # 校验成功，执行命令代码
        log.logger.debug("userTest.uartParse data checksum success!")

        # 获取2字节功能码
        cmd = data[headIdx + 2:headIdx + 4]
        log.logger.debug("userTest.uartParse cmd %s" % cmd)

        # 执行相应指令
        if cmd in self.cmdInsideProcessor.keys():
            self.cmdInsideProcessor[cmd](data[headIdx + 6:headIdx + cnt + 6])
        elif cmd in self.cmdProcessor:
            self.cmd_testItem(cmd, data[headIdx + 6:headIdx + cnt + 6])
        else:
            log.logger.error("userTest.uartParse parse cmd error!")
            return False, data[headIdx + cnt + 7:]

        # 正确处理完一条信息，正常返回
        return True, data[headIdx + cnt + 7:]

    # 接受串口收到的信息
    def uartProc(self, data):
        # 判断输入data是否有效
        if not data or len(data) == 0:
            return None
        # 追加到数据缓存区，hex字符串拼接
        self.readBuf = self.readBuf + data

        # print("userTest.uartProc", "rdbuf", self.rdbuf)
        # 将处理的的数据转换成bytes字节串
        unproc = self.util.HexStringToByte(self.readBuf)
        # 根据帧结构循环解析未处理过的数据
        while True:
            res, unproc = self.uartParse(unproc)
            if not unproc or unproc == '' or not res:
                break
        # 已处理完的数据从缓存区去除
        self.readBuf = self.util.asciiB2HexString(unproc) or ''
        # print("userTest.uartProc", "rdbuf", self.rdbuf)

    # 云端HTTP设备注册
    def dealHttpDeviceAuth(self, nodeId):

        self.tokenText = 0
        # 向平台申请接口token
        # tokenUrl = 'http://iot.vehiclink.com/api/v1/oauth2/clientToken'
        tokenUrl = self.regUrl + '/api/v1/oauth2/clientToken'
        tokenPara = {"clientId": "dhvnw41mfa", "clientSecret": "74a464528d5646e7a67a0597d57ef2bc"}

        x = requests.post(tokenUrl, json=tokenPara)

        if x.status_code == 200:
            # 网络状态码正确
            tokenRequest = json.loads(x.text)
            if tokenRequest['code'] == 200:
                # 内容状态码正确
                try:
                    self.tokenText = tokenRequest['data']['token']
                except Exception as e:
                    log.logger.error("主程序抛错：")
                    log.logger.error(e)
                    log.logger.error("\n" + traceback.format_exc())

                # log.logger.debug("设备token获取成功！ token：%s" % self.tokenText)
                log.logger.debug("设备token获取成功!")
            else:
                log.logger.error("设备token获取失败! code:%d" % tokenRequest['code'])
        else:
            log.logger.error("设备token Http失败! status_code:%d" % x.status_code)

        if self.tokenText != '':
            # 如果token获取到了，向平台注册设备
            # regDeviceUrl = 'http://iot.vehiclink.com/api/v1/device/regDevice'
            regDeviceUrl = self.regUrl + '/api/v1/device/regDevice'
            regDevicePara_str = '{"nodeId":"' + nodeId + '","productIotId":"' + self.PID + '"}'
            regDevicePara = json.loads(regDevicePara_str)
            # print(regDevicePara, type(regDevicePara))
            regDeviceHeaders_str = '{"token":"' + self.tokenText + '"}'
            regDeviceHeaders = json.loads(regDeviceHeaders_str)
            # print(regDeviceHeaders, type(regDeviceHeaders))
            y = requests.post(regDeviceUrl, json=regDevicePara, headers=regDeviceHeaders)

            if y.status_code == 200:
                # 网络状态码正确
                regRequest = json.loads(y.text)
                # print(regRequest)
                if regRequest['code'] == 200:
                    # 内容状态码正确
                    try:
                        self.deviceIotId = regRequest['data']['deviceIotId']
                        self.deviceSecret = regRequest['data'].get('deviceSecret', "")
                        tmpPid = regRequest['data']['productIotId']
                    except Exception as e:
                        log.logger.error("主程序抛错：")
                        log.logger.error(e)
                        log.logger.error("\n" + traceback.format_exc())

                    if self.PID == tmpPid:
                        # PID匹配
                        log.logger.info("云端设备注册成功!")
                        log.logger.info(y.text)
                        # log.logger.info("deviceIotId：%s" % self.deviceIotId)
                        # log.logger.info("deviceSecret：%s" % self.deviceSecret)

                        print('AA03', str(self.regInfoDict))

                        # 发送完整的授权信息
                        # self.authInfo_sinOut.emit(y.text)

                        return True

                    else:
                        log.logger.error("设备获取PID错误！ PID：%d" % tmpPid)
                        return False

                else:
                    log.logger.error("设备注册失败！ code：%d" % regRequest['code'])
                    return False
            else:
                log.logger.error("设备注册Http失败！ status_code：%d" % y.status_code)
                return False

    def run(self):
        # 创建小型状态机，处理与下位机的通讯
        # S_ENTER:进入产测,FF00命令
        # S_RESET:重置，FF01命令
        #############
        # ---S_GET_PRODINFO:查询设备信息，AA00命令
        # ---S_GET_DEV_SN:查询设备唯一码信息，AA01\AA02命令
        # ---S_AUTH_LOAD:授权信息烧录，AA03\AA05命令
        # ---S_AUTH_QUERY：授权信息查询，AA04\AA06命令
        #############
        # ---S_TEST：根据配置进行测试
        #############
        # S_END:退出产测，FF01指令

        print("启动UserTestThread线程")

        # 建立状态互斥锁
        self.sendMutexFlag = True

        # 清空顺序状态机列表
        self.stateList.clear()
        # 初始化列表索引
        self.listIndex = 0

        # 增加'state_enterTest'状态，初始状态
        self.stateList.append(testStatus.S_ENTER)

        # 增加'state_reset'状态,进行设备重启
        # self.stateList.append(testStatus.S_RESET)

        if self.Auth:
            # 提示进入授权模式
            log.logger.info('待测设备授权开始！')
            # 打印PID
            log.logger.info("待测设备PID：%s" % self.PID)

            # 增加获取产品信息状态
            self.stateList.append(testStatus.S_GET_PRODINFO)

            # 增加获取设备唯一码状态
            self.stateList.append(testStatus.S_GET_DEV_SN)

            # 增加授权烧录状态
            self.stateList.append(testStatus.S_AUTH_LOAD)

            # 增加授权查询状态
            self.stateList.append(testStatus.S_AUTH_QUERY)

        if self.FactoryTest:
            # 增加测试状态
            self.stateList.append(testStatus.S_TEST)

        # 增加退出产测状态，结束状态
        self.stateList.append(testStatus.S_END)

        print(self.stateList)

        # 初始状态
        self.stateMachine = self.stateList[self.listIndex]

        while True:

            if self.stateMachine == testStatus.S_ENTER:
                # 进入产测模式，持续查询，直到设备正确回复
                self.userTestSend("FF00", 0)

                # 测试项索引初始化
                self.testIndex = 0
                # self.progressBar_sinOut.emit(self.testPercentCal(), True, "等待设备进入产测")
                # 等待200ms
                time.sleep(0.2)

            elif self.stateMachine == testStatus.S_GET_PRODINFO:
                # 进入通信获取设备信息状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    self.userTestSend("AA00", 0)
                    self.progressBar_sinOut.emit(self.testPercentCal(), True, "获取设备信息中")
                # 等待500ms
                time.sleep(0.5)
                # 超时
                if self.retryCnt == 3:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.retryCnt = 0
                    self.sendMutexFlag = True
                    log.logger.info('AA00设备通信超时！！！')

                    # 发送进度条信息
                    self.progressBar_sinOut.emit(self.testPercentCal(), False, "获取设备信息超时")
                    # 等待
                    time.sleep(0.1)
                else :
                    self.retryCnt = self.retryCnt + 1

            elif self.stateMachine == testStatus.S_GET_DEV_SN:
                # 进入通信获取设备信息状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    if self.deviceType == 'BLE':
                        self.userTestSend("AA01", 0)
                    elif self.deviceType == 'BLE&4G':
                        self.userTestSend("AA01", 0)
                        time.sleep(0.1)
                        self.userTestSend("AA02", 0)  # 仅为记录 IMEI和ICCID

                    elif self.deviceType == '4G':
                        self.userTestSend("AA02", 0)

                    self.progressBar_sinOut.emit(self.testPercentCal(), True, "获取设备唯一码")
                # 等待1000ms
                time.sleep(3)
                # 超时

                if self.retryCnt == 3:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.retryCnt = 0
                    log.logger.info('AA01设备通信超时！！！')

                    # 发送进度条信息
                    self.progressBar_sinOut.emit(self.testPercentCal(), False, "获取设备唯一码超时")
                    # 等待
                    time.sleep(0.1)
                else:
                    self.retryCnt += 1
                self.sendMutexFlag = True

            elif self.stateMachine == testStatus.S_AUTH_LOAD:
                # 进入授权信息烧录状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False

                    if self.deviceType == '4G':

                        # 获取现在的时间
                        curTime = QDateTime.currentDateTime()
                        # 格式化时间为 yyMMddhhmmss
                        self.deviceIotId = curTime.toString('yyMMddhhmmss')

                        try:
                            authInf_str = ('{"deviceIotId":"' + self.deviceIotId + '","HostAddr":"' +
                                           self.hostAddr + '","HostPort": ' + str(self.hostPort) + '}')

                            authInf_bytes = codecs.encode(authInf_str)
                            authInf = ''.join(["%02X" % x for x in authInf_bytes])
                            authInfLen = len(authInf_str)

                            self.userTestSend("AA05", authInfLen, authInf)
                        except:
                            log.logger.error('AA05授权数据解析错误！')

                    if self.deviceType == 'BLE' or self.deviceType == 'BLE&4G':

                        try:
                            if self.deviceType == 'BLE':
                                authInf_str = '{"deviceIotId":"' + self.deviceIotId + '"}'
                            elif self.deviceType == 'BLE&4G':
                                authInf_str = '{"deviceIotId":"' + self.deviceIotId + '","deviceSecret":"' + self.deviceSecret + '"}'

                            authInf_bytes = codecs.encode(authInf_str)
                            authInf = ''.join(["%02X" % x for x in authInf_bytes])
                            authInfLen = len(authInf_str)

                            self.userTestSend("AA03", authInfLen, authInf)
                        except:
                            log.logger.error('AA03授权数据解析错误！')

                # 等待500ms
                time.sleep(0.5)

                # 超时
                if self.retryCnt == 5:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.retryCnt = 0
                    log.logger.info('设备烧录通信超时！！！')

                    # 发送进度条信息
                    self.progressBar_sinOut.emit(self.testPercentCal(), False, "设备烧录通信超时")

                    # 等待
                    time.sleep(0.1)
                else:
                    self.retryCnt = self.retryCnt + 1

                self.sendMutexFlag = True

            elif self.stateMachine == testStatus.S_AUTH_QUERY:
                # 进入授权信息查询状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    if self.deviceType == '4G':
                        self.userTestSend("AA06", 0)
                    else:
                        self.userTestSend("AA04", 0)

                    self.progressBar_sinOut.emit(self.testPercentCal(), True, "查询设备授权信息")

                # 等待500ms
                time.sleep(0.5)

                # 超时

                if self.retryCnt == 10:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.retryCnt = 0
                    log.logger.info('查询设备授权信息通信超时！！！')
                    # 发送进度条信息
                    self.progressBar_sinOut.emit(self.testPercentCal(), False, "查询设备授权信息通信超时")

                    # 等待
                    time.sleep(0.1)
                else:
                    self.retryCnt = self.retryCnt + 1

                self.sendMutexFlag = True

            elif self.stateMachine == testStatus.S_TEST:
                # 进入测试项下发

                cmd = self.testProcessor[self.testIndex].cmd
                data = self.testProcessor[self.testIndex].data
                name = self.testProcessor[self.testIndex].dspName
                retry = self.testProcessor[self.testIndex].retry
                inv = self.testProcessor[self.testIndex].interval

                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    try:
                        tmp_str = data
                        tmp_bytes = codecs.encode(tmp_str)
                        tmp = ''.join(["%02X" % x for x in tmp_bytes])
                        tmpLen = len(tmp_str)

                        self.userTestSend(cmd, tmpLen, tmp)

                    except Exception as e:
                        log.logger.error('%s授权数据解析错误！%s' % cmd % str(e))

                # 等待命令对应延迟
                time.sleep(inv / 1000.0)

                # 超时

                if self.retryCnt == retry:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.retryCnt = 0

                    log.logger.info('%s%s通信超时！！！' % (cmd, name))

                    # 发送进度条信息
                    self.progressBar_sinOut.emit(self.testPercentCal(), False, '%s%s通信超时！！！' % (cmd, name))

                    # 等待
                    time.sleep(0.2)

                self.retryCnt = self.retryCnt + 1
                self.sendMutexFlag = True

            elif self.stateMachine == testStatus.S_END:
                # 进入退出测试状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    self.userTestSend("FF01", 0)

                # 等待500ms
                time.sleep(0.5)

                # 超时
                self.retryCnt = self.retryCnt + 1
                if self.retryCnt == 6:
                    self.listIndex = 0
                    self.stateMachine = self.stateList[self.listIndex]
                    self.retryCnt = 0
                    self.sendMutexFlag = True
                    log.logger.info('FF01设备通信超时！！！')

                    # 发送进度条信息
                    time.sleep(0.2)

            # 与BaseUartThread线程进行同步，统一都是由串口状态判定
            if not self.Ser.isOpen():
                print("关闭UserTestThread线程")
                self.quit()
                return
