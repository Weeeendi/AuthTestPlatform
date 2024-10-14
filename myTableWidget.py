import json
import sys

import pandas as pd
from PyQt5.QtCore import Qt, QAbstractTableModel, QSize
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget, QMainWindow, QHeaderView, QSizePolicy

from baseLogger import log
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

        self.jsonData = jsonData
        self.dpList = []

        df = self.__fillTableByJson()
        self.TableModel = PandasModel(df)
        self.setModel(self.TableModel)
        self.setItemDelegate(CustomTableItemDelegate(self))
        self.verticalHeader().hide()
        self.setBorderVisible(True)
        self.setBorderRadius(8)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def __fillTableByJson(self):
        # 存储所有去重后的name
        unique_names = set()

        # 以name, type, value作为列标题的数据列表
        data_list = []

        for item in self.jsonData:
            if item.get("msg") == "ver":
                continue
            name = item.get("name")
            dpid = int(item.get("id"))
            itype = item.get("property").get("type")
            value = item.get("defaultValue") if item.get("defaultValue") is not None else item.get("value", "")
            unit = item.get("property").get("unit") if item.get("property").get("unit") is not None else item.get(
                "property").get("unit", "")

            if itype == "enum" and value != '':
                enum_des = item.get("property").get("enum_desc").split(",")

                if int(value) >= len(enum_des):
                    return None

                value = enum_des[int(value)]

            # 如果name还未被处理过，添加到集合和数据列表
            if name and name not in unique_names:
                unique_names.add(name)
                data_list.append({"name": name, "dpid": dpid, "type": itype, "value": value, "unit": unit})

        # 将数据列表转换为DataFrame
        return pd.DataFrame(data_list)

    def updateData(self, id, type, value):
        row = PandasModel.search(self.TableModel, 1, id)
        if row is not None:
            if PandasModel.getData(self.TableModel, row, 2) != type:
                log.logger.error("数据类型不一致")
                return

            self.TableModel.update_data(row, 3, value)

            header = self.horizontalHeader()
            column_count = self.model().columnCount()
            # 设置倒数第二列既适应内容又拉伸
            # 设置倒数第二列既适应内容又拉伸
            self.resizeColumnsToContents()
            header.setSectionResizeMode(column_count - 2, QHeaderView.Stretch)
            # 将倒数第二列的调整模式设置为 Stretch
            # header.setSectionResizeMode(column_count - 2, QHeaderView.Stretch)

            # 确保列宽至少是min_section_size
            min_section_size = 100  # 设置最小列宽
            for section in range(header.count()):
                if (section == column_count - 1):
                    header.resizeSection(section, 100)
                    continue
                header.resizeSection(section, max(header.sectionSize(section), min_section_size))

        else:
            log.logger.error("数据非法,不在列表中的数据")
            log.logger.error(id)
            log.logger.error(value)

    def resizeEvent(self, event):
        # 调整列宽
        super().resizeEvent(event)  # 调用父类的resizeEvent方法以确保窗口大小的自适应

        header = self.horizontalHeader()
        # 假设模型中有一些数据，因此有列
        column_count = self.model().columnCount()
        # 设置倒数第二列既适应内容又拉伸
        header.setSectionResizeMode(column_count - 2, QHeaderView.Stretch)
        # 将倒数第二列的调整模式设置为 Stretch
        # header.setSectionResizeMode(column_count - 2, QHeaderView.Stretch)
        # 设置列宽模式为Interactive，允许用户手动调整列宽
        # header.setSectionResizeMode(QHeaderView.Interactive)

        # 首次调整列宽以适应内容
        self.resizeColumnsToContents()

        # 确保列宽至少是min_section_size
        min_section_size = 100  # 设置最小列宽
        for section in range(header.count()):
            if(section == column_count - 1):
                header.resizeSection(section, 100)
                continue
            header.resizeSection(section, max(header.sectionSize(section), min_section_size))



class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super(PandasModel, self).__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            # 获取数据
            value = self._data.iloc[index.row(), index.column()]
            return str(value)
        elif role == Qt.TextAlignmentRole:
            # 设置文本对齐方式为居中
            return Qt.AlignCenter

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
    with open('resources/config/dataPointCfg.json', 'r', encoding='utf-8', errors='ignore') as file:
        jsondata = json.load(file)

    ex = myTableModel(jsondata["BMS_Dp_Data"])

    ex.updateData(41, "string", "{version:1.0.0}")
    ex.updateData(29, "string", 40)
    # 设置窗口布局
    layout = QHBoxLayout()
    layout.addWidget(ex)
    centralWidget = QWidget()
    centralWidget.setLayout(layout)
    window.setCentralWidget(centralWidget)

    window.show()
    sys.exit(app.exec_())
