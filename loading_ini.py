import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication, QSettings


class SectionList:
    baseSet = "BASE_SETTING"
    testItems = "TEST_ITEM_SELECT"
    testItemc = "TEST_ITEM_CONFIG"


class param_struct:

    def __init__(self, section, key, value) -> None:
        self.section = section
        self.key = key
        self.value = value


class ini_object:

    def __init__(self, path: str):
        self.app = QApplication(sys.argv)
        self.pathName = path
        self.config = QSettings(self.pathName, QSettings.IniFormat)

    def read_bykey(self, section: str, key):
        value = self.config.value(section + '/' + key)
        return value

    def write_bykey(self, section: str, key, value):
        # 添加section和对应的数据 
        self.config.setValue(section + '/' + key, value)

    def write_bykey_with_comment(self, section: str, comment: str = ''):
        # 添加注释行
        if comment:
            comment_bytes = comment.encode('gbk')
            self.config.setValue(section + '/;' + comment_bytes.decode('gbk'), '')
