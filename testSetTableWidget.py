import json
import sys

import pandas as pd
from PyQt5.QtCore import Qt, QAbstractTableModel, QSize, QByteArray, QDataStream, QIODevice, QMimeData, QVariant, \
    QModelIndex
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget, QMainWindow, QHeaderView, QSizePolicy, \
    QAbstractItemView

from qfluentwidgets import TableView, TableItemDelegate


class CustomTableItemDelegate(TableItemDelegate):
    """ Custom table item delegate """

    # def paint(self, painter, option, index):
    #     text = index.model().data(index, Qt.DisplayRole)
    #     painter.save()
    #     painter.setFont(option.font)
    #
    #     # 使用QStyle来绘制背景和边框
    #     style = option.widget.style()
    #     options = QStyleOptionViewItem(option)
    #     options.rect.setWidth(option.rect.width())
    #     options.rect.setHeight(option.rect.height())
    #     style.drawPrimitive(QStyle.PE_PanelItemViewItem, options, painter, option.widget)
    #
    #     # 绘制文本
    #     textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options, option.widget)
    #     painter.drawText(textRect, Qt.AlignCenter, text)
    #     painter.restore()
    # super().paint()

    def sizeHint(self, option, index):
        # super().sizeHint(option,index)
        text = index.model().data(index, Qt.DisplayRole)
        fontMetrics = QFontMetrics(option.font)
        lines = text.split('\n')
        height = fontMetrics.height() * (len(lines) if lines else 1)
        height = height + 10
        return option.decorationSize + QSize(0, height)


class myTableModel(TableView):
    def __init__(self, jsonData=None):
        super().__init__()
        # 存储所有去重后的name
        self.unique_names = set()
        self.jsonData = jsonData
        self.header = self.jsonData[0].keys()

        df = self.__fillTableByJson()
        self.TableModel = PandasModel(df)

        self.setDragEnabled(True)  # 允许拖拽
        self.setAcceptDrops(True)  # 允许放置
        self.setDragDropOverwriteMode(False)  # 防止拖拽时覆盖其它数据
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setModel(self.TableModel)
        # self.setItemDelegate(EditableDelegate(self))
        self.verticalHeader().hide()
        self.setBorderVisible(True)
        self.setBorderRadius(8)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def __fillTableByJson(self):
        # 以name, type, value作为列标题的数据列表
        data_list = []

        for item in self.jsonData:
            enable = item.get("enable", False)
            if not enable:
                continue
            headerName = next(iter(item))
            nameValue = item.get(headerName)
            # 如果name还未被处理过，添加到集合和数据列表
            if nameValue and nameValue not in self.unique_names:
                self.unique_names.add(nameValue)
                itemlist = item
                ret1 = itemlist.pop(headerName, None)
                ret2 = itemlist.pop("enable", None)
                if ret1 and ret2:
                    data_list.append(itemlist)

        # 将数据列表转换为DataFrame
        return pd.DataFrame(data_list)

    def updateData(self, jsonObj):
        state = jsonObj.get("enable", "")
        if not state:
            cmd = jsonObj.get("cmd", "")
            row = PandasModel.search(self.TableModel, 2, cmd)
            if row is not None:
                self.TableModel.removeRow(row)
        else:
            headerName = next(iter(jsonObj))
            nameValue = jsonObj.get(headerName)
            if nameValue and nameValue not in self.unique_names:
                self.unique_names.add(nameValue)
                itemlist = jsonObj
                ret1 = itemlist.pop(headerName, None)
                ret2 = itemlist.pop("enable", None)
                if ret1 and ret2:
                    self.TableModel.appendRow(itemlist)

    def resizeEvent(self, event):
        # 调整列宽
        super().resizeEvent(event)  # 调用父类的resizeEvent方法以确保窗口大小的自适应

        header = self.horizontalHeader()
        # 假设模型中有一些数据，因此有列
        column_count = self.model().columnCount()
        # 设置倒数第二列既适应内容又拉伸
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        # 将倒数第二列的调整模式设置为 Stretch
        # header.setSectionResizeMode(column_count - 2, QHeaderView.Stretch)
        # 设置列宽模式为Interactive，允许用户手动调整列宽
        # header.setSectionResizeMode(QHeaderView.Interactive)

        # 首次调整列宽以适应内容
        self.resizeColumnsToContents()

        # 确保列宽至少是min_section_size
        min_section_size = 80  # 设置最小列宽
        for section in range(header.count()):
            if (section == 0):
                header.resizeSection(section, 280)
                continue
            header.resizeSection(section, max(header.sectionSize(section), min_section_size))


class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super(PandasModel, self).__init__()
        self._data = data

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
        if role == Qt.DisplayRole or role == Qt.EditRole:
            # 获取数据
            value = self._data.iloc[index.row(), index.column()]
            return str(value)

        elif role == Qt.TextAlignmentRole:
            # 返回对齐方式为居中
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
        return False

    def flags(self, index):
        # 返回索引的 flags
        flags = super().flags(index)
        flags |= Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
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

        targetRow = row if row != -1 else self.rowCount()

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
