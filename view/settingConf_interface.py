# coding:utf-8
import json
import os
import sys
import re

from PyQt5 import QtWidgets
from PyQt5.QtCore import QSize, Qt, QSettings, QSignalBlocker
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QWidget, QVBoxLayout, QGridLayout, QSizePolicy, QFileDialog, QSpacerItem

import baseUtils
import data_manage
import testSetTableWidget
import runtime_device_info
from qfluentwidgets import FluentIcon as FIF, LineEdit, SwitchButton
from qfluentwidgets import (HeaderCardWidget, ScrollArea, BodyLabel, InfoBar, InfoBarPosition, ComboBox,
                            HyperlinkButton, SpinBox, PillToolButton,
                            CheckBox, PrimaryPushButton)

# 导入版本管理模块，避免循环导入
try:
    # 确保当前目录在sys.path中
    current_dir = os.path.abspath('.')
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    from version_manager import get_version_string, DEFAULT_VERSION_STRING
    APP_VERSION = get_version_string()
except ImportError:
    # 如果导入失败，使用默认版本号
    from version_manager import DEFAULT_VERSION_STRING
    APP_VERSION = DEFAULT_VERSION_STRING


class SettingInterface(ScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # self.setupUi(self)
        self.forbidSetting = False  # 在测试执行时禁止进行设置

        self.view = QtWidgets.QWidget()
        self.view.setObjectName("scrollAreaWidgetContents")
        self.vBoxLayout = QVBoxLayout(self.view)

        self.BasicSetCard = sysSettingCard(self)
        self.DeviceInfoSetCard = DeviceInfoSettingCard(self.BasicSetCard.systemSettingWidget, self)
        # self.SettingSelectCard = setSelectCard(self)
        self.TestSetHeaderCard = setDetailCard(self)
        self.DescriptionCard = DescriptionCard(self)

        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("SettingInterface")

        self.vBoxLayout.setSpacing(5)

        self.vBoxLayout.addWidget(self.BasicSetCard, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.DeviceInfoSetCard, 0, Qt.AlignTop)
        # self.vBoxLayout.addWidget(self.SettingSelectCard, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.TestSetHeaderCard, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.DescriptionCard, 0, Qt.AlignTop)

        # add shadow effect to card
        self.setShadowEffect(self.BasicSetCard)
        self.setShadowEffect(self.DeviceInfoSetCard)
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

    def clearDeviceInfoRuntime(self):
        """Clear runtime device info UI + in-memory runtime storage."""
        try:
            self.DeviceInfoSetCard.clearRuntimeDeviceInfo()
        except Exception:
            pass


def errorNotice(self, notice_comm):
    """错误提示"""
    InfoBar.error(
        title='ERROR',
        content=notice_comm,
        orient=Qt.Horizontal,
        isClosable=False,
        position=InfoBarPosition.BOTTOM_RIGHT,
        duration=2000,  # won't disappear automatically
        parent=self.parent().parent()
    )


def createNoticeInfoBar(self, content: str, isSuccess: bool):
    if isSuccess:
        InfoBar.success(
            title='提示',
            content=content,
            orient=Qt.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.parent().parent()
        )
    else:
        InfoBar.error(
            title='错误',
            content=content,
            orient=Qt.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP,
            duration=2500,
            parent=self.parent().parent()
        )


class DeviceInfoSettingCard(HeaderCardWidget):

    def __init__(self, systemSettingWidget: QWidget, parent=None):
        super().__init__(parent)
        self.setTitle('设备烧录信息配置')

        self.systemSettingWidget = systemSettingWidget

        # Use a pure spacer here (no visible line)
        self.headerLayout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.importPillToolButton = PillToolButton(FIF.FOLDER, self)
        self.importPillToolButton.setFixedSize(32, 32)
        self.importPillToolButton.setIconSize(QSize(12, 12))

        self.savePillToolButton = PillToolButton(FIF.SAVE, self)
        self.savePillToolButton.setFixedSize(32, 32)
        self.savePillToolButton.setIconSize(QSize(12, 12))

        self._headerRightWidget = QWidget(self)
        self._headerRightLayout = QtWidgets.QHBoxLayout(self._headerRightWidget)
        self._headerRightLayout.setContentsMargins(0, 0, 0, 0)
        self._headerRightLayout.setSpacing(8)
        self._headerRightLayout.addWidget(self.importPillToolButton)
        self._headerRightLayout.addWidget(self.savePillToolButton)

        self.headerLayout.addWidget(self._headerRightWidget, 0, Qt.AlignRight)

        self.qSettings = QSettings('FluentAuthTestTool', 'FluentAuthTestTool')
        self.rootDirStr = os.path.abspath('.')
        self.lastDirStr = str(self.qSettings.value('deviceInfo/lastDir', '') or '').strip()

        self.deviceInfoWidget = QWidget(self)
        self.deviceInfoWidget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.deviceInfoGridLayout = QGridLayout(self.deviceInfoWidget)
        self.deviceInfoWidget.setLayout(self.deviceInfoGridLayout)
        self.viewLayout.addWidget(self.deviceInfoWidget, 0, Qt.AlignLeft)
        self.viewLayout.setContentsMargins(20, 20, 20, 20)

        self.queryPidLabel = BodyLabel('PID', self)
        self.queryPidLineEdit = LineEdit(self)

        self.hardwareVersionLabel = BodyLabel('硬件版本号', self)
        self.hardwareVersionLineEdit = LineEdit(self)

        self.queryHostPushButton = PrimaryPushButton('查询连接地址', self)

        self.manualHostLabel = BodyLabel('手动输入设备连接地址', self)
        self.manualHostSwitchButton = SwitchButton(self)
        self.manualHostSwitchButton.setOffText('关')
        self.manualHostSwitchButton.setOnText('开')

        self.hostAddrLabel = BodyLabel('host', self)
        self.hostAddrLineEdit = LineEdit(self)

        self.hostPortLabel = BodyLabel('port', self)
        self.hostPortLineEdit = LineEdit(self)

        self.burningPidLabel = BodyLabel('烧写PID', self)
        self.burningPidSwitchButton = SwitchButton(self)
        self.burningPidSwitchButton.setOffText('否')
        self.burningPidSwitchButton.setOnText('是')

        self.burningHostLabel = BodyLabel('烧写host/port', self)
        self.burningHostSwitchButton = SwitchButton(self)
        self.burningHostSwitchButton.setOffText('否')
        self.burningHostSwitchButton.setOnText('是')

        leftLabelWidthInt = max(
            self.queryPidLabel.sizeHint().width(),
            self.manualHostLabel.sizeHint().width(),
            self.hostAddrLabel.sizeHint().width(),
            self.burningPidLabel.sizeHint().width()
        )
        rightLabelWidthInt = max(
            self.hardwareVersionLabel.sizeHint().width(),
            self.hostPortLabel.sizeHint().width(),
            self.burningHostLabel.sizeHint().width()
        )

        self.queryPidLabel.setFixedWidth(leftLabelWidthInt)
        self.manualHostLabel.setFixedWidth(leftLabelWidthInt)
        self.hostAddrLabel.setFixedWidth(leftLabelWidthInt)
        self.burningPidLabel.setFixedWidth(leftLabelWidthInt)

        self.hardwareVersionLabel.setFixedWidth(rightLabelWidthInt)
        self.hostPortLabel.setFixedWidth(rightLabelWidthInt)
        self.burningHostLabel.setFixedWidth(rightLabelWidthInt)

        shortLineEditWidthInt = 220
        pidLineEditWidthInt = shortLineEditWidthInt
        self.queryPidLineEdit.setFixedWidth(pidLineEditWidthInt)
        self.hardwareVersionLineEdit.setFixedWidth(shortLineEditWidthInt)
        self.hostAddrLineEdit.setFixedWidth(pidLineEditWidthInt)
        self.hostPortLineEdit.setFixedWidth(shortLineEditWidthInt)

        self.deviceInfoGridLayout.addWidget(self.queryPidLabel, 0, 0)
        self.deviceInfoGridLayout.addWidget(self.queryPidLineEdit, 0, 1)
        self.deviceInfoGridLayout.addWidget(self.hardwareVersionLabel, 1, 0)
        self.deviceInfoGridLayout.addWidget(self.hardwareVersionLineEdit, 1, 1)

        # Row 1: burning PID (one option per row)
        self.deviceInfoGridLayout.addWidget(self.burningPidLabel, 2, 0)
        self.deviceInfoGridLayout.addWidget(self.burningPidSwitchButton, 2, 1)

        # Row 2: burning host/port (one option per row)
        self.deviceInfoGridLayout.addWidget(self.burningHostLabel, 3, 0)
        self.deviceInfoGridLayout.addWidget(self.burningHostSwitchButton, 3, 1)

        # Row 3: manual input toggle + query button (mutually exclusive)
        self.deviceInfoGridLayout.addWidget(self.manualHostLabel, 4, 0)
        self.deviceInfoGridLayout.addWidget(self.manualHostSwitchButton, 4, 1)

        # Row 4: host/port
        self.deviceInfoGridLayout.addWidget(self.hostAddrLabel, 5, 0)
        self.deviceInfoGridLayout.addWidget(self.hostAddrLineEdit, 5, 1)
        self.deviceInfoGridLayout.addWidget(self.hostPortLabel, 5, 2)
        self.deviceInfoGridLayout.addWidget(self.hostPortLineEdit, 5, 3)

        self.deviceInfoGridLayout.addWidget(self.queryHostPushButton, 6, 0, 1, 2)

        self.deviceInfoGridLayout.setSpacing(15)
        self.deviceInfoGridLayout.setColumnStretch(0, 0)
        self.deviceInfoGridLayout.setColumnStretch(1, 0)
        self.deviceInfoGridLayout.setColumnStretch(2, 0)
        self.deviceInfoGridLayout.setColumnStretch(3, 0)

        self.deviceInfoWidget.setFixedWidth(
            leftLabelWidthInt
            + pidLineEditWidthInt
            + rightLabelWidthInt
            + shortLineEditWidthInt
            + self.deviceInfoGridLayout.horizontalSpacing() * 3
            + self.deviceInfoGridLayout.contentsMargins().left()
            + self.deviceInfoGridLayout.contentsMargins().right()
        )

        # Requirement: do not persist as default fill data.
        # Always start empty; user must import each session (no paramConfig.json).
        self.clearRuntimeDeviceInfo()

        self.manualHostSwitchButton.checkedChanged.connect(self._onManualHostChanged)
        self.burningPidSwitchButton.checkedChanged.connect(self._onFieldChanged)
        self.burningHostSwitchButton.checkedChanged.connect(self._onBurningHostChanged)
        self.queryHostPushButton.clicked.connect(self._onQueryHostClicked)
        self.importPillToolButton.clicked.connect(self._onImportClicked)
        self.savePillToolButton.clicked.connect(self._onSaveClicked)

        self.queryPidLineEdit.textChanged.connect(self._onFieldChanged)
        self.hardwareVersionLineEdit.textChanged.connect(self._onFieldChanged)
        self.hostAddrLineEdit.textChanged.connect(self._onFieldChanged)
        self.hostPortLineEdit.textChanged.connect(self._onFieldChanged)

    def clearRuntimeDeviceInfo(self):
        """Clear UI fields and reset in-memory runtime device info."""
        blockers = [
            QSignalBlocker(self.queryPidLineEdit),
            QSignalBlocker(self.hardwareVersionLineEdit),
            QSignalBlocker(self.manualHostSwitchButton),
            QSignalBlocker(self.hostAddrLineEdit),
            QSignalBlocker(self.hostPortLineEdit),
            QSignalBlocker(self.burningPidSwitchButton),
            QSignalBlocker(self.burningHostSwitchButton),
        ]
        try:
            self._resetDeviceInfoFields()
            runtime_device_info.clear_device_info()
        finally:
            pass

    def _onFieldChanged(self, *args):
        runtime_device_info.set_device_info(self._getDeviceInfoDict())

    def _resetToolButtonState(self, btn: QWidget):
        """Avoid stuck highlight when a modal dialog is closed via window X."""
        try:
            # ToolButton/QAbstractButton APIs
            if hasattr(btn, 'setDown'):
                btn.setDown(False)
            if hasattr(btn, 'isCheckable') and btn.isCheckable() and hasattr(btn, 'setChecked'):
                btn.setChecked(False)
        except Exception:
            pass

    def _getDefaultDirStr(self) -> str:
        return self.lastDirStr or self.rootDirStr

    def _setLastDir(self, dirStr: str):
        dirStr = str(dirStr or '').strip()
        if not dirStr:
            return
        self.lastDirStr = dirStr
        self.qSettings.setValue('deviceInfo/lastDir', dirStr)

    def _resetDeviceInfoFields(self):
        self.queryPidLineEdit.clear()
        self.hardwareVersionLineEdit.clear()
        self.hostAddrLineEdit.clear()
        self.hostPortLineEdit.clear()
        self.manualHostSwitchButton.setChecked(False)
        self.burningPidSwitchButton.setChecked(False)
        self.burningHostSwitchButton.setChecked(False)
        self._applyBurningHostState(False)
        self._applyManualHostState(False)

    def _applyBurningHostState(self, burningHostBool: bool):
        """When burning host is disabled, disable all host-related controls below."""
        enabled = bool(burningHostBool)
        try:
            self.manualHostLabel.setEnabled(enabled)
            self.manualHostSwitchButton.setEnabled(enabled)
            self.queryHostPushButton.setEnabled(enabled)

            self.hostAddrLabel.setEnabled(enabled)
            self.hostAddrLineEdit.setEnabled(enabled)
            self.hostPortLabel.setEnabled(enabled)
            self.hostPortLineEdit.setEnabled(enabled)
        except Exception:
            pass

        if not enabled:
            # force manual host off when the whole host section is disabled
            try:
                self.manualHostSwitchButton.setChecked(False)
            except Exception:
                pass

    def _onBurningHostChanged(self, checkedBool: bool):
        self._applyBurningHostState(checkedBool)
        # re-apply mutual exclusion based on current manual-host
        self._applyManualHostState(bool(self.manualHostSwitchButton.isChecked()))
        runtime_device_info.set_device_info(self._getDeviceInfoDict())

    def _applyManualHostState(self, manualHostBool: bool):
        self.hostAddrLineEdit.setReadOnly(not manualHostBool)
        self.hostPortLineEdit.setReadOnly(not manualHostBool)
        # Mutual exclusion: manual input ON => disable query button (only when burning_host is enabled)
        try:
            if not bool(self.burningHostSwitchButton.isChecked()):
                self.queryHostPushButton.setDisabled(True)
            else:
                self.queryHostPushButton.setDisabled(bool(manualHostBool))
        except Exception:
            pass

    def _onManualHostChanged(self, checkedBool: bool):
        self._applyManualHostState(checkedBool)
        runtime_device_info.set_device_info(self._getDeviceInfoDict())

    def _getDeviceInfoDict(self) -> dict:
        return {
            'manual_host': bool(self.manualHostSwitchButton.isChecked()),
            'host': str(self.hostAddrLineEdit.text() or '').strip(),
            'port': str(self.hostPortLineEdit.text() or '').strip(),
            'query_pid': str(self.queryPidLineEdit.text() or '').strip(),
            'hardware_version': str(self.hardwareVersionLineEdit.text() or '').strip(),
            'burning_pid': bool(self.burningPidSwitchButton.isChecked()),
            'burning_host': bool(self.burningHostSwitchButton.isChecked())
        }

    def getCurrentDeviceInfoDict(self) -> dict:
        """Public accessor for current UI values."""
        return self._getDeviceInfoDict()

    def _applyDeviceInfoDict(self, dataDict: dict):
        if not isinstance(dataDict, dict):
            return

        self.burningHostSwitchButton.setChecked(bool(dataDict.get('burning_host', False)))
        self._applyBurningHostState(bool(self.burningHostSwitchButton.isChecked()))

        self.manualHostSwitchButton.setChecked(bool(dataDict.get('manual_host', False)))
        self._applyManualHostState(bool(self.manualHostSwitchButton.isChecked()))
        self.hostAddrLineEdit.setText(str(dataDict.get('host', '') or ''))
        self.hostPortLineEdit.setText(str(dataDict.get('port', '') or ''))
        self.queryPidLineEdit.setText(str(dataDict.get('query_pid', '') or ''))
        self.hardwareVersionLineEdit.setText(str(dataDict.get('hardware_version', '') or ''))
        self.burningPidSwitchButton.setChecked(bool(dataDict.get('burning_pid', False)))

    def _extractRegUrlStr(self) -> str:
        try:
            urlString = str(self.systemSettingWidget.authAddrDictComboBox.currentText() or '')
        except Exception:
            urlString = ''
        urlPatternStr = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        matchObj = re.search(urlPatternStr, urlString or '')
        return matchObj.group() if matchObj else ''

    def _onQueryHostClicked(self):
        pidStr = str(self.queryPidLineEdit.text() or '').strip()
        hwStr = str(self.hardwareVersionLineEdit.text() or '').strip()

        if not pidStr or not hwStr:
            createNoticeInfoBar(self, '请输入 PID 与硬件版本号', False)
            return

        regUrlStr = self._extractRegUrlStr()
        try:
            clientIdStr = str(self.systemSettingWidget.authAccountIDLineEdit.text() or '').strip()
            clientSecretStr = str(self.systemSettingWidget.authAccountPassWordLineEdit.text() or '').strip()
        except Exception:
            clientIdStr = ''
            clientSecretStr = ''

        if not regUrlStr or not clientIdStr or not clientSecretStr:
            createNoticeInfoBar(self, '配置缺失：授权地址/用户id/密钥', False)
            return

        from view.Firmware_interface import FirmwareApiWorker

        self.queryHostPushButton.setDisabled(True)
        self.worker = FirmwareApiWorker(regUrlStr, clientIdStr, clientSecretStr, self)
        self.worker.mode = 'query'
        self.worker.hw_version = hwStr
        self.worker.product_iot_id = pidStr
        self.worker.queryFinished.connect(self._onQueryHostOk)
        self.worker.failed.connect(self._onQueryHostFailed)
        self.worker.start()

    def _onQueryHostOk(self, infoDict: dict):
        hostStr = ''
        portStr = ''
        if isinstance(infoDict, dict):
            hostStr = str(infoDict.get('hostAddr') or infoDict.get('host') or '')
            portStr = str(infoDict.get('hostPort') or infoDict.get('port') or '')

        if not hostStr or not portStr:
            self.hostAddrLineEdit.clear()
            self.hostPortLineEdit.clear()
            createNoticeInfoBar(self, '查询成功，但未返回 host/port 字段', False)
        else:
            self.hostAddrLineEdit.setText(hostStr)
            self.hostPortLineEdit.setText(portStr)
            createNoticeInfoBar(self, '已更新连接地址', True)

        runtime_device_info.set_device_info(self._getDeviceInfoDict())
        self.queryHostPushButton.setDisabled(False)

    def _onQueryHostFailed(self, msgStr: str):
        self.hostAddrLineEdit.clear()
        self.hostPortLineEdit.clear()
        createNoticeInfoBar(self, str(msgStr or ''), False)
        runtime_device_info.set_device_info(self._getDeviceInfoDict())
        self.queryHostPushButton.setDisabled(False)

    def _onImportClicked(self):
        try:
            defaultDirStr = self._getDefaultDirStr()
            filePathStr, _ = QFileDialog.getOpenFileName(self, '导入设备信息', defaultDirStr, 'JSON Files (*.json)')
            filePathStr = str(filePathStr or '').strip()
            if not filePathStr:
                return

            try:
                with open(filePathStr, 'r', encoding='utf-8', errors='ignore') as file:
                    dataDict = json.load(file)
                self._applyDeviceInfoDict(dataDict)
                runtime_device_info.set_device_info(self._getDeviceInfoDict())
                self._setLastDir(os.path.dirname(filePathStr))
                createNoticeInfoBar(self, '导入成功', True)
            except Exception:
                createNoticeInfoBar(self, '导入失败：文件格式不正确', False)
        finally:
            self._resetToolButtonState(self.importPillToolButton)

    def _onSaveClicked(self):
        try:
            defaultDirStr = self._getDefaultDirStr()
            defaultPathStr = os.path.join(defaultDirStr, 'deviceInfo.json')
            filePathStr, _ = QFileDialog.getSaveFileName(self, '保存设备信息', defaultPathStr, 'JSON Files (*.json)')
            filePathStr = str(filePathStr or '').strip()
            if not filePathStr:
                return

            dataDict = self._getDeviceInfoDict()
            try:
                with open(filePathStr, 'w', encoding='utf-8', errors='ignore') as file:
                    json.dump(dataDict, file, ensure_ascii=False, indent=4)
                runtime_device_info.set_device_info(dataDict)
                self._setLastDir(os.path.dirname(filePathStr))
                createNoticeInfoBar(self, '保存成功', True)
            except Exception:
                createNoticeInfoBar(self, '保存失败：无法写入文件', False)
        finally:
            self._resetToolButtonState(self.savePillToolButton)


def successNotice(self, notice_comm):
    """成功提醒"""
    InfoBar.success(
        title='SUCCESS',
        content=notice_comm,
        orient=Qt.Horizontal,
        isClosable=False,
        position=InfoBarPosition.BOTTOM_RIGHT,
        # position='Custom',   # NOTE: use custom info bar manager
        duration=2000,
        parent=self.parent().parent()
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
        configPath = baseUtils.resource_path("resources\\config\\userConfig.json")
        self.file = configPath

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
        LineEdit_edits = self.findChildren(LineEdit)
        CheckBox_edits = self.findChildren(CheckBox)
        SwitchButton_edits = self.findChildren(SwitchButton)

        for le in ComboBox_edits:
            le.setDisabled(True)
        for le in SpinBox_edits:
            le.setDisabled(True)
        for le in LineEdit_edits:
            le.setDisabled(True)
        for le in CheckBox_edits:
            le.setDisabled(True)
        for le in SwitchButton_edits:
            le.setDisabled(True)

    def setComponentState(self, isChecked: bool):
        # 获取所有的控件  
        ComboBox_edits = self.findChildren(ComboBox)
        SpinBox_edits = self.findChildren(SpinBox)
        LineEdit_edits = self.findChildren(LineEdit)
        CheckBox_edits = self.findChildren(CheckBox)
        SwitchButton_edits = self.findChildren(SwitchButton)
        # 设置所有控件状态
        if isChecked:
            for le in ComboBox_edits:
                le.setDisabled(False)
            for le in SpinBox_edits:
                le.setDisabled(False)
            for le in LineEdit_edits:
                le.setDisabled(False)
            for le in CheckBox_edits:
                le.setDisabled(False)
            for le in SwitchButton_edits:
                le.setDisabled(False)

        else:
            for le in ComboBox_edits:
                le.setDisabled(True)
            for le in SpinBox_edits:
                le.setDisabled(True)
            for le in LineEdit_edits:
                le.setDisabled(True)
            for le in CheckBox_edits:
                le.setDisabled(True)
            for le in SwitchButton_edits:
                le.setDisabled(True)
            # save data
            try:
                self.systemSettingWidget.save_configs()
            except Exception:
                pass
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
        self.file = baseUtils.resource_path('resources\\config\\userConfig.json')
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
            # 退出编辑前进行校验：至少有一项勾选(enable=True)
            updated_items = self.detailInfo.updateData2Json() if self.detailInfo else []
            enabled_count = 0
            try:
                enabled_count = sum(1 for it in updated_items if isinstance(it, dict) and it.get('enable', False))
            except Exception:
                enabled_count = 0

            if enabled_count <= 0:
                # 不满足条件，保留编辑态并提示错误，不写入文件
                errorNotice(self, '请至少勾选一条测试项后再保存')
                # 保持编辑模式
                self.expandButton.setChecked(True)
                self.detailInfo.forbidEdit(False)
                return

            # 校验通过，保存并退出编辑
            self.detailInfo.forbidEdit(True)
            with open(self.file, 'w', encoding='utf-8', errors='ignore') as file:
                self.testItemsData["TestItems"] = updated_items
                json.dump(self.testItemsData, file, ensure_ascii=False, indent=4)

            createSaveInfoBar(self)


class DescriptionCard(HeaderCardWidget):
    """ Description card """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.QGridLayOut = QGridLayout()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.descriptionLabel = BodyLabel('本工具用于云迹物联生产测试使用,详细配置说明请见', self)

        self.hyperlinkButton = HyperlinkButton(
            url='https://funhez50ho.feishu.cn/wiki/C0HewWD8oincnbkUcLycSZwanbh?from=from_copylink',
            text='[产测说明文档]',
            parent=self,
            icon=FIF.LINK
        )

        # 使用APP_VERSION变量更新版本号
        self.versionLabel = BodyLabel(f'版本号 {APP_VERSION}', self)
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
