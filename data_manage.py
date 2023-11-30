import os
from enum import Enum
from loading_ini import SectionList, ini_object

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


class UserSetItems:
    test_type: StrSetting
    mainBatt: Value_MMSetting
    subBatt: Value_MMSetting
    LteStar: ValueSetting
    BLERssi: ValueSetting
    G_sensor: ValueSetting
    flash: ValueSetting

    def __init__(self, test_type, mainBatt, subBatt, LteStar, BLERssi, G_sensor, flash):
        self.test_type = test_type
        self.mainBatt = mainBatt
        self.subBatt = subBatt
        self.LteStar = LteStar
        self.BLERssi = BLERssi
        self.G_sensor = G_sensor
        self.flash = flash


class TestOptions:
    """产测配置说明"""

    def __init__(self):
        self.sections = SectionList()

        self.base_set = BaseSetItems(
            reg_url=StrSetting(value="example.com", name="reg_url"),
            logger_level=StrSetting(value="info", name="logger_level"),
            tag_print_times=ValueSetting(enable=True, value=1, name="tag_print_times")
        )

        self.UserSet = UserSetItems(
            test_type=StrSetting(value="BLE", name='Test_type'),
            mainBatt=Value_MMSetting(name='Main_Battery'),
            subBatt=Value_MMSetting(name='Sub_Battery'),  # Changed from 'subBattMax'
            LteStar=Value_mSetting(name='LTE_Signal_Strength'),
            BLERssi=Value_mSetting(name='BLE_Signal_Strength'),
            G_sensor=ValueSetting(name='G_sensor_Test'),  # Added
            flash=ValueSetting(name='flash_Test')  # Added
        )

        self.iniBaseSet = ini_object("resource/config/sys_config.ini")
        self.iniUserSet = ini_object("resource/config/user_config.ini")

        self._read_basedata()

        """
        读用户指令
        如果有配置文件,读配置文件,否则生成配置文件
        """
        if not os.path.exists("resource/config/user_config.ini"):
            self.write_userdata()

        self.read_userdata()

    # 写基础设置内容
    def _write_basedata(self):
        for item_name, item_var in vars(self.base_set).items():
            self.iniBaseSet.write_bykey(self.sections.baseSet, item_var.name, item_var.value)

    # 读基础设置内容
    def _read_basedata(self):
        for item_name, item_var in vars(self.base_set).items():
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
                item_var.enable = int(self.iniUserSet.read_bykey(self.sections.testItems, item_var.name + '_enable'))
            if hasattr(item_var, 'retry'):
                item_var.retry = int(self.iniUserSet.read_bykey(self.sections.testItemc, item_var.name + '_retry'))
            if hasattr(item_var, 'maxvalue'):
                item_var.maxvalue = int(
                    self.iniUserSet.read_bykey(self.sections.testItemc, item_var.name + '_maxvalue'))
            if hasattr(item_var, 'minvalue'):
                item_var.minvalue = int(
                    self.iniUserSet.read_bykey(self.sections.testItemc, item_var.name + '_minvalue'))


if __name__ == '__main__':
    q = TestOptions()
