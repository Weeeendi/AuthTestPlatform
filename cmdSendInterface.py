import json
import os

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHeaderView, QSizePolicy, QHBoxLayout

from baseLogger import log
from qfluentwidgets import ToolButton, FluentIcon, LineEdit, CheckBox, TableWidget, PushButton, BodyLabel, Flyout, \
    InfoBarIcon, SpinBox, TransparentToolButton

MAX_CONSTANT = float('inf')

class Dp_Row:
    def __init__(self, select=False, des='', hexx=''):
        self.select = select
        self.des = des
        self.hexx = hexx

    def to_dict(self):
        return {
            "select": self.select,
            "des": self.des,
            "hexx": self.hexx,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(d.get("select"), d.get("des"), d.get("hexx"))


def check_data(typeName: str, data, minLimit=0, maxLimit=MAX_CONSTANT) -> bool:
    if not isinstance(data, str):
        return False

    if typeName == "HEX":
        data = data.replace(" ", "")

        if len(data) % 2 != 0:
            return False

        try:
            for i in range(0, len(data), 2):
                hexx = int(data[i:i + 2], 16)
                if hexx < 0 or hexx > 255:
                    return False
            return True
        except ValueError:
            return False

    if typeName == "INT":
        try:
            number = int(data)
            if minLimit <= number <= maxLimit:
                return True
            else:
                return False
        except ValueError:
            return False
        pass

    if typeName == "URL":
        if not data.startswith("http://") and not data.startswith("https://"):
            return False

    return True


class DP_ListTable(QWidget):
    dataPointSignal = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.filename = "resource/user/send_dp_list.json"
        self.totalItems = 0
        self.isProcessingDelete = False
        self.initUI()

    def initUI(self):
        self.LayOut = QVBoxLayout(self)

        # 创建发送布局
        self.SendLayout = QHBoxLayout()
        self.saveButton = ToolButton(FluentIcon.SAVE)

        self.saveButton.clicked.connect(self.saveTheDpList)
        self.delButton = ToolButton(FluentIcon.DELETE)
        if os.path.exists(self.filename):
            self.delButton.setDisabled(False)
        else:
            self.delButton.setDisabled(True)

        self.delButton.clicked.connect(self.deleteAllDpList)

        # 创建表格
        self.table = TableWidget()

        self.table.setRowCount(2)  # 设置行数
        self.table.setColumnCount(4)  # 设置列数

        # 设置表格头
        self.table.setWordWrap(False)
        self.table.setHorizontalHeaderLabels(['select', 'describe', 'dp date', 'del'])

        if not self.loadTheDpList():
            # 无法加载到用户的数据，添加默认的数据

            checkBox = CheckBox()
            self.table.setCellWidget(self.totalItems, 0, checkBox)
            checkBox.stateChanged.connect(lambda :self.saveButton.setDisabled(False))

            deslineEdit = LineEdit()
            deslineEdit.setMaximumHeight(30)
            deslineEdit.setPlaceholderText("描述")
            deslineEdit.textChanged.connect(lambda :self.saveButton.setDisabled(False))
            self.table.setCellWidget(self.totalItems, 1, deslineEdit)

            lineEdit = LineEdit()
            lineEdit.editingFinished.connect(self.onHexEditChanged)
            lineEdit.textChanged.connect(lambda :self.saveButton.setDisabled(False))
            lineEdit.setMaximumHeight(30)
            lineEdit.setPlaceholderText("命令内容")
            self.table.setCellWidget(self.totalItems, 2, lineEdit)

            deleteButton = TransparentToolButton(FluentIcon.DELETE)

            deleteButton.setMaximumSize(30, 30)
            self.table.setCellWidget(self.totalItems, 3, deleteButton)
            deleteButton.clicked.connect(self.deleteCommand)
            self.totalItems += 1

        self.addButton = ToolButton(FluentIcon.ADD)
        self.addButton.clicked.connect(self.addCommand)
        self.addButton.setMaximumHeight(30)
        self.table.setSpan(self.totalItems, 0, 1, 4)
        self.table.setCellWidget(self.totalItems, 0, self.addButton)

        # 让第二列扩展以填充可用空间
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setRowHeight(self.totalItems, 35)

        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.LayOut.addWidget(self.table)

        # 创建参数布局
        self.ParamsLayout = QHBoxLayout()
        self.IntervalName = BodyLabel("Interval")
        self.IntervalName.setMaximumWidth(50)

        self.Interval = SpinBox()
        self.Interval.setRange(20, 9999)
        self.Interval.setMaximumWidth(140)
        self.IntervalUnit = BodyLabel("ms/times")
        self.ParamsLayout.addWidget(self.IntervalName, Qt.AlignLeft)
        self.ParamsLayout.addWidget(self.Interval, Qt.AlignLeft)
        self.ParamsLayout.addWidget(self.IntervalUnit, Qt.AlignLeft)

        self.LayOut.addLayout(self.ParamsLayout)

        self.SendLayout.addWidget(self.saveButton)
        self.SendLayout.addWidget(self.delButton)
        self.SendLayout.addStretch()

        self.cancelButton = ToolButton(FluentIcon.CANCEL)

        self.sendButton = PushButton("发送")

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        self.sendButton.setSizePolicy(sizePolicy)
        self.sendButton.clicked.connect(self.sendDpCommand)
        self.SendLayout.addWidget(self.sendButton)

        self.saveButton.setDisabled(True)

        self.LayOut.addLayout(self.SendLayout)

    def showFlyout(self, icon: InfoBarIcon, title, content, Widget_object):
        Flyout.create(
            icon=icon,
            title=title,
            content=content,
            target=Widget_object,
            parent=self,
            isClosable=False
        )

    def deleteAllDpList(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)
            self.showFlyout(InfoBarIcon.SUCCESS, "提示", "删除数据成功", self)
        else:
            self.showFlyout(InfoBarIcon.ERROR, "提示", "删除数据失败,文件不存在", self.delButton)

        self.delButton.setDisabled(True)

    def onHexEditChanged(self):
        # 获取发送信号的 QLineEdit
        edit = self.sender()
        text = edit.text()

        # 检查数据是否符合十六进制格式
        if not check_data("HEX", text):
            self.showFlyout(InfoBarIcon.ERROR, "提示", "请输入正确的十六进制数据", edit)
            edit.setText("")

    def addCommand(self, select=False, des='', hexx=''):

        self.table.insertRow(self.totalItems)  # 插入一行
        self.table.setRowCount(self.totalItems + 2)  # 设置列数

        checkBox = CheckBox()
        checkBox.setChecked(select)
        checkBox.stateChanged.connect(lambda :self.saveButton.setDisabled(False))
        self.table.setCellWidget(self.totalItems, 0, checkBox)

        deslineEdit = LineEdit()
        deslineEdit.textChanged.connect(lambda :self.saveButton.setDisabled(False))
        deslineEdit.setText(des)

        self.table.setCellWidget(self.totalItems, 1, deslineEdit)

        lineEdit = LineEdit()
        lineEdit.setText(hexx)
        lineEdit.editingFinished.connect(self.onHexEditChanged)
        lineEdit.textChanged.connect(lambda :self.saveButton.setDisabled(False))
        self.table.setCellWidget(self.totalItems, 2, lineEdit)

        deleteButton = TransparentToolButton(FluentIcon.DELETE)
        deleteButton.setMaximumSize(30, 30)
        deleteButton.clicked.connect(self.deleteCommand)
        self.table.setCellWidget(self.totalItems, 3, deleteButton)
        self.table.setRowHeight(self.totalItems, 35)
        self.totalItems += 1

    def saveTheDpList(self):
        dict_list = []
        DpList = []
        for row in range(self.totalItems):
            try:
                hexx = self.table.cellWidget(row, 2).text()
                if hexx == "":
                    continue
                select = self.table.cellWidget(row, 0).isChecked()
                des = self.table.cellWidget(row, 1).text()

            except AttributeError:
                log.logger.error("error:dp list not attribute")
                return

            dp_item = Dp_Row(select, des, hexx)
            DpList.append(dp_item)

        if len(DpList) == 0:
            self.showFlyout(InfoBarIcon.WARNING, "提示", "请先添加指令", self.saveButton)
            return

        # 将对象列表转换为字典列表
        for obj in DpList:
            if obj.hexx != '':
                dict_list.append(obj.to_dict())
        try:
            # 将字典列表写入JSON文件
            with open(self.filename, "w") as file:
                json.dump(dict_list, file, indent=4)

            self.showFlyout(InfoBarIcon.SUCCESS, "提示", "保存成功", self.table)
            self.delButton.setDisabled(False)
            self.saveButton.setDisabled(True)
        except IOError as e:
            log.logger.error(f"An error occurred while writing to file: {e.strerror}")

    def loadTheDpList(self) -> bool:
        cls = Dp_Row()
        DpList = []
        # 读取命令列表
        if os.path.exists(self.filename):
            # 从JSON文件中读取数据
            with open(self.filename, "r") as file:
                dict_list = json.load(file)

            # 将字典列表转换为对象列表
            DpList = [cls.from_dict(d) for d in dict_list]  # 使用列表推导式，并将结果直接赋值给 self.DpList

            if len(DpList) > 0:
                for i in range(len(DpList)):
                    # 遍历该行的每一列，并删除单元格的设置
                    self.addCommand(select=DpList[i].select, des=DpList[i].des,
                                    hexx=DpList[i].hexx)  # 添加dp列表数据到table
                return True
            else:
                log.logger.error("数据转换失败")
                return False

        else:
            log.logger.error("无dp存储数据")
            return False

    def deleteCommand(self):

        if self.isProcessingDelete:
            return  # 忽略重复的删除请求
        self.isProcessingDelete = True

        try:
            # 删除指定的命令布局
            btn = self.sender()
            btn.disconnect()
            # 获取按钮所在的行
            row = self.table.indexAt(btn.pos()).row()

            log.logger.debug("delete row %d" % row)

            # 遍历该行的每一列，并删除单元格的设置
            for col in range(self.table.columnCount()):
                self.table.setCellWidget(row, col, None)  # 移除单元格的小部件
                # 删除特定行
            if row != -1:  # 确保获取的行号有效
                self.table.removeRow(row)

            # 更新 totalItems 计数以反映当前的行数
            if self.totalItems > 0:
                self.totalItems -= 1

            # 调整行数以删除包含按钮的那一行
            self.table.setRowCount(self.totalItems + 1)
        finally:
            self.isProcessingDelete = False

        self.table.viewport().update()

    def sendDpCommand(self):
        log.logger.debug("sendDpCommand")
        hexxText = ""
        for row in range(self.totalItems):
            try:
                select = self.table.cellWidget(row, 0).isChecked()
                hexx = self.table.cellWidget(row, 2).text()
                if hexx == "" or select is False:
                    continue
                hexx = hexx.replace(" ", "")
                hexxText += hexx + ","

            except Exception as e:
                log.logger.error(e)
        Interval = int(self.Interval.value())

        self.dataPointSignal.emit(hexxText, Interval)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 初始化 UI
        self.initUI()

    def initUI(self):
        # 设置窗口标题
        self.setWindowTitle('PyQt Table Widget Example')

        # 创建一个 QTableWidget 实例
        self.table = DP_ListTable(self)

        self.QWidget = QWidget()
        self.layout = QVBoxLayout(self.QWidget)
        self.layout.addWidget(self.table)
        # 将 QTableWidget 实例放置在窗口中

        # 设置窗口大小
        self.resize(800, 600)
        self.setCentralWidget(self.QWidget)
        # 显示窗口
        self.show()


if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    app.exec_()
