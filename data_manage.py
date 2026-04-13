import json
import re

from PyQt5.QtWidgets import QWidget, QGridLayout
from PyQt5.QtCore import Qt, pyqtSignal

import baseUtils
from qfluentwidgets import (
    CheckBox,
    ComboBox,
    SpinBox,
    BodyLabel,
    LineEdit,
    SwitchButton,
    PrimaryPushButton,
)


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
            self.desc = self.sysItemsData.get("desc", "")
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

            # 配置授权地址账号
            self.authAccountIDLabel = BodyLabel("用户id:", self)
            self.authAccountIDLineEdit = LineEdit(self)
            self.authAccountID = self.sysItemsData.get("current_auth_account", "")
            self.authAccountIDLineEdit.setText(self.authAccountID)
            self.authAccountPassWordLabel = BodyLabel("密钥:", self)
            self.authAccountPassWordLineEdit = LineEdit(self)
            self.authAccountPassWord = self.sysItemsData.get("current_auth_password", "")
            self.authAccountPassWordLineEdit.setText(self.authAccountPassWord)

            self.LayOut.addWidget(self.logLevelLabel, 0, 0)
            self.LayOut.addWidget(self.logLevelComboBox, 0, 1)

            self.LayOut.addWidget(self.deviceTypeLabel, 1, 0)
            self.LayOut.addWidget(self.deviceTypeComboBox, 1, 1)

            self.LayOut.addWidget(self.labelPrintCountLabel, 2, 0)
            self.LayOut.addWidget(self.labelPrintCountSpinBox, 2, 1)

            self.LayOut.addWidget(self.authAddrDictLabel, 3, 0)
            self.LayOut.addWidget(self.authAddrDictComboBox, 3, 1)

            self.LayOut.addWidget(self.authParamLabel, 4, 0)
            self.LayOut.addWidget(self.authParamComboBox, 4, 1)

            self.LayOut.addWidget(self.authAccountIDLabel, 5, 0)
            self.LayOut.addWidget(self.authAccountIDLineEdit, 5, 1)

            self.LayOut.addWidget(self.authAccountPassWordLabel, 5, 2)
            self.LayOut.addWidget(self.authAccountPassWordLineEdit, 5, 3)

            # 设置控件宽度
            self.authAccountPassWordLineEdit.setFixedWidth(300)

            self.LayOut.setSpacing(10)
            self.LayOut.setColumnStretch(1, 1)
            self.LayOut.setRowStretch(3, 1)

            self.update_host()

        else:
            print("sysItemsData is not a dictionary.")

    def update_host(self):
        print("update_host")
        for authAddr in self.authAddrDict:
            desc = authAddr.get("desc", "")
            if desc == self.desc:
                url = authAddr.get("url", "")
                combo_item = f'({desc}){url}'
                self.authAddrDictComboBox.setCurrentText(combo_item)
                return
            else:
                continue

    def _update_sys_items_from_widgets(self):
        if not isinstance(self.sysItemsData, dict):
            self.sysItemsData = {}

        self.sysItemsData["current_logger_level"] = self.logLevelComboBox.currentText()
        self.sysItemsData["current_device_type"] = self.deviceTypeComboBox.currentText()
        self.sysItemsData["current_auth_param"] = self.authParamComboBox.currentText()
        self.sysItemsData["tag_print_times"] = self.labelPrintCountSpinBox.value()

        url_string = self.authAddrDictComboBox.currentText()
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        match = re.search(url_pattern, url_string or '')
        if match:
            self.current_url = match.group()
            self.desc = url_string[1:match.start() - 1]
            self.sysItemsData["desc"] = self.desc
            self.sysItemsData["reg_url"] = self.current_url

        self.sysItemsData["current_auth_account"] = self.authAccountIDLineEdit.text()
        self.sysItemsData["current_auth_password"] = self.authAccountPassWordLineEdit.text()
        # NOTE: burning_pid is now managed via runtime device info (DeviceInfoSettingCard)

    def save_configs(self):
        """Persist current system settings from the UI widgets to the JSON config file.

        This is the preferred high-level save entry point for system settings. It
        first calls :meth:`_update_sys_items_from_widgets` to synchronize
        ``self.sysItemsData`` with the current widget state and then writes the
        resulting dictionary to ``self.File``.

        The older :meth:`write_dict2Json` method performs similar work but
        duplicates the update logic inline and is kept for legacy / existing
        call sites. New code should call :meth:`save_configs` instead.
        """
        self._update_sys_items_from_widgets()
        with open(self.File, 'w', encoding='utf-8', errors='ignore') as file:
            json.dump(self.sysItemsData, file, ensure_ascii=False, indent=4)

    def write_dict2Json(self):
        # 确保sysItemsData是一个字典
        if isinstance(self.sysItemsData, dict):
            self.sysItemsData["current_logger_level"] = self.logLevelComboBox.currentText()
            self.sysItemsData["current_device_type"] = self.deviceTypeComboBox.currentText()
            self.sysItemsData["current_auth_param"] = self.authParamComboBox.currentText()
            self.sysItemsData["tag_print_times"] = self.labelPrintCountSpinBox.value()
            # 使用正则表达式匹配以 http 开头的 URL
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            url_string = self.authAddrDictComboBox.currentText()

            desc_pattern = r'*\(*\)'

            match = re.search(url_pattern, url_string)
            if not match:
                print("not match any legal http string")
                return
            self.current_url = match.group()
            self.desc = url_string[1:match.start()-1]
            self.update_host()
            self.sysItemsData["desc"] = self.desc
            self.sysItemsData["reg_url"] = self.current_url
            self.sysItemsData["current_auth_account"] = self.authAccountIDLineEdit.text()
            self.sysItemsData["current_auth_password"] = self.authAccountPassWordLineEdit.text()
            # NOTE: burning_pid is now managed via runtime device info (DeviceInfoSettingCard)
            with open(self.File, 'w', encoding='utf-8', errors='ignore') as file:
                json.dump(self.sysItemsData, file, ensure_ascii=False, indent=4)

        else:
            print("sysItemsData is not a dictionary.")

