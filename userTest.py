import time
from PyQt5.QtCore import QThread, QDateTime, Qt, pyqtSignal, QSettings
import baseUtils
from baseLogger import log
import requests
from requests.exceptions import SSLError
import json
import traceback
import codecs


class UserTestThread(QThread):
    # 自定义信号，用来发送串口write数据
    uartWrite_sinOut = pyqtSignal(str)
    # 自定义信号，用来发送打印信息及授权信息
    printMsg_sinOut = pyqtSignal(str, str, str)
    # 自定义信号，用来界面显示完整的授权信息
    authInfo_sinOut = pyqtSignal(str)
    # 自定义信号，用来发送授权进度条数据
    progressBarAuth_sinOut = pyqtSignal(int, str)
    # 自定义信号，用来发送测试进度条数据
    progressBarTest_sinOut = pyqtSignal(int, str)

    def __init__(self, Ser, PID, Auth, manualInput, FactoryTest, regUrl):
        super(UserTestThread, self).__init__()
        # 创建BaseUtils实例
        self.util = baseUtils.BaseUtils()
        # 接受主函数传递的参数
        self.Ser = Ser
        self.PID = PID
        self.Auth = Auth
        self.manualInput = manualInput
        self.FactoryTest = FactoryTest
        self.regUrl = regUrl
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
        self.stateMachine = 'state_enterTest'
        # 创建小型状态机，子状态
        self.stateMachineSub = ''
        # 创建循环次数变量
        self.cycleCnt = 0
        # 创建重新测试次数变量
        self.retryCnt = 0
        # 定义发送互斥标志位，除了FF00是循环发送查询，其他指令只发一次，返回错误或者超时，直接判错，True可以发送，False不能发送
        self.sendMutexFlag = True
        # 创建ACK CMD表
        self.cmdProcessor = {}

        # 授权测试开始时间戳
        self.startStamp = 0
        # 授权测试结束时间戳
        self.endStamp = 0
        # 测试时间间隔
        self.testInterval = 0

        # FLASH测试结果标志位
        self.testFlashFlag = False
        # G-sensor测试结果标志位
        self.testGsensorFlag = False
        # ADC测试结果标志位
        self.testAdcFlag = False
        # volt值
        self.adcVolt = 0
        # subVolt值
        self.adcSubVolt = 0
        # ICCID信息
        self.ICCID = ''
        # IMEI信息
        self.IMEI = ''
        # 4G测试结果标志位
        self.testLteFlag = False
        # 4G CSQ值
        self.lteCsq = 0
        # GPS测试结果标志位
        self.testGpsFlag = False
        # GPS有用星数
        self.gpsUStarNum = 0

        # csv记录列表
        self.regInfoDict = {}

        # 创建顺序状态机列表
        self.stateList = []
        # 创建列表索引
        self.listIndex = 0

        # 通过外部ini文件配置相关测试参数
        try:
            self.settings = QSettings("resource/config/user_config.ini", QSettings.IniFormat)
            self.lteTestFlag = self.settings.value("TEST/lteTest_flag")
            self.subBattFlag = self.settings.value("TEST/subBattFlag")

            self.flashRetryNum = int(self.settings.value("TEST/flash_retryNum"))
            self.gSensorRetryNum = int(self.settings.value("TEST/gSensor_retryNum"))

            self.voltMaxTh = int(self.settings.value("TEST/volt_maxTh"))
            self.voltMinTh = int(self.settings.value("TEST/volt_minTh"))
            self.subVoltMaxTh = int(self.settings.value("TEST/subVolt_maxTh"))
            self.subVoltMinTh = int(self.settings.value("TEST/subVolt_minTh"))
            self.voltRetryNum = int(self.settings.value("TEST/volt_retryNum"))

            self.lteInfoRetryNum = int(self.settings.value("TEST/lteInfo_retryNum"))

            self.csqMinTh = int(self.settings.value("TEST/csq_minTh"))
            self.csqRetryNum = int(self.settings.value("TEST/csq_retryNum"))
            self.uStarNum = int(self.settings.value("TEST/uStarNum_minTh"))
            self.uStarNumRetryNum = int(self.settings.value("TEST/uStarNum_retryNum"))

        except IOError:
            log.logger.error('userTest缺少user_config.ini文件！')
            self.lteTestFlag = 'false'

            self.flashRetryNum = 5
            self.gSensorRetryNum = 5

            self.voltMaxTh = 4900
            self.voltMinTh = 4700
            self.subVoltMaxTh = 420
            self.subVoltMinTh = 300
            self.voltRetryNum = 5

            self.lteInfoRetryNum = 10

            self.csqMinTh = 10
            self.csqRetryNum = 120
            self.uStarNum = 3
            self.uStarNumRetryNum = 360

        print("userTest中获取外部ini参数: lteTest_flag:", self.lteTestFlag)
        print("userTest中获取外部ini参数: subBattFlag:", self.subBattFlag)
        print("userTest中获取外部ini参数: flash_retryNum:", self.flashRetryNum)
        print("userTest中获取外部ini参数: gSensor_retryNum:", self.gSensorRetryNum)
        print("userTest中获取外部ini参数: volt_maxTh:", self.voltMaxTh)
        print("userTest中获取外部ini参数: volt_minTh:", self.voltMinTh)
        print("userTest中获取外部ini参数: subVolt_maxTh:", self.subVoltMaxTh)
        print("userTest中获取外部ini参数: subVolt_minTh:", self.subVoltMinTh)
        print("userTest中获取外部ini参数: volt_retryNum:", self.voltRetryNum)
        print("userTest中获取外部ini参数: lteInfo_retryNum:", self.lteInfoRetryNum)
        print("userTest中获取外部ini参数: csq_minTh:", self.csqMinTh)
        print("userTest中获取外部ini参数: csq_retryNum:", self.csqRetryNum)
        print("userTest中获取外部ini参数: uStarNum_minTh:", self.uStarNum)
        print("userTest中获取外部ini参数: uStarNum_retryNum:", self.uStarNumRetryNum)

        print("创建UserTestThread线程")

    # 发送测试指令
    def userTestSend(self, testCmd, testLen, testData=''):
        # 发送数据组包
        dataTmp = "66AA" + testCmd + testLen + testData
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
        if self.stateMachine == 'state_enterTest':

            if len(hexx) == 1:
                # 长度符合
                if hexx[0] == 0:
                    # 进入产测模式成功
                    self.listIndex = self.listIndex + 1
                    self.stateMachine = self.stateList[self.listIndex]
                    log.logger.info('待测设备已接入!')

                    if self.FactoryTest:
                        # 初始化测试进度条
                        self.progressBarTest_sinOut.emit(25, '待测设备已接入')

                    else:
                        # 如果没有授权操作，发送测试进度条信息
                        if self.lteTestFlag == 'true':
                            self.progressBarTest_sinOut.emit(25, '待测设备已接入')
                        else:
                            self.progressBarTest_sinOut.emit(25, '待测设备已接入')

                    # 初始化授权与测试信息
                    self.nodeId = ''
                    self.deviceIotId = ''
                    self.deviceSecret = ''
                    self.testFlashFlag = False
                    self.testGsensorFlag = False
                    self.testAdcFlag = False
                    self.adcVolt = 0
                    self.adcSubVolt = 0
                    self.ICCID = ''
                    self.IMEI = ''
                    self.testLteFlag = False
                    self.lteCsq = 0
                    self.testGpsFlag = False
                    self.gpsUStarNum = 0

                    # 获取开始时间戳
                    self.startStamp = time.time()

                else:
                    # 进入产测模式失败
                    self.listIndex = 0
                    self.stateMachine = self.stateList[self.listIndex]
                    log.logger.info('进入产测失败!')

                # 清零周期次数变量
                self.cycleCnt = 0
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
        if self.stateMachine == 'state_quitTest':

            if len(hexx) == 1:
                # 长度符合
                # 退出产测模式成功
                self.listIndex = 0
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('待测设备退出产测模式!')

                # 发送打印标签及授权信息
                self.printMsg_sinOut.emit(self.nodeId, self.deviceIotId, self.PID)

                # 获取结束时间戳
                self.endStamp = time.time()
                # self.testInterval = self.endStamp - self.startStamp
                self.testInterval = '{:.2f}'.format(self.endStamp - self.startStamp)

                # log.logger.info("本次耗费时间(秒)：%.02f", self.testInterval)
                log.logger.info("本次耗费时间(秒)：%s", self.testInterval)

                # 记录测试结果
                self.regInfoDict['TEST_FLASH'] = self.testFlashFlag
                self.regInfoDict['TEST_GSENSOR'] = self.testGsensorFlag
                self.regInfoDict['VOLT'] = self.adcVolt
                self.regInfoDict['SUBVOLT'] = self.adcSubVolt
                self.regInfoDict['TEST_ADC'] = self.testAdcFlag
                self.regInfoDict['TEST_4G'] = self.testLteFlag
                self.regInfoDict['CSQ'] = self.lteCsq
                self.regInfoDict['ICCID'] = self.ICCID
                self.regInfoDict['IMEI'] = self.IMEI
                self.regInfoDict['TEST_GPS'] = self.testGpsFlag
                self.regInfoDict['GPSNUM'] = self.gpsUStarNum
                self.regInfoDict['TIME_CONS(s)'] = self.testInterval

                print('FF01', str(self.regInfoDict))
                self.util.addToRegList(self.regInfoDict)

                log.logger.info('**************************************************')

                # 清零周期次数变量
                self.cycleCnt = 0
                # 初始化发送互斥标志位
                self.sendMutexFlag = True

        else:
            log.logger.warning('FF01错误应答，未在对应状态！')

    # 解析授权烧录指令AA00
    def cmd_AA00(self, hexx):
        # print("userTest.cmd_AA00", hexx)
        log.logger.debug("cmd_AA00接受数据：%s" % hexx)

        # 如果在'state_authLoad'状态
        if self.stateMachine == 'state_authLoad':

            if len(hexx) == 1:
                # 长度符合
                if hexx[0] == 0:
                    # 授权信息烧录成功
                    self.listIndex = self.listIndex + 1
                    self.stateMachine = self.stateList[self.listIndex]
                    log.logger.info('设备授权信息烧录完毕！')

                    # 发送进度条信息
                    self.progressBarAuth_sinOut.emit(75, 'working')
                else:
                    # 授权信息烧录不成功，请重试
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    log.logger.info('设备授权信息烧录出错！')

                    # 发送进度条信息
                    self.progressBarAuth_sinOut.emit(0, 'fail')

                # 清零周期次数变量
                self.cycleCnt = 0
                # 初始化发送互斥标志位
                self.sendMutexFlag = True
        else:
            log.logger.warning('AA00错误应答，未在对应状态！')

    # 解析授权查询指令AA01
    def cmd_AA01(self, hexx):
        # print("userTest.cmd_AA01", hexx)
        log.logger.debug("cmd_AA01接受数据：%s" % hexx)

        # 如果在'state_authQuery'状态
        if self.stateMachine == 'state_authQuery':

            # b"example"  --->  "example",转换成字符串
            authtmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            authtmp = json.loads(authtmp_str)
            if authtmp['deviceIotId'] == self.deviceIotId and authtmp['deviceSecret'] == self.deviceSecret:
                # 查询设备烧录授权信息正确
                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('查询待测设备烧录的授权信息正确！')

                # 发送进度条信息
                self.progressBarAuth_sinOut.emit(100, 'success')
            else:
                # 查询设备烧录授权信息不正确
                self.listIndex = -1
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.error('查询设备烧录授权信息不正确!')

                # 发送进度条信息
                self.progressBarAuth_sinOut.emit(0, 'fail')

            # 清零周期次数变量
            self.cycleCnt = 0
            # 初始化发送互斥标志位
            self.sendMutexFlag = True
        else:
            log.logger.warning('AA01错误应答，未在对应状态！')

    # 解析授权查询指令AA02
    def cmd_AA02(self, hexx):
        # print("userTest.cmd_AA02", hexx)
        log.logger.debug("cmd_AA02接受数据：%s" % hexx)

        # 如果在'state_obtainDeviceInfo'状态
        if self.stateMachine == 'state_obtainDeviceInfo':

            # b"example"  --->  "example",转换成字符串
            authtmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            authtmp = json.loads(authtmp_str)

            if not authtmp['mac'] or len(authtmp['mac']) != 12:
                self.listIndex = -1
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('查询设备mac出错！')

                # 发送进度条信息
                self.progressBarAuth_sinOut.emit(0, 'fail')
                return

            if authtmp['productId'] == self.PID:

                log.logger.info("已查询nodeId:" + authtmp['mac'])
                self.nodeId = authtmp['mac']

                if self.dealHttpDeviceAuth(self.nodeId):
                    self.listIndex = self.listIndex + 1
                    self.stateMachine = self.stateList[self.listIndex]
                    log.logger.info('查询设备产品信息完毕！')

                    # 发送进度条信息
                    self.progressBarAuth_sinOut.emit(50, 'working')
                else:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    log.logger.info('查询设备产品信息出错！')

                    # 发送进度条信息
                    self.progressBarAuth_sinOut.emit(0, 'fail')

            else:
                # 查询设备产品信息不成功，请重试
                self.listIndex = -1
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('查询设备产品信息PID出错！')

                # 发送进度条信息
                self.progressBarAuth_sinOut.emit(0, 'fail')

            # 清零周期次数变量
            self.cycleCnt = 0
            # 初始化发送互斥标志位
            self.sendMutexFlag = True

        else:
            log.logger.warning('AA02错误应答，未在对应状态！')

    # 解析授权查询指令AA03
    def cmd_AA03(self, hexx):
        # print("userTest.cmd_AA03", hexx)
        log.logger.debug("cmd_AA03接受数据：%s" % hexx)

        # 如果在'state_obtain4GInfo'状态
        if self.stateMachine == 'state_obtain4GInfo':

            # b"example"  --->  "example",转换成字符串
            authtmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            authtmp = json.loads(authtmp_str)

            if len(authtmp['iccid']) > 0 and len(authtmp['IMEI']) > 0:

                self.ICCID = authtmp['iccid'] + '\t'
                self.IMEI = authtmp['IMEI'] + '\t'

                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('查询设备蜂窝信息正确！')

                # 重试次数清零
                self.retryCnt = 0

                # 发送测试进度条信息
                self.progressBarTest_sinOut.emit(50, 'working')

            else:
                self.retryCnt = self.retryCnt + 1
                if self.retryCnt == self.lteInfoRetryNum:
                    # 重试次数清零
                    self.retryCnt = 0
                    # 更新状态
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]

                    # 发送进度条信息
                    self.progressBarTest_sinOut.emit(0, 'fail')

                    log.logger.info('查询设备蜂窝信息出错！')
                # log.logger.debug('查询设备蜂窝信息中...')

            # 清零周期次数变量
            self.cycleCnt = 0
            # 初始化发送互斥标志位
            self.sendMutexFlag = True

        else:
            log.logger.warning('AA03错误应答，未在对应状态！')

    # 解析授权查询指令0001
    def cmd_0001(self, hexx):
        # print("userTest.cmd_0001", hexx)
        log.logger.debug("cmd_0001接受数据：%s" % hexx)

        # 如果在'state_testFlash'状态
        if self.stateMachine == 'state_testFlash':

            # b"example"  --->  "example",转换成字符串
            authtmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            authtmp = json.loads(authtmp_str)

            if authtmp['ret'] == 0:
                # 设备返回成功
                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                self.testFlashFlag = True
                log.logger.info('测试FLASH成功！')

                # 重试次数清零
                self.retryCnt = 0

                # 发送测试进度条信息
                if self.lteTestFlag == 'true':
                    self.progressBarTest_sinOut.emit(20, 'working')
                else:
                    self.progressBarTest_sinOut.emit(50, 'working')

            else:
                self.retryCnt = self.retryCnt + 1
                if self.retryCnt == self.flashRetryNum:
                    # 重试次数清零
                    self.retryCnt = 0
                    # 更新状态
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.testFlashFlag = False
                    log.logger.info('测试FLASH出错！')

                    # 发送进度条信息
                    self.progressBarTest_sinOut.emit(0, 'fail')

            # 清零周期次数变量
            self.cycleCnt = 0
            # 初始化发送互斥标志位
            self.sendMutexFlag = True

        else:
            log.logger.warning('0001错误应答，未在对应状态！')

    # 解析授权查询指令0002
    def cmd_0002(self, hexx):
        # print("userTest.cmd_0002", hexx)
        log.logger.debug("cmd_0002接受数据：%s" % hexx)

        # 如果在'state_testGsensor'状态
        if self.stateMachine == 'state_testGsensor':

            # b"example"  --->  "example",转换成字符串
            authtmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            authtmp = json.loads(authtmp_str)

            if authtmp['ret'] == 0:
                # 设备返回成功
                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                self.testGsensorFlag = True
                log.logger.info('测试G-sensor成功！')

                # 重试次数清零
                self.retryCnt = 0

                # 发送测试进度条信息
                if self.lteTestFlag == 'true':
                    self.progressBarTest_sinOut.emit(30, 'working')
                else:
                    self.progressBarTest_sinOut.emit(75, 'working')

            else:
                self.retryCnt = self.retryCnt + 1
                if self.retryCnt == self.gSensorRetryNum:
                    # 重试次数清零
                    self.retryCnt = 0
                    # 更新状态
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.testGsensorFlag = False
                    log.logger.info('测试G-sensor出错！')

                    # 发送进度条信息
                    self.progressBarTest_sinOut.emit(0, 'fail')

            # 清零周期次数变量
            self.cycleCnt = 0
            # 初始化发送互斥标志位
            self.sendMutexFlag = True

        else:
            log.logger.warning('0002错误应答，未在对应状态！')

    # 解析授权查询指令0006
    def cmd_0006(self, hexx):
        # print("userTest.cmd_0006", hexx)
        log.logger.debug("cmd_0006接受数据：%s" % hexx)

        # 如果在'state_testAdc'状态
        if self.stateMachine == 'state_testAdc':

            # b"example"  --->  "example",转换成字符串
            authtmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            authtmp = json.loads(authtmp_str)

            self.adcVolt = authtmp['Volt']
            self.adcSubVolt = authtmp['SubVolt']
            if self.subBattFlag == 'true':
                ret = ((self.voltMinTh <= authtmp['Volt'] <= self.voltMaxTh) and (self.subVoltMinTh <= authtmp[
                    'SubVolt'] <= self.subVoltMaxTh))
            else:
                ret = (self.voltMinTh <= authtmp['Volt'] <= self.voltMaxTh)

            if ret:
                # 设备返回成功
                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                self.testAdcFlag = True
                log.logger.info('测试ADC功能成功！')

                # 重试次数清零
                self.retryCnt = 0

                # 发送测试进度条信息
                if self.lteTestFlag == 'true':
                    self.progressBarTest_sinOut.emit(40, 'working')
                else:
                    self.progressBarTest_sinOut.emit(100, 'success')

            else:
                self.retryCnt = self.retryCnt + 1
                if self.retryCnt == self.voltRetryNum:
                    # 重试次数清零
                    self.retryCnt = 0
                    # 更新状态
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.testAdcFlag = False
                    log.logger.info("volt: %d" % self.adcVolt)
                    log.logger.info("subVolt: %d" % self.adcSubVolt)
                    log.logger.info('测试ADC功能出错！')

                    # 发送进度条信息
                    self.progressBarTest_sinOut.emit(0, 'fail')

            # 清零周期次数变量
            self.cycleCnt = 0
            # 初始化发送互斥标志位
            self.sendMutexFlag = True

        else:
            log.logger.warning('0006错误应答，未在对应状态！')

    # 解析授权查询指令0020
    def cmd_0020(self, hexx):
        # print("userTest.cmd_0020", hexx)
        log.logger.debug("cmd_0020接受数据：%s" % hexx)

        # 如果在'state_test4G'状态
        if self.stateMachine == 'state_test4G':

            # b"example"  --->  "example",转换成字符串
            authtmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            authtmp = json.loads(authtmp_str)

            self.lteCsq = authtmp['CSQ']

            if authtmp['ret'] == 0 and authtmp['CSQ'] >= self.csqMinTh:
                # 设备返回成功
                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                self.testLteFlag = True
                log.logger.info('测试4G功能成功！')

                # 重试次数清零
                self.retryCnt = 0

                # 发送测试进度条信息
                self.progressBarTest_sinOut.emit(70, 'working')

            else:
                self.retryCnt = self.retryCnt + 1
                if self.retryCnt == self.csqRetryNum:
                    # 重试次数清零
                    self.retryCnt = 0
                    # 更新状态
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.testLteFlag = False

                    # 发送进度条信息
                    self.progressBarTest_sinOut.emit(0, 'fail')

                    log.logger.info("4G CSQ: %d" % self.lteCsq)
                    log.logger.info('测试4G功能出错！')
                log.logger.debug('测试4G功能中...')

            # 清零周期次数变量
            self.cycleCnt = 0
            # 初始化发送互斥标志位
            self.sendMutexFlag = True

        else:
            log.logger.warning('0020错误应答，未在对应状态！')

    # 解析授权查询指令0021
    def cmd_0021(self, hexx):
        # print("userTest.cmd_0021", hexx)
        log.logger.debug("cmd_0021接受数据：%s" % hexx)

        # 如果在'state_testGps'状态
        if self.stateMachine == 'state_testGps':

            # b"example"  --->  "example",转换成字符串
            authtmp_str = self.util.BytesToStr(hexx)
            # 加载成json格式
            authtmp = json.loads(authtmp_str)

            self.gpsUStarNum = authtmp['star']

            # if authtmp['ret'] == 0 and authtmp['star'] >= self.uStarNum:
            if authtmp['star'] >= self.uStarNum:
                # 设备返回成功
                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                self.testGpsFlag = True
                log.logger.info('测试GPS功能成功！')

                # 重试次数清零
                self.retryCnt = 0

                # 发送测试进度条信息
                self.progressBarTest_sinOut.emit(100, 'success')

            else:
                self.retryCnt = self.retryCnt + 1
                if self.retryCnt == self.uStarNumRetryNum:
                    # 重试次数清零
                    self.retryCnt = 0
                    # 更新状态
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.testGpsFlag = False

                    # 发送进度条信息
                    self.progressBarTest_sinOut.emit(0, 'fail')

                    log.logger.info("GPS有用星数: %d" % self.gpsUStarNum)
                    log.logger.info('测试GPS功能出错！')
                # log.logger.debug('测试GPS功能中...')

            # 清零周期次数变量
            self.cycleCnt = 0
            # 初始化发送互斥标志位
            self.sendMutexFlag = True

        else:
            log.logger.warning('0021错误应答，未在对应状态！')

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

        # 创建测试协议cmd字典
        self.cmdProcessor = {
            bytes.fromhex("FF00"): self.cmd_FF00,
            bytes.fromhex("FF01"): self.cmd_FF01,
            bytes.fromhex("AA00"): self.cmd_AA00,
            bytes.fromhex("AA01"): self.cmd_AA01,
            bytes.fromhex("AA02"): self.cmd_AA02,
            bytes.fromhex("AA03"): self.cmd_AA03,
            bytes.fromhex("0001"): self.cmd_0001,
            bytes.fromhex("0002"): self.cmd_0002,
            bytes.fromhex("0006"): self.cmd_0006,
            bytes.fromhex("0020"): self.cmd_0020,
            bytes.fromhex("0021"): self.cmd_0021,
        }

        # 可能存在没有相应指令函数，则报错退出
        try:
            # 执行相应指令
            self.cmdProcessor[cmd](data[headIdx + 6:headIdx + cnt + 6])
        except:
            # print("userTest.uartParse", "parse cmd error", cmd)
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
                        self.deviceSecret = regRequest['data']['deviceSecret']
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

                        # 记录授权信息
                        now = QDateTime.currentDateTime()
                        self.regInfoDict['TIME'] = now.toString(Qt.ISODate)
                        self.regInfoDict['PID'] = self.PID
                        self.regInfoDict['DID'] = self.deviceIotId
                        self.regInfoDict['DSECRET'] = self.deviceSecret
                        self.regInfoDict['MAC'] = self.nodeId
                        print('AA02', str(self.regInfoDict))

                        # 发送完整的授权信息
                        self.authInfo_sinOut.emit(y.text)

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

    # 接受输入的硬件标识码
    def dealInputDeviceId(self, text):
        if self.stateMachine == 'state_manualInputInfo':
            log.logger.info("已输入nodeId:" + text)
            self.nodeId = text

            if self.dealHttpDeviceAuth(self.nodeId):
                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('手动输入设备产品信息完毕！')
            else:
                self.listIndex = 0
                self.stateMachine = self.stateList[self.listIndex]
                log.logger.info('手动输入设备产品信息出错！')

        else:
            log.logger.warning("未在设备授权模式")

    def run(self):
        # 创建小型状态机，处理与下位机的通讯
        # state_enterTest:进入产测,FF00命令
        #############
        # ---state_obtainDeviceInfo:查询设备信息，AA02命令
        # ---state_manualInputInfo:手动输入设备信息，无命令
        # ---state_authLoad:授权信息烧录，AA00命令
        # ---state_authQuery：授权信息查询，AA01命令
        #############
        # ---state_testFlash：测试FLASH，0001命令
        # ---state_testGsensor：测试G-sensor，0002命令
        # ---state_testAdc：测试ADC功能，0006命令
        # ---state_obtain4GInfo:查询蜂窝信息，AA03命令
        # ---state_test4G：测试4G，0020命令
        # ---state_testGps：测试GPS，0021命令
        #############
        # state_quitTest:退出产测，FF01指令

        print("启动UserTestThread线程")

        # 建立状态互斥锁
        self.sendMutexFlag = True

        # 清空顺序状态机列表
        self.stateList.clear()
        # 初始化列表索引
        self.listIndex = 0

        # 增加'state_enterTest'状态，初始状态
        self.stateList.append('state_enterTest')

        if self.Auth:
            # 提示进入授权模式
            log.logger.info('待测设备授权开始！')
            # 打印PID
            log.logger.info("待测设备PID：%s" % self.PID)

            # 增加'state_obtainDeviceInfo'状态
            self.stateList.append('state_obtainDeviceInfo')

            # 增加'state_authLoad'状态
            self.stateList.append('state_authLoad')

            # 增加'state_authQuery'状态
            self.stateList.append('state_authQuery')

        if self.FactoryTest:
            # 增加'state_testFlash'状态
            self.stateList.append('state_testFlash')

            # 增加'state_testGsensor'状态
            self.stateList.append('state_testGsensor')

            # 增加'state_testAdc'状态
            self.stateList.append('state_testAdc')

            if self.lteTestFlag == 'true':
                # 增加'state_obtain4GInfo'状态
                self.stateList.append('state_obtain4GInfo')

                # 增加'state_test4G'状态
                self.stateList.append('state_test4G')

                # 增加'state_testGps'状态
                self.stateList.append('state_testGps')

        # 增加'state_quitTest'状态，结束状态
        self.stateList.append('state_quitTest')

        print(self.stateList)

        # 初始状态
        self.stateMachine = self.stateList[self.listIndex]

        while True:

            if self.stateMachine == 'state_enterTest':
                # 进入产测模式，持续查询，直到设备正确回复
                self.userTestSend("FF00", "0000")

                # 等待200ms
                time.sleep(0.2)

            elif self.stateMachine == 'state_obtainDeviceInfo':
                # 进入通信获取设备信息状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    self.userTestSend("AA02", "0000")

                # 等待500ms
                time.sleep(0.5)

                # 超时
                self.cycleCnt = self.cycleCnt + 1
                if self.cycleCnt == 10:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.cycleCnt = 0
                    self.sendMutexFlag = True
                    log.logger.info('AA02设备通信超时！！！')

                    # 发送进度条信息
                    self.progressBarAuth_sinOut.emit(0, 'fail')
                    # 等待
                    time.sleep(3)

            elif self.stateMachine == 'state_manualInputInfo':
                # 等到手动输入信息

                # 等待500ms
                time.sleep(0.5)

            elif self.stateMachine == 'state_authLoad':
                # 进入授权信息烧录状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False

                    try:
                        authInf_str = '{"deviceIotId":"' + self.deviceIotId + '","deviceSecret":"' + self.deviceSecret + '"}'
                        authInf_bytes = codecs.encode(authInf_str)
                        authInf = ''.join(["%02X" % x for x in authInf_bytes])
                        authInfLen = ''.join(["%04X" % len(authInf_str)])

                        self.userTestSend("AA00", authInfLen, authInf)
                    except:
                        log.logger.error('AA00授权数据解析错误！')

                # 等待500ms
                time.sleep(0.5)

                # 超时
                self.cycleCnt = self.cycleCnt + 1
                if self.cycleCnt == 10:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.cycleCnt = 0
                    self.sendMutexFlag = True
                    log.logger.info('AA00设备通信超时！！！')

                    # 发送进度条信息
                    self.progressBarAuth_sinOut.emit(0, 'fail')
                    # 等待
                    time.sleep(3)

            elif self.stateMachine == 'state_authQuery':
                # 进入授权信息查询状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    self.userTestSend("AA01", "0000")

                # 等待500ms
                time.sleep(0.5)

                # 超时
                self.cycleCnt = self.cycleCnt + 1
                if self.cycleCnt == 10:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.cycleCnt = 0
                    self.sendMutexFlag = True
                    log.logger.info('AA01设备通信超时！！！')

                    # 发送进度条信息
                    self.progressBarAuth_sinOut.emit(0, 'fail')
                    # 等待
                    time.sleep(3)

            elif self.stateMachine == 'state_testFlash':
                # 进入FLASH测试状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    self.userTestSend("0001", "0000")

                    if self.retryCnt == 0:
                        log.logger.info('设备Flash功能测试中...')

                # 等待500ms
                time.sleep(0.5)

                # 超时
                self.cycleCnt = self.cycleCnt + 1
                if self.cycleCnt == 10:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.cycleCnt = 0
                    self.sendMutexFlag = True
                    log.logger.info('0001设备通信超时！！！')

                    # 发送进度条信息
                    self.progressBarTest_sinOut.emit(0, 'fail')
                    # 等待
                    time.sleep(3)

            elif self.stateMachine == 'state_testGsensor':
                # 进入G-sensor测试状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    self.userTestSend("0002", "0000")

                    if self.retryCnt == 0:
                        log.logger.info('设备G-sensor功能测试中...')

                # 等待500ms
                time.sleep(0.5)

                # 超时
                self.cycleCnt = self.cycleCnt + 1
                if self.cycleCnt == 10:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.cycleCnt = 0
                    self.sendMutexFlag = True
                    log.logger.info('0002设备通信超时！！！')

                    # 发送进度条信息
                    self.progressBarTest_sinOut.emit(0, 'fail')
                    # 等待
                    time.sleep(3)

            elif self.stateMachine == 'state_testAdc':
                # 进入ADC测试状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    self.userTestSend("0006", "0000")

                    if self.retryCnt == 0:
                        log.logger.info('设备ADC功能测试中...')

                # 等待500ms
                time.sleep(0.5)

                # 超时
                self.cycleCnt = self.cycleCnt + 1
                if self.cycleCnt == 10:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.cycleCnt = 0
                    self.sendMutexFlag = True
                    log.logger.info('0006设备通信超时！！！')

                    # 发送进度条信息
                    self.progressBarTest_sinOut.emit(0, 'fail')
                    # 等待
                    time.sleep(3)

            elif self.stateMachine == 'state_obtain4GInfo':
                # 进入获取设备蜂窝信息状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    self.userTestSend("AA03", "0000")

                    if self.retryCnt == 0:
                        log.logger.info('设备蜂窝信息查询中...')

                # 等待500ms
                time.sleep(0.5)

                # 超时
                self.cycleCnt = self.cycleCnt + 1
                if self.cycleCnt == 10:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.cycleCnt = 0
                    self.sendMutexFlag = True
                    log.logger.info('AA03设备通信超时！！！')

                    # 发送进度条信息
                    self.progressBarTest_sinOut.emit(0, 'fail')
                    # 等待
                    time.sleep(3)

            elif self.stateMachine == 'state_test4G':
                # 进入4G测试状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    self.userTestSend("0020", "0000")

                    if self.retryCnt == 0:
                        log.logger.info('4G功能测试中...')

                # 等待500ms
                time.sleep(0.5)

                # 超时
                self.cycleCnt = self.cycleCnt + 1
                if self.cycleCnt == 10:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.cycleCnt = 0
                    self.sendMutexFlag = True
                    log.logger.info('0020设备通信超时！！！')

                    # 发送进度条信息
                    self.progressBarTest_sinOut.emit(0, 'fail')
                    # 等待
                    time.sleep(3)

            elif self.stateMachine == 'state_testGps':
                # 进入GPS测试状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    self.userTestSend("0021", "0000")

                    if self.retryCnt == 0:
                        log.logger.info('GPS定位测试中...')

                # 等待500ms
                time.sleep(0.5)

                # 超时
                self.cycleCnt = self.cycleCnt + 1
                if self.cycleCnt == 10:
                    self.listIndex = -1
                    self.stateMachine = self.stateList[self.listIndex]
                    self.cycleCnt = 0
                    self.sendMutexFlag = True
                    log.logger.info('0021设备通信超时！！！')

                    # 发送进度条信息
                    self.progressBarTest_sinOut.emit(0, 'fail')
                    # 等待
                    time.sleep(3)

            elif self.stateMachine == 'state_quitTest':
                # 进入GPS测试状态
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    self.userTestSend("FF01", "0000")

                # 等待500ms
                time.sleep(0.5)

                # 超时
                self.cycleCnt = self.cycleCnt + 1
                if self.cycleCnt == 6:
                    self.listIndex = 0
                    self.stateMachine = self.stateList[self.listIndex]
                    self.cycleCnt = 0
                    self.sendMutexFlag = True
                    log.logger.info('FF01设备通信超时！！！')
                    # 等待
                    time.sleep(3)

            # 与BaseUartThread线程进行同步，统一都是由串口状态判定
            if not self.Ser.isOpen():
                print("关闭UserTestThread线程")
                self.quit()
                return
