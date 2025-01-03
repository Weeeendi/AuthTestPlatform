import pandas as pd
from PyQt5.QtChart import (QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis)
from PyQt5.QtCore import Qt, QMargins, QPoint
from PyQt5.QtGui import QColor, QPainter, QFont
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QToolTip
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import baseUtils
from qfluentwidgets import MessageBox, themeColor
from resources.ui.ChartInterface_UI import Ui_ChartInterface_UI


def showMessage(title, content, parent=None):
    MessageBox(title, content, parent).show()


class DataAnalysis:
    """
    fileName:csv文件名
    PID:产品ID
    """
    result_stats = {
        "PASS_count": 0,
        "FAIL_count": 0,
        "PASS_avg_TIME_CONS": 0,
        "TOTAL_TIME_CONS": 0,
        "error_list": []
    }

    def __init__(self, fileName, PID):
        self.fileName = fileName
        self.PID = PID
        self.data = pd.read_csv(fileName)
        filtered_data = self.data[self.data['PID'] == PID]
        self.resultAnalysis = self.count_data(filtered_data)

    def count_data(self, df=None):
        # 统计RESULT列中PASS和FAIL的数量
        self.result_stats["PASS_count"] = (df['RESULT'] == 'PASS').sum()
        self.result_stats["FAIL_count"] = (df['RESULT'] == 'FAIL').sum()
        self.result_stats["TOTAL_TIME_CONS"] = df['TIME_CONS(s)'].sum()

        # 计算PASS行中TIME_CONS(s)的平均值
        if self.result_stats["PASS_count"] > 0:
            self.result_stats["PASS_avg_TIME_CONS"] = df[df['RESULT'] == 'PASS']['TIME_CONS(s)'].mean()

        # 获取错误项的名称及出现次数
        error_counts = {}
        for index, row in df[df['RESULT'] == 'FAIL'].iterrows():
            for column in df.columns[1:-1]:  # 假设第一列是标识列，最后一列是RESULT
                if row[column] is False:
                    if column in error_counts:
                        error_counts[column] += 1
                    else:
                        error_counts[column] = 1

        # 将错误统计结果转换为指定的字典列表格式
        for err_name, err_cnt in error_counts.items():
            self.result_stats["error_list"].append({"errName": err_name, "errCnt": err_cnt})

        return self.result_stats


class ChartRecordInterface(Ui_ChartInterface_UI, QWidget):
    # errorList = ['开始授权', '获取MAC', '请求接口', '读取授权', 'GSensor', 'Lte', 'BLE-Rssi', 'Flash',
    #              '主电池电压', '副电池电压', 'GPS']

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.errorList = []
        self.errorCntList = []
        self.setupUi(self)
        self.loadRecord()

        # hide
        self.LisenceNums.hide()
        self.LisenceTotleNum.hide()
        self.LisenceLeftCnt.hide()
        self.BodyLabel_3.hide()

        # add shadow effect to card
        self.setShadowEffect(self.SearchCard)
        self.setShadowEffect(self.DataCard)
        self.setShadowEffect(self.FailReasonCard)

    def drawChart(self):
        indexList = list(range(1, len(self.errorList) + 1))
        df = pd.DataFrame(self.errorCntList, columns=['a'], index=indexList)

        df['故障'] = self.errorList
        # 对图表排序后进行显示
        df = df.sort_values(by=df.columns[0], ascending=False)

        cols = list(df.columns)
        # valuesArray = list(df.values)
        series = QBarSeries()

        setTemp = QBarSet('Values')
        setTemp.append(df['a'].astype(int))
        series.append(setTemp)

        chart = QChart()
        chart.addSeries(series)

        chart.setAnimationOptions(QChart.SeriesAnimations)

        maxValue = df['a'].max()
        axisY = QValueAxis()
        axisY.setRange(0, maxValue * 2)
        axisY.applyNiceNumbers()
        axisY.setLabelFormat("%d")
        chart.addAxis(axisY, Qt.AlignLeft)
        series.attachAxis(axisY)

        self.axis_x = QBarCategoryAxis()
        self.axis_x.clear()
        self.axis_x.append(df['故障'])
        self.axis_x.setLabelsAngle(45)
        self.axis_x.setLabelsFont(QFont('Microsoft YaHei', pointSize=8))
        chart.addAxis(self.axis_x, Qt.AlignBottom)
        series.attachAxis(self.axis_x)
        # 添加工具提示

        # 连接 hovered 信号到槽函数
        series.hovered.connect(self.showTooltip)

        chart.legend().setVisible(False)
        chart.legend().setAlignment(Qt.AlignBottom)

        chart.setBackgroundVisible(False)
        self.chartView = QChartView(chart)
        self.chartView.setRenderHint(QPainter.Antialiasing)
        # 去除边框
        self.chartView.chart().setMargins(QMargins(0, 0, 0, 0))
        self.FailReasonLayout.addWidget(self.chartView)

    def showTooltip(self, state, index):
        if state:  # 确保索引有效
            value = self.errorCntList[index]
            # 获取柱子的位置
            barRect = self.chartView.chart().plotArea()
            barWidth = barRect.width() / len(self.errorCntList)
            xPos = barRect.topLeft().x() + barWidth / 2 + index * barWidth
            yPos = barRect.topLeft().y()
            # 设置工具提示的位置
            # 将窗口坐标转换为屏幕坐标
            globalPos = self.chartView.mapToGlobal(QPoint(xPos, yPos))
            # self.chartView.setToolTip(f"故障数量: {value}")
            QToolTip.showText(globalPos, f"故障数量: {value}")  # 显示在 (xPos, yPos) 位置
        else:
            QToolTip.hideText()

    def drawPieChart(self, success, fail):
        # 设置饼图数据
        self.figure = Figure(figsize=(3, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        labels = ['成功', '失败']
        sizes = [success, fail]
        r, g, b, _ = themeColor().getRgb()
        hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
        colors = [hex_color, '#ff9999']
        explode = (0.05, 0.05)

        self.ax.pie(sizes, explode=explode, labels=labels, colors=colors,
                    autopct='%1.1f%%', shadow=True, startangle=140,
                    textprops={'fontproperties': 'Microsoft YaHei', 'color': 'black'})
        self.ax.axis('equal')
        self.figure.set_alpha(0)
        self.figure.set_facecolor('none')
        # 去除白底
        self.ax.set_facecolor('none')  # 或者使用其他颜色，如 'black'

        self.canvas.draw()
        self.canvas.flush_events()

    def showChart(self, success, fail):
        self.PieLayOut = QVBoxLayout()
        self.drawPieChart(success, fail)

        self.drawChart()
        # 创建图表视图
        self.PieLayOut.addWidget(self.canvas)

        self.ProdTestDataLayout.addLayout(self.PieLayOut)
        self.chartView.setStyleSheet('QWidget {background:transparent}')
        self.canvas.setStyleSheet('QWidget {background:transparent}')

    def loadRecord(self):
        self.csvPcb = DataAnalysis(baseUtils.resource_path("output\\regList_YJ0003kj2u_20241219.csv"), "YJ0003kj2u")
        for item in self.csvPcb.result_stats["error_list"]:
            self.errorList.append(item["errName"])
            self.errorCntList.append(item["errCnt"])

        self.averageTime = self.csvPcb.result_stats["PASS_avg_TIME_CONS"]
        self.showChart(self.csvPcb.result_stats["PASS_count"], self.csvPcb.result_stats["FAIL_count"])
        self.updateSummary()

    def updateSummary(self):
        self.SuccessCnt.setText(str(self.csvPcb.result_stats["PASS_count"]))
        self.FailCnt.setText(str(self.csvPcb.result_stats["FAIL_count"]))
        self.TestAvgTimeLabel.setText(str(self.csvPcb.result_stats["PASS_avg_TIME_CONS"]) + "s")
        self.csvPcb.result_stats["TOTAL_TIME_CONS"] = int(self.csvPcb.result_stats["TOTAL_TIME_CONS"])
        if self.csvPcb.result_stats["TOTAL_TIME_CONS"] < 60:
            self.TestTotleTimeText_2.setText(str(self.csvPcb.result_stats["TOTAL_TIME_CONS"]) + "s")
        elif self.csvPcb.result_stats["TOTAL_TIME_CONS"] >= 60 and self.csvPcb.result_stats["TOTAL_TIME_CONS"] <= 3600:
            self.TestTotleTimeText_2.setText(str(self.csvPcb.result_stats["TOTAL_TIME_CONS"] / 60) + "min" +
                                             str(self.csvPcb.result_stats["TOTAL_TIME_CONS"] % 60) + "s")
        else:
            min = self.csvPcb.result_stats["TOTAL_TIME_CONS"] % 3600
            hour = self.csvPcb.result_stats["TOTAL_TIME_CONS"] / 3600
            s = min % 60
            self.TestTotleTimeText_2.setText(str(hour) + "h" + str(min / 60) + "min" + str(s) + "s")

    def setShadowEffect(self, card: QWidget):
        shadowEffect = QGraphicsDropShadowEffect(self)
        shadowEffect.setColor(QColor(0, 0, 0, 15))
        shadowEffect.setBlurRadius(10)
        shadowEffect.setOffset(0, 0)
        card.setGraphicsEffect(shadowEffect)


if __name__ == '__main__':
    filePath = baseUtils.resource_path("..\\output\\regList_YJ0003kj2u_20241219.csv")
    try:
        data = DataAnalysis(filePath, "YJ0003kj2u")
        data.count_data()
    except Exception as e:
        if e == BaseException:
            print("Please check the param")
        if e == FileNotFoundError:
            print("Please check the file path")
        print(str(e))
