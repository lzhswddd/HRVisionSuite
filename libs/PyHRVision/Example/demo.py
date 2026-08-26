import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from HRVision.Algorithm.Calibrator import XYRotCalib

xyr = XYRotCalib()

print(xyr.compute_compensate((10,0,0), (0,100,10)))