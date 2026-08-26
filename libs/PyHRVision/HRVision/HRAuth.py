# -*- coding: utf-8 -*-
"""HRAuth - HRVision 一键认证模块

任何程序只需 import 后一行调用即可完成认证：

    import HRAuth

    if not HRAuth.check_license():      # 失败已弹窗提示，返回 False
        sys.exit(1)

    HRAuth.check_license()              # 一键模式：失败自动弹窗（60 秒倒计时）并退出

    HRAuth.check_license(exit_on_fail=False)          # 失败返回 False，由调用方决定
    HRAuth.check_license(pattern="MyApp_license_*.lic")  # 自定义认证文件命名
    HRAuth.check_license(popup=False)                 # 无弹窗，控制台打印提示
    HRAuth.check_license(on_fail=lambda code: log(code))  # 失败回调（code 为本机硬件码或 None）

认证流程（与 HRLicensing 一致）：
    查找认证文件 → LicenseCheck（注册表优先 → 文件回退 → 通过后写注册表并删除文件）
    失败时弹窗显示本机硬件码（用户可复制发给厂商注册），倒计时结束后进程退出。

分发清单（3 个文件放同一目录即可）：
    HRAuth.py
    HRLicenseCheck.cp312-win_amd64.pyd   # 认证核心（Cython 编译，保护认证逻辑）
    HRVision_license_*.lic               # 授权文件（HRLicensingUI 生成）
"""
import glob
import os
import sys
import threading
import time

_DEFAULT_PATTERN = "HRVision_license_*.lic"

_popup_lock = threading.Lock()


def _load_license_check():
    """加载认证核心模块：优先包内相对导入（HRVision 包内），失败则绝对导入（pyd 放程序目录）"""
    try:
        from .HRLicenseCheck import LicenseCheck, RegisterLicenseFailed
        return LicenseCheck, RegisterLicenseFailed
    except ImportError:
        import HRLicenseCheck
        return HRLicenseCheck.LicenseCheck, HRLicenseCheck.RegisterLicenseFailed


def find_license_file(pattern=_DEFAULT_PATTERN, extra_dirs=None):
    """查找认证文件：当前目录 → 本模块所在目录 → sys.path（可附加 extra_dirs），多个取最新

    Returns:
        认证文件绝对路径；未找到返回 None
    """
    candidates = []
    search_dirs = [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    if extra_dirs:
        search_dirs.extend(extra_dirs)
    search_dirs.extend(sys.path)
    seen = set()
    for search_dir in search_dirs:
        if not search_dir or search_dir in seen:
            continue
        seen.add(search_dir)
        candidates.extend(glob.glob(os.path.join(search_dir, pattern)))
    if not candidates:
        return None
    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0]


def _show_popup(text, timeout=60):
    """tkinter 弹窗显示文本，倒计时自动关闭；无 GUI 环境自动降级为控制台打印"""
    with _popup_lock:
        try:
            import tkinter as tk
            from tkinter import Toplevel, Text, Button

            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口

            popup = Toplevel()
            popup.title("Message")

            # 可复制的文本框
            text_box = Text(popup, wrap="word", height=12, width=64)
            text_box.insert("1.0", text)
            text_box.config(state="disabled")  # 只读
            text_box.pack(padx=10, pady=10, fill="both", expand=True)

            # 倒计时标签
            countdown_label = tk.Label(popup, text=f"Closing in {timeout} seconds...")
            countdown_label.pack(pady=5)

            # 关闭按钮
            def close_and_exit():
                popup.destroy()
                root.quit()

            close_button = Button(popup, text="Close", command=close_and_exit)
            close_button.pack(pady=5)

            popup.protocol("WM_DELETE_WINDOW", close_and_exit)

            def timeOut_closing():
                for i in range(timeout, 0, -1):
                    countdown_label.config(text=f"Closing in {i} seconds...")
                    time.sleep(1)
                popup.destroy()
                root.quit()

            th = threading.Thread(target=timeOut_closing)
            th.daemon = True
            th.start()
            popup.mainloop()
            return True
        except Exception:
            # 无 GUI 环境（Tk 创建失败等）→ 降级为打印
            print(text)
            return False


def check_license(pattern=_DEFAULT_PATTERN, exit_on_fail=True, popup=True,
                  timeout=60, on_fail=None, extra_dirs=None,
                  company="英锐捷（厦门）信息科技有限公司", project=""):
    """一键认证入口。

    Args:
        pattern: 认证文件命名模式，默认 HRVision_license_*.lic
        exit_on_fail: 认证失败时是否退出程序（默认 True）
        popup: 失败时是否弹窗提示（无 GUI 自动降级为打印）
        timeout: 弹窗倒计时秒数（默认 60）
        on_fail: 失败回调 on_fail(code)，code 为本机硬件码字符串；找不到文件时为 None
        extra_dirs: 附加的认证文件搜索目录列表
        company: 期望公司标记（v2 授权码 company 字段；默认英锐捷（厦门）信息科技有限公司）
        project: 期望项目名（v2 授权码 project 字段，支持中文；空 = 不锁项目）

    Returns:
        True 认证通过；False 认证失败（仅 exit_on_fail=False 时返回）
    """
    LicenseCheck, RegisterLicenseFailed = _load_license_check()

    # 注册失败回调：LicenseCheck 校验失败时会先回调（携带本机硬件码），随后终止进程。
    # 在回调中弹窗（mainloop 阻塞），用户看完/倒计时结束 → 关闭弹窗 → 进程退出。
    def _on_failed(data, user):
        try:
            code = data.decode('utf-8')
        except Exception:
            code = str(data)
        if on_fail:
            try:
                on_fail(code)
            except Exception:
                pass
        msg = "License authentication failed. Please verify your license.\n\n" \
              "license code:\n\n" + code
        if popup:
            _show_popup(msg, timeout)
        else:
            print(msg)

    RegisterLicenseFailed(_on_failed)

    license_path = find_license_file(pattern, extra_dirs)
    if license_path is None:
        # 找不到认证文件：不触发 LicenseCheck，由本模块直接提示并退出
        msg = ("License authentication failed. No license file found.\n\n"
               "Please contact your vendor to obtain a license file:\n" + pattern)
        if on_fail:
            try:
                on_fail(None)
            except Exception:
                pass
        if popup:
            _show_popup(msg, timeout)
        else:
            print(msg)
        if exit_on_fail:
            sys.exit(1)
        return False

    # project 空 = 不锁项目（只锁公司）；非空 = 项目锁（防串用）
    ret = LicenseCheck(license_path, company=company, project=project)
    if ret == 0:
        return True
    # LicenseCheck 失败时内部已触发回调（弹窗）并终止进程，正常到不了这里；防御性兜底
    if exit_on_fail:
        sys.exit(1)
    return False


if __name__ == "__main__":
    check_license()
