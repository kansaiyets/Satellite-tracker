import streamlit as st
import pandas as pd
import requests
from io import StringIO
from rapidfuzz import process, fuzz
import numpy as np
import pydeck as pdk
import re

st.title("🛰️ UCS & TLE 衛星マッチング＆可視化アプリ")

# ---------------------
# データ取得
# ---------------------
@st.cache_data
def load_ucs_data():
    url = "https://www.ucsusa.org/sites/default/files/2024-01/UCS-Satellite-Database%205-1-2023%20%28text%29.txt"
    data = requests.get(url).content.decode("utf-8", errors="ignore")
    df = pd.read_csv(StringIO(data), sep="\t")
    df.columns = [col.strip().strip('"') for col in df.columns]
    df = df.applymap(lambda x: x.strip('"') if isinstance(x, str) else x)
    return df

@st.cache_data
def load_tle_data():
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    lines = requests.get(url).text.strip().split("\n")
    tle_data = []
    for i in range(0, len(lines), 3):
        if i+2 >= len(lines):
            continue
        name, line1, line2 = lines[i:i+3]
        year_str = line1[18:20]
        try:
            year = int(year_str)
            epoch_year = 2000 + year if year < 57 else 1900 + year
        except:
            epoch_year = None
        tle_data.append({
            "tle_name": name.strip(),
            "line1": line1.strip(),
            "line2": line2.strip(),
            "epoch_year": epoch_year
        })
    return tle_data

# ---------------------
# 名前候補抽出
# ---------------------
def extract_satellite_names(name):
    if pd.isna(name):
        return []
    name = re.sub(r"[()]", ",", name)
    return [n.strip() for n in re.split(r"[,\s]+", name) if n.strip()]

# ---------------------
# ファジーマッチ処理
# ---------------------
def fuzzy_match(name, candidates, threshold=80):
    result = process.extractOne(name, candidates, scorer=fuzz.token_sort_ratio, score_cutoff=threshold)
    return result[0] if result else None

# ---------------------
# ダミー軌道生成
# ---------------------
def dummy_orbit_positions(n=100):
    lats = 10 * np.sin(np.linspace(0, 2*np.pi, n))
    lons = np.linspace(-180, 180, n)
    return pd.DataFrame({"lat": lats, "lon": lons})

# ---------------------
# 実行処理
# ---------------------
st.write("🔄 データ取得中...")
ucs_df = load_ucs_data()
tle_data = load_tle_data()

st.write(f"✅ UCS 衛星数: {len(ucs_df)}、TLE 衛星数: {len(tle_data)}")

threshold = st.slider("ファジーマッチの閾値", 20, 100, 60)

if st.button("マッチングを実行"):
    st.write("🔍 マッチングを実行中...")

    ucs_df["Name Variants"] = ucs_df["Name of Satellite, Alternate Names"].apply(extract_satellite_names)
    name_to_index = {
        name: idx
        for idx, variants in ucs_df["Name Variants"].items()
        for name in variants
    }
    candidates = list(name_to_index.keys())

    matched_list = []
    for tle in tle_data:
        match_name = fuzzy_match(tle["tle_name"], candidates, threshold)
        if match_name:
            ucs_row = ucs_df.iloc[name_to_index[match_name]]
            launch_year = pd.to_numeric(ucs_row.get("Launch Year", ""), errors="coerce")
            if tle["epoch_year"] is not None and pd.notna(launch_year) and tle["epoch_year"] < launch_year:
                continue
            matched_list.append({
                "TLE Name": tle["tle_name"],
                "Matched UCS Name": match_name,
                "Country of Operator": ucs_row.get("Country of Operator", ""),
                "Users": ucs_row.get("Users", ""),
                "Launch Year": launch_year,
                "line1": tle["line1"],
                "line2": tle["line2"]
            })

    matched_df = pd.DataFrame(matched_list)

    st.success(f"✅ 一致した衛星数: {len(matched_df)}")

    # 絞り込み
    countries = matched_df["Country of Operator"].dropna().unique()
    selected_country = st.selectbox("🌍 国でフィルタ", ["すべて"] + sorted(countries.tolist()))
    if selected_country != "すべて":
        matched_df = matched_df[matched_df["Country of Operator"] == selected_country]

    users = matched_df["Users"].dropna().unique()
    selected_user = st.selectbox("🎯 目的でフィルタ", ["すべて"] + sorted(users.tolist()))
    if selected_user != "すべて":
        matched_df = matched_df[matched_df["Users"] == selected_user]

    # 表示
    st.dataframe(matched_df[["TLE Name", "Matched UCS Name", "Country of Operator", "Users", "Launch Year"]])

    # 軌道可視化
    if not matched_df.empty:
        selected_row = st.selectbox("🛰️ 衛星を選んで軌道表示", matched_df["TLE Name"].tolist())
        if selected_row:
            pos_df = dummy_orbit_positions()
            st.pydeck_chart(pdk.Deck(
                map_style="mapbox://styles/mapbox/light-v9",
                initial_view_state=pdk.ViewState(
                    latitude=0,
                    longitude=0,
                    zoom=1,
                    pitch=0,
                ),
                layers=[
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=pos_df,
                        get_position='[lon, lat]',
                        get_radius=300000,
                        get_fill_color='[0, 100, 255, 160]',
                        pickable=True,
                    ),
                ],
            ))
