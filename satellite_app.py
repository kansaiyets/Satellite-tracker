import streamlit as st
import pandas as pd
import requests
import io
from pyorbital.orbital import Orbital
from datetime import datetime
from rapidfuzz import process
import folium
from folium.plugins import MarkerCluster

# UCSデータを読み込む
@st.cache_data
def load_ucs_data():
    url = "https://www.ucsusa.org/sites/default/files/2024-01/UCS-Satellite-Database%205-1-2023%20%28text%29.txt"
    return pd.read_csv(url, sep="\t", encoding="ISO-8859-1")

# TLEデータを読み込む
@st.cache_data
def load_tle_data():
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    response = requests.get(url)
    lines = response.text.strip().splitlines()

    tle_entries = []
    for i in range(0, len(lines), 3):
        if i + 2 >= len(lines):
            continue
        name = lines[i].strip()
        line1 = lines[i + 1].strip()
        line2 = lines[i + 2].strip()
        tle_entries.append({
            "OBJECT_NAME": name,
            "TLE_LINE1": line1,
            "TLE_LINE2": line2
        })
    return pd.DataFrame(tle_entries)

# UCS名の前処理
def preprocess_ucs_name(name):
    if pd.isna(name):
        return []
    name = name.replace("（", "(").replace("）", ")")  # 全角括弧を半角に統一
    parts = name.split(",")
    result = []
    for part in parts:
        if "(" in part and ")" in part:
            main, rest = part.split("(", 1)
            rest = rest.rstrip(")")
            result.append(main.strip())
            result.append(rest.strip())
        else:
            result.append(part.strip())
    return list(set(result))

# ユーザー名を正規化する
def normalize_users(user):
    if pd.isna(user):
        return "不明"
    parts = [p.strip() for p in user.split("/")]
    return "/".join(sorted(parts))

# UCSとTLEのデータをマッチングする
def match_satellites(ucs_df, tle_df):
    matches = []
    for idx, tle_row in tle_df.iterrows():
        tle_name = tle_row["OBJECT_NAME"]
        match_found = False

        for ucs_idx, ucs_row in ucs_df.iterrows():
            names = preprocess_ucs_name(ucs_row["Name of Satellite, Alternate Names"])
            if not names:
                continue
            best_name, score, _ = process.extractOne(tle_name, names)
            if score < 90:
                continue
            # 打ち上げ年確認
            tle_epoch = tle_row.get("EPOCH", "")
            if isinstance(tle_epoch, str) and len(tle_epoch) >= 4:
                tle_year = int(tle_epoch[:4])
            else:
                tle_year = None

            ucs_launch = ucs_row.get("Launch Year", "")
            try:
                ucs_year = int(ucs_launch)
            except:
                ucs_year = None

            if tle_year is not None and ucs_year is not None and tle_year < ucs_year:
                continue  # エポック年が打ち上げ年より古いものは除外

            match = {
                "TLE Name": tle_name,
                "UCS Name": best_name,
                "Match Score": score,
                "OBJECT_ID": tle_row["OBJECT_ID"],
                "EPOCH": tle_row["EPOCH"],
                "Country of Operator": ucs_row.get("Country of Operator", "不明"),
                "Users": normalize_users(ucs_row.get("Users", "不明")),
                "Purpose": ucs_row.get("Purpose", "不明"),
                "Class of Orbit": tle_row.get("CLASS_OF_ORBIT", "不明"),
                "Mean Motion": tle_row.get("MEAN_MOTION", ""),
                "Inclination": tle_row.get("INCLINATION", ""),
                "Apogee": tle_row.get("APOAPSIS", ""),
                "Perigee": tle_row.get("PERIAPSIS", ""),
            }
            matches.append(match)
            match_found = True
            break  # 複数候補があっても最初の一致で確定

    return pd.DataFrame(matches)

# データ読み込み
ucs_df = load_ucs_data()
tle_df = load_tle_data()

# Streamlitアプリのタイトル
st.title("UCS × CelesTrak 衛星マッチング")

# 初回マッチング実行
if "matched_df" not in st.session_state:
    if st.button("マッチングを実行"):
        st.session_state.matched_df = match_satellites(ucs_df, tle_df)
else:
    st.success("マッチング結果を表示中")

if "matched_df" in st.session_state and not st.session_state.matched_df.empty:
    matched_df = st.session_state.matched_df

    # フィルタUI
    countries = ["すべて"] + sorted(matched_df["Country of Operator"].fillna("不明").unique().tolist())
    selected_country = st.selectbox("国でフィルタ", countries)

    users = ["すべて"] + sorted(matched_df["Users"].fillna("不明").unique().tolist())
    selected_user = st.selectbox("目的（Users）でフィルタ", users)

    filtered_df = matched_df.copy()
    if selected_country != "すべて":
        filtered_df = filtered_df[filtered_df["Country of Operator"] == selected_country]
    if selected_user != "すべて":
        filtered_df = filtered_df[filtered_df["Users"] == selected_user]

    st.write(f"表示中の衛星数：{len(filtered_df)} 件")
    st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

    # 地図表示
    tle_lines = [
        Orbital(f["UCS Name"], line1=f["TLE_LINE1"], line2=f["TLE_LINE2"]) for _, f in filtered_df.iterrows()
    ]

    now = datetime.utcnow()
    coords = []
    for tle in tle_lines:
        try:
            lon, lat, _ = tle.get_lonlatalt(now)
            coords.append({"name": tle.name, "lat": lat, "lon": lon})
        except Exception as e:
            continue

    # 地図作成
    if coords:
        map_center = [coords[0]["lat"], coords[0]["lon"]]
        m = folium.Map(location=map_center, zoom_start=2)

        marker_cluster = MarkerCluster().add_to(m)
        for coord in coords:
            folium.Marker([coord["lat"], coord["lon"]], popup=coord["name"]).add_to(marker_cluster)

        st.markdown("### 衛星の位置")
        st.write("衛星の現在位置を地図に表示しています。")
        st.pydeck_chart(m)
