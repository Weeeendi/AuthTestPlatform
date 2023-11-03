from PyQt5.QtWidgets import QApplication  
from PyQt5.QtCore import QCoreApplication, QSettings  
import sys 

class sectionList:
    baseSet = "BASE SETTING",
    testItems  =  "TEST ITEM SELECT",
    testItemc  =  "TEST ITEM CONFIG",

class param_struct:

    def __init__(self,section,key,value) -> None:
        self.section = section
        self.key = key
        self.value = value


class ini_object:

    def __init__(self,path:str):
        self.app = QApplication(sys.argv)
        self.pathName = path
        self.config = QSettings(self.pathName,QSettings.IniFormat)
        self.level = self.read_byKey('SETUP','logger_level')
        print(self.level)

    def read_byKey(self,section:str,key):
        value = self.config.value(section+'/'+key)
        return value
  
    def wirte_byKey(self,section:str,key,value):
        # 添加section和对应的数据 
        self.config.setValue(section+'/'+key,value)


if __name__ == '__main__':
    myapp = ini_object()
    myapp.app.exec()