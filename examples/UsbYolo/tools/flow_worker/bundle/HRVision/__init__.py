# -*- coding: utf-8 -*-
"""HRVision 包（打包子进程精简版）：仅框架核心 + ProcessIsolate。"""
import os
import sys
import sysconfig

__path__ = __import__('pkgutil').extend_path(__path__, __name__)


def find_hr():
    ext_suffix = sysconfig.get_config_var('EXT_SUFFIX') or '.so'
    pyd_filename = 'HRFlowController' + ext_suffix
    package_dir = os.path.dirname(__file__)
    if os.path.isfile(os.path.join(package_dir, pyd_filename)):
        if sys.platform.startswith('win'):
            try:
                os.add_dll_directory(package_dir)
            except AttributeError:
                pass
        return


find_hr()
del find_hr
