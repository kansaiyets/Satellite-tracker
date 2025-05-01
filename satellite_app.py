import streamlit as st
import pandas as pd
from fuzzywuzzy import process
from datetime import datetime
import numpy as np
import pydeck as pdk

# ---- 衛星名の候補生成 ----
def extract_satellite_names(name):
    parts = []
    if pd.isna(name):
        return parts
    for segment in name.split(","):
        segment = segment.strip()
        if "(" in segment:
            before, inside = segment.split("(", 1)
            before = before.strip()
            inside = inside.replace(")", "").strip()
            if before:
                parts.append(before)
            if inside:
                parts.append(inside)
        else:
            parts.append(segment)
    return list(set(parts))  # 重複除去

# ---- ファジーマッチング処理 ----
def fuzzy_match(satellite_name, candidates, year=None):
    best_match, score = process.extractOne(satellite_name, candidates)
    if score < 80:
        return None
    return best_match

# ---- TLEエポック年抽出 ----
def extract_epoch_year(line1):
    try:
        year_str = line1[18:20]
        year = int(year_str)
        return 2000 + year if year < 57 else 1900 + year
    except:
        return None

# ---- TLE読み込み ----
def load_tle_file(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines()]
    satellites = []
    for i in range(0, len(lines), 3):
        if i+2 >= len(lines):
            continue
        name, line1, line2 = lines[i:i+3]
        year = extract_epoch_year(line1)
        satellites.append({
            "tle_name": name,
            "line1": line1,
            "line2": line2,
            "epoch_year": year
        })
    return satellites

# ---- 緯度経度推定（単純な円軌道モデルで仮表示） ----
def dummy_orbit_positions(n=100):
    lats = 10 * np.sin(np.linspace(0, 2*np.pi, n))
    lons = np.linspace(-180, 180, n)
    return pd.DataFrame({"lat": lats, "lon": lons})

# ---- Streamlitアプリ本体 ----
def main():
    st.title("🌍 UCS & TLE 衛星マッチングアプリ")

    # データ読み込み
    ucs_df = pd.read_csv("ucs.csv", quotechar='"')
    tle_data = load_tle_file("tle.txt")

    # UCS 衛星名の候補を展開
    ucs_df["Name Variants"] = ucs_df["Name of Satellite, Alternate Names"].apply(extract_satellite_names)
    name_to_index = {
        name: idx
        for idx, variants in ucs_df["Name Variants"].items()
        for name in variants
    }

    # マッチ処理
    matched_list = []
    for tle in tle_data:
        match_name = fuzzy_match(tle["tle_name"], list(name_to_index.keys()))
        if match_name:
            ucs_row = ucs_df.iloc[name_to_index[match_name]]
            if tle["epoch_year"] is not None:
                launch_year = pd.to_numeric(ucs_row["Launch Year"], errors="coerce")
                if pd.notna(launch_year) and tle["epoch_year"] < launch_year:
                    continue  # TLEが打ち上げ年より前 → 無視
            matched_list.append({
                "TLE Name": tle["tle_name"],
                "Matched UCS Name": match_name,
                "Country of Operator": ucs_row.get("Country of Operator", ""),
                "Users": ucs_row.get("Users", ""),
                "Launch Year": ucs_row.get("Launch Year", ""),
                "line1": tle["line1"],
                "line2": tle["line2"]
            })

    matched_df = pd.DataFrame(matched_list)

    st.success(f"🔍 一致した衛星数: {len(matched_df)}")

    # 絞り込み
    countries = matched_df["Country of Operator"].dropna().unique()
    selected_country = st.selectbox("国を選択", ["すべて"] + sorted(countries.tolist()))
    if selected_country != "すべて":
        matched_df = matched_df[matched_df["Country of Operator"] == selected_country]

    users = matched_df["Users"].dropna().unique()
    selected_user = st.selectbox("目的を選択", ["すべて"] + sorted(users.tolist()))
    if selected_user != "すべて":
        matched_df = matched_df[matched_df["Users"] == selected_user]

    # 表示
    st.dataframe(matched_df[["TLE Name", "Matched UCS Name", "Country of Operator", "Users", "Launch Year"]])

    # 衛星を選択して軌道表示
    selected_row = st.selectbox("衛星を選択して軌道表示", matched_df["TLE Name"].tolist())
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
                    get_fill_color='[255, 0, 0, 160]',
                    pickable=True,
                ),
            ],
        ))

if __name__ == "__main__":
    main()
