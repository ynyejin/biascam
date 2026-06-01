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
    # 이전 결과 파일 삭제
    old_files = [
        "output/fancam.mp4",
        "output/fancam_web.mp4",
        "output/analysis/energy_graph.png",
        "output/analysis/angle_graph.png",
        "output/analysis/trajectory_3d.png",
        "output/analysis/motion_report.txt",
        "output/faces/faces_meta.json",
        "selected_member.json",
    ]

    for path in old_files:
        if os.path.exists(path):
            os.remove(path)

    # 이전 후보 이미지 삭제
    for filename in os.listdir(FACE_DIR):
        file_path = os.path.join(FACE_DIR, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

    temp_video_path = "data/input/uploaded_video_temp.mp4"

    with open(temp_video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    os.replace(temp_video_path, CURRENT_VIDEO_PATH)

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

    # -----------------------------
    # 설정값
    # -----------------------------
    sample_count = 40
    MAX_RESULT_CARDS = 20

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

    # 앞뒤 10% 구간 제외하고 중간 80%에서 균등 샘플링
    start_idx = int(total_frames * 0.10)
    end_idx = int(total_frames * 0.90)

    if end_idx <= start_idx:
        start_idx = 0
        end_idx = total_frames - 1

    sample_indices = np.linspace(
        start_idx,
        end_idx,
        sample_count,
        dtype=int
    )

    sample_indices = set(int(idx) for idx in sample_indices)

    print("total_frames:", total_frames)
    print("sample_count:", len(sample_indices))
    print("sample_range:", start_idx, "~", end_idx)

    def crop_with_margin(image, x1, y1, x2, y2, margin_ratio=0.45):
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
        if face_crop is None or face_crop.size == 0:
            return 0.0

        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()

        return min(blur_value / 300.0, 1.0)

    def calc_face_score(face_crop, frame_w, frame_h, x1, y1, x2, y2, det_score):
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

        size_score = min(face_area_ratio * 120, 1.0)
        blur_score = calc_blur_score(face_crop)

        score = (
            float(det_score) * 0.45
            + size_score * 0.30
            + blur_score * 0.15
            + center_x_score * 0.07
            + center_y_score * 0.03
        )

        return score

    # -----------------------------
    # 1. 샘플 프레임마다 InsightFace 직접 탐지
    # -----------------------------
    while True:
        ret, frame = cap.read()

        if not ret:
            break

        if frame_idx not in sample_indices:
            frame_idx += 1
            continue

        frame_h, frame_w = frame.shape[:2]

        faces = face_analyzer.get(frame)

        if faces is None or len(faces) == 0:
            frame_idx += 1
            continue

        for face in faces:
            det_score = float(face.det_score)

            # 너무 신뢰도 낮은 얼굴 제외
            if det_score < 0.45:
                continue

            x1, y1, x2, y2 = face.bbox.astype(int)

            if x2 <= x1 or y2 <= y1:
                continue

            face_w = x2 - x1
            face_h = y2 - y1

            # 너무 작은 얼굴 제외
            face_area_ratio = (face_w * face_h) / (frame_w * frame_h)
            if face_area_ratio < 0.001:
                continue

            face_card_crop, crop_bbox = crop_with_margin(
                frame,
                x1,
                y1,
                x2,
                y2,
                margin_ratio=0.45
            )

            if face_card_crop is None or face_card_crop.size == 0:
                continue

            embedding = face.normed_embedding

            if embedding is None:
                continue

            embedding = np.array(embedding, dtype=np.float32)

            # NaN / inf 방지
            if not np.all(np.isfinite(embedding)):
                continue

            face_score = calc_face_score(
                face_crop=face_card_crop,
                frame_w=frame_w,
                frame_h=frame_h,
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                det_score=det_score
            )

            face_candidates.append({
                "frame_idx": int(frame_idx),
                "face_bbox": [int(x1), int(y1), int(x2), int(y2)],
                "person_bbox": [int(x1), int(y1), int(x2), int(y2)],  # 프론트 호환용
                "crop_bbox": [int(v) for v in crop_bbox],
                "crop": face_card_crop,
                "embedding": embedding,
                "score": float(face_score),
                "det_score": det_score
            })

        frame_idx += 1

    cap.release()

    if len(face_candidates) == 0:
        return {
            "message": "no face candidates detected",
            "count": 0,
            "faces": []
        }

    # 너무 많은 후보는 상위 점수만 사용
    face_candidates = sorted(
        face_candidates,
        key=lambda c: c["score"],
        reverse=True
    )

    face_candidates = face_candidates[:100]

    # -----------------------------
    # 2. 얼굴 임베딩 clustering
    # -----------------------------
    embeddings = np.array(
        [candidate["embedding"] for candidate in face_candidates],
        dtype=np.float32
    )

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

    valid_embeddings = np.nan_to_num(
        valid_embeddings,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    )

    norms = np.linalg.norm(valid_embeddings, axis=1, keepdims=True)
    valid_embeddings = valid_embeddings / np.maximum(norms, 1e-8)

    valid_embeddings = np.nan_to_num(
        valid_embeddings,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    ).astype(np.float64)

    face_candidates = [face_candidates[i] for i in valid_indices]

    # -----------------------------
    # 3. 동적 eps 재시도 기반 clustering
    # -----------------------------

    def cosine_distance(emb1, emb2):
        emb1 = np.array(emb1, dtype=np.float32)
        emb2 = np.array(emb2, dtype=np.float32)

        denom = np.linalg.norm(emb1) * np.linalg.norm(emb2)

        if denom == 0:
            return 1.0

        similarity = float(np.dot(emb1, emb2) / denom)
        return 1.0 - similarity


    def is_duplicate_cluster(candidate, selected_candidates, threshold):
        for selected in selected_candidates:
            dist = cosine_distance(candidate["embedding"], selected["embedding"])

            if dist < threshold:
                return True

        return False


    def build_selected_candidates(eps, merge_threshold):
        """
        eps와 merge_threshold 조합으로 clustering을 실행하고,
        cluster 대표 후보들을 만든 뒤,
        대표 후보끼리 한 번 더 병합해서 최종 후보를 반환한다.
        """
        clustering = DBSCAN(
            eps=eps,
            min_samples=1,
            metric="cosine"
        ).fit(valid_embeddings)

        labels = clustering.labels_

        clusters = {}
        noise_count = 0

        for idx, label in enumerate(labels):
            candidate = face_candidates[idx]
            label = int(label)

            if label == -1:
                noise_count += 1
                continue

            if label not in clusters:
                clusters[label] = []

            clusters[label].append(candidate)

        # cluster별 대표 후보 만들기
        cluster_representatives = []

        for label, members in clusters.items():
            best_candidate = max(
                members,
                key=lambda c: c["score"]
            )

            best_candidate["cluster_label"] = int(label)
            best_candidate["cluster_size"] = int(len(members))
            best_candidate["source_type"] = "cluster"

            cluster_representatives.append(best_candidate)

        # 점수 높은 후보부터 선택
        cluster_representatives = sorted(
            cluster_representatives,
            key=lambda c: c["score"],
            reverse=True
        )

        # cluster 대표 후보끼리 중복 제거
        selected = []

        for candidate in cluster_representatives:
            if is_duplicate_cluster(
                candidate,
                selected,
                threshold=merge_threshold
            ):
                continue

            selected.append(candidate)

        return {
            "eps": eps,
            "merge_threshold": merge_threshold,
            "selected_candidates": selected,
            "cluster_count": int(len(clusters)),
            "noise_count": int(noise_count),
            "final_count": int(len(selected))
        }


    # 여러 조합을 순서대로 시도
    # 위쪽은 강하게 묶는 설정, 아래쪽은 덜 묶는 설정
    clustering_trials = [
        {"eps": 0.65, "merge": 0.80},
        {"eps": 0.60, "merge": 0.75},
        {"eps": 0.55, "merge": 0.70},
        {"eps": 0.50, "merge": 0.65},
        {"eps": 0.45, "merge": 0.60},
        {"eps": 0.40, "merge": 0.55},
    ]

    # BiasCam은 보통 3명 이상 그룹 영상을 대상으로 하므로
    # final_count가 2 이하이면 너무 적게 묶인 것으로 보고 다음 설정을 시도한다.
    # 8명 그룹도 고려해서 상한은 넉넉하게 둔다.
    ACCEPT_MIN_COUNT = 3
    ACCEPT_MAX_COUNT = 12

    trial_results = []

    for trial in clustering_trials:
        result = build_selected_candidates(
            eps=trial["eps"],
            merge_threshold=trial["merge"]
        )

        trial_results.append(result)

        print(
            f"trial eps={result['eps']}, "
            f"merge={result['merge_threshold']}, "
            f"cluster_count={result['cluster_count']}, "
            f"final_count={result['final_count']}, "
            f"noise_count={result['noise_count']}"
        )

    # 모든 trial을 다 실행한 뒤 선택
    valid_results = [
        r for r in trial_results
        if ACCEPT_MIN_COUNT <= r["final_count"] <= ACCEPT_MAX_COUNT
    ]

    if len(valid_results) > 0:
        # 누락보다 중복이 덜 치명적이므로, 후보가 더 많이 나온 결과를 선택
        chosen_result = max(
            valid_results,
            key=lambda r: r["final_count"]
        )
    else:
        # 정상 범위가 없으면, 전체 중 가장 많이 나온 결과 선택
        chosen_result = max(
            trial_results,
            key=lambda r: r["final_count"]
        )

    selected_candidates = chosen_result["selected_candidates"]

    cluster_count = chosen_result["cluster_count"]
    noise_count = chosen_result["noise_count"]
    selected_eps = chosen_result["eps"]
    selected_merge_threshold = chosen_result["merge_threshold"]

    # 안전 상한
    MAX_RESULT_CARDS = 20
    selected_candidates = selected_candidates[:MAX_RESULT_CARDS]

    print("selected_eps:", selected_eps)
    print("selected_merge_threshold:", selected_merge_threshold)

    if len(selected_candidates) == 0:
        print("DEBUG: no selected candidates")
        print("raw_face_candidates:", int(len(face_candidates)))
        print("cluster_count:", int(cluster_count))
        print("noise_count:", int(noise_count))

        return {
            "message": "no clustered members detected",
            "count": 0,
            "raw_face_candidates": int(len(face_candidates)),
            "cluster_count": int(cluster_count),
            "noise_count": int(noise_count),
            "selected_eps": float(selected_eps),
            "selected_merge_threshold": float(selected_merge_threshold),
            "faces": []
        }

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
    print("cluster_count:", int(cluster_count))
    print("noise_count:", int(noise_count))
    print("final_faces_count:", int(len(faces_result)))

    import json

    faces_meta_path = os.path.join(FACE_DIR, "faces_meta.json")

    with open(faces_meta_path, "w", encoding="utf-8") as f:
        json.dump(faces_result, f, ensure_ascii=False, indent=2)

    print("faces_meta saved:", faces_meta_path)
    
    return {
        "message": "face candidates clustered",
        "count": int(len(faces_result)),
        "raw_face_candidates": int(len(face_candidates)),
        "cluster_count": int(cluster_count),
        "noise_count": int(noise_count),
        "selected_eps": float(selected_eps),
        "selected_merge_threshold": float(selected_merge_threshold),
        "faces": faces_result
    }


@app.get("/progress")
def get_progress():
    return process_status


@app.post("/process")
def process_video(request: ProcessRequest):
    try:
        print("PROCESS CALLED")
        print("selected face_id:", request.face_id)

        update_status(5, "Selected face received")

        # 이전 직캠/분석 결과 삭제
        # 새 직캠 생성에 실패했을 때 예전 결과가 화면에 뜨는 것을 방지
        old_process_outputs = [
            "output/fancam.mp4",
            "output/fancam_web.mp4",
            "output/analysis/energy_graph.png",
            "output/analysis/angle_graph.png",
            "output/analysis/trajectory_3d.png",
            "output/analysis/motion_report.txt",
        ]

        for path in old_process_outputs:
            if os.path.exists(path):
                os.remove(path)

        import json
        import time

        selected_member = None

        # detect_faces_from_video()를 다시 호출하지 않음.
        # 사용자가 실제로 봤던 후보 목록을 저장한 faces_meta.json을 읽음.
        faces_meta_path = os.path.join(FACE_DIR, "faces_meta.json")

        if not os.path.exists(faces_meta_path):
            raise Exception("faces_meta.json not found. Please run face detection first.")

        with open(faces_meta_path, "r", encoding="utf-8") as f:
            faces = json.load(f)

        for person in faces:
            if int(person["id"]) == int(request.face_id):
                selected_member = person
                break

        if selected_member is None:
            raise Exception("selected member not found")

        # face_match.py에서 읽을 선택 멤버 정보 저장
        with open("selected_member.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "id": int(selected_member["id"]),
                    "bbox": selected_member["bbox"],
                    "person_bbox": selected_member.get("person_bbox"),
                    "frame_idx": selected_member.get("frame_idx"),
                    "cluster_label": selected_member.get("cluster_label"),
                    "cluster_size": selected_member.get("cluster_size"),
                    "score": selected_member.get("score"),
                },
                f,
                ensure_ascii=False,
                indent=2
            )

        update_status(25, "Generating fancam")

        subprocess.run(
            ["python", "src/tracking/face_match.py"],
            check=True
        )

        print("DONE face_match.py")
        print("fancam exists:", os.path.exists("output/fancam.mp4"))
        print("fancam size:", os.path.getsize("output/fancam.mp4") if os.path.exists("output/fancam.mp4") else None)

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

        if not os.path.exists("output/fancam_web.mp4") or os.path.getsize("output/fancam_web.mp4") == 0:
            raise Exception("fancam_web.mp4 was not created or is empty")

        update_status(75, "Running motion analysis")

        subprocess.run(
            ["python", "src/analysis/analyze_motion.py"],
            check=True
        )

        update_status(100, "Complete", done=True)

        # 브라우저 캐시 방지용 timestamp
        timestamp = int(time.time())

        return {
            "message": "processing complete",
            "fancam_url": f"http://127.0.0.1:8000/output/fancam_web.mp4?t={timestamp}",
            "energy_graph": f"http://127.0.0.1:8000/output/analysis/energy_graph.png?t={timestamp}",
            "angle_graph": f"http://127.0.0.1:8000/output/analysis/angle_graph.png?t={timestamp}",
            "trajectory_graph": f"http://127.0.0.1:8000/output/analysis/trajectory_3d.png?t={timestamp}",
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