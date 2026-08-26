from enum import Enum
from pathlib import Path
from typing import Union, Tuple, Sequence
import numpy as np
import cv2
from abc import ABC, abstractmethod
import json
from .ChessboardCalibrationTool import TransformerEx, CalibratorEx, AutoCalibratorEx

# import os, sys
# sys.path.append(r'D:\Python\frame\package\PyHRVision\HRVision\bin')
# os.add_dll_directory(r'D:\Python\frame\package\PyHRVision\HRVision\bin')
# from ChessboardCalibrationTool import TransformerEx, CalibratorEx, AutoCalibratorEx

def valid_point(point:Union[Tuple, np.ndarray], n=2) -> np.ndarray:
    """
    检查点是否有效
    :param point: 输入点坐标 (x, y)
    :return: 是否有效的布尔值和转换后的点坐标
    """
    if isinstance(point, tuple):
        point = np.array(point, dtype=np.float64).reshape(1, n)
    elif isinstance(point, np.ndarray):
        point = point
    else:
        raise ValueError("输入点必须是元组或numpy数组")
    if point.shape == (n,):
        point = point.reshape(1, n)
        
    if point.shape[1] != n:
        point = point[:, :n]
    
    return point
    
class Transformer(ABC):
    """
    Transformer接口类，提供正向和反向坐标转换功能。
    """
        
    @abstractmethod
    def forward(self, p:Union[Tuple, np.ndarray], *args, **kwargs) -> Union[Tuple, np.ndarray]:
        """
        正向坐标转换，将原始坐标 (x, y) 转换为目标坐标系中的坐标。
        
        :param p: 输入点坐标 (x, y)
        :param args: 其他参数
        :param kwargs: 其他参数
        :return: 转换后的 (x', y') 坐标
        """
        raise NotImplementedError("子类必须实现 forward 方法")

    @abstractmethod
    def inverse(self, p:Union[Tuple, np.ndarray], *args, **kwargs) -> Union[Tuple, np.ndarray]:
        """
        反向坐标转换，将目标坐标系中的坐标 (x, y) 转换回原始坐标系。
        
        :param p: 输入点坐标 (x, y)
        :param args: 其他参数
        :param kwargs: 其他参数
        :return: 转换回原始坐标系的 (x', y') 坐标
        """
        raise NotImplementedError("子类必须实现 inverse 方法")
    
    @abstractmethod
    def save(self, path:str):
        """
        保存变换器的参数到指定路径
        
        :param path: 保存路径
        """
        raise NotImplementedError("子类必须实现 save 方法")
    
    @abstractmethod
    def load(self, path:str):
        """
        从指定路径加载变换器的参数
        
        :param path: 加载路径
        """
        raise NotImplementedError("子类必须实现 load 方法")
    
class TransformerGroup(Transformer):
    def __init__(self, transformers:Sequence[Transformer] = None):
        """
        初始化变换器组
        :param transformers: 变换器列表
        """
        self.transformers_ = transformers if transformers is not None else []
    
    def forward(self, p, *args, **kwargs):
        """
        使用当前的变换器对输入点进行变换
        :param p: 输入点坐标 (x, y)
        :param args: 其他参数
        :param kwargs: 其他参数
        :return: 变换后的点坐标 (x', y')
        """
        point = valid_point(p)
        for transformer in self.transformers_:
            point = transformer.forward(point, *args, **kwargs)
        
        if isinstance(p, tuple):
            return tuple(point.flatten())
        else:
            return point
    
    def inverse(self, p, *args, **kwargs):
        """
        使用当前的逆变换器对输入点进行变换
        :param p: 输入点坐标 (x, y)
        :param args: 其他参数
        :param kwargs: 其他参数
        :return: 变换后的点坐标 (x', y')
        """
        point = valid_point(p)
        
        for transformer in reversed(self.transformers_):
            point = transformer.inverse(point, *args, **kwargs)
        
        if isinstance(p, tuple):
            return tuple(point.flatten())
        else:
            return point
        
    def save(self, path):
        """
        保存变换器的参数到指定路径
        :param path: 保存路径
        """
        for index in range(len(self.transformers_)):
            filePath = Path(path)
            fileName = filePath.stem + '_' + str(index) + filePath.suffix
            self.transformers_[index].save(str(Path(path).parent / fileName))
        
    def load(self, path):
        """
        从指定路径加载变换器的参数
        :param path: 加载路径
        """
        for index in range(len(self.transformers_)):
            filePath = Path(path)
            fileName = filePath.stem + '_' + str(index) + filePath.suffix
            self.transformers_[index].load(str(Path(path).parent / fileName))
    
class AffineModel(Transformer):
    def __init__(self, matrix:np.ndarray = None, inv_matrix:np.ndarray = None):
        self.matrix_ = matrix if matrix is not None else np.eye(3)  # 默认单位矩阵
        self.inv_matrix_ = inv_matrix if inv_matrix is not None else np.linalg.inv(self.matrix_)

    def move_origin(self, center:Tuple[float, float]):
        """
        移动坐标系原点
        :param center: 新的坐标系原点 (x, y)
        """
        if len(center) != 2:
            raise ValueError("输入坐标必须是长度为2的元组或列表")
        self.matrix_[0, 2] = center[0]
        self.matrix_[1, 2] = center[1]
        self.inv_matrix_[0, 2] = -center[0]
        self.inv_matrix_[1, 2] = -center[1]
    
    def move(self, dx:float, dy:float):
        """
        移动坐标系
        :param dx: x 方向的移动距离
        :param dy: y 方向的移动距离
        """
        if self.matrix_ is None:
            raise ValueError("变换矩阵未初始化")
        
        self.matrix_[0, 2] += dx
        self.matrix_[1, 2] += dy
        self.inv_matrix_[0, 2] -= dx
        self.inv_matrix_[1, 2] -= dy

    def origin(self) -> Tuple[float, float]:
        """
        获取当前坐标系原点
        :return: 当前坐标系原点 (x, y)
        """
        return self.matrix_[0, 2], self.matrix_[1, 2]

    def forward(self, p:Union[Tuple, np.ndarray], *args, **kwargs) -> Union[Tuple, np.ndarray]:
        """
        使用当前的变换矩阵对输入点进行变换
        :param p: 输入点坐标 (x, y)
        :return: 变换后的点坐标 (x', y')
        """
        point = valid_point(p)
        
        # 将点转换为齐次坐标
        p_homogeneous = np.hstack((point, np.ones((point.shape[0], 1), dtype=np.float64)))
        transformed_point = (p_homogeneous @ self.matrix_.T)[:, :2]  # 只取前两列
        
        if isinstance(p, tuple):
            return tuple(transformed_point.flatten())
        else:
            return transformed_point
    
    def inverse(self, p:Union[Tuple, np.ndarray], *args, **kwargs) -> Union[Tuple, np.ndarray]:
        """
        使用当前的逆变换矩阵对输入点进行变换
        :param p: 输入点坐标 (x, y)
        :return: 变换后的点坐标 (x', y')
        """
        point = valid_point(p)
            
        # 将点转换为齐次坐标
        p_homogeneous = np.hstack((point, np.ones((point.shape[0], 1), dtype=np.float64)))
        transformed_point = (p_homogeneous @ self.inv_matrix_.T)[:, :2]  # 只取前两列
        
        if isinstance(p, tuple):
            return tuple(transformed_point.flatten())
        else:
            return transformed_point
     
    def save(self, path:str):
        """
        保存变换器的参数到指定路径
        :param path: 保存路径
        """
        matrix = []
        inv_matrix = []
        for i in range(3):
            matrix.append(self.matrix_[i].tolist())
            inv_matrix.append(self.inv_matrix_[i].tolist())
        
        data = {
            'matrix': matrix,
            'inv_matrix': inv_matrix
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def load(self, path:str):
        """
        从指定路径加载变换器的参数
        :param path: 加载路径
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data is not None:
            self.matrix_ = np.array(data['matrix'], dtype=np.float64)
            self.inv_matrix_ = np.array(data['inv_matrix'], dtype=np.float64)

    def __call__(self, p:np.ndarray):
        """
        使用当前的变换矩阵对输入点进行变换
        :param p: 输入点坐标 (x, y)
        :return: 变换后的点坐标 (x', y')
        """
        return self.forward(p)

class RotationModel(Transformer):
    def __init__(self, center:Tuple[float, float] = (0, 0)):
        self.center_ : Tuple[float, float] = center  # 圆心坐标
    
    def move_center(self, center:Tuple[float, float]):
        """
        移动坐标系中心
        :param center: 新的坐标系中心 (x, y)
        """
        if len(center) != 2:
            raise ValueError("输入坐标必须是长度为2的元组或列表")
        
        self.center_ = center
    
    def move(self, dx:float, dy:float):
        """
        移动坐标系
        :param dx: x 方向的移动距离
        :param dy: y 方向的移动距离
        """
        if self.center_ is None:
            raise ValueError("变换矩阵未初始化")
        
        self.center_ = (self.center_[0] + dx, self.center_[1] + dy)

    def forward(self, p:Union[Tuple, np.ndarray], *args, **kwargs) -> Union[Tuple, np.ndarray]:
        """
        使用当前的变换矩阵对输入点进行变换
        :param p: 输入点坐标 (x, y)
        :param args: 旋转角度（弧度）
        :return: 变换后的点坐标 (x', y')
        """
        point = valid_point(p)
        
        if 'angle' in kwargs:
            angle = kwargs['angle']
            theta = np.deg2rad(angle)  # 将角度转换为弧度
        elif 'theta' in kwargs:
            theta = kwargs['theta']
        else:
            theta = 0
            
        # 计算点绕圆心旋转 theta 后的坐标
        x, y = point[:, 0] - self.center_[0], point[:, 1] - self.center_[1]  # 平移到圆心为原点
        x_rot = x * np.cos(theta) - y * np.sin(theta)  # 旋转后的 x 坐标
        y_rot = x * np.sin(theta) + y * np.cos(theta)  # 旋转后的 y 坐标
        transformed_point = np.column_stack((x_rot + self.center_[0], y_rot + self.center_[1]))  # 平移回原位置
        
        if isinstance(p, tuple):
            return tuple(transformed_point.flatten())
        else:
            return transformed_point
    
    def inverse(self, p:Union[Tuple, np.ndarray], *args, **kwargs) -> Union[Tuple, np.ndarray]:
        """
        使用当前的逆变换矩阵对输入点进行变换
        :param p: 输入点坐标 (x, y)
        :param args: 旋转角度（弧度）
        :return: 变换后的点坐标 (x', y')
        """
        point = valid_point(p)
        
        if 'angle' in kwargs:
            angle = kwargs['angle']
            theta = np.deg2rad(angle)  # 将角度转换为弧度
        elif 'theta' in kwargs:
            theta = kwargs['theta']
        else:
            theta = 0
            
        theta = -theta  # 逆变换时角度取反
            
        # 计算点绕圆心旋转 theta 后的坐标
        x, y = point[:, 0] - self.center_[0], point[:, 1] - self.center_[1]
        # 平移到圆心为原点
        x_rot = x * np.cos(theta) - y * np.sin(theta)  # 旋转后的 x 坐标
        y_rot = x * np.sin(theta) + y * np.cos(theta)  # 旋转后的 y 坐标
        transformed_point = np.column_stack((x_rot + self.center_[0], y_rot + self.center_[1]))  # 平移回原位置
        
        if isinstance(p, tuple):
            return tuple(transformed_point.flatten())
        else:
            return transformed_point

    def save(self, path:str):
        """
        保存变换器的参数到指定路径
        :param path: 保存路径
        """
        data = {
            'center': self.center_
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        
    def load(self, path:str):
        """
        从指定路径加载变换器的参数
        :param path: 加载路径
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data is not None:
            self.center_ = tuple(data['center'])

class CameraModel(Transformer):
    def __init__(self, camera_matrix:np.ndarray, dist_coeffs:np.ndarray, affineMatrix:np.ndarray, ignore_depth_output:bool = False):
        self.transformer_ = TransformerEx(camera_matrix, dist_coeffs, affineMatrix)  # 创建变换器对象
        self.ignore_depth_ = ignore_depth_output  # 是否忽略深度参数
        
    def __init__(self, camera_matrix:np.ndarray, camera_matrix_inv:np.ndarray, dist_coeffs:np.ndarray, affineMatrix:np.ndarray, affineMatrix_inv:np.ndarray, ignore_depth_output:bool = False):
        self.transformer_ = TransformerEx(camera_matrix, camera_matrix_inv, dist_coeffs, affineMatrix, affineMatrix_inv)
        self.ignore_depth_ = ignore_depth_output  # 是否忽略深度参数

    def __init__(self, transformer:TransformerEx = TransformerEx(), ignore_depth_output:bool = False):
        self.transformer_ = transformer
        self.ignore_depth_ = ignore_depth_output  # 是否忽略深度参数
        
    def set_ignore_depth(self, ignore:bool):
        """
        设置是否忽略深度输出
        :param ignore: 是否忽略深度输出
        """
        self.ignore_depth_ = ignore
        
    def ignore_depth(self) -> bool:
        """
        获取是否忽略深度输出
        :return: 是否忽略深度输出
        """
        return self.ignore_depth_

    def forward(self, p:Union[Tuple, np.ndarray], *args, **kwargs) -> Union[Tuple, np.ndarray]:
        # 实现相机模型的正向变换逻辑
        # 例如使用 OpenCV 的 undistortPoints 函数
        point = valid_point(p)
        depth = kwargs.get('depth', 0)  # 获取深度参数，默认为0
        if isinstance(depth, np.ndarray):
            if len(depth) != point.shape[0]:
                raise ValueError("深度数组的长度与点坐标的长度不匹配")
        elif isinstance(depth, (float, int)):
            pass
        else:
            raise ValueError("深度参数必须是 float 或 numpy 数组")
        transformed_point = self.transformer_.getWorldCoordinate(point, depth)
        if self.ignore_depth_:
            transformed_point = transformed_point[:, :2]
        if isinstance(p, tuple):
            return tuple(transformed_point.flatten())
        else:
            return transformed_point

    def inverse(self, p:Union[Tuple, np.ndarray], *args, **kwargs) -> Union[Tuple, np.ndarray]:
        # 实现相机模型的反向变换逻辑
        if self.ignore_depth_:
            point = valid_point(p, 2)
        else:
            point = valid_point(p, 3)
        
        transformed_point = self.transformer_.getPixelCoordinate(point)
        
        if isinstance(p, tuple):
            return tuple(transformed_point.flatten())
        else:
            return transformed_point

    def save(self, path:str):
        # 保存变换器的参数到指定路径
        self.transformer_.save(path)
    
    def load(self, path:str):
        # 从指定路径加载变换器的参数
        self.transformer_.load(path)

class XYCalib:
    def __init__(self):
        """初始化标定器，存储源点和目标点"""
        self.src_points_ = []  # 存储原始坐标系点（例如图像坐标）
        self.dst_points_ = []  # 存储目标坐标系点（例如物理坐标）
        self.transformer_ = AffineModel()  # 创建变换器对象
    
    def add_point(self, src, dst):
        """
        添加一组对应点
        :param src: 源点坐标 (x, y)
        :param dst: 目标点坐标 (x', y')
        """
        if len(src) != 2 or len(dst) != 2:
            raise ValueError("输入坐标必须是长度为2的元组或列表")
        self.src_points_.append(src)
        self.dst_points_.append(dst)
    
    def set_points(self, src, dst):
        self.src_points_ = src
        self.dst_points_ = dst
    
    def reset(self):
        """重置所有存储的点"""
        self.src_points_ = []
        self.dst_points_ = []
        self.transformer_ = AffineModel()  # 重置变换器对象
       
    def compute_transform(self):
        """
        计算3x3投影变换矩阵
        :return: 3x3变换矩阵（numpy数组）
        """
        if len(self.src_points_) < 3 or len(self.dst_points_) < 3:
            raise ValueError("需要至少3组对应点进行计算")
        
        src_points_np = np.array(self.src_points_, dtype=np.float64)
        dst_points_np = np.array(self.dst_points_, dtype=np.float64)
        
        try:
            # 估算仿射变换矩阵
            matrix, inliers = cv2.estimateAffine2D(src_points_np, dst_points_np)
            if inliers is not None and np.sum(inliers) < 3:
                raise ValueError("有效的内点数量不足以计算变换矩阵")
            matrix = np.vstack((matrix, [0, 0, 1]))  # 将2x3矩阵转换为3x3矩阵
            inv_matrix = np.linalg.inv(matrix)
            
            self.transformer_ = AffineModel(matrix, inv_matrix)
        except cv2.error as e:
            raise RuntimeError(f"计算仿射变换矩阵时发生错误: {e}")

    def compute_compensate(self, src_point:Union[Tuple[float, float], np.ndarray], dst_point:Union[Tuple[float, float], np.ndarray]) -> Tuple:
        """
        计算补偿值
        :param src_point: 源点坐标 (x, y)
        :param dst_point: 目标点坐标 (x', y')
        :return: 补偿值 (dx, dy)
        """
        
        src_points = valid_point(src_point)
        dst_points = valid_point(dst_point)
        
        transformer_src_points = self.transformer_.forward(src_points)
        transformer_dst_points = self.transformer_.forward(dst_points)
        
        diff = transformer_dst_points - transformer_src_points
        
        return diff[:, 0], diff[:, 1]  # 返回补偿值 (dx, dy)
 
    def transformer(self) -> AffineModel:
        """
        返回当前的变换器
        :return: 当前的变换器对象
        """
        return self.transformer_

class RotCalib:
    def __init__(self):
        """初始化旋转标定器"""
        self.points_ = []  # 存储坐标系点
        self.transformer_ = RotationModel()  # 创建变换器对象
        
    def add_point(self, points):
        """
        添加一组对应点
        :param points: 源点坐标 (x, y)
        """
        if len(points) != 2:
            raise ValueError("输入坐标必须是长度为2的元组或列表")
        self.points_.append(points)
    
    def set_points(self, points):
        self.points_ = points
    
    def reset(self):
        """重置所有存储的点"""
        self.points_ = []
        self.transformer_ = RotationModel()
    
    def compute_transform(self):
        """
        计算旋转变换矩阵
        :return: 旋转变换矩阵（numpy数组）
        """
        if len(self.points_) > 3:
            raise ValueError("需要至少3组对应点进行计算")
        
        points_np = np.array(self.points_, dtype=np.float64)
        
        try:
            # 使用最小二乘法拟合圆
            A = np.hstack((2 * points_np, np.ones((points_np.shape[0], 1))))
            b = np.sum(points_np**2, axis=1)
            x = np.linalg.lstsq(A, b, rcond=None)[0]
            center = (x[0], x[1])  # 圆心坐标
            self.transformer_ = RotationModel(center)
        except Exception as e:
            raise RuntimeError(f"计算旋转变换矩阵时发生错误: {e}")

    def compute_compensate(self,point:Union[Tuple[float, float], np.ndarray], r:float) -> Tuple:
        """
        计算补偿值
        :param point : 源点坐标 (x, y)
        :param r: 旋转角度（弧度）
        :return: 补偿值 (dx, dy)
        """
        points = valid_point(point)
        
        transformer_points = self.transformer_.forward(points, angle=r)
        
        diff = transformer_points - points
        
        return diff[:, 0], diff[:, 1]

    def transformer(self) -> RotationModel:
        """
        返回当前的变换器
        :return: 当前的变换器对象
        """
        return self.transformer_

class XYRotCalib:
    def __init__(self):
        """初始化XY旋转标定器"""
        self.src_rotation_points_ = []  # 存储源点坐标
        self.dst_rotation_points_ = []  # 存储目标点坐标
        self.xy_calib_ = XYCalib()  # 创建XY标定器对象
        self.rot_calib_ = RotCalib()  # 创建旋转标定器对象
        
    def add_affine_point(self, src, dst):
        """
        添加一组对应点
        :param src: 源点坐标 (x, y)
        :param dst: 目标点坐标 (x', y')
        """
        self.xy_calib_.add_point(src, dst)
        
    def set_affine_points(self, src, dst):
        self.xy_calib_.set_points(src, dst)
    
    def add_rotation_point(self, src, dst):
        """
        添加一组对应点
        :param src: 源点坐标 (x, y)
        :param dst: 目标点坐标 (x', y')
        """
        self.src_rotation_points_.append(src)
        self.dst_rotation_points_.append(dst)
        
    def set_rotation_points(self, src, dst):
        self.src_rotation_points_ = src
        self.dst_rotation_points_ = dst
    
    def reset(self):
        """重置所有存储的点"""
        self.src_rotation_points_ = []
        self.dst_rotation_points_ = []
        self.xy_calib_ = XYCalib()  # 重置仿射变换器对象
        self.rot_calib_ = RotCalib()  # 重置旋转变换器对象
        
    def compute_transform(self):
        """
        计算仿射变换矩阵和旋转变换矩阵
        """
        self.xy_calib_.compute_transform()  # 计算仿射变换矩阵
        
        src_points_np = np.array(self.src_rotation_points_, dtype=np.float64)
        dst_points_np = np.array(self.dst_rotation_points_, dtype=np.float64)
        
        # orgin = self.xy_calib_.transformer().origin()  # 获取当前坐标系原点
        
        target_points_np = self.xy_calib_.transformer().forward(src_points_np)
        points_np = target_points_np - dst_points_np  # 计算旋转点
        
        self.rot_calib_.set_points(points_np)
        self.rot_calib_.compute_transform()  # 计算旋转变换矩阵
        
    def compute_compensate(self, src_vector:Union[Tuple[float, float, float], np.ndarray], dst_vector:Union[Tuple[float, float, float], np.ndarray]) -> Tuple:
        """
        计算补偿值
        :param src_vector: 源点坐标 (x, y, r)
        :param dst_vector: 目标点坐标 (x', y', r')
        :return: 补偿值 (dx, dy, dr)
        """
        src_point = valid_point(src_vector, 3)
        dst_point = valid_point(dst_vector, 3)
        diif_r = dst_point[:, 2] - src_point[:, 2]
        target_point = self.xy_calib_.transformer().forward(src_point[:, :2])  # 获取目标点坐标
        rot_x, rot_y = self.rot_calib_.compute_compensate(target_point[:, :2], diif_r)
        rot_point = valid_point((rot_x, rot_y))
        diff_xy = self.xy_calib_.compute_compensate(rot_point[:, :2], dst_point[:, :2])

        return diff_xy[0], diff_xy[1], diif_r
        
    def transform(self) -> TransformerGroup:
        """
        返回当前的变换器
        :return: 当前的变换器对象
        """
        return TransformerGroup([self.xy_calib_.transformer(), self.rot_calib_.transformer()])  # 返回变换器组

class ZhangCalib:
    def __init__(self, square_size:Tuple[float, float] = (1.0, 1.0), border_rank:Tuple[int, int] = (1, 1), is_auto:bool = False):
        """
        初始化棋盘格标定器
        :param square_size: 每个方格的大小（单位：毫米）
        :param border_rank: 棋盘格角点行列
        :param is_auto: 是否自动标定 (True) 或手动标定 (False), 自动标定不需要提供棋盘格角点行列
        """
        self.device_ = AutoCalibratorEx(square_size) if is_auto else CalibratorEx(border_rank, square_size)
        self.transformer_:Transformer = CameraModel()  # 创建变换器对象
        if is_auto:
            self.device_.registerCallback(lambda x: print(f"自动标定信息: {x}"))
    
    def add_image(self, image):
        """
        添加棋盘格图像
        :param image: 棋盘格图像
        """
        self.device_.appendImage(image)
    
    def set_images(self, images):
        """
        设置棋盘格图像
        :param images: 棋盘格图像列表
        """
        self.device_.setImages(images)
    
    def clear_image(self):
        """清除图像数据"""
        self.device_.clearImage()

    def reset(self):
        """重置所有存储的数据"""
        self.device_.clear()
        self.transformer_ = CameraModel()
    
    def compute_transform(self):
        """
        计算棋盘格的变换矩阵
        """
        ret = self.device_.calibrate()
        if ret:
            self.transformer_ = CameraModel(self.device_.getTransformer())
        return ret

    def get_border_rank(self) -> Sequence[Tuple[int, int]]:
        """
        获取棋盘格角点行列
        :return: 棋盘格角点行列
        """
        return self.device_.getChessBoardRank()

    def get_image_points(self) -> Sequence[np.ndarray]:
        """
        获取标定的图像点
        :return: 标定的图像点列表
        """
        return self.device_.getImagePoints()
    
    def get_world_points(self) -> Sequence[np.ndarray]:
        """
        获取标定的世界点
        :return: 标定的世界点列表
        """
        return self.device_.getWorldPoints()
    
    def get_corner_image(self, index:int = 0) -> np.ndarray:
        """
        获取角点图像
        :param index: 图像索引
        :return: 角点图像
        """
        return self.device_.getCornerImage(index)

    def transformer(self) -> CameraModel:
        """
        返回当前的变换器
        :param index: 变换器索引
        :return: 当前的变换器对象
        """
        return self.transformer_
    
    def compute_compensate(self, src_point:Union[Tuple[float, float], np.ndarray], dst_point:Union[Tuple[float, float], np.ndarray]) -> Tuple:
        """
        计算补偿值
        :param src_point: 源点坐标 (x, y)
        :param dst_point: 目标点坐标 (x', y')
        :return: 补偿值 (dx, dy)
        """
        
        src_points = valid_point(src_point)
        dst_points = valid_point(dst_point)
        
        transformer_src_points = self.transformer_.forward(src_points)
        transformer_dst_points = self.transformer_.forward(dst_points)
        
        diff = transformer_dst_points - transformer_src_points
        
        return diff[:, 0], diff[:, 1]

class ZhangHRCalib(ZhangCalib):
    def __init__(self, square_size:Tuple[float, float] = (1.0, 1.0), border_rank:Tuple[int, int] = (1, 1), is_auto:bool = False):
        """
        初始化棋盘格标定器
        :param rows: 棋盘格行数
        :param cols: 棋盘格列数
        :param square_size: 每个方格的大小（单位：毫米）
        """
        super().__init__(square_size, border_rank, is_auto)
        
        self.handeye_origin_ = np.array((0, 0))       # 当前坐标系原点
        self.handeye_x_direction_ = np.array((1, 0))  # 当前坐标系x轴方向
        self.handeye_y_direction_ = np.array((0, 1))  # 当前坐标系y轴方向
        self.handeye_ = XYCalib()  # 创建手眼标定器对象
        
    def set_handeye_origin(self, origin:Tuple[float, float]):
        """
        设置手眼标定器的原点
        :param origin: 原点坐标 (x, y)
        """
        if len(origin) != 2:
            raise ValueError("输入坐标必须是长度为2的元组或列表")
        
        self.handeye_origin_ = np.array(origin)
    
    def set_handeye_x_direction(self, x_direction:Tuple[float, float]):
        """
        设置手眼标定器的x轴方向
        :param x_direction: x轴方向坐标 (x, y)
        """
        if len(x_direction) != 2:
            raise ValueError("输入坐标必须是长度为2的元组或列表")
        
        self.handeye_x_direction_ = np.array(x_direction)
        
    def set_handeye_y_direction(self, y_direction:Tuple[float, float]):
        """
        设置手眼标定器的y轴方向
        :param y_direction: y轴方向坐标 (x, y)
        """
        if len(y_direction) != 2:
            raise ValueError("输入坐标必须是长度为2的元组或列表")
        
        self.handeye_y_direction_ = np.array(y_direction)
        
    def reset(self):
        """重置所有存储的数据"""
        self.handeye_origin_ = np.array((0, 0))       # 当前坐标系原点
        self.handeye_x_direction_ = np.array((1, 0))  # 当前坐标系x轴方向
        self.handeye_y_direction_ = np.array((0, 1))  # 当前坐标系y轴方向
        self.handeye_.reset()
        super().reset()
        
    def compute_transform(self):
        super().compute_transform()
        x_vector = self.handeye_x_direction_ - self.handeye_origin_
        y_vector = self.handeye_y_direction_ - self.handeye_origin_
        x_unit_vector = x_vector / np.linalg.norm(x_vector)
        y_unit_vector = y_vector / np.linalg.norm(y_vector)
        x_unit_point = self.handeye_origin_ + x_unit_vector
        y_unit_point = self.handeye_origin_ + y_unit_vector
        src_points = [(0, 0), (1, 0), (0, 1)]  # 原点和x、y轴方向上的单位向量
        dst_points = [
            self.handeye_origin_,
            x_unit_point,
            y_unit_point
        ]
        self.handeye_.set_points(src_points, dst_points)
        self.handeye_.compute_transform()
        
    def compute_compensate(self, src_point:Union[Tuple[float, float], np.ndarray], dst_point:Union[Tuple[float, float], np.ndarray]) -> Tuple:
        """
        计算补偿值
        :param src_x: 源点x坐标
        :param src_y: 源点y坐标
        :param dst_x: 目标点x坐标
        :param dst_y: 目标点y坐标
        :return: 补偿值 (dx, dy)
        """
        dx, dy = super().compute_compensate(src_point, dst_point)
        diff = valid_point((dx, dy))
        temp_point = np.zeros_like(diff)
        return self.handeye_.compute_compensate(temp_point, diff)

    def transform(self) -> TransformerGroup:
        """
        返回当前的变换器
        :return: 当前的变换器对象
        """
        return TransformerGroup([super().transformer(), self.handeye_.transformer()])
        
# 示例用法
if __name__ == "__main__":
    # 创建标定器
    calibrator = XYCalib()
    # 假设的测试数据（实际使用时替换为真实数据）
    test_src = [(i, j) for i in range(3) for j in range(3)]  # 3x3网格点
    # test_dst = [(y*100, x*100) for x, y in test_src]  # 简单仿射变换示例
    test_dst = []
    for r in range(-int(3/2), int(3/2)+1, 1):
        for c in range(-int(3/2), int(3/2)+1, 1):
            test_dst.append((c, r))  # 简单仿射变换示例
    # 添加对应点
    for s, d in zip(test_src, test_dst):
        calibrator.add_point(s, d)
    
    # 计算变换矩阵
    try:
        calibrator.compute_transform()
        calibrator.transformer().save("transformer.json")
        calibrator.transformer().load("transformer.json")
        
        # raise ValueError("测试结束")
        
        # test_src_array = np.array(test_src, dtype=np.float64)
        # test_dst_array = np.array(test_dst, dtype=np.float64)
        
        # # target = calibrator.transformer().forward(test_src_array)
        # # print(target)
        # # print(test_dst)
        # # target = calibrator.transformer().inverse(test_src_array)
        transformer = RotationModel((100, 100))
        p0 = (0, 0)
        p1 = transformer.forward(p0, theta=-np.pi/2)
        p2 = transformer.forward(p0, theta=np.pi/2)
        print("p0:", p0)
        print("p1:", p1)
        print("p2:", p2)
        
        rot_calib = RotCalib()
        rot_calib.set_points([p0, p1, p2])
        rot_calib.compute_transform()
        print("旋转中心：", rot_calib.transformer_.center_)
        
        rot_calib.transformer().save("transformer_rot.json")
        rot_calib.transformer().load("transformer_rot.json")
        
        # raise ValueError("测试结束")
        
        # # print("变换矩阵：", calibrator.transformer_.matrix_)
        # # center = calibrator.transformer_.matrix_[0:2, 2]
        # # print(calibrator.transformer().inverse(center.T))
        # # print(calibrator.transformer().inverse((0, 0)))
        
        # # dx, dy = calibrator.compute_compensate(
        # #     test_dst_array[:, 0], test_dst_array[:, 1],
        # #     test_dst_array[:, 0]+2, test_dst_array[:, 1])
        
        # # print("补偿值：", dx, dy)
        xyr = XYRotCalib()
        
        xyr.set_affine_points(test_src, test_dst)
        orgin = calibrator.transformer().origin()
        xyr.add_rotation_point(p0, orgin)
        xyr.add_rotation_point(p1, orgin)
        xyr.add_rotation_point(p2, orgin)
        
        xyr.compute_transform()
        
        # print("仿射变换矩阵：", xyr.xy_calib_.transformer_.matrix_)
        # print("旋转变换中心：", xyr.rot_calib_.transformer_.center_)
        
        print("测试", xyr.transform().forward((0, 0), angle=45))
        
        # raise ValueError("测试结束")

        
        chessboard = ZhangCalib(square_size=(20, 20), is_auto=True)
        imagepath = r'C:\Users\lzh\Desktop\标定图\02.png'
        chessboard.add_image(imagepath)
        chessboard.compute_transform()
        
        pp1 = chessboard.transformer_.inverse((0, 0, 0))
        pp2 = chessboard.transformer_.inverse((20, 0, 0))
        
        print(chessboard.compute_compensate(pp1, pp2))
        # for pp in chessboard.device_.getImagePoints():
        #     for p in pp:
        #         print(p)
        #         print(chessboard.transformer_.forward(p))
        
        # print(chessboard.transformer_.inverse((0, 0, 0)))
        
        # raise ValueError("测试异常")
        
        zhe = ZhangHRCalib(square_size=(20, 20), is_auto=True)
        zhe.add_image(imagepath)
        zhe.set_handeye_origin(p0)
        zhe.set_handeye_x_direction(p1)
        zhe.set_handeye_y_direction(p2)
        zhe.compute_transform()
        print(zhe.transform().forward((0, 0)))
        print(zhe.compute_compensate(pp1, pp2))
        
    except ValueError as e:
        print(f"错误：{e}")
