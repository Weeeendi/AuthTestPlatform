import json
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QVBoxLayout

from qfluentwidgets import CheckBox, setThemeColor


class SysItemEditFactory(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.LayOut = QVBoxLayout()
        self.setLayout(self.LayOut)


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

    def resizeEvent(self, event):
        # 获取当前窗口尺寸
        width, height = self.width(), self.height()
        print(f"标签的大小: {width, height}")
        # 设置窗口的最小宽度和高度
        minWidth, minHeight = 380, 300
        # 确保窗口大小不小于最小尺寸
        if width < minWidth or height < minHeight:
            self.resize(max(width, minWidth), max(height, minHeight))
            self.setMinimumSize(380, 300)
        event.accept()  # 确保事件被接受和处理


if __name__ == '__main__':
    # 创建Qt对象
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    file = 'resources/config/userConfig.json'
    setting_interface = TestItemEditFactory(file)
    setThemeColor("#000000")
    setting_interface.setWindowTitle("功能选择窗口测试")

    setting_interface.show()

    sys.exit(app.exec())
