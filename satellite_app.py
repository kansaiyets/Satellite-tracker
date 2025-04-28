import streamlit as st
import pandas as pd
import requests
from skyfield.api import load
import plotly.express as px
from PIL import Image
from io import BytesIO
import folium

# ---- データ定義 ----
satellites_info = {
    "ISS (International Space Station)": {
        "country": "International",
        "purpose": "Research",
        "launch_date": "1998-11-20",
        "description": "The International Space Station (ISS) is a modular space station in low Earth orbit.",
        "tle_url": "https://celestrak.org/NORAD/elements/stations.txt",
        "image_url": "https://cdn.pixabay.com/photo/2012/10/26/02/39/international-space-station-63128_1280.jpg"
    },
    "Hubble Space Telescope": {
        "country": "USA",
        "purpose": "Astronomy",
        "launch_date": "1990-04-24",
        "tle_url": "https://celestrak.org/NORAD/elements/science.txt",
        "image_url": "https://cdn.pixabay.com/photo/2017/07/06/16/00/hubble-2481066_1280.jpg"
    },
    # 他の衛星情報を追加可能
}

# ---- Streamlit画面 ----
st.title("🌍 衛星リアルタイムビューア")

# 国や目的で衛星をフィルタリング
countries = list(set([info['country'] for info in satellites_info.values()]))
purposes = list(set([info['purpose'] for info in satellites_info.values()]))

selected_country = st.selectbox("国を選択", countries)
selected_purpose = st.selectbox("目的を選択", purposes)

# フィルタリングされた衛星リスト
filtered_satellites = [sat for sat, info in satellites_info.items() if info['country'] == selected_country and info['purpose'] == selected_purpose]
selected_satellite = st.selectbox("衛星を選択してください", filtered_satellites)

# 衛星データ取得
info = satellites_info[selected_satellite]

st.subheader(f"🛰️ {selected_satellite}")
st.write(f"**国**: {info['country']}")
st.write(f"**目的**: {info['purpose']}")
st.write(f"**打ち上げ日**: {info['launch_date']}")
st.write(f"**説明**: {info['description']}")

# 画像表示
response = requests.get(info["image_url"])
img = Image.open(BytesIO(response.content))
st.image(img, caption=selected_satellite, use_container_width=True)

# 衛星位置表示
stations_url = info["tle_url"]
satellites = load.tle_file(stations_url)
satellite = [s for s in satellites if s.name == selected_satellite][0]

ts = load.timescale()
t = ts.now()
geocentric = satellite.at(t)
subpoint = geocentric.subpoint()

# 緯度経度を取得
lat = subpoint.latitude.degrees
lon = subpoint.longitude.degrees

# foliumで地図を作成
m = folium.Map(location=[lat, lon], zoom_start=3)

# 衛星の位置にマーカーを追加
folium.Marker([lat, lon], popup=f"{selected_satellite}の位置").add_to(m)

# Streamlitでfolium地図を表示
st.components.v1.html(m._repr_html_(), height=500)

# 過去24時間の軌跡を表示
time_steps = [t - ts.seconds(3600 * i) for i in range(24)]  # 24時間分の時刻
latitudes = []
longitudes = []

for t in time_steps:
    geocentric = satellite.at(t)
    subpoint = geocentric.subpoint()
    latitudes.append(subpoint.latitude.degrees)
    longitudes.append(subpoint.longitude.degrees)

# 地図に過去の軌跡を追加
for lat, lon in zip(latitudes, longitudes):
    folium.Marker([lat, lon], popup="過去の位置").add_to(m)

# 地図を再表示
st.components.v1.html(m._repr_html_(), height=500)

# 衛星位置情報の表示
st.write(f"**現在位置**: 緯度 {lat:.2f}°, 経度 {lon:.2f}°")
