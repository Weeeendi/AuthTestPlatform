import binascii
import csv
import os
import re
import sys
from datetime import datetime

import pandas as pd


class BaseUtils:

    # ascii码转hex字符串
    def asciiB2HexString(self, strB):
        # 判断输入strB是否有效
        if not strB or len(strB) == 0:
            return False

        strHex = binascii.b2a_hex(strB).upper()
        # print("baseUtils.asciiB2HexString", strHex, type(strHex))
        return re.sub(r"(?<=\w)(?=(?:\w\w)+$)", "", strHex.decode())

    # hex字符串转ascii码
    def hexStringB2Hex(self, hexString):
        dataList = hexString.split(" ")
        j = 0
        for i in dataList:
            if len(i) > 2:
                return -1
            elif len(i) == 1:
                dataList[j] = "0" + i
            j += 1
        data = "".join(dataList)
        try:
            data = bytes.fromhex(data)
        except Exception as e:
            print(e)
            return -1
        # print(data)
        return data

    # 累加无符号hex字符串，返回hex字符串
    def uchar_checksum(self, data):

        checksum = 0
        # 转换为16进制数据
        tmp = bytearray.fromhex(data)
        # print(tmp, type(tmp), len(tmp))

        for i in range(0, len(tmp)):
            checksum += tmp[i]
            checksum &= 0xFF   # 强制截断，保留低8位
        # print(checksum)

        strHex = "%02x" % checksum

        return strHex.upper()

    # 累加无符号字节串，返回低8位累加和，bytes类型
    def uchar_byte_checksum(self, data):

        checksum = 0

        for i in range(0, len(data)):
            checksum += data[i]
            checksum &= 0xFF   # 强制截断，保留低8位
        # print(checksum)
        return checksum

    # 转换一段字节串为hex字符串，
    def byteToHexString(self, bins, spaceFlag=True):
        # 判断输入bins是否有效
        if not bins or len(bins) == 0:
            return None

        # 默认hex字符串是通过空格分隔的，如果不需要，则传入实参False
        if spaceFlag:
            return ''.join(["%02X" % x+" " for x in bins]).strip()
        else:
            return ''.join(["%02X" % x for x in bins]).strip()

    # 转换一段hex字符串为一段字节串
    def HexStringToByte(self, hexStr):
        # 判断输入hexStr是否有效
        if not hexStr or len(hexStr) == 0:
            return None

        return bytes.fromhex(hexStr)

    # str to bytes,    "example"  --->  b"example"
    def StrToBytes(self, sStr):
        # 判断输入sStr是否有效
        if not sStr or len(sStr) == 0:
            return None

        return bytes(sStr, encoding="utf8")

    # bytes to str,    b"example"  --->  "example"
    def BytesToStr(self, bBytes):
        # 判断输入bBytes是否有效
        if not bBytes or len(bBytes) == 0:
            return None

        return str(bBytes, encoding="utf8")

    def resource_path(self, relative_path):
        """获取程序中所需文件资源的绝对路径"""
        try:
            # PyInstaller创建临时文件夹,将路径存储于_MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    # 将生成的授权信息记录到regList列表
    def addToRegList(self, regInfo):

        # repFlag = False
        # 获取当前时间
        current_time = datetime.now().date()
        # 格式化日期戳
        datestamp = current_time.strftime("%Y%m%d")
        RecordFilePath = 'resource/regList_'+datestamp+'.csv'

        try:
            # 尝试读文件
            # 使用with来处理上下文，可以在读/写完成后自动关闭文件
            with open(RecordFilePath, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)

            # 写文件
            with open(RecordFilePath, 'a', newline='') as csvfile:
                fieldnames = ['TIME', 'PID', 'DID', 'DSECRET', 'MAC', 'ICCID', 'IMEI', 'TEST_FLASH', 'TEST_GSENSOR',
                              'VOLT', 'SUBVOLT', 'TEST_ADC', 'CSQ', 'TEST_4G', 'GPSNUM', 'TEST_GPS', 'TIME_CONS(s)']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writerow(regInfo)

            print('记录成功！')

        except Exception as e:
            print(e)
            print('没有发现regList,重新生成regList！')

            with open(RecordFilePath, 'a', newline='') as csvfile:
                fieldnames = ['TIME', 'PID', 'DID', 'DSECRET', 'MAC', 'ICCID', 'IMEI', 'TEST_FLASH', 'TEST_GSENSOR',
                              'VOLT', 'SUBVOLT', 'TEST_ADC', 'CSQ', 'TEST_4G', 'GPSNUM', 'TEST_GPS', 'TIME_CONS(s)']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # 重新生成的表格需要填写表格头
                writer.writeheader()
                writer.writerow(regInfo)

        data = pd.read_csv(RecordFilePath)
        data.drop_duplicates(subset=['DID'], keep='last', inplace=True)
        data.to_csv(RecordFilePath, index=False)


