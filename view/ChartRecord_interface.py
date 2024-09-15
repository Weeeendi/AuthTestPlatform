import numpy as np
import pandas as pd
from PyQt5.QtChart import (QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis, QPieSeries)
from PyQt5.QtCore import Qt, QMargins
from PyQt5.QtGui import QColor, QPainter, QFont
from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect, QFrame, QVBoxLayout

from qfluentwidgets import MessageBox, themeColor, BodyLabel
from resource.ui.ChartInterface_UI import Ui_ChartInterface_UI


def showMessage(title, content, parent=None):
    MessageBox(title, content, parent).show()


class ChartRecordInterface(Ui_ChartInterface_UI, QWidget):
    errorList = ['开始授权', '获取MAC', '请求接口', '读取授权', 'GSensor', 'Lte', 'BLE-Rssi', 'Flash',
                 '主电池电压', '副电池电压', 'GPS']

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.loadRecord()
        self.showChart(1000, 50)

        # add shadow effect to card
        self.setShadowEffect(self.SearchCard)
        self.setShadowEffect(self.DataCard)
        self.setShadowEffect(self.FailReasonCard)

    def drawChart(self):
        indexList = list(range(1, len(self.errorList) + 1))
        df = pd.DataFrame(np.random.randint(20, high=100, size=(len(self.errorList), 1)), columns=list('a'),
                          index=indexList)

        df['故障'] = self.errorList
        # 对图表排序后进行显示
        df = df.sort_values(by=df.columns[0], ascending=False)

        cols = list(df.columns)
        # valuesArray = list(df.values)
        series = QBarSeries()

        setTemp = QBarSet('Values')
        setTemp.append(df['a'].astype(float))
        series.append(setTemp)

        chart = QChart()
        chart.addSeries(series)

        chart.setAnimationOptions(QChart.SeriesAnimations)

        axisY = QValueAxis()
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

        chart.legend().setVisible(False)
        chart.legend().setAlignment(Qt.AlignBottom)

        chart.setBackgroundVisible(False)
        self.chartView = QChartView(chart)
        self.chartView.setRenderHint(QPainter.Antialiasing)
        # 去除边框
        self.chartView.chart().setMargins(QMargins(0, 0, 0, 0))
        self.FailReasonLayout.addWidget(self.chartView)

    def drawPieChart(self, success, fail):
        # 设置饼图数据
        self.pieSeries = QPieSeries()

        total = success + fail
        failPercent = int(fail * 1000 / total)
        self.pieSeries.append('fail ' + str('%d‰' % failPercent), fail)
        self.pieSeries.append("", success)
        # 'success ' + str('%d‰' % (1000-failPercent)
        success_color = themeColor()  # Green
        failure_color = "#F56C6C"  # Red
        # 处理索引号为1的片
        pieSlice = self.pieSeries.slices()[0]
        # pieSlice.setExploded()
        pieSlice.setLabelVisible(False)  # 设置标签可见,缺省不可见
        pieSlice.setLabelFont(QFont('Microsoft YaHei', pointSize=10))
        pieSlice.setBrush(QColor(failure_color))

        # 处理索引号为2的片
        pieSlice2 = self.pieSeries.slices()[1]
        pieSlice2.setExploded()
        pieSlice2.setLabelFont(QFont('Microsoft YaHei', pointSize=10))
        pieSlice2.setLabelVisible(False)  # 设置标签可见,缺省不可见
        # pieSlice2.setBorderWidth(0)
        pieSlice2.setBrush(QColor(success_color))

        # 创建图表
        self.PieChart = QChart()
        self.PieChart.legend().setAlignment(Qt.AlignVCenter)  # 调整图例位置
        self.PieChart.addSeries(self.pieSeries)
        # self.PieChart.setTitle('通过比例')
        self.PieChart.legend().hide()
        self.PieChart.setBackgroundVisible(0)

        self.PieLabel = BodyLabel()
        self.PieLabel.setText('Fail:' + str('%d‰' % failPercent))
        self.PieLabel.setTextColor(QColor(failure_color))
        self.PieLabel.setFont(QFont('Microsoft YaHei', pointSize=16))
        self.PieLabel.setAlignment(Qt.AlignCenter)

    def showChart(self, success, fail):
        self.PieLayOut = QVBoxLayout()
        self.drawPieChart(success, fail)
        self.drawChart()
        # 创建图表视图
        self.PieChartView = QChartView(self.PieChart)
        self.PieChartView.setRenderHint(QPainter.Antialiasing)  # 可选的，用于抗锯齿
        self.PieChartView.setFrameShape(QFrame.NoFrame)  # 将框架形状设置为无框
        self.PieLayOut.addWidget(self.PieChartView)
        self.PieLayOut.addWidget(self.PieLabel)

        self.ProdTestDataLayout.addLayout(self.PieLayOut)
        self.PieChartView.setStyleSheet('QWidget {background:transparent}')
        self.chartView.setStyleSheet('QWidget {background:transparent}')

    def loadRecord(self):
        pass

    def setShadowEffect(self, card: QWidget):
        shadowEffect = QGraphicsDropShadowEffect(self)
        shadowEffect.setColor(QColor(0, 0, 0, 15))
        shadowEffect.setBlurRadius(10)
        shadowEffect.setOffset(0, 0)
        card.setGraphicsEffect(shadowEffect)
