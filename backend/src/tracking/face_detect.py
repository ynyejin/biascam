import cv2
import mediapipe as mp

# MediaPipe 초기화
mp_face = mp.solutions.face_detection
mp_draw = mp.solutions.drawing_utils


def run_face_detection(video_path):
    cap = cv2.VideoCapture(video_path)

    # MediaPipe Face Detection
    with mp_face.FaceDetection(
        model_selection=1,  # 0: 근거리 / 1: 원거리
        min_detection_confidence=0.7
    ) as face_detection:

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 속도 개선 (resize)
            frame = cv2.resize(frame, None, fx=0.7, fy=0.7)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb)

            h, w, _ = frame.shape

            if results.detections:
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box

                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    bw = int(bbox.width * w)
                    bh = int(bbox.height * h)

                    # 화면 밖 좌표 방지
                    x = max(0, x)
                    y = max(0, y)

                    # confidence 표시
                    score = int(detection.score[0] * 100)

                    # 텍스트
                    cv2.putText(
                        frame,
                        f"{score}%",
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2
                    )

            cv2.imshow("Face Detection (MediaPipe)", frame)

            # ESC 종료
            if cv2.waitKey(1) & 0xFF == 27:
                break

    cap.release()
    cv2.destroyAllWindows()
