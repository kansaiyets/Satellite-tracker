import streamlit as st
import pandas as pd
import requests
import io
from rapidfuzz import process
from datetime import datetime
from pyorbital.orbital import Orbital
from pyorbital import tlefile
import pydeck as pdk

@st.cache_data
def load_ucs_data():
    url = "https://www.ucsusa.org/sites/default/files/2024-01/UCS-Satellite-Database%205-1-2023%20%28text%29.txt"
    response = requests.get(url)
    df = pd.read_csv(io.StringIO(response.text), sep='\t')
    df.columns = df.columns.str.strip()
    return df

@st.cache_data
def load_tle_data():
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=csv"
    response = requests.get(url)
    return pd.read_csv(io.StringIO(response.text))

def preprocess_ucs_name(name):
    if pd.isna(name):
        return []
    name = name.replace("（", "(").replace("）", ")")
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
    user = user.replace("Government/Military", "Military/Government")
    user = user.replace("Commercial", "Commercial")  # 統一用ダミー
    parts = [p.strip() for p in user.split("/")]
    return "/".join(sorted(set(parts)))

def match_satellites(ucs_df, tle_df):
    matches = []
    for idx, tle_row in tle_df.iterrows():
        tle_name = tle_row["OBJECT_NAME"]
        match_found = False

        for ucs_idx, ucs_row in ucs_df.iterrows():
            names = preprocess_ucs_name(ucs_row.get("Name of Satellite, Alternate Names", ""))
            if not names:
                continue
            best_name, score, _ = process.extractOne(tle_name, names)
            if score < 90:
                continue

            tle_epoch = tle_row.get("EPOCH", "")
            try:
                tle_year = int(tle_epoch[:4]) if isinstance(tle_epoch, str) else None
            except:
                tle_year = None

            try:
                ucs_year = int(ucs_row.get("Launch Year", ""))
            except:
                ucs_year = None

            if tle_year is not None and ucs_year is not None and tle_year < ucs_year:
                continue

            match = {
                "TLE Name": tle_name,
                "UCS Name": best_name,
                "Match Score": score,
                "OBJECT_ID": tle_row.get("OBJECT_ID", ""),
                "EPOCH": tle_row.get("EPOCH", ""),
                "Country of Operator": ucs_row.get("Country of Operator", "不明"),
                "Users": normalize_users(ucs_row.get("Users", "不明")),
                "Purpose": ucs_row.get("Purpose", "不明"),
                "Class of Orbit": tle_row.get("CLASS_OF_ORBIT", "不明"),
                "Mean Motion": tle_row.get("MEAN_MOTION", ""),
                "Inclination": tle_row.get("INCLINATION", ""),
                "Apogee": tle_row.get("APOAPSIS", ""),
                "Perigee": tle_row.get("PERIAPSIS", ""),
                "TLE Line1": tle_row.get("TLE_LINE1", ""),
                "TLE Line2": tle_row.get("TLE_LINE2", "")
            }
            matches.append(match)
            match_found = True
            break

    return pd.DataFrame(matches)

ucs_df = load_ucs_data()
tle_df = load_tle_data()

st.title("UCS × CelesTrak 衛星マッチング")

if "matched_df" not in st.session_state:
    if st.button("マッチングを実行"):
        st.session_state.matched_df = match_satellites(ucs_df, tle_df)
else:
    st.success("マッチング結果を表示中")

if "matched_df" in st.session_state and not st.session_state.matched_df.empty:
    matched_df = st.session_state.matched_df

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
        tlefile.Tle(f["UCS Name"], f["TLE Line1"], f["TLE Line2"]) for _, f in filtered_df.iterrows()
    ]

    now = datetime.utcnow()
    coords = []
    for tle in tle_lines:
        orb = Orbital(tle.name, line1=tle.line1, line2=tle.line2)
        try:
            lon, lat, _ = orb.get_lonlatalt(now)
            coords.append({"name": tle.name, "lat": lat, "lon": lon})
        except:
            continue

    if coords:
        st.map(pd.DataFrame(coords))
