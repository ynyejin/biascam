import os
import streamlit as st

st.set_page_config(
    page_title="BiasCam",
    page_icon="🎥",
    layout="wide"
)

FANCAM_PATH = "output/fancam.mp4"
ENERGY_GRAPH_PATH = "output/analysis/energy_graph.png"
ANGLE_GRAPH_PATH = "output/analysis/angle_graph.png"
TRAJECTORY_3D_PATH = "output/analysis/trajectory_3d.png"
REPORT_PATH = "output/analysis/motion_report.txt"

st.title("🎥 BiasCam")
st.subheader("Who’s Your Bias?")

st.markdown(
    """
단체 아이돌 영상에서 선택한 멤버를 추적해 자동 직캠을 생성하고,  
해당 멤버의 안무 움직임을 에너지, 관절 각도, 3D 궤적으로 분석하는 시스템입니다.
"""
)

st.divider()

required_files = [
    FANCAM_PATH,
    ENERGY_GRAPH_PATH,
    ANGLE_GRAPH_PATH,
    TRAJECTORY_3D_PATH,
    REPORT_PATH,
]

missing_files = [path for path in required_files if not os.path.exists(path)]

if missing_files:
    st.warning("아직 생성되지 않은 결과 파일이 있습니다.")

    st.code(
        """
python src/tracking/face_match.py
python src/analysis/analyze_motion.py
python -m streamlit run app.py
"""
    )

    st.write("없는 파일:")
    for path in missing_files:
        st.write(f"- {path}")

    st.stop()

# =========================
# 1. 최애 직캠 영상
# =========================
st.header("1. 최애 멤버 자동 직캠")

with open(FANCAM_PATH, "rb") as f:
    st.video(f.read())

st.caption("단체 영상에서 선택한 멤버를 추적하고, bbox 기반 crop과 smoothing을 적용해 생성한 개인 직캠입니다.")

st.divider()

# =========================
# 2. 분석 그래프
# =========================
st.header("2. 안무 분석 결과")

col1, col2 = st.columns(2)

with col1:
    st.subheader("움직임 에너지 그래프")
    st.image(ENERGY_GRAPH_PATH, use_container_width=True)

with col2:
    st.subheader("관절 각도 그래프")
    st.image(ANGLE_GRAPH_PATH, use_container_width=True)

st.subheader("Pseudo-3D 관절 궤적")
st.image(TRAJECTORY_3D_PATH, use_container_width=True)

st.divider()

# =========================
# 3. 분석 리포트
# =========================
st.header("3. 분석 리포트")

with open(REPORT_PATH, "r", encoding="utf-8") as f:
    report = f.read()

st.text_area(
    "BiasCam Motion Analysis Report",
    value=report,
    height=450
)

st.divider()

# =========================
# 4. 파이프라인 설명
# =========================
st.header("4. 전체 파이프라인")

st.markdown(
    """
```text
단체 아이돌 영상 입력
        ↓
첫 프레임에서 최애 멤버 선택
        ↓
MediaPipe Face Detection + FaceMesh 기반 추적
        ↓
bbox smoothing + 자동 crop
        ↓
최애 멤버 직캠 생성
        ↓
MediaPipe Pose 기반 안무 분석
        ↓
에너지 / 각도 / pseudo-3D 궤적 / 리포트 출력
"""
)

st.success("BiasCam 결과 대시보드가 정상적으로 로드되었습니다.")