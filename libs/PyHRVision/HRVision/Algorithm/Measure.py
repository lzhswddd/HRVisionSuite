import halcon as ha
import numpy as np
from typing import Sequence, Union, Optional, Tuple
import math

class MeasureResult:
    def __init__(self, result:Tuple[Sequence[float], Sequence[float], Sequence[float], Sequence[float]], shape:dict[str, list[float]] = {}):
        """
        Initializes the MeasureResult object.

        Parameters:
            result: A tuple containing four sequences:
                - row_edge: The row coordinates of the edge points.
                - column_edge: The column coordinates of the edge points.
                - amplitude: The amplitude values at the edge points.
                - distance: The distance values at the edge points.
        """
        self.shape_type = shape.get("type", "rectangle")
        self.shape = shape.get("data", [])
        self.row_edge, self.column_edge, self.amplitude, self.distance = result
        
    def best(self) -> Union[Tuple[float, float, float], None]:
        """
        Returns the best result from the measure.

        Returns:
            A tuple containing four sequences:
                - row_edge: The row coordinates of the edge points.
                - column_edge: The column coordinates of the edge points.
                - amplitude: The amplitude values at the edge points.
                - distance: The distance values at the edge points.
        """
        if len(self.row_edge) == 0:
            return None
        if len(self.row_edge) == 1:
            return (self.column_edge[0], self.row_edge[0], self.amplitude[0])
        best_index = np.argmax(self.amplitude)
        return (self.column_edge[best_index], self.row_edge[best_index], self.amplitude[best_index])

class Measure:
    def __init__(self, **kwargs):
        """ 
        Initializes the Measure object.
        Parameters:
            width: The width of the image.
            height: The height of the image.
            sigma: The sigma value for the measure.
            threshold: The threshold value for the measure.
            transition: The transition type for the measure. e.g. 'all', 'positive', 'negative'.
            select: The selection type for the measure. e.g. 'all', 'first', 'last'.
        """
        self.__shapes = []
        self.__handles = []
        self.width = kwargs.get('width', 0)
        self.height = kwargs.get('height', 0)
        self.sigma = kwargs.get('sigma', 1)
        self.threshold = kwargs.get('threshold', 30)
        self.transition = kwargs.get('transition', 'all')
        self.select = kwargs.get('select', 'all')
        self.interpolation = kwargs.get('interpolation', 'nearest_neighbor')
        
    def __del__(self):
        self.clear()

    def shape(self) -> Sequence[dict[str, list[float]]]:
        """
        Returns the shapes of the measure.

        Returns:
            A sequence of dictionaries containing the shape type and data.
        """
        return self.__shapes

    def set_image_size(self, width, height):
        """
        Sets the image size for the measure.

        Parameters:
            width: The width of the image.
            height: The height of the image.
        """
        self.width = width
        self.height = height

    def add_rectangle2_point(self,
                       top_left:Sequence[Tuple[Union[int,float], Union[int,float]]],
                       bottom_left:Sequence[Tuple[Union[int,float], Union[int,float]]],
                       top_right:Sequence[Tuple[Union[int,float], Union[int,float]]],
                       bottom_right:Sequence[Tuple[Union[int,float], Union[int,float]]],
                       interpolation:str='nearest_neighbor'):
        """
        Adds rectangle2 measure to the image using corner points.
        Parameters:
            top_left: The top left corner of the rectangle.
            bottom_left: The bottom left corner of the rectangle.
            top_right: The top right corner of the rectangle.
            bottom_right: The bottom right corner of the rectangle.
            interpolation: The interpolation method. Default is 'nearest_neighbor'. e.g. 'nearest_neighbor', 'bilinear', 'bicubic'.
        """
        if isinstance(top_left, tuple):
            top_left = [top_left]
        if isinstance(bottom_left, tuple):
            bottom_left = [bottom_left]
        if isinstance(top_right, tuple):
            top_right = [top_right]
        if isinstance(bottom_right, tuple):
            bottom_right = [bottom_right]
            
        for i in range(len(top_left)):
            # Calculate the center point of the rectangle
            center_row = (top_left[i][1] + bottom_right[i][1]) / 2
            center_column = (top_left[i][0] + bottom_right[i][0]) / 2

            # Calculate the angle of the rectangle
            delta_row = top_left[i][1] - bottom_left[i][1]
            delta_column = top_left[i][0] - bottom_left[i][0]
            angle = np.pi - math.atan2(delta_row, delta_column)

            # Calculate the lengths of the rectangle
            length1 = math.sqrt((top_left[i][1] - bottom_left[i][1])**2 + (top_left[i][0] - bottom_left[i][0])**2) / 2
            length2 = math.sqrt((top_left[i][1] - top_right[i][1])**2 + (top_left[i][0] - top_right[i][0])**2) / 2

            # Add the rectangle to the measure object
            handle = ha.gen_measure_rectangle2(center_row, center_column, angle, length1, length2, self.width, self.height, interpolation)
            self.__shapes.append({'type':'rectangle', 'data':[center_row, center_column, angle, length1, length2]})
            self.__handles.append(handle)           

    def add_rectangle(self, rectangle:Sequence[Tuple[Union[int,float], Union[int,float], Union[int,float], Union[int,float], Union[int,float]]],
                       interpolation:str='nearest_neighbor'):
        """
        Adds rectangle2 measure to the image using center points and angles.
        Parameters:
            rectangle: A sequence of tuples containing the center row, center column, angle, length1, and length2 of the rectangle.
            interpolation: The interpolation method. Default is 'nearest_neighbor'. e.g. 'nearest_neighbor', 'bilinear', 'bicubic'.
        """
        if isinstance(rectangle, tuple):
            rectangle = [rectangle]
        for i in range(len(rectangle)):
            handle = ha.gen_measure_rectangle2(rectangle[i][0], rectangle[i][1], rectangle[i][2], rectangle[i][3], rectangle[i][4], self.width, self.height, interpolation)
            self.__shapes.append({'type':'rectangle', 'data':[rectangle[i][0], rectangle[i][1], rectangle[i][2], rectangle[i][3], rectangle[i][4]]})
            self.__handles.append(handle)
        
    def add_rectangle2(self, 
                       row:Sequence[Union[int,float]], 
                       column:Sequence[Union[int,float]], 
                       phi:Sequence[Union[int,float]], 
                       length1:Sequence[Union[int,float]], 
                       length2:Sequence[Union[int,float]], 
                       interpolation:str='nearest_neighbor'):
        """
        Adds rectangle2 measure to the image.

        Parameters:
            row: The row of the rectangle center.
            column: The column of the rectangle center.
            phi: The angle of the rectangle in radians.
            length1: The first length of the rectangle.
            length2: The second length of the rectangle.
            interpolation: The interpolation method. Default is 'nearest_neighbor'. e.g. 'nearest_neighbor', 'bilinear', 'bicubic'.
        """
        if isinstance(row, (int, float)):
            row = [row]
        if isinstance(column, (int, float)):
            column = [column]
        if isinstance(phi, (int, float)):
            phi = [phi]
        if isinstance(length1, (int, float)):
            length1 = [length1]
        if isinstance(length2, (int, float)):
            length2 = [length2]
            
        for i in range(len(row)):
            handle = ha.gen_measure_rectangle2(row[i], column[i], phi[i], length1[i], length2[i], self.width, self.height, interpolation)
            self.__shapes.append({'type':'rectangle', 'data':[row[i], column[i], phi[i], length1[i], length2[i]]})
            self.__handles.append(handle)
    
    def add_arc(self, arc:Sequence[Tuple[Union[int,float], Union[int,float], Union[int,float], Union[int,float], Union[int,float], Union[int,float]]], interpolation:str='nearest_neighbor'): 
        """
        Adds arc measure to the image using center points and angles.
        Parameters:
            arc: A sequence of tuples containing the center row, center column, radius, start angle, and end angle of the arc.
            interpolation: The interpolation method. Default is 'nearest_neighbor'. e.g. 'nearest_neighbor', 'bilinear', 'bicubic'.
        """
        if isinstance(arc, tuple):
            arc = [arc]
        for i in range(len(arc)):
            handle = ha.gen_measure_arc(arc[i][0], arc[i][1], arc[i][2], arc[i][3], arc[i][4], arc[i][5], self.width, self.height, interpolation)
            self.__shapes.append({'type':'arc', 'data':[arc[i][0], arc[i][1], arc[i][2], arc[i][3], arc[i][4], arc[i][5]]})
            self.__handles.append(handle)
    
    def add_arc2(self,
                center_row:Sequence[Union[int,float]],
                center_column:Sequence[Union[int,float]],
                radius:Sequence[Union[int,float]],
                angle_start:Sequence[Union[int,float]],
                angle_extent:Sequence[Union[int,float]],
                annulus_radius:Sequence[Union[int,float]],
                interpolation:str='nearest_neighbor'):
        """
        Adds arc measure to the image.
        Parameters:
            center_row: The row of the arc center.
            center_column: The column of the arc center.
            radius: The radius of the arc.
            angle_start: The start angle of the arc in radians.
            angle_extent: The extent angle of the arc in radians.
            annulus_radius: The annulus radius of the arc.
            interpolation: The interpolation method. Default is 'nearest_neighbor'. e.g. 'nearest_neighbor', 'bilinear', 'bicubic'.
        """
        if isinstance(center_row, (int, float)):
            center_row = [center_row]
        if isinstance(center_column, (int, float)):
            center_column = [center_column]
        if isinstance(radius, (int, float)):
            radius = [radius]
        if isinstance(angle_start, (int, float)):
            angle_start = [angle_start]
        if isinstance(angle_extent, (int, float)):
            angle_extent = [angle_extent]
        if isinstance(annulus_radius, (int, float)):
            annulus_radius = [annulus_radius]
        for i in range(len(center_row)):
            handle = ha.gen_measure_arc(center_row[i], center_column[i], radius[i], angle_start[i], angle_extent[i], annulus_radius[i], self.width, self.height, interpolation)
            self.__shapes.append({'type':'arc', 'data':[center_row[i], center_column[i], radius[i], angle_start[i], angle_extent[i], annulus_radius[i]]})
            self.__handles.append(handle)
    
    def clear(self):
        """
        Clears all measure handles.
        """
        for handle in self.__handles:
            ha.close_measure(handle)
        self.__shapes = []
        self.__handles = []
    
    def translate(self, dx: float, dy: float):
        """
        Translates the measure handles by the given row and column offsets.

        Parameters:
            row: The row offset.
            column: The column offset.
        """
        
        for i in range(len(self.__shapes)):
            shape = self.__shapes[i]
            if shape['type'] == 'rectangle':
                shape['data'][0] += dy
                shape['data'][1] += dx
            elif shape['type'] == 'arc':
                shape['data'][0] += dy
                shape['data'][1] += dx
                
        for handle in self.__handles:
            ha.translate_measure(handle, shape['data'][0], shape['data'][1])

            
    def rotate(self, angle: float, center: Optional[Tuple[float, float]] = None):
        """
        Rotates the measure handles by the given angle.

        Parameters:
            angle: The angle in radians.
            center: The center point of rotation. If None, the center of the image is used.
        """
        if center is None:
            center = (self.width / 2, self.height / 2)
            
        mat = ha.hom_mat2d_identity()
        mat = ha.hom_mat2d_translate(mat, -center[1], -center[0])
        mat = ha.hom_mat2d_rotate(mat, angle, 0, 0)
        mat = ha.hom_mat2d_translate(mat, center[1], center[0])
        
        for i in range(len(self.__shapes)):
            shape = self.__shapes[i]
            px, py = ha.affine_trans_point_2d(mat, shape['data'][0], shape['data'][1])
            shape['data'][0] = px[0]
            shape['data'][1] = py[0]
            if shape['type'] == 'rectangle':
                shape['data'][2] += angle
            elif shape['type'] == 'arc':
                shape['data'][3] += angle
                shape['data'][4] += angle
        
        for handle in self.__handles:
            ha.close_measure(handle)
        self.__handles.clear()
        
        for i in range(len(self.__shapes)):
            shape = self.__shapes[i]
            if shape['type'] == 'rectangle':
                handle = ha.gen_measure_rectangle2(shape['data'][0], shape['data'][1], shape['data'][2], shape['data'][3], shape['data'][4], self.width, self.height, self.interpolation)
            elif shape['type'] == 'arc':
                handle = ha.gen_measure_arc(shape['data'][0], shape['data'][1], shape['data'][2], shape['data'][3], shape['data'][4], shape['data'][5], self.width, self.height, self.interpolation)
            self.__handles.append(handle)

    def affine(self, dx: float, dy: float, angle: float, center: Optional[Tuple[float, float]] = None):
        """
        Rotates the measure handles by the given angle.

        Parameters:
            angle: The angle in radians.
            center: The center point of rotation. If None, the center of the image is used.
        """
        if center is None:
            center = (self.width / 2, self.height / 2)
            
        mat = ha.hom_mat2d_identity()
        mat = ha.hom_mat2d_translate(mat, -center[1], -center[0])
        mat = ha.hom_mat2d_rotate(mat, angle, 0, 0)
        mat = ha.hom_mat2d_translate(mat, center[1]+dy, center[0]+dx)
        
        for i in range(len(self.__shapes)):
            shape = self.__shapes[i]
            px, py = ha.affine_trans_point_2d(mat, shape['data'][0], shape['data'][1])
            shape['data'][0] = px[0]
            shape['data'][1] = py[0]
            if shape['type'] == 'rectangle':
                shape['data'][2] += angle
            elif shape['type'] == 'arc':
                shape['data'][3] += angle
                shape['data'][4] += angle
        
        for handle in self.__handles:
            ha.close_measure(handle)
        self.__handles.clear()
        
        for i in range(len(self.__shapes)):
            shape = self.__shapes[i]
            if shape['type'] == 'rectangle':
                handle = ha.gen_measure_rectangle2(shape['data'][0], shape['data'][1], shape['data'][2], shape['data'][3], shape['data'][4], self.width, self.height, self.interpolation)
            elif shape['type'] == 'arc':
                handle = ha.gen_measure_arc(shape['data'][0], shape['data'][1], shape['data'][2], shape['data'][3], shape['data'][4], shape['data'][5], self.width, self.height, self.interpolation)
            self.__handles.append(handle)
    
    def run(self, image: Union[ha.HObject, np.ndarray, str], 
            sigma: Optional[float] = None, 
            threshold: Optional[float] = None, 
            transition: Optional[str] = None, 
            select: Optional[str] = None) -> Sequence[MeasureResult]:
        """
        Runs the measure on the given image.

        Parameters:
            image: The input image.
        """
        if sigma is None:
            sigma = self.sigma
        if threshold is None:
            threshold = self.threshold
        if transition is None:
            transition = self.transition
        if select is None:
            select = self.select
            
        if isinstance(image, np.ndarray):
            image = ha.himage_from_numpy_array(image)
        elif isinstance(image, str):
            image = ha.read_image(image)
        if not isinstance(image, ha.HObject):
            raise ValueError("template_image must be a Halcon image or a numpy array.")
        if ha.count_channels(image) == 3:
            image = ha.rgb1_to_gray(image)
            
        results = []
        for handle in self.__handles:
            results.append(MeasureResult(ha.measure_pos(image, handle, sigma, threshold, transition, select), self.__shapes[len(results)]))
        return results
    
    @staticmethod
    def gen_line_rotrectangle(line_start:tuple[float,float], line_end:tuple[float,float], 
                           measure_width:float, measure_height:float, measure_gap:float) -> Sequence[tuple[float,float,float,float,float]]:
        """
        Generates rotate rectangle measures by a line segment.
        Parameters:
            line_start: The start point of the line.
            line_end: The end point of the line.
            measure_width: The width of the measure.
            measure_height: The height of the measure.
            measure_gap: The gap between measures.
        Returns:
            A tuple containing four sequences:
                - row: The row coordinates of the edge points.
                - column: The column coordinates of the edge points.
                - theta: The angle of the line in radians.
                - length1: The first length of the rectangle.
                - length2: The second length of the rectangle.
        """
        distance = math.sqrt((line_end[0] - line_start[0])**2 + (line_end[1] - line_start[1])**2)
        theta = math.atan2(line_end[1] - line_start[1], line_end[0] - line_start[0])
        rect_center_spacing = measure_width + measure_gap
        num_rectangles = int(distance // rect_center_spacing)
        rot_rect = []
        for i in range(num_rectangles):
            y = line_start[0] + (i + 0.5) * rect_center_spacing * math.cos(theta)
            x = line_start[1] + (i + 0.5) * rect_center_spacing * math.sin(theta)
            rot_rect.append((y, x, theta, measure_height / 2, measure_width / 2))
        return rot_rect
    
if __name__ == "__main__":
    import Shape
    
    image = ha.read_image("C:/Users/lzh/Desktop/微信图片_20250410143310.bmp")
    width, height = ha.get_image_size(image)
    
    p0 = (528.693, 547.168)
    p1 = (1656.69, 629.198)
    
    rect_width = 5
    rect_height = 100
    rect_gap = 10
    
    rot_rects = Measure.gen_line_rotrectangle(p0, p1, rect_width, rect_height, rect_gap)

    # Create the measure object
    rectangle2s = None
    # Add the rectangles to the measure object
    measure = Measure(width=width, height=height, sigma = 0.5, threshold=30, transition='negative', select='first')
    measure.add_rectangle(rectangle=rot_rects)
    # measure.add_rectangle2_point(rect_top_left, rect_bottom_left, rect_top_right, rect_bottom_right)
    for shape in measure.shape():
        rect = shape['data']
        rectangle = ha.gen_rectangle2(rect[0], rect[1], rect[2], rect[3], rect[4])
        if rectangle2s is None:
            rectangle2s = rectangle
        else:
            rectangle2s = ha.concat_obj(rectangle2s, rectangle)
        ha.write_region(rectangle2s, "rectangles.hobj")
        
    measure.rotate(np.pi / 2, (1245, 1068))
    
    for shape in measure.shape():
        rect = shape['data']
        rectangle = ha.gen_rectangle2(rect[0], rect[1], rect[2], rect[3], rect[4])
        if rectangle2s is None:
            rectangle2s = rectangle
        else:
            rectangle2s = ha.concat_obj(rectangle2s, rectangle)
        ha.write_region(rectangle2s, "rectangles1.hobj")
        
    measure.rotate(np.pi / 2, (1245, 1068))
    
    for shape in measure.shape():
        rect = shape['data']
        rectangle = ha.gen_rectangle2(rect[0], rect[1], rect[2], rect[3], rect[4])
        if rectangle2s is None:
            rectangle2s = rectangle
        else:
            rectangle2s = ha.concat_obj(rectangle2s, rectangle)
        ha.write_region(rectangle2s, "rectangles2.hobj")
        
    measure.rotate(np.pi / 2, (1245, 1068))
    
    for shape in measure.shape():
        rect = shape['data']
        rectangle = ha.gen_rectangle2(rect[0], rect[1], rect[2], rect[3], rect[4])
        if rectangle2s is None:
            rectangle2s = rectangle
        else:
            rectangle2s = ha.concat_obj(rectangle2s, rectangle)
        ha.write_region(rectangle2s, "rectangles3.hobj")
    #     measure.add_rectangle2(row=center[0], column=center[1], phi=angle, length1=rect_height / 2, length2=rect_width / 2)
    
    results = measure.run(image)
    # y = []
    # x = []
    # for result in results:
    #     y.extend(result.row_edge)
    #     x.extend(result.column_edge)
    #     print(result.__dict__)
        
    # a, b = Shape.fit_line(np.array([x, y]).T)
    
    # for i in range(len(x)):
    #     print("Point:", (x[i], y[i]))
    #     print("Fitted line:", a * x[i] + b)
    #     print("Distance from point to line:", Shape.point_to_line_distance((x[i], y[i]), a, b))
    
        
    