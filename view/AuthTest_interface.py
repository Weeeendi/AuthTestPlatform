# coding:utf-8
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect
from qfluentwidgets import FluentIcon, setFont, InfoBarIcon

from resource.ui.AuthTestInterface_ui import Ui_AuthTestInterface



class AuthTestInterface(Ui_AuthTestInterface, QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)

        # set the icon of button
        self.PrimaryToolButton_Update.setIcon(FluentIcon.SYNC)
        # self.PrimaryToolButton_playlog.setIcon(FluentIcon.PLAY)

        # add shadow effect to card
        self.setShadowEffect(self.SettingCard)
        self.setShadowEffect(self.progressCard)
        self.setShadowEffect(self.LogViewerCard)

    

    def setShadowEffect(self, card: QWidget):
        shadowEffect = QGraphicsDropShadowEffect(self)
        shadowEffect.setColor(QColor(0, 0, 0, 15))
        shadowEffect.setBlurRadius(10)
        shadowEffect.setOffset(0, 0)
        card.setGraphicsEffect(shadowEffect)
