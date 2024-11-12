import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import h3
from folium.plugins import MarkerCluster

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

# 데이터 파일 불러오기
if mode == "새 파일 업로드":
    uploaded_file = st.file_uploader("새 파일을 업로드하세요 (CSV 형식)", type="csv")
    if uploaded_file:
        data = pd.read_csv(uploaded_file, dtype={'단말번호': str})
        data = format_terminal_number(data)
        st.write("새 파일 데이터 미리보기:")
        st.dataframe(data)
else:
    data = pd.read_csv(latest_status_file, dtype={'단말번호': str})
    data = format_terminal_number(data)
    st.write("최신 현황 데이터 미리보기:")
    st.dataframe(data)

# 지도 표시 버튼과 지도 상태 관리
if 'show_map' not in st.session_state:
    st.session_state['show_map'] = False

if st.button("지도보기"):
    st.session_state['show_map'] = True

# 지도 표시 로직
if st.session_state['show_map']:
    # 필요한 열 확인
    required_columns = {'위도', '경도', '연결상태'}
    if required_columns.issubset(data.columns):
        # 열 이름을 위도/경도에 맞게 변경
        data = data.rename(columns={'위도': 'latitude', '경도': 'longitude'})

        # H3 클러스터링 및 센서 상태 카운트 집계
        data['h3_index'] = data.apply(lambda row: h3.latlng_to_cell(row['latitude'], row['longitude'], 5), axis=1)
        h3_dict = {}
        for h3_index, group in data.groupby('h3_index'):
            coords = h3.cell_to_boundary(h3_index)
            total_count = len(group)
            normal_count = sum(group['연결상태'] == 'normal')
            disc_count = sum(group['연결상태'] == 'disc.')

            h3_dict[h3_index] = {
                'coords': coords,
                'total_count': total_count,
                'normal_count': normal_count,
                'disc_count': disc_count,
            }

        # Folium 지도 생성
        m = folium.Map(location=[data['latitude'].mean(), data['longitude'].mean()], zoom_start=10)

        # H3 경계 및 센서 개수 지도에 표시
        for h3_index, cell_data in h3_dict.items():
            # H3 셀 경계선을 PolyLine으로 추가
            boundary_coords = [(lat, lon) for lat, lon in cell_data['coords']]
            folium.PolyLine(boundary_coords, color="darkred", weight=4, opacity=0.8).add_to(m)

            # 셀의 중심 위치 계산 및 센서 수 표시
            lat_center = sum([lat for lat, lon in boundary_coords]) / len(boundary_coords)
            lon_center = sum([lon for lat, lon in boundary_coords]) / len(boundary_coords)

            # 새로운 형식의 라벨 "00(00/00)"
            label = f"{cell_data['total_count']} ({cell_data['normal_count']}/{cell_data['disc_count']})"

            folium.Marker(
                location=[lat_center, lon_center],
                popup=f"센서 수: {label}",
                icon=folium.DivIcon(html=f"""
                    <div style="text-align: center;">
                        <span style="font-size: 14pt; font-weight: bold; color: darkblue">{label}</span>
                    </div>
                """)
            ).add_to(m)

        # 개별 센서 위치 및 상태 표시
        marker_cluster = MarkerCluster().add_to(m)
        for idx, row in data.iterrows():
            color = "green" if row['연결상태'] == "normal" else "red"
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"단말번호: {row['단말번호']}\n연결상태: {row['연결상태']}",
                icon=folium.Icon(color=color)
            ).add_to(marker_cluster)

        # Streamlit에 Folium 지도 표시
        st.components.v1.html(m._repr_html_(), width=700, height=700)
    else:
        st.write("필요한 열 중 일부가 데이터에 없습니다. 위치 정보를 확인해 주세요.")
