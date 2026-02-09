# app.py
# Streamlit: AI 습관 트래커 (단일 파일)
# 실행: streamlit run app.py

from __future__ import annotations

import os
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st


# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="AI 습관 트래커", page_icon="📊", layout="wide")
st.title("📊 AI 습관 트래커")

with st.sidebar:
    st.header("🔑 API 설정")
    openai_api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    owm_api_key = st.text_input("OpenWeatherMap API Key", type="password", placeholder="OWM API Key")
    st.caption("키는 브라우저 세션(session_state)에만 사용됩니다. 배포 시 Secrets 사용 권장.")


# -----------------------------
# 상수 / 유틸
# -----------------------------
HABITS = [
    ("wake", "🌅", "기상 미션"),
    ("water", "💧", "물 마시기"),
    ("study", "📚", "공부/독서"),
    ("workout", "🏃", "운동하기"),
    ("sleep", "😴", "수면"),
]

CITIES = [
    "Seoul", "Busan", "Incheon", "Daegu", "Daejeon",
    "Gwangju", "Suwon", "Ulsan", "Jeju", "Sejong"
]

COACH_STYLES = {
    "스파르타 코치": "엄격하고 단호한 코치. 변명은 컷, 행동만 강조.",
    "따뜻한 멘토": "공감과 격려 중심. 작은 성취를 칭찬하고 지속을 돕는 멘토.",
    "게임 마스터": "RPG 세계관. 퀘스트/레벨/보상/보스전 같은 표현을 사용.",
}


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(x)))


def calc_achievement(habit_state: Dict[str, bool]) -> Tuple[int, float]:
    done = sum(1 for k, _, _ in HABITS if habit_state.get(k, False))
    pct = (done / len(HABITS)) * 100.0
    return done, pct


# -----------------------------
# session_state 초기화
# -----------------------------
def init_state() -> None:
    if "history" not in st.session_state:
        # 데모용 6일 샘플 데이터 + 오늘은 사용자가 입력
        base = datetime.now().date()
        sample_days = 6
        rows = []
        # 샘플은 약간의 변동을 주기 위한 패턴
        patterns = [
            (3, 6), (4, 7), (2, 5), (5, 8), (3, 7), (4, 6)
        ]
        for i in range(sample_days, 0, -1):
            d = base - timedelta(days=i)
            done, mood = patterns[(sample_days - i) % len(patterns)]
            pct = (done / 5) * 100
            rows.append({"date": d.strftime("%Y-%m-%d"), "done": done, "pct": pct, "mood": mood})
        st.session_state.history = rows

    if "today_record" not in st.session_state:
        st.session_state.today_record = {
            "date": _today_str(),
            "habits": {k: False for k, _, _ in HABITS},
            "mood": 7,
            "city": "Seoul",
            "coach_style": "따뜻한 멘토",
        }


init_state()


# -----------------------------
# API 연동: 날씨 / 강아지
# -----------------------------
def get_weather(city: str, api_key: str) -> Optional[Dict[str, str]]:
    """
    OpenWeatherMap에서 날씨 가져오기 (한국어, 섭씨)
    실패 시 None 반환, timeout=10
    반환 예:
      {
        "city": "Seoul",
        "temp_c": "2.3",
        "feels_like_c": "0.1",
        "desc_kr": "흐림",
        "humidity": "55",
        "wind_ms": "2.1"
      }
    """
    if not city or not api_key:
        return None
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "kr",
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        main = data.get("main", {}) or {}
        weather0 = (data.get("weather") or [{}])[0] or {}
        wind = data.get("wind", {}) or {}
        return {
            "city": str(data.get("name") or city),
            "temp_c": f"{main.get('temp', '')}",
            "feels_like_c": f"{main.get('feels_like', '')}",
            "desc_kr": str(weather0.get("description") or ""),
            "humidity": f"{main.get('humidity', '')}",
            "wind_ms": f"{wind.get('speed', '')}",
        }
    except Exception:
        return None


def _breed_from_dog_url(url: str) -> Optional[str]:
    # Dog CEO URL 예: https://images.dog.ceo/breeds/hound-afghan/n02088094_1003.jpg
    # breeds/{breed}/... or breeds/{breed-sub}/...
    try:
        parts = url.split("/")
        if "breeds" not in parts:
            return None
        i = parts.index("breeds")
        breed_part = parts[i + 1] if i + 1 < len(parts) else ""
        if not breed_part:
            return None
        breed = breed_part.replace("-", " ").strip()
        # 보기 좋게 Title Case
        return " ".join(w.capitalize() for w in breed.split())
    except Exception:
        return None


def get_dog_image() -> Optional[Dict[str, str]]:
    """
    Dog CEO에서 랜덤 강아지 사진 URL과 품종 가져오기
    실패 시 None 반환, timeout=10
    반환 예:
      {"url": "...", "breed": "Hound Afghan"}
    """
    url = "https://dog.ceo/api/breeds/image/random"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("status") != "success":
            return None
        img_url = data.get("message")
        if not img_url:
            return None
        breed = _breed_from_dog_url(img_url) or "Unknown"
        return {"url": img_url, "breed": breed}
    except Exception:
        return None


# -----------------------------
# OpenAI: 리포트 생성
# -----------------------------
SPARTA_SYSTEM = """너는 '스파르타 코치'다.
- 말투는 짧고 단호하다. 변명은 차단한다.
- 행동/습관의 빈틈을 정확히 지적하고, 내일의 구체적 실행을 요구한다.
- 불필요한 장식은 최소화한다.
"""

MENTOR_SYSTEM = """너는 '따뜻한 멘토'다.
- 공감/격려 중심. 오늘의 노력에서 의미를 찾아준다.
- 하지만 현실적인 조언과 작은 다음 행동을 제시한다.
- 다정하지만 과장된 칭찬은 피한다.
"""

GAMEMASTER_SYSTEM = """너는 '게임 마스터'다.
- RPG 세계관으로 묘사한다(퀘스트/경험치/레벨/아이템/보스전 등).
- 사용자의 하루를 한 판의 게임처럼 요약하고 내일 퀘스트를 제시한다.
- 유쾌하지만 내용은 구체적이어야 한다.
"""


def _coach_system_prompt(style: str) -> str:
    if style == "스파르타 코치":
        return SPARTA_SYSTEM
    if style == "게임 마스터":
        return GAMEMASTER_SYSTEM
    return MENTOR_SYSTEM


def generate_report(
    openai_key: str,
    coach_style: str,
    habit_state: Dict[str, bool],
    mood: int,
    weather: Optional[Dict[str, str]],
    dog: Optional[Dict[str, str]],
) -> Optional[str]:
    """
    습관+기분+날씨+강아지 품종을 모아서 OpenAI에 전달
    - 코치 스타일별 시스템 프롬프트
    - 출력 형식:
        컨디션 등급(S~D),
        습관 분석,
        날씨 코멘트,
        내일 미션,
        오늘의 한마디
    - 모델: gpt-5-mini
    """
    if not openai_key:
        return None

    done, pct = calc_achievement(habit_state)
    habits_done = [label for k, _, label in HABITS if habit_state.get(k, False)]
    habits_miss = [label for k, _, label in HABITS if not habit_state.get(k, False)]

    payload = {
        "date": _today_str(),
        "achievement": {"done": done, "total": len(HABITS), "pct": round(pct, 1)},
        "mood_1to10": _clamp_int(mood, 1, 10),
        "habits_done": habits_done,
        "habits_missed": habits_miss,
        "weather": weather or None,
        "dog": dog or None,
        "instructions": {
            "language": "Korean",
            "format": "Markdown",
            "required_sections": [
                "컨디션 등급(S~D)",
                "습관 분석",
                "날씨 코멘트",
                "내일 미션",
                "오늘의 한마디",
            ],
        },
    }

    sys = _coach_system_prompt(coach_style)
    user = f"""
다음은 사용자의 오늘 데이터다. 이 데이터를 기반으로 코치 리포트를 작성하라.

[오늘 데이터(JSON)]
{json.dumps(payload, ensure_ascii=False, indent=2)}

[출력 규칙]
- 반드시 아래 섹션 제목을 그대로 사용해 Markdown으로 출력:
  1) 컨디션 등급(S~D)
  2) 습관 분석
  3) 날씨 코멘트
  4) 내일 미션
  5) 오늘의 한마디
- 등급은 S/A/B/C/D 중 하나만.
- 내용은 구체적으로: 습관별로 좋았던 점/빈틈/개선 1가지를 제시.
- '내일 미션'은 3개, 체크리스트 형태.
- 너무 길지 않게(대략 12~20줄).
""".strip()

    # OpenAI SDK 호환성: Responses API 우선, 실패 시 Chat Completions로 폴백
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=openai_key)

        # 1) Responses API (권장)
        try:
            resp = client.responses.create(
                model="gpt-5-mini",
                input=[
                    {"role": "system", "content": sys},
                    {"role": "user", "content": user},
                ],
            )
            # SDK 버전에 따라 출력 접근이 다를 수 있어 방어적으로 처리
            txt = None
            if hasattr(resp, "output_text"):
                txt = resp.output_text
            if not txt and hasattr(resp, "output") and resp.output:
                # 일부 SDK는 output[*].content[*].text 형태
                chunks = []
                for item in resp.output:
                    for c in getattr(item, "content", []) or []:
                        t = getattr(c, "text", None)
                        if t:
                            chunks.append(t)
                txt = "\n".join(chunks).strip() if chunks else None
            return txt or None
        except Exception:
            pass

        # 2) Chat Completions 폴백
        try:
            cc = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": sys},
                    {"role": "user", "content": user},
                ],
            )
            return (cc.choices[0].message.content or "").strip() or None
        except Exception:
            return None

    except Exception:
        return None


# -----------------------------
# 습관 체크인 UI
# -----------------------------
record = st.session_state.today_record

st.subheader("✅ 오늘의 체크인")

col_a, col_b = st.columns([1.2, 1.0], gap="large")

with col_a:
    st.markdown("#### 🧩 습관 체크")
    c1, c2 = st.columns(2, gap="medium")

    # 2열로 체크박스 5개 배치
    for idx, (key, emoji, label) in enumerate(HABITS):
        target_col = c1 if idx % 2 == 0 else c2
        with target_col:
            record["habits"][key] = st.checkbox(
                f"{emoji} {label}",
                value=bool(record["habits"].get(key, False)),
                key=f"habit_{key}",
            )

    st.markdown("#### 🙂 기분")
    record["mood"] = st.slider(
        "오늘 기분은 몇 점인가요?",
        min_value=1, max_value=10,
        value=int(record.get("mood", 7)),
        key="mood_slider",
    )

with col_b:
    st.markdown("#### 🌍 환경 설정")
    record["city"] = st.selectbox(
        "도시 선택",
        options=CITIES,
        index=CITIES.index(record.get("city", "Seoul")) if record.get("city", "Seoul") in CITIES else 0,
        key="city_select",
    )
    record["coach_style"] = st.radio(
        "코치 스타일",
        options=list(COACH_STYLES.keys()),
        index=list(COACH_STYLES.keys()).index(record.get("coach_style", "따뜻한 멘토"))
        if record.get("coach_style", "따뜻한 멘토") in COACH_STYLES else 1,
        key="coach_style_radio",
    )
    st.caption(COACH_STYLES.get(record["coach_style"], ""))


# -----------------------------
# 달성률 + 메트릭
# -----------------------------
done_cnt, pct = calc_achievement(record["habits"])

m1, m2, m3 = st.columns(3, gap="medium")
m1.metric("달성률", f"{pct:.0f}%")
m2.metric("달성 습관", f"{done_cnt}/{len(HABITS)}")
m3.metric("기분", f"{record['mood']}/10")

st.divider()

# -----------------------------
# 7일 바 차트 (6일 샘플 + 오늘)
# -----------------------------
# 오늘 값을 history에 반영하기 위해, 버튼 누르기 전이라도 "오늘 행"은 차트에만 합성
history_rows = list(st.session_state.history)

today_row = {
    "date": _today_str(),
    "done": done_cnt,
    "pct": (done_cnt / 5) * 100,
    "mood": record["mood"],
}
chart_rows = history_rows + [today_row]
df = pd.DataFrame(chart_rows)

st.subheader("📈 최근 7일 달성 현황")
c_chart, c_note = st.columns([1.2, 0.8], gap="large")

with c_chart:
    # Streamlit 기본 bar_chart는 wide 데이터가 보기 좋아서 pivot
    df_plot = df.set_index("date")[["pct"]]
    st.bar_chart(df_plot, height=280)

with c_note:
    best_day = df.loc[df["pct"].idxmax(), "date"]
    st.markdown("#### 🧠 인사이트(간단)")
    st.write(f"- 최고 달성일: **{best_day}**")
    st.write(f"- 오늘 달성률: **{pct:.0f}%**")
    st.write("- 아래 버튼으로 오늘 기록을 저장하고 AI 리포트를 생성할 수 있습니다.")


# -----------------------------
# 결과 표시: 버튼 / 카드 / 리포트 / 공유 텍스트
# -----------------------------
st.divider()
st.subheader("🧾 컨디션 리포트")

btn_col1, btn_col2 = st.columns([0.25, 0.75], gap="medium")
with btn_col1:
    generate_clicked = st.button("컨디션 리포트 생성", use_container_width=True)

status_area = btn_col2.empty()

weather_data = None
dog_data = None
report_text = None

if generate_clicked:
    # 1) 오늘 기록 저장(session_state)
    # history는 6일 샘플 + 오늘로 7일 유지
    # 이미 오늘이 들어있으면 업데이트, 없으면 append
    updated = False
    for row in st.session_state.history:
        if row.get("date") == _today_str():
            row.update(today_row)
            updated = True
            break
    if not updated:
        st.session_state.history.append(today_row)

    # 길이 유지 (최근 7개)
    st.session_state.history = st.session_state.history[-7:]

    # 2) 외부 API 호출
    with status_area:
        st.info("날씨/강아지 데이터를 불러오고 AI 리포트를 생성합니다...")

    weather_data = get_weather(record["city"], owm_api_key)
    dog_data = get_dog_image()

    # 3) OpenAI 리포트 생성
    report_text = generate_report(
        openai_key=openai_api_key,
        coach_style=record["coach_style"],
        habit_state=record["habits"],
        mood=record["mood"],
        weather=weather_data,
        dog=dog_data,
    )

    with status_area:
        if not openai_api_key:
            st.warning("OpenAI API Key가 필요합니다. 사이드바에 입력하세요.")
        elif report_text is None:
            st.error("AI 리포트 생성에 실패했습니다. 키/네트워크/모델 설정을 확인하세요.")
        else:
            st.success("리포트 생성 완료")

# 카드 2열: 날씨 + 강아지
card1, card2 = st.columns(2, gap="large")

with card1:
    st.markdown("#### 🌦️ 오늘의 날씨")
    if generate_clicked and weather_data:
        st.metric("도시", weather_data.get("city", record["city"]))
        st.write(f"- 상태: **{weather_data.get('desc_kr', '')}**")
        st.write(f"- 기온: **{weather_data.get('temp_c', '')}°C** (체감 {weather_data.get('feels_like_c', '')}°C)")
        st.write(f"- 습도: **{weather_data.get('humidity', '')}%** / 바람: **{weather_data.get('wind_ms', '')} m/s**")
    elif generate_clicked and not weather_data:
        st.caption("날씨 정보를 가져오지 못했습니다(키/도시/네트워크 확인).")
    else:
        st.caption("버튼을 누르면 날씨 카드가 채워집니다.")

with card2:
    st.markdown("#### 🐶 오늘의 강아지")
    if generate_clicked and dog_data:
        st.write(f"- 품종(추정): **{dog_data.get('breed', 'Unknown')}**")
        st.image(dog_data.get("url", ""), use_container_width=True)
    elif generate_clicked and not dog_data:
        st.caption("강아지 이미지를 가져오지 못했습니다(네트워크 확인).")
    else:
        st.caption("버튼을 누르면 랜덤 강아지가 등장합니다.")


# AI 리포트 본문 + 공유 텍스트
st.markdown("#### 🤖 AI 코치 리포트")
if generate_clicked:
    if report_text:
        st.markdown(report_text)

        # 공유용 텍스트
        share_lines = []
        share_lines.append(f"📊 AI 습관 트래커 - {_today_str()}")
        share_lines.append(f"도시: {record['city']} / 코치: {record['coach_style']}")
        share_lines.append(f"달성률: {pct:.0f}% ({done_cnt}/5) / 기분: {record['mood']}/10")
        if weather_data:
            share_lines.append(f"날씨: {weather_data.get('desc_kr','')} {weather_data.get('temp_c','')}°C")
        if dog_data:
            share_lines.append(f"오늘의 강아지: {dog_data.get('breed','Unknown')}")
        share_lines.append("")
        share_lines.append(report_text.strip())

        st.markdown("#### 🔗 공유용 텍스트")
        st.code("\n".join(share_lines), language="markdown")
    else:
        st.caption("리포트가 비어있습니다. 설정을 확인 후 다시 시도하세요.")
else:
    st.caption("버튼을 눌러 리포트를 생성하세요.")


# -----------------------------
# API 안내 (expander)
# -----------------------------
with st.expander("📌 API 안내 / 트러블슈팅"):
    st.markdown(
        """
- **OpenWeatherMap**
  - 키 발급: OpenWeatherMap 계정 생성 후 API Key 생성
  - 호출: `api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric&lang=kr`
  - 본 앱은 **섭씨(metric)**, **한국어(lang=kr)** 로 요청합니다. (timeout=10)

- **Dog CEO**
  - 랜덤 이미지: `https://dog.ceo/api/breeds/image/random` (timeout=10)
  - 품종은 이미지 URL 경로에서 **추정**합니다.

- **OpenAI**
  - 모델: `gpt-5-mini`
  - SDK 버전에 따라 Responses API 또는 Chat Completions로 호출합니다.
  - 실패 시: 키/네트워크/모델 접근 권한을 확인하세요.

- **배포 팁**
  - Streamlit Cloud 사용 시: `st.secrets["OPENAI_API_KEY"]` 같은 방식으로 키를 보관하세요.
"""
    )
