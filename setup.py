# -*- coding: utf-8 -*-
"""HRVisionSuite：HRVision 全家桶 meta 包（库依赖 + 例程）。

一键部署见 install_all.bat（安装全部子库 + 拷贝例程到工作目录）。
库：HRVision（框架）、HrFluentWidgets（UI 组件）、HrMotionController（运动控制）、
    PLCInterface（PLC 通信）。
"""
from setuptools import setup, find_packages

setup(
    name='HRVisionSuite',
    version='1.0.0',
    packages=find_packages(),
    author='HR',
    description='HRVision 全家桶：框架 + UI + 运动控制 + PLC 库与例程（一键部署）',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'pycryptodome',
        'numpy',
        'psutil',
        'wmi',
        'PySide6',
        'PySide6-Fluent-Widgets',
        'pandas',
    ],
    python_requires='>=3.12',
)
