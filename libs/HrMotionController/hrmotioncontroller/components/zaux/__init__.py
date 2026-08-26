#!/usr/bin/python
# coding:utf-8


def find_zaux():
    import os, sys
        
    module_name = 'zauxdll'
    # 生成 .pyd 文件名
    pyd_filename = f"{module_name}.dll"
    
    package_dir = os.path.dirname(sys.executable)
    if not os.path.isfile(os.path.join(package_dir, pyd_filename)):
        path = os.environ['PATH']
        
        package_dir = os.path.dirname(__file__)
        if os.path.isfile(os.path.join(package_dir, pyd_filename)):
            path = package_dir + ';' + path
            os.environ['PATH'] = path
        else:
            for package_dir in path.split(';'):
                if os.path.isfile(os.path.join(package_dir, pyd_filename)):
                    break
            else:
                return
    try:
        sys.path.append(package_dir)
        os.add_dll_directory(package_dir)
    except AttributeError:
        pass
    
find_zaux()
del find_zaux

from .hrZmotion import ZauxAxis, ZauxMotion, ZauxEtherCatAxis, ZauxEtherCatMotion 