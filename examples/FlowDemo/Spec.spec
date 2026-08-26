# -*- mode: python ; coding: utf-8 -*-
import importlib.util
import os
import sys
# 使用 sys.argv[0] 获取.spec 文件名
current_file_name = os.path.basename(sys.argv[0]).replace('.spec', '')
print(f"Current file name: {current_file_name}")
SPEC_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))   # 项目根（pathex：Flow/services 可解析）
def get_package_path(package_name):
    """
    动态获取包路径
    : param package_name: 包名
    :return: 包的根目录路径
    """
    spec = importlib.util.find_spec(package_name)
    if spec is not None:
        return spec.submodule_search_locations[0]  # 获取包的根目录
    else:
        raise RuntimeError(f"Package {package_name} not found.")
# 使用函数获取路径
hrvision_package_path = get_package_path("HRVision")
print(f"Package path: {hrvision_package_path}")
hrfluentwidgets_package_path = get_package_path("hrfluentwidgets")
print(f"Package path: {hrfluentwidgets_package_path}")
a = Analysis(
    ['HRStarRun.py'],
    pathex = [SPEC_DIR],
    binaries = [],
    datas = [
        # ---- FlowDemo 运行时文件（缺失任何一项 = 冻结包对应功能不可用） ----
        ('Flow/*.ndjs', 'Flow'),                 # 流程图（开发路径；--code 时用 dat）
        ('Flow/*.dat', 'Flow'),                  # 代码包（ProgramCode.dat ← --code 路径）
        ('Flow/pipeline.json', 'Flow'),          # 管线拓扑！ProgramGlobalData 运行时加载，缺了会静默回退内置默认
        ('Flow/videos/*.avi', 'Flow/videos'),    # 模拟视频源（缺了相机无帧可抓）
        # 兜底：节点/固定 py 落盘（节点代码来自 dat 时不需要；保留防框架按文件读）
        ('Flow/algo/*.py', 'Flow/algo'),
        ('Flow/camera/*.py', 'Flow/camera'),
        ('Flow/main/*.py', 'Flow/main'),
        ('Flow/ProgramGlobalData.py', 'Flow'),
        # ---- HRVision 运行时 ----
        # 将 HRVision.Bin 文件夹中的所有.dll 文件添加到打包数据中
        (hrvision_package_path + '/bin/*.dll', 'HRVision/bin'),
        (hrfluentwidgets_package_path + '/motion/thirdparty/*.dll', 'hrfluentwidgets/motion/thirdparty'),
        # 认证文件：HRAuth 按 HRVision_license_*.lic 通配查找（cwd 优先，取最新）。
        # 不要写死日期名（如 HRVision_license_20260814_121524.lic）——换授权会漏打。
        (hrvision_package_path + '/HRVision_license_*.lic', '.'),
    ],
    hiddenimports = [
        # 流程/业务模块收集（原 importFlow.py 静态链已移除；节点文件是代码片段，
        # 运行时不可 import，故只能走 hiddenimports）
        'Flow.algo.等帧处理_a2', 'Flow.algo.开始_a1', 'Flow.algo.透传_a3',
        'Flow.algo.ThreadGlobalData',
        'Flow.camera.开始_c1', 'Flow.camera.退出检查_c3', 'Flow.camera.抓帧_c2',
        'Flow.camera.ThreadGlobalData',
        'Flow.main.创建UI_m3', 'Flow.main.结束_m4', 'Flow.main.开始_m1',
        'Flow.main.启动进程_m2', 'Flow.main.ThreadGlobalData',
        'Flow.ProgramGlobalData',
        'services.algo_engine', 'services.camera_driver', 'services.ui',
        # 认证：HRAuth 是 Python 模块，入口未 import 时 PyInstaller 静态分析看不到
        #（框架 pyd 内部 import 无法被分析追踪）；wmi/Crypto 同理（pyd 内部依赖）
        'HRVision.HRAuth', 'HRVision.HRLicenseCheck', 'wmi',
        'Crypto.Cipher', 'Crypto.Util.Padding',
    ],
    hookspath = [],
    hooksconfig = {},
    runtime_hooks = [],
    excludes = [],
    noarchive = False,
    optimize = 0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries = True,
    name = 'FlowDemo',
    debug = False,
    bootloader_ignore_signals = False,
    strip = False,
    upx = True,
    console = True,
    disable_windowed_traceback = False,
    argv_emulation = False,
    target_arch = None,
    codesign_identity = None,
    entitlements_file = None,
    version = 'version_info.txt',  # 指定版本信息文件
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip = False,
    upx = True,
    upx_exclude = [],
    name = 'FlowDemo',
)
