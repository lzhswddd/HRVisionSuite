import numpy as np
import typing
import halcon as ha

def get_line_points(x:np.ndarray, slope:float, intercept:float) -> np.ndarray:
    """
    Calculate the y-coordinates of points on a line given x-coordinates, slope, and intercept.

    Parameters:
        x (np.ndarray): An array of x-coordinates.
        slope (float): The slope of the line.
        intercept (float): The y-intercept of the line.

    Returns:
        np.ndarray: An array of y-coordinates corresponding to the input x-coordinates.
    """
    return slope * x + intercept

def get_line(line_start:typing.Tuple[float, float], line_end:typing.Tuple[float, float]) -> typing.Tuple[float, float]:
    """
    Calculate the slope and intercept of a line given two points.

    Parameters:
        line_start (tuple): A tuple (x1, y1) representing the start point of the line.
        line_end (tuple): A tuple (x2, y2) representing the end point of the line.

    Returns:
        tuple: (slope, intercept) of the line.
    """
    x1, y1 = line_start
    x2, y2 = line_end
    if x2 == x1:
        raise ValueError("The line is vertical; slope is undefined.")
    slope = (y2 - y1) / (x2 - x1)
    intercept = y1 - slope * x1
    return slope, intercept

def get_line2(line_start:typing.Tuple[float, float], line_end:typing.Tuple[float, float]):
    """
    Generate the parametric equation of a line given two points.

    Parameters:
        line_start (tuple): A tuple (x1, y1) representing the start point of the line.
        line_end (tuple): A tuple (x2, y2) representing the end point of the line.

    Returns:
        tuple: Two functions x(t) and y(t) representing the parametric equations of the line.
    """
    x1, y1 = line_start
    x2, y2 = line_end

    def x(t: float) -> float:
        return x1 + t * (x2 - x1)

    def y(t: float) -> float:
        return y1 + t * (y2 - y1)

    return x, y

def fit_line(points: np.ndarray) -> tuple:
    """
    Fits a line to a set of points using least squares.

    Parameters:
        points (np.ndarray): An Nx2 array of (x, y) coordinates.

    Returns:
        tuple: (slope, intercept) of the fitted line.
    """
    x = points[:, 0]
    y = points[:, 1]
    A = np.vstack([x, np.ones(len(x))]).T
    slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
    return slope, intercept

def fit_line_segment(points: np.ndarray) -> tuple:
    """
    Fits a line segment to a set of points and returns the start and end points.

    Parameters:
        points (np.ndarray): An Nx2 array of (x, y) coordinates.

    Returns:
        tuple: ((x1, y1), (x2, y2)) representing the start and end points of the line segment.
    """
    slope, intercept = fit_line(points)
    x_min, x_max = points[:, 0].min(), points[:, 0].max()
    y_min = slope * x_min + intercept
    y_max = slope * x_max + intercept
    return (x_min, y_min), (x_max, y_max)

def point_to_line_distance(point: typing.Union[tuple, np.ndarray], slope: float, intercept: float) -> typing.Sequence[float]:
    """
    Calculate the perpendicular distance from a point to a line.

    Parameters:
        point (tuple): A tuple (x, y) representing the coordinates of the point.
        slope (float): The slope of the line.
        intercept (float): The y-intercept of the line.

    Returns:
        float: The perpendicular distance from the point to the line.
    """
    x, y = point
    numerator = abs(slope * x - y + intercept)
    denominator = np.sqrt(slope**2 + 1)
    return numerator / denominator

def point_to_line_distance2(point: typing.Union[tuple, np.ndarray], line_start:typing.Tuple[float, float], line_end:typing.Tuple[float, float]):
    """
    Calculate the perpendicular distance from a point to a line segment.

    Parameters:
        point (tuple): A tuple (x, y) representing the coordinates of the point.
        line_start (tuple): A tuple (x1, y1) representing the start point of the line segment.
        line_end (tuple): A tuple (x2, y2) representing the end point of the line segment.

    Returns:
        float: The perpendicular distance from the point to the line segment.
    """
    if line_start[0] == line_end[0]:  # vertical line
        return abs(point[0] - line_start[0])
    if line_start[1] == line_end[1]:
        return abs(point[1] - line_start[1])
    a, b = get_line(line_start, line_end)
    return point_to_line_distance(point, a, b)

def gen_rotate_mat(angle:float, center:typing.Tuple[float, float]) -> typing.Sequence[float]:
    """
    Generate a rotation matrix for a given angle and center.

    Parameters:
        angle (float): The angle in degrees.
        center (tuple): A tuple (cx, cy) representing the center of rotation.
    
    Returns:
        list: A 2x3 rotation matrix.
    """
    mat = ha.hom_mat2d_identity()
    mat = ha.hom_mat2d_translate(mat, -center[1], -center[0])
    mat = ha.hom_mat2d_rotate(mat, angle, 0, 0)
    mat = ha.hom_mat2d_translate(mat, center[1], center[0])
    
    return mat