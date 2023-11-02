# coding:utf-8
import sys

from PyQt5 import  QtWidgets
from PyQt5.QtCore import Qt,QSize,pyqtSignal
from PyQt5.QtGui import QIcon,QColor,QIntValidator,QDoubleValidator
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QLayout,QWidget,QHBoxLayout,QVBoxLayout,QSpacerItem,QGridLayout

from qfluentwidgets import (HeaderCardWidget,ScrollArea,BodyLabel,InfoBar,HorizontalSeparator,
                            InfoBarPosition,SwitchButton,ComboBox,HyperlinkButton,DoubleSpinBox,IndicatorPosition,
                            SpinBox,PillToolButton)
from qfluentwidgets import FluentIcon as FIF

# from resource.ui.SettingInterface_ui import Ui_SettingInterface


class SettingInterface(ScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent = parent)
        
        # self.setupUi(self)

        self.view = QtWidgets.QWidget()
        self.view.setObjectName("scrollAreaWidgetContents")
        self.vBoxLayout = QVBoxLayout(self.view)

        self.BasicSetCard = BaseSettingCard(self)    
        self.TestSetHeaderCard = TestSetHeaderCard(self)
        self.DescriptionCard = DescriptionCard(self)

        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("SettingInterface")

        self.vBoxLayout.setSpacing(10)
        self.vBoxLayout.setContentsMargins(30, 30, 30, 30)
        self.vBoxLayout.addWidget(self.BasicSetCard,0,Qt.AlignTop)
        self.vBoxLayout.addWidget(self.TestSetHeaderCard,0,Qt.AlignTop)
        self.vBoxLayout.addWidget(self.DescriptionCard,0,Qt.AlignTop)

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
    
    # def retranslateUi(self, AuthTestInterface):
        # self.TestSetHeaderCard.   
  
    def errorNotice(self,str):
        """错误提示"""   
        InfoBar.error(
            title='ERROR',
            content= str,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=-1,    # won't disappear automatically
            parent=self
        )


    def successNotice(self,str):
        """成功提醒"""
        InfoBar.success(
            title='SUCCESS',
            content= str,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            # position='Custom',   # NOTE: use custom info bar manager
            duration=2000,
            parent=self
        )

class BaseSettingCard(HeaderCardWidget):

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
        self.GridLayout.addWidget(self.LogLevelLabel,0,0,Qt.AlignLeft)  
        self.GridLayout.addWidget(self.LogLevelCombo,0,1,Qt.AlignRight)
        self.GridLayout.setColumnStretch(0, 1)
        self.GridLayout.setColumnStretch(1, 2)  
        
        self.tagPrintLabel = BodyLabel("标签打印次数", self)
        self.tagPrintNum   = SpinBox(self)
        self.GridLayout.addWidget(self.tagPrintLabel,1,0,Qt.AlignLeft)
        self.GridLayout.addWidget(self.tagPrintNum,1,1,Qt.AlignRight)


        self.TokenTakeAddrLabel = BodyLabel("注册地址选择", self)
        self.TokenTakeAddrCombo = ComboBox(self)
        self.TokenTakeAddrCombo.setMinimumWidth(200)
        self.GridLayout.addWidget(self.TokenTakeAddrLabel,2,0,Qt.AlignLeft)
        self.GridLayout.addWidget(self.TokenTakeAddrCombo,2,1,Qt.AlignRight)

        self.GridLayout.setAlignment(Qt.AlignLeft)

        # self.viewLayout.addLayout(self.GridLayout)
        self._componentInit()

    def _componentInit(self):
        """set lineEdit"""
        ComboBox_edits = self.findChildren(ComboBox) 
        SpinBox_edits = self.findChildren(SpinBox) 
        for le in ComboBox_edits: 
            le.setDisabled(True)    
        for le in SpinBox_edits:
            le.setDisabled(True)    

    def setComponentState(self,isChecked:bool):
        # 获取所有的控件  
        ComboBox_edits = self.findChildren(ComboBox) 
        SpinBox_edits = self.findChildren(SpinBox) 
  
        # 设置所有控件状态
        if  isChecked: 
            for le in ComboBox_edits: 
                le.setDisabled(False)    
            for le in SpinBox_edits:
                le.setDisabled(False)   
        else:
            for le in ComboBox_edits: 
                le.setDisabled(True)    
            for le in SpinBox_edits:
                le.setDisabled(True) 
        
class TestSetHeaderCard(HeaderCardWidget):
    def __init__(self,parent = None):
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
        #4G Test
        self.Test4GLabel = BodyLabel("4G测试", self)
        self.switchTest4G = SwitchButton(self.tr('Off'),self,IndicatorPosition.RIGHT)
        self.switchTest4G.checkedChanged.connect(self.onCheckedChanged)
        #flash retry
        self.RetryFlashTestLabel = BodyLabel("Flash测试重试次数", self)
        self.RetryFlashEdit = IntEditBox(99,self)
        #Gsensor retry
        self.RetryGsensorTestLabel = BodyLabel("Gsensor测试重试次数", self)
        self.RetryGsensorEdit = IntEditBox(99,self)

        #BatteryRead retry
        self.RetryBatteryReadLabel = BodyLabel("电池测试重试次数", self)
        self.RetryBatteryReadEdit = IntEditBox(99,self) 

        #Lte retry
        self.RetryLteLabel = BodyLabel("蜂窝测试重试次数", self)
        self.RetryLteEdit = IntEditBox(99,self)     

        #Main Battery MAX volt
        self.BattMaxVoltLabel = BodyLabel("主电池上限电压阈值(V)", self)
        self.BattMaxVoltEdit = DoubleEditBox(99,1,self)

        # Creat a HorizontalSeparator list
        HorizontalSeparator_list =  [HorizontalSeparator() for i in range(self.BoxNum)]

        #Main Battery MIN volt
        self.BattMinVoltLabel = BodyLabel("主电池下限电压阈值(V)", self)
        self.BattMinVoltEdit = DoubleEditBox(99,1,self)

        #Sub Battery MAX
        self.SubBattMaxVoltLabel = BodyLabel("备用电池上限电压阈值(V)", self)
        self.SubBattMaxVoltEdit = DoubleEditBox(9,0.1,self)

        #Sub Battery MIN volt
        self.SubBattMinVoltLabel = BodyLabel("备用电池下限电压阈值(V)", self)
        self.SubBattMinVoltEdit = DoubleEditBox(9,0.1,self)

        self.QGridLayOut.addWidget(self.Test4GLabel,self.GridRowCount,0,Qt.AlignLeft)
        self.QGridLayOut.addWidget(self.switchTest4G,self.GridRowCount,1,Qt.AlignRight)
        self.GridRowCount += 1

        self.QGridLayOut.addWidget(HorizontalSeparator_list[0],self.GridRowCount,0,1,2)
        self.GridRowCount += 1

        self.QGridLayOut.addWidget(self.RetryFlashTestLabel,self.GridRowCount,0,Qt.AlignLeft)
        self.QGridLayOut.addWidget(self.RetryFlashEdit,self.GridRowCount,1,Qt.AlignRight)
        self.GridRowCount += 1

        self.QGridLayOut.addWidget(self.RetryGsensorTestLabel,self.GridRowCount,0,Qt.AlignLeft)
        self.QGridLayOut.addWidget(self.RetryGsensorEdit,self.GridRowCount,1,Qt.AlignRight)
        self.GridRowCount += 1

        self.QGridLayOut.addWidget(self.RetryBatteryReadLabel,self.GridRowCount,0,Qt.AlignLeft)
        self.QGridLayOut.addWidget(self.RetryBatteryReadEdit,self.GridRowCount,1,Qt.AlignRight)
        self.GridRowCount += 1

        self.QGridLayOut.addWidget(self.RetryLteLabel,self.GridRowCount,0,Qt.AlignLeft)
        self.QGridLayOut.addWidget(self.RetryLteEdit,self.GridRowCount,1,Qt.AlignRight)
        self.GridRowCount += 1

        self.QGridLayOut.addWidget(HorizontalSeparator_list[1],self.GridRowCount,0,1,2)
        self.GridRowCount += 1

        self.QGridLayOut.addWidget(self.BattMaxVoltLabel,self.GridRowCount,0,Qt.AlignLeft)
        self.QGridLayOut.addWidget(self.BattMaxVoltEdit,self.GridRowCount,1,Qt.AlignRight)
        self.GridRowCount += 1

        self.QGridLayOut.addWidget(self.BattMinVoltLabel,self.GridRowCount,0,Qt.AlignLeft)
        self.QGridLayOut.addWidget(self.BattMinVoltEdit,self.GridRowCount,1,Qt.AlignRight)
        self.GridRowCount += 1

        self.QGridLayOut.addWidget(self.SubBattMaxVoltLabel,self.GridRowCount,0,Qt.AlignLeft)
        self.QGridLayOut.addWidget(self.SubBattMaxVoltEdit,self.GridRowCount,1,Qt.AlignRight)
        self.GridRowCount += 1

        self.QGridLayOut.addWidget(self.SubBattMinVoltLabel,self.GridRowCount,0,Qt.AlignLeft)
        self.QGridLayOut.addWidget(self.SubBattMinVoltEdit,self.GridRowCount,1,Qt.AlignRight)
        self.GridRowCount += 1

        
        #self.viewLayout.addLayout(self.QGridLayOut)
        self._LineEditInit()
        
       
    def _LineEditInit(self):
        """set lineEdit"""
        self.switchTest4G.setDisabled(True)
        Doubleline_edits = self.findChildren(DoubleEditBox) 
        Intline_edits = self.findChildren(IntEditBox) 
        for le in Intline_edits: 
            le.setDisabled(True)    
        for le in Doubleline_edits:
            le.setDisabled(True)    

    def setLineEditReadOnly(self,isChecked:bool):
        # 获取所有的LineEdit控件  
        Doubleline_edits = self.findChildren(DoubleEditBox) 
        Intline_edits = self.findChildren(IntEditBox) 
  
        # 设置所有的LineEdit为只读
        if  isChecked: 
            self.switchTest4G.setDisabled(False) 
            for le in Intline_edits: 
                le.setDisabled(False)    
            for le in Doubleline_edits:
                le.setDisabled(False)   
        else:
            self.switchTest4G.setDisabled(True)
            for le in Intline_edits: 
                le.setDisabled(True)    
            for le in Doubleline_edits:
                le.setDisabled(True) 


    def setValueLayOut(self,Box,LabelWidget,SpinBoxWidget,indicatorPos = 0):
        # set layout
        if(indicatorPos == 0):
            Box.addWidget(SpinBoxWidget,4)
            Box.addWidget(LabelWidget,4)
            Box.setAlignment(Qt.AlignRight)
        else:
            Box.addWidget(SpinBoxWidget,3,Qt.AlignRight)
            Box.addWidget(LabelWidget,3,Qt.AlignRight)
            Box.setAlignment(Qt.AlignRight)

    def onCheckedChanged(self, isChecked: bool):
        text = 'On' if isChecked else 'Off'
        self.switchTest4G.setText(text) 

class IntEditBox(SpinBox):
    """ Int line edit """
    # valueChanged = pyqtSignal(str)

    def __init__(self,max,parent = None):
        super().__init__(parent = parent)
        self.setFixedSize(120, 33)
        self.setMaximum(max)

class DoubleEditBox(DoubleSpinBox):
    """ Double line edit """
    # valueChanged = pyqtSignal(str)

    def __init__(self,max,step = 1,parent = None):
        super().__init__(parent = parent)
        self.setFixedSize(120, 33)
        self.setMaximum(max)
        self.setSingleStep(0.1)
        self.step = step

        # super().upButton.clicked.connect(self.stepUp)
        # super().downButton.clicked.connect(self.stepDown)

    def stepBy(self,step):  
        # 重载 stepBy 方法，允许你自定义每次step的值
        if(step == 1):  
            super().stepBy(self.step/0.1)
        else:
            super().stepBy(-self.step/0.1)

    def stepUp(self):  
        # 重载 stepUp 方法，允许你自定义每次step的值
            super().stepBy(self.step/0.1)

    def stepDown(self):
        # 重载 stepDown 方法，允许你自定义每次step的值    
            super().stepBy(-self.step/0.1)


class DescriptionCard(HeaderCardWidget):
    """ Description card """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.horizontalLayout = QHBoxLayout(self)

        self.descriptionLabel = BodyLabel('以上配置项可以根据实际产测环境进行配置, 详细设置说明请见', self)
        self.descriptionLabel.setMaximumWidth(999)
        # self.descriptionLabel.setWordWrap(True)
        self.hyperlinkButton = HyperlinkButton(
            url='https://im.qq.com/pcqq/index.shtml',
            text='<产测说明文档>',
            parent=self,
            icon=FIF.LINK
        )
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addWidget(self.descriptionLabel)
        self.horizontalLayout.addWidget(self.hyperlinkButton)
        self.horizontalLayout.addItem(spacerItem)
        
        self.viewLayout.addLayout(self.horizontalLayout)

        self.setTitle('关于')
