import json
import threading
import time
from enum import Enum

from PyQt5.QtCore import QThread, pyqtSignal

from baseLogger import log
from baseUtils import BaseUtils

VER_PROTOCAL = 0x01


class MachineState(Enum):
    Waiting = 1
    CheckVer = 2
    DpDisplay = 3
    OTAStart = 4
    OTABlockSend = 5


class Frame:
    """
    帧格式定义
    """
    HEAD = 2
    SN = 4
    ACK_SN = 4
    CMD = 2
    DATA_LEN = 2
    DATA = 2
    CHK_SUM = 1

    DATA_START = HEAD + SN + ACK_SN + CMD + DATA_LEN
    LEN_EXPDATA = DATA_START + CHK_SUM


class OTAState:
    GoOn = 1
    Fail = 2
    TransDataComplete = 3
    Success = 4
    UserExit = 5
    OverTime = 6




def calc_crc16_modbus(data: bytes, poly: int = 0x8005) -> int:
    """
    Calculate the CRC16-Modbus checksum value.

    This function calculates the CRC16-Modbus checksum value for the given data.

    Args:
        data (bytes): The data to calculate the checksum for.
        poly (int, optional): The polynomial to use. Defaults to 0x8005 (0x1021 can also be used).

    Returns:
        int: The calculated checksum value.
    """
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for i in range(8):
            if (crc & 1) != 0:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1

    return ((crc & 0xff) << 8) + (crc >> 8)


class OTA_PCB:
    def __init__(self, FilePath, devType, FileSize, FileCrc32, BlockCnt):
        self.FilePath = FilePath
        self.devType = devType
        self.FileSize = FileSize
        self.BlockSize = 4096
        self.BlockCnt = BlockCnt
        self.CurrentPackageSize = 0
        self.crc32File = FileCrc32
        self.OTAState = OTAState.GoOn
        self.blockLock = True
        self.otaExit = False

    def onOVER(self):
        self.FilePath = ''
        self.BlockCnt = 0
        self.CurrentPackageSize = 0
        self.FileSize = 0
        self.crc32File = 0
        self.blockLock = True

    def otaPercentCal(self):
        try:
            otaPercent = float(self.BlockCnt * self.BlockSize + self.CurrentPackageSize) * 100 / float(
                self.FileSize)
        except ZeroDivisionError:
            otaPercent = 1

        return int(otaPercent)


class DataPointRev:
    def __init__(self, dpid, type, value):
        self.dpid = dpid
        self.type = type
        self.value = value


class DeviceStateChkThread(QThread):
    # 自定义信号，用来发送串口write数据
    DS_uartWrite_sinOut = pyqtSignal(str)

    # 自定义信号，用来发送进度条数据及进度描述
    DS_progressBar_sinOut = pyqtSignal(int, int, str)

    # 自定义信号，用来发送接收到的dp
    DS_dPRevSignal_sinOut = pyqtSignal(DataPointRev)

    # 自定义信号，用来发送dongle版本号
    DS_dongleVersionSignal_sinOut = pyqtSignal(str, str, str)

    # 自定义信号，用来发送握手成功
    DS_shakeHandSignal_sinOut = pyqtSignal()

    pageTypeList = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 4), (5, 5)]

    def __init__(self):
        super(DeviceStateChkThread, self).__init__()
        # 创建串口读到的数据缓冲区
        self.exiting = False
        self.cycleCnt = 0
        self.checkAllDp = 0
        self.readBuf = ''
        # 创建小型状态机，主状态
        self.stateMachine = 'state_dpDisplay'

        # 定义发送互斥量
        self.sendMutexFlag = True

        # 创建sn和 acksn
        self.sn = 0
        self.acksn = 0

        # 创建任务状态机列表
        self.stateList = []

        # 创建列表索引
        self.listIndex = 0

        # 创建测试协议cmd字典
        self.cmdProcessor = {
            bytes.fromhex("0000"): self.cmd_shakeHand,
            bytes.fromhex("0001"): self.cmd_DongleInfo,
            bytes.fromhex("0002"): self.cmd_dataPointSend,
            bytes.fromhex("0003"): self.cmd_chkDataPoint,
            bytes.fromhex("0005"): self.cmd_SerialDisconn,
            bytes.fromhex("000C"): self.cmd_OTAStart,
            bytes.fromhex("000E"): self.cmd_OTAHead,
            bytes.fromhex("000F"): self.cmd_OTATail,
            bytes.fromhex("0011"): self.cmd_OTAExit,
            bytes.fromhex("0012"): self.cmd_OTAState,
            bytes.fromhex("8001"): self.cmd_DpUpdata,
        }

        print("创建 DeviceStateChkThread线程")

    def DS_Send(self, Sn, ackSn, testCmd, testLen, testData=''):
        # 发送数据组包
        # 将整数value转换为4个字节，使用大端字节序
        SnBytes = Sn.to_bytes(4, byteorder='big', signed=False)

        SnBytesStr = f"{int.from_bytes(SnBytes, byteorder='big', signed=False):08}"
        AckSnBytes = ackSn.to_bytes(4, byteorder='big', signed=False)
        AckSnBytesStr = f"{int.from_bytes(AckSnBytes, byteorder='big', signed=False):08}"

        if isinstance(testData, bytes):
            testData = testData.hex()
        dataTmp = "66AA" + SnBytesStr + AckSnBytesStr + testCmd + str(testLen) + testData

        self.sn += 1
        # print("userTestSend", dataTmp, type(dataTmp))
        tmp = BaseUtils.uchar_checksum(dataTmp)
        dataTmp = dataTmp + tmp
        # 发送串口写信号
        self.DS_uartWrite_sinOut.emit(dataTmp)

    def DpListSend(self, DpListStr: str, Interval: int):
        # 发送数据组包
        offset = 0
        DpItemList = ""

        for i in range(0, len(DpListStr)):
            if DpListStr[i] == ",":
                DpItem = DpListStr[offset:i]
                offset = i + 1
                if len(DpItemList) + len(DpItem) < 255:
                    DpItemList += DpItem
                else:
                    DpLen = int(len(DpItemList) / 2)
                    lenStr = DpLen.to_bytes(2, byteorder='big', signed=False).hex()
                    self.DS_Send(self.sn, 0, "0002", lenStr, DpItemList)
                    time.sleep(float(Interval) / 1000)
                    DpItemList = ""

        if DpItemList != "":
            DpLen = int(len(DpItemList) / 2)
            lenStr = DpLen.to_bytes(2, byteorder='big', signed=False).hex()
            self.DS_Send(self.sn, 0, "0002", lenStr, DpItemList)

    def dealDpData(self, data, dataLen) -> bool:
        """
        处理数据
        """
        if dataLen == 0:
            log.logger.debug('dp数据长度异常')
            return False

        dpid = data[0]
        dataType = data[1]

        if dataType > 0x05:
            log.logger.debug('dp数据类型异常')
            return False

        dataValue = data[4:]

        DpRev = DataPointRev(dpid, dataType, dataValue)
        log.logger.debug("Rev Dp Data: %s" % data.hex())
        self.DS_dPRevSignal_sinOut.emit(DpRev)
        return True

    @staticmethod
    def findHead(bytesList: bytes, headfirst, headsecond):

        if len(bytesList) < 2:
            return -1

        for i in range(len(bytesList) - 1):
            if bytesList[i] == headfirst and bytesList[i + 1] == headsecond:
                return i
        return -1

    # 按照帧结构解析处理一条完整的帧数据
    def uartParse(self, data):
        if not data:
            return None

        # print("check uart", data, len(data))
        # log.logger.debug("userTest.processReadBuffer %s ",% self.readBuf.hex())
        log.logger.debug("Rev Dp Data: %s" % data.hex())
        # print("userTest.processReadBuffer", "readBuf", self.readBuf)

        result = True
        remaining_data = data  # 剩余待处理的数据

        while True:
            headIdx = self.findHead(remaining_data, 0x66, 0xAA)  #
            offset = headIdx

            if headIdx < 0:
                # 没有找到更多的起始标志，退出循环
                log.logger.debug("check uart parse not find head")
                break

            # 当索引值大于等于总体数据长度，需要再等多一些字节数据
            if len(remaining_data) < headIdx + 15:
                log.logger.debug("check uart parse wait cnt bytes")
                return False, b''

            # 读取sn号
            self.acksn = (remaining_data[headIdx + Frame.HEAD + Frame.SN] << 24) | \
                         (remaining_data[headIdx + Frame.HEAD + Frame.SN + 1] << 16) | \
                         (remaining_data[headIdx + Frame.HEAD + Frame.SN + 2] << 8) | \
                         remaining_data[headIdx + Frame.HEAD + Frame.SN + 3]

            offset += (Frame.HEAD + Frame.ACK_SN + Frame.SN)
            # 获取2字节功能码
            cmd = remaining_data[offset:offset + Frame.CMD]

            offset += Frame.CMD

            try:
                # 获取数据长度
                dataCnt = (remaining_data[offset] << 8) | remaining_data[offset + 1]
            except:
                log.logger.debug("check uart no cnt info")
                return False, b''

            offset += Frame.DATA_LEN

            # 等待数据帧完整
            if len(remaining_data) < dataCnt + Frame.LEN_EXPDATA:
                log.logger.debug(
                    "check uart parse wait complete %d" % (
                            dataCnt + Frame.LEN_EXPDATA - len(remaining_data)))
                return True, b''

            # 校验数据
            dataCheckSum = remaining_data[offset + dataCnt]
            checkTmp = BaseUtils.uchar_byte_checksum(
                remaining_data[headIdx:offset + dataCnt])

            if dataCheckSum != checkTmp:
                log.logger.debug("check uart data checksum fail!")
                result = False
                break
            else:
                log.logger.debug("check uart data checksum success!")

                # 执行相应指令
                if cmd in self.cmdProcessor:
                    self.cmdProcessor[cmd](
                        remaining_data[offset:offset + dataCnt])
                else:
                    result = False
                    log.logger.error("check uart parse cmd error!")
                    break

                offset += dataCnt + 1

            # 更新remaining_data为当前处理位置之后的数据
            remaining_data = remaining_data[offset:]

        # 返回处理结果和剩余未处理的数据
        return result, b''

    def uartProc(self, data):
        """
        接受串口收到的信息
        """
        # 判断输入data是否有效
        if not data or len(data) == 0:
            return None
        # 追加到数据缓存区，hex字符串拼接
        self.readBuf = self.readBuf + data

        # print("userTest.uartProc", "rdbuf", self.rdbuf)

    def processReadBuffer(self):
        """
        处理读缓冲区中的数据
        """
        if not self.readBuf or len(self.readBuf) == 0:
            return None

        # 将处理的的数据转换成bytes字节串
        unProc = BaseUtils.HexStringToByte(self.readBuf)
        # 根据帧结构循环解析未处理过的数据
        while True:
            res, unProc = self.uartParse(unProc)
            if not unProc or unProc == '' or not res:
                break
        # 已处理完的数据从缓存区去除
        self.readBuf = BaseUtils.asciiB2HexString(unProc) or ''

    def cmd_shakeHand(self, hexx):
        """
        解析握手指令
        """
        if self.stateMachine == MachineState.Waiting:
            self.listIndex = self.listIndex + 1
            self.stateMachine = self.stateList[self.listIndex]
            log.logger.debug("握手成功")

            # 初始化发送互斥标志
            self.sendMutexFlag = True

            self.cycleCnt = 0

        else:
            log.logger.debug('握手命令错误应答，未在对应状态！')

    def cmd_DongleInfo(self, hexx):
        if self.stateMachine == MachineState.CheckVer:

            log.logger.debug("接收到Dongle设备信息")
            try:
                jsonData = json.loads(hexx)
                SoftVer = jsonData.get('SoftwareVersion', '')
                HardVer = jsonData.get('HardwareVersion', '')
                BootloaderVersion = jsonData.get('BootloaderVersion', '')

                self.DS_dongleVersionSignal_sinOut.emit(SoftVer, HardVer, BootloaderVersion)

                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
                # 初始化DP检查标志
                self.checkAllDp = True

                self.cycleCnt = 0

            except Exception as e:
                log.logger.debug("json 解析错误 %s" % e)
                return

            # 初始化发送互斥标志
            self.sendMutexFlag = True


        else:
            log.logger.debug('错误应答，未在对应状态！,current state is %s' % self.stateMachine)

    def cmd_dataPointSend(self, hexx):
        """
        解析数据下发回复
        """
        if self.stateMachine == MachineState.DpDisplay:
            if len(hexx) == 1:
                if hexx[0] == 0x00:
                    log.logger.debug("数据下发成功")
                elif hexx[0] == 0x01:
                    log.logger.debug("dp 点不在设备支持的列表中")
                elif hexx[0] == 0x02:
                    log.logger.debug("dp 类型不符合定义")
                elif hexx[0] == 0x03:
                    log.logger.debug("dp 长度超出限制范围")
                else:
                    log.logger.debug("未知错误")

            else:
                # 数据下发失败
                log.logger.debug("数据长度异常")

            # 初始化发送互斥标志
            self.sendMutexFlag = True

        else:
            log.logger.debug('错误应答，未在对应状态！,current state is %s' % self.stateMachine)

    def cmd_chkDataPoint(self, hexx):
        """
        查询dp点数据回复解析
        """
        if self.stateMachine == MachineState.DpDisplay:
            if len(hexx) == 1:
                if hexx[0] == 0:
                    log.logger.debug("查询dp数据成功")
                elif hexx[0] == 1:
                    log.logger.debug("dp 点不在设备支持的列表中")
                else:
                    log.logger.debug("未知错误")

            else:
                # 数据下发失败
                log.logger.error("数据长度异常")

        else:
            log.logger.debug('错误应答，未在对应状态！current state is %s', self.stateMachine)
            if self.stateMachine != MachineState.OTAStart and self.stateMachine != MachineState.OTABlockSend:
                self.stateMachine = MachineState.DpDisplay

    def cmd_SerialDisconn(self, hexx):
        """
        设备断开回复
        """
        if self.stateMachine == MachineState.DpDisplay:
            self.listIndex = self.listIndex - 1
            self.stateMachine = self.stateList[self.listIndex]
            log.logger.debug("断开连接成功")

            # 初始化发送互斥标志
            self.sendMutexFlag = True

        else:
            log.logger.debug('断开命令错误应答，未在对应状态！')

    def cmd_OTAStart(self, hexx):
        """
        OTA 开始
        """

        if self.stateMachine == MachineState.OTAStart:
            if self.PCB.devType != int(hexx[0]):
                log.logger.debug("设备返回类型不符")
                self.UpdateProcessState('返回设备类型不符', OTAState.Fail)
                return

            if VER_PROTOCAL != int(hexx[1]):
                log.logger.debug("设备返回OTA协议版本不符")
                self.UpdateProcessState('设备返回OTA协议版本不符', OTAState.Fail)
                return

            if int(hexx[2]) != 0x00:
                log.logger.debug('设备拒绝升级！')
                self.UpdateProcessState('设备拒绝升级', OTAState.Fail)
                return

            self.listIndex = self.listIndex + 1
            self.stateMachine = self.stateList[self.listIndex]
            # 初始化发送互斥标志
            self.sendMutexFlag = True
        else:
            log.logger.debug('OTA开始命令错误应答，未在对应状态！ %s' % hexx.hex())

    def cmd_OTAHead(self, hexx):
        """
        OTA 传输包头
        """
        if self.stateMachine == MachineState.OTABlockSend:
            if len(hexx) == 1:
                if hexx[0] == 0x00:
                    self.PCB.blockLock = False
                elif hexx[0] == 0xA0:
                    self.UpdateProcessState('包数异常', OTAState.Fail)
                elif hexx[0] == 0xA1:
                    self.UpdateProcessState('包数据长度异常', OTAState.Fail)
                else:
                    self.UpdateProcessState('未知错误', OTAState.Fail)

            else:
                # OTA包头下发失败
                log.logger.error("帧长度异常")

            self.sendMutexFlag = True
        else:
            log.logger.debug('OTA 包头命令错误应答，未在对应状态！ %s' % hexx)

    def cmd_OTATail(self, hexx):
        """
        OTA 传输包尾
        """
        if self.stateMachine == MachineState.OTABlockSend:
            if len(hexx) == 1:
                if hexx[0] == 0x00:
                    self.PCB.blockLock = False
                elif hexx[0] == 0xA0:
                    self.UpdateProcessState('包数异常', OTAState.Fail)
                elif hexx[0] == 0xA1:
                    self.UpdateProcessState('实际接收到的数据长度与包头中数据长度不符合', OTAState.Fail)
                elif hexx[0] == 0xA2:
                    self.UpdateProcessState('包校验异常', OTAState.Fail)
                else:
                    self.UpdateProcessState('未知错误', OTAState.Fail)

            else:
                # OTA包头下发失败
                log.logger.error("块尾帧数据长度异常")

            # 初始化发送互斥标志位
            self.sendMutexFlag = True
        else:
            log.logger.debug('OTA 包头命令错误应答，未在对应状态！ %s' % hexx)

    def cmd_OTAExit(self, hexx):
        """
        退出 OTA
        """
        if self.stateMachine == MachineState.OTABlockSend:
            if len(hexx) == 2:
                if int(hexx[0]) != self.PCB.devType:
                    log.logger.debug("返回设备类型不符")

                if hexx[1] == 0x00:
                    log.logger.debug("OTA 退出成功")
                    self.PCB.otaExit = True

                elif hexx[1] == 0x02:
                    log.logger.debug("数据总长度错误")
                    self.UpdateProcessState('数据总长度错误', OTAState.Fail)
                elif hexx[1] == 0x03:
                    log.logger.debug("数据总crc校验失败")
                    self.UpdateProcessState('数据总crc校验失败', OTAState.Fail)
                elif hexx[1] == 0x04:
                    log.logger.debug("设备回复超时")
                    self.UpdateProcessState('设备回复超时', OTAState.Fail)
                elif hexx[1] == 0x05:
                    log.logger.debug("设备类型出错")
                    self.UpdateProcessState('设备类型出错', OTAState.Fail)
                elif hexx[1] == 0xFF:
                    log.logger.debug("OTA 退出失败")
                else:
                    log.logger.debug("未知错误")

                self.stateMachine = MachineState.DpDisplay

                for i in range(len(self.stateList)):
                    if self.stateList[i] == self.stateMachine:
                        self.listIndex = i

            else:
                # OTA包头下发失败
                log.logger.error("块尾数据长度异常")

            # 初始化发送互斥标志位
            self.sendMutexFlag = True

        else:
            log.logger.debug('OTA 包头命令错误应答，未在对应状态！ %s' % hexx)

    def cmd_OTAState(self, hexx):
        if MachineState.OTABlockSend == self.stateMachine or MachineState.OTAStart == self.stateMachine:
            if len(hexx) != 2:
                if hexx[0] == 0x00:
                    log.logger.debug('设备主动退出 OTA 升级')
                    self.UpdateProcessState('设备主动退出 OTA 升级', OTAState.Fail)
                elif hexx[0] == 0x01:
                    log.logger.debug('OTA 升级失败，未在对应状态！ %s' % hexx[1])
                    errorCode = hexx[1].hex()
                    self.UpdateProcessState('OTA 升级失败,原因： %s' % errorCode, OTAState.Fail)
                elif hexx[0] == 0x02:
                    pass
                elif hexx[0] == 0x03:
                    self.PCB.OTAState = OTAState.Success
                    log.logger.debug('OTA 完成')
                elif hexx[0] == 0x04:
                    revDataPercent = hexx[1]
                    log.logger.debug('OTA 设备已接收 %d %%' % revDataPercent)
                    if revDataPercent == 100:
                        self.PCB.OTAState = OTAState.Success

            else:
                log.logger.debug('OTA 状态数据长度错误')
        else:
            log.logger.debug('OTA 状态错误上报，未在对应状态！ %s' % hexx)

    def cmd_DpUpdata(self, hexx):
        """
        dp 点数据更新
        """
        offset = 0
        if self.stateMachine == MachineState.DpDisplay:
            while offset < len(hexx):
                dpLen = hexx[offset + 2] * 0x100 + hexx[offset + 3]
                state = self.dealDpData(hexx[offset:offset + 4 + dpLen], dpLen)

                if state:
                    offset = offset + dpLen + 4
                else:
                    break

        else:
            log.logger.debug('错误应答，未在对应状态！')
            if self.stateMachine != MachineState.OTAStart and self.stateMachine != MachineState.OTABlockSend:
                self.stateMachine = MachineState.DpDisplay

    def onStartOTA(self, path, devType):
        protocolDeviceType = -1

        # 获取协议类型
        for i in range(len(self.pageTypeList)):
            if devType == self.pageTypeList[i][0]:
                protocolDeviceType = self.pageTypeList[i][1]
        if protocolDeviceType == -1:
            log.logger.debug('设备类型错误')
            return
        fileSize, crc32 = BaseUtils.calculate_file_info(path)

        # 初始化 PCB
        log.logger.debug("升级文件地址： %s" % path)
        self.PCB = OTA_PCB(path, protocolDeviceType, fileSize, crc32, 0)

        # 初始化发送互斥标志位
        self.sendMutexFlag = True
        self.UpdateProcessState('等待升级', OTAState.GoOn, 0)
        # 进入 OTA 状态

        self.stateMachine = MachineState.OTAStart

        for i in range(len(self.stateList)):
            if self.stateList[i] == self.stateMachine:
                self.listIndex = i
                break

    def doStopOTA(self, goBackState):
        devTypeStr = self.PCB.devType.to_bytes(1, byteorder='big', signed=False).hex()
        # 发送退出OTA命令
        self.DS_Send(self.sn, 0, "0011", '0001', devTypeStr)

        self.PCB.onOVER()
        self.stateMachine = goBackState
        self.sendMutexFlag = True
        self.cycleCnt = 0

        for i in range(len(self.stateList)):
            if self.stateList[i] == self.stateMachine:
                self.listIndex = i
                break

    def onSharkOverTime(self):
        self.cycleCnt = 0
        self.DS_shakeHandSignal_sinOut.emit()
        log.logger.info('握手超时！')

    def UpdateProcessState(self, str, state: OTAState, percent=0):

        if state == OTAState.Fail or state == OTAState.UserExit:
            self.doStopOTA(MachineState.DpDisplay)
            percent = 0

        if state == OTAState.TransDataComplete:
            # 发送退出OTA命令
            devTypeStr = self.PCB.devType.to_bytes(1, byteorder='big', signed=False).hex()
            self.DS_Send(self.sn, 0, "0011", '0001', devTypeStr)
            percent = 100

        if state == OTAState.Success:
            self.doStopOTA(MachineState.Waiting)
            percent = 100

        self.DS_progressBar_sinOut.emit(percent, state, str)

    def sendBlockHead(self, blockSize, blockCnt):
        """
        发送块头
        """
        blockCntBytes = blockCnt.to_bytes(4, byteorder='big', signed=False)
        blockSizeBytes = blockSize.to_bytes(2, byteorder='big', signed=False)

        self.DS_Send(self.sn, 0, "000E", '0006', blockCntBytes + blockSizeBytes)

        self.PCB.blockLock = True

    def sendBlockTail(self, blockCnt, crc16):
        """
        发送块尾
        """
        crc16Bytes = crc16.to_bytes(2, byteorder='big', signed=False)
        blockCntBytes = blockCnt.to_bytes(4, byteorder='big', signed=False)

        self.DS_Send(self.sn, 0, "000F", '0006', blockCntBytes + crc16Bytes)

        self.PCB.blockLock = True

    def sendBlockData(self, dataLen, data):
        """
        发送块数据
        """
        pkgCntBytes = dataLen.to_bytes(2, byteorder='big', signed=False).hex()
        self.DS_Send(self.sn, 0, "000E", pkgCntBytes, data)

    def processData(self):
        while True:
            self.processReadBuffer()
            time.sleep(0.01)

    def send_query_dp(self, dpList=[]):
        if len(dpList) == 0:
            self.DS_Send(self.sn, 0, "0003", '0000')
        else:
            dpListLen = len(dpList).to_bytes(2, byteorder='big', signed=False).hex()
            dpListBytes = ''
            for i in range(len(dpList)):
                dpListBytes += dpList[i].to_bytes(1, byteorder='big', signed=False).hex()
            self.DS_Send(self.sn, 0, "0003", dpListLen, dpListBytes)

    def run(self):

        self.stateList.append(MachineState.Waiting)
        self.stateList.append(MachineState.CheckVer)
        self.stateList.append(MachineState.DpDisplay)
        self.stateList.append(MachineState.OTAStart)
        self.stateList.append(MachineState.OTABlockSend)
        # 初始状态
        self.stateMachine = self.stateList[self.listIndex]

        self.ProcessTask = threading.Thread(target=self.processData)
        self.ProcessTask.start()

        while not self.exiting:
            if self.stateMachine == MachineState.Waiting:
                # 握手模式
                self.DS_Send(self.sn, 0, "0000", '0000')

                # 超时
                self.cycleCnt = self.cycleCnt + 1
                if self.cycleCnt == 300:
                    self.onSharkOverTime()
                # 等待100ms
                time.sleep(0.2)

            elif self.stateMachine == MachineState.CheckVer:
                # 版本号查询
                self.DS_Send(self.sn, 0, "0001", '0000')

                # 超时
                self.cycleCnt = self.cycleCnt + 1
                if self.cycleCnt == 3:
                    self.onSharkOverTime()
                # 等待100ms
                time.sleep(0.2)

            elif self.stateMachine == MachineState.DpDisplay:
                # DP 模式
                if self.checkAllDp and self.sendMutexFlag:
                    self.checkAllDp = False
                    self.sendMutexFlag = False
                    # self.send_query_dp()

                # 等待100ms
                time.sleep(0.1)

            elif self.stateMachine == MachineState.OTAStart:
                # OTA 开始
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    devType = self.PCB.devType.to_bytes(1, byteorder='big', signed=False)
                    fileLen = self.PCB.FileSize.to_bytes(4, byteorder='big', signed=False)
                    fileCrc = self.PCB.crc32File.to_bytes(4, byteorder='big', signed=False)

                    self.DS_Send(self.sn, 0, "000C", '0009', devType + fileLen + fileCrc)

                # 超时
                self.cycleCnt = self.cycleCnt + 1
                if self.exiting:
                    self.UpdateProcessState("设备连接断开", OTAState.Fail)

                if self.PCB.OTAState == OTAState.UserExit:
                    self.UpdateProcessState("用户取消升级", OTAState.UserExit)

                if self.cycleCnt == 30:
                    self.UpdateProcessState('目标设备未进入升级状态', OTAState.Fail)

                # 等待200ms
                time.sleep(0.2)

            elif self.stateMachine == MachineState.OTABlockSend:
                # OTA 块头
                """切分bin文件并通过串口发送"""
                self.otaSendDataTask()

            # 处理串口数据
            # self.processReadBuffer()

    def otaStop(self):
        self.PCB.OTAState = OTAState.UserExit

    def otaStateChk(self) -> bool:

        if self.PCB.OTAState == OTAState.Fail:
            self.UpdateProcessState("升级失败", OTAState.Fail)
            return False
        elif self.PCB.OTAState == OTAState.UserExit:
            self.UpdateProcessState("用户取消升级", OTAState.UserExit)
            return False

        elif self.PCB.OTAState == OTAState.Success:
            self.UpdateProcessState("设备升级成功", OTAState.Success)
            return False

        elif self.PCB.OTAState == OTAState.OverTime:
            self.UpdateProcessState("设备超时回复", OTAState.OverTime)
            return False
        elif self.exiting:
            self.UpdateProcessState('连接断开', OTAState.Fail)
            return False

        return True

    def otaSendDataTask(self):
        # 发送数据块头
        offset = 0
        PkgIdx = 1  # 包计数，取值范围1~255 循环计数
        try:
            with open(self.PCB.FilePath, 'rb') as file:
                while chunk := file.read(self.PCB.BlockSize):

                    # 发送数据块头
                    BlockLen = len(chunk)
                    crc16Cal = calc_crc16_modbus(chunk)
                    self.sendBlockHead(BlockLen, self.PCB.BlockCnt)

                    # 等待10s
                    while self.PCB.blockLock:
                        time.sleep(0.1)  # 根据实际情况调整
                        if self.cycleCnt >= 100:
                            self.PCB.OTAState = OTAState.OverTime
                            break
                        self.cycleCnt += 1
                        if self.exiting:
                            break
                        if not self.otaStateChk():
                            break

                    if not self.otaStateChk():
                        break
                    self.cycleCnt = 0

                    BlockLen = len(chunk)
                    pkgCnt = int(BlockLen / 512)
                    pkg_last = BlockLen % 512
                    pkgCurrCnt = 0

                    if BlockLen < 4096:
                        log.logger.debug("最后一包数据，长度为%d", BlockLen)

                    # 发送数据块
                    while offset < BlockLen:
                        PkgIdxByte = PkgIdx.to_bytes(1, byteorder='big', signed=False)
                        if pkgCnt > pkgCurrCnt:
                            self.DS_Send(self.sn, 0, "0010", '0201', PkgIdxByte + chunk[offset:offset + 512])
                            offset = offset + 512
                            pkgCurrCnt += 1
                        else:
                            pkgCntBytes = (pkg_last + 1).to_bytes(2, byteorder='big', signed=False).hex()
                            self.DS_Send(self.sn, 0, "0010", pkgCntBytes, PkgIdxByte + chunk[offset:offset + pkg_last])
                            offset = offset + pkg_last
                            self.PCB.PkgCnt = 0
                        time.sleep(0.1)  # 根据实际情况调整

                        if PkgIdx == 255:
                            PkgIdx = 1
                        else:
                            PkgIdx += 1

                        self.PCB.CurrentPackageSize = offset
                        if not self.otaStateChk():
                            break
                        else:
                            self.UpdateProcessState('升级中', OTAState.GoOn, self.PCB.otaPercentCal())

                    # 发送块尾
                    self.sendBlockTail(self.PCB.BlockCnt, crc16Cal)
                    if self.PCB.CurrentPackageSize == self.PCB.BlockSize:
                        self.PCB.BlockCnt = self.PCB.BlockCnt + 1
                    offset = 0

                    # 等待10s
                    while self.PCB.blockLock:
                        time.sleep(0.1)  # 根据实际情况调整
                        if self.cycleCnt >= 100:
                            self.PCB.OTAState = OTAState.OverTime
                            break
                        self.cycleCnt += 1
                        if self.exiting:
                            break
                        if not self.otaStateChk():
                            break

                    if not self.otaStateChk():
                        break

                    self.cycleCnt = 0
                    # if BlockLen < 4096:
                    #     log.logger.debug("升级完成")
                    # 判断是否完成
                    if self.PCB.otaPercentCal() == 100:

                        self.UpdateProcessState('文件传输完成，等待校验', OTAState.TransDataComplete)

                        while not self.PCB.otaExit:
                            time.sleep(0.2)  # 根据实际情况调整
                            if self.cycleCnt >= 500:
                                self.PCB.OTAState = OTAState.OverTime
                                break
                            self.cycleCnt += 1
                            if self.exiting:
                                break
                            if not self.otaStateChk():
                                break

                        if self.cycleCnt < 100:
                            self.UpdateProcessState('设备升级完成', OTAState.Success)
                            time.sleep(6)
                        else:
                            self.UpdateProcessState('设备回复超时', OTAState.OverTime)

                    self.cycleCnt = 0

        except Exception as e:
            self.UpdateProcessState(f'升级失败: {str(e)}', OTAState.Fail)

    def stop(self):
        self.exiting = True
        self.quit()
        self.wait()
