from enum import Enum
import json
from enum import Enum

from PyQt5.QtCore import Qt

from qfluentwidgets import BodyLabel, SpinBox, CheckBox

"""授权唯一凭证"""


class IntEditBox(SpinBox):
    """ Int line edit """

    # valueChanged = pyqtSignal(str)

    def __init__(self, maxVal, parent=None):
        super().__init__(parent=parent)
        self.setFixedSize(120, 33)
        self.setMaximum(maxVal)


class AuthType(Enum):
    BY_BLE_MAC = 0
    BY_IMEI = 1


def load_json_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Invalid JSON in file '{file_path}'.")
        return None


class TestItem:
    """产测配置说明"""

    def __init__(self):
        self.funName = ""
        self.dspName = ""
        self.type = ""
        self.maxValue = 0
        self.minValue = 0
        self.enable = False
        self.cmd = ""
        self.interval = 0
        self.retry = 0
        self.ret = ""
        self.describe = ""

    def __str__(self):
        return f"TestItem(funName={self.funName}, dspName={self.dspName}, type={self.type}, maxValue={self.maxValue}, minValue={self.minValue}, enable={self.enable}, retry={self.retry},describe={self.describe}, cmd={self.cmd}, interval={self.interval})"


class TestItemBuilder:
    def __init__(self):
        self.testItem = TestItem()

    def set_index(self, index):
        self.testItem.index = index
        return self

    def set_funName(self, funName):
        self.testItem.funName = funName
        return self

    def set_dspName(self, dspName):
        self.testItem.dspName = dspName
        return self

    def set_type(self, type):
        self.testItem.type = type
        return self

    def set_maxValue(self, maxValue):
        self.testItem.maxValue = maxValue
        return self

    def set_minValue(self, minValue):
        self.testItem.minValue = minValue
        return self

    def set_enable(self, enable):
        self.testItem.enable = enable
        return self

    def set_retry(self, retry):
        self.testItem.retry = retry
        return self

    def set_cmd(self, cmd):
        self.testItem.cmd = cmd
        return self

    def set_interval(self, interval):
        self.testItem.interval = interval
        return self

    def set_describe(self, describe):
        self.testItem.describe = describe
        return self

    def build(self):
        return self.testItem


class Director:
    def __init__(self):
        pass

    @staticmethod
    def construct(testParam):
        builder = TestItemBuilder()  # 创建一个TestItemBuilder对象
        return builder \
            .set_index(testParam.get("index", 0)) \
            .set_funName(testParam.get("funName", "")) \
            .set_dspName(testParam.get("dspName", "")) \
            .set_describe(testParam.get("describe", "")) \
            .set_type(testParam.get("type", "")) \
            .set_maxValue(testParam.get("MaxMin", 0)[0]) \
            .set_minValue(testParam.get("MaxMin", 0)[1]) \
            .set_enable(testParam.get("enable", False)) \
            .set_retry(testParam.get("retry", 0)) \
            .set_cmd(testParam.get("cmd", "")) \
            .set_interval(testParam.get("interval", 0)) \
            .build()

    @staticmethod
    def print_test_item(testParam):
        print(testParam)


class TestItemFactory:

    def __init__(self):
        self.GridRowCount = 0
        self.testItemsData = load_json_from_file("resource/config/user_testCfg.json")

        # 确保testItemsData是一个字典
        if isinstance(self.testItemsData, dict):
            testItemsList = self.testItemsData.get("TestItems", [])
            # 确保testItemsList是一个列表
            if isinstance(testItemsList, list):
                self.testItems = []
                director = Director()
                for testItemData in testItemsList:
                    testItem = director.construct(testItemData)
                    self.testItems.append(testItem)
            else:
                print("testItemsList is not a list.")
        else:
            print("testItemsData is not a dictionary.")

    @staticmethod
    def create_component_enable(testParam, widget):
        if testParam.enable:
            setattr(widget, testParam.funName + "CheckBox", CheckBox(testParam.dspName, widget))
            getattr(widget, testParam.funName + "CheckBox").setChecked(True)
        else:
            setattr(widget, testParam.funName + "CheckBox", CheckBox(testParam.dspName, widget))
            getattr(widget, testParam.funName + "CheckBox").setChecked(False)

    def create_component_test_item(self, testParam, widget):
        if testParam.type == "Value":
            setattr(widget, testParam.funName + "Label", BodyLabel(testParam.dspName + testParam.describe, widget))
            widget.QGridLayOut.addWidget(getattr(widget, testParam.funName + "Label"), self.GridRowCount, 0,
                                         Qt.AlignLeft)

            setattr(widget, testParam.funName + "maxEdit", IntEditBox(testParam.maxValue, widget))
            setattr(widget, testParam.funName + "minEdit", IntEditBox(testParam.minValue, widget))

            widget.QGridLayOut.addWidget(getattr(widget, testParam.funName + "maxEdit"), self.GridRowCount, 1,
                                         Qt.AlignRight)
            widget.QGridLayOut.addWidget(getattr(widget, testParam.funName + "minEdit"), self.GridRowCount, 2,
                                         Qt.AlignRight)
            self.GridRowCount += 1

        if testParam.type == "bool":
            setattr(widget, testParam.funName + "Label", BodyLabel(testParam.dspName + testParam.unit, widget))
            widget.QGridLayOut.addWidget(getattr(widget, testParam.funName + "Label"), self.GridRowCount, 0,
                                         Qt.AlignLeft)
            setattr(widget, testParam.funName + "CheckBox", CheckBox(testParam.dspName + testParam.unit, widget))
            widget.QGridLayOut.addWidget(getattr(widget, testParam.funName + "Button"), self.GridRowCount, 1,
                                         Qt.AlignRight)
            self.GridRowCount += 1


if __name__ == '__main__':
    # 读配置文件
    testItemsData = load_json_from_file("resource/config/user_testcfg.json")

    testItemsSize = len(testItemsData.get("TestItems", []))
    # 确保testItemsData是一个字典
    if isinstance(testItemsData, dict):
        testItemsList = testItemsData.get("TestItems", [])
        # 确保testItemsList是一个列表
        if isinstance(testItemsList, list):
            testItems = []
            director = Director()
            for testItemData in testItemsList:
                testItem = director.construct(testItemData)
                testItems.append(testItem)
        else:
            print("testItemsList is not a list.")
    else:
        print("testItemsData is not a dictionary.")

    for item in testItems:
        print(item)
