import streamlit as st
import pandas as pd
import requests
from skyfield.api import load
from PIL import Image
from io import BytesIO
import folium

# ---- データ定義（有名衛星20個） ----
satellites_info = {
    "ISS (ZARYA)": {
        "country": "International",
        "purpose": "Research",
        "launch_date": "1998-11-20",
        "description": "The International Space Station (ISS) is a modular space station in low Earth orbit.",
        "tle_url": "https://celestrak.org/NORAD/elements/stations.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/d/d0/International_Space_Station_after_undocking_of_STS-132.jpg"
    },
    "Hubble Space Telescope": {
        "country": "USA",
        "purpose": "Astronomy",
        "launch_date": "1990-04-24",
        "description": "The Hubble Space Telescope is a large space-based observatory launched by NASA.",
        "tle_url": "https://celestrak.org/NORAD/elements/science.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/3f/HST-SM4.jpeg"
    },
    "NOAA 15": {
        "country": "USA",
        "purpose": "Weather",
        "launch_date": "1998-05-13",
        "description": "A weather satellite operated by NOAA.",
        "tle_url": "https://celestrak.org/NORAD/elements/noaa.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/6/65/NOAA-15.jpg"
    },
    "NOAA 19": {
        "country": "USA",
        "purpose": "Weather",
        "launch_date": "2009-02-06",
        "description": "The final satellite in the NOAA Polar Operational Environmental Satellite series.",
        "tle_url": "https://celestrak.org/NORAD/elements/noaa.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/39/NOAA-19.jpg"
    },
    "TERRA": {
        "country": "USA",
        "purpose": "Earth Observation",
        "launch_date": "1999-12-18",
        "description": "Terra is a multi-national NASA scientific research satellite in a Sun-synchronous orbit.",
        "tle_url": "https://celestrak.org/NORAD/elements/earth-resources.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/5/5f/Terra_satellite.jpg"
    },
    "AQUA": {
        "country": "USA",
        "purpose": "Earth Observation",
        "launch_date": "2002-05-04",
        "description": "Aqua is a NASA Earth observation satellite carrying six Earth-observing instruments.",
        "tle_url": "https://celestrak.org/NORAD/elements/earth-resources.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/2/25/Aqua_satellite.jpg"
    },
    "Landsat 8": {
        "country": "USA",
        "purpose": "Earth Observation",
        "launch_date": "2013-02-11",
        "description": "Landsat 8 is an American Earth observation satellite launched in 2013.",
        "tle_url": "https://celestrak.org/NORAD/elements/landsat.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/2/24/Landsat_8.jpg"
    },
    "GPS BIIR-2": {
        "country": "USA",
        "purpose": "Navigation",
        "launch_date": "1997-07-23",
        "description": "Part of the GPS satellite constellation.",
        "tle_url": "https://celestrak.org/NORAD/elements/gps-ops.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/2/20/GPS_Satellite_NASA.jpg"
    },
    "Galileo 1": {
        "country": "EU",
        "purpose": "Navigation",
        "launch_date": "2011-10-21",
        "description": "Galileo is the European global navigation satellite system (GNSS).",
        "tle_url": "https://celestrak.org/NORAD/elements/galileo.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/d/d6/Galileo_satellite_test.jpg"
    },
    "Beidou 3": {
        "country": "China",
        "purpose": "Navigation",
        "launch_date": "2018-11-19",
        "description": "The BeiDou Navigation Satellite System (BDS) is a Chinese satellite navigation system.",
        "tle_url": "https://celestrak.org/NORAD/elements/beidou.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/5/58/BeiDou-3.jpg"
    },
    # 以下さらに追加可
}

# ---- Streamlit画面 ----
st.title("🌍 衛星リアルタイムビューア")

# 衛星リストを国・目的でフィルタ
countries = sorted(set(info['country'] for info in satellites_info.values()))
purposes = sorted(set(info['purpose'] for info in satellites_info.values()))

selected_country = st.selectbox("国を選択", countries)
selected_purpose = st.selectbox("目的を選択", purposes)

filtered_satellites = [name for name, info in satellites_info.items()
                       if info['country'] == selected_country and info['purpose'] == selected_purpose]

if not filtered_satellites:
    st.warning("この条件に一致する衛星は登録されていません。")
    st.stop()

selected_satellite = st.selectbox("衛星を選んでください", filtered_satellites)
info = satellites_info[selected_satellite]

# 衛星の説明
st.subheader(f"🛰️ {selected_satellite}")
st.write(f"**国**: {info['country']}")
st.write(f"**目的**: {info['purpose']}")
st.write(f"**打ち上げ日**: {info['launch_date']}")
st.write(f"**説明**: {info['description']}")

# 画像を表示
try:
    response = requests.get(info["image_url"])
    img = Image.open(BytesIO(response.content))
    st.image(img, caption=f"{selected_satellite} (Image: Wikipedia)", use_container_width=True)
except:
    st.info("画像を読み込めませんでした。")

# TLEデータ読み込み
stations_url = info["tle_url"]
satellites = load.tle_file(stations_url)
satellite = next((s for s in satellites if s.name.strip().lower() == selected_satellite.strip().lower()), None)

if not satellite:
    st.error("TLEデータに衛星が見つかりませんでした。")
    st.stop()

# 現在位置取得
ts = load.timescale()
t_now = ts.now()
geocentric = satellite.at(t_now)
subpoint = geocentric.subpoint()
lat_now = subpoint.latitude.degrees
lon_now = subpoint.longitude.degrees

# folium地図作成
m = folium.Map(location=[lat_now, lon_now], zoom_start=3)
folium.Marker([lat_now, lon_now], popup=f"{selected_satellite} 現在位置").add_to(m)

# 過去24時間の軌跡
time_steps = [t_now - (i / 144) for i in range(1, 145)]
for t in time_steps:
    geocentric = satellite.at(t)
    subpoint = geocentric.subpoint()
    folium.CircleMarker(
        location=[subpoint.latitude.degrees, subpoint.longitude.degrees],
        radius=2, color="blue", fill=True
    ).add_to(m)

# 地図を表示
st.components.v1.html(m._repr_html_(), height=600)

# 現在位置表示
st.write(f"**現在位置**: 緯度 {lat_now:.2f}°, 経度 {lon_now:.2f}°")
