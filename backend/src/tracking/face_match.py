import os
import cv2
import mediapipe as mp
import numpy as np
from collections import deque

VIDEO_PATH = "data/input/uploaded_video.mp4"
OUTPUT_FANCAM_PATH = "output/fancam.mp4"

DISPLAY_SCALE = 0.7
SIMILARITY_THRESHOLD = 0.5
HISTORY_SIZE = 8
MAX_LOST_FRAMES = 20

FANCAM_SIZE = (720, 1280)  # width, height
BBOX_SMOOTH_ALPHA = 0.15
CROP_SMOOTH_ALPHA = 0.08
EMBEDDING_UPDATE_ALPHA = 0.05

mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh

clicked_bbox = None
clicked_done = False

os.makedirs("output", exist_ok=True)


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)

    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0

    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


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


def make_fancam_crop(frame, bbox, output_size=FANCAM_SIZE, padding=7.0):
    frame_h, frame_w, _ = frame.shape
    x, y, w, h = bbox

    cx = x + w / 2
    cy = y + h / 2

    crop_h = int(h * padding)
    crop_w = int(crop_h * output_size[0] / output_size[1])

    cy = cy + h * 3.0

    x1 = int(cx - crop_w / 2)
    y1 = int(cy - crop_h / 2)
    x2 = x1 + crop_w
    y2 = y1 + crop_h

    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(frame_w, x2)
    y2 = min(frame_h, y2)

    crop = frame[y1:y2, x1:x2]

    if crop.size == 0:
        return None, (x1, y1, x2 - x1, y2 - y1)

    crop = cv2.resize(crop, output_size)
    return crop, (x1, y1, x2 - x1, y2 - y1)


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


def select_target_face(cap, face_detection, face_mesh):
    selected_face_file = "selected_face.txt"

    if not os.path.exists(selected_face_file):
        print("selected_face.txt 파일이 없습니다.")
        return None, None

    with open(selected_face_file, "r") as f:
        selected_face_id = int(f.read().strip())

    print(f"프론트에서 선택한 face_id: {selected_face_id}")

    frame_idx = 0
    max_scan_frames = 300
    selected_frame = None
    selected_faces = []

    while frame_idx < max_scan_frames:
        ret, frame_original = cap.read()

        if not ret:
            break

        frame_idx += 1

        frame_display = cv2.resize(
            frame_original,
            None,
            fx=DISPLAY_SCALE,
            fy=DISPLAY_SCALE
        )

        faces_display = detect_faces(frame_display, face_detection)

        if len(faces_display) > len(selected_faces):
            selected_faces = faces_display
            selected_frame = frame_original.copy()

    if selected_frame is None or len(selected_faces) == 0:
        print("영상에서 얼굴 후보를 찾지 못했습니다.")
        return None, None

    if selected_face_id < 0 or selected_face_id >= len(selected_faces):
        print("선택한 face_id가 얼굴 후보 범위를 벗어났습니다.")
        return None, None

    selected_bbox_display = selected_faces[selected_face_id]["bbox"]
    selected_bbox_original = scale_bbox_to_original(
        selected_bbox_display,
        DISPLAY_SCALE
    )

    selected_crop = crop_face(selected_frame, selected_bbox_original)
    reference_embedding = get_face_embedding(selected_crop, face_mesh)

    if reference_embedding is None:
        print("선택한 얼굴에서 embedding 추출 실패")
        return None, None

    return selected_bbox_original, reference_embedding


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

    with mp_face_detection.FaceDetection(
        model_selection=1,
        min_detection_confidence=0.5
    ) as face_detection, mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True
    ) as face_mesh:

        selected_bbox, reference_embedding = select_target_face(
            cap,
            face_detection,
            face_mesh
        )

        if selected_bbox is None or reference_embedding is None:
            cap.release()
            cv2.destroyAllWindows()
            return

        # 선택 과정에서 지나간 프레임을 다시 처음부터 처리
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        last_bbox = selected_bbox

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

            faces_display = detect_faces(frame_display, face_detection)

            candidates = []

            for face in faces_display:
                bbox_display = face["bbox"]
                bbox_original = scale_bbox_to_original(bbox_display, DISPLAY_SCALE)

                face_crop = crop_face(frame_original, bbox_original)
                embedding = get_face_embedding(face_crop, face_mesh)

                if embedding is None:
                    continue

                similarity = cosine_similarity(reference_embedding, embedding)

                distance_bonus = 0.0

                if last_bbox is not None:
                    current_center = bbox_center(bbox_original)
                    previous_center = bbox_center(last_bbox)
                    distance = np.linalg.norm(current_center - previous_center)

                    distance_bonus = max(0.0, 0.20 - distance / 850)

                final_score = similarity + distance_bonus

                candidates.append({
                    "bbox_original": bbox_original,
                    "bbox_display": bbox_display,
                    "embedding": embedding,
                    "similarity": similarity,
                    "final_score": final_score
                })

            best_candidate = None

            if candidates:
                best_candidate = max(candidates, key=lambda c: c["final_score"])

            selected_bbox = None
            selected_bbox_display = None
            selected_similarity = None
            selected_embedding = None

            if best_candidate is not None:
                raw_similarity = best_candidate["similarity"]
                similarity_history.append(raw_similarity)

                avg_similarity = np.mean(similarity_history)

                if raw_similarity >= SIMILARITY_THRESHOLD or avg_similarity >= SIMILARITY_THRESHOLD:
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

                if selected_embedding is not None and selected_similarity is not None:
                    if selected_similarity > 0.7:
                        reference_embedding = update_reference_embedding(
                            reference_embedding,
                            selected_embedding
                        )

                raw_crop, raw_crop_bbox = make_fancam_crop(
                    frame_original,
                    selected_bbox,
                    output_size=FANCAM_SIZE,
                    padding=7.0
                )

                crop_bbox = smooth_crop_bbox(crop_bbox, raw_crop_bbox)

                x, y, w, h = crop_bbox
                x = max(0, x)
                y = max(0, y)
                x2 = min(frame_original.shape[1], x + w)
                y2 = min(frame_original.shape[0], y + h)

                crop = frame_original[y:y2, x:x2]

                if crop.size != 0:
                    fancam_frame = cv2.resize(crop, FANCAM_SIZE)

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
                    dx1 = int(x * DISPLAY_SCALE)
                    dy1 = int(y * DISPLAY_SCALE)
                    dx2 = int(x2 * DISPLAY_SCALE)
                    dy2 = int(y2 * DISPLAY_SCALE)
                    cv2.rectangle(frame_display, (dx1, dy1), (dx2, dy2), (255, 200, 0), 2)

            for face in faces_display:
                x, y, w, h = face["bbox"]
                cv2.rectangle(frame_display, (x, y), (x + w, y + h), (120, 120, 120), 1)

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
                f"faces: {len(faces_display)} | lost: {lost_frames}",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

            cv2.imshow("Bias Tracking - Original Quality Fancam", frame_display)

            if cv2.waitKey(1) & 0xFF == 27:
                break

    if fancam_writer is not None:
        fancam_writer.release()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_face_matching(VIDEO_PATH)