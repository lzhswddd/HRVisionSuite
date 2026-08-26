
__path__ = __import__('pkgutil').extend_path(__path__, __name__)


def find_hr():
    import os, sys
    import sysconfig
    # 扩展文件名由 Python 决定，自动适配各平台：
    #   Windows: HRFlowController.cp312-win_amd64.pyd
    #   Linux:   HRFlowController.cp312-x86_64-linux-gnu.so
    #   macOS:   HRFlowController.cp312-darwin.so
    module_name = 'HRFlowController'
    ext_suffix = sysconfig.get_config_var('EXT_SUFFIX') or '.so'
    pyd_filename = module_name + ext_suffix

    package_dir = os.path.dirname(sys.executable)
    if not os.path.isfile(os.path.join(package_dir, pyd_filename)):
        path = os.environ['PATH']

        package_dir = os.path.dirname(__file__)
        if os.path.isfile(os.path.join(package_dir, pyd_filename)):
            dll_dir = os.path.join(package_dir, 'bin')
            path = dll_dir + os.pathsep + path
            os.environ['PATH'] = path
            if sys.platform.startswith('win'):
                os.add_dll_directory(dll_dir)
        else:
            for package_dir in path.split(os.pathsep):
                if os.path.isfile(os.path.join(package_dir, pyd_filename)):
                    break
            else:
                return
    if sys.platform.startswith('win'):
        try:
            os.add_dll_directory(package_dir)
        except AttributeError:
            pass

find_hr()
del find_hr

from .camera_parameter_tree import CameraParameterTree


def create_parameter_tree(camera) -> CameraParameterTree:
    """Create a CameraParameterTree bound to a Camera instance."""
    import json as _json

    def _parse_tree_result(result):
        value, error = result
        if error:
            return None
        if isinstance(value, str):
            return _json.loads(value)
        if hasattr(value, '__str__'):
            return _json.loads(str(value))
        return None

    def _parse_set_result(result):
        value, error = result
        err_str = str(error) if error else ""
        success = error == "" or error is None or str(error).strip() == ""
        if not success:
            return {"success": False, "actualValue": "", "errorMessage": err_str}
        actual_value = str(value) if value is not None else ""
        return {"success": True, "actualValue": actual_value, "errorMessage": ""}

    def _get_camera_serial(cam):
        try:
            cfg = cam.GetConfig()
            return cfg.get("SerialNumber", str(id(cam)))
        except Exception:
            return str(id(cam))

    return CameraParameterTree(
        tree_fetcher=lambda: _parse_tree_result(camera.GetParameterTree()),
        value_setter=lambda name, val: _parse_set_result(camera.SetValue(name, val)),
        serial_number=_get_camera_serial(camera),
    )


def __getattr__(name: str):
    """
    惰性暴露 Qt 图像转换工具（需 PySide6，仅在调用时加载）。
    支持：from HRVision import ndarray_to_qimage, qimage_to_ndarray
    """
    if name in ("ndarray_to_qimage", "qimage_to_ndarray"):
        from .Controller import ProcessQt
        return getattr(ProcessQt, name)
    raise AttributeError(f"module 'HRVision' has no attribute '{name}'")