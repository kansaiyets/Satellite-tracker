import streamlit as st
import pandas as pd
import requests
import io
from rapidfuzz import process
from datetime import datetime

@st.cache_data
def load_ucs_data():
    url = "https://raw.githubusercontent.com/space-track/UCS-Satellite-Database/main/ucs-satellite-database.csv"
    df = pd.read_csv(url, quotechar='"')
    df.columns = df.columns.str.strip('"')  # 列名から余分なダブルクォートを削除
    return df

@st.cache_data
def load_tle_data():
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=csv"
    response = requests.get(url)
    return pd.read_csv(io.StringIO(response.text))

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

def normalize_users(user):
    if pd.isna(user):
        return "不明"
    parts = [p.strip() for p in user.split("/")]
    return "/".join(sorted(parts))

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
