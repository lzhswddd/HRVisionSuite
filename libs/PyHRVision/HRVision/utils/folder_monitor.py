#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import threading
from datetime import datetime

class FolderMonitor:
    def __init__(self, folder_path, max_size_bytes, max_age_days=None, interval=60, debugPrint=False):
        """
        :param folder_path: 要监控的目录路径
        :param max_size_bytes: 最大容量（字节）
        :param max_age_days: 文件最大保留天数，超过此天数的老文件会被删除（可选）
        :param interval: 检查间隔（秒）
        """
        self.folder = folder_path
        self.max_size = max_size_bytes
        self.max_age_days = max_age_days
        self.interval = interval
        self.thread:threading.Thread = None
        self.loop = True
        self.stop_event = threading.Event()
        self.debugPrint = debugPrint
            
    def __del__(self):
        """析构函数，确保线程被停止"""
        self.stop()
        if self.debugPrint:
            print("FolderMonitor 线程已停止。")

    def get_dir_size(self):
        """递归计算目录大小（字节）"""
        total = 0
        for root, _, files in os.walk(self.folder):
            for f in files:
                fp = os.path.join(root, f)
                if not os.path.islink(fp):
                    try:
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
        return total

    def list_files_sorted_by_mtime(self):
        """列出目录下所有文件，按修改时间从旧到新排序"""
        file_list = []
        for root, _, files in os.walk(self.folder):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(fp)
                    file_list.append((fp, mtime))
                except OSError:
                    pass
        file_list.sort(key=lambda x: x[1])
        return [fp for fp, _ in file_list]

    def remove_empty_dirs(self):
        """递归删除空目录"""
        for root, dirs, _ in os.walk(self.folder, topdown=False):
            for d in dirs:
                dp = os.path.join(root, d)
                if not os.listdir(dp):
                    try:
                        os.rmdir(dp)
                        if self.debugPrint:
                            print(f"删除空目录: {dp}")
                    except OSError:
                        pass

    def remove_old_files(self):
        """删除超过设定年龄的文件"""
        if self.max_age_days is None:
            return
        cutoff = time.time() - self.max_age_days * 86400
        for root, _, files in os.walk(self.folder):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(fp)
                except OSError:
                    continue
                if mtime < cutoff:
                    try:
                        os.remove(fp)
                        if self.debugPrint:
                            print(f"删除老文件: {fp} (修改时间: {datetime.fromtimestamp(mtime)})")
                    except OSError:
                        pass

    def enforce_max_size(self):
        """当总大小超限时，删除最早的文件直到低于阈值"""
        size = self.get_dir_size()
        if size <= self.max_size:
            return
        if self.debugPrint:
            print(f"当前目录大小 {size} 字节，超过阈值 {self.max_size} 字节，开始按时间顺序清理……")
        for fp in self.list_files_sorted_by_mtime():
            if size <= self.max_size:
                break
            try:
                fsize = os.path.getsize(fp)
                os.remove(fp)
                size -= fsize
                if self.debugPrint:
                    print(f"删除文件: {fp} ({fsize} 字节)，剩余 {size} 字节")
            except OSError:
                pass
        self.remove_empty_dirs()
        if self.debugPrint:
            print("大小清理完成。")

    def run_once(self):
        """执行一次清理周期：先删老文件，再删超限文件，再删空目录"""
        self.remove_old_files()
        self.enforce_max_size()
        self.remove_empty_dirs()

    def run(self):
        """持续监控，按 interval 定期执行"""
        if self.debugPrint:
            print(f"开始监控 {self.folder}，阈值 {self.max_size} 字节，文件最大保存 {self.max_age_days} 天，检查间隔 {self.interval} 秒")
        try:
            self.loop = True
            while self.loop:
                if not os.path.exists(self.folder):
                    if self.debugPrint:
                        print(f"目录不存在: {self.folder}")
                    break
                self.run_once()
                self.stop_event.wait(self.interval) 
        except KeyboardInterrupt:
            if self.debugPrint:
                print("已停止监控。")
            
    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self.run)
            self.thread.start()
    
    def stop(self):
        if self.thread is not None:
            self.loop = False
            self.stop_event.set()
            self.thread.join()
            self.thread = None
    
if __name__ == "__main__":
    # 配置示例
    WATCH_FOLDER   = r"D:\Python\frame\test"
    MAX_SIZE_MB    = 500           # 最大容量（MB）
    MAX_AGE_DAYS   = 90            # 文件最大保留期（天），例如 90 天
    INTERVAL_SEC   = 10           # 检查间隔（秒）

    max_bytes = MAX_SIZE_MB * 1024 * 1024
    monitor = FolderMonitor(WATCH_FOLDER, max_bytes, max_age_days=MAX_AGE_DAYS, interval=INTERVAL_SEC, debugPrint=True)
    monitor.start()

    try:
        input("按任意键退出...\n")
    except KeyboardInterrupt:
        print("\n检测到中断，正在退出...")
    finally:
        monitor.stop()