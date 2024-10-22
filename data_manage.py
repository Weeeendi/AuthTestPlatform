import json
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget

from qfluentwidgets import CheckBox


class TestItemFactory(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.GridRowCount = 0
        with open('resources/config/userConfig.json', 'r', encoding='utf-8', errors='ignore') as file:
            self.testItemsData = json.loads(file.read())

        # 确保testItemsData是一个字典
        if isinstance(self.testItemsData, dict):
            testItemsList = self.testItemsData.get("TestItems", [])
            # 确保testItemsList是一个列表
            if isinstance(testItemsList, list):
                self.testItems = []
                # director = Director()
                # for testItemData in testItemsList:
                # testItem = director.construct(testItemData)
                # self.testItems.append(testItem)
            else:
                print("testItemsList is not a list.")
        else:
            print("testItemsData is not a dictionary.")

    def create_component_enable(self, objName, state: bool):
        try:
            setattr(self, objName + "CheckBox", CheckBox(objName, self))
            getattr(self, objName + "CheckBox").setChecked(state)
        except Exception:
            pass


if __name__ == '__main__':
    # 创建Qt对象
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)

    Window = QWidget()


    Window.show()

    sys.exit(app.exec())
