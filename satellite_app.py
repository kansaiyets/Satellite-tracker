import streamlit as st
import pandas as pd
import requests
from skyfield.api import load
from PIL import Image
from io import BytesIO
import folium

# ---- データ定義（20個くらい衛星） ----
satellites_info = {
    "ISS (ZARYA)": {
        "country": "International",
        "purpose": "Research",
        "launch_date": "1998-11-20",
        "description": "International Space Station.",
        "tle_url": "https://celestrak.org/NORAD/elements/stations.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/9/97/ISS_in_2021.jpg"
    },
    "Hubble Space Telescope": {
        "country": "USA",
        "purpose": "Astronomy",
        "launch_date": "1990-04-24",
        "description": "Space telescope orbiting Earth.",
        "tle_url": "https://celestrak.org/NORAD/elements/science.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/3f/HST-SM4.jpeg"
    },
    "Terra": {
        "country": "USA",
        "purpose": "Earth Observation",
        "launch_date": "1999-12-18",
        "description": "Earth observing satellite.",
        "tle_url": "https://celestrak.org/NORAD/elements/earth-observation.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/5/51/Terra_satellite.jpg"
    },
    "Aqua": {
        "country": "USA",
        "purpose": "Earth Observation",
        "launch_date": "2002-05-04",
        "description": "Studies Earth's water cycle.",
        "tle_url": "https://celestrak.org/NORAD/elements/earth-observation.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/6/66/Aqua_satellite.jpg"
    },
    "Landsat 8": {
        "country": "USA",
        "purpose": "Earth Imaging",
        "launch_date": "2013-02-11",
        "description": "Landsat program satellite.",
        "tle_url": "https://celestrak.org/NORAD/elements/earth-observation.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/6/64/Landsat_8_in_orbit.jpg"
    },
    # 以下、同様に追加できる（省略）
}

# ---- Streamlit画面 ----
st.title("🌍 衛星リアルタイムビューア")

# 衛星選択
satellite_names = list(satellites_info.keys())
selected_satellite = st.selectbox("衛星を選んでください", satellite_names)

# 衛星情報表示
info = satellites_info[selected_satellite]
st.subheader(f"🛰️ {selected_satellite}")
st.write(f"**国**: {info['country']}")
st.write(f"**目的**: {info['purpose']}")
st.write(f"**打ち上げ日**: {info['launch_date']}")
st.write(f"**説明**: {info['description']}")

# 衛星画像
try:
    response = requests.get(info["image_url"])
    img = Image.open(BytesIO(response.content))
    st.image(img, caption=f"{selected_satellite} (Image credit: Wikimedia/Pixabay)", use_container_width=True)
except:
    st.warning("画像の取得に失敗しました。")

# 衛星位置計算
try:
    satellites = load.tle_file(info["tle_url"])
    satellite_obj = None
    for sat in satellites:
        if selected_satellite.lower() in sat.name.lower():
            satellite_obj = sat
            break
    if not satellite_obj:
        raise Exception("TLEデータから衛星を見つけられませんでした。")

    ts = load.timescale()
    t_now = ts.now()

    geocentric_now = satellite_obj.at(t_now)
    subpoint_now = geocentric_now.subpoint()

    lat_now = subpoint_now.latitude.degrees
    lon_now = subpoint_now.longitude.degrees

    # 地図表示
    m = folium.Map(location=[lat_now, lon_now], zoom_start=3)
    folium.Marker([lat_now, lon_now], popup=f"現在位置: {lat_now:.2f}, {lon_now:.2f}").add_to(m)

    # 過去24時間の軌跡
    for hour in range(1, 241):
        past_time = t_now - (hour / 1440.0)
        past_geocentric = satellite_obj.at(past_time)
        past_subpoint = past_geocentric.subpoint()
        lat_past = past_subpoint.latitude.degrees
        lon_past = past_subpoint.longitude.degrees
        folium.CircleMarker(
            location=[lat_past, lon_past],
            radius=2,
            color="blue",
            fill=True,
            fill_opacity=0.7
        ).add_to(m)

    # 地図を表示
    st.components.v1.html(m._repr_html_(), height=600)

    # 現在位置も表示
    st.write(f"**現在位置**: 緯度 {lat_now:.2f}°, 経度 {lon_now:.2f}°")

except Exception as e:
    st.error(f"衛星データの取得に失敗しました: {e}")
