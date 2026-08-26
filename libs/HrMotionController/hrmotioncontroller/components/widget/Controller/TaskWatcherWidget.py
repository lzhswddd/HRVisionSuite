from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QTableWidgetItem
from qfluentwidgets import (SimpleCardWidget,DotInfoBadge,TransparentPushButton,BodyLabel,StrongBodyLabel,
                            InfoLevel,FlowLayout,isDarkTheme,InfoBar,TableWidget)
from ....common import MotionBase, MotionStatus, TaskerBase, TaskState, Controller

class TaskerDetailWidget(SimpleCardWidget):
    def __init__(self, name, tasker:TaskerBase, parent=None):
        super().__init__(parent)
        self.name = name
        self.tasker = tasker
        
        # Create UI elements
        self.setObjectName(self.name)
        self.labelList = {}
        layout = QVBoxLayout(self)
        
        self.tabelWidget = TableWidget(self)
        self.tabelWidget.setColumnCount(2)
        self.tabelWidget.setRowCount(len(self.tasker.__dict__))
        layout.addWidget(self.tabelWidget)
        count = 0
        for key, value in self.tasker.__dict__.items():
            # NameLabel = StrongBodyLabel(key, self)
            # NameLabel.setAlignment(Qt.AlignLeft)
            
            # label = BodyLabel(f"{value}", self)
            # label.setAlignment(Qt.AlignLeft)
            item1 = QTableWidgetItem()
            item1.setText(f"{key}")
            
            item2 = QTableWidgetItem()
            item2.setText(f"{value}")
            
            self.tabelWidget.setItem(count, 0, item1)
            self.tabelWidget.setItem(count, 1, item2)
            count = count + 1
            
            self.labelList[key] = item2
            
        self.setWindowTitle("TaskerDetailWidget")
        if isDarkTheme():
            self.setStyleSheet("TaskerDetailWidget {background: rgb(32,32,32);}")
        else:
            self.setStyleSheet("TaskerDetailWidget {background: rgb(255,255,255);}")
            
        self.timerId = self.startTimer(1000)  # 每秒更新一次
        
    def updateTaskerDetails(self):
        """ 更新任务器的详细信息 """
        if self.tasker is not None:
            dict_data = self.tasker.__dict__.copy()
            for key, value in dict_data.items():
                if key in self.labelList:
                    self.labelList[key].setText(f"{value}")
                # else:
                #     hlayout = QHBoxLayout()
                    
                #     NameLabel = StrongBodyLabel(key, self)
                #     NameLabel.setAlignment(Qt.AlignLeft)
                #     label = BodyLabel(f"{value}", self)
                #     label.setAlignment(Qt.AlignLeft)
                    
                #     hlayout.addWidget(NameLabel)
                #     hlayout.addWidget(label, 1)
                #     self.layout().addLayout(hlayout)
                #     self.labelList[key] = label
        
    def timerEvent(self, event):
        if event.timerId() == self.timerId:
            self.updateTaskerDetails()
        """ 定时器事件，用于更新任务器状态 """
        super().timerEvent(event)

class TaskerLed(SimpleCardWidget):
    def __init__(self, name, taskerName:str, tasker, parent=None):
        super().__init__(parent)
        self.name = name
        self.taskerName = taskerName
        self.tasker = tasker  # TaskerBase instance

        # Create UI elements
        self.setObjectName(self.name)
        layout = QHBoxLayout(self)
        self.status = DotInfoBadge.info()
        self.btn = TransparentPushButton(self.name, self)

        self.status.setFixedSize(30,30)
        self.setMaximumSize(150,50)
        self.setMinimumSize(150,50)
        # self.btn.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # Add elements to layout
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        layout.addWidget(self.status,0,Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.btn,1,Qt.AlignmentFlag.AlignLeft)
        
        self.taskerDetailWidget = None  # Placeholder for tasker detail widget
        
        self.btn.clicked.connect(self.onShowTaskerDetails)
        # self.label.setToolTip("任务:{}".format(self.taskerName))
        # self.label.installEventFilter(ToolTipFilter(self.label, 500,ToolTipPosition.BOTTOM_RIGHT))

    def setTaskerStatus(self, status:TaskState):
        if status == TaskState.IDLE:
            self.status.setLevel(InfoLevel.INFOAMTION)
        elif status == TaskState.RUNNING:
            self.status.setLevel(InfoLevel.ATTENTION)
        elif status in [TaskState.FAILED, TaskState.TIMEOUT, TaskState.STOPPED]:
            self.status.setLevel(InfoLevel.ERROR)
        elif status in [TaskState.PAUSED, TaskState.STOPPED]:
            self.status.setLevel(InfoLevel.WARNING)
        elif status == TaskState.COMPLETED:
            self.status.setLevel(InfoLevel.SUCCESS)
        else:
            self.status.setLevel(InfoLevel.INFOAMTION)

    def getTaskerName(self):
        return self.taskerName
    
    def onShowTaskerDetails(self):
        """ 显示任务器的详细信息 """
        if self.taskerDetailWidget is not None:
            InfoBar.warning(
                self.tr("警告"), 
                self.tr("任务信息窗体已存在，请先关闭当前窗体。"),
                parent=self.window())
        else:
            self.taskerDetailWidget = TaskerDetailWidget(self.name, self.tasker, self)
            self.taskerDetailWidget.setParent(self, Qt.WindowType.Window)
            self.taskerDetailWidget.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            self.taskerDetailWidget.destroyed.connect(lambda: setattr(self, 'taskerDetailWidget', None))
            self.taskerDetailWidget.show()
    
class TaskerWatchWidget(QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.setWindowTitle("TaskerWatchWidget")
        if isDarkTheme():
            self.setStyleSheet("TaskerWatchWidget {background: rgb(32,32,32);}")
        else:
            self.setStyleSheet("TaskerWatchWidget {background: rgb(255,255,255);}")
        self.controller:Controller = kwargs.get('controller', None)
        
    def setController(self, controller: Controller):
        """ 设置控制器实例，用于获取任务状态等信息  
        :param controller: 控制器实例
        """
        self.controller = controller
            
    def initWidget(self):
        # rows = len(self.ioList) // cols
        self.layout_ = FlowLayout(self)
        self.layout_.setSpacing(6)
        self.layout_.setContentsMargins(30, 30, 30, 30)
        self.layout_.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        if self.controller is not None:
            for name, tasker in self.controller.get_all_taskers().items():
                taskerWidget = TaskerLed(tasker.name, name, tasker, self)
                self.layout_.addWidget(taskerWidget)
        self.resize(500,800)

        self.startTimer(200)

    def updateTaskerStatus(self):
        try:
            for index in range(self.layout_.count()):
                item = self.layout_.itemAt(index)
                if not item:
                    continue
                taskerWidget = item.widget()
                if not isinstance(taskerWidget, TaskerLed):
                    continue
                taskerName = taskerWidget.getTaskerName()
                tasker = self.controller.get_tasker(taskerName)  # Ensure tasker is loaded
                taskerWidget.setTaskerStatus(tasker.state)
        except Exception as e:
            print(f"Error updating TaskerBase status: {e}")

    def timerEvent(self, event):
        self.updateTaskerStatus()
        return super().timerEvent(event)
