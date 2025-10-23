

from ultralytics import YOLO
import cv2
import torch
import time

# ✅ Use YOLOv8 small for balance between speed & accuracy
model = YOLO("yolov8s.pt")

# ✅ GPU if available
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model.to(device)

# ✅ IP camera stream
url = "http://192.168.0.100:8080/video"
cap = cv2.VideoCapture(url)

if not cap.isOpened():
    raise IOError("Cannot open IP camera stream")

# Optional: Reduce resolution for speed
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# ✅ Only process every nth frame for speed
process_every_n_frames = 2  
frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    frame_count += 1

    # Skip frames to increase FPS
    if frame_count % process_every_n_frames != 0:
        continue

    start_time = time.time()

    results = model.predict(
        frame,
        imgsz=480,      # Lower resolution = faster
        conf=0.4,
        iou=0.45,
        device=device,
        verbose=False
    )

    annotated = results[0].plot()

    # FPS calculation
    fps = 1 / (time.time() - start_time)
    cv2.putText(annotated, f"FPS: {fps:.2f}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("YOLOv8 Fast IP Cam", annotated)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

