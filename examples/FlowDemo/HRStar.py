# -*- coding: utf-8 -*-
"""FlowDemo 入口：仅框架流程代码。

业务逻辑（相机驱动/算法引擎/管线管理/监控/UI）全部封装在 services/ 与
Flow/ 节点胶水里；本文件只做框架装配。框架本体用环境 pyd：
    from HRVision.HRFlowController import main
"""
import os
import sys

path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(path))   # 项目根（services 可导入；spawn 子进程也经 __mp_main__ 执行此行）

if __name__ == "__main__":
    sys.argv = [path, '--flow', os.path.join(os.path.dirname(path), 'Flow'), '--main', 'main']
    from HRVision.HRFlowController import main
    main()
