import ctypes  # 通过这个模块来调用C#的dll库
from PyQt5.QtCore import QThread
import time
from baseLogger import log
import baseUtils

# 创建BaseUtils实例
util = baseUtils.BaseUtils()

# 加载dll库
mydll = ctypes.WinDLL("resource/Seagull.BarTender.Print.dll")

# 可能会出现“Import "Seagull.BarTender.Print" could not be resolved”这个波浪线错误，这里不用管

class BaseBarTender():  # 创建打印机类方便在上位机主程序中调用
    def __init__(self, filePath):
        # 启用引擎
        self.btEngine = mydll.Engine(True)
        self.filePath = filePath
        # self.printerName = ''
        # self.btFormat = ''

    def getPrinterList(self):  # 获取你电脑上的打印机列表
        printers = mydll.Printers()
        printerList = []
        for printer in printers:
            printerList.append(printer.PrinterName)
        self.printerName = printers.Default.PrinterName  # 这里为了方便，将要打印机确定为默认打印机
        # 默认打印机只需在电脑的控制面板中设定即可

    def createTask(self):  # 创建打印任务
        self.btFormat = self.btEngine.Documents.Open(self.filePath)

    # 调试过程中发现保存功能无法生效
    # def abortTask(self):
    #     self.btEngine.Stop(SaveOptions.SaveChanges)

    def get_data_dict(self, key=None):  # 获取你的标签文件.btw的内容
        data_dict = {}
        if self.btFormat:
            if key:
                return self.btFormat.SubStrings[key].Value
            for substring in self.btFormat.SubStrings:
                data_dict[substring.Name] = substring.Value
        return data_dict

    # 传入一个字典：{'num':11111}则会把num变量的值设置为11111
    def set_data_dict(self, data_dict):  # 将你需要的数据源内容内容写入到标签.btw文件中
        if len(data_dict) and self.btFormat:
            for key, value in data_dict.items():
                for substring in self.btFormat.SubStrings:
                    if substring.Name == key:
                        self.btFormat.SubStrings.SetSubString(key, value)

    # def __del__(self):
    #     #关闭引擎，释放资源
    #     if self.btEngine.IsAlive:
    #         self.btEngine.Stop()
    #         self.btEngine.Dispose()


class BasePrinterThread(QThread):
    def __init__(self, Ser, cnt):
        super(BasePrinterThread, self).__init__()
        # # 创建BaseUtils实例
        # self.util = baseUtils.BaseUtils()
        # 接受主函数传递的参数
        self.Ser = Ser  # 串口实例
        self.cnt = cnt  # 打印次数
        # 创建一个空列表，接受打印消息队列
        self.list = []
        # print('BasePrinterThread.init', 'cnt:', self.cnt, type(self.cnt))

        try:
            # 生成bartender对象
            self.seagullBartender = BaseBarTender(util.resource_path("resource/yunJi_tag.btw"))
            # 生成目标文件对象
            self.seagullBartender.createTask()
            # 搜寻默认打印机
            self.seagullBartender.getPrinterList()
            # 绑定打印机
            self.seagullBartender.btFormat.PrintSetup.PrinterName = self.seagullBartender.printerName
            # 绑定打印机
            self.seagullBartender.btFormat.PrintSetup.IdenticalCopiesOfLabel = self.cnt
        except:
            print("打印机初始化失败！")

        print("创建BasePrinterThread线程")

    def insertMsg(self, bleMac, deviceIotId, PID):
        print("basePrinter.insertMsg", bleMac, deviceIotId, PID)
        log.logger.info("开始打印标签！")

        dict = {}
        dict["deviceIotId"] = deviceIotId
        dict["bleMac"] = 'BLE:' + bleMac
        dict["PID"] = 'PID:' + PID
        dict["showId"] = '设备编号：' + deviceIotId[0:2] + deviceIotId[7:]

        print("basePrinter.insertMsg", dict, type(dict))
        self.list.insert(0, dict)

    def run(self):
        print("启动BasePrinterThread线程")

        while True:
            # 处理打印消息队列中的信息
            while len(self.list) > 0:
                # 获取列表中的字典信息
                outMsg = self.list.pop()
                print("outMsg:", outMsg)

                # 打印内容设置
                self.seagullBartender.set_data_dict(outMsg)

                # 开始打印
                printerResult = self.seagullBartender.btFormat.Print("printjob", 5000)
                log.logger.info("标签打印结果：%s" % printerResult)
                # log.logger.info(printerResult)

                # 等待0.1秒
                time.sleep(0.1)

            # 等待0.2秒
            time.sleep(0.2)
            if self.Ser.isOpen() == False:
                print("关闭BasePrinterThread线程")
                self.quit()
                return

# if __name__ == "__main__":
# dict = {
# "deviceIotId" : "sxq123456"
# }
# #key:"num"为在bartender中命名的数据源，value:"1234567"为你想输出的条码内容
# # b= BarTender(os.getcwd()+"\\barTender_test.btw")#path为先前设计的标签路径
# b= BarTender(os.getcwd()+"\\yunJi_iGo.btw")#path为先前设计的标签路径
# b.getPrinterList()
# b.createTask()
# b.btFormat.PrintSetup.PrinterName = b.printerName
# b.set_data_dict(dict)
# result = b.btFormat.Print("printjob",2000)
# print(result)


# b = BasePrinterThread(3)
# # b.start()
# # b.insertMsg('112233445566', 'sxq123456', '1234567890')
# b.seagullBartender.set_data_dict(dict)
# result = b.seagullBartender.btFormat.Print("printjob",2000)
# print(result)
