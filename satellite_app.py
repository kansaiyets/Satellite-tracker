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
    }
}

# ---- Streamlit画面 ----
st.title("🌍 衛星リアルタイムビューア")

# 衛星選択
satellite_names = list(satellites_info.keys())
selected_satellite = st.selectbox("衛星を選択してください", satellite_names)

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
satellite = [s for s in satellites if s.name == "ISS (ZARYA)"][0]

ts = load.timescale()
t = ts.now()
geocentric = satellite.at(t)
subpoint = geocentric.subpoint()

# 緯度経度を取得
lat = subpoint.latitude.degrees
lon = subpoint.longitude.degrees

# foliumで地図を作成
m = folium.Map(location=[lat, lon], zoom_start=3)  # ズームレベルを調整

# 衛星の位置にマーカーを追加
folium.Marker([lat, lon], popup=f"{selected_satellite}の位置").add_to(m)

# Streamlitでfolium地図を表示
st.components.v1.html(m._repr_html_(), height=500)

# 衛星位置情報の表示
st.write(f"**現在位置**: 緯度 {lat:.2f}°, 経度 {lon:.2f}°")
