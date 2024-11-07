# coding:utf-8
import json

from PyQt5 import QtWidgets
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QWidget, QVBoxLayout, QGridLayout, QSizePolicy

import data_manage
import testSetTableWidget
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import (HeaderCardWidget, ScrollArea, BodyLabel, InfoBar, InfoBarPosition, ComboBox,
                            HyperlinkButton, SpinBox, PillToolButton,
                            CheckBox)


class SettingInterface(ScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # self.setupUi(self)
        self.forbidSetting = False  # 在测试执行时禁止进行设置

        self.view = QtWidgets.QWidget()
        self.view.setObjectName("scrollAreaWidgetContents")
        self.vBoxLayout = QVBoxLayout(self.view)

        self.BasicSetCard = sysSettingCard(self)
        # self.SettingSelectCard = setSelectCard(self)
        self.TestSetHeaderCard = setDetailCard(self)
        self.DescriptionCard = DescriptionCard(self)

        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("SettingInterface")

        self.vBoxLayout.setSpacing(5)

        self.vBoxLayout.addWidget(self.BasicSetCard, 0, Qt.AlignTop)
        # self.vBoxLayout.addWidget(self.SettingSelectCard, 0, Qt.AlignTop)
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


class setSelectCard(HeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ColumnCount = None
        self.rowCount = None
        self.setTitle('测试项目选择')

        self.expandButton = PillToolButton(FIF.EDIT, self)
        self.expandButton.setFixedSize(32, 32)
        self.expandButton.setIconSize(QSize(12, 12))
        self.headerLayout.addWidget(self.expandButton, 1, Qt.AlignRight)

        self.expandButton.toggled.connect(self._setComponentState)
        # 读配置文件
        self.file = 'resources/config/userConfig.json'

        self.setSelectWidget = data_manage.TestItemEditFactory(self.file, self)
        self.viewLayout.addWidget(self.setSelectWidget, 0, Qt.AlignLeft)

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


class sysSettingCard(HeaderCardWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('基本设置')

        self.expandButton = PillToolButton(FIF.EDIT, self)
        self.expandButton.setFixedSize(32, 32)
        self.expandButton.setIconSize(QSize(12, 12))
        self.headerLayout.addWidget(self.expandButton, 1, Qt.AlignRight)

        self.expandButton.toggled.connect(self.setComponentState)

        self.systemSettingWidget = data_manage.SysItemEditFactory()
        self.viewLayout.addWidget(self.systemSettingWidget, 0, Qt.AlignLeft)
        self.viewLayout.setContentsMargins(20, 20, 20, 20)

        ComboBox_edits = self.findChildren(ComboBox)
        SpinBox_edits = self.findChildren(SpinBox)

        for le in ComboBox_edits:
            le.setDisabled(True)
        for le in SpinBox_edits:
            le.setDisabled(True)

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
            createSaveInfoBar(self)


class setDetailCard(HeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 卡片右上角添加编辑按钮
        self.expandButton = PillToolButton(FIF.EDIT, self)
        self.expandButton.setFixedSize(32, 32)
        self.expandButton.setIconSize(QSize(12, 12))
        self.headerLayout.addWidget(self.expandButton, 1, Qt.AlignRight)

        self.expandButton.toggled.connect(self.setComponentState)

        # 读配置文件
        self.file = 'resources/config/userConfig.json'
        try :
            with open(self.file, 'r', encoding='utf-8', errors='ignore') as file:
                self.testItemsData = json.load(file)
        except Exception:
            self.testItemsData = {
                "TestItems": []
            }

        self.setTitle('测试项目详情')

        self.detailInfo = testSetTableWidget.myTableModel(self.testItemsData["TestItems"])
        try:
            self.detailInfo.forbidEdit(True)
            self.viewLayout.addWidget(self.detailInfo)
            self.setMinimumHeight(self.detailInfo.getHighOfTable() + 100)

        except Exception:
            # 处理 self.detailInfo 为 None 的情况
            print("Failed to create table model")
            # 可以选择添加一个占位符或其他提示信息
            placeholder = BodyLabel("No data available")
            self.viewLayout.addWidget(placeholder)
            self.setMinimumHeight(placeholder.sizeHint().height() + 100)
            self.expandButton.setDisabled(True)
            pass
        self.viewLayout.setContentsMargins(20, 20, 20, 20)

    def setComponentState(self, isChecked: bool):
        if isChecked:
            self.detailInfo.forbidEdit(False)
        else:
            self.detailInfo.forbidEdit(True)
            with open(self.file, 'w', encoding='utf-8', errors='ignore') as file:
                # 将数据以JSON格式写入文件，确保中文不被转义
                self.testItemsData["TestItems"] = self.detailInfo.updateData2Json()
                json.dump(self.testItemsData, file, ensure_ascii=False, indent=4)

            createSaveInfoBar(self)


class DescriptionCard(HeaderCardWidget):
    """ Description card """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.QGridLayOut = QGridLayout(self)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.descriptionLabel = BodyLabel('本工具用于云迹物联生产测试使用,详细配置说明请见', self)

        self.hyperlinkButton = HyperlinkButton(
            url='https://funhez50ho.feishu.cn/wiki/Ejf2wb8Nji68YTkqdE7cEvAQnId',
            text='<产测说明文档>',
            parent=self,
            icon=FIF.LINK
        )

        self.versionLabel = BodyLabel('版本号 v231113.1.1.0', self)
        self.helpLabel = BodyLabel('技术支持：云迹物联\r\nCopyright© 2021-2025 All right reverse', self)

        self.QGridLayOut.addWidget(self.descriptionLabel, 0, 0, Qt.AlignLeft)
        self.QGridLayOut.addWidget(self.hyperlinkButton, 0, 1, Qt.AlignLeft)
        self.QGridLayOut.setColumnStretch(1,1)

        self.QGridLayOut.addWidget(self.versionLabel, 1, 0, Qt.AlignLeft)
        self.QGridLayOut.addWidget(self.helpLabel, 2, 0, Qt.AlignLeft)

        self.viewLayout.addLayout(self.QGridLayOut)
        self.viewLayout.setSpacing(0)
        self.viewLayout.setContentsMargins(20, 20, 20, 20)

        self.setTitle('关于')
