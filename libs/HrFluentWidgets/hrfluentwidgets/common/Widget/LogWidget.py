from qfluentwidgets import TextEdit, CommandBar, Action, FluentIcon, HeaderCardWidget
from PySide6.QtCore import Qt,QThread,Signal,QObject,QTimer
import logging
from logging.handlers import TimedRotatingFileHandler
import os

# 全局日志记录器
log = logging.getLogger()
log.setLevel(logging.DEBUG)

# 初始化文件handler（只需执行一次）
if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = TimedRotatingFileHandler(
    filename='logs/logRecord.log',
    when='midnight',
    backupCount=90,
    encoding='utf-8'
)
file_handler.suffix = "%Y-%m-%d.log"
# 添加格式器 ↓↓↓
file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s.%(msecs)03d][%(levelname)s][%(filename)s:%(lineno)d][%(name)s][%(funcName)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
log.addHandler(file_handler)

class QTextEditHandler(QObject, logging.Handler):
    _log_signal = Signal(str)
    def __init__(self, textedit: TextEdit):
        QObject.__init__(self)
        logging.Handler.__init__(self)
        self.textedit = textedit
        
        # 初始化缓冲区和定时器
        self._buffer = []
        self._timer = QTimer()
        self._timer.timeout.connect(self._flush_buffer)
        self._timer.start(100)  # 每100毫秒刷新一次
        
        self._log_signal.connect(self._safe_append)

        self.isShowColor = True

    def _get_log_color(self, level):
        """ 根据日志级别返回RGB颜色 """
        return {
            logging.DEBUG: '#808080',        # 灰色
            logging.INFO: '#FFFFFF',         # 白色
            logging.WARNING: '#FF8C00',      # 橙色
            logging.ERROR: '#CD5C5C',       # 红色
            logging.CRITICAL: '#9370DB'
        }.get(level, '#FFFFFF')

    def _safe_append(self, msg):
        """ 线程安全的缓冲区添加 """
        self._buffer.append(msg)

    def emit(self, record):
        """ 重写日志处理器方法 """
        msg = self.format(record)
        # 添加字体大小定义 ↓↓↓
        if self.isShowColor:
            color = self._get_log_color(record.levelno)
            bold = "font-weight: bold;" if record.levelno >= logging.WARNING else ""
            colored_msg = f'<span style="{bold}color:{color}; font-family: Consolas; font-size: 11pt;">{msg}</span>'
            self._log_signal.emit(colored_msg)
        else:
            color = self._get_log_color()
            colored_msg = f'<span style="color:{color}; font-family: Consolas; font-size: 11pt;">{msg}</span>'
            self._log_signal.emit(colored_msg)

    def _flush_buffer(self):
        """ 批量刷新到UI """
        if self._buffer:
            # 直接拼接HTML内容（已包含换行标签）
            self.textedit.append('<br>'.join(self._buffer))
            self._buffer.clear()

class LogWidget(HeaderCardWidget):
    """ 日志显示组件 """
    def __init__(self, parent=None,identifier=""):
        super().__init__(parent)
        self.identifier = identifier  # 新增唯一标识
        self._init_ui()

    def _init_ui(self):
        """ 初始化界面组件 """
        self.setObjectName('logWidget')
        self.headerLayout.setContentsMargins(16, 0, 8, 0)
        self.headerView.setFixedHeight(32)
        self.setTitle(self.tr("日志"))

        # 日志显示区域
        self.textEdit = TextEdit(self)
        self.textEdit.setAcceptRichText(True)
        self.textEdit.setReadOnly(True)
        self.textEdit.document().setMaximumBlockCount(1000)
        self.textEdit.setFontFamily("Consolas")
        self.textEdit.setFontPointSize(11)
        self.viewLayout.setContentsMargins(1, 1, 1, 1)
        self.viewLayout.addWidget(self.textEdit)

        # 工具栏
        self.action = Action(FluentIcon.DELETE, self.tr("Clear"), triggered=self.textEdit.clear)
        self.commandBar = CommandBar(self)
        self.commandBar.addAction(self.action)
        self.commandBar.resizeToSuitableWidth()
        self.headerLayout.addWidget(self.commandBar, Qt.AlignRight)

        self.handler = QTextEditHandler(self.textEdit)
        self.handler.addFilter(self._log_filter)  # 添加过滤器
        self.handler.setFormatter(logging.Formatter(
            '[%(asctime)s.%(msecs)03d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self.handler.setLevel(logging.INFO) 
        log.addHandler(self.handler)

    def _log_filter(self, record):
        """ 根据标识符过滤日志 """
        if not self.identifier:
            # 显示所有未标记的日志
            return not hasattr(record, 'recordID')
        else:
            # 只显示匹配标识符的日志
            return getattr(record, 'recordID', '') == self.identifier

    def setShowColor(self, isShowColor):
        self.handler.isShowColor = isShowColor

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
    from PySide6.QtCore import QTimer
    from qfluentwidgets import FluentIcon as FIF

    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout(window)
    logWidget = LogWidget()
    layout.addWidget(logWidget)

    button = QPushButton("测试日志")
    button.clicked.connect(lambda: log.info("这是一条测试日志"))
    layout.addWidget(button)

    window.show()

    # class Worker(QThread):
    #     def __init__(self):
    #         super().__init__()
    #         self.logger = log.getChild(self.__class__.__name__)
    #     def run(self):
    #         for i in range(1000000):
    #             self.logger.debug("debug 消息")
    #             self.logger.info("info 消息")
    #             self.logger.warning("warning 消息")
    #             self.logger.error("error 消息")
    #             self.logger.critical("critical 消息")

    # worker = Worker()
    # worker.start()

    # 测试不同标识符的日志
    log_widget1 = LogWidget(identifier="CAMERA")  # 相机相关日志
    log_widget2 = LogWidget(identifier="MOTION")  # 运动控制日志

    log_widget1.show()
    log_widget2.show()

    log.info("相机初始化完成", extra={"recordID": "CAMERA"})
    log.warning("运动控制超时", extra={"recordID": "MOTION"})

    sys.exit(app.exec())