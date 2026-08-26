# -*- coding: utf-8 -*-
# 退出检查：raise ("return", 0) 回等待触发（循环）；("return", 1) 走 handle 2 → 结束
from camera.ThreadGlobalData import *
raise Exception("return", 0)
