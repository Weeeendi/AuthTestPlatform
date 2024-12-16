import binascii
import csv
import os
import re
import sys
import zlib
from datetime import datetime

import chardet
import pandas as pd


def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not running in PyInstaller, use the actual path
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class BaseUtils:

    # ascii码转hex字符串
    @staticmethod
    def asciiB2HexString(strB):
        # 判断输入strB是否有效
        if not strB or len(strB) == 0:
            return False

        strHex = binascii.b2a_hex(strB).upper()
        # print("baseUtils.asciiB2HexString", strHex, type(strHex))
        return re.sub(r"(?<=\w)(?=(?:\w\w)+$)", "", strHex.decode())

    # hex字符串转ascii码
    @staticmethod
    def hexStringB2Hex(hexString):
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
    @staticmethod
    def uchar_checksum(data):

        checksum = 0
        # 转换为16进制数据
        tmp = bytearray.fromhex(data)
        # print(tmp, type(tmp), len(tmp))

        for i in range(0, len(tmp)):
            checksum += tmp[i]
            checksum &= 0xFF  # 强制截断，保留低8位
        # print(checksum)

        strHex = "%02x" % checksum

        return strHex.upper()

    @staticmethod
    def calculate_file_info(file_path):
        total_size = os.path.getsize(file_path)
        crc = 0
        with open(file_path, 'rb') as file:
            while chunk := file.read(4096):  # 读取文件的一部分
                crc = zlib.crc32(chunk, crc)
        return total_size, crc & 0xFFFFFFFF  # CRC32返回一个有符号整数，可能需要转换

    # 累加无符号字节串，返回低8位累加和，bytes类型
    @staticmethod
    def uchar_byte_checksum(data):

        checksum = 0

        for i in range(0, len(data)):
            checksum += data[i]
            checksum &= 0xFF  # 强制截断，保留低8位
        # print(checksum)
        return checksum

    # 转换一段字节串为hex字符串，
    @staticmethod
    def byteToHexString(bins, spaceFlag=True):
        # 判断输入bins是否有效
        if not bins or len(bins) == 0:
            return None

        # 默认hex字符串是通过空格分隔的，如果不需要，则传入实参False
        if spaceFlag:
            return ''.join(["%02X" % x + " " for x in bins]).strip()
        else:
            return ''.join(["%02X" % x for x in bins]).strip()

    # 转换一段hex字符串为一段字节串
    @staticmethod
    def HexStringToByte(hexStr):
        # 判断输入hexStr是否有效
        if not hexStr or len(hexStr) == 0:
            return None

        return bytes.fromhex(hexStr)

    # str to bytes,    "example"  --->  b"example"
    @staticmethod
    def StrToBytes(sStr):
        # 判断输入sStr是否有效
        if not sStr or len(sStr) == 0:
            return None

        return bytes(sStr, encoding="utf8")

    # bytes to str,    b"example"  --->  "example"
    @staticmethod
    def BytesToStr(bBytes):
        # 判断输入bBytes是否有效
        if not bBytes or len(bBytes) == 0:
            return None
        try:
            return str(bBytes, encoding="utf8")
        except UnicodeDecodeError as e:
            print(str(e))

        return str(bBytes, encoding="utf8")

    @staticmethod
    def resource_path(relative_path):
        """获取程序中所需文件资源的绝对路径"""
        try:
            # PyInstaller创建临时文件夹,将路径存储于_MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    # 将生成的授权信息记录到regList列表
    @staticmethod
    def addToRegList(regInfo, fieldnames,type):

        # repFlag = False
        # 获取当前时间
        current_time = datetime.now().date()
        # 格式化日期戳
        datestamp = current_time.strftime("%Y%m%d")
        RecordFilePath = 'output/regList_' + regInfo['PID'] + '_' + datestamp + '.csv'
        encoding = 'utf-8-sig'
        # 分离文件路径和文件名
        folder_path = os.path.dirname(RecordFilePath)
        # 检查文件夹是否存在，如果不存在则创建
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        try:
            # 尝试读文件
            # 使用with来处理上下文，可以在读/写完成后自动关闭文件
            with open(RecordFilePath, 'r', newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)

            # 写文件
            with open(RecordFilePath, 'a', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writerow(regInfo)

            print('记录成功！')

        except PermissionError:
            print('文件正被其他进程占用！请关闭后重试')
            return

        except FileNotFoundError:
            print('没有发现regList,重新生成regList！')

            with open(RecordFilePath, 'a', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # 重新生成的表格需要填写表格头
                writer.writeheader()
                writer.writerow(regInfo)

        except UnicodeDecodeError:
            # 自动检测文件编码
            with open(RecordFilePath, 'rb') as f:
                result = chardet.detect(f.read())
                encoding = result['encoding']

        # 读取CSV文件
        data = pd.read_csv(RecordFilePath, encoding=encoding)

        if type:
            data.drop_duplicates(subset=['IMEI'], keep='last', inplace=True)
        else:
            data.drop_duplicates(subset=['DID'], keep='last', inplace=True)
        # 保留最后一次出现的重复项（即具有"RESULT"为"PASS"的行）
        data.to_csv(RecordFilePath, index=False, encoding='utf-8-sig')
