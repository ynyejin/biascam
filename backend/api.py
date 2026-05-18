from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import shutil
import os
import subprocess

app = FastAPI()

# CORS 허용 (frontend 연결용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 폴더 생성
os.makedirs("data/input", exist_ok=True)
os.makedirs("output", exist_ok=True)

# 결과 파일 접근 가능하게
app.mount("/output", StaticFiles(directory="output"), name="output")


@app.get("/")
def root():
    return {"message": "BiasCam API running"}


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):

    video_path = f"data/input/{file.filename}"

    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "message": "upload success",
        "video_path": video_path
    }


@app.post("/process")
async def process_video():

    # 기존 OpenCV 코드 실행
    subprocess.run(
        ["python", "src/tracking/face_match.py"],
        check=True
    )

    subprocess.run(
        ["python", "src/analysis/analyze_motion.py"],
        check=True
    )

    return {
        "message": "processing complete",
        "fancam_url": "http://127.0.0.1:8000/output/fancam.mp4",
        "energy_graph": "http://127.0.0.1:8000/output/analysis/energy_graph.png",
        "angle_graph": "http://127.0.0.1:8000/output/analysis/angle_graph.png",
        "trajectory_graph": "http://127.0.0.1:8000/output/analysis/trajectory_3d.png",
    }