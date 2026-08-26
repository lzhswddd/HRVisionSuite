# -*- coding: utf-8 -*-
"""启动管线：pipeline_spec → PipelineManager 装配启动。"""
from main.ThreadGlobalData import *
from HRVision.HRFlowController import PipelineManager

gData.user.pipeline = PipelineManager(
    gData, signal_instance, gData.user.pipeline_spec, gData.user)
gData.user.pipeline.start()
raise Exception("return", 0)
