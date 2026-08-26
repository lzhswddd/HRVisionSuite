# -*- coding: utf-8 -*-
"""启动管线：pipeline_spec → PipelineManager 装配启动。

类型：ProgramData.pipeline 已在类字段标注（PipelineManager | None）——
动态模块实例（gData.user）上不能做属性注解（Pylance 无法解析其类型）。
"""
from main.ThreadGlobalData import *
from HRVision.HRFlowController import PipelineManager

gData.user.pipeline = PipelineManager(
    gData, signal_instance, gData.user.pipeline_spec, gData.user)
gData.user.pipeline.start()
raise Exception("return", 0)
