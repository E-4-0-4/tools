# YOLOv8 Real-Time Object Detection with IP Camera

This project demonstrates **real-time object detection** using the [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) model with an **IP camera** stream.  
It balances **speed** and **accuracy** by using the `yolov8s.pt` model, frame skipping, and reduced image size.

---

## 📦 Features
- **YOLOv8 Small** model for a balance between speed & accuracy.
- **GPU support** (CUDA) if available.
- **Real-time IP camera streaming**.
- Adjustable **frame skipping** for faster inference.
- **FPS display** on video output.

---

## 📋 Requirements

- Python **3.8+**
- IP Camera or mobile camera streaming via **IP Webcam** app
- Packages:
  - ultralytics
  - opencv-python
  - torch
 
---

## ⚙️ Installation

1️⃣ **Clone this repository** (or copy the script):

```bash
git clone https://github.com/anonyTheCoder/tools
cd tools/objectIdentify
