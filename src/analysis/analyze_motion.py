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
TRAJECTORY_3D_PATH = f"{OUTPUT_DIR}/trajectory_3d.png"

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

    max_idx = int(np.argmax(energies))
    max_time = times[max_idx]
    max_energy = energies[max_idx]

    plt.figure(figsize=(12, 6))
    plt.plot(times, energies, linewidth=2)
    plt.scatter(max_time, max_energy, s=100)
    plt.axvline(max_time, linestyle="--")
    plt.title("BiasCam Movement Energy")
    plt.xlabel("Time (sec)")
    plt.ylabel("Energy")
    plt.text(max_time, max_energy, f"Killing Part\n{max_time:.2f}s")
    plt.grid(True)
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


def plot_3d_trajectory(pose_rows):
    target_joints = [
        "left_wrist",
        "right_wrist",
        "left_ankle",
        "right_ankle"
    ]

    pose_data = {}

    for frame, time, joint, x, y, z, visibility in pose_rows:
        if joint not in target_joints:
            continue

        if joint not in pose_data:
            pose_data[joint] = {"x": [], "y": [], "z": [], "time": []}

        pose_data[joint]["x"].append(x)
        pose_data[joint]["y"].append(y)
        pose_data[joint]["z"].append(z)
        pose_data[joint]["time"].append(time)

    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection="3d")

    for joint, data in pose_data.items():
        ax.plot(
            data["x"],
            data["y"],
            data["time"],
            label=joint
        )

    ax.set_title("BiasCam Pseudo-3D Joint Trajectory")
    ax.set_xlabel("X Position")
    ax.set_ylabel("Y Position")
    ax.set_zlabel("Time (sec)")
    ax.legend()

    plt.tight_layout()
    plt.savefig(TRAJECTORY_3D_PATH, dpi=300)
    plt.close()


def save_report(energy_rows, angle_rows):
    total_upper = sum(row[2] for row in energy_rows)
    total_lower = sum(row[3] for row in energy_rows)
    total_energy = sum(row[4] for row in energy_rows)

    if total_energy == 0:
        upper_ratio = 0
        lower_ratio = 0
    else:
        upper_ratio = total_upper / total_energy * 100
        lower_ratio = total_lower / total_energy * 100

    max_energy_row = max(energy_rows, key=lambda row: row[4])
    max_time = max_energy_row[1]
    max_energy = max_energy_row[4]

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
        f.write("BiasCam Motion Analysis Report\n")
        f.write("=================================\n\n")

        f.write("[프로젝트 요약]\n")
        f.write("단체 영상에서 선택한 멤버를 추적하여 자동 직캠을 생성하고,\n")
        f.write("생성된 직캠 영상에 MediaPipe Pose를 적용해 안무 움직임을 분석하였다.\n\n")

        f.write("[움직임 에너지 분석]\n")
        f.write(f"- 전체 움직임 에너지: {total_energy:.2f}\n")
        f.write(f"- 상체 움직임 비중: {upper_ratio:.2f}%\n")
        f.write(f"- 하체 움직임 비중: {lower_ratio:.2f}%\n")
        f.write(f"- 안무 스타일 해석: {style}\n\n")

        f.write("[킬링파트 자동 감지]\n")
        f.write(f"- 최고 에너지 구간: {max_time:.2f}초\n")
        f.write(f"- 최고 에너지 값: {max_energy:.2f}\n\n")

        f.write("[관절 각도 요약]\n")
        for joint, values in angle_summary.items():
            f.write(f"- {joint}\n")
            f.write(f"  평균 각도: {np.mean(values):.2f}도\n")
            f.write(f"  최소 각도: {np.min(values):.2f}도\n")
            f.write(f"  최대 각도: {np.max(values):.2f}도\n")

        f.write("\n[3D 시각화 설명]\n")
        f.write("본 프로젝트의 3D 궤적은 단일 카메라에서 실제 공간 좌표를 완전히 복원한 것이 아니라,\n")
        f.write("MediaPipe Pose의 상대적 z값 및 시간축을 활용한 pseudo-3D motion visualization이다.\n")


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
    plot_3d_trajectory(pose_rows)
    save_report(energy_rows, angle_rows)

    print("BiasCam 안무 분석 완료!")
    print(f"관절 데이터 저장: {POSE_CSV_PATH}")
    print(f"에너지 데이터 저장: {ENERGY_CSV_PATH}")
    print(f"각도 데이터 저장: {ANGLE_CSV_PATH}")
    print(f"에너지 그래프 저장: {ENERGY_GRAPH_PATH}")
    print(f"각도 그래프 저장: {ANGLE_GRAPH_PATH}")
    print(f"3D 궤적 그래프 저장: {TRAJECTORY_3D_PATH}")
    print(f"분석 리포트 저장: {REPORT_PATH}")


if __name__ == "__main__":
    print("analyze_motion.py 실행 시작")
    run_motion_analysis()