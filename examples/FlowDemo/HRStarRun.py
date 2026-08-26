# run.py
import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(path))
import HRVision.HRFlowController
if __name__ == "__main__":
	sys.argv = [path, '--flow', os.path.join(os.path.dirname(path), 'Flow'), '--main', 'main', '--code', os.path.join(os.path.dirname(path), 'Flow', 'ProgramCode.dat')]
	HRVision.HRFlowController.main()
	sys.exit(0)
# 注意：不要在模块级 import importFlow —— spawn 子进程会以 __mp_main__ 重执行本文件，
# 会触发节点代码片段（等帧处理_a2 等）在无框架注入时执行 → AttributeError。
# 流程模块收集已移到 Spec.spec 的 hiddenimports（打包用）。
