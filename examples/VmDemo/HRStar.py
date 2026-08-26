# -*- coding: utf-8 -*-
"""VmDemo 入口：仅框架流程代码。

业务逻辑（VM 桥接 / 算法 / UI）全部封装在 services/ 与 Flow/ 节点胶水里；
本文件只做框架装配。框架本体用环境 pyd：
    from HRVision.HRFlowController import main
"""
import os
import sys

path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(path))

if __name__ == "__main__":
    sys.argv = [path, '--flow', os.path.join(os.path.dirname(path), 'Flow'), '--main', 'main']
    from HRVision.HRFlowController import main
    main()
