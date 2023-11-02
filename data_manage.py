from enum import Enum

"""授权唯一凭证"""
class AUTH_TYPE(Enum):
    BY_BLE_MAC = 0
    BY_IMEI    = 1


class test_options(object):

    def __init__(self) -> None:
        self.subBatteryVolt = 0
        self.MainBatteryVolt = 0
        self.LteStar = 0
        self.GensorState = 0


    def write_data(self):
        pass

    def read_data(self):
        pass


class config_options(object):
    def __init__(self):
        self.AuthByWhat = AUTH_TYPE.BY_BLE_MAC