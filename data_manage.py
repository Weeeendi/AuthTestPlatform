import json
import re
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout

import baseUtils
from qfluentwidgets import CheckBox, setThemeColor, ComboBox, SpinBox, BodyLabel, LineEdit


class SysItemEditFactory(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.LayOut = QGridLayout()
        self.setLayout(self.LayOut)
        self.File = baseUtils.resource_path('resources\\config\\sysConfig.json')

        with open(self.File, 'r', encoding='utf-8', errors='ignore') as file:
            self.sysItemsData = json.loads(file.read())

        # 确保sysItemsData是一个字典
        if isinstance(self.sysItemsData, dict):

            # 设置日志级别
            self.logLevelList = self.sysItemsData.get("logger_level", [])
            self.logLevel = self.sysItemsData.get("current_logger_level", "debug")
            self.logLevelLabel = BodyLabel("日志级别:", self)
            self.logLevelComboBox = ComboBox(self)
            self.logLevelComboBox.addItems(self.logLevelList)
            self.logLevelComboBox.setCurrentText(self.logLevel)

            # 设置设备类型
            self.deviceTypeList = self.sysItemsData.get("device_type", [])
            self.deviceType = self.sysItemsData.get("current_device_type", "BLE")
            self.deviceTypeLabel = BodyLabel("设备类型:", self)
            self.deviceTypeComboBox = ComboBox(self)
            self.deviceTypeComboBox.addItems(self.deviceTypeList)
            self.deviceTypeComboBox.setCurrentText(self.deviceType)

            # 配置授权凭证
            self.authParamList = self.sysItemsData.get("auth_params", [])
            self.authParamLabel = BodyLabel("授权凭证:", self)
            self.authParamComboBox = ComboBox(self)
            self.authParamComboBox.addItems(self.authParamList)
            self.authParamComboBox.setCurrentText(self.sysItemsData.get("current_auth_param", "MAC"))

            # 配置标签打印次数
            self.labelPrintCount = self.sysItemsData.get("tag_print_times", 3)
            self.labelPrintCountLabel = BodyLabel("标签打印次数:", self)
            self.labelPrintCountSpinBox = SpinBox(self)

            self.labelPrintCountSpinBox.setValue(self.labelPrintCount)

            # 配置授权地址
            urls = []
            self.current_url = self.sysItemsData.get("reg_url", "")
            self.authAddrDict = self.sysItemsData.get("reg_urls", "")
            for authAddr in self.authAddrDict:
                desc = authAddr.get("desc", "")
                url = authAddr.get("url", "")
                urls.append(f'({desc}){url}')
            self.authAddrDictLabel = BodyLabel("授权地址:", self)
            self.authAddrDictComboBox = ComboBox(self)
            self.authAddrDictComboBox.addItems(urls)
            self.authAddrDictComboBox.setCurrentText(self.current_url)

            self.burningPIDLabel = BodyLabel("烧写PID:", self)
            self.burningPIDCheckBox = CheckBox(self)
            self.burningPID = self.sysItemsData.get("burning_pid", False)
            if self.burningPID:
                self.burningPIDCheckBox.setChecked(True)
            else:
                self.burningPIDCheckBox.setChecked(False)

            # 配置授权地址账号
            self.authAccountIDLabel = BodyLabel("用户id:", self)
            self.authAccountIDLineEdit = LineEdit(self)
            self.authAccountID = self.sysItemsData.get("current_auth_account", "")
            self.authAccountIDLineEdit.setText(self.authAccountID)
            self.authAccountPassWordLabel = BodyLabel("密钥:", self)
            self.authAccountPassWordLineEdit = LineEdit(self)
            self.authAccountPassWord = self.sysItemsData.get("current_auth_password", "")
            self.authAccountPassWordLineEdit.setText(self.authAccountPassWord)

            # 配置服务器地址
            self.hostAddrLabel = BodyLabel("host", self)
            self.hostAddrLineEdit = LineEdit(self)
            # self.hostAddrLineEdit.setText(self.sysItemsData.get("host", ""))
            # self.hostAddrLineEdit.setDisabled(True)

            self.hostPortLabel = BodyLabel("port", self)
            self.hostPortLineEdit = LineEdit(self)
            # self.hostPortLineEdit.setText(self.sysItemsData.get("port", ""))
            # self.hostPortLineEdit.setDisabled(True)


            self.LayOut.addWidget(self.logLevelLabel, 0, 0)
            self.LayOut.addWidget(self.logLevelComboBox, 0, 1)

            # self.LayOut.addWidget(self.deviceTypeLabel, 1, 0)
            # self.LayOut.addWidget(self.deviceTypeComboBox, 1, 1)

            self.LayOut.addWidget(self.labelPrintCountLabel, 2, 0)
            self.LayOut.addWidget(self.labelPrintCountSpinBox, 2, 1)

            self.LayOut.addWidget(self.authAddrDictLabel, 3, 0)
            self.LayOut.addWidget(self.authAddrDictComboBox, 3, 1)

            self.LayOut.addWidget(self.burningPIDLabel, 3, 2)
            self.LayOut.addWidget(self.burningPIDCheckBox, 3, 3)

            self.LayOut.addWidget(self.deviceTypeLabel, 4, 0)
            self.LayOut.addWidget(self.deviceTypeComboBox, 4, 1)

            self.LayOut.addWidget(self.authParamLabel, 4, 2)
            self.LayOut.addWidget(self.authParamComboBox, 4, 3)

            self.LayOut.addWidget(self.hostAddrLabel, 5, 0)
            self.LayOut.addWidget(self.hostAddrLineEdit, 5, 1)

            self.LayOut.addWidget(self.hostPortLabel, 5, 2)
            self.LayOut.addWidget(self.hostPortLineEdit, 5, 3)

            self.LayOut.addWidget(self.authAccountIDLabel, 6, 0)
            self.LayOut.addWidget(self.authAccountIDLineEdit, 6, 1)

            self.LayOut.addWidget(self.authAccountPassWordLabel, 6, 2)
            self.LayOut.addWidget(self.authAccountPassWordLineEdit, 6, 3)

            # 设置控件宽度
            self.authAccountPassWordLineEdit.setFixedWidth(300)

            # 绑定事件
            self.logLevelComboBox.currentTextChanged.connect(self.write_dict2Json)
            self.deviceTypeComboBox.currentTextChanged.connect(self.write_dict2Json)
            self.authParamComboBox.currentTextChanged.connect(self.write_dict2Json)


            self.labelPrintCountSpinBox.valueChanged.connect(self.write_dict2Json)
            self.authAddrDictComboBox.currentTextChanged.connect(self.write_dict2Json)
            self.authAccountIDLineEdit.textChanged.connect(self.write_dict2Json)
            self.authAccountPassWordLineEdit.textChanged.connect(self.write_dict2Json)
            self.burningPIDCheckBox.stateChanged.connect(self.write_dict2Json)

            self.LayOut.setSpacing(10)
            self.LayOut.setColumnStretch(1, 1)
            self.LayOut.setRowStretch(3, 1)

            self.chk_device_type()
            self.deviceTypeComboBox.currentTextChanged.connect(self.chk_device_type)
            self.update_host()
            self.authParamComboBox.currentTextChanged.connect(self.update_host)
        else:
            print("sysItemsData is not a dictionary.")

    def update_host(self):
        print("update_host")
        for authAddr in self.authAddrDict:
            url = authAddr.get("url", "")
            if url == self.current_url:
                desc = authAddr.get("desc", "")
                host = authAddr.get("host", "")
                port = authAddr.get("port", "")
                combo_item = f'({desc}){url}'
                self.hostAddrLineEdit.setText(host)
                self.hostPortLineEdit.setText(port)
                self.authAddrDictComboBox.setCurrentText(combo_item)
                return
            else:
                continue

    def chk_device_type(self):
        if self.deviceTypeComboBox.currentText() != "BLE":
            self.hostAddrLabel.show()
            self.hostAddrLineEdit.show()
            self.hostPortLabel.show()
            self.hostPortLineEdit.show()
        else:
            self.hostAddrLabel.hide()
            self.hostAddrLineEdit.hide()
            self.hostPortLabel.hide()
            self.hostPortLineEdit.hide()

    def write_dict2Json(self):
        # 确保sysItemsData是一个字典
        if isinstance(self.sysItemsData, dict):
            self.sysItemsData["current_logger_level"] = self.logLevelComboBox.currentText()
            self.sysItemsData["current_device_type"] = self.deviceTypeComboBox.currentText()
            self.sysItemsData["current_auth_param"] = self.authParamComboBox.currentText()
            self.sysItemsData["tag_print_times"] = self.labelPrintCountSpinBox.value()
            # 使用正则表达式匹配以 http 开头的 URL
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            match = re.search(url_pattern, self.authAddrDictComboBox.currentText())
            self.current_url = match.group()
            self.sysItemsData["reg_url"] = self.current_url
            self.sysItemsData["current_auth_account"] = self.authAccountIDLineEdit.text()
            self.sysItemsData["current_auth_password"] = self.authAccountPassWordLineEdit.text()
            self.sysItemsData["burning_pid"] = self.burningPIDCheckBox.isChecked()
            # if self.deviceTypeComboBox.currentText() != "BLE":
            #     self.sysItemsData["host"] = self.hostAddrLineEdit.text()
            #     self.sysItemsData["port"] = self.hostPortLineEdit.text()
            with open(self.File, 'w', encoding='utf-8', errors='ignore') as file:
                json.dump(self.sysItemsData, file, ensure_ascii=False, indent=4)

        else:
            print("sysItemsData is not a dictionary.")


class TestItemEditFactory(QWidget):
    def __init__(self, File, parent=None):
        super().__init__(parent)
        self.File = File
        self.GridRowCount = 0
        self.GridColCount = 0
        self.LayOut = QGridLayout()
        self.LayOut.setColumnStretch(1, 1)

        with open(self.File, 'r', encoding='utf-8', errors='ignore') as file:
            self.testItemsData = json.loads(file.read())

        # 确保testItemsData是一个字典
        if isinstance(self.testItemsData, dict):
            testItemsList = self.testItemsData.get("TestItems", [])
            for item in testItemsList:
                name = item.get("dspName", "")
                state = item.get("enable", False)
                if name != '':
                    self.create_component_enable(name, state)
        else:
            print("testItemsData is not a dictionary.")
        self.LayOut.setRowStretch(self.GridRowCount, 1)
        self.setLayout(self.LayOut)

    def write_dict2Json(self):
        # 确保testItemsData是一个字典
        if isinstance(self.testItemsData, dict):
            testItemsList = self.testItemsData.get("TestItems", [])
            for item in testItemsList:
                name = item.get("dspName", "")
                if name != '' and self.check_component_enable(name):
                    item.update({"enable": True})
                else:
                    item.update({"enable": False})
        else:
            print("testItemsData is not a dictionary.")

        with open(self.File, 'w', encoding='utf-8', errors='ignore') as file:
            # 将数据以JSON格式写入文件，确保中文不被转义
            json.dump(self.testItemsData, file, ensure_ascii=False, indent=4)

    def create_component_enable(self, objName, state: bool):
        try:
            setattr(self, objName + "CheckBox", CheckBox(objName, self))
            getattr(self, objName + "CheckBox").setChecked(state)
            getattr(self, objName + "CheckBox").setMinimumWidth(200)
            getattr(self, objName + "CheckBox").stateChanged.connect(self.write_dict2Json)
            self.LayOut.addWidget(getattr(self, objName + "CheckBox"), self.GridRowCount, self.GridColCount,
                                  Qt.AlignLeft | Qt.AlignTop)
            if self.GridColCount == 1:
                self.GridRowCount += 1
                self.GridColCount = 0
            else:
                self.GridColCount += 1

        except Exception:
            pass

    def check_component_enable(self, objName) -> bool:
        try:
            state = getattr(self, objName + "CheckBox").isChecked()
            return state
        except Exception:
            return None

    # def resizeEvent(self, event):
    #     # 获取当前窗口尺寸
    #     width, height = self.width(), self.height()
    #     print(f"标签的大小: {width, height}")
    #     # 设置窗口的最小宽度和高度
    #     minWidth, minHeight = 380, 300
    #     # 确保窗口大小不小于最小尺寸
    #     if width < minWidth or height < minHeight:
    #         self.resize(max(width, minWidth), max(height, minHeight))
    #         self.setMinimumSize(380, 300)
    #     event.accept()  # 确保事件被接受和处理


if __name__ == '__main__':
    # 创建Qt对象
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    # file = 'resources/config/userConfig.json'
    # setting_interface = TestItemEditFactory(file)
    setting_interface = SysItemEditFactory()
    setThemeColor("#000000")
    setting_interface.setWindowTitle("功能选择窗口测试")

    setting_interface.show()

    sys.exit(app.exec())
