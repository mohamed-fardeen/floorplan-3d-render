import os
import cv2
import numpy as np

def create_side_by_side_comparison(image_paths, output_path, max_height=800):
    """
    Concatenate a list of images side by side.
    Resizes them to have the same height.
    """
    images = []
    for path in image_paths:
        if path and os.path.exists(path):
            img = cv2.imread(path)
            if img is not None:
                images.append(img)
                
    if not images:
        return False
        
    # Resize to uniform height
    resized_images = []
    for img in images:
        h, w = img.shape[:2]
        if h != max_height:
            scale = max_height / h
            new_w = int(w * scale)
            resized = cv2.resize(img, (new_w, max_height), interpolation=cv2.INTER_AREA)
        else:
            resized = img
        resized_images.append(resized)
        
    # Concatenate horizontally
    combined = np.hstack(resized_images)
    
    cv2.imwrite(output_path, combined)
    return True
