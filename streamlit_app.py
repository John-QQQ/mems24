import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import h3
from shapely.geometry import Polygon
from shapely import wkt

# 타이틀과 설명 추가
st.title("MEMS 메타데이터 관리")
st.write("SKT MEMS 시각화 및 필터, 메타데이터 열람기능")

# 최신 현황 파일 경로 설정
latest_status_file = 'Sensor_data_1024.csv'

# 작업 모드 선택
mode = st.radio("작업을 선택하세요:", ("최신 현황 불러오기 ('24년10월 기준)", "새 파일 업로드"))

def format_terminal_number(data):
    # 단말번호가 있는 경우, 11자리 문자열로 고정
    if '단말번호' in data.columns:
        # 단말번호를 문자열로 변환 후 11자리로 맞추기
        data['단말번호'] = data['단말번호'].astype(str).str.zfill(11)
    return data

if mode == "새 파일 업로드":
    uploaded_file = st.file_uploader("새 파일을 업로드하세요 (CSV 형식)", type="csv")
    if uploaded_file:
        # CSV 파일을 '단말번호' 열을 문자열로 읽기
        data = pd.read_csv(uploaded_file, dtype={'단말번호': str})
        data = format_terminal_number(data)
        st.write("새 파일 데이터 미리보기:")
        st.dataframe(data)
else:
    # 최신 현황 파일 불러오기 (단말번호 열을 문자열로 읽기)
    data = pd.read_csv(latest_status_file, dtype={'단말번호': str})
    data = format_terminal_number(data)
    st.write("최신 현황 데이터 미리보기:")
    st.dataframe(data)

# 지도 보기 버튼을 클릭했을 때만 지도 표시
if '위도' in data.columns and '경도' in data.columns and '연결상태' in data.columns:
    if st.button("지도보기"):
        # 위도와 경도 열 이름을 latitude, longitude로 변경
        data = data.rename(columns={'위도': 'latitude', '경도': 'longitude'})

        # H3 클러스터링 (h3.latlng_to_cell 사용)
        data['h3_index'] = data.apply(lambda row: h3.latlng_to_cell(row['latitude'], row['longitude'], 5), axis=1)
        h3_counts = data.groupby('h3_index').size().reset_index(name='count')

        # Folium 지도 생성
        m = folium.Map(location=[data['latitude'].mean(), data['longitude'].mean()], zoom_start=10)

        # H3 Resolution 5 경계선과 센서 수를 지도에 추가
        for _, row in h3_counts.iterrows():
            h3_index = row['h3_index']
            count = row['count']
            
            # H3 셀 경계 생성
            hex_boundary = h3.cell_to_boundary(h3_index)
            polygon = Polygon(hex_boundary)
            folium.GeoJson(polygon, style_function=lambda x: {'fillColor': '#blue', 'color': 'blue', 'weight': 1}).add_to(m)

            # 클러스터 센서 개수 표시
            center = h3.cell_to_latlng(h3_index)
            folium.Marker(
                location=center,
                popup=f"센서 개수: {count}",
                icon=folium.DivIcon(html=f"<div style='color: black; background-color: rgba(255, 255, 255, 0.6); border-radius: 5px; padding: 2px 5px;'><b>{count}</b></div>")
            ).add_to(m)

        # Streamlit에 Folium 지도 표시
        st.write("H3 클러스터링과 경계선이 포함된 지도 표시")
        st_folium(m, width=700, height=500)
else:
    st.write("위도, 경도, 연결상태 열이 데이터에 없습니다. 위치 정보를 확인해 주세요.")