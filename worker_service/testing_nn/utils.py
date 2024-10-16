import cv2
from ultralytics import YOLO

def load_model(model_path):
    """Load the YOLO model from the specified path."""
    return YOLO(model_path)

def predict_and_detect(image_path, model, conf=0.5):
    """Perform detection on the given image using the specified model."""
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Could not read the image")

    results = model.predict(image, conf=conf)
    boxes = []
    for result in results:
        for box in result.boxes:
            boxes.append({
                "class": result.names[int(box.cls[0])],
                "coordinates": box.xyxy[0].tolist()  # Convert to list for JSON serialization
            })
    return boxes
