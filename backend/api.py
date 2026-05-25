from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from ultralytics import YOLO
from collections import Counter
from sklearn.cluster import DBSCAN
from insightface.app import FaceAnalysis

import os
import shutil
import cv2
import subprocess
import mediapipe as mp
import numpy as np

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

yolo_model = YOLO("yolov8n.pt")

# face_app = FaceAnalysis(
#     name="buffalo_l",
#     providers=["CPUExecutionProvider"]
# )
# face_app.prepare(ctx_id=-1, det_size=(640, 640))
face_app = None

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

def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def expand_bbox(x, y, w, h, frame_w, frame_h, margin_x_ratio=0.18, margin_y_ratio=0.10):
    margin_x = int(w * margin_x_ratio)
    margin_y = int(h * margin_y_ratio)

    x1 = clamp(x - margin_x, 0, frame_w - 1)
    y1 = clamp(y - margin_y, 0, frame_h - 1)
    x2 = clamp(x + w + margin_x, 0, frame_w)
    y2 = clamp(y + h + margin_y, 0, frame_h)

    return x1, y1, x2, y2


def get_face_app():
    global face_app

    if face_app is None:
        print("Loading InsightFace model...")

        face_app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )

        # 속도 개선: 640x640 대신 320x320 사용
        face_app.prepare(ctx_id=-1, det_size=(320, 320))

        print("InsightFace model loaded.")

    return face_app



def score_person_crop(x, y, w, h, frame_w, frame_h, conf):
    """
    멤버 선택 카드에 쓰기 좋은 사람 crop을 고르기 위한 점수.
    - confidence가 높을수록 좋음
    - 너무 작지 않을수록 좋음
    - 화면 중앙에 가까울수록 좋음
    """
    area_ratio = (w * h) / (frame_w * frame_h)

    cx = x + w / 2
    cy = y + h / 2

    center_x_score = 1.0 - abs(cx - frame_w / 2) / (frame_w / 2)
    center_y_score = 1.0 - abs(cy - frame_h / 2) / (frame_h / 2)

    center_x_score = max(0.0, center_x_score)
    center_y_score = max(0.0, center_y_score)

    size_score = min(area_ratio * 12, 1.0)

    score = (
        conf * 0.45
        + size_score * 0.35
        + center_x_score * 0.10
        + center_y_score * 0.10
    )

    return score

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
    face_analyzer = get_face_app()

    # 이전 후보 이미지 삭제
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

    # max_scan_frames = 300
    # frame_skip = 10

    # # 너무 많이 보여주면 UI가 지저분해져서 상한 설정
    # MAX_RESULT_CARDS = 12

    # face_candidates = []
    # frame_idx = 0
    # 영상 전체에서 균등하게 샘플링할 프레임 개수

    sample_count = 30

    # 너무 많이 보여주면 UI가 지저분해져서 상한 설정
    MAX_RESULT_CARDS = 12

    face_candidates = []
    frame_idx = 0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total_frames <= 0:
        cap.release()
        return {
            "message": "invalid video frame count",
            "count": 0,
            "faces": []
        }

    # 영상 전체 구간에서 sample_count개 프레임을 균등하게 선택
    sample_indices = np.linspace(
        0,
        total_frames - 1,
        sample_count,
        dtype=int
    )

    sample_indices = set(int(idx) for idx in sample_indices)

    print("total_frames:", total_frames)
    print("sample_count:", len(sample_indices))

    def crop_with_margin(image, x1, y1, x2, y2, margin_ratio=0.35):
        h, w = image.shape[:2]

        box_w = x2 - x1
        box_h = y2 - y1

        mx = int(box_w * margin_ratio)
        my = int(box_h * margin_ratio)

        nx1 = max(0, x1 - mx)
        ny1 = max(0, y1 - my)
        nx2 = min(w, x2 + mx)
        ny2 = min(h, y2 + my)

        return image[ny1:ny2, nx1:nx2], [nx1, ny1, nx2, ny2]

    def calc_blur_score(face_crop):
        """
        얼굴이 너무 흐린 후보를 낮게 평가하기 위한 점수.
        """
        if face_crop is None or face_crop.size == 0:
            return 0.0

        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()

        # 너무 큰 값 방지용 normalize
        return min(blur_value / 300.0, 1.0)

    def calc_face_score(face, face_crop, frame_w, frame_h):
        """
        후보 카드로 쓰기 좋은 얼굴인지 평가.
        기준:
        - 얼굴 detection confidence
        - 얼굴 크기
        - 화면 중앙성
        - 선명도
        """
        x1, y1, x2, y2 = face.bbox.astype(int)

        face_w = x2 - x1
        face_h = y2 - y1

        if face_w <= 0 or face_h <= 0:
            return 0.0

        face_area_ratio = (face_w * face_h) / (frame_w * frame_h)

        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

        center_x_score = 1.0 - abs(cx - frame_w / 2) / (frame_w / 2)
        center_y_score = 1.0 - abs(cy - frame_h / 2) / (frame_h / 2)

        center_x_score = max(0.0, center_x_score)
        center_y_score = max(0.0, center_y_score)

        size_score = min(face_area_ratio * 80, 1.0)
        blur_score = calc_blur_score(face_crop)

        det_score = float(face.det_score)

        score = (
            det_score * 0.40
            + size_score * 0.30
            + blur_score * 0.15
            + center_x_score * 0.10
            + center_y_score * 0.05
        )

        return score

    # while frame_idx < max_scan_frames:
    #     ret, frame = cap.read()

    #     if not ret:
    #         break

    #     frame_idx += 1

    #     if frame_idx % frame_skip != 0:
    #         continue

    #     frame_h, frame_w = frame.shape[:2]

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        if frame_idx not in sample_indices:
            frame_idx += 1
            continue

        frame_h, frame_w = frame.shape[:2]

        # 1. YOLO로 사람 후보 탐지
        results = yolo_model(
            frame,
            verbose=False
        )

        people = []

        for result in results:
            boxes = result.boxes

            if boxes is None:
                continue

            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])

                # COCO class 0 = person
                if cls_id != 0:
                    continue

                if conf < 0.30:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                x1 = int(x1)
                y1 = int(y1)
                x2 = int(x2)
                y2 = int(y2)

                if x2 <= x1 or y2 <= y1:
                    continue

                person_w = x2 - x1
                person_h = y2 - y1

                area_ratio = (person_w * person_h) / (frame_w * frame_h)

                # 너무 작은 사람 후보 제거
                if area_ratio < 0.004:
                    continue

                people.append({
                    "bbox": [x1, y1, x2, y2],
                    "score": conf
                })

        # 2. 각 person crop 안에서 얼굴 탐지 + 임베딩 추출
        for person in people:
            px1, py1, px2, py2 = person["bbox"]

            person_crop = frame[py1:py2, px1:px2]

            if person_crop.size == 0:
                continue

            faces = face_analyzer.get(person_crop)

            if faces is None or len(faces) == 0:
                continue

            # 한 person crop 안에서 가장 큰 얼굴만 사용
            faces = sorted(
                faces,
                key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
                reverse=True
            )

            face = faces[0]

            fx1, fy1, fx2, fy2 = face.bbox.astype(int)

            face_w = fx2 - fx1
            face_h = fy2 - fy1

            if face_w <= 0 or face_h <= 0:
                continue

            # 얼굴이 너무 작은 경우 제외
            person_crop_h, person_crop_w = person_crop.shape[:2]
            face_area_ratio_in_person = (face_w * face_h) / (person_crop_w * person_crop_h)

            if face_area_ratio_in_person < 0.015:
                continue

            # person crop 좌표계의 face bbox를 원본 frame 좌표계로 변환
            abs_fx1 = int(px1 + fx1)
            abs_fy1 = int(py1 + fy1)
            abs_fx2 = int(px1 + fx2)
            abs_fy2 = int(py1 + fy2)

            face_card_crop, crop_bbox = crop_with_margin(
                frame,
                abs_fx1,
                abs_fy1,
                abs_fx2,
                abs_fy2,
                margin_ratio=0.45
            )

            if face_card_crop.size == 0:
                continue

            embedding = face.normed_embedding

            if embedding is None:
                continue

            embedding = np.array(embedding, dtype=np.float32)

            # NaN / inf embedding 방지
            if not np.all(np.isfinite(embedding)):
                continue

            face_score = calc_face_score(
                face=face,
                face_crop=face_card_crop,
                frame_w=frame_w,
                frame_h=frame_h
            )

            face_candidates.append({
                "frame_idx": int(frame_idx),
                "person_bbox": [int(v) for v in person["bbox"]],
                "face_bbox": [int(abs_fx1), int(abs_fy1), int(abs_fx2), int(abs_fy2)],
                "crop_bbox": [int(v) for v in crop_bbox],
                "crop": face_card_crop,
                "embedding": embedding,
                "score": float(face_score),
                "det_score": float(face.det_score)
            })

        # 실제로 분석한 프레임도 인덱스 증가
        frame_idx += 1

    cap.release()

    if len(face_candidates) == 0:
        return {
            "message": "no face candidates detected",
            "count": 0,
            "faces": []
        }

    # 점수순으로 너무 많은 후보를 줄여서 clustering 부담 감소
    face_candidates = sorted(
        face_candidates,
        key=lambda c: c["score"],
        reverse=True
    )

    # 너무 많은 프레임에서 얼굴이 잡히면 clustering이 느려질 수 있으므로 상위 후보만 사용
    face_candidates = face_candidates[:80]

    # 3. 얼굴 임베딩 clustering
    embeddings = np.array(
        [candidate["embedding"] for candidate in face_candidates],
        dtype=np.float32
    )

    # NaN / inf 방지
    valid_indices = []
    valid_embeddings = []

    for i, emb in enumerate(embeddings):
        if np.all(np.isfinite(emb)):
            valid_indices.append(i)
            valid_embeddings.append(emb)

    if len(valid_embeddings) == 0:
        return {
            "message": "no valid face embeddings",
            "count": 0,
            "faces": []
        }

    valid_embeddings = np.array(valid_embeddings, dtype=np.float32)
    face_candidates = [face_candidates[i] for i in valid_indices]

    clustering = DBSCAN(
        eps=0.28,
        min_samples=2,
        metric="cosine"
    ).fit(valid_embeddings)

    labels = clustering.labels_

    clusters = {}
    noise_candidates = []

    for idx, label in enumerate(labels):
        candidate = face_candidates[idx]

        label = int(label)

        if label == -1:
            noise_candidates.append(candidate)
            continue

        if label not in clusters:
            clusters[label] = []

        clusters[label].append(candidate)

    # selected_candidates = []

    # # 4. cluster별 best crop 선택
    # for label, members in clusters.items():
    #     best_candidate = max(
    #         members,
    #         key=lambda c: c["score"]
    #     )

    #     best_candidate["cluster_label"] = int(label)
    #     best_candidate["cluster_size"] = int(len(members))

    #     selected_candidates.append(best_candidate)

    # # 5. noise 후보도 보조 후보로 추가
    # # 중요: 이 루프는 cluster 루프 밖에 있어야 함
    # noise_candidates = sorted(
    #     noise_candidates,
    #     key=lambda c: c["score"],
    #     reverse=True
    # )

    # for candidate in noise_candidates:
    #     candidate["cluster_label"] = -1
    #     candidate["cluster_size"] = 1
    #     selected_candidates.append(candidate)

    #     if len(selected_candidates) >= MAX_RESULT_CARDS:
    #         break

    # # cluster가 하나도 없고 noise만 있는 경우도 대비
    # if len(selected_candidates) == 0:
    #     selected_candidates = noise_candidates[:MAX_RESULT_CARDS]

    #     for candidate in selected_candidates:
    #         candidate["cluster_label"] = -1
    #         candidate["cluster_size"] = 1

    # # 점수순 정렬 후 최대 카드 수 제한
    # selected_candidates = sorted(
    #     selected_candidates,
    #     key=lambda c: c["score"],
    #     reverse=True
    # )

    # selected_candidates = selected_candidates[:MAX_RESULT_CARDS]

    def cosine_distance(emb1, emb2):
        """
        InsightFace normed_embedding 기준 cosine distance 계산.
        값이 작을수록 같은 사람일 가능성이 높음.
        """
        emb1 = np.array(emb1, dtype=np.float32)
        emb2 = np.array(emb2, dtype=np.float32)

        denom = np.linalg.norm(emb1) * np.linalg.norm(emb2)

        if denom == 0:
            return 1.0

        similarity = float(np.dot(emb1, emb2) / denom)
        distance = 1.0 - similarity

        return distance


    def is_duplicate_candidate(candidate, selected_candidates, threshold=0.32):
        """
        이미 선택된 후보들과 얼굴 임베딩이 너무 비슷하면 중복으로 판단.
        threshold가 작을수록 엄격하게 다른 사람으로 봄.
        threshold가 클수록 같은 사람으로 더 많이 묶음.
        """
        for selected in selected_candidates:
            dist = cosine_distance(candidate["embedding"], selected["embedding"])

            if dist < threshold:
                return True

        return False


    # -----------------------------
    # 4. cluster별 best crop 후보 만들기
    # -----------------------------
    cluster_best_candidates = []

    for label, members in clusters.items():
        best_candidate = max(
            members,
            key=lambda c: c["score"]
        )

        best_candidate["cluster_label"] = int(label)
        best_candidate["cluster_size"] = int(len(members))

        cluster_best_candidates.append(best_candidate)


    # cluster 대표 후보는 점수순 정렬
    cluster_best_candidates = sorted(
        cluster_best_candidates,
        key=lambda c: c["score"],
        reverse=True
    )


    # -----------------------------
    # 5. noise 후보도 보조 후보로 준비
    # -----------------------------
    noise_candidates = sorted(
        noise_candidates,
        key=lambda c: c["score"],
        reverse=True
    )

    for candidate in noise_candidates:
        candidate["cluster_label"] = -1
        candidate["cluster_size"] = 1


    # -----------------------------
    # 6. cluster 후보 + noise 후보를 합친 뒤 최종 중복 제거
    # -----------------------------
    candidate_pool = cluster_best_candidates + noise_candidates

    selected_candidates = []

    DUPLICATE_DISTANCE_THRESHOLD = 0.44

    for candidate in candidate_pool:
        if is_duplicate_candidate(
            candidate,
            selected_candidates,
            threshold=DUPLICATE_DISTANCE_THRESHOLD
        ):
            continue

        selected_candidates.append(candidate)

        if len(selected_candidates) >= MAX_RESULT_CARDS:
            break


    # 그래도 아무 후보도 없으면 점수 높은 noise라도 사용
    if len(selected_candidates) == 0:
        selected_candidates = noise_candidates[:MAX_RESULT_CARDS]


    # 최종 점수순 정렬
    selected_candidates = sorted(
        selected_candidates,
        key=lambda c: c["score"],
        reverse=True
    )

    selected_candidates = selected_candidates[:MAX_RESULT_CARDS]

    faces_result = []

    for idx, candidate in enumerate(selected_candidates):
        face_filename = f"face_{idx}.jpg"
        face_path = os.path.join(FACE_DIR, face_filename)

        cv2.imwrite(face_path, candidate["crop"])

        faces_result.append({
            "id": int(idx),
            "image_url": f"http://127.0.0.1:8000/output/faces/{face_filename}",
            "bbox": [int(v) for v in candidate["face_bbox"]],
            "person_bbox": [int(v) for v in candidate["person_bbox"]],
            "score": float(round(float(candidate["score"]), 4)),
            "det_score": float(round(float(candidate["det_score"]), 4)),
            "frame_idx": int(candidate["frame_idx"]),
            "cluster_label": int(candidate["cluster_label"]),
            "cluster_size": int(candidate["cluster_size"])
        })

    print("raw_face_candidates:", int(len(face_candidates)))
    print("cluster_count:", int(len(clusters)))
    print("noise_count:", int(len(noise_candidates)))
    print("final_faces_count:", int(len(faces_result)))

    return {
        "message": "face candidates clustered",
        "count": int(len(faces_result)),
        "raw_face_candidates": int(len(face_candidates)),
        "cluster_count": int(len(clusters)),
        "noise_count": int(len(noise_candidates)),
        "faces": faces_result
    }


@app.get("/progress")
def get_progress():
    return process_status


@app.post("/process")
def process_video(request: ProcessRequest):
    try:
        update_status(5, "Selected face received")

        selected_member = None

        detect_result = detect_faces_from_video()

        for person in detect_result["faces"]:
            if person["id"] == request.face_id:
                selected_member = person
                break

        if selected_member is None:
            raise Exception("selected member not found")

        import json

        with open("selected_member.json", "w") as f:
            json.dump(
                {
                    "id": selected_member["id"],
                    "bbox": selected_member["bbox"]
                },
                f
            )

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
    
@app.get("/analysis-results")
def get_analysis_results():
    report_path = "output/analysis/motion_report.txt"

    report_text = ""

    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            report_text = f.read()

    return {
        "message": "analysis results",
        "energy_graph": "http://127.0.0.1:8000/output/analysis/energy_graph.png",
        "angle_graph": "http://127.0.0.1:8000/output/analysis/angle_graph.png",
        "trajectory_graph": "http://127.0.0.1:8000/output/analysis/trajectory_3d.png",
        "report": report_text
    }

@app.get("/analysis-data")
def get_analysis_data():
    import csv

    energy_data = []
    angle_data = []
    trajectory_data = []

    with open("output/analysis/energy_data.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            energy_data.append({
                "time": float(row["time"]),
                "upper_energy": float(row["upper_energy"]),
                "lower_energy": float(row["lower_energy"]),
                "total_energy": float(row["total_energy"]),
            })

    with open("output/analysis/angle_data.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            angle_data.append({
                "time": float(row["time"]),
                "joint": row["joint"],
                "angle": float(row["angle"]),
            })

    with open("output/analysis/pose_data.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["joint"] in ["left_wrist", "right_wrist", "left_ankle", "right_ankle"]:
                trajectory_data.append({
                    "time": float(row["time"]),
                    "joint": row["joint"],
                    "x": float(row["x"]),
                    "y": float(row["y"]),
                    "z": float(row["z"]),
                })

    return {
        "energy_data": energy_data,
        "angle_data": angle_data,
        "trajectory_data": trajectory_data,
    }