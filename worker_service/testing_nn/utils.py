import cv2
import tempfile
import numpy as np
from ultralytics import YOLO
import logging
import os
from PIL import Image, ImageDraw
import io

logger = logging.getLogger(__name__)

def load_model(model_data):
    """Load the YOLO model from the specified data stream."""
    try:
        # Save the BytesIO object to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pt") as tmp_file:
            tmp_file.write(model_data.getvalue())
            tmp_file_path = tmp_file.name

        # Load the model from the temporary file
        model = YOLO(tmp_file_path)
        return model
    except Exception as e:
        logger.error(f"Error loading model from stream: {e}")
        raise
    finally:
        # Clean up the temporary file
        if tmp_file_path:
            try:
                os.unlink(tmp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")
                


def predict_and_detect(image_data, model, conf=0.5):
    """Perform detection on the given image using the specified model."""
    # Convert bytes to a NumPy array
    image_array = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

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



def draw_boxes_on_image(image_data, boxes):
    """
    Draw bounding boxes on the image.
    :param image_data: Binary image data.
    :param boxes: List of bounding boxes in the format [{'class': 'class_name', 'coordinates': [x1, y1, x2, y2]}, ...].
    :return: Annotated image in binary format.
    """
    # Open the image
    image = Image.open(io.BytesIO(image_data))
    draw = ImageDraw.Draw(image)

    # Draw each bounding box
    for box in boxes:
        # Extract coordinates from the dictionary
        x1, y1, x2, y2 = box['coordinates']
        # Draw the rectangle
        draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
        # Optionally, add the class label
        draw.text((x1, y1 - 10), box['class'], fill="red")

    # Save the annotated image to a byte stream
    byte_stream = io.BytesIO()
    image.save(byte_stream, format="PNG")
    byte_stream.seek(0)

    return byte_stream.getvalue()