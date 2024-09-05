import json
import threading
import time
from enum import Enum

from PyQt5.QtCore import QThread, pyqtSignal

from baseLogger import log
from baseUtils import BaseUtils


class MachineState(Enum):
    Waiting = 1
    DpDisplay = 2
    OTAStart = 3
    OTABlockSend = 4


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
    Success = 3
    UserExit = 4
    OverTime = 5


def calc_crc16(data: bytes, poly: int = 0x1021) -> int:
    """
    Calculate the CRC16-modbus checksum value.

    This function calculates the CRC16-modbus checksum value for the given data.

    Args:
        data (bytes): The data to calculate the checksum for.
        poly (int, optional): The polynomial to use. Defaults to 0x1021.

    Returns:
        int: The calculated checksum value.
    """
    crc = 0x0000
    # Iterate over each byte in the data
    for b in data:
        # XOR the current byte with the current CRC value
        crc ^= (b << 8)
        # Iterate 8 times to process each bit in the current byte
        for _ in range(8):
            # If the current bit is 1, XOR the CRC value with the polynomial
            if crc & 0x8000:
                crc = (crc << 1) ^ poly
            # If the current bit is 0, just shift the CRC value
            else:
                crc = crc << 1
            # Ensure crc remains in 16-bit
            crc &= 0xFFFF

    # Perform two more iterations to finalize the CRC value
    crc = (crc << 1) ^ poly
    crc = (crc << 1) & 0xFFFF  # Ensure crc remains in 16-bit
    return crc


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

    # 按照帧结构解析处理一条完整的帧数据
    def uartParse(self, data):
        IndexCnt = 0
        # 判断输入data是否有效
        if not data:
            return None
        # 打印即将处理的数据
        print("check uart", data, len(data))
        #log.logger.debug("userTest.uartParse", str(data), len(data))
        # 打印更新后的缓存区数据
        print("userTest.processReadBuffer", "readBuf", self.readBuf)

        # 判断起始标志
        headIdx = data.find(bytes.fromhex("66AA"))

        IndexCnt += (Frame.HEAD + Frame.SN)
        # print("userTest.uartParse", "headidx", headidx)
        # 如果没有找到起始标志，返回等待数据完整
        if headIdx < 0:
            log.logger.debug("check uart parse no head error")
            return False, b''

        # 当索引值大于等于总体数据长度，需要再等多一些字节数据
        if len(data) <= headIdx + IndexCnt:
            log.logger.debug("check uart parse wait cnt bytes")
            return False, data

        # 读取sn号
        self.acksn = data[headIdx + IndexCnt] * pow(2, 16) + data[headIdx + IndexCnt + 1] * pow(2, 12) + \
                     data[headIdx + IndexCnt + 2] * pow(2, 8) + data[headIdx + IndexCnt + 3]

        IndexCnt += Frame.ACK_SN
        # 获取2字节功能码
        cmd = data[headIdx + IndexCnt:headIdx + IndexCnt + Frame.CMD]
        IndexCnt += Frame.CMD
        # 可能存在断包情况，获取不到cnt信息
        try:
            # 获取数据长度
            dataCnt = data[headIdx + IndexCnt] * 256 + data[headIdx + IndexCnt + 1]
            print("check uart", "cnt", dataCnt)
        except:
            log.logger.debug("check uart no cnt info")
            return False, b''

        # 等待数据帧完整
        if len(data) < headIdx + dataCnt + Frame.LEN_EXPDATA:
            log.logger.debug(
                "check uart parse wait complete %d" % (headIdx + dataCnt + Frame.LEN_EXPDATA - len(data)))
            return True, b''

        # 校验数据
        dataCheckSum = data[headIdx + dataCnt + Frame.DATA_START]
        checkTmp = BaseUtils.uchar_byte_checksum(data[headIdx:headIdx + dataCnt + Frame.DATA_START])
        # 如果校验失败
        if dataCheckSum != checkTmp:
            log.logger.debug("check uart data checksum fail!")
            return False, data[headIdx + dataCnt + Frame.LEN_EXPDATA:]

        # 校验成功，执行命令代码
        log.logger.debug("check uart data checksum success!")

        # 可能存在没有相应指令函数，则报错退出
        try:
            # 执行相应指令
            if dataCnt:
                self.cmdProcessor[cmd](data[headIdx + Frame.DATA_START:headIdx + Frame.DATA_START + dataCnt])

            else:
                self.cmdProcessor[cmd]()

        except KeyError:
            # print("userTest.uartParse", "parse cmd error", cmd)
            log.logger.error("check uart parse cmd error!")
            return False, data[headIdx + Frame.DATA_START + dataCnt:]

        # 正确处理完一条信息，正常返回
        return True, data[headIdx + dataCnt + Frame.LEN_EXPDATA + 1:]

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

    def cmd_shakeHand(self):
        """
        解析握手指令
        """
        if self.stateMachine == MachineState.Waiting:
            self.listIndex = self.listIndex + 1
            self.stateMachine = self.stateList[self.listIndex]
            log.logger.debug("握手成功")

            # 初始化DP检查标志
            self.checkAllDp = True
            # 初始化发送互斥标志
            self.sendMutexFlag = True

        else:
            log.logger.debug('握手命令错误应答，未在对应状态！')

    def cmd_DongleInfo(self, hexx):
        if self.stateMachine == MachineState.DpDisplay:
            log.logger.debug("接收到Dongle设备信息")
            try:
                jsonData = json.loads(hexx)
                SoftVer = jsonData['SoftwareVersion']
                HardVer = jsonData['HardwareVersion']
                BootloaderVersion = jsonData['HardwareVersion']

                self.DS_dongleVersionSignal_sinOut.emit(SoftVer, HardVer, BootloaderVersion)

            except Exception as e:
                log.logger.debug("json 解析错误 %s" % e)
                return

        else:
            log.logger.debug('错误应答，未在对应状态！')

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
            log.logger.debug('错误应答，未在对应状态！')

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
            log.logger.debug('错误应答，未在对应状态！')

    def cmd_SerialDisconn(self):
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
            if int(hexx[0]) == 0 and self.PCB.devType == int(hexx[1]):
                self.listIndex = self.listIndex + 1
                self.stateMachine = self.stateList[self.listIndex]
            else:
                log.logger.debug('设备拒绝升级或者返回设备类型不符！')
                self.UpdateProcessState('设备拒绝升级或者返回设备类型不符', OTAState.Fail)

            # 初始化发送互斥标志
            self.sendMutexFlag = True
        else:
            log.logger.debug('OTA开始命令错误应答，未在对应状态！ %s' % hexx.hex())

    def cmd_OTAHead(self, hexx):
        """
        OTA 传输包头
        """
        if self.stateMachine == MachineState.OTAStart:
            if len(hexx) == 1:
                if hexx[0] == 0x55:
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
        if self.stateMachine == MachineState.OTAStart:
            if len(hexx) == 1:
                if hexx[0] == 0x55:
                    self.PCB.blockLock = False
                elif hexx[0] == 0xA0:
                    self.UpdateProcessState('包数异常', OTAState.Fail)
                elif hexx[0] == 0xA1:
                    self.UpdateProcessState('实际接收到的数据长度与包头中数据长度不符合', OTAState.Fail)
                elif hexx[0] == 0xA2:
                    self.UpdateProcessState('校验码异常', OTAState.Fail)
                elif hexx[0] == 0xA6:
                    self.UpdateProcessState('硬件校验异常', OTAState.Fail)
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
                else:
                    log.logger.debug("OTA 退出失败")

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
        if MachineState.OTABlockTail >= self.stateMachine >= MachineState.OTAStart:
            if len(hexx) != 5:
                if hexx[0] == 0x00:
                    log.logger.debug('设备主动退出 OTA 升级')
                    self.UpdateProcessState('设备主动退出 OTA 升级', OTAState.Fail)
                elif hexx[0] == 0x01:
                    log.logger.debug('OTA 升级失败，未在对应状态！ %s' % hexx[4])
                    errorCode = hexx[4].hex()
                    self.UpdateProcessState('OTA 升级失败,原因： %s' % errorCode, OTAState.Fail)
                elif hexx[0] == 0x02:
                    pass
                elif hexx[0] == 0x03:
                    self.PCB.OTAState = OTAState.Success
                    log.logger.debug('OTA 完成')
                elif hexx[0] == 0x04:
                    revDataLen = hexx[1] * 0x1000000 + hexx[2] * 0x10000 + hexx[3] * 0x100 + hexx[4]
                    log.logger.debug('OTA 已接收字节 %d' % revDataLen)

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

    def doStopOTA(self):
        devTypeStr = self.PCB.devType.to_bytes(1, byteorder='big', signed=False).hex()
        # 发送退出OTA命令
        self.DS_Send(self.sn, 0, "0011", '0001', devTypeStr)

        self.PCB.onOVER()
        self.stateMachine = MachineState.DpDisplay
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

        if state != OTAState.GoOn:
            self.doStopOTA()
            percent = 0
            state = OTAState.Fail
        self.DS_progressBar_sinOut.emit(percent, state, str)

    def sendBlockHead(self, blockSize, blockCnt):
        """
        发送块头
        """
        blockCntBytes = blockCnt.to_bytes(4, byteorder='big', signed=False)
        blockSizeBytes = blockSize.to_bytes(2, byteorder='big', signed=False)

        self.DS_Send(self.sn, 0, "000D", '0006', blockCntBytes + blockSizeBytes)

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
            time.sleep(0.1)

    def run(self):

        self.stateList.append(MachineState.Waiting)
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
                if self.cycleCnt == 10:
                    self.onSharkOverTime()
                # 等待100ms
                time.sleep(0.1)

            elif self.stateMachine == MachineState.DpDisplay:
                # DP 模式
                if self.checkAllDp and self.sendMutexFlag:
                    self.checkAllDp = False
                    self.sendMutexFlag = False
                    self.DS_Send(self.sn, 0, "0003", '0000')

                # 等待100ms
                time.sleep(0.1)

            elif self.stateMachine == MachineState.OTAStart:
                # OTA 开始
                if self.sendMutexFlag:
                    self.sendMutexFlag = False
                    devTypeStr = self.PCB.devType.to_bytes(1, byteorder='big', signed=False).hex()
                    self.DS_Send(self.sn, 0, "000C", '0001', devTypeStr)

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
        elif self.PCB.OTAState == OTAState.Success:
            self.UpdateProcessState("升级成功", OTAState.Success)
            return False
        elif self.PCB.OTAState == OTAState.OverTime:
            self.UpdateProcessState("设备超时回复", OTAState.OverTime)
            return False
        elif self.exiting:
            self.UpdateProcessState('设备断开', OTAState.Fail)
            return False

        return True

    def otaSendDataTask(self):
        # 发送数据块头
        offset = 0
        try:
            with open(self.PCB.FilePath, 'rb') as file:
                while chunk := file.read(self.PCB.BlockSize):

                    # 发送数据块头
                    BlockLen = len(chunk)

                    crc16Cal = calc_crc16(chunk)
                    self.sendBlockHead(BlockLen, self.PCB.BlockCnt)

                    # 等待1000ms
                    while self.PCB.blockLock:
                        time.sleep(0.01)  # 根据实际情况调整
                        if self.cycleCnt >= 100:
                            self.PCB.OTAState = OTAState.OverTime
                            break
                        self.cycleCnt += 1
                        if self.exiting:
                            break

                    if not self.otaStateChk():
                        break
                    self.cycleCnt = 0

                    BlockLen = len(chunk)
                    pkgCnt = int(BlockLen / 512)
                    pkg_last = BlockLen % 512
                    pkgCurrCnt = 0

                    # 发送数据块
                    while offset < BlockLen:
                        if pkgCnt > pkgCurrCnt:
                            self.DS_Send(self.sn, 0, "000E", '0400', chunk[offset:offset + 512])
                            offset = offset + 512
                            pkgCurrCnt += 1
                        else:
                            pkgCntBytes = pkg_last.to_bytes(2, byteorder='big', signed=False).hex()
                            self.DS_Send(self.sn, 0, "000E", pkgCntBytes, chunk[offset:offset + pkg_last])
                            offset = offset + pkg_last
                            self.PCB.PkgCnt = 0
                        time.sleep(0.02)  # 根据实际情况调整
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

                    # 等待1000ms
                    while self.PCB.blockLock:
                        time.sleep(0.01)  # 根据实际情况调整
                        if self.cycleCnt >= 100:
                            self.PCB.OTAState = OTAState.OverTime
                            break
                        self.cycleCnt += 1
                        if self.exiting:
                            break

                    if not self.otaStateChk():
                        break

                    self.cycleCnt = 0
                    # if BlockLen < 4096:
                    #     log.logger.debug("升级完成")
                    # 判断是否完成
                    if self.PCB.otaPercentCal() == 100 or self.PCB.OTAState == OTAState.Success:
                        self.UpdateProcessState('设备升级完成', OTAState.Success)

        except Exception as e:
            self.UpdateProcessState(f'升级失败: {str(e)}', OTAState.Fail)

    def stop(self):
        self.exiting = True
        self.quit()
        self.wait()
