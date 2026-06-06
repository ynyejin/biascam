import cv2
import mediapipe as mp
import numpy as np
import csv
import os
import matplotlib.pyplot as plt

INPUT_VIDEO_PATH = "output/fancam.mp4"

OUTPUT_DIR = "output/analysis"
POSE_CSV_PATH = f"{OUTPUT_DIR}/pose_data.csv"
ENERGY_CSV_PATH = f"{OUTPUT_DIR}/energy_data.csv"
ANGLE_CSV_PATH = f"{OUTPUT_DIR}/angle_data.csv"
REPORT_PATH = f"{OUTPUT_DIR}/motion_report.txt"

ENERGY_GRAPH_PATH = f"{OUTPUT_DIR}/energy_graph.png"
ANGLE_GRAPH_PATH = f"{OUTPUT_DIR}/angle_graph.png"
HEATMAP_GRAPH_PATH = f"{OUTPUT_DIR}/position_heatmap.png"

ORIGINAL_VIDEO_PATH = "data/input/uploaded_video.mp4"
STAGE_POSITION_CSV_PATH = f"{OUTPUT_DIR}/stage_position.csv"
HEATMAP_GRAPH_PATH = f"{OUTPUT_DIR}/position_heatmap.png"

os.makedirs(OUTPUT_DIR, exist_ok=True)

mp_pose = mp.solutions.pose

LANDMARKS = {
    "left_shoulder": mp_pose.PoseLandmark.LEFT_SHOULDER,
    "right_shoulder": mp_pose.PoseLandmark.RIGHT_SHOULDER,
    "left_elbow": mp_pose.PoseLandmark.LEFT_ELBOW,
    "right_elbow": mp_pose.PoseLandmark.RIGHT_ELBOW,
    "left_wrist": mp_pose.PoseLandmark.LEFT_WRIST,
    "right_wrist": mp_pose.PoseLandmark.RIGHT_WRIST,
    "left_hip": mp_pose.PoseLandmark.LEFT_HIP,
    "right_hip": mp_pose.PoseLandmark.RIGHT_HIP,
    "left_knee": mp_pose.PoseLandmark.LEFT_KNEE,
    "right_knee": mp_pose.PoseLandmark.RIGHT_KNEE,
    "left_ankle": mp_pose.PoseLandmark.LEFT_ANKLE,
    "right_ankle": mp_pose.PoseLandmark.RIGHT_ANKLE,
}

UPPER_BODY = [
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist"
]

LOWER_BODY = [
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle"
]


def extract_keypoints(results, width, height):
    keypoints = {}

    if not results.pose_landmarks:
        return keypoints

    for name, landmark_id in LANDMARKS.items():
        lm = results.pose_landmarks.landmark[landmark_id]

        keypoints[name] = {
            "x": float(lm.x * width),
            "y": float(lm.y * height),
            "z": float(lm.z),
            "visibility": float(lm.visibility)
        }

    return keypoints


def calculate_distance(p1, p2):
    dx = p2["x"] - p1["x"]
    dy = p2["y"] - p1["y"]
    return np.sqrt(dx ** 2 + dy ** 2)


def calculate_energy(current_keypoints, previous_keypoints, target_joints):
    if previous_keypoints is None:
        return 0.0

    energy = 0.0

    for joint in target_joints:
        if joint in current_keypoints and joint in previous_keypoints:
            energy += calculate_distance(previous_keypoints[joint], current_keypoints[joint])

    return energy


def calculate_angle(a, b, c):
    a = np.array([a["x"], a["y"]])
    b = np.array([b["x"], b["y"]])
    c = np.array([c["x"], c["y"]])

    ba = a - b
    bc = c - b

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)

    if norm_ba == 0 or norm_bc == 0:
        return 0.0

    cosine_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)

    return np.degrees(np.arccos(cosine_angle))


def calculate_joint_angles(keypoints):
    angles = {}

    if all(j in keypoints for j in ["left_shoulder", "left_elbow", "left_wrist"]):
        angles["left_elbow"] = calculate_angle(
            keypoints["left_shoulder"],
            keypoints["left_elbow"],
            keypoints["left_wrist"]
        )

    if all(j in keypoints for j in ["right_shoulder", "right_elbow", "right_wrist"]):
        angles["right_elbow"] = calculate_angle(
            keypoints["right_shoulder"],
            keypoints["right_elbow"],
            keypoints["right_wrist"]
        )

    if all(j in keypoints for j in ["left_hip", "left_knee", "left_ankle"]):
        angles["left_knee"] = calculate_angle(
            keypoints["left_hip"],
            keypoints["left_knee"],
            keypoints["left_ankle"]
        )

    if all(j in keypoints for j in ["right_hip", "right_knee", "right_ankle"]):
        angles["right_knee"] = calculate_angle(
            keypoints["right_hip"],
            keypoints["right_knee"],
            keypoints["right_ankle"]
        )

    return angles


def save_csv(pose_rows, energy_rows, angle_rows):
    with open(POSE_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "time", "joint", "x", "y", "z", "visibility"])
        writer.writerows(pose_rows)

    with open(ENERGY_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "time", "upper_energy", "lower_energy", "total_energy"])
        writer.writerows(energy_rows)

    with open(ANGLE_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "time", "joint", "angle"])
        writer.writerows(angle_rows)


def plot_energy_graph(energy_rows):
    times = [row[1] for row in energy_rows]
    energies = [row[4] for row in energy_rows]

    if len(times) == 0 or len(energies) == 0:
        print("에너지 그래프 생성 실패: energy 데이터 없음")
        return

    energies_np = np.array(energies, dtype=np.float32)

    mean_energy = float(np.mean(energies_np))
    std_energy = float(np.std(energies_np))

    low_threshold = mean_energy
    high_threshold = mean_energy + std_energy

    max_idx = int(np.argmax(energies_np))
    max_time = times[max_idx]
    max_energy = energies[max_idx]

    plt.figure(figsize=(12, 6))

    for i in range(len(times) - 1):
        current_time = [times[i], times[i + 1]]
        current_energy = [energies[i], energies[i + 1]]

        if energies[i] >= high_threshold:
            color = "#ff4d6d"   # High intensity
        elif energies[i] >= low_threshold:
            color = "#ffb703"   # Medium intensity
        else:
            color = "#4cc9f0"   # Low intensity

        plt.fill_between(
            current_time,
            current_energy,
            color=color,
            alpha=0.45
        )

    plt.plot(
        times,
        energies,
        linewidth=1.8,
        color="black",
        alpha=0.8,
        label="Movement energy"
    )

    plt.axhline(
        mean_energy,
        linestyle="--",
        linewidth=1,
        color="gray",
        alpha=0.7,
        label="Average"
    )

    plt.axhline(
        high_threshold,
        linestyle="--",
        linewidth=1,
        color="red",
        alpha=0.6,
        label="High intensity threshold"
    )

    plt.scatter(
        max_time,
        max_energy,
        s=120,
        color="red",
        zorder=5,
        label="Killing part"
    )

    plt.axvline(
        max_time,
        linestyle="--",
        color="red",
        alpha=0.7
    )

    plt.text(
        max_time,
        max_energy,
        f"Killing Part\n{max_time:.2f}s",
        fontsize=10,
        ha="left",
        va="bottom"
    )

    plt.title("BiasCam Movement Energy by Intensity Zone")
    plt.xlabel("Time (sec)")
    plt.ylabel("Movement Energy")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(ENERGY_GRAPH_PATH, dpi=300)
    plt.close()


def plot_angle_graph(angle_rows):
    angle_data = {}

    for frame, time, joint, angle in angle_rows:
        if joint not in angle_data:
            angle_data[joint] = {"time": [], "angle": []}

        angle_data[joint]["time"].append(time)
        angle_data[joint]["angle"].append(angle)

    plt.figure(figsize=(12, 6))

    for joint, data in angle_data.items():
        plt.plot(data["time"], data["angle"], label=joint)

    plt.title("BiasCam Joint Angle Change")
    plt.xlabel("Time (sec)")
    plt.ylabel("Angle (degree)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(ANGLE_GRAPH_PATH, dpi=300)
    plt.close()


def plot_stage_position_heatmap(stage_position_csv, original_video_path):
    cap = cv2.VideoCapture(original_video_path)

    if not cap.isOpened():
        print("원본 영상을 열 수 없어 히트맵을 생성할 수 없습니다.")
        return {
            "horizontal_range": 0.0,
            "vertical_range": 0.0,
            "point_count": 0
        }

    ret, bg_frame = cap.read()

    if not ret:
        print("원본 영상 첫 프레임을 읽을 수 없습니다.")
        cap.release()
        return {
            "horizontal_range": 0.0,
            "vertical_range": 0.0,
            "point_count": 0
        }

    frame_h, frame_w = bg_frame.shape[:2]
    cap.release()

    if not os.path.exists(stage_position_csv):
        print("stage_position.csv가 없어 히트맵을 생성할 수 없습니다.")
        return {
            "horizontal_range": 0.0,
            "vertical_range": 0.0,
            "point_count": 0
        }

    centers = []

    with open(stage_position_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                x = float(row["center_x"])
                y = float(row["center_y"])
            except Exception:
                continue

            if 0 <= x < frame_w and 0 <= y < frame_h:
                centers.append((x, y))

    heatmap = np.zeros((frame_h, frame_w), dtype=np.float32)

    for x, y in centers:
        cv2.circle(
            heatmap,
            (int(x), int(y)),
            45,
            1.0,
            -1
        )

    if len(centers) == 0:
        print("히트맵 위치 데이터가 없습니다.")
        overlay = bg_frame.copy()
    else:
        heatmap = cv2.GaussianBlur(heatmap, (101, 101), 0)

        heatmap_norm = cv2.normalize(
            heatmap,
            None,
            0,
            255,
            cv2.NORM_MINMAX
        )

        heatmap_color = cv2.applyColorMap(
            heatmap_norm.astype(np.uint8),
            cv2.COLORMAP_JET
        )

        overlay = cv2.addWeighted(
            bg_frame,
            0.45,
            heatmap_color,
            0.55,
            0
        )

    overlay_rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)

    plt.figure(figsize=(12, 7))
    plt.imshow(overlay_rgb)
    plt.title("Stage Position Heatmap")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(HEATMAP_GRAPH_PATH, dpi=300)
    plt.close()

    if len(centers) > 1:
        xs = [p[0] for p in centers]
        ys = [p[1] for p in centers]

        horizontal_range = (max(xs) - min(xs)) / frame_w * 100
        vertical_range = (max(ys) - min(ys)) / frame_h * 100
    else:
        horizontal_range = 0.0
        vertical_range = 0.0

    return {
        "horizontal_range": float(horizontal_range),
        "vertical_range": float(vertical_range),
        "point_count": int(len(centers))
    }


def save_report(energy_rows, angle_rows, heatmap_stats=None):
    total_upper = sum(row[2] for row in energy_rows)
    total_lower = sum(row[3] for row in energy_rows)
    total_energy = sum(row[4] for row in energy_rows)

    if total_energy == 0:
        upper_ratio = 0
        lower_ratio = 0
    else:
        upper_ratio = total_upper / total_energy * 100
        lower_ratio = total_lower / total_energy * 100

    energies = [row[4] for row in energy_rows]

    if len(energies) > 0:
        mean_energy = float(np.mean(energies))
        std_energy = float(np.std(energies))
        high_threshold = mean_energy + std_energy

        high_count = sum(1 for e in energies if e >= high_threshold)
        medium_count = sum(1 for e in energies if mean_energy <= e < high_threshold)
        low_count = sum(1 for e in energies if e < mean_energy)

        total_count = len(energies)

        high_ratio = high_count / total_count * 100
        medium_ratio = medium_count / total_count * 100
        low_ratio = low_count / total_count * 100

        max_energy_row = max(energy_rows, key=lambda row: row[4])
        max_time = max_energy_row[1]
        max_energy = max_energy_row[4]
    else:
        mean_energy = 0.0
        std_energy = 0.0
        high_ratio = 0.0
        medium_ratio = 0.0
        low_ratio = 0.0
        max_time = 0.0
        max_energy = 0.0

    if upper_ratio > lower_ratio:
        style = "상체 중심 안무"
    elif lower_ratio > upper_ratio:
        style = "하체 중심 안무"
    else:
        style = "상체와 하체가 균형적인 안무"

    angle_summary = {}

    for row in angle_rows:
        joint = row[2]
        angle = row[3]

        if joint not in angle_summary:
            angle_summary[joint] = []

        angle_summary[joint].append(angle)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("BiasCam Motion Analysis Summary\n")
        f.write("=================================\n\n")

        f.write("[프로젝트 요약]\n")
        f.write("단체 퍼포먼스 영상에서 선택한 멤버를 추적하여 개인 직캠을 생성하고,\n")
        f.write("생성된 직캠과 추적 좌표를 기반으로 움직임 에너지, 안무 스타일, 무대 위치 점유를 분석하였다.\n\n")

        f.write("[움직임 에너지 분석]\n")
        f.write(f"- 전체 움직임 에너지: {total_energy:.2f}\n")
        f.write(f"- 평균 움직임 에너지: {mean_energy:.2f}\n")
        f.write(f"- 에너지 표준편차: {std_energy:.2f}\n")
        f.write(f"- 고강도 움직임 구간 비율: {high_ratio:.2f}%\n")
        f.write(f"- 중강도 움직임 구간 비율: {medium_ratio:.2f}%\n")
        f.write(f"- 저강도 움직임 구간 비율: {low_ratio:.2f}%\n\n")

        f.write("[상체/하체 움직임 비율]\n")
        f.write(f"- 상체 움직임 비중: {upper_ratio:.2f}%\n")
        f.write(f"- 하체 움직임 비중: {lower_ratio:.2f}%\n")
        f.write(f"- 안무 스타일 해석: {style}\n\n")

        f.write("[킬링파트 자동 감지]\n")
        f.write(f"- 최고 에너지 구간: {max_time:.2f}초\n")
        f.write(f"- 최고 에너지 값: {max_energy:.2f}\n")
        f.write("  → 전체 영상에서 움직임 변화량이 가장 큰 구간을 킬링파트 후보로 판단하였다.\n\n")

        f.write("[무대 위치 히트맵]\n")
        f.write("원본 단체 영상 기준으로 선택 멤버의 추적 bbox 중심 좌표를 프레임별로 누적하여,\n")
        f.write("무대 화면에서 어느 위치를 많이 사용했는지 히트맵으로 시각화하였다.\n")

        if heatmap_stats is not None:
            f.write(f"- 좌우 활동 범위: {heatmap_stats['horizontal_range']:.2f}%\n")
            f.write(f"- 상하 활동 범위: {heatmap_stats['vertical_range']:.2f}%\n")
            f.write(f"- 히트맵 누적 포인트 수: {heatmap_stats['point_count']}개\n")

            if heatmap_stats["horizontal_range"] > heatmap_stats["vertical_range"]:
                f.write("  → 좌우 동선 이동이 상대적으로 큰 퍼포먼스 패턴을 보였다.\n")
            elif heatmap_stats["vertical_range"] > heatmap_stats["horizontal_range"]:
                f.write("  → 상하 방향의 위치 변화가 상대적으로 크게 나타났다.\n")
            else:
                f.write("  → 좌우와 상하 이동 범위가 비교적 균형적으로 나타났다.\n")

        f.write("\n[관절 각도 요약]\n")
        for joint, values in angle_summary.items():
            f.write(f"- {joint}\n")
            f.write(f"  평균 각도: {np.mean(values):.2f}도\n")
            f.write(f"  최소 각도: {np.min(values):.2f}도\n")
            f.write(f"  최대 각도: {np.max(values):.2f}도\n")

        f.write("\n[분석 해석]\n")
        f.write("본 분석은 MediaPipe Pose로 추정한 관절 좌표와 직캠 생성 과정에서 기록한 추적 위치를 기반으로 한다.\n")
        f.write("따라서 실제 3차원 무대 좌표가 아니라, 영상 프레임 내 움직임과 위치 변화량을 정량화한 결과이다.\n")


def run_motion_analysis(video_path=INPUT_VIDEO_PATH):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("직캠 영상을 열 수 없습니다.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps == 0:
        fps = 30

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    ret, first_frame = cap.read()

    if ret:
        first_frame = first_frame.copy()
    else:
        first_frame = None

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    pose_rows = []
    energy_rows = []
    angle_rows = []

    previous_keypoints = None
    frame_idx = 0

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            time_sec = frame_idx / fps

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb_frame)

            keypoints = extract_keypoints(results, width, height)

            for joint, point in keypoints.items():
                pose_rows.append([
                    frame_idx,
                    time_sec,
                    joint,
                    point["x"],
                    point["y"],
                    point["z"],
                    point["visibility"]
                ])

            upper_energy = calculate_energy(keypoints, previous_keypoints, UPPER_BODY)
            lower_energy = calculate_energy(keypoints, previous_keypoints, LOWER_BODY)
            total_energy = upper_energy + lower_energy

            energy_rows.append([
                frame_idx,
                time_sec,
                upper_energy,
                lower_energy,
                total_energy
            ])

            angles = calculate_joint_angles(keypoints)

            for joint, angle in angles.items():
                angle_rows.append([
                    frame_idx,
                    time_sec,
                    joint,
                    angle
                ])

            previous_keypoints = keypoints.copy()
            frame_idx += 1

    cap.release()

    save_csv(pose_rows, energy_rows, angle_rows)

    plot_energy_graph(energy_rows)
    plot_angle_graph(angle_rows)

    heatmap_stats = plot_stage_position_heatmap(
        STAGE_POSITION_CSV_PATH,
        ORIGINAL_VIDEO_PATH
    )

    save_report(energy_rows, angle_rows, heatmap_stats)

    print("BiasCam 안무 분석 완료!")
    print(f"관절 데이터 저장: {POSE_CSV_PATH}")
    print(f"에너지 데이터 저장: {ENERGY_CSV_PATH}")
    print(f"각도 데이터 저장: {ANGLE_CSV_PATH}")
    print(f"에너지 그래프 저장: {ENERGY_GRAPH_PATH}")
    print(f"각도 그래프 저장: {ANGLE_GRAPH_PATH}")
    print(f"무대 점유 히트맵 저장: {HEATMAP_GRAPH_PATH}")
    print(f"분석 리포트 저장: {REPORT_PATH}")


if __name__ == "__main__":
    print("analyze_motion.py 실행 시작")
    run_motion_analysis()