import cv2
import numpy as np

def has_gray_scale(image:np.ndarray, low_threshold=0, high_threshold=255):
    """
    Determines if an image contains gray scale values above a certain threshold.

    Args:
        image (numpy.ndarray): The input image.
        threshold (int): The gray scale threshold value.

    Returns:
        bool: True if gray scale values above the threshold are found, False otherwise.
    """
    if len(image.shape) == 2:  # Grayscale image
        return np.any(image >= low_threshold) and np.any(image <= high_threshold)
    elif len(image.shape) == 3:  # Color image
        if image.shape[2] == 1:
            gray_image = image[:, :, 0]
        elif image.shape[2] == 3:
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif image.shape[2] == 4:
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        return np.any(gray_image >= low_threshold) and np.any(gray_image <= high_threshold)
    else:
        raise ValueError("Unsupported image format")
    
def has_gray_blob(image:np.ndarray, low_threshold=0, high_threshold=255, limit_area=0):
    """
    Determines if an image contains gray blobs above a certain threshold.

    Args:
        image (numpy.ndarray): The input image.
        low_threshold (int): The lower gray scale threshold value.
        high_threshold (int): The upper gray scale threshold value.
        limit_area (int): The minimum area of the blob to be considered.

    Returns:
        bool: True if gray blobs above the threshold are found, False otherwise.
    """
    if len(image.shape) == 2:  # Grayscale image
        gray_image = image
    elif len(image.shape) == 3:  # Color image
        if image.shape[2] == 1:
            gray_image = image[:, :, 0]
        elif image.shape[2] == 3:
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif image.shape[2] == 4:
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        raise ValueError("Unsupported image format")

    binary_image = cv2.inRange(gray_image, low_threshold, high_threshold)
    
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        if cv2.contourArea(contour) >= limit_area:
            return True
            
    return False

def get_maxblob_rotatedrect(image:np.ndarray, low_threshold=0, high_threshold=255):
    """
    Finds the largest gray blob in an image and returns its rotated rectangle.

    Args:
        image (numpy.ndarray): The input image.
        low_threshold (int): The lower gray scale threshold value.
        high_threshold (int): The upper gray scale threshold value.

    Returns:
        tuple: The rotated rectangle of the largest gray blob, or None if no blobs found.
    """
    if len(image.shape) == 2:  # Grayscale image
        gray_image = image
    elif len(image.shape) == 3:  # Color image
        if image.shape[2] == 1:
            gray_image = image[:, :, 0]
        elif image.shape[2] == 3:
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif image.shape[2] == 4:
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        raise ValueError("Unsupported image format")

    binary_image = cv2.inRange(gray_image, low_threshold, high_threshold)
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    max_area = 0
    max_idx = -1
    max_rect = None
    idx = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > max_area:
            max_area = area
            max_idx = idx
        idx += 1
            # max_rect = cv2.minAreaRect(contour)
            
    if max_idx != -1:
        max_rect = cv2.minAreaRect(contours[max_idx])
    return max_rect

if __name__ == "__main__":
    # Example usage
    image = cv2.imread(r"C:\Users\lzh\Desktop\jiaokou\2025-05-28\20250528010821255.jpg", cv2.IMREAD_UNCHANGED)
    # ret = has_gray_scale(image, low_threshold=0, high_threshold=100)
    ret = get_maxblob_rotatedrect(image, low_threshold=0, high_threshold=100)
    if ret is not None:
        center, size, angle = ret if ret else (None, None, None)
        max_length = max(size)
        # points = cv2.boxPoints(ret)
        # points = np.int32(points)
        # cv2.drawContours(image, [points], 0, (0, 255, 0), 2)
        # cv2.imshow("Max Blob", image)
        # cv2.waitKey(0)
    print(f"Gray scale values above threshold found: {ret}")