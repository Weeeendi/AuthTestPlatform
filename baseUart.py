import time
from PyQt5 import QtCore
from PyQt5.QtCore import QThread, pyqtSignal
import baseUtils
import codecs


class BaseUartThread(QThread):
    # 自定义信号，用来发送接收到的数据
    revData_sinOut = pyqtSignal(str)

    def __init__(self, Ser):
        super(BaseUartThread, self).__init__()
        # 创建BaseUtils实例
        self.util = baseUtils.BaseUtils()
        self.Ser = Ser

        # 创建一个互斥锁
        self.uartTx_mutex = QtCore.QMutex()
        print("创建BaseUartThread线程")

    #
    def uartWrite(self, data):
        # 判断输入data是否有效
        if not data:
            return None
        # 加写串口数据互斥锁，锁
        self.uartTx_mutex.lock()
        # print("baseUart", "uartWrite", data, type(data))

        tmp = codecs.decode(data, "hex_codec")

        if self.Ser.isOpen():
            try:
                # 向串口写数据
                self.Ser.write(tmp)
            except:
                print("baseUart.uartWrite", "serial write false!")
        # 加写串口数据互斥锁，解锁
        self.uartTx_mutex.unlock()

    def run(self):
        print("启动BaseUartThread线程")
        while True:
            try:
                # 获得接受到的字符
                count = self.Ser.inWaiting()
            except Exception as e:
                print(e)
                print("uart ser err!")
                count = 0
            if count != 0:
                # 读串口数据
                recv = self.Ser.read(count)

                dealStr = self.util.asciiB2HexString(recv)

                # print("baseUart.run", dealStr, type(dealStr))
                # 发送接收到的数据
                self.revData_sinOut.emit(dealStr)
                # # 清空接受缓冲区
                # self.Ser.flushInput()
            # 等待0.1秒
            time.sleep(0.1)
            if not self.Ser.isOpen():
                print("关闭BaseUartThread线程")
                self.quit()
                return
