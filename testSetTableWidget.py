import json
import sys

import pandas as pd
from PyQt5.QtCore import Qt, QAbstractTableModel, QSize, QByteArray, QDataStream, QIODevice, QMimeData, QVariant, \
    QModelIndex, QPoint, pyqtSignal
from PyQt5.QtGui import QFontMetrics, QColor, QPainter, QPen
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget, QMainWindow, QHeaderView, QSizePolicy, \
    QAbstractItemView

from qfluentwidgets import TableView, TableItemDelegate


class CustomTableItemDelegate(TableItemDelegate):
    """ Custom table item delegate """

    def sizeHint(self, option, index):
        """
        Gets the size hint of item delegate.

        Args:
            option (QStyleOptionViewItem): The style option of item.
            index (QModelIndex): The model index of item.

        Returns:
            QSize: The size hint of item delegate.
        """
        text = index.model().data(index, Qt.DisplayRole)
        if text is not None:
            text = str(text)  # Convert QVariant to string
            fontMetrics = QFontMetrics(option.font)
            lines = text.split('\n')
            height = fontMetrics.height() * (len(lines) if lines else 1)
            height = height + 10
            return option.decorationSize + QSize(0, height)
        return option.decorationSize


class myTableModel(TableView):
    dropRowChangeSin = pyqtSignal(int)

    def __init__(self, jsonData=None):
        super().__init__()
        self.initialRow = -1  # 用于存储拖拽行的初始行数
        self.dropRow = -1  # 用于存储拖拽行的目标位置
        self.dropHighlightColor = QColor(0, 0, 0, 20)  # 高亮颜色
        self.initialMousePos = None  # 用于存储初始拖拽时的鼠标位置

        # 存储所有去重后的name
        self.unique_names = set()
        self.jsonData = jsonData

        if not self.jsonData:
            return None

        self.header = self.jsonData[0].keys()

        df = self.__fillTableByJson()
        self.TableModel = PandasModel(df,"enable")
        self.dropRowChangeSin.connect(self.TableModel.droprowRev)


        self.setDragEnabled(True)  # 允许拖拽
        self.setAcceptDrops(True)  # 允许放置
        self.setDragDropOverwriteMode(False)  # 防止拖拽时覆盖其它数据
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setModel(self.TableModel)
        self.setItemDelegate(CustomTableItemDelegate(self))
        self.setColumnHidden(0, True)  # 隐藏第一列

        self.verticalHeader().hide()
        self.setBorderVisible(True)
        self.setBorderRadius(8)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def __fillTableByJson(self):
        # 以name, type, value作为列标题的数据列表
        data_list = []

        if self.jsonData:
            for item in self.jsonData:
                # 获取测试项类型名称
                headerName = next(iter(item))
                nameValue = item.get(headerName)
                # 如果name还未被处理过，添加到集合和数据列表
                if nameValue and nameValue not in self.unique_names:
                    self.unique_names.add(nameValue)
                    itemlist = item
                    # ret1 = itemlist.pop(headerName, None)
                    # ret2 = itemlist.pop("enable", None)
                    # if ret1:
                    data_list.append(itemlist)

        # 将数据列表转换为DataFrame
        return pd.DataFrame(data_list)

    def getHighOfTable(self) -> int:
        # 假设 tableView 是你的 QTableView 实例
        rowHeight = self.rowHeight(0)  # 假设至少有一行
        rowCount = self.TableModel.rowCount()

        return rowHeight * (rowCount + 1)

    def forbidEdit(self, state: bool):
        if state:
            self.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.TableModel.setCheckBoxEditable(False)
            self.setDragEnabled(False)
            self.setAcceptDrops(False)  # 不允许放置

        else:
            self.setEditTriggers(QAbstractItemView.AllEditTriggers)
            self.TableModel.setCheckBoxEditable(True)
            self.setDragEnabled(True)
            self.setAcceptDrops(True)

    def updateData2Json(self) -> dict:
        """
        将 QAbstractItemModel 转换为字典格式的 JSON 数据。
        注意：此函数假设模型结构是简单的表格形式，没有分层。
        """
        data = []
        rowCount = self.TableModel.rowCount()
        columnCount = self.TableModel.columnCount()

        # 更新并保存数据

        for row in range(rowCount):
            row_data = {}
            for column in range(columnCount):
                index = self.TableModel.index(row, column, QModelIndex())
                if self.TableModel.headerData(column, Qt.Horizontal, Qt.DisplayRole) == 'enable':
                    value = bool(self.TableModel.data(index, Qt.CheckStateRole))
                else:
                    value = self.TableModel.data(index, Qt.DisplayRole)
                key = self.TableModel.headerData(column, Qt.Horizontal, Qt.DisplayRole)
                if key == 'interval(ms)' or key == 'retry':
                    value = int(value)

                row_data[key] = value
            data.append(row_data)

        return data

    def dragEnterEvent(self, event):
        # 记录初始拖拽位置
        self.initialMousePos = event.pos()
        self.initialRow = self.indexAt(event.pos()).row()
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self.initialMousePos is None:
            super().dragMoveEvent(event)
            return

        # 保持水平位置不变，即使用初始的X坐标
        currentVerticalPosition = event.pos().y()
        fixedHorizontalPosition = self.initialMousePos.x()

        # 创建新的位置，其中X坐标是初始的，Y坐标是当前的
        adjustedPos = QPoint(fixedHorizontalPosition, currentVerticalPosition)

        # 使用adjustedPos来确定索引和行
        index = self.indexAt(adjustedPos)
        row = index.row()

        # 计算鼠标位置对应的行的中点，决定指示线位置
        LineRowMidY = self.rowViewportPosition(row) + self.rowHeight(row) / 2

        # print("dropRow:" + str(LineRowMidY) + "   initialRow:" + str(adjustedPos.y()))
        if adjustedPos.y() < LineRowMidY:
            self.dropRow = row
        else:
            self.dropRow = row + 1

        # 计算鼠标位置对应的未来行的中点，决定指示线位置
        SendRowMidY = self.rowViewportPosition(row) + self.rowHeight(row) / 2
        if row > self.initialRow:
            if adjustedPos.y() > SendRowMidY:
                SendRow = row
            else:
                SendRow = row - 1
        else:
            if adjustedPos.y() > SendRowMidY:
                SendRow = row + 1
            else:
                SendRow = row

        # print("dropRow:" + str(SendRow) + "   initialRow:" + str(self.indexAt(self.initialMousePos).row()))

        self.dropRowChangeSin.emit(SendRow)

        event.setDropAction(Qt.MoveAction)
        event.accept()
        self.update()

    def dropEvent(self, event):
        index = self.indexAt(event.pos())
        # row = index.row()
        # mousePos = event.pos()
        # rowMidY = self.rowViewportPosition(row) + self.rowHeight(row) / 2
        #
        # # 决定最终放置的行
        # if mousePos.y() < rowMidY:
        #     self.dropRow = row
        # else:
        #     self.dropRow = row + 1

        event.setDropAction(Qt.MoveAction)
        super().dropEvent(event)
        event.accept()
        self.update()
        self.dropRow = -1  # 重置为-1表示没有高亮
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.dropRow != -1:
            painter = QPainter(self.viewport())
            # 计算行的y坐标
            y = self.rowViewportPosition(self.dropRow)

            # 最后绘制实际的细线
            finalPen = QPen(QColor(0, 0, 0), 1, Qt.SolidLine)  # 黑色的实线，宽度为1
            painter.setPen(finalPen)
            painter.drawLine(0, y, self.width(), y)


    # def updateData(self, jsonObj):
    #     state = jsonObj.get("enable", "")
    #     if not state:
    #         cmd = jsonObj.get("cmd", "")
    #         row = PandasModel.search(self.TableModel, 2, cmd)
    #         if row is not None:
    #             self.TableModel.removeRow(row)
    #     else:
    #         headerName = next(iter(jsonObj))
    #         nameValue = jsonObj.get(headerName)
    #         if nameValue and nameValue not in self.unique_names:
    #             self.unique_names.add(nameValue)
    #             itemlist = jsonObj
    #             ret1 = itemlist.pop(headerName, None)
    #             ret2 = itemlist.pop("enable", None)
    #             if ret1 and ret2:
    #                 self.TableModel.appendRow(itemlist)

    def resizeEvent(self, event):
        # 调整列宽
        super().resizeEvent(event)  # 调用父类的resizeEvent方法以确保窗口大小的自适应

        headers = self.horizontalHeader()
        # 假设模型中有一些数据，因此有列
        column_count = self.model().columnCount()

        # 确保列宽至少是min_section_size
        min_section_size = 70  # 设置最小列宽
        for section in range(column_count):
            column_title = headers.model().headerData(section, Qt.Horizontal,Qt.DisplayRole)
            if column_title == "data" or column_title == "rev_dict":
                headers.setSectionResizeMode(section, QHeaderView.Stretch)
            if column_title == "dspName":
                headers.resizeSection(section, 250)
            headers.resizeSection(section, max(headers.sectionSize(section), min_section_size))
        # 将倒数第二列的调整模式设置为 Stretch
        # header.setSectionResizeMode(column_count - 2, QHeaderView.Stretch)
        # 设置列宽模式为Interactive，允许用户手动调整列宽
        # header.setSectionResizeMode(QHeaderView.Interactive)

        # 首次调整列宽以适应内容
        self.resizeColumnsToContents()


        for section in range(headers.count()):
            name = headers.model().headerData(section, Qt.Horizontal, Qt.DisplayRole)
            if name == 'dspName':
                headers.resizeSection(section, 250)
                continue
            if name == 'enable':
                headers.resizeSection(section, 60)
                continue
            headers.resizeSection(section, max(headers.sectionSize(section), min_section_size))

class PandasModel(QAbstractTableModel):

    def __init__(self, data, checkable_column_name=None):
        super(PandasModel, self).__init__()
        self._data = data
        self.checkable_column_name = checkable_column_name  # 设置可勾选列的名称
        self.droprow = -1

    def droprowRev(self, row):
        self.droprow = row

    def appendRow(self, new_row_data):
        self.beginInsertRows(QModelIndex(), self.rowCount(),
                             self.rowCount())  # 在末尾插入            # 将 new_row_data 添加到 self._data 和 self.filtered_data
        self._data = self._data.append(new_row_data, ignore_index=True)
        self.endInsertRows()

    def removeRow(self, row):
        self.beginRemoveRows(QModelIndex(), row, row)
        # 从 self._data 和 self.filtered_data 中移除指定行
        self._data = self._data.drop(row)
        self.filtered_data = self.filtered_data.drop(row)
        self.endRemoveRows()

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.CheckStateRole:
            # 根据列名查找索引
            checkable_column_index = self._data.columns.get_loc(self.checkable_column_name)
            if index.column() == checkable_column_index:
                # 返回复选框的状态
                return Qt.Checked if self._data.iat[index.row(), checkable_column_index] else Qt.Unchecked

        elif role == Qt.DisplayRole or role == Qt.EditRole:
            # 对于非复选框列，正常显示数据
            checkable_column_index = self._data.columns.get_loc(self.checkable_column_name)
            if index.column() != checkable_column_index:
                value = self._data.iloc[index.row(), index.column()]
                return str(value)
            # 对于复选框列，不显示任何内容
            return QVariant()

        elif role == Qt.TextAlignmentRole:
            return int(Qt.AlignHCenter | Qt.AlignVCenter)

        return QVariant()

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._data.columns[section]
            else:
                return self._data.index[section]
        return None

    def getData(self, row, col):
        # 查找DataFrame中的数据
        value = self._data.iat[row, col]
        return value

    # 添加对数据进行修改的方法
    def update_data(self, row, col, value):
        assert isinstance(row, int), "row must be an integer"
        assert isinstance(col, int), "col must be an integer"
        self._data.iat[row, col] = value
        index = self.createIndex(row, col)
        self.dataChanged.emit(index, index)

    # 如果需要支持编辑
    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            # 更新Pandas DataFrame中的数据
            self._data.iat[index.row(), index.column()] = value
            # 发出数据变更信号
            self.dataChanged.emit(index, index)
            return True
        elif role == Qt.CheckStateRole:
            checkable_column_index = self._data.columns.get_loc(self.checkable_column_name)
            if index.column() == checkable_column_index:
                self._data.iat[index.row(), checkable_column_index] = value == Qt.Checked
                self.dataChanged.emit(index, index, [Qt.DisplayRole])
                return True
        return False

    def setCheckBoxEditable(self, editable):
        self.editable = editable

    def flags(self, index):
        flags = super().flags(index)
        flags |= Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        # 根据列名查找索引
        checkable_column_index = self._data.columns.get_loc(self.checkable_column_name)
        if index.column() == checkable_column_index:
            if self.editable:
                flags |= Qt.ItemIsUserCheckable  # 允许复选框交互
                flags &= ~Qt.ItemIsEditable  # 移除编辑标志
            else:
                flags &= ~(Qt.ItemIsUserCheckable | Qt.ItemIsEditable)  # 禁止复选框交互和编辑
        else:
            if self.editable:
                flags |= Qt.ItemIsEditable  # 允许其他列编辑
        return flags


    # 如果要支持拖动行
    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        return ["application/x-qabstractitemmodeldatalist"]

    def mimeData(self, indexes):
        encodedData = QByteArray()
        stream = QDataStream(encodedData, QIODevice.WriteOnly)
        for index in indexes:
            if index.isValid():
                stream.writeInt(index.row())
        mimeData = QMimeData()
        mimeData.setData("application/x-qabstractitemmodeldatalist", encodedData)
        return mimeData

    def dropMimeData(self, data, action, row, column, parent):
        if action == Qt.IgnoreAction:
            return True
        if not data.hasFormat("application/x-qabstractitemmodeldatalist"):
            return False

        encodedData = data.data("application/x-qabstractitemmodeldatalist")
        stream = QDataStream(encodedData, QIODevice.ReadOnly)
        sourceRow = stream.readInt()

        row = self.droprow
        print("sourceRow:", sourceRow, "row:", row)

        if row != -1:
            targetRow = row
        else:
            return False

        # 使用pandas的方法重新排序行
        # 从源行删除，然后插入到目标位置
        moved_row = self._data.iloc[sourceRow]  # 获取要移动的行
        self._data = self._data.drop(self._data.index[sourceRow])  # 删除该行
        if targetRow == self.rowCount():  # 如果是移动到末尾
            self._data = pd.concat([self._data, pd.DataFrame(moved_row).T])
        else:
            self._data = pd.concat(
                [self._data.iloc[:targetRow], pd.DataFrame(moved_row).T, self._data.iloc[targetRow:]])

        return True

    def search(self, column, value):
        # 使用Pandas来查找匹配的值
        mask = self._data[self._data.columns[column]] == value
        matching_rows = mask[mask].index.tolist()
        return matching_rows[0] if matching_rows else None


if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    window = QMainWindow()
    with open('resources/config/userConfig.json', 'r', encoding='utf-8', errors='ignore') as file:
        jsondata = json.load(file)

    ex = myTableModel(jsondata["TestItems"])

    # ex.updateData(41, "string", "{version:1.0.0}")
    # ex.updateData(29, "string", 40)
    # 设置窗口布局
    layout = QHBoxLayout()
    layout.addWidget(ex)
    centralWidget = QWidget()
    centralWidget.setLayout(layout)
    window.setCentralWidget(centralWidget)

    window.show()
    sys.exit(app.exec_())
