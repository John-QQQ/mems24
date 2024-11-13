import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import h3
from folium.plugins import MarkerCluster

st.title("MEMS 메타데이터 관리")
st.write("SKT MEMS 시각화 및 필터, 메타데이터 열람기능")

latest_status_file = 'Sensor_data_1024.csv'

# 작업 모드 선택
mode = st.radio("작업을 선택하세요:", ("최신 현황 불러오기 ('24년10월 기준)", "새 파일 업로드"))

def format_terminal_number(data):
    if '단말번호' in data.columns:
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

# 위도와 경도 열 이름 변경
if '위도' in data.columns and '경도' in data.columns:
    data = data.rename(columns={'위도': 'latitude', '경도': 'longitude'})

# 주소 선택 기능 활성화 여부 관리 (세션 상태)
if 'show_address_selection' not in st.session_state:
    st.session_state['show_address_selection'] = False

# "주소로 선택하기" 버튼 클릭 시 상태 토글
if st.button("주소로 선택하기"):
    st.session_state['show_address_selection'] = not st.session_state['show_address_selection']

# 연결상태 선택 기능 활성화 여부 관리 (세션 상태)
if 'show_status_selection' not in st.session_state:
    st.session_state['show_status_selection'] = False

# "연결상태로 선택하기" 버튼 클릭 시 상태 토글
if st.button("연결상태로 선택하기"):
    st.session_state['show_status_selection'] = not st.session_state['show_status_selection']

# 필터링 조건 초기화
filtered_data = data.copy()

# 주소 선택 기능 활성화 상태에 따른 동작
if st.session_state['show_address_selection']:
    if '주소' in data.columns:
        data['주소_첫단어'] = data['주소'].apply(lambda x: str(x).split()[0] if pd.notna(x) else '')
        data['주소_두번째단어'] = data['주소'].apply(lambda x: str(x).split()[1] if pd.notna(x) and len(str(x).split()) > 1 else '')

        st.write("첫 번째 주소 선택:")
        selected_first_words = []
        
        col1, col2 = st.columns(2)
        with col1:
            for word in sorted(data['주소_첫단어'].unique()):
                if st.checkbox(word, key=f"first_{word}"):
                    selected_first_words.append(word)

        selected_second_words = {}
        with col2:
            for first_word in selected_first_words:
                st.write(f"두 번째 주소 선택 ({first_word}):")
                second_words = sorted(data[data['주소_첫단어'] == first_word]['주소_두번째단어'].unique())
                selected_second_words[first_word] = [
                    second_word for second_word in second_words if st.checkbox(second_word, key=f"{first_word}_{second_word}")
                ]

        # 주소 필터링 조건 적용
        if selected_second_words:
            address_filtered_data = pd.DataFrame()
            for first_word, second_words in selected_second_words.items():
                if second_words:
                    temp_data = data[(data['주소_첫단어'] == first_word) & (data['주소_두번째단어'].isin(second_words))]
                    address_filtered_data = pd.concat([address_filtered_data, temp_data])
            # 전체 필터링 데이터에 주소 필터링 적용
            if not address_filtered_data.empty:
                filtered_data = filtered_data[filtered_data.index.isin(address_filtered_data.index)]
            else:
                filtered_data = pd.DataFrame()  # 조건에 맞는 데이터가 없을 때 빈 데이터프레임으로 설정

# 연결 상태 선택 기능 활성화 상태에 따른 동작
if st.session_state['show_status_selection']:
    if '연결상태' in data.columns:
        st.write("연결 상태 선택:")
        unique_statuses = sorted(data['연결상태'].unique())
        selected_statuses = [status for status in unique_statuses if st.checkbox(status, key=f"status_{status}")]

        # 연결 상태 필터링 조건 적용
        if selected_statuses:
            filtered_data = filtered_data[filtered_data['연결상태'].isin(selected_statuses)]
    else:
        st.write("데이터에 '연결상태' 열이 없습니다.")

# 최종 필터링된 데이터 표시
st.write("선택한 조건에 따른 최종 데이터:")
if not filtered_data.empty:
    st.dataframe(filtered_data)
else:
    st.write("선택한 조건에 해당하는 데이터가 없습니다.")

# 지도보기 기능 상태 관리 (세션 상태)
if 'show_map' not in st.session_state:
    st.session_state['show_map'] = False

# "지도보기" 버튼 클릭 시 상태 토글
if st.button("지도보기"):
    st.session_state['show_map'] = not st.session_state['show_map']

# 지도 표시 로직
if st.session_state['show_map']:
    if not filtered_data.empty and 'latitude' in filtered_data.columns and 'longitude' in filtered_data.columns:
        # Folium 지도 생성
        m = folium.Map(location=[filtered_data['latitude'].mean(), filtered_data['longitude'].mean()], zoom_start=10)

        # H3 클러스터링 및 센서 상태 카운트 집계
        filtered_data['h3_index'] = filtered_data.apply(lambda row: h3.latlng_to_cell(row['latitude'], row['longitude'], 5), axis=1)
        
        h3_dict = {}
        for h3_index, group in filtered_data.groupby('h3_index'):
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

        # H3 경계 및 센서 개수 지도에 표시
        for h3_index, cell_data in h3_dict.items():
            boundary_coords = [(lat, lon) for lat, lon in cell_data['coords']]
            folium.PolyLine(boundary_coords, color="darkred", weight=4, opacity=0.8).add_to(m)

            # 셀 중심에 센서 수 표시
            lat_center = sum([lat for lat, lon in boundary_coords]) / len(boundary_coords)
            lon_center = sum([lon for lat, lon in boundary_coords]) / len(boundary_coords)
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
        for idx, row in filtered_data.iterrows():
            color = "green" if row['연결상태'] == "normal" else "red"
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"단말번호: {row['단말번호']}\n연결상태: {row['연결상태']}",
                icon=folium.Icon(color=color)
            ).add_to(marker_cluster)

        # Streamlit에 Folium 지도 표시
        st_folium(m, width=700, height=500)
    else:
        st.write("위치 정보가 포함된 필터링된 데이터가 없습니다.")
