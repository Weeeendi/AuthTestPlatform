# coding:utf-8
import json
import re
from typing import Optional

import requests
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QWidget, QVBoxLayout, QGridLayout, QSizePolicy

import baseUtils
from qfluentwidgets import (
    QColor,
    ScrollArea,
    HeaderCardWidget,
    BodyLabel,
    LineEdit,
    PrimaryPushButton,
    InfoBar,
    InfoBarPosition,
)
from qfluentwidgets.common.animation import QGraphicsDropShadowEffect


class FirmwareApiWorker(QThread):
    """Background worker to call token/query/download APIs."""

    queryFinished = pyqtSignal(dict)  # emits firmware info dict on success
    downloadFinished = pyqtSignal(str)  # emits saved file path on success
    failed = pyqtSignal(str)

    def __init__(self, reg_url: str, client_id: str, client_secret: str, parent=None):
        super().__init__(parent)
        self.reg_url = reg_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.mode = None  # 'query' | 'download'
        self.hw_version = ''
        self.product_iot_id = ''
        self.download_upload_id = ''
        self.save_path = ''

    def _get_token(self) -> Optional[str]:
        token_url = f"{self.reg_url}/api/v1/oauth2/clientToken"
        payload = {"clientId": self.client_id, "clientSecret": self.client_secret}
        try:
            resp = requests.post(token_url, json=payload, timeout=10)
            status = resp.status_code
            text = resp.text[:200]
            try:
                data = resp.json()
            except Exception:
                self.failed.emit(f"获取 token 失败：HTTP {status} 响应不可解析，片段: {text}")
                return None
            if data.get('code') == 200 and data.get('data', {}).get('token'):
                print("获取Token成功")
                return data['data']['token']
            msg = data.get('msg') or '未知错误'
            self.failed.emit(f"获取 token 失败：HTTP {status}，msg: {msg}")
            return None
        except Exception as e:
            self.failed.emit(f"获取 token 异常：{str(e)}")
            return None

    def _post_firmware_info(self, token: str) -> Optional[dict]:
        # Endpoint path was not specified in the brief; keep it configurable here if needed.
        # Default to a reasonable backend route naming.
        info_url = f"{self.reg_url}/api/v1/firmware/queryProductionInfo"
        payload = {
            "hardwareVersion": self.hw_version,
            "productIotId": self.product_iot_id
        }
        headers = {"token": token}

        errors = []
        
        try:
            resp = requests.post(info_url, json=payload, headers=headers, timeout=10)
            status = resp.status_code
            body_snip = resp.text[:200]
            try:
                data = resp.json()
            except Exception:
                errors.append(f"{info_url} -> HTTP {status}, 非 JSON: {body_snip}")
                return None
            if data.get('code') == 200 and isinstance(data.get('data'), dict):
                return data['data']
            errors.append(f"{info_url} -> HTTP {status}, msg: {data.get('msg')}")
        except Exception as e:
            errors.append(f"{info_url} -> 请求异常: {str(e)}")

        self.failed.emit("固件信息接口失败：\n" + "\n".join(errors))
        return None

    def _download_firmware(self, token: str) -> Optional[str]:
        url = f"{self.reg_url}/api/v1/common/file/download/{self.download_upload_id}"
        headers = {"token": token}
        try:
            with requests.get(url, headers=headers, stream=True, timeout=30) as r:
                status = r.status_code
                if status != 200:
                    self.failed.emit(f"下载失败：HTTP {status}，路径: {url}")
                    return None
                with open(self.save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            return self.save_path
        except Exception as e:
            self.failed.emit(f"下载异常：{str(e)}")
            return None

    def run(self):
        token = self._get_token()
        if not token:
            return

        if self.mode == 'query':
            info = self._post_firmware_info(token)
            if info is None:
                return
            self.queryFinished.emit(info)
        elif self.mode == 'download':
            saved = self._download_firmware(token)
            if not saved:
                return
            self.downloadFinished.emit(saved)


class FirmwareInterface(ScrollArea):
    """固件管理页面：查询固件信息与下载生产固件"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.view = QtWidgets.QWidget()
        self.view.setObjectName('FirmwareInterfaceScrollArea')
        self.vBoxLayout = QVBoxLayout(self.view)
        self.vBoxLayout.setSpacing(6)

        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName('FirmwareInterface')

        # 从系统配置读取云端地址与凭证
        self.regUrl, self.clientId, self.clientSecret = None, None, None

        # 顶部输入与操作卡片
        self.headerCard = HeaderCardWidget(self)
        self.headerCard.setTitle('固件管理')
        # 限制纵向扩展：按内容高度显示
        self.headerCard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self._build_header_content()
        self.vBoxLayout.addWidget(self.headerCard)
        self.headerCard.viewLayout.setContentsMargins(20, 20, 20, 20)

        # 结果展示卡片
        self.resultCard = HeaderCardWidget(self)
        self.resultCard.setTitle('固件信息')
        # 限制纵向扩展：按内容高度显示
        self.resultCard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self._build_result_content()
        self.vBoxLayout.addWidget(self.resultCard)
        # 将多余空间交给拉伸项，促使卡片靠上堆叠
        self.vBoxLayout.addStretch(1)
        self.resultCard.viewLayout.setContentsMargins(20, 20, 20, 20)

        # 状态
        self.currentInfo = {}
        self.currentUploadId = ''
        self.currentFilename = ''

        self.setShadowEffect(self.headerCard)
        self.setShadowEffect(self.resultCard)

        self.setStyleSheet("QScrollArea {border: none; background:transparent}")
        self.view.setStyleSheet('QWidget {background:transparent}')


    
    def setShadowEffect(self, card: QWidget):
        shadowEffect = QGraphicsDropShadowEffect(self)
        shadowEffect.setColor(QColor(0, 0, 0, 15))
        shadowEffect.setBlurRadius(10)
        shadowEffect.setOffset(0, 0)
        card.setGraphicsEffect(shadowEffect)

    # --------------------- UI 构建 ---------------------
    def _build_header_content(self):
        # 顶部水平行：PID + 硬件版本输入 + 按钮
        row = QtWidgets.QWidget(self.headerCard)
        rowLayout = QtWidgets.QGridLayout(row)
        rowLayout.setContentsMargins(10, 10, 10, 0)

        self.pidLabel = BodyLabel('PID', row)
        self.pidEdit = LineEdit(row)
        self.pidEdit.setPlaceholderText('例如：YJ0000aj1d')
        self.pidEdit.setFixedWidth(200)
        #Test value
        self.pidEdit.setText('YJ0000aj1d')

        self.hwLabel = BodyLabel('硬件版本号', row)
        self.hwEdit = LineEdit(row)
        self.hwEdit.setPlaceholderText('例如：VBox-TC01-R-1.0')
        self.hwEdit.setFixedWidth(200)
        #Test value
        self.hwEdit.setText('VBox-TC01-R-1.0')

        self.queryBtn = PrimaryPushButton('查询固件信息', row)
        self.queryBtn.clicked.connect(self._on_query_clicked)

        rowLayout.addWidget(self.pidLabel, 0, 0)
        rowLayout.addWidget(self.pidEdit, 0, 1)
        rowLayout.addWidget(self.hwLabel, 0, 2)
        rowLayout.addWidget(self.hwEdit, 0, 3)
        rowLayout.addWidget(self.queryBtn, 0, 4)

        self.headerCard.viewLayout.addWidget(row, 0, Qt.AlignBottom)
        # 默认支持编辑：无需切换按钮

    def _build_result_content(self):
        # 使用一个容器承载“键值网格 + 底部下载按钮”，确保按钮在信息列表下方
        container = QWidget(self.resultCard)
        v = QVBoxLayout(container)
        v.setContentsMargins(10, 10, 10, 6)
        v.setSpacing(8)

        # 键值网格
        self.kvLayout = QGridLayout()
        self.kvLayout.setHorizontalSpacing(16)
        self.kvLayout.setVerticalSpacing(8)
        v.addLayout(self.kvLayout)

        # 下载按钮位于信息网格下方，初始不显示
        self.downloadBtn = PrimaryPushButton('下载生产固件', container)
        self.downloadBtn.setEnabled(False)
        self.downloadBtn.setVisible(False)
        self.downloadBtn.clicked.connect(self._on_download_clicked)
        v.addWidget(self.downloadBtn, 0, Qt.AlignLeft)

        self.resultCard.viewLayout.addWidget(container)

    # --------------------- 配置读取 ---------------------
    def _load_sys_config(self):
        config_path = baseUtils.resource_path('resources\\config\\sysConfig.json')
        reg_url = ''
        client_id = ''
        client_secret = ''
        try:
            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                cfg = json.load(f)
                # 与 data_manage.py 保持一致的字段
                # reg_url 可能包含形如 "(desc)http://..."，需提取 URL
                url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
                m = re.search(url_pattern, cfg.get('reg_url', ''))
                reg_url = m.group() if m else cfg.get('reg_url', '')
                client_id = cfg.get('current_auth_account', '')
                client_secret = cfg.get('current_auth_password', '')
        except Exception:
            pass
        return reg_url, client_id, client_secret

    # --------------------- 交互逻辑 ---------------------
    def _on_query_clicked(self):
        # 每次查询前重新读取最新的配置
        self.regUrl, self.clientId, self.clientSecret = self._load_sys_config()
        pid = self.pidEdit.text().strip()
        hw = self.hwEdit.text().strip()
        if not pid or not hw:
            self._error('请输入 PID 与硬件版本号')
            return
        if not self.regUrl or not self.clientId or not self.clientSecret:
            self._error('配置缺失：云端地址/用户ID/密钥')
            return

        self.queryBtn.setDisabled(True)
        # 查询进行中，底部下载按钮隐藏并禁用
        self.downloadBtn.setVisible(False)
        self.downloadBtn.setDisabled(True)

        self.worker = FirmwareApiWorker(self.regUrl, self.clientId, self.clientSecret, self)
        self.worker.mode = 'query'
        self.worker.hw_version = hw
        self.worker.product_iot_id = pid
        self.worker.queryFinished.connect(self._on_query_ok)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_download_clicked(self):
        if not self.currentUploadId:
            self._error('请先查询获取 uploadId')
            return

        # 选择保存文件路径，默认使用返回的文件名
        default_name = self.currentFilename or f"firmware_{self.currentUploadId}.bin"
        save_path, _ = QFileDialog.getSaveFileName(self, '保存固件文件', default_name)
        if not save_path:
            return

        self.queryBtn.setDisabled(True)
        self.downloadBtn.setDisabled(True)

        self.worker = FirmwareApiWorker(self.regUrl, self.clientId, self.clientSecret, self)
        self.worker.mode = 'download'
        self.worker.download_upload_id = self.currentUploadId
        self.worker.save_path = save_path
        self.worker.downloadFinished.connect(self._on_download_ok)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    # --------------------- 回调 ---------------------
    def _on_query_ok(self, info: dict):
        self.currentInfo = info
        self.currentUploadId = info.get('uploadId', '') or ''
        self.currentFilename = info.get('filename', '') or ''
        self._render_kv(info)
        self._success('查询成功')
        self.queryBtn.setDisabled(False)
        # 显示底部下载按钮，并依据 uploadId 决定可用性
        self.downloadBtn.setVisible(True)
        self.downloadBtn.setDisabled(not bool(self.currentUploadId))

    def _on_download_ok(self, path: str):
        self._success(f'已保存至: {path}')
        self.queryBtn.setDisabled(False)
        self.downloadBtn.setDisabled(False)

    def _on_failed(self, msg: str):
        self._error(msg)
        self.queryBtn.setDisabled(False)
        # 查询或下载失败，隐藏底部下载按钮，避免误点
        self.downloadBtn.setVisible(False)
        self.downloadBtn.setDisabled(True)

    # --------------------- 辅助 ---------------------
    def _clear_kv(self):
        while self.kvLayout.count():
            item = self.kvLayout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _render_kv(self, data: dict):
        self._clear_kv()
        if not isinstance(data, dict):
            return
        row = 0
        for k, v in data.items():
            key_label = BodyLabel(str(k))
            val_label = BodyLabel(str(v) if v is not None else '')
            self.kvLayout.addWidget(key_label, row, 0, Qt.AlignLeft)
            self.kvLayout.addWidget(val_label, row, 1, Qt.AlignLeft)
            row += 1

    def _success(self, text: str):
        InfoBar.success(
            title='成功',
            content=text,
            orient=Qt.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def _error(self, text: str):
        InfoBar.error(
            title='错误',
            content=text,
            orient=Qt.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP,
            duration=2500,
            parent=self
        )
