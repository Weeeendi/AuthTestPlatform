# coding:utf-8
import json
import os
import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import QSize, pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout

import data_manage
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import (HeaderCardWidget, ScrollArea, BodyLabel, InfoBar, InfoBarPosition, ComboBox,
                            HyperlinkButton, DoubleSpinBox, SpinBox, PillToolButton,
                            CheckBox)

# 导入版本管理模块，避免循环导入
try:
    # 确保当前目录在sys.path中
    current_dir = os.path.abspath('.')
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    from version_manager import get_version_string
    APP_VERSION = get_version_string()
except ImportError:
    APP_VERSION = "V25.1.0.0"  # 固定的默认版本号


class SettingInterface(ScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # self.setupUi(self)

        self.view = QtWidgets.QWidget()
        self.view.setObjectName("scrollAreaWidgetContents")
        self.vBoxLayout = QVBoxLayout(self.view)

        self.BasicSetCard = BaseSettingCard(self)
        self.SettingSelectCard = SettingSelectCard(self)
        self.TestSetHeaderCard = TestSetHeaderCard(self)
        self.DescriptionCard = DescriptionCard(self)

        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("SettingInterface")

        self.vBoxLayout.setSpacing(10)
        self.vBoxLayout.setContentsMargins(30, 30, 30, 30)
        self.vBoxLayout.addWidget(self.BasicSetCard, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.SettingSelectCard, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.TestSetHeaderCard, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.DescriptionCard, 0, Qt.AlignTop)

        # add shadow effect to card
        self.setShadowEffect(self.BasicSetCard)
        self.setShadowEffect(self.TestSetHeaderCard)
        self.setShadowEffect(self.DescriptionCard)

        self.setStyleSheet("QScrollArea {border: none; background:transparent}")
        self.view.setStyleSheet('QWidget {background:transparent}')

    def setShadowEffect(self, card: QWidget):
        shadowEffect = QGraphicsDropShadowEffect(self)
        shadowEffect.setColor(QColor(0, 0, 0, 15))
        shadowEffect.setBlurRadius(10)
        shadowEffect.setOffset(0, 0)
        card.setGraphicsEffect(shadowEffect)


def errorNotice(self, notice_comm):
    """错误提示"""
    InfoBar.error(
        title='ERROR',
        content=notice_comm,
        orient=Qt.Horizontal,
        isClosable=False,
        position=InfoBarPosition.BOTTOM_RIGHT,
        duration=2000,  # won't disappear automatically
        parent=self
    )


def successNotice(self, notice_comm):
    """成功提醒"""
    InfoBar.success(
        title='SUCCESS',
        content=notice_comm,
        orient=Qt.Horizontal,
        isClosable=False,
        position=InfoBarPosition.TOP,
        # position='Custom',   # NOTE: use custom info bar manager
        duration=2000,
        parent=self
    )


def createSaveInfoBar(self):
    InfoBar.success(
        title='提示',
        content="已保存当前设置",
        orient=Qt.Horizontal,
        isClosable=False,  # disable close button
        position=InfoBarPosition.TOP,
        duration=2000,
        parent=self.parent().parent()
    )


class SettingSelectCard(HeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ColumnCount = None
        self.GridLayout = QGridLayout(self)
        self.rowCount = None
        self.setTitle('测试项目选择')

        self.expandButton = PillToolButton(FIF.EDIT, self)
        self.expandButton.setFixedSize(32, 32)
        self.expandButton.setIconSize(QSize(12, 12))
        self.headerLayout.addWidget(self.expandButton, 0, Qt.AlignRight)

        self.expandButton.toggled.connect(self._setComponentState)
        # 读配置文件
        self.fileData = data_manage.TestItemFactory()
        for item in self.fileData.testItems:
            self.fileData.create_component_enable(item, self)
        self.LayOurSetting()

        CheckBox_edits = self.findChildren(CheckBox)
        for le in CheckBox_edits:
            le.setDisabled(True)
        # self._setComponentState(False)

    def LayOurSetting(self):
        self.rowCount = 0
        self.ColumnCount = 0
        CheckBox_edits = self.findChildren(CheckBox)
        for le in CheckBox_edits:
            if self.ColumnCount > 0:
                self.GridLayout.addWidget(le, self.rowCount, self.ColumnCount, Qt.AlignLeft)
                self.rowCount += 1
                self.ColumnCount = 0
                continue
            self.GridLayout.addWidget(le, self.rowCount, self.ColumnCount, Qt.AlignLeft)
            self.ColumnCount += 1

        self.viewLayout.addLayout(self.GridLayout)

    def _setComponentState(self, isChecked: bool):
        """set lineEdit"""
        CheckBox_edits = self.findChildren(CheckBox)
        for le in CheckBox_edits:
            if isChecked:
                le.setDisabled(False)
            else:
                le.setDisabled(True)
        if not isChecked:
            createSaveInfoBar(self)


class BaseSettingCard(HeaderCardWidget):
    # 自定义信号，用来发送注册地址的值
    reg_url_sinOut = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('基本设置')

        self.expandButton = PillToolButton(FIF.EDIT, self)
        self.expandButton.setFixedSize(32, 32)
        self.expandButton.setIconSize(QSize(12, 12))
        self.headerLayout.addWidget(self.expandButton, 0, Qt.AlignRight)

        self.expandButton.toggled.connect(self.setComponentState)

        self.GridLayout = QGridLayout(self)
        self.LogLevelLabel = BodyLabel("日志等级", self)
        self.LogLevelCombo = ComboBox(self)
        listOps = ["info", "debug", "error"]
        self.LogLevelCombo.addItems(listOps)
        self.LogLevelCombo.setMinimumWidth(100)
        self.GridLayout.addWidget(self.LogLevelLabel, 0, 0, Qt.AlignLeft)
        self.GridLayout.addWidget(self.LogLevelCombo, 0, 1, Qt.AlignRight)
        self.GridLayout.setColumnStretch(0, 1)
        self.GridLayout.setColumnStretch(1, 2)

        self.tagPrintLabel = BodyLabel("标签打印次数", self)
        self.tagPrintNum = SpinBox(self)
        self.GridLayout.addWidget(self.tagPrintLabel, 1, 0, Qt.AlignLeft)
        self.GridLayout.addWidget(self.tagPrintNum, 1, 1, Qt.AlignRight)

        self.TokenTakeAddrLabel = BodyLabel("注册地址选择", self)
        self.TokenTakeAddrCombo = ComboBox(self)
        self.TokenTakeAddrCombo.setMinimumWidth(400)
        self.GridLayout.addWidget(self.TokenTakeAddrLabel, 2, 0, Qt.AlignLeft)
        self.GridLayout.addWidget(self.TokenTakeAddrCombo, 2, 1, Qt.AlignRight)
        self.GridLayout.setAlignment(Qt.AlignLeft)

        self.TokenTakeAddrCombo.currentTextChanged.connect(self.handle_combo_text_changed)

        self.viewLayout.addLayout(self.GridLayout)
        self._componentInit()

        # self.options = TestOptions()
        # self.loading_data()

    def handle_combo_text_changed(self):
        # Emit your custom signal with the current text
        text = self.TokenTakeAddrCombo.currentText()
        self.reg_url_sinOut.emit(text)

    def _componentInit(self):

        """set lineEdit"""
        ComboBox_edits = self.findChildren(ComboBox)
        SpinBox_edits = self.findChildren(SpinBox)
        for le in ComboBox_edits:
            le.setDisabled(True)
        for le in SpinBox_edits:
            le.setDisabled(True)

    def data_saving(self):
        """保存设置"""
        self.options.base_set.logger_level.value = self.LogLevelCombo.currentText()
        self.options.base_set.tag_print_times.value = self.tagPrintNum.value()
        self.options.base_set.reg_urls[0].value = self.TokenTakeAddrCombo.currentText()
        self.options.write_basedata()

    def loading_data(self):
        """上传数据"""
        self.options.read_basedata()
        self.LogLevelCombo.setCurrentText(self.options.base_set.logger_level.value)
        self.tagPrintNum.setValue(int(self.options.base_set.tag_print_times.value))
        for item in self.options.base_set.reg_urls:
            if item.value != '' and item.value is not None:
                self.TokenTakeAddrCombo.addItem(item.value)

    def setComponentState(self, isChecked: bool):
        # 获取所有的控件  
        ComboBox_edits = self.findChildren(ComboBox)
        SpinBox_edits = self.findChildren(SpinBox)

        # 设置所有控件状态
        if isChecked:
            for le in ComboBox_edits:
                le.setDisabled(False)
            for le in SpinBox_edits:
                le.setDisabled(False)

        else:
            for le in ComboBox_edits:
                le.setDisabled(True)
            for le in SpinBox_edits:
                le.setDisabled(True)
            # save data
            self.data_saving()
            createSaveInfoBar(self)


class TestSetHeaderCard(HeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.BoxNum = 10
        self.BoxCount = 0
        self.GridRowCount = 0

        self.setTitle('测试项设置')
        self.expandButton = PillToolButton(FIF.EDIT, self)
        self.expandButton.setFixedSize(32, 32)
        self.expandButton.setIconSize(QSize(12, 12))
        self.headerLayout.addWidget(self.expandButton, 0, Qt.AlignRight)

        self.expandButton.toggled.connect(self.setLineEditReadOnly)

        self.QGridLayOut = QGridLayout(self)
        self.QGridLayOut.setColumnStretch(0, 1)
        self.QGridLayOut.setColumnStretch(1, 1)

        self.fileData = data_manage.TestItemFactory()
        for testParam in self.fileData.testItemsData:
            self.fileData

        self.viewLayout.addLayout(self.QGridLayOut)
        # self.date = TestOptions()
        # self._loadSettingData()
        self._LineEditInit()

    # def _loadSettingData(self):
    #
    #
    # def _saveSettingData(self):

    def _LineEditInit(self):
        """set lineEdit"""
        DoubleLine_edits = self.findChildren(DoubleEditBox)
        IntLine_edits = self.findChildren(IntEditBox)
        for le in IntLine_edits:
            le.setDisabled(True)
        for le in DoubleLine_edits:
            le.setDisabled(True)

    def setLineEditReadOnly(self, isChecked: bool):
        # 获取所有的LineEdit控件  
        DoubleLine_edits = self.findChildren(DoubleEditBox)
        IntLine_edits = self.findChildren(IntEditBox)

        # 设置所有的LineEdit为只读
        if isChecked:
            for le in IntLine_edits:
                le.setDisabled(False)
            for le in DoubleLine_edits:
                le.setDisabled(False)

        else:
            for le in IntLine_edits:
                le.setDisabled(True)
            for le in DoubleLine_edits:
                le.setDisabled(True)

            createSaveInfoBar(self)

    def LayOurSetting(self):
        self.rowCount = 0
        self.ColumnCount = 0
        CheckBox_edits = self.findChildren(CheckBox)
        for le in CheckBox_edits:
            if self.ColumnCount > 0:
                self.GridLayout.addWidget(le, self.rowCount, self.ColumnCount, Qt.AlignLeft)
                self.rowCount += 1
                self.ColumnCount = 0
                continue
            self.GridLayout.addWidget(le, self.rowCount, self.ColumnCount, Qt.AlignLeft)
            self.ColumnCount += 1

        self.viewLayout.addLayout(self.GridLayout)

    @staticmethod
    def setValueLayOut(Box, LabelWidget, SpinBoxWidget, indicatorPos=0):
        # 设置布局
        if indicatorPos == 0:
            Box.addWidget(SpinBoxWidget, 4)  # 添加SpinBoxWidget到布局中，行数为4
            Box.addWidget(LabelWidget, 4)  # 添加LabelWidget到布局中，行数为4
            Box.setAlignment(Qt.AlignRight)  # 设置布局中的对齐方式为右对齐
        else:
            Box.addWidget(SpinBoxWidget, 3, Qt.AlignRight)  # 添加SpinBoxWidget到布局中，行数为3，并设置右对齐
            Box.addWidget(LabelWidget, 3, Qt.AlignRight)  # 添加LabelWidget到布局中，行数为3，并设置右对齐
            Box.setAlignment(Qt.AlignRight)  # 设置布局中的对齐方式为右对齐


class IntEditBox(SpinBox):
    """ Int line edit """

    # valueChanged = pyqtSignal(str)

    def __init__(self, maxVal, parent=None):
        super().__init__(parent=parent)
        self.setFixedSize(120, 33)
        self.setMaximum(maxVal)


class DoubleEditBox(DoubleSpinBox):
    """ Double line edit """

    # valueChanged = pyqtSignal(str)

    def __init__(self, maxVal, step: float, parent=None):
        super().__init__(parent=parent)
        self.setFixedSize(120, 33)
        self.setMaximum(maxVal)
        self.setSingleStep(0.1)
        self.step = step

        # super().upButton.clicked.connect(self.stepUp)
        # super().downButton.clicked.connect(self.stepDown)

    def stepBy(self, step):
        # 重载 stepBy 方法，允许你自定义每次step的值
        if step == 1:
            super().stepBy(int(self.step / 0.1))
        else:
            super().stepBy(-int(self.step / 0.1))

    def stepUp(self):
        # 重载 stepUp 方法，允许你自定义每次step的值
        super().stepBy(int(self.step / 0.1))

    def stepDown(self):
        # 重载 stepDown 方法，允许你自定义每次step的值    
        super().stepBy(-int(self.step / 0.1))


class DescriptionCard(HeaderCardWidget):
    """ Description card """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.QGridLayOut = QGridLayout(self)

        self.horizontalLayout = QHBoxLayout()
        self.descriptionLabel = BodyLabel('详细配置说明请见', self)

        self.hyperlinkButton = HyperlinkButton(
            url='https://funhez50ho.feishu.cn/wiki/C0HewWD8oincnbkUcLycSZwanbh?from=from_copylink',
            text='[产测说明文档]',
            parent=self,
            icon=FIF.LINK
        )

        # 使用APP_VERSION变量更新版本号
        self.versionLabel = BodyLabel(f'版本号 {APP_VERSION}', self)
        self.helpLabel = BodyLabel('技术支持：云迹物联\r\nCopyright© 2021-2025 All right reverse', self)

        self.horizontalLayout.addWidget(self.descriptionLabel)
        self.horizontalLayout.addWidget(self.hyperlinkButton)
        self.horizontalLayout.setAlignment(Qt.AlignLeft)

        self.QGridLayOut.addLayout(self.horizontalLayout, 0, 0, Qt.AlignLeft)

        self.QGridLayOut.addWidget(self.versionLabel, 1, 0, Qt.AlignLeft)
        self.QGridLayOut.addWidget(self.helpLabel, 2, 0, Qt.AlignLeft)

        self.viewLayout.addLayout(self.QGridLayOut)

        self.setTitle('关于')
