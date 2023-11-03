import os
from enum import Enum
from loading_ini import sectionList, ini_object

"""授权唯一凭证"""


class AuthType(Enum):
    BY_BLE_MAC = 0
    BY_IMEI = 1


class BoolSetting():
    enable: bool
    switch: bool
    name: str

    def __init__(self, enable, switch, name):
        self.enable = enable
        self.switch = switch
        self.name = name


class ValueSetting:
    enable: bool
    value: int
    name: str

    def __init__(self, enable, value, name):
        self.enable = enable
        self.value = value
        self.name = name


class str_setting():
    value: str
    name: str

    def __init__(self, value: str, name: str):
        self.value = value
        self.name = name


class BaseSetItems:
    reg_url: str_setting
    logger_level: str_setting  # support INFO,DEBUG,ERROR
    tag_print_times: ValueSetting

    def __init__(self, reg_url, logger_level, tag_print_times):
        self.reg_url = reg_url
        self.logger_level = logger_level
        self.tag_print_times = tag_print_times


class UserSetItems:
    test_type: str_setting
    mainBattMin: ValueSetting
    mainBattMax: ValueSetting
    subBattMax: ValueSetting
    subBattMin: ValueSetting
    LteStar: ValueSetting
    BLERssi: ValueSetting
    LteRetry: ValueSetting
    G_sensorRetry: ValueSetting
    batteryRetry: ValueSetting
    flashRetry: ValueSetting

    def __init__(self, test_type, mainBattMin, mainBattMax, subBattMax, subBattMin,
                 LteStar, BLERssi, LteRetry, G_sensorRetry, batteryRetry, flashRetry):
        self.test_type = test_type
        self.mainBattMin = mainBattMin
        self.mainBattMax = mainBattMax
        self.subBattMax = subBattMax
        self.subBattMin = subBattMin
        self.LteStar = LteStar
        self.BLERssi = BLERssi
        self.LteRetry = LteRetry
        self.G_sensorRetry = G_sensorRetry
        self.batteryRetry = batteryRetry
        self.flashRetry = flashRetry


class test_options:

    def __init__(self):
        self.sections = sectionList()

        self.base_set = BaseSetItems(
            reg_url=str_setting(value="example.com", name="reg_url"),
            logger_level=str_setting(value="info", name="logger_level"),
            tag_print_times=ValueSetting(enable=True, value=1, name="tag_print_times")
        )

        self.UserSet = UserSetItems(
            test_type=str_setting(value="BLE", name='test type'),
            mainBattMin=ValueSetting(enable=True, value=20, name='Main Battery Minimum'),
            mainBattMax=ValueSetting(enable=True, value=50, name='Main Battery Maximum'),
            subBattMin=ValueSetting(enable=False, value=10, name='Sub Battery Minimum'),
            subBattMax=ValueSetting(enable=True, value=30, name='Sub Battery Maximum'),
            LteStar=ValueSetting(enable=False, value=5, name='LTE Signal Strength'),
            BLERssi=ValueSetting(enable=True, value=-80, name='BLE Signal Strength'),
            LteRetry=ValueSetting(enable=True, value=-80, name='BLE Signal Strength'),
        )

        self.iniBaseSet = ini_object("resource/config/sys_config.ini")
        self.iniUserSet = ini_object("resource/config/user_config.ini")

        self.write_userdata()

    def write_userdata(self):
        for item in vars(self.UserSet).items():
            if hasattr(item, 'enable'):
                self.iniUserSet.wirte_byKey(self.sections.testItems, item.name + ' enable', item.enable)
            if hasattr(item, 'value'):
                self.iniUserSet.wirte_byKey(self.sections.testItemc, item.name, item.value)

    def _read_basedata(self):
        for item in vars(self.base_set).items():
            item.value = self.iniBaseSet.read_byKey(self.sections.baseSet, item.name)

    def read_userdata(self):
        for item in self.UserSet:
            if hasattr(item, 'enable'):
                item.enable = self.iniUserSet.read_byKey(self.sections.testItems, item.name + ' enable')
            if hasattr(item, 'value'):
                item.value = self.iniUserSet.read_byKey(self.sections.testItemc, item.name)


if __name__ == '__main__':
    myapp = test_options()
