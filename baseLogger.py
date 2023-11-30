import time
import os
import logging
from logging import handlers
from PyQt5.QtCore import *
from PyQt5.QtCore import pyqtSignal
import baseUtils

formater = '%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s'


class ConsolePanelHandler(QObject, logging.Handler):
    new_record = pyqtSignal(object)

    def __init__(self, parent):
        # logging.Handler.__init__(self)
        # self.parent = parent
        super().__init__(parent)
        super(logging.Handler).__init__()
        # 设置日志格式
        format_str = logging.Formatter(formater)
        self.setFormatter(format_str)

    def emit(self, record):
        msg = self.format(record) + '\r\n'
        self.new_record.emit(msg)


# 路径管理
def log_path_check():
    log_path = os.getcwd() + '/Logs/'
    if not os.path.exists(log_path):
        os.mkdir(log_path)
    day = time.strftime('%Y-%m-%d', time.localtime())
    log_name = log_path + day + '.log'
    return log_name


class Logger(object):
    def __init__(self, filename=log_path_check(), level='info', when='D', backCount=3,
                 fmt=formater):
        # 日志级别关系映射
        self.level_relations = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'crit': logging.CRITICAL
        }
        self.logger = logging.getLogger(__name__)
        print("baseLogger.Logger", self.logger)

        # 创建BaseUtils实例
        self.util = baseUtils.BaseUtils()

        # 通过外部ini文件配置相关参数
        # 获取log level
        try:
            self.settings = QSettings("resource/config/sys_config.ini", QSettings.IniFormat)
            self.loggerLevel = self.settings.value("SETUP/logger_level")
            level = self.loggerLevel
        except:
            level = 'info'

        print("log level:", level)

        # 设置日志格式
        format_str = logging.Formatter(fmt)
        # 设置日志级别
        try:
            self.logger.setLevel(self.level_relations.get(level))
        except TypeError as e:
            self.logger.setLevel(logging.INFO)
        # 输出到控制台
        sh = logging.StreamHandler()
        # 设置屏幕上显示的格式
        sh.setFormatter(format_str)
        th = handlers.TimedRotatingFileHandler(filename=filename, when=when, backupCount=backCount, encoding='GBK')
        # 往文件里写入#指定间隔时间自动生成文件的处理器
        # 实例化TimedRotatingFileHandler
        # interval是时间间隔，backupCount是备份文件的个数，如果超过这个个数，就会自动删除，when是间隔的时间单位，单位有以下几种：
        # S 秒
        # M 分
        # H 小时、
        # D 天、
        # W 每星期（interval==0时代表星期一）
        # midnight 每天凌晨

        # 设置文件里写入的格式
        th.setFormatter(format_str)
        # 把对象加到logger里
        self.logger.addHandler(sh)
        self.logger.addHandler(th)


log = Logger()

if __name__ == '__main__':
    # log = Logger('all.log', level='debug')
    log.logger.debug('debug')
    log.logger.info('info')
    log.logger.warning('警告')
    log.logger.error('报错')
    log.logger.critical('严重')
    # Logger('error.log', level='error').logger.error('error')
