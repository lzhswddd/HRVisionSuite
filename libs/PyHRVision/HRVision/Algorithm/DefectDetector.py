from .Measure import Measure
from .Shape import point_to_line_distance2, fit_line, gen_rotate_mat
import typing
import halcon as ha
import numpy as np

class LineSegDefect:
    def __init__(self, **kwargs):
        self.line_start = kwargs.get('line_start', (0, 0))
        self.line_end = kwargs.get('line_end', (0, 0))
        self.measure:Measure = kwargs.get('measure', Measure(**kwargs))

    def set_line(self, line_start:typing.Tuple[float,float], line_end:typing.Tuple[float,float]):
        self.line_start = line_start
        self.line_end = line_end
    
    def get_line(self):
        return self.line_start, self.line_end

    def set_measure(self, measure):
        self.measure = measure
        
    def get_measure(self):
        return self.measure
        
    def create(self, measure_width:float, measure_height:float, measure_gap:float):
        
        if self.measure is None:
            raise ValueError("Measure object is not set.")
            
        rot_rects = Measure.gen_line_rotrectangle(self.line_start, self.line_end, measure_width, measure_height, measure_gap)    
        
        self.measure.clear()
        self.measure.add_rectangle(rot_rects)

    def clear(self):
        if self.measure is not None:
            self.measure.clear()
        else:
            raise ValueError("Measure object is already released or not set.")
        
    def translate(self, dx:float, dy:float):
        if self.measure is None:
            raise ValueError("Measure object is not set.")
        
        self.line_start = (self.line_start[0] + dx, self.line_start[1] + dy)
        self.line_end = (self.line_end[0] + dx, self.line_end[1] + dy)
        
        self.measure.translate(dx, dy)
        
    def rotate(self, angle:float, center:typing.Tuple[float, float]):
        if self.measure is None:
            raise ValueError("Measure object is not set.")
        
        mat = gen_rotate_mat(angle, center)
        py, px = ha.affine_trans_point_2d(mat, self.line_start[1], self.line_start[0])
        self.line_start = (px[0], py[0])
        py, px = ha.affine_trans_point_2d(mat, self.line_end[1], self.line_end[0])
        self.line_end = (px[0], py[0])
        
        self.measure.rotate(angle, center)
        
    def affine(self, dx: float, dy: float, angle: float, center: typing.Optional[typing.Tuple[float, float]] = None):
        if self.measure is None:
            raise ValueError("Measure object is not set.")
        
        mat = gen_rotate_mat(angle, center)
        py, px = ha.affine_trans_point_2d(mat, self.line_start[1], self.line_start[0])
        self.line_start = (px[0]+dx, py[0]+dy)
        py, px = ha.affine_trans_point_2d(mat, self.line_end[1], self.line_end[0])
        self.line_end = (px[0]+dx, py[0]+dy)
        
        self.measure.affine(dx, dy, angle, center)
        
    def run(self, image, limit_distance:typing.Tuple[float, float], limit_width:float = None, measure_sigma:float = None, measure_threshold:float = None, measure_transition:str = None, measure_select:str = None):
        if self.measure is None:
            raise ValueError("Measure object is not set.")
        
        results = self.measure.run(image, measure_sigma, measure_threshold, measure_transition, measure_select)
        
        count = 1
        temp_defects = []
        defects = []
        other_data = []
        for result in results:
            pos = result.best()
            if pos is not None:
                y = pos[1]
                x = pos[0]
                distance = point_to_line_distance2((x, y), self.line_start, self.line_end) 
                if distance < limit_distance[0] or distance > limit_distance[1]:
                    if limit_width is not None:
                        if count < limit_width:
                            count += 1
                            temp_defects.append((x, y, distance))
                        else:
                            count = 1
                            if len(temp_defects) > 0:
                                defects.extend(temp_defects)
                                temp_defects = []
                            defects.append((x, y, distance))
                    else:
                        defects.append((x, y, distance))
                else:
                    other_data.append((x, y, distance))
        if len(temp_defects) > 0:
            other_data.extend(temp_defects)
            temp_defects = []
                
        return {
            "defect": defects,
            "other": other_data
        }
    
class FitLineSegDefect(LineSegDefect):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def run(self, image, limit_distance:typing.Tuple[float, float], limit_width:float = None, measure_sigma:float = None, measure_threshold:float = None, measure_transition:str = None, measure_select:str = None):
        if self.measure is None:
            raise ValueError("Measure object is not set.")
        
        results = self.measure.run(image, measure_sigma, measure_threshold, measure_transition, measure_select)
        
        if len(results) == 0:
            return {
                "defect": [],
                "other": [],
                "error": "No results found."
            }
        
        # Fit line to the results
        y = []
        x = []
        for result in results:
            pos = result.best()
            if pos is not None:
                y.append(pos[1])
                x.append(pos[0])
                
        if len(x) == 0 or len(y) == 0:
            return {
                "defect": [],
                "other": [],
                "error": "No valid points found."
            }
        
        try:
            contour = ha.gen_contour_polygon_xld(y, x)
            row_begin, col_begin, row_end, col_end, nr, nc, dist = ha.fit_line_contour_xld(contour, 'tukey', -1, 0, 5, 2)
        
            line_start = (col_begin[0], row_begin[0])
            line_end = (col_end[0], row_end[0])
        except Exception as e:
            return {
                "defect": [],
                "other": [],
                "error": str(e)
            }
        
        count = 1
        temp_defects = []
        defects = []
        other_data = []
        for result in results:
            pos = result.best()
            if pos is not None:
                y = pos[1]
                x = pos[0]
                distance = point_to_line_distance2((x, y), line_start, line_end) 
                if distance < limit_distance[0] or distance > limit_distance[1]:
                    if limit_width is not None:
                        if count < limit_width:
                            count += 1
                            temp_defects.append((x, y, distance))
                        else:
                            count = 1
                            if len(temp_defects) > 0:
                                defects.extend(temp_defects)
                                temp_defects = []
                            defects.append((x, y, distance))
                    else:
                        defects.append((x, y, distance))
                else:
                    other_data.append((x, y, distance))
        if len(temp_defects) > 0:
            other_data.extend(temp_defects)
            temp_defects = []
                
        return {
            "defect": defects,
            "other": other_data,
            "line_start": line_start,
            "line_end": line_end,
            "error": None
        }

if __name__ == "__main__":
    import json
    import halcon as ha
    import Match
    from PySide6.QtCore import QRectF
 
    ha.set_system('clip_region', 'false')
 
    def rect_to_points(rects:list[QRectF], dire:str) -> tuple[list[tuple[float, float]]]:
        top_lefts = []
        top_rights = []
        bottom_lefts = []
        bottom_rights = []
        
        for rect_ in rects:
            rect__ = rect_.get('rect')
            rect = QRectF(rect__[0], rect__[1], rect__[2], rect__[3])
            top_left = rect.topLeft()
            top_right = rect.topRight()
            bottom_left = rect.bottomLeft()
            bottom_right = rect.bottomRight()
            
            if dire == "top":
                top_lefts.append((top_left.x(), top_left.y()))
                top_rights.append((top_right.x(), top_right.y()))
                bottom_lefts.append((bottom_left.x(), bottom_left.y()))
                bottom_rights.append((bottom_right.x(), bottom_right.y()))
            elif dire == "right":
                top_lefts.append((bottom_left.x(), bottom_left.y()))
                top_rights.append((top_left.x(), top_left.y()))
                bottom_lefts.append((bottom_right.x(), bottom_right.y()))
                bottom_rights.append((top_right.x(), top_right.y()))
            elif dire == "bottom":
                top_lefts.append((bottom_right.x(), bottom_right.y()))
                top_rights.append((bottom_left.x(), bottom_left.y()))
                bottom_lefts.append((top_left.x(), top_left.y()))
                bottom_rights.append((top_right.x(), top_right.y()))
            elif dire == "left":
                top_lefts.append((top_right.x(), top_right.y()))
                top_rights.append((bottom_right.x(), bottom_right.y()))
                bottom_lefts.append((top_left.x(), top_left.y()))
                bottom_rights.append((bottom_left.x(), bottom_left.y()))
                
        return top_lefts, top_rights, bottom_lefts, bottom_rights

 
    shape = Match.ScaledShapeMatch()
    shape.read_model(r'C:\Users\lzh\Desktop\jiaokou\current\model.model')
    shape.min_score = 0.3
    image = ha.read_image(r"C:\Users\lzh\Desktop\jiaokou\2025-05-28\20250528010821255.jpg")
    width, height = ha.get_image_size(image)
    
    rows, cols, angles, _, _ = shape.find_model(image)
    
    data = {}
    with open(r"C:\Users\lzh\Desktop\jiaokou\current\param.json", 'r') as f:
        data = json.load(f)
    
    camera = data.get('camera-1', {})
    calipers = camera.get('calipers', {})
    calipers1 = calipers.get('calipers', {})
    
    top = calipers1.get("top", [])
    left = calipers1.get("left", [])
    bottom = calipers1.get("bottom", [])
    right = calipers1.get("right", [])
    
    topDefectDetect = FitLineSegDefect()
    leftDefectDetect = FitLineSegDefect()
    bottomDefectDetect = FitLineSegDefect()
    rightDefectDetect = FitLineSegDefect()
            
    topMeasure = Measure(width=width,height=height)
    leftMeasure = Measure(width=width,height=height)
    bottomMeasure = Measure(width=width,height=height)
    rightMeasure = Measure(width=width,height=height)
    
    topMeasure.clear()
    leftMeasure.clear()
    bottomMeasure.clear()
    rightMeasure.clear()
    
    top_lefts, top_rights, bottom_lefts, bottom_rights = rect_to_points(top, "top")
    topMeasure.add_rectangle2_point(top_left=top_lefts, 
                                    top_right=top_rights, 
                                    bottom_left=bottom_lefts, 
                                    bottom_right=bottom_rights)
    
    top_lefts, top_rights, bottom_lefts, bottom_rights = rect_to_points(left, "left")
    leftMeasure.add_rectangle2_point(top_left=top_lefts, 
                                    top_right=top_rights, 
                                    bottom_left=bottom_lefts, 
                                    bottom_right=bottom_rights)
    
    top_lefts, top_rights, bottom_lefts, bottom_rights = rect_to_points(bottom, "bottom")
    bottomMeasure.add_rectangle2_point(top_left=top_lefts, 
                                    top_right=top_rights, 
                                    bottom_left=bottom_lefts, 
                                    bottom_right=bottom_rights)
    
    top_lefts, top_rights, bottom_lefts, bottom_rights = rect_to_points(right, "right")
    rightMeasure.add_rectangle2_point(top_left=top_lefts, 
                                    top_right=top_rights, 
                                    bottom_left=bottom_lefts, 
                                    bottom_right=bottom_rights)
    
    rect1 = calipers.get("rect", {})
    temprect = QRectF(rect1.get("x", 0), rect1.get("y", 0),
                    rect1.get("width", 0), rect1.get("height", 0))
    topDefectDetect.set_line((temprect.topLeft().x(), temprect.topLeft().y()),
                            (temprect.topRight().x(), temprect.topRight().y()))
    leftDefectDetect.set_line((temprect.topLeft().x(), temprect.topLeft().y()),
                            (temprect.bottomLeft().x(), temprect.bottomLeft().y()))
    bottomDefectDetect.set_line((temprect.bottomLeft().x(), temprect.bottomLeft().y()),
                            (temprect.bottomRight().x(), temprect.bottomRight().y()))
    rightDefectDetect.set_line((temprect.bottomRight().x(), temprect.bottomRight().y()),
                            (temprect.topRight().x(), temprect.topRight().y()))
    
    topDefectDetect.set_measure(topMeasure)
    leftDefectDetect.set_measure(leftMeasure)
    bottomDefectDetect.set_measure(bottomMeasure)
    rightDefectDetect.set_measure(rightMeasure)
    
    rectangle2s = None
    for shape in topDefectDetect.measure.shape():
        rect = shape['data']
        rectangle = ha.gen_rectangle2(rect[0], rect[1], rect[2], rect[3], rect[4])
        if rectangle2s is None:
            rectangle2s = rectangle
        else:
            rectangle2s = ha.concat_obj(rectangle2s, rectangle)
        ha.write_region(rectangle2s, "rectangles.hobj")

    topDefectDetect.affine(cols[0]-temprect.center().x(), rows[0]-temprect.center().y(), angles[0], (temprect.center().x(), temprect.center().y()))
    leftDefectDetect.affine(cols[0]-temprect.center().x(), rows[0]-temprect.center().y(), angles[0], (temprect.center().x(), temprect.center().y()))
    bottomDefectDetect.affine(cols[0]-temprect.center().x(), rows[0]-temprect.center().y(), angles[0], (temprect.center().x(), temprect.center().y()))
    rightDefectDetect.affine(cols[0]-temprect.center().x(), rows[0]-temprect.center().y(), angles[0], (temprect.center().x(), temprect.center().y()))
        
    # topDefectDetect.rotate(angles[0], (temprect.center().x(), temprect.center().y()))
    # topDefectDetect.translate(cols[0]-temprect.center().x(), rows[0]-temprect.center().y())
    
    # leftDefectDetect.rotate(angles[0], (temprect.center().x(), temprect.center().y()))
    # leftDefectDetect.translate(cols[0]-temprect.center().x(), rows[0]-temprect.center().y())
    
    # bottomDefectDetect.rotate(angles[0], (temprect.center().x(), temprect.center().y()))
    # bottomDefectDetect.translate(cols[0]-temprect.center().x(), rows[0]-temprect.center().y())
    
    # rightDefectDetect.rotate(angles[0], (temprect.center().x(), temprect.center().y()))
    # rightDefectDetect.translate(cols[0]-temprect.center().x(), rows[0]-temprect.center().y())
        
    # topDefectDetect.translate(cols[0]-temprect.center().x(), rows[0]-temprect.center().y())
    # topDefectDetect.rotate(angles[0], (cols[0], rows[0]))
    
    # leftDefectDetect.translate(cols[0]-temprect.center().x(), rows[0]-temprect.center().y())
    # leftDefectDetect.rotate(angles[0], (cols[0], rows[0]))
    
    # bottomDefectDetect.translate(cols[0]-temprect.center().x(), rows[0]-temprect.center().y())
    # bottomDefectDetect.rotate(angles[0], (cols[0], rows[0]))
    
    # rightDefectDetect.translate(cols[0]-temprect.center().x(), rows[0]-temprect.center().y())
    # rightDefectDetect.rotate(angles[0], (cols[0], rows[0]))
    
    rectangle2s = None
    for shape in topDefectDetect.measure.shape():
        rect = shape['data']
        rectangle = ha.gen_rectangle2(rect[0], rect[1], rect[2], rect[3], rect[4])
        if rectangle2s is None:
            rectangle2s = rectangle
        else:
            rectangle2s = ha.concat_obj(rectangle2s, rectangle)
        ha.write_region(rectangle2s, "rectangles1.hobj")
        
    topResult = topDefectDetect.run(image, (0, 20))
    leftResult = leftDefectDetect.run(image, (0, 20))
    bottomResult = bottomDefectDetect.run(image, (0, 20))
    rightResult = rightDefectDetect.run(image, (0, 20))
    
    print("Top Defects:", topResult)
    print("Left Defects:", leftResult)
    print("Bottom Defects:", bottomResult)
    print("Right Defects:", rightResult)
    
    
    