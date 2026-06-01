import os
import cv2
import mediapipe as mp
import numpy as np
import json
from collections import deque
from insightface.app import FaceAnalysis

VIDEO_PATH = "data/input/uploaded_video.mp4"
OUTPUT_FANCAM_PATH = "output/fancam.mp4"

DISPLAY_SCALE = 0.7
SIMILARITY_THRESHOLD = 0.35
HISTORY_SIZE = 8
MAX_LOST_FRAMES = 12

FANCAM_SIZE = (720, 1280)  # width, height
BBOX_SMOOTH_ALPHA = 0.13
CROP_SMOOTH_ALPHA = 0.06
EMBEDDING_UPDATE_ALPHA = 0.02

mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh

clicked_bbox = None
clicked_done = False

os.makedirs("output", exist_ok=True)

face_recognizer = None

def get_face_recognizer():
    global face_recognizer

    if face_recognizer is None:
        print("Loading InsightFace for tracking...")

        face_recognizer = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )

        face_recognizer.prepare(ctx_id=-1, det_size=(320, 320))

        print("InsightFace tracking model loaded.")

    return face_recognizer


def cosine_similarity(a, b):
    a = np.array(a, dtype=np.float32).flatten()
    b = np.array(b, dtype=np.float32).flatten()

    if a.size == 0 or b.size == 0:
        return -1.0

    if a.shape[0] != b.shape[0]:
        min_len = min(a.shape[0], b.shape[0])
        a = a[:min_len]
        b = b[:min_len]

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return -1.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def xyxy_to_xywh(bbox):
    x1, y1, x2, y2 = bbox

    return (
        int(x1),
        int(y1),
        int(x2 - x1),
        int(y2 - y1)
    )


def scale_bbox_to_original(bbox, scale):
    x, y, w, h = bbox
    return (
        int(x / scale),
        int(y / scale),
        int(w / scale),
        int(h / scale)
    )


def crop_face(image, bbox, margin=0.8):
    h, w, _ = image.shape
    x, y, bw, bh = bbox

    mx = int(bw * margin * 1.2)
    my_top = int(bh * margin * 1.2)
    my_bottom = int(bh * margin * 0.7)

    x1 = max(0, x - mx)
    y1 = max(0, y - my_top)
    x2 = min(w, x + bw + mx)
    y2 = min(h, y + bh + my_bottom)

    return image[y1:y2, x1:x2]


def make_fancam_crop(frame, bbox, output_size=FANCAM_SIZE, padding=8.0):
    frame_h, frame_w, _ = frame.shape
    x, y, w, h = bbox

    cx = x + w / 2
    cy = y + h / 2

    crop_h = int(h * padding)
    crop_w = int(crop_h * output_size[0] / output_size[1])

    # 얼굴보다 아래쪽, 즉 상반신/전신 쪽을 더 포함
    cy = cy + h * 3.0

    x1 = int(cx - crop_w / 2)
    y1 = int(cy - crop_h / 2)

    # 여기서 프레임 안으로 clamp하지 말 것
    # 프레임 밖으로 나간 부분은 crop_frame_with_padding()이 처리함
    return None, (x1, y1, crop_w, crop_h)


def get_face_embedding(face_img, face_mesh):
    if face_img is None or face_img.size == 0:
        return None

    face_img = cv2.resize(face_img, (192, 192))
    rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if not results.multi_face_landmarks:
        return None

    landmarks = results.multi_face_landmarks[0].landmark

    points = np.array(
        [[lm.x, lm.y, lm.z] for lm in landmarks],
        dtype=np.float32
    )

    center = np.mean(points, axis=0)
    points = points - center

    scale = np.linalg.norm(points)

    if scale == 0:
        return None

    points = points / scale
    return points.flatten()


def update_reference_embedding(old_embedding, new_embedding, alpha=EMBEDDING_UPDATE_ALPHA):
    updated = (1 - alpha) * old_embedding + alpha * new_embedding
    norm = np.linalg.norm(updated)

    if norm == 0:
        return old_embedding

    return updated / norm


def detect_faces(frame, face_detection):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_detection.process(rgb)

    h, w, _ = frame.shape
    faces = []

    if not results.detections:
        return faces

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
            "bbox": (x, y, bw, bh),
            "score": float(detection.score[0])
        })

    return faces


def bbox_center(bbox):
    x, y, w, h = bbox
    return np.array([x + w / 2, y + h / 2])


def smooth_bbox(prev_bbox, new_bbox, alpha=BBOX_SMOOTH_ALPHA):
    if prev_bbox is None:
        return new_bbox

    px, py, pw, ph = prev_bbox
    nx, ny, nw, nh = new_bbox

    x = int(px * (1 - alpha) + nx * alpha)
    y = int(py * (1 - alpha) + ny * alpha)
    w = int(pw * (1 - alpha) + nw * alpha)
    h = int(ph * (1 - alpha) + nh * alpha)

    return (x, y, w, h)


def smooth_crop_bbox(prev_bbox, new_bbox, alpha=CROP_SMOOTH_ALPHA):
    if prev_bbox is None:
        return new_bbox

    px, py, pw, ph = prev_bbox
    nx, ny, nw, nh = new_bbox

    x = int(px * (1 - alpha) + nx * alpha)
    y = int(py * (1 - alpha) + ny * alpha)
    w = int(pw * (1 - alpha) + nw * alpha)
    h = int(ph * (1 - alpha) + nh * alpha)

    return (x, y, w, h)


def point_inside_bbox(px, py, bbox):
    x, y, w, h = bbox
    return x <= px <= x + w and y <= py <= y + h


def mouse_callback(event, x, y, flags, param):
    global clicked_bbox, clicked_done

    if event == cv2.EVENT_LBUTTONDOWN:
        faces = param["faces"]

        for face in faces:
            bbox = face["bbox"]

            if point_inside_bbox(x, y, bbox):
                clicked_bbox = bbox
                clicked_done = True
                print(f"선택된 얼굴 bbox: {clicked_bbox}")
                break


def select_target_face(cap, face_recognizer):
    selected_file = "selected_member.json"

    if not os.path.exists(selected_file):
        print("selected_member.json 없음")
        return None, None

    with open(selected_file, "r", encoding="utf-8") as f:
        selected = json.load(f)

    selected_id = int(selected["id"])

    # 사용자가 실제로 선택한 후보 이미지
    selected_face_path = f"output/faces/face_{selected_id}.jpg"

    if not os.path.exists(selected_face_path):
        print("선택한 후보 이미지 없음:", selected_face_path)
        return None, None

    selected_img = cv2.imread(selected_face_path)

    if selected_img is None or selected_img.size == 0:
        print("선택한 후보 이미지 읽기 실패")
        return None, None

    faces = face_recognizer.get(selected_img)

    if faces is None or len(faces) == 0:
        print("선택한 후보 이미지에서 InsightFace embedding 추출 실패")
        return None, None

    # 후보 이미지 안에서 가장 큰 얼굴 사용
    face = max(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
    )

    reference_embedding = np.array(face.normed_embedding, dtype=np.float32)

    if reference_embedding is None or reference_embedding.size == 0:
        print("reference embedding 없음")
        return None, None

    # selected_member.json의 bbox는 [x1, y1, x2, y2]
    raw_bbox = selected["bbox"]
    selected_bbox = xyxy_to_xywh(raw_bbox)

    print("selected id:", selected_id)
    print("selected face image:", selected_face_path)
    print("selected bbox:", selected_bbox)

    return selected_bbox, reference_embedding


def detect_faces_with_insightface(frame, face_recognizer, min_det_score=0.30):
    faces = face_recognizer.get(frame)

    results = []

    if faces is None or len(faces) == 0:
        return results

    for face in faces:
        det_score = float(face.det_score)

        if det_score < min_det_score:
            continue

        x1, y1, x2, y2 = face.bbox.astype(int)

        if x2 <= x1 or y2 <= y1:
            continue

        embedding = face.normed_embedding

        if embedding is None:
            continue

        embedding = np.array(embedding, dtype=np.float32)

        if not np.all(np.isfinite(embedding)):
            continue

        bbox = (
            int(x1),
            int(y1),
            int(x2 - x1),
            int(y2 - y1)
        )

        results.append({
            "bbox_original": bbox,
            "embedding": embedding,
            "det_score": det_score
        })

    return results


def run_face_matching(video_path):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("영상을 열 수 없습니다.")
        return

    original_fps = cap.get(cv2.CAP_PROP_FPS)
    if original_fps == 0:
        original_fps = 30

    last_bbox = None
    lost_frames = 0
    similarity_history = deque(maxlen=HISTORY_SIZE)

    face_recognizer = get_face_recognizer()

    selected_bbox, reference_embedding = select_target_face(
        cap,
        face_recognizer
    )

    if selected_bbox is None or reference_embedding is None:
        cap.release()
        cv2.destroyAllWindows()
        return

    # 선택 과정에서 지나간 프레임을 다시 처음부터 처리
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    last_bbox = None
    fancam_writer = None
    crop_bbox = None

    while True:
        ret, frame_original = cap.read()

        if not ret:
            break

        frame_display = cv2.resize(
            frame_original,
            None,
            fx=DISPLAY_SCALE,
            fy=DISPLAY_SCALE
        )

        faces = detect_faces_with_insightface(
            frame_original,
            face_recognizer,
            min_det_score=0.30
        )

        candidates = []

        for face in faces:
            bbox_original = face["bbox_original"]
            embedding = face["embedding"]

            if embedding is None:
                continue

            similarity = cosine_similarity(reference_embedding, embedding)

            distance_bonus = 0.0

            if last_bbox is not None:
                current_center = bbox_center(bbox_original)
                previous_center = bbox_center(last_bbox)
                distance = np.linalg.norm(current_center - previous_center)

                # InsightFace similarity를 우선하므로 위치 보너스는 약하게
                distance_bonus = max(0.0, 0.05 - distance / 1000)

            final_score = similarity + distance_bonus

            x, y, w, h = bbox_original
            bbox_display = (int(x * DISPLAY_SCALE), int(y * DISPLAY_SCALE), int(w * DISPLAY_SCALE), int(h * DISPLAY_SCALE))

            candidates.append({
                "bbox_original": bbox_original,
                "bbox_display": bbox_display,
                "embedding": embedding,
                "similarity": similarity,
                "final_score": final_score
            })

        best_candidate = None

        if candidates:
            best_candidate = max(candidates, key=lambda c: c["similarity"])

        selected_bbox = None
        selected_bbox_display = None
        selected_similarity = None
        selected_embedding = None

        if best_candidate is not None:
            raw_similarity = best_candidate["similarity"]
            similarity_history.append(raw_similarity)

            avg_similarity = np.mean(similarity_history)

            if raw_similarity >= SIMILARITY_THRESHOLD:
                selected_bbox = best_candidate["bbox_original"]
                selected_bbox_display = best_candidate["bbox_display"]
                selected_similarity = raw_similarity
                selected_embedding = best_candidate["embedding"]
                lost_frames = 0
            else:
                lost_frames += 1
        else:
            lost_frames += 1

        if selected_bbox is None and last_bbox is not None and lost_frames <= MAX_LOST_FRAMES:
            selected_bbox = last_bbox
            selected_similarity = np.mean(similarity_history) if similarity_history else 0.0

        if lost_frames > MAX_LOST_FRAMES and candidates:
            print("재탐색 시도")

            best_recovery = max(candidates, key=lambda c: c["final_score"])

            if best_recovery is not None:
                print("재탐색 성공")
                selected_bbox = best_recovery["bbox_original"]
                selected_similarity = best_recovery["similarity"]
                selected_embedding = best_recovery["embedding"]
                lost_frames = 0

        if selected_bbox is not None:
            selected_bbox = smooth_bbox(last_bbox, selected_bbox)
            last_bbox = selected_bbox

            # if selected_embedding is not None and selected_similarity is not None:
                # if selected_similarity > 0.8 and lost_frames == 0:
                #     reference_embedding = update_reference_embedding(
                #         reference_embedding,
                #         selected_embedding
                #     )

            raw_crop, raw_crop_bbox = make_fancam_crop(
                frame_original,
                selected_bbox,
                output_size=FANCAM_SIZE,
                padding=7.0
            )

            crop_bbox = smooth_crop_bbox(crop_bbox, raw_crop_bbox)

            fancam_frame = crop_frame_with_padding(
                frame_original,
                crop_bbox,
                output_size=FANCAM_SIZE
            )

            if fancam_frame is not None:
                if fancam_writer is None:
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    fancam_writer = cv2.VideoWriter(
                        OUTPUT_FANCAM_PATH,
                        fourcc,
                        original_fps,
                        FANCAM_SIZE
                    )

                fancam_writer.write(fancam_frame)

                # 표시용 crop box는 display scale로 변환해서 그림
                x, y, w, h = crop_bbox
                x2 = x + w
                y2 = y + h

                dx1 = int(max(0, x) * DISPLAY_SCALE)
                dy1 = int(max(0, y) * DISPLAY_SCALE)
                dx2 = int(min(frame_original.shape[1], x2) * DISPLAY_SCALE)
                dy2 = int(min(frame_original.shape[0], y2) * DISPLAY_SCALE)

                cv2.rectangle(frame_display, (dx1, dy1), (dx2, dy2), (255, 200, 0), 2)

        for face in faces:
            x, y, w, h = face["bbox_original"]

            dx = int(x * DISPLAY_SCALE)
            dy = int(y * DISPLAY_SCALE)
            dw = int(w * DISPLAY_SCALE)
            dh = int(h * DISPLAY_SCALE)

            cv2.rectangle(
                frame_display,
                (dx, dy),
                (dx + dw, dy + dh),
                (120, 120, 120),
                1
            )

        if last_bbox is not None:
            x, y, w, h = last_bbox
            dx = int(x * DISPLAY_SCALE)
            dy = int(y * DISPLAY_SCALE)
            dw = int(w * DISPLAY_SCALE)
            dh = int(h * DISPLAY_SCALE)

            cv2.rectangle(frame_display, (dx, dy), (dx + dw, dy + dh), (0, 255, 0), 3)

            label = "BIAS"
            if selected_similarity is not None:
                label += f" {selected_similarity:.2f}"

            cv2.putText(
                frame_display,
                label,
                (dx, max(20, dy - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

        cv2.putText(
            frame_display,
            f"faces: {len(faces)} | lost: {lost_frames}",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

    if fancam_writer is not None:
        fancam_writer.release()

    cap.release()

def crop_frame_with_padding(frame, crop_bbox, output_size=FANCAM_SIZE):
    frame_h, frame_w, _ = frame.shape
    x, y, w, h = crop_bbox

    x1 = int(x)
    y1 = int(y)
    x2 = int(x + w)
    y2 = int(y + h)

    src_x1 = max(0, x1)
    src_y1 = max(0, y1)
    src_x2 = min(frame_w, x2)
    src_y2 = min(frame_h, y2)

    if src_x2 <= src_x1 or src_y2 <= src_y1:
        return None

    crop = frame[src_y1:src_y2, src_x1:src_x2]

    pad_left = max(0, -x1)
    pad_top = max(0, -y1)
    pad_right = max(0, x2 - frame_w)
    pad_bottom = max(0, y2 - frame_h)

    if pad_left > 0 or pad_top > 0 or pad_right > 0 or pad_bottom > 0:
        crop = cv2.copyMakeBorder(
            crop,
            pad_top,
            pad_bottom,
            pad_left,
            pad_right,
            cv2.BORDER_REPLICATE
        )

    if crop.size == 0:
        return None

    return cv2.resize(crop, output_size)


if __name__ == "__main__":
    run_face_matching(VIDEO_PATH)