diff --git a/app.py b/app.py
index bf85c2e77c3dd41f9a304cb5e131777fbfac5e88..05866f4759de5380037b9ce5d0927fe31ec1976b 100644
--- a/app.py
+++ b/app.py
@@ -1,93 +1,251 @@
 # app.py
 # Streamlit: AI 습관 트래커 (단일 파일)
 # 실행: streamlit run app.py
 
 from __future__ import annotations
 
-import os
+import calendar
 import json
-import time
-from dataclasses import dataclass
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
 
+st.markdown(
+    """
+<style>
+:root {
+  --bg: #0f172a;
+  --card: #111827;
+  --muted: #94a3b8;
+  --accent: #38bdf8;
+  --success: #22c55e;
+  --warning: #f59e0b;
+  --danger: #ef4444;
+}
+.app-subtitle { color: var(--muted); margin-top: -12px; margin-bottom: 24px; }
+.section-title { margin-top: 16px; margin-bottom: 8px; }
+.card {
+  background: var(--card);
+  padding: 16px 18px;
+  border-radius: 16px;
+  border: 1px solid rgba(148, 163, 184, 0.15);
+  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.2);
+}
+.card h4 { margin: 0 0 8px 0; }
+.muted { color: var(--muted); }
+.pill {
+  display: inline-flex;
+  align-items: center;
+  gap: 6px;
+  padding: 4px 10px;
+  border-radius: 999px;
+  background: rgba(56, 189, 248, 0.15);
+  color: #e0f2fe;
+  font-size: 12px;
+  font-weight: 600;
+}
+.calendar {
+  width: 100%;
+  border-collapse: separate;
+  border-spacing: 6px;
+}
+.calendar th {
+  text-align: center;
+  font-size: 12px;
+  color: var(--muted);
+  padding: 4px 0;
+}
+.calendar td {
+  text-align: center;
+  padding: 10px 0;
+  border-radius: 12px;
+  font-size: 13px;
+  font-weight: 600;
+  color: #e2e8f0;
+}
+.calendar .empty {
+  background: transparent;
+  border: 1px dashed rgba(148, 163, 184, 0.1);
+  color: transparent;
+}
+.calendar-legend {
+  display: flex;
+  align-items: center;
+  gap: 8px;
+  font-size: 12px;
+  color: var(--muted);
+  margin-top: 12px;
+}
+.legend-box {
+  width: 16px;
+  height: 10px;
+  border-radius: 999px;
+}
+</style>
+""",
+    unsafe_allow_html=True,
+)
+st.markdown('<p class="app-subtitle">습관 · 리포트 · API를 하나의 흐름으로 정리한 데일리 트래커</p>', unsafe_allow_html=True)
+
 with st.sidebar:
-    st.header("🔑 API 설정")
+    st.header("🛠️ 설정")
+    st.caption("앱 설정은 사이드바에서 관리하고, 본문에서는 습관과 리포트에 집중하세요.")
+    st.subheader("🔑 API")
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
 
 
+def _pct_to_color(pct: float) -> str:
+    if pct >= 90:
+        return "#22c55e"
+    if pct >= 70:
+        return "#38bdf8"
+    if pct >= 40:
+        return "#f59e0b"
+    if pct > 0:
+        return "#fb7185"
+    return "#1f2937"
+
+
+def _calendar_matrix(year: int, month: int) -> List[List[Optional[int]]]:
+    cal = calendar.Calendar(firstweekday=0)
+    weeks = cal.monthdayscalendar(year, month)
+    return [[day if day != 0 else None for day in week] for week in weeks]
+
+
+def calc_streak(history_rows: List[Dict[str, float]]) -> int:
+    streak = 0
+    today = datetime.now().date()
+    history_map = {row["date"]: row for row in history_rows}
+    for offset in range(0, 365):
+        day = today - timedelta(days=offset)
+        key = day.strftime("%Y-%m-%d")
+        row = history_map.get(key)
+        if row and row.get("done", 0) > 0:
+            streak += 1
+        else:
+            break
+    return streak
+
+
+def render_calendar(history_rows: List[Dict[str, float]], focus_date: datetime) -> None:
+    history_map = {row["date"]: row for row in history_rows}
+    year = focus_date.year
+    month = focus_date.month
+    weeks = _calendar_matrix(year, month)
+    month_label = focus_date.strftime("%Y년 %m월")
+
+    st.markdown(f"#### 🗓️ {month_label}")
+    table = ['<table class="calendar">']
+    table.append("<thead><tr>")
+    for day in ["월", "화", "수", "목", "금", "토", "일"]:
+        table.append(f"<th>{day}</th>")
+    table.append("</tr></thead><tbody>")
+    for week in weeks:
+        table.append("<tr>")
+        for day in week:
+            if not day:
+                table.append('<td class="empty">.</td>')
+                continue
+            date_key = f"{year}-{month:02d}-{day:02d}"
+            row = history_map.get(date_key)
+            pct = row["pct"] if row else 0
+            mood = row.get("mood") if row else None
+            color = _pct_to_color(pct)
+            label = f"{day}<br/><span style='font-size:11px; color:#e2e8f0'>{pct:.0f}%</span>"
+            if mood:
+                label += f"<div style='font-size:11px; color:#cbd5f5'>🙂 {mood}</div>"
+            table.append(
+                f"<td style='background:{color};'>{label}</td>"
+            )
+        table.append("</tr>")
+    table.append("</tbody></table>")
+    st.markdown("".join(table), unsafe_allow_html=True)
+
+    st.markdown(
+        """
+<div class="calendar-legend">
+  <span class="legend-box" style="background:#1f2937;"></span>미기록
+  <span class="legend-box" style="background:#fb7185;"></span>낮음
+  <span class="legend-box" style="background:#f59e0b;"></span>보통
+  <span class="legend-box" style="background:#38bdf8;"></span>높음
+  <span class="legend-box" style="background:#22c55e;"></span>아주 높음
+</div>
+""",
+        unsafe_allow_html=True,
+    )
+
+
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
@@ -311,249 +469,266 @@ def generate_report(
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
-# 습관 체크인 UI
+# 메인 UI
 # -----------------------------
 record = st.session_state.today_record
-
-st.subheader("✅ 오늘의 체크인")
-
-col_a, col_b = st.columns([1.2, 1.0], gap="large")
-
-with col_a:
-    st.markdown("#### 🧩 습관 체크")
-    c1, c2 = st.columns(2, gap="medium")
-
-    # 2열로 체크박스 5개 배치
-    for idx, (key, emoji, label) in enumerate(HABITS):
-        target_col = c1 if idx % 2 == 0 else c2
-        with target_col:
-            record["habits"][key] = st.checkbox(
-                f"{emoji} {label}",
-                value=bool(record["habits"].get(key, False)),
-                key=f"habit_{key}",
-            )
-
-    st.markdown("#### 🙂 기분")
-    record["mood"] = st.slider(
-        "오늘 기분은 몇 점인가요?",
-        min_value=1, max_value=10,
-        value=int(record.get("mood", 7)),
-        key="mood_slider",
-    )
-
-with col_b:
-    st.markdown("#### 🌍 환경 설정")
-    record["city"] = st.selectbox(
-        "도시 선택",
-        options=CITIES,
-        index=CITIES.index(record.get("city", "Seoul")) if record.get("city", "Seoul") in CITIES else 0,
-        key="city_select",
-    )
-    record["coach_style"] = st.radio(
-        "코치 스타일",
-        options=list(COACH_STYLES.keys()),
-        index=list(COACH_STYLES.keys()).index(record.get("coach_style", "따뜻한 멘토"))
-        if record.get("coach_style", "따뜻한 멘토") in COACH_STYLES else 1,
-        key="coach_style_radio",
-    )
-    st.caption(COACH_STYLES.get(record["coach_style"], ""))
-
-
-# -----------------------------
-# 달성률 + 메트릭
-# -----------------------------
 done_cnt, pct = calc_achievement(record["habits"])
 
-m1, m2, m3 = st.columns(3, gap="medium")
-m1.metric("달성률", f"{pct:.0f}%")
-m2.metric("달성 습관", f"{done_cnt}/{len(HABITS)}")
-m3.metric("기분", f"{record['mood']}/10")
-
-st.divider()
-
-# -----------------------------
-# 7일 바 차트 (6일 샘플 + 오늘)
-# -----------------------------
-# 오늘 값을 history에 반영하기 위해, 버튼 누르기 전이라도 "오늘 행"은 차트에만 합성
-history_rows = list(st.session_state.history)
-
 today_row = {
     "date": _today_str(),
     "done": done_cnt,
     "pct": (done_cnt / 5) * 100,
     "mood": record["mood"],
 }
+history_rows = list(st.session_state.history)
 chart_rows = history_rows + [today_row]
 df = pd.DataFrame(chart_rows)
+streak = calc_streak(chart_rows)
 
-st.subheader("📈 최근 7일 달성 현황")
-c_chart, c_note = st.columns([1.2, 0.8], gap="large")
-
-with c_chart:
-    # Streamlit 기본 bar_chart는 wide 데이터가 보기 좋아서 pivot
-    df_plot = df.set_index("date")[["pct"]]
-    st.bar_chart(df_plot, height=280)
-
-with c_note:
-    best_day = df.loc[df["pct"].idxmax(), "date"]
-    st.markdown("#### 🧠 인사이트(간단)")
-    st.write(f"- 최고 달성일: **{best_day}**")
-    st.write(f"- 오늘 달성률: **{pct:.0f}%**")
-    st.write("- 아래 버튼으로 오늘 기록을 저장하고 AI 리포트를 생성할 수 있습니다.")
+if "report_cache" not in st.session_state:
+    st.session_state.report_cache = {"weather": None, "dog": None, "text": None}
 
+tab_home, tab_habits, tab_calendar, tab_report, tab_api = st.tabs(
+    ["🏠 홈", "✅ 습관", "🗓️ 캘린더", "🧾 리포트", "ℹ️ API"]
+)
 
-# -----------------------------
-# 결과 표시: 버튼 / 카드 / 리포트 / 공유 텍스트
-# -----------------------------
-st.divider()
-st.subheader("🧾 컨디션 리포트")
-
-btn_col1, btn_col2 = st.columns([0.25, 0.75], gap="medium")
-with btn_col1:
-    generate_clicked = st.button("컨디션 리포트 생성", use_container_width=True)
-
-status_area = btn_col2.empty()
-
-weather_data = None
-dog_data = None
-report_text = None
-
-if generate_clicked:
-    # 1) 오늘 기록 저장(session_state)
-    # history는 6일 샘플 + 오늘로 7일 유지
-    # 이미 오늘이 들어있으면 업데이트, 없으면 append
-    updated = False
-    for row in st.session_state.history:
-        if row.get("date") == _today_str():
-            row.update(today_row)
-            updated = True
-            break
-    if not updated:
-        st.session_state.history.append(today_row)
-
-    # 길이 유지 (최근 7개)
-    st.session_state.history = st.session_state.history[-7:]
-
-    # 2) 외부 API 호출
-    with status_area:
-        st.info("날씨/강아지 데이터를 불러오고 AI 리포트를 생성합니다...")
-
-    weather_data = get_weather(record["city"], owm_api_key)
-    dog_data = get_dog_image()
-
-    # 3) OpenAI 리포트 생성
-    report_text = generate_report(
-        openai_key=openai_api_key,
-        coach_style=record["coach_style"],
-        habit_state=record["habits"],
-        mood=record["mood"],
-        weather=weather_data,
-        dog=dog_data,
+with tab_home:
+    st.markdown("### 오늘의 요약")
+    h1, h2, h3, h4 = st.columns([1, 1, 1, 1], gap="large")
+    h1.markdown(
+        f"<div class='card'><h4>오늘 달성률</h4><div style='font-size:28px;font-weight:700'>{pct:.0f}%</div><div class='muted'>총 {done_cnt}/{len(HABITS)} 습관</div></div>",
+        unsafe_allow_html=True,
+    )
+    h2.markdown(
+        f"<div class='card'><h4>연속 기록</h4><div style='font-size:28px;font-weight:700'>{streak}일</div><div class='muted'>끊기지 않게 이어가기</div></div>",
+        unsafe_allow_html=True,
     )
+    h3.markdown(
+        f"<div class='card'><h4>오늘 기분</h4><div style='font-size:28px;font-weight:700'>{record['mood']}/10</div><div class='muted'>컨디션을 함께 기록</div></div>",
+        unsafe_allow_html=True,
+    )
+    h4.markdown(
+        f"<div class='card'><h4>선택한 코치</h4><div style='font-size:18px;font-weight:700'>{record['coach_style']}</div><div class='muted'>{COACH_STYLES.get(record['coach_style'], '')}</div></div>",
+        unsafe_allow_html=True,
+    )
+
+    st.markdown("### 주간 흐름")
+    c_chart, c_note = st.columns([1.2, 0.8], gap="large")
+    with c_chart:
+        df_plot = df.set_index("date")[["pct"]]
+        st.bar_chart(df_plot, height=260)
+    with c_note:
+        best_day = df.loc[df["pct"].idxmax(), "date"]
+        st.markdown(
+            f"""
+<div class='card'>
+  <h4>오늘의 인사이트</h4>
+  <p class='muted'>최고 달성일: <strong>{best_day}</strong></p>
+  <p class='muted'>오늘 달성률: <strong>{pct:.0f}%</strong></p>
+  <p class='muted'>리포트 탭에서 AI 요약을 생성할 수 있어요.</p>
+</div>
+""",
+            unsafe_allow_html=True,
+        )
+
+with tab_habits:
+    st.markdown("### ✅ 오늘의 습관 체크")
+    col_a, col_b = st.columns([1.3, 1.0], gap="large")
+
+    with col_a:
+        st.markdown("#### 🧩 습관 목록")
+        c1, c2 = st.columns(2, gap="medium")
+        for idx, (key, emoji, label) in enumerate(HABITS):
+            target_col = c1 if idx % 2 == 0 else c2
+            with target_col:
+                record["habits"][key] = st.checkbox(
+                    f"{emoji} {label}",
+                    value=bool(record["habits"].get(key, False)),
+                    key=f"habit_{key}",
+                )
+
+        st.markdown("#### 🙂 기분")
+        record["mood"] = st.slider(
+            "오늘 기분은 몇 점인가요?",
+            min_value=1,
+            max_value=10,
+            value=int(record.get("mood", 7)),
+            key="mood_slider",
+        )
+
+    with col_b:
+        st.markdown("#### 🌍 환경 설정")
+        record["city"] = st.selectbox(
+            "도시 선택",
+            options=CITIES,
+            index=CITIES.index(record.get("city", "Seoul")) if record.get("city", "Seoul") in CITIES else 0,
+            key="city_select",
+        )
+        record["coach_style"] = st.radio(
+            "코치 스타일",
+            options=list(COACH_STYLES.keys()),
+            index=list(COACH_STYLES.keys()).index(record.get("coach_style", "따뜻한 멘토"))
+            if record.get("coach_style", "따뜻한 멘토") in COACH_STYLES else 1,
+            key="coach_style_radio",
+        )
+        st.caption(COACH_STYLES.get(record["coach_style"], ""))
+        st.markdown(
+            "<div class='card'><h4>오늘의 체크 팁</h4><p class='muted'>습관 체크는 <strong>오늘 목표를 완료한 후</strong>에 눌러 주세요. 작은 완료 표시가 큰 동기부여가 됩니다.</p></div>",
+            unsafe_allow_html=True,
+        )
+
+with tab_calendar:
+    st.markdown("### 🗓️ 달력 기반 습관 기록")
+    month_options = [
+        datetime.now(),
+        datetime.now() - timedelta(days=30),
+        datetime.now() - timedelta(days=60),
+    ]
+    month_labels = [d.strftime("%Y-%m") for d in month_options]
+    selected = st.selectbox("월 선택", month_labels, index=0)
+    focus_date = datetime.strptime(f"{selected}-01", "%Y-%m-%d")
+    render_calendar(chart_rows, focus_date)
+    st.markdown("### 📈 최근 7일 달성 현황")
+    st.bar_chart(df.set_index("date")[["pct"]], height=220)
+
+with tab_report:
+    st.markdown("### 🧾 컨디션 리포트")
+    btn_col1, btn_col2 = st.columns([0.25, 0.75], gap="medium")
+    with btn_col1:
+        generate_clicked = st.button("컨디션 리포트 생성", use_container_width=True)
+    status_area = btn_col2.empty()
+
+    if generate_clicked:
+        updated = False
+        for row in st.session_state.history:
+            if row.get("date") == _today_str():
+                row.update(today_row)
+                updated = True
+                break
+        if not updated:
+            st.session_state.history.append(today_row)
+        st.session_state.history = st.session_state.history[-7:]
+
+        with status_area:
+            st.info("날씨/강아지 데이터를 불러오고 AI 리포트를 생성합니다...")
+
+        weather_data = get_weather(record["city"], owm_api_key)
+        dog_data = get_dog_image()
+        report_text = generate_report(
+            openai_key=openai_api_key,
+            coach_style=record["coach_style"],
+            habit_state=record["habits"],
+            mood=record["mood"],
+            weather=weather_data,
+            dog=dog_data,
+        )
+
+        st.session_state.report_cache = {
+            "weather": weather_data,
+            "dog": dog_data,
+            "text": report_text,
+        }
 
-    with status_area:
-        if not openai_api_key:
-            st.warning("OpenAI API Key가 필요합니다. 사이드바에 입력하세요.")
-        elif report_text is None:
-            st.error("AI 리포트 생성에 실패했습니다. 키/네트워크/모델 설정을 확인하세요.")
+        with status_area:
+            if not openai_api_key:
+                st.warning("OpenAI API Key가 필요합니다. 사이드바에 입력하세요.")
+            elif report_text is None:
+                st.error("AI 리포트 생성에 실패했습니다. 키/네트워크/모델 설정을 확인하세요.")
+            else:
+                st.success("리포트 생성 완료")
+
+    weather_data = st.session_state.report_cache.get("weather")
+    dog_data = st.session_state.report_cache.get("dog")
+    report_text = st.session_state.report_cache.get("text")
+
+    card1, card2 = st.columns(2, gap="large")
+    with card1:
+        st.markdown("#### 🌦️ 오늘의 날씨")
+        if weather_data:
+            st.metric("도시", weather_data.get("city", record["city"]))
+            st.write(f"- 상태: **{weather_data.get('desc_kr', '')}**")
+            st.write(
+                f"- 기온: **{weather_data.get('temp_c', '')}°C** (체감 {weather_data.get('feels_like_c', '')}°C)"
+            )
+            st.write(
+                f"- 습도: **{weather_data.get('humidity', '')}%** / 바람: **{weather_data.get('wind_ms', '')} m/s**"
+            )
+        elif generate_clicked:
+            st.caption("날씨 정보를 가져오지 못했습니다(키/도시/네트워크 확인).")
         else:
-            st.success("리포트 생성 완료")
-
-# 카드 2열: 날씨 + 강아지
-card1, card2 = st.columns(2, gap="large")
-
-with card1:
-    st.markdown("#### 🌦️ 오늘의 날씨")
-    if generate_clicked and weather_data:
-        st.metric("도시", weather_data.get("city", record["city"]))
-        st.write(f"- 상태: **{weather_data.get('desc_kr', '')}**")
-        st.write(f"- 기온: **{weather_data.get('temp_c', '')}°C** (체감 {weather_data.get('feels_like_c', '')}°C)")
-        st.write(f"- 습도: **{weather_data.get('humidity', '')}%** / 바람: **{weather_data.get('wind_ms', '')} m/s**")
-    elif generate_clicked and not weather_data:
-        st.caption("날씨 정보를 가져오지 못했습니다(키/도시/네트워크 확인).")
-    else:
-        st.caption("버튼을 누르면 날씨 카드가 채워집니다.")
-
-with card2:
-    st.markdown("#### 🐶 오늘의 강아지")
-    if generate_clicked and dog_data:
-        st.write(f"- 품종(추정): **{dog_data.get('breed', 'Unknown')}**")
-        st.image(dog_data.get("url", ""), use_container_width=True)
-    elif generate_clicked and not dog_data:
-        st.caption("강아지 이미지를 가져오지 못했습니다(네트워크 확인).")
-    else:
-        st.caption("버튼을 누르면 랜덤 강아지가 등장합니다.")
+            st.caption("버튼을 누르면 날씨 카드가 채워집니다.")
 
+    with card2:
+        st.markdown("#### 🐶 오늘의 강아지")
+        if dog_data:
+            st.write(f"- 품종(추정): **{dog_data.get('breed', 'Unknown')}**")
+            st.image(dog_data.get("url", ""), use_container_width=True)
+        elif generate_clicked:
+            st.caption("강아지 이미지를 가져오지 못했습니다(네트워크 확인).")
+        else:
+            st.caption("버튼을 누르면 랜덤 강아지가 등장합니다.")
 
-# AI 리포트 본문 + 공유 텍스트
-st.markdown("#### 🤖 AI 코치 리포트")
-if generate_clicked:
+    st.markdown("#### 🤖 AI 코치 리포트")
     if report_text:
         st.markdown(report_text)
 
-        # 공유용 텍스트
-        share_lines = []
-        share_lines.append(f"📊 AI 습관 트래커 - {_today_str()}")
-        share_lines.append(f"도시: {record['city']} / 코치: {record['coach_style']}")
-        share_lines.append(f"달성률: {pct:.0f}% ({done_cnt}/5) / 기분: {record['mood']}/10")
+        share_lines = [
+            f"📊 AI 습관 트래커 - {_today_str()}",
+            f"도시: {record['city']} / 코치: {record['coach_style']}",
+            f"달성률: {pct:.0f}% ({done_cnt}/5) / 기분: {record['mood']}/10",
+        ]
         if weather_data:
             share_lines.append(f"날씨: {weather_data.get('desc_kr','')} {weather_data.get('temp_c','')}°C")
         if dog_data:
             share_lines.append(f"오늘의 강아지: {dog_data.get('breed','Unknown')}")
-        share_lines.append("")
-        share_lines.append(report_text.strip())
+        share_lines.extend(["", report_text.strip()])
 
         st.markdown("#### 🔗 공유용 텍스트")
         st.code("\n".join(share_lines), language="markdown")
     else:
         st.caption("리포트가 비어있습니다. 설정을 확인 후 다시 시도하세요.")
-else:
-    st.caption("버튼을 눌러 리포트를 생성하세요.")
 
-
-# -----------------------------
-# API 안내 (expander)
-# -----------------------------
-with st.expander("📌 API 안내 / 트러블슈팅"):
+with tab_api:
+    st.markdown("### 📌 API 안내 / 트러블슈팅")
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
