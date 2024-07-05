import os
from enum import Enum
from typing import List
from PyQt5.QtCore import QSettings
import json



"""授权唯一凭证"""


class AuthType(Enum):
    BY_BLE_MAC = 0
    BY_IMEI = 1


write_attrList = ['enable', 'value', 'maxvalue', 'minvalue', 'retry', 'unit']


# 阈值类型属性
class Value_MMSetting:
    __slots__ = ('enable', 'value', 'maxvalue', 'minvalue', 'name', 'retry', 'unit')

    def __init__(self, name, enable=False, value=0, maxvalue=0, minvalue=0, retry=1, unit=''):
        self.retry = retry
        self.value = value
        self.enable = enable
        self.maxvalue = maxvalue
        self.minvalue = minvalue
        self.name = name
        self.unit = unit


class Value_mSetting:
    __slots__ = ('enable', 'value', 'minvalue', 'name', 'retry', 'unit')

    def __init__(self, name, enable=False, value=0, minvalue=0, retry=1, unit=''):
        self.retry = retry
        self.value = value
        self.enable = enable
        self.minvalue = minvalue
        self.name = name
        self.unit = unit


# 值类型属性
class ValueSetting:
    __slots__ = ('enable', 'name', 'value', 'retry', 'unit')

    def __init__(self, name, enable=False, value=0, retry=1, unit=''):
        self.value = value
        self.enable = enable
        self.retry = retry
        self.name = name
        self.unit = unit


class StrSetting:
    __slots__ = ('value', 'name')

    def __init__(self, name: str, value="", ):
        self.value = value
        self.name = name


class BaseSetItems:
    reg_url: StrSetting
    logger_level: StrSetting  # support INFO,DEBUG,ERROR
    tag_print_times: ValueSetting

    def __init__(self, reg_url, logger_level, tag_print_times):
        self.reg_url = reg_url
        self.logger_level = logger_level
        self.tag_print_times = tag_print_times


class TestOptions:
    """产测配置说明"""

    def __init__(self):

        self.base_set = BaseSetItems(
            reg_url=StrSetting(value="example.com", name="reg_url"),
            logger_level=StrSetting(value="info", name="logger_level"),
            tag_print_times=ValueSetting(enable=True, value=1, name="tag_print_times")
        )
        try:
            self.iniBaseSet = QSettings("resource/config/sys_config.ini")
            self.base_set.logger_level.value = self.iniBaseSet.value("BASE_SETTING/logger_level")
            self.base_set.reg_url.value = self.iniBaseSet.value("BASE_SETTING/reg_url")
            self.base_set.tag_print_times.value = self.iniBaseSet.value("BASE_SETTING/tag_print_times")
        except Exception as e:
            print("读取配置文件失败", str(e))

        config = self.load_json_from_file("resource/config/user_testcfg.json")
        if config is not None:
            self.iniUserSet = self.create_form(config)

        self.read_basedata()

        """
        读用户指令
        如果有配置文件,读配置文件,否则生成配置文件
        """
        if not os.path.exists("resource/config/user_config.ini"):
            self.write_userdata()

        self.read_userdata()

    def load_json_from_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                return data
        except FileNotFoundError:
            print(f"File '{file_path}' not found.")
            return None
    def create_form(self, config):
        for item in config:
            if item.get('enable', False):

                if item['type'] == 'MM_value':
                    min_val = item.get('minValue', 0)
                    max_val = item.get('maxValue', 100)
                    spin_box = QSpinBox()
                    spin_box.setRange(min_val, max_val)
                    spin_box.setSuffix(f" {item.get('unit', '')}")
                    self.layout.addWidget(spin_box)
                elif item['type'] == 'm_value':

                    min_val = item.get('minValue', 0)
                elif item['type'] == 'bool':
                    check_box = QCheckBox()
                    self.layout.addWidget(check_box)
                else:
                    line_edit = QLineEdit()
                    self.layout.addWidget(line_edit)
    # 写基础设置内容
    def write_basedata(self):
        for item_name, item_var in vars(self.base_set).items():
            if item_name == 'reg_urls':
                for setting in item_var:
                    self.iniBaseSet.write_bykey(self.sections.baseSet, setting.name, setting.value)
                    break
            else:
                self.iniBaseSet.write_bykey(self.sections.baseSet, item_var.name, item_var.value)

    # 读基础设置内容
    def read_basedata(self):
        for item_name, item_var in vars(self.base_set).items():
            if 'reg_urls' == item_name:
                for setting in item_var:
                    setting.value = self.iniBaseSet.read_bykey(self.sections.baseSet, setting.name)
            else:
                item_var.value = self.iniBaseSet.read_bykey(self.sections.baseSet, item_var.name)

    # 写用户设置内容
    def write_userdata(self):

        for item_name, item_var in vars(self.UserSet).items():
            if hasattr(item_var, 'enable'):
                self.iniUserSet.write_bykey(self.sections.testItems, item_var.name + '_enable', item_var.enable)
            if hasattr(item_var, 'retry'):
                self.iniUserSet.write_bykey(self.sections.testItemc, item_var.name + '_retry', item_var.retry)
            if hasattr(item_var, 'maxvalue'):
                self.iniUserSet.write_bykey(self.sections.testItemc, item_var.name + '_maxvalue', item_var.maxvalue)
            if hasattr(item_var, 'minvalue'):
                self.iniUserSet.write_bykey(self.sections.testItemc, item_var.name + '_minvalue', item_var.minvalue)

    # 读用户设置内容
    def read_userdata(self):
        for item_name, item_var in vars(self.UserSet).items():
            if hasattr(item_var, 'enable'):
                try:
                    if 'True' == self.iniUserSet.read_bykey(self.sections.testItems, item_var.name + '_enable'):
                        item_var.enable = True
                    else:
                        item_var.enable = False
                except TypeError:
                    item_var.enable = False
                    pass
            if hasattr(item_var, 'retry'):
                try:
                    item_var.retry = int(self.iniUserSet.read_bykey(self.sections.testItemc, item_var.name + '_retry'))
                except TypeError:
                    item_var.retry = 1
                    pass
            if hasattr(item_var, 'maxvalue'):
                try:
                    item_var.maxvalue = int(
                        self.iniUserSet.read_bykey(self.sections.testItemc, item_var.name + '_maxvalue'))
                except TypeError:
                    item_var.maxvalue = 0
                    pass
            if hasattr(item_var, 'minvalue'):
                try:
                    item_var.minvalue = int(
                        self.iniUserSet.read_bykey(self.sections.testItemc, item_var.name + '_minvalue'))
                except TypeError:
                    item_var.minvalue = 0
                    pass


if __name__ == '__main__':
    q = TestOptions()
