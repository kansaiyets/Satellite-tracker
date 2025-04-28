import streamlit as st
import pandas as pd
import requests
from skyfield.api import load
from PIL import Image
from io import BytesIO
import folium

# ---- 衛星情報定義 (20個) ----
satellites_info = {
    "ISS (ZARYA)": {
        "country": "International",
        "purpose": "Research",
        "tle_url": "https://celestrak.org/NORAD/elements/stations.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/d/d0/ISS_Expedition_20.jpg"
    },
    "Hubble Space Telescope": {
        "country": "USA",
        "purpose": "Astronomy",
        "tle_url": "https://celestrak.org/NORAD/elements/science.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/3f/HST-SM4.jpeg"
    },
    "Terra": {
        "country": "USA",
        "purpose": "Earth Observation",
        "tle_url": "https://celestrak.org/NORAD/elements/resource.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/4/45/Terra_Satellite.jpg"
    },
    "Aqua": {
        "country": "USA",
        "purpose": "Earth Observation",
        "tle_url": "https://celestrak.org/NORAD/elements/resource.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/5/57/Aqua_satellite.jpg"
    },
    "Landsat 8": {
        "country": "USA",
        "purpose": "Earth Observation",
        "tle_url": "https://celestrak.org/NORAD/elements/resource.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/e/e6/Landsat_8_artwork.jpg"
    },
    "NOAA 19": {
        "country": "USA",
        "purpose": "Weather",
        "tle_url": "https://celestrak.org/NORAD/elements/noaa.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/d/d3/NOAA-19.jpg"
    },
    "Sentinel-1A": {
        "country": "EU",
        "purpose": "Earth Observation",
        "tle_url": "https://celestrak.org/NORAD/elements/resource.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/2/23/Sentinel-1_spacecraft_model.png"
    },
    "Sentinel-2A": {
        "country": "EU",
        "purpose": "Earth Observation",
        "tle_url": "https://celestrak.org/NORAD/elements/resource.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/7c/Sentinel-2_model.jpg"
    },
    "Jason-3": {
        "country": "International",
        "purpose": "Oceanography",
        "tle_url": "https://celestrak.org/NORAD/elements/resource.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/5/5e/Jason-3_Artist_Concept.jpg"
    },
    "Starlink-30000": {
        "country": "USA",
        "purpose": "Communications",
        "tle_url": "https://celestrak.org/NORAD/elements/starlink.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/5/5a/Starlink_SpaceX.jpg"
    },
    "Globalstar M086": {
        "country": "USA",
        "purpose": "Communications",
        "tle_url": "https://celestrak.org/NORAD/elements/globalstar.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/d/db/Globalstar_Satellite.jpg"
    },
    "TDRS 12": {
        "country": "USA",
        "purpose": "Communications",
        "tle_url": "https://celestrak.org/NORAD/elements/tdrs.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/6/62/TDRS-M_Artist_Rendering.jpg"
    },
    "COSMO-SkyMed 1": {
        "country": "Italy",
        "purpose": "Earth Observation",
        "tle_url": "https://celestrak.org/NORAD/elements/resource.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/f/f3/COSMO-SkyMed.jpg"
    },
    "Envisat": {
        "country": "EU",
        "purpose": "Earth Observation",
        "tle_url": "https://celestrak.org/NORAD/elements/resource.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/73/Envisat_artist_view.jpg"
    },
    "MetOp-B": {
        "country": "EU",
        "purpose": "Weather",
        "tle_url": "https://celestrak.org/NORAD/elements/noaa.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/e/e7/Metop-B.jpg"
    },
    "TanDEM-X": {
        "country": "Germany",
        "purpose": "Earth Observation",
        "tle_url": "https://celestrak.org/NORAD/elements/resource.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/c/c2/TanDEM-X_Satellite.jpg"
    },
    "WorldView-3": {
        "country": "USA",
        "purpose": "Earth Observation",
        "tle_url": "https://celestrak.org/NORAD/elements/resource.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/1/1a/WorldView-3_Artist_Rendering.jpg"
    },
    "IKONOS": {
        "country": "USA",
        "purpose": "Earth Observation",
        "tle_url": "https://celestrak.org/NORAD/elements/resource.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/2/2b/IKONOS_satellite.jpg"
    },
    "Cartosat-2": {
        "country": "India",
        "purpose": "Earth Observation",
        "tle_url": "https://celestrak.org/NORAD/elements/resource.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/76/Cartosat-2_Artist_View.jpg"
    },
    "Fengyun 3D": {
        "country": "China",
        "purpose": "Weather",
        "tle_url": "https://celestrak.org/NORAD/elements/weather.txt",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/f/f5/Fengyun-3.jpg"
    }
}

# ---- Streamlit画面 ----
st.title("🌍 衛星リアルタイムビューア")

# 国・目的でフィルタリング
countries = sorted(set(info["country"] for info in satellites_info.values()))
purposes = sorted(set(info["purpose"] for info in satellites_info.values()))

selected_country = st.selectbox("🌎 国を選択", ["すべて"] + countries)
selected_purpose = st.selectbox("🎯 目的を選択", ["すべて"] + purposes)

# 衛星リストフィルタ
def satellite_filter(info):
    if selected_country != "すべて" and info["country"] != selected_country:
        return False
    if selected_purpose != "すべて" and info["purpose"] != selected_purpose:
        return False
    return True

filtered_satellites = [name for name, info in satellites_info.items() if satellite_filter(info)]
if not filtered_satellites:
    st.error("条件に合う衛星がありません。")
    st.stop()

selected_satellite = st.selectbox("🛰️ 衛星を選択", filtered_satellites)
sat_info = satellites_info[selected_satellite]

# 衛星基本情報
st.subheader(f"🛰️ {selected_satellite}")
st.write(f"**国**: {sat_info['country']}")
st.write(f"**目的**: {sat_info['purpose']}")

# 画像表示
#response = requests.get(sat_info["image_url"])
#img = Image.open(BytesIO(response.content))
#st.image(img, caption=f"{selected_satellite} (出典: Wikimedia Commons)", use_container_width=True)

# 衛星位置取得
stations_url = sat_info["tle_url"]
satellites = load.tle_file(stations_url)
satellite_obj = None
for s in satellites:
    if s.name == selected_satellite:
        satellite_obj = s
        break
if satellite_obj is None:
    st.error("選択した衛星のTLEデータが見つかりませんでした。")
    st.stop()

# 現在時刻取得
ts = load.timescale()
t_now = ts.now()

# 衛星位置計算
geocentric = satellite_obj.at(t_now)
subpoint = geocentric.subpoint()
lat_now = subpoint.latitude.degrees
lon_now = subpoint.longitude.degrees

# 地図作成
m = folium.Map(location=[lat_now, lon_now], zoom_start=3)
folium.Marker([lat_now, lon_now], popup=f"現在位置: {selected_satellite}").add_to(m)

# 過去24時間の軌跡
time_steps = [t_now - (i * 1440) for i in range(1, 25)]  # 1時間おき

# 点で軌跡をプロット
for t in time_steps:
    geocentric = satellite.at(t)
    subpoint = geocentric.subpoint()
    folium.CircleMarker(
        location=[subpoint.latitude.degrees, subpoint.longitude.degrees],
        radius=2, color="blue", fill=True
    ).add_to(m)


#trajectory = []
#for t in time_steps:
#    geo = satellite_obj.at(t)
#    sp = geo.subpoint()
#    trajectory.append((sp.latitude.degrees, sp.longitude.degrees))

# 線で軌跡をプロット
#folium.PolyLine(trajectory, color="blue", weight=2.5, opacity=0.7).add_to(m)

# 地図表示
st.components.v1.html(m._repr_html_(), height=500)

# 現在位置表示
st.write(f"**現在位置**: 緯度 {lat_now:.2f}°, 経度 {lon_now:.2f}°")
