import halcon as ha
import numpy as np
from typing import Sequence, Union

class ScaledShapeMatch:
    def __init__(self, **kwargs):
        """
        ScaledShapeMatch类用于创建和查找缩放形状模型。\n
        参数:\n
            num_levels (int, str): 模型的层数，默认为'auto'。
            angle_start (float): 起始角度，默认为-0.39。
            angle_extent (float): 角度范围，默认为0.79。
            angle_step (float, str): 角度步长，默认为'auto'。
            scale_min (float): 最小缩放比例，默认为0.9。
            scale_max (float): 最大缩放比例，默认为1.1。
            scale_step (float, str): 缩放步长，默认为'auto'。
            optimization (str): 优化方法，默认为'auto'。
            metric (str): 评估指标，默认为'use_polarity'。
            contrast (int, str): 对比度，默认为'auto'。
            min_contrast (int, str): 最小对比度，默认为'auto'。
            min_score (float): 最小匹配分数，默认为0.5。
            num_matches (int): 匹配数量，默认为1。
            max_overlap (float): 最大重叠度，默认为0.5。
            sub_pixel (str): 亚像素精度，默认为'least_squares'。
            match_num_levels (int): 匹配层数，默认为0。
            greediness (float): 贪婪度，默认为0.9。
            search_region (tuple): 搜索区域，默认为(0, 0, 0, 0)。
        """
        self.num_levels: Union[int, str] = kwargs.get('num_levels', 'auto')
        self.angle_start: float = kwargs.get('angle_start', -0.39)
        self.angle_extent: float = kwargs.get('angle_extent', 0.79)
        self.angle_step: Union[float, str] = kwargs.get('angle_step', 'auto')
        self.scale_min: float = kwargs.get('scale_min', 0.9)
        self.scale_max: float = kwargs.get('scale_max', 1.1)
        self.scale_step: Union[float, str] = kwargs.get('scale_step', 'auto')
        self.optimization: str = kwargs.get('optimization', 'auto')
        self.metric: str = kwargs.get('metric', 'use_polarity')
        self.contrast: Union[int, str] = kwargs.get('contrast', 'auto')
        self.min_contrast: Union[int, str] = kwargs.get('min_contrast', 'auto')
        
        self.min_score: float = kwargs.get('min_score', 0.5)
        self.num_matches: int = kwargs.get('num_matches', 1)
        self.max_overlap: float = kwargs.get('max_overlap', 0.5)
        self.sub_pixel: str = kwargs.get('sub_pixel', 'least_squares')
        self.match_num_levels: int = kwargs.get('match_num_levels', 0)
        self.greediness: float = kwargs.get('greediness', 0.9)
        
        self.search_region: tuple[Union[float, int]] = kwargs.get('search_region', (0, 0, 0, 0))
        
        self.model_id = None

    def __del__(self):
        self.clear_model()
        
    def create_model(self, template_image: Union[ha.HObject, np.ndarray, str]):
        try:
            if isinstance(template_image, np.ndarray):
                template_image = ha.himage_from_numpy_array(template_image)
            elif isinstance(template_image, str):
                template_image = ha.read_image(template_image)
            if not isinstance(template_image, ha.HObject):
                raise ValueError("template_image must be a Halcon image or a numpy array.")
            if self.model_id is not None:
                self.clear_model()
            self.model_id = ha.create_scaled_shape_model(
                template_image,
                self.num_levels,
                self.angle_start,
                self.angle_extent,
                self.angle_step,
                self.scale_min,
                self.scale_max,
                self.scale_step,
                self.optimization,
                self.metric,
                self.contrast,
                self.min_contrast
            )
            if self.model_id is None:
                raise ValueError("Failed to create scaled shape model.")
        except Exception as e:
            print(f"Error creating scaled shape model: {e}")
            raise

    def find_model(self, search_image: Union[ha.HObject, np.ndarray, str]) -> ha.Tuple[Sequence[float], Sequence[float], Sequence[float], Sequence[float], Sequence[float]]:
        if self.model_id is None:
            raise ValueError("Model has not been created. Call create_model() first.")
        try:
            if isinstance(search_image, np.ndarray):
                search_image = ha.himage_from_numpy_array(search_image)
            elif isinstance(search_image, str):
                search_image = ha.read_image(search_image)
            if not isinstance(search_image, ha.HObject):
                raise ValueError("template_image must be a Halcon image or a numpy array.")
            if self.search_region != (0, 0, 0, 0):
                roi = ha.gen_rectangle1(*self.search_region)
                search_image = ha.reduce_domain(search_image, roi)
            return ha.find_scaled_shape_model(
                search_image, 
                self.model_id, 
                self.angle_start, 
                self.angle_extent, 
                self.scale_min, 
                self.scale_max, 
                self.min_score, 
                self.num_matches,
                self.max_overlap,
                self.sub_pixel,
                self.match_num_levels,
                self.greediness
            )
        except Exception as e:
            print(f"Error finding scaled shape model: {e}")
            raise

    def clear_model(self):
        if self.model_id is not None:
            ha.clear_shape_model(self.model_id)
            self.model_id = None
    
    def write_model(self, file_name: str):
        if self.model_id is None:
            raise ValueError("Model has not been created. Call create_model() first.")
        try:
            ha.write_shape_model(self.model_id, file_name)
        except Exception as e:
            print(f"Error writing scaled shape model: {e}")
            raise
        
    def read_model(self, file_name: str):
        try:
            self.model_id = ha.read_shape_model(file_name)
            if self.model_id is None:
                raise ValueError("Failed to read scaled shape model.")
        except Exception as e:
            print(f"Error reading scaled shape model: {e}")
            raise
        
class NCCMath:
    def __init__(self, **kwargs):
        """
        NCCMath类用于创建和查找归一化互相关模型。\n
        参数:\n
            num_levels (int, str): 模型的层数，默认为'auto'。
            angle_start (float): 起始角度，默认为-0.39。
            angle_extent (float): 角度范围，默认为0.79。
            angle_step (float, str): 角度步长，默认为'auto'。
            metric (str): 评估指标，默认为'use_polarity'。
            min_score (float): 最小匹配分数，默认为0.5。
            num_matches (int): 匹配数量，默认为1。
            max_overlap (float): 最大重叠度，默认为0.5。
            sub_pixel (str): 亚像素精度，默认为'true'。
            match_num_levels (int): 匹配层数，默认为0。
            search_region (tuple): 搜索区域，默认为(0, 0, 0, 0)。
        """
        self.num_levels: Union[int, str] = kwargs.get('num_levels', 'auto')
        self.angle_start: float = kwargs.get('angle_start', -0.39)
        self.angle_extent: float = kwargs.get('angle_extent', 0.79)
        self.angle_step: Union[float, str] = kwargs.get('angle_step', 'auto')
        self.metric: str = kwargs.get('metric', 'use_polarity')
        
        self.min_score: float = kwargs.get('min_score', 0.5)
        self.num_matches: int = kwargs.get('num_matches', 1)
        self.max_overlap: float = kwargs.get('max_overlap', 0.5)
        self.sub_pixel: str = kwargs.get('sub_pixel', 'true')
        self.match_num_levels: int = kwargs.get('match_num_levels', 0)
        
        self.model_id = None
        self.search_region: tuple[Union[float, int]] = kwargs.get('search_region', (0, 0, 0, 0))
    
    def __del__(self):
        self.clear_model()
    
    def create_model(self, template_image: Union[ha.HObject, np.ndarray, str]):
        try:
            if isinstance(template_image, np.ndarray):
                template_image = ha.himage_from_numpy_array(template_image)
            elif isinstance(template_image, str):
                template_image = ha.read_image(template_image)
            if not isinstance(template_image, ha.HObject):
                raise ValueError("template_image must be a Halcon image or a numpy array.")
            if self.model_id is not None:
                self.clear_model()
            self.model_id = ha.create_ncc_model(
                template_image,
                self.num_levels,
                self.angle_start,
                self.angle_extent,
                self.angle_step,
                self.metric
            )
            if self.model_id is None:
                raise ValueError("Failed to create NCC model.")
        except Exception as e:
            print(f"Error creating NCC model: {e}")
            raise
    
    def find_model(self, search_image: Union[ha.HObject, np.ndarray, str]) -> ha.Tuple[Sequence[float], Sequence[float], Sequence[float], Sequence[float]]:
        if self.model_id is None:
            raise ValueError("Model has not been created. Call create_model() first.")
        try:
            if isinstance(search_image, np.ndarray):
                search_image = ha.himage_from_numpy_array(search_image)
            elif isinstance(search_image, str):
                search_image = ha.read_image(search_image)
            if not isinstance(search_image, ha.HObject):
                raise ValueError("template_image must be a Halcon image or a numpy array.")
            if self.search_region != (0, 0, 0, 0):
                roi = ha.gen_rectangle1(*self.search_region)
                search_image = ha.reduce_domain(search_image, roi)
            return ha.find_ncc_model(
                search_image,
                self.model_id,
                self.angle_start,
                self.angle_extent,
                self.min_score,
                self.num_matches,
                self.max_overlap,
                self.sub_pixel,
                self.match_num_levels
            )
        except Exception as e:
            print(f"Error finding NCC model: {e}")
            raise
    
    def clear_model(self):
        if self.model_id is not None:
            ha.clear_ncc_model(self.model_id)
            self.model_id = None
    
    def write_model(self, file_name: str):
        if self.model_id is None:
            raise ValueError("Model has not been created. Call create_model() first.")
        try:
            ha.write_ncc_model(self.model_id, file_name)
        except Exception as e:
            print(f"Error writing NCC model: {e}")
            raise
    
    def read_model(self, file_name: str):
        try:
            self.model_id = ha.read_ncc_model(file_name)
            if self.model_id is None:
                raise ValueError("Failed to read NCC model.")
        except Exception as e:
            print(f"Error reading NCC model: {e}")
            raise
    
class AnisoShapeMatch:
    def __init__(self, **kwargs):
        """
        AnisoShapeMatch类用于创建和查找各向异性形状模型。\n
        参数:\n
            num_levels (int, str): 模型的层数，默认为'auto'。
            angle_start (float): 起始角度，默认为-0.39。
            angle_extent (float): 角度范围，默认为0.79。
            angle_step (float, str): 角度步长，默认为'auto'。
            aniso_min (float): 最小各向异性比例，默认为0.9。
            aniso_max (float): 最大各向异性比例，默认为1.1。
            aniso_step (float, str): 各向异性步长，默认为'auto'。
            scale_min (float): 最小缩放比例，默认为0.9。
            scale_max (float): 最大缩放比例，默认为1.1。
            scale_step (float, str): 缩放步长，默认为'auto'。
            optimization (str): 优化方法，默认为'auto'。
            metric (str): 评估指标，默认为'use_polarity'。
            contrast (int, str): 对比度，默认为'auto'。
            min_contrast (int, str): 最小对比度，默认为'auto'。
            min_score (float): 最小匹配分数，默认为0.5。
            num_matches (int): 匹配数量，默认为1。
            max_overlap (float): 最大重叠度，默认为0.5。
            sub_pixel (str): 亚像素精度，默认为'least_squares'。
            match_num_levels (int): 匹配层数，默认为0。
            greediness (float): 贪婪度，默认为0.9。
            search_region (tuple): 搜索区域，默认为(0, 0, 0, 0)。
        """
        self.num_levels: Union[int, str] = kwargs.get('num_levels', 'auto')
        self.angle_start: float = kwargs.get('angle_start', -0.39)
        self.angle_extent: float = kwargs.get('angle_extent', 0.79)
        self.angle_step: Union[float, str] = kwargs.get('angle_step', 'auto')
        self.aniso_min: float = kwargs.get('aniso_min', 0.9)
        self.aniso_max: float = kwargs.get('aniso_max', 1.1)
        self.aniso_step: Union[float, str] = kwargs.get('aniso_step', 'auto')
        self.scale_min: float = kwargs.get('scale_min', 0.9)
        self.scale_max: float = kwargs.get('scale_max', 1.1)
        self.scale_step: Union[float, str] = kwargs.get('scale_step', 'auto')
        self.optimization: str = kwargs.get('optimization', 'auto')
        self.metric: str = kwargs.get('metric', 'use_polarity')
        self.contrast: Union[int, str] = kwargs.get('contrast', 'auto')
        self.min_contrast: Union[int, str] = kwargs.get('min_contrast', 'auto')

        self.min_score: float = kwargs.get('min_score', 0.5)
        self.num_matches: int = kwargs.get('num_matches', 1)
        self.max_overlap: float = kwargs.get('max_overlap', 0.5)
        self.sub_pixel: str = kwargs.get('sub_pixel', 'least_squares')
        self.match_num_levels: int = kwargs.get('match_num_levels', 0)
        self.greediness: float = kwargs.get('greediness', 0.9)

        self.search_region: tuple[Union[float, int]] = kwargs.get('search_region', (0, 0, 0, 0))

        self.model_id = None

    def __del__(self):
        self.clear_model()

    def create_model(self, template_image: Union[ha.HObject, np.ndarray, str]):
        try:
            if isinstance(template_image, np.ndarray):
                template_image = ha.himage_from_numpy_array(template_image)
            elif isinstance(template_image, str):
                template_image = ha.read_image(template_image)
            if not isinstance(template_image, ha.HObject):
                raise ValueError("template_image must be a Halcon image or a numpy array.")
            if self.model_id is not None:
                self.clear_model()
            self.model_id = ha.create_aniso_shape_model(
                template_image,
                self.num_levels,
                self.angle_start,
                self.angle_extent,
                self.angle_step,
                self.scale_min,
                self.scale_max,
                self.scale_step,
                self.aniso_min,
                self.aniso_max,
                self.aniso_step,
                self.optimization,
                self.metric,
                self.contrast,
                self.min_contrast
            )
            if self.model_id is None:
                raise ValueError("Failed to create anisotropic shape model.")
        except Exception as e:
            print(f"Error creating anisotropic shape model: {e}")
            raise

    def find_model(self, search_image: Union[ha.HObject, np.ndarray, str]) -> ha.Tuple[Sequence[float], Sequence[float], Sequence[float], Sequence[float], Sequence[float], Sequence[float]]:
        if self.model_id is None:
            raise ValueError("Model has not been created. Call create_model() first.")
        try:
            if isinstance(search_image, np.ndarray):
                search_image = ha.himage_from_numpy_array(search_image)
            elif isinstance(search_image, str):
                search_image = ha.read_image(search_image)
            if not isinstance(search_image, ha.HObject):
                raise ValueError("search_image must be a Halcon image or a numpy array.")
            if self.search_region != (0, 0, 0, 0):
                roi = ha.gen_rectangle1(*self.search_region)
                search_image = ha.reduce_domain(search_image, roi)
            return ha.find_aniso_shape_model(
                search_image,
                self.model_id,
                self.angle_start,
                self.angle_extent,
                self.scale_min,
                self.scale_max,
                self.aniso_min,
                self.aniso_max,
                self.min_score,
                self.num_matches,
                self.max_overlap,
                self.sub_pixel,
                self.match_num_levels,
                self.greediness
            )
        except Exception as e:
            print(f"Error finding anisotropic shape model: {e}")
            raise

    def clear_model(self):
        if self.model_id is not None:
            ha.clear_shape_model(self.model_id)
            self.model_id = None

    def write_model(self, file_name: str):
        if self.model_id is None:
            raise ValueError("Model has not been created. Call create_model() first.")
        try:
            ha.write_shape_model(self.model_id, file_name)
        except Exception as e:
            print(f"Error writing anisotropic shape model: {e}")
            raise

    def read_model(self, file_name: str):
        try:
            self.model_id = ha.read_shape_model(file_name)
            if self.model_id is None:
                raise ValueError("Failed to read anisotropic shape model.")
        except Exception as e:
            print(f"Error reading anisotropic shape model: {e}")
            raise
    
if __name__ == '__main__':
    image = ha.read_image(r"C:\Users\lzh\Desktop\saozi\IMG_20250320_144630.jpg")
    image = ha.rgb1_to_gray(image)
    rect = ha.gen_rectangle1(1102.2, 3492.18, 1698.97, 3952.85)
    circle = ha.gen_circle(1409.64, 3645.82, 85.9455)
    roi = ha.difference(rect, circle)
    template_image = ha.reduce_domain(image, roi)
    
    # template_image = ha.read_image(r"C:/Users/lzh/Desktop/saozi/1.jpg")
    # Example usage
    matcher = AnisoShapeMatch(min_score=0.5)
    matcher.create_model(template_image)
    # matcher.write_model(r"C:/Users/lzh/Desktop/saozi/model")
    results = matcher.find_model(image)
    print(results)