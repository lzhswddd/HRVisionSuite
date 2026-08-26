import halcon as ha
import numpy as np
from typing import Sequence, Union, Optional 

class MetrologyObjectParam:
    def __init__(self, shape: str, **kwargs):
        self.shape = shape
        self.shape_param = kwargs.get('shape_param', [])
        self.measure_length_1 = kwargs.get('measure_length_1', 20)
        self.measure_length_2 = kwargs.get('measure_length_2', 5)
        self.measure_sigma = kwargs.get('measure_sigma', 1)
        self.measure_threshold = kwargs.get('measure_threshold', 30)
        self.gen_param_name = kwargs.get('gen_param_name', [])
        self.gen_param_value = kwargs.get('gen_param_value', [])

class MetrologyRectangleParam(MetrologyObjectParam):
    def __init__(self, 
                 row:Union[int, float],  
                 column:Union[int, float], 
                 phi:Union[int, float], 
                 length1:Union[int, float], 
                 length2:Union[int, float], 
                 **kwargs):
        kwargs['shape_param'] = [row, column, phi, length1, length2]
        super().__init__('rectangle2', **kwargs)
        
class MetrologyCircleParam(MetrologyObjectParam):
    def __init__(self, 
                 row:Union[int, float], 
                 column:Union[int, float], 
                 radius:Union[int, float], 
                 **kwargs):
        kwargs['shape_param'] = [row, column, radius]
        super().__init__('circle', **kwargs)
        
class MetrologyEllipseParam(MetrologyObjectParam):
    def __init__(self, 
                 row:Union[int, float], 
                 column:Union[int, float], 
                 phi:Union[int, float], 
                 radius1:Union[int, float], 
                 radius2:Union[int, float], 
                 **kwargs):
        kwargs['shape_param'] = [row, column, phi, radius1, radius2]
        super().__init__('ellipse', **kwargs)
        
class MetrologyLineParam(MetrologyObjectParam):
    def __init__(self, 
                 row1:Union[int, float], 
                 column1:Union[int, float], 
                 row2:Union[int, float], 
                 column2:Union[int, float], 
                 **kwargs):
        kwargs['shape_param'] = [row1, column1, row2, column2]
        super().__init__('line', **kwargs)
       
class MetrologyResult:
    def __init__(self, handle: int, object: int, **kwargs):
        instance = kwargs.get('instance', 'all')
        gen_param_name = kwargs.get('gen_param_name', 'result_type')
        gen_param_value = kwargs.get('gen_param_value', 'all_param')
        
        self.result = ha.get_metrology_object_result(handle, object, instance, gen_param_name, gen_param_value)
        have_contour = kwargs.get('have_contour', False)
        if have_contour:
            resolution = kwargs.get('resolution', 1.5)
            self.contour = ha.get_metrology_object_result_contour (handle, object, instance, resolution)
        else:
            self.contour = None
        have_measure = kwargs.get('have_measure', False)
        if have_measure:
            transition = kwargs.get('transition', 'all')
            self.measures, self.measure_rows, self.measure_columns = ha.get_metrology_object_measures (handle, object, transition)
        else:
            self.measures = None
            self.measure_rows = None
            self.measure_columns = None
            
    def get(self, index: int = 0) -> tuple:
        return None
        
class MetrologyRectangleResult(MetrologyResult):
    def __init__(self, handle: int, object: int, **kwargs):
        super().__init__(handle, object, **kwargs)
        self.length = int(len(self.result) / 5)
        if self.length == 0:
            self.row, self.column, self.phi, self.length1, self.length2 = (None,) * 5
        else:
            indexs = [i * 5 for i in range(self.length)]
            self.row = [self.result[i] for i in indexs]
            self.column = [self.result[i + 1] for i in indexs]
            self.phi = [self.result[i + 2] for i in indexs]
            self.length1 = [self.result[i + 3] for i in indexs]
            self.length2 = [self.result[i + 4] for i in indexs]
        
    def get(self, index: int = 0) -> tuple[float, float, float, float, float]:
        if index >= self.length or index < 0:
            return None
        return self.row[index], self.column[index], self.phi[index], self.length1[index], self.length2[index]
        
class MetrologyCircleResult(MetrologyResult):
    def __init__(self, handle: int, object: int, **kwargs):
        super().__init__(handle, object, **kwargs)
        self.length = int(len(self.result) / 3)
        if self.length == 0:
            self.row, self.column, self.radius = (None,) * 3
        else:
            indexs = [i * 3 for i in range(self.length)]
            self.row = [self.result[i] for i in indexs]
            self.column = [self.result[i + 1] for i in indexs]
            self.radius = [self.result[i + 2] for i in indexs]
            
    def get(self, index: int = 0) -> tuple[float, float, float]:
        if index >= self.length or index < 0:
            return None
        return self.row[index], self.column[index], self.radius[index]
    
class MetrologyEllipseResult(MetrologyResult):
    def __init__(self, handle: int, object: int, **kwargs):
        super().__init__(handle, object, **kwargs)
        self.length = int(len(self.result) / 5)
        if self.length == 0:
            self.row, self.column, self.phi, self.radius1, self.radius2 = (None,) * 5
        else:
            indexs = [i * 5 for i in range(self.length)]
            self.row = [self.result[i] for i in indexs]
            self.column = [self.result[i + 1] for i in indexs]
            self.phi = [self.result[i + 2] for i in indexs]
            self.radius1 = [self.result[i + 3] for i in indexs]
            self.radius2 = [self.result[i + 4] for i in indexs]
            
    def get(self, index: int = 0) -> tuple[float, float, float, float, float]:
        if index >= self.length or index < 0:
            return None
        return self.row[index], self.column[index], self.phi[index], self.radius1[index], self.radius2[index]
            
class MetrologyLineResult(MetrologyResult):
    def __init__(self, handle: int, object: int, **kwargs):
        super().__init__(handle, object, **kwargs)
        self.length = int(len(self.result) / 4)
        if self.length == 0:
            self.row1, self.column1, self.row2, self.column2 = (None,) * 4
        else:
            indexs = [i * 4 for i in range(self.length)]
            self.row1 = [self.result[i] for i in indexs]
            self.column1 = [self.result[i + 1] for i in indexs]
            self.row2 = [self.result[i + 2] for i in indexs]
            self.column2 = [self.result[i + 3] for i in indexs]
        
    def get(self, index: int = 0) -> tuple[float, float, float, float]:
        if index >= self.length or index < 0:
            return None
        return self.row1[index], self.column1[index], self.row2[index], self.column2[index]
        
class Metrology:
    def __init__(self):
        self._objects_type = {}
        self._objects = {}
        self._handle = ha.create_metrology_model()  
    
    def __del__(self):
        ha.clear_metrology_model(self._handle)
        
    def set_image_size(self, width: int, height: int):
        """
        设置图像大小
        :param width: 图像宽度
        :param height: 图像高度
        """
        ha.set_metrology_model_image_size(self._handle, width, height)
        
    def set_param(self, key:str, param_name, param_value):
        """
        设置测量模型参数
        :param key: 测量对象的唯一键
        :param param_name: 参数名称
        :param param_value: 参数值
        """
        if key not in self._objects:
            raise ValueError(f"Key {key} does not exist.")
        ha.set_metrology_model_param(self._handle, self._objects[key], param_name, param_value)
        
    def get_param(self, key:str, param_name):
        """
        获取测量模型参数
        :param key: 测量对象的唯一键
        :param param_name: 参数名称
        :return: 参数值
        """
        if key not in self._objects:
            raise ValueError(f"Key {key} does not exist.")
        return ha.get_metrology_model_param(self._handle, self._objects[key], param_name)
    
    def have_object(self, key: str) -> bool:
        """
        检查测量对象是否存在
        :param key: 测量对象的唯一键
        :return: 是否存在
        """
        return key in self._objects
    
    def add_object(self, key:str, shape_param: MetrologyObjectParam):
        """
        添加测量对象
        :param key: 测量对象的唯一键
        :param shape_param: 测量对象参数
        """
        if key in self._objects:
            raise ValueError(f"Key {key} already exists.")
        try:
            self._objects[key] = ha.add_metrology_object_generic(
                self._handle, 
                shape_param.shape, shape_param.shape_param,
                shape_param.measure_length_1, shape_param.measure_length_2,
                shape_param.measure_sigma, shape_param.measure_threshold,
                shape_param.gen_param_name, shape_param.gen_param_value)
            self._objects_type[key] = shape_param.shape
        except Exception as e:
            raise ValueError(f"Failed to add object {key}: {e}")
        
    def remove_object(self, key: str):
        """
        移除测量对象
        :param key: 测量对象的唯一键
        """
        if key not in self._objects:
            raise ValueError(f"Key {key} does not exist.")
        try:
            ha.clear_metrology_object(self._handle, self._objects[key])
            del self._objects[key]
            del self._objects_type[key]
        except Exception as e:
            raise ValueError(f"Failed to remove object {key}: {e}")
    
    def run(self, image: Union[ha.HObject, np.ndarray, str], have_contour: bool = False, have_measure: bool = False, **kwargs) -> dict[str, MetrologyResult]:
        """
        运行测量
        :param image: 输入图像
        :return: 测量结果
        """
        if isinstance(image, np.ndarray):
            image = ha.himage_from_numpy_array(image)
        elif isinstance(image, str):
            image = ha.read_image(image)
        if not isinstance(image, ha.HObject):
            raise ValueError("template_image must be a Halcon image or a numpy array.")
        if ha.count_channels(image) == 3:
            image = ha.rgb1_to_gray(image)
        ha.apply_metrology_model(image, self._handle)
        results = {}
        for key, object in self._objects.items():
            if self._objects_type[key] == 'rectangle2':
                results[key] = MetrologyRectangleResult(self._handle, object, have_contour=have_contour, have_measure=have_measure, **kwargs)
            elif self._objects_type[key] == 'circle':
                results[key] = MetrologyCircleResult(self._handle, object, have_contour=have_contour, have_measure=have_measure, **kwargs)
            elif self._objects_type[key] == 'ellipse':
                results[key] = MetrologyEllipseResult(self._handle, object, have_contour=have_contour, have_measure=have_measure, **kwargs)
            elif self._objects_type[key] == 'line':
                results[key] = MetrologyLineResult(self._handle, object, have_contour=have_contour, have_measure=have_measure, **kwargs)
            else:
                results[key] = MetrologyResult(self._handle, object, have_contour=have_contour, have_measure=have_measure, **kwargs)
        return results

if __name__ == '__main__':
    image = ha.read_image(r"C:\Users\public\Documents\MVTec\HALCON-20.11-Steady\examples\images\pads.png")
    width, height = ha.get_image_size(image)
    metrology = Metrology()
    metrology.set_image_size(width, height)
    metrology.add_object('rectangle', MetrologyRectangleParam(
        row=410, 
        column=215,
        phi=0,
        length1=85,
        length2=88,
        measure_length_1=10,
        measure_length_2=5,
        measure_sigma=0.5,
        measure_threshold=1
        ))
    item = metrology.run(image)['rectangle']
    print(item.__dict__)