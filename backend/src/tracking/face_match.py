import os
import cv2
import numpy as np
import json
from insightface.app import FaceAnalysis

VIDEO_PATH = "data/input/uploaded_video.mp4"
OUTPUT_FANCAM_PATH = "output/fancam.mp4"

DISPLAY_SCALE = 0.7
MAX_LOST_FRAMES = 12
DETECT_EVERY_N_FRAMES = 3
DETECT_SCALE = 0.75 

FAST_MOVE_DISTANCE = 80

FANCAM_SIZE = (720, 1280)  # width, height
BBOX_SMOOTH_ALPHA = 0.35
CROP_SMOOTH_ALPHA = 0.17

SIMILARITY_THRESHOLD = 0.40
SIMILARITY_MARGIN = 0.05
MAX_JUMP_DISTANCE_RATIO = 0.15

PROGRESS_FILE = "output/progress.json"

os.makedirs("output", exist_ok=True)

face_recognizer = None

def write_progress(progress, message="Generating fancam...", done=False, error=None):
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)

    data = {
        "progress": progress,
        "message": message,
        "done": done,
        "error": error
    }

    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

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


def make_fancam_crop(frame, bbox, output_size=FANCAM_SIZE):
    frame_h, frame_w, _ = frame.shape
    x, y, w, h = bbox

    # -----------------------------
    # 얼굴 bbox 기준 비대칭 확장
    # -----------------------------
    side_expand = 4.0     # 좌우 확장
    top_expand = 2.5      # 위쪽은 적게
    bottom_expand = 9.0   # 아래쪽은 많이 (전신용)

    x1 = int(x - w * side_expand)
    x2 = int(x + w + w * side_expand)

    y1 = int(y - h * top_expand)
    y2 = int(y + h + h * bottom_expand)

    crop_w = x2 - x1
    crop_h = y2 - y1

    # -----------------------------
    # output_size 비율 맞추기
    # -----------------------------
    target_ratio = output_size[0] / output_size[1]   # width / height
    current_ratio = crop_w / crop_h

    if current_ratio < target_ratio:
        # 너무 세로로 길면 폭을 더 넓힘
        new_crop_w = int(crop_h * target_ratio)
        extra_w = new_crop_w - crop_w
        x1 -= extra_w // 2
        x2 += extra_w - (extra_w // 2)

    elif current_ratio > target_ratio:
        # 너무 가로로 넓으면 높이를 더 늘림
        new_crop_h = int(crop_w / target_ratio)
        extra_h = new_crop_h - crop_h

        # 추가 높이도 아래쪽으로 더 많이 배분
        extra_top = int(extra_h * 0.25)
        extra_bottom = extra_h - extra_top

        y1 -= extra_top
        y2 += extra_bottom

    final_w = x2 - x1
    final_h = y2 - y1

    # 여기서는 clamp하지 않고 그대로 넘김
    # crop_frame_with_padding()에서 프레임 밖 영역 처리
    return None, (x1, y1, final_w, final_h)


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


def apply_dead_zone(prev_bbox, new_bbox, threshold=25):
    if prev_bbox is None:
        return new_bbox

    if new_bbox is None:
        return prev_bbox

    px, py, pw, ph = prev_bbox
    nx, ny, nw, nh = new_bbox

    prev_cx = px + pw / 2
    prev_cy = py + ph / 2

    new_cx = nx + nw / 2
    new_cy = ny + nh / 2

    distance = np.sqrt(
        (new_cx - prev_cx) ** 2 +
        (new_cy - prev_cy) ** 2
    )

    # crop 중심 이동이 threshold보다 작으면 이전 crop 유지
    if distance < threshold:
        return prev_bbox

    return new_bbox


def normalize_embedding(embedding):
    embedding = np.array(embedding, dtype=np.float32)

    if embedding.size == 0:
        return None

    norm = np.linalg.norm(embedding)

    if norm == 0:
        return None

    return embedding / norm


def build_reference_embedding(
    cap,
    face_recognizer,
    selected_img,
    selected_bbox,
    selected_frame_idx,
    max_embeddings=5
):
    embeddings = []

    # 1. 선택된 후보 이미지에서 먼저 embedding 추출
    faces = face_recognizer.get(selected_img)

    if faces is not None and len(faces) > 0:
        face = max(
            faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
        )

        emb = normalize_embedding(face.normed_embedding)

        if emb is not None:
            embeddings.append(emb)
            print("reference embedding added from selected image")

    # 2. 선택된 원본 프레임 주변에서 추가 embedding 수집
    sx, sy, sw, sh = selected_bbox
    selected_center = np.array([sx + sw / 2, sy + sh / 2])

    # 선택 프레임 주변만 탐색
    frame_offsets = [-30, -15, 0, 15, 30, 45, 60]

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        total_frames = 1

    for offset in frame_offsets:
        if len(embeddings) >= max_embeddings:
            break

        target_frame_idx = selected_frame_idx + offset

        if target_frame_idx < 0 or target_frame_idx >= total_frames:
            continue

        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_idx)
        ret, frame = cap.read()

        if not ret:
            continue

        faces_in_frame = face_recognizer.get(frame)

        if faces_in_frame is None or len(faces_in_frame) == 0:
            continue

        best_face = None
        best_dist = float("inf")

        for face in faces_in_frame:
            if face.normed_embedding is None:
                continue

            x1, y1, x2, y2 = face.bbox.astype(int)
            face_center = np.array([(x1 + x2) / 2, (y1 + y2) / 2])

            dist = np.linalg.norm(face_center - selected_center)

            if dist < best_dist:
                best_dist = dist
                best_face = face

        # 너무 멀리 있는 얼굴은 다른 멤버일 가능성이 있어서 제외
        max_allowed_dist = max(sw, sh) * 2.5

        if best_face is not None and best_dist <= max_allowed_dist:
            emb = normalize_embedding(best_face.normed_embedding)

            if emb is not None:
                embeddings.append(emb)
                print(
                    f"reference embedding added from frame {target_frame_idx}, "
                    f"dist={best_dist:.1f}"
                )

    if len(embeddings) == 0:
        return None

    # 3. 여러 embedding 평균
    mean_embedding = np.mean(embeddings, axis=0)
    mean_embedding = normalize_embedding(mean_embedding)

    print(f"reference embedding count: {len(embeddings)}")

    return mean_embedding


def select_target_face(cap, face_recognizer):
    selected_file = "selected_member.json"

    if not os.path.exists(selected_file):
        print("selected_member.json 없음")
        return None, None

    with open(selected_file, "r", encoding="utf-8") as f:
        selected = json.load(f)

    selected_id = int(selected["id"])

    selected_face_path = f"output/faces/face_{selected_id}.jpg"

    if not os.path.exists(selected_face_path):
        print("선택한 후보 이미지 없음:", selected_face_path)
        return None, None

    selected_img = cv2.imread(selected_face_path)

    if selected_img is None or selected_img.size == 0:
        print("선택한 후보 이미지 읽기 실패")
        return None, None

    raw_bbox = selected["bbox"]
    selected_bbox = xyxy_to_xywh(raw_bbox)

    selected_frame_idx = int(selected.get("frame_idx", 0))

    reference_embedding = build_reference_embedding(
        cap=cap,
        face_recognizer=face_recognizer,
        selected_img=selected_img,
        selected_bbox=selected_bbox,
        selected_frame_idx=selected_frame_idx,
        max_embeddings=5
    )

    if reference_embedding is None or reference_embedding.size == 0:
        print("reference embedding 생성 실패")
        return None, None

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
        raise Exception("video open failed")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total_frames <= 0:
        total_frames = 1

    original_fps = cap.get(cv2.CAP_PROP_FPS)
    if original_fps == 0:
        original_fps = 30

    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_diag = np.sqrt(frame_w ** 2 + frame_h ** 2)
    max_jump_distance = frame_diag * MAX_JUMP_DISTANCE_RATIO

    last_bbox = None
    lost_frames = 0

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
    frame_idx = 0
    last_faces = []
    last_fancam_frame = None
    last_center = None
    fast_motion_mode = False

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fancam_writer = cv2.VideoWriter(
        OUTPUT_FANCAM_PATH,
        fourcc,
        original_fps,
        FANCAM_SIZE
    )

    input_frame_count = 0
    output_frame_count = 0
    insightface_call_count = 0
    last_progress = -1

    while True:
        ret, frame_original = cap.read()

        if not ret:
            break

        frame_idx += 1
        input_frame_count += 1

        tracking_progress = 25 + int((frame_idx / total_frames) * 30)
        tracking_progress = min(tracking_progress, 54)

        if tracking_progress != last_progress:
            write_progress(
                tracking_progress,
                f"Generating fancam... {tracking_progress}%"
            )
            last_progress = tracking_progress
                
        # 3프레임마다만 InsightFace 실행
        should_detect = (
            frame_idx == 1
            or frame_idx % DETECT_EVERY_N_FRAMES == 0
            or last_bbox is None
        )

        faces = []
        candidates = []

        if should_detect:
            current_detect_scale = DETECT_SCALE

            frame_small = cv2.resize(
                frame_original,
                None,
                fx=current_detect_scale,
                fy=current_detect_scale
            )

            insightface_call_count += 1

            faces_small = detect_faces_with_insightface(
                frame_small,
                face_recognizer,
                min_det_score=0.30
            )

            # bbox 좌표를 원본 해상도로 역산
            faces = []

            for face in faces_small:
                x, y, w, h = face["bbox_original"]

                bbox_original = (
                    int(x / current_detect_scale),
                    int(y / current_detect_scale),
                    int(w / current_detect_scale),
                    int(h / current_detect_scale)
                )
                faces.append({
                    "bbox_original": bbox_original,
                    "embedding": face["embedding"],
                    "det_score": face.get("det_score", 1.0)
                })

            last_faces = faces

            for face in faces:
                bbox_original = face["bbox_original"]
                embedding = face["embedding"]

                similarity = cosine_similarity(reference_embedding, embedding)

                distance_bonus = 0.0

                if last_bbox is not None:
                    current_center = bbox_center(bbox_original)
                    previous_center = bbox_center(last_bbox)
                    distance = np.linalg.norm(current_center - previous_center)

                    # 위치 보너스는 약하게만 사용
                    distance_bonus = max(0.0, 0.05 - distance / 1000)

                final_score = similarity + distance_bonus

                candidates.append({
                    "bbox_original": bbox_original,
                    "embedding": embedding,
                    "similarity": similarity,
                    "final_score": final_score
                })
        else:
            # 탐지하지 않는 프레임은 이전 bbox를 그대로 사용
            faces = last_faces
        
        selected_bbox = None
        selected_similarity = None
        selected_embedding = None

        if should_detect:
            best_candidate = None

            # last_bbox가 있으면 너무 멀리 떨어진 후보는 제거
            filtered_candidates = []

            for candidate in candidates:
                if last_bbox is not None:
                    current_center = bbox_center(candidate["bbox_original"])
                    previous_center = bbox_center(last_bbox)
                    distance = np.linalg.norm(current_center - previous_center)

                    if distance > max_jump_distance:
                        continue

                filtered_candidates.append(candidate)

            if filtered_candidates:
                filtered_candidates = sorted(
                    filtered_candidates,
                    key=lambda c: c["similarity"],
                    reverse=True
                )

                best_candidate = filtered_candidates[0]
                second_similarity = (
                    filtered_candidates[1]["similarity"]
                    if len(filtered_candidates) > 1
                    else -1.0
                )

                raw_similarity = best_candidate["similarity"]
                margin = raw_similarity - second_similarity

                if raw_similarity >= SIMILARITY_THRESHOLD and margin >= SIMILARITY_MARGIN:
                    selected_bbox = best_candidate["bbox_original"]
                    selected_similarity = raw_similarity
                    selected_embedding = best_candidate["embedding"]
                    lost_frames = 0
                else:
                    # 확신이 없으면 새 후보로 갈아타지 않음
                    lost_frames += 1
            else:
                lost_frames += 1

        else:
            # 탐지하지 않는 프레임은 이전 bbox 그대로 사용
            if last_bbox is not None:
                selected_bbox = last_bbox
                selected_similarity = None
                selected_embedding = None

        if selected_bbox is None and last_bbox is not None and lost_frames <= MAX_LOST_FRAMES:
            selected_bbox = last_bbox
            selected_similarity = None

        if lost_frames > MAX_LOST_FRAMES and candidates:
            print("재탐색 시도")

            recovery_candidates = sorted(
                candidates,
                key=lambda c: c["similarity"],
                reverse=True
            )

            best_recovery = recovery_candidates[0]

            if best_recovery["similarity"] >= SIMILARITY_THRESHOLD + 0.10:
                print("재탐색 성공")
                selected_bbox = best_recovery["bbox_original"]
                selected_similarity = best_recovery["similarity"]
                selected_embedding = best_recovery["embedding"]
                lost_frames = 0
            else:
                print("재탐색 보류")

        fancam_frame = None

        # 1. 선택 멤버 bbox를 새로 찾은 경우
        if selected_bbox is not None:
            current_center = bbox_center(selected_bbox)

            if last_center is not None:
                move_distance = np.linalg.norm(current_center - last_center)
                fast_motion_mode = move_distance > FAST_MOVE_DISTANCE
            else:
                fast_motion_mode = False

            selected_bbox = smooth_bbox(last_bbox, selected_bbox)
            last_bbox = selected_bbox
            last_center = bbox_center(selected_bbox)

            raw_crop, raw_crop_bbox = make_fancam_crop(
                frame_original,
                selected_bbox,
                output_size=FANCAM_SIZE,
            )

            raw_crop_bbox = apply_dead_zone(
                crop_bbox,
                raw_crop_bbox,
                threshold=20
            )

            crop_bbox = smooth_crop_bbox(
                crop_bbox,
                raw_crop_bbox
            )

        # 2. 얼굴을 못 찾은 프레임이면, 이전 crop_bbox 위치를 현재 프레임에 그대로 적용
        if crop_bbox is not None:
            fancam_frame = crop_frame_with_padding(
                frame_original,
                crop_bbox,
                output_size=FANCAM_SIZE
            )

        # 3. 그래도 없으면, 정말 초기 상태라서 이전 crop도 없는 것
        #    이 경우에는 화면 중앙 crop을 임시로 사용
        if fancam_frame is None:
            frame_h, frame_w, _ = frame_original.shape

            center_crop_h = frame_h
            center_crop_w = int(center_crop_h * FANCAM_SIZE[0] / FANCAM_SIZE[1])

            if center_crop_w > frame_w:
                center_crop_w = frame_w
                center_crop_h = int(center_crop_w * FANCAM_SIZE[1] / FANCAM_SIZE[0])

                center_x = frame_w // 2
                center_y = frame_h // 2

                center_bbox = (
                    int(center_x - center_crop_w / 2),
                    int(center_y - center_crop_h / 2),
                    int(center_crop_w),
                    int(center_crop_h)
                )

                fancam_frame = crop_frame_with_padding(
                    frame_original,
                    center_bbox,
                    output_size=FANCAM_SIZE
                )

        # 4. 그래도 None이면 검은 화면이라도 생성
        if fancam_frame is None:
            fancam_frame = np.zeros(
                (FANCAM_SIZE[1], FANCAM_SIZE[0], 3),
                dtype=np.uint8                )

        # 5. 여기서 매 프레임 반드시 write
        fancam_writer.write(fancam_frame)
        output_frame_count += 1

    if fancam_writer is not None:
        fancam_writer.release()

    print("insightface_call_count:", insightface_call_count)
    print("input_frame_count:", input_frame_count)
    print("output_frame_count:", output_frame_count)

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