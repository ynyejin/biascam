from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import os
import shutil
import cv2
import subprocess
import mediapipe as mp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INPUT_DIR = "data/input"
OUTPUT_DIR = "output"
FACE_DIR = "output/faces"

CURRENT_VIDEO_PATH = "data/input/uploaded_video.mp4"

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FACE_DIR, exist_ok=True)

app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

mp_face_detection = mp.solutions.face_detection

process_status = {
    "progress": 0,
    "message": "Waiting",
    "done": False,
    "error": None
}

def update_status(progress, message, done=False, error=None):
    process_status["progress"] = progress
    process_status["message"] = message
    process_status["done"] = done
    process_status["error"] = error

class ProcessRequest(BaseModel):
    face_id: int

@app.get("/")
def root():
    return {"message": "BiasCam API running"}


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    with open(CURRENT_VIDEO_PATH, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "message": "upload success",
        "video_path": CURRENT_VIDEO_PATH
    }


@app.post("/detect-faces")
def detect_faces_from_video():
    # 이전 얼굴 이미지 삭제
    for filename in os.listdir(FACE_DIR):
        file_path = os.path.join(FACE_DIR, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

    cap = cv2.VideoCapture(CURRENT_VIDEO_PATH)

    if not cap.isOpened():
        return {
            "message": "video open failed",
            "faces": []
        }

    faces_result = []
    frame_idx = 0
    max_scan_frames = 300  # 앞부분 약 3초 정도 탐색
    selected_frame = None
    selected_faces = []

    with mp_face_detection.FaceDetection(
        model_selection=1,
        min_detection_confidence=0.35
    ) as face_detection:

        while frame_idx < max_scan_frames:
            ret, frame = cap.read()

            if not ret:
                break

            frame_idx += 1

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb)

            if not results.detections:
                continue

            h, w, _ = frame.shape
            faces = []

            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box

                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                bw = int(bbox.width * w)
                bh = int(bbox.height * h)

                x = max(0, x)
                y = max(0, y)
                bw = min(w - x, bw)
                bh = min(h - y, bh)

                if bw <= 0 or bh <= 0:
                    continue

                faces.append({
                    "bbox": [x, y, bw, bh],
                    "score": float(detection.score[0])
                })

            # 얼굴이 가장 많이 잡힌 프레임 사용
            if len(faces) > len(selected_faces):
                selected_faces = faces
                selected_frame = frame.copy()

    cap.release()

    if selected_frame is None or len(selected_faces) == 0:
        return {
            "message": "no faces detected",
            "faces": []
        }

    h, w, _ = selected_frame.shape

    for idx, face in enumerate(selected_faces):
        x, y, bw, bh = face["bbox"]

        margin = 0.6
        mx = int(bw * margin)
        my = int(bh * margin)

        x1 = max(0, x - mx)
        y1 = max(0, y - my)
        x2 = min(w, x + bw + mx)
        y2 = min(h, y + bh + my)

        face_crop = selected_frame[y1:y2, x1:x2]

        face_filename = f"face_{idx}.jpg"
        face_path = os.path.join(FACE_DIR, face_filename)

        cv2.imwrite(face_path, face_crop)

        faces_result.append({
            "id": idx,
            "image_url": f"http://127.0.0.1:8000/output/faces/{face_filename}",
            "bbox": face["bbox"],
            "score": face["score"]
        })

    return {
        "message": "faces detected",
        "count": len(faces_result),
        "faces": faces_result
    }


@app.get("/progress")
def get_progress():
    return process_status


@app.post("/process")
def process_video(request: ProcessRequest):
    try:
        update_status(5, "Selected face received")

        selected_face_id = request.face_id

        with open("selected_face.txt", "w") as f:
            f.write(str(selected_face_id))

        update_status(25, "Generating fancam")

        subprocess.run(
            ["python", "src/tracking/face_match.py"],
            check=True
        )

        update_status(55, "Converting video for web playback")

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", "output/fancam.mp4",
                "-vcodec", "libx264",
                "-pix_fmt", "yuv420p",
                "output/fancam_web.mp4"
            ],
            check=True
        )

        update_status(75, "Running motion analysis")

        subprocess.run(
            ["python", "src/analysis/analyze_motion.py"],
            check=True
        )

        update_status(100, "Complete", done=True)

        return {
            "message": "processing complete",
            "fancam_url": "http://127.0.0.1:8000/output/fancam_web.mp4",
            "energy_graph": "http://127.0.0.1:8000/output/analysis/energy_graph.png",
            "angle_graph": "http://127.0.0.1:8000/output/analysis/angle_graph.png",
            "trajectory_graph": "http://127.0.0.1:8000/output/analysis/trajectory_3d.png",
        }

    except Exception as e:
        update_status(100, "Processing failed", done=True, error=str(e))
        return {
            "message": "processing failed",
            "error": str(e)
        }