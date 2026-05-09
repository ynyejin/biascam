import os
import cv2
import mediapipe as mp
import numpy as np
from collections import deque

VIDEO_PATH = "data/input/test.mp4"
OUTPUT_FANCAM_PATH = "output/fancam.mp4"

DISPLAY_SCALE = 0.7
SIMILARITY_THRESHOLD = 0.5
HISTORY_SIZE = 8
MAX_LOST_FRAMES = 20

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


def make_fancam_crop(frame, bbox, output_size=(720, 1280), padding=4.0):
    frame_h, frame_w, _ = frame.shape
    x, y, w, h = bbox

    cx = x + w / 2
    cy = y + h / 2

    crop_h = int(h * padding)
    crop_w = int(crop_h * output_size[0] / output_size[1])

    # 얼굴보다 몸이 아래에 있으니까 crop 중심을 아래로 내림
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

        score = float(detection.score[0])

        faces.append({
            "bbox": (x, y, bw, bh),
            "score": score
        })

    return faces


def bbox_center(bbox):
    x, y, w, h = bbox
    return np.array([x + w / 2, y + h / 2])


def smooth_bbox(prev_bbox, new_bbox, alpha=0.35):
    if prev_bbox is None:
        return new_bbox

    px, py, pw, ph = prev_bbox
    nx, ny, nw, nh = new_bbox

    x = int(px * (1 - alpha) + nx * alpha)
    y = int(py * (1 - alpha) + ny * alpha)
    w = int(pw * (1 - alpha) + nw * alpha)
    h = int(ph * (1 - alpha) + nh * alpha)

    return (x, y, w, h)


def smooth_crop_bbox(prev_bbox, new_bbox, alpha=0.18):
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
    global clicked_bbox, clicked_done

    clicked_bbox = None
    clicked_done = False

    while True:
        ret, frame = cap.read()

        if not ret:
            print("첫 프레임을 읽을 수 없습니다.")
            return None, None, None

        frame = cv2.resize(frame, None, fx=DISPLAY_SCALE, fy=DISPLAY_SCALE)
        faces = detect_faces(frame, face_detection)

        if len(faces) == 0:
            cv2.putText(
                frame,
                "No face detected. Press any key for next frame / ESC to quit.",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

            cv2.imshow("Select Your Bias", frame)
            key = cv2.waitKey(0)

            if key == 27:
                return None, None, None

            continue

        display = frame.copy()

        for idx, face in enumerate(faces):
            x, y, w, h = face["bbox"]
            cv2.rectangle(display, (x, y), (x + w, y + h), (120, 120, 120), 2)
            cv2.putText(
                display,
                f"Face {idx}",
                (x, max(20, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (120, 120, 120),
                2
            )

        cv2.putText(
            display,
            "Click your bias face. ESC: quit",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        cv2.imshow("Select Your Bias", display)
        cv2.setMouseCallback("Select Your Bias", mouse_callback, {"faces": faces})

        while not clicked_done:
            key = cv2.waitKey(1) & 0xFF

            if key == 27:
                cv2.destroyWindow("Select Your Bias")
                return None, None, None

        selected_crop = crop_face(frame, clicked_bbox)
        reference_embedding = get_face_embedding(selected_crop, face_mesh)

        if reference_embedding is None:
            print("선택한 얼굴에서 embedding 추출 실패. 다른 프레임/얼굴을 선택하세요.")
            clicked_bbox = None
            clicked_done = False
            continue

        cv2.destroyWindow("Select Your Bias")
        return clicked_bbox, reference_embedding, frame


def run_face_matching(video_path):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("영상을 열 수 없습니다.")
        return

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

        selected_bbox, reference_embedding, selected_frame = select_target_face(
            cap,
            face_detection,
            face_mesh
        )

        if selected_bbox is None or reference_embedding is None:
            cap.release()
            cv2.destroyAllWindows()
            return

        last_bbox = selected_bbox

        # VideoWriter 관련 변수
        fancam_writer = None
        crop_bbox = None

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            frame = cv2.resize(frame, None, fx=DISPLAY_SCALE, fy=DISPLAY_SCALE)

            faces = detect_faces(frame, face_detection)

            candidates = []

            for face in faces:
                bbox = face["bbox"]
                face_crop = crop_face(frame, bbox)
                embedding = get_face_embedding(face_crop, face_mesh)

                if embedding is None:
                    continue

                similarity = cosine_similarity(reference_embedding, embedding)

                distance_bonus = 0.0

                if last_bbox is not None:
                    current_center = bbox_center(bbox)
                    previous_center = bbox_center(last_bbox)
                    distance = np.linalg.norm(current_center - previous_center)

                    distance_bonus = max(0.0, 0.20 - distance / 600)

                final_score = similarity + distance_bonus

                candidates.append({
                    "bbox": bbox,
                    "similarity": similarity,
                    "final_score": final_score
                })

            best_candidate = None

            if candidates:
                best_candidate = max(candidates, key=lambda c: c["final_score"])

            selected_bbox = None
            selected_similarity = None

            if best_candidate is not None:
                raw_similarity = best_candidate["similarity"]
                similarity_history.append(raw_similarity)

                avg_similarity = np.mean(similarity_history)

                if raw_similarity >= SIMILARITY_THRESHOLD or avg_similarity >= SIMILARITY_THRESHOLD:
                    selected_bbox = best_candidate["bbox"]
                    selected_similarity = raw_similarity
                    lost_frames = 0
                else:
                    lost_frames += 1
            else:
                lost_frames += 1

            if selected_bbox is None and last_bbox is not None and lost_frames <= MAX_LOST_FRAMES:
                selected_bbox = last_bbox
                selected_similarity = np.mean(similarity_history) if similarity_history else 0.0

            # 재탐색 로직 추가
            if lost_frames > MAX_LOST_FRAMES and faces:
                print("재탐색 시도")

                best_recovery = None
                best_score = -1

                for face in faces:
                    bbox = face["bbox"]

                    face_crop = crop_face(frame, bbox)
                    embedding = get_face_embedding(face_crop, face_mesh)

                    if embedding is None:
                        continue

                    similarity = cosine_similarity(reference_embedding, embedding)

                    # 거리 + similarity 같이 고려
                    if last_bbox is not None:
                        dist = np.linalg.norm(bbox_center(bbox) - bbox_center(last_bbox))
                        score = similarity - dist / 800
                    else:
                        score = similarity

                    if score > best_score:
                        best_score = score
                        best_recovery = bbox

                if best_recovery is not None:
                    print("재탐색 성공")
                    last_bbox = best_recovery
                    selected_bbox = best_recovery
                    lost_frames = 0

            if selected_bbox is not None:
                selected_bbox = smooth_bbox(last_bbox, selected_bbox, alpha=0.15)
                last_bbox = selected_bbox

                # 자동 직캠 crop 생성
                fancam_frame = None

                if selected_bbox is not None:
                    raw_crop, raw_crop_bbox = make_fancam_crop(
                        frame,
                        selected_bbox,
                        output_size=(720, 1280),
                        padding=7.0
                    )

                    crop_bbox = smooth_crop_bbox(crop_bbox, raw_crop_bbox, alpha=0.08)

                    x, y, w, h = crop_bbox
                    x2 = min(frame.shape[1], x + w)
                    y2 = min(frame.shape[0], y + h)
                    x = max(0, x)
                    y = max(0, y)

                    crop = frame[y:y2, x:x2]

                    if crop.size != 0:
                        fancam_frame = cv2.resize(crop, (720, 1280))

                        if fancam_writer is None:
                            fps = cap.get(cv2.CAP_PROP_FPS)
                            if fps == 0:
                                fps = 30

                            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                            fancam_writer = cv2.VideoWriter(
                                OUTPUT_FANCAM_PATH,
                                fourcc,
                                fps,
                                (720, 1280)
                            )

                        fancam_writer.write(fancam_frame)

                        cv2.rectangle(frame, (x, y), (x2, y2), (255, 200, 0), 2)

            for face in faces:
                x, y, w, h = face["bbox"]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (120, 120, 120), 1)

            if selected_bbox is not None:
                x, y, w, h = selected_bbox

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)

                label = "BIAS"
                if selected_similarity is not None:
                    label += f" {selected_similarity:.2f}"

                cv2.putText(
                    frame,
                    label,
                    (x, max(20, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

            cv2.putText(
                frame,
                f"faces: {len(faces)} | lost: {lost_frames}",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

            cv2.imshow("Bias Tracking - Click Initialized", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break

    if fancam_writer is not None:
        fancam_writer.release()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_face_matching(VIDEO_PATH)