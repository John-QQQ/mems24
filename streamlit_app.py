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

# 지도 표시 버튼과 지도 상태 관리
if 'show_map' not in st.session_state:
    st.session_state['show_map'] = False

if st.button("지도보기"):
    st.session_state['show_map'] = True

# 지도 표시 로직
if st.session_state['show_map']:
    required_columns = {'위도', '경도', '연결상태'}
    if required_columns.issubset(data.columns):
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

        m = folium.Map(location=[data['latitude'].mean(), data['longitude'].mean()], zoom_start=10)

        # H3 경계 및 센서 개수 지도에 표시
        for h3_index, cell_data in h3_dict.items():
            boundary_coords = [(lat, lon) for lat, lon in cell_data['coords']]
            folium.PolyLine(boundary_coords, color="darkred", weight=4, opacity=0.8).add_to(m)

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
        for idx, row in data.iterrows():
            color = "green" if row['연결상태'] == "normal" else "red"
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"단말번호: {row['단말번호']}\n연결상태: {row['연결상태']}",
                icon=folium.Icon(color=color)
            ).add_to(marker_cluster)

        # Folium 지도 Streamlit에 표시 (st_folium 사용)
        st_folium(m, width=700, height=700)
    else:
        st.write("필요한 열 중 일부가 데이터에 없습니다. 위치 정보를 확인해 주세요.")


# 주소 열의 첫 단어 및 두 번째 단어 추출
if '주소' in data.columns:
    data['주소_첫단어'] = data['주소'].apply(lambda x: str(x).split()[0] if pd.notna(x) else '')
    data['주소_두번째단어'] = data['주소'].apply(lambda x: str(x).split()[1] if pd.notna(x) and len(str(x).split()) > 1 else '')

    # 첫 번째 단어 체크박스 생성
    st.write("첫 번째 주소 선택:")
    selected_first_words = [word for word in sorted(data['주소_첫단어'].unique()) if st.checkbox(word, key=word)]
    
    # 두 번째 단어 필터링 및 체크박스 생성
    selected_second_words = {}
    if selected_first_words:
        for first_word in selected_first_words:
            st.write(f"두 번째 주소 선택 ({first_word}):")
            second_words = sorted(data[data['주소_첫단어'] == first_word]['주소_두번째단어'].unique())
            
            selected_second_words[first_word] = [
                second_word for second_word in second_words if st.checkbox(second_word, key=f"{first_word}_{second_word}")
            ]
    
    # 선택한 첫 번째 단어와 두 번째 단어로 데이터 필터링
    if selected_second_words:
        # 선택된 조건에 맞는 데이터를 필터링
        filtered_data = pd.DataFrame()
        for first_word, second_words in selected_second_words.items():
            if second_words:  # 두 번째 단어가 선택된 경우만 필터링
                temp_data = data[(data['주소_첫단어'] == first_word) & (data['주소_두번째단어'].isin(second_words))]
                filtered_data = pd.concat([filtered_data, temp_data])

        # 필터링된 데이터 표시
        if not filtered_data.empty:
            st.write("선택한 주소의 데이터:")
            st.dataframe(filtered_data)
        else:
            st.write("선택한 조건에 해당하는 데이터가 없습니다.")
    else:
        st.write("두 번째 주소를 선택하세요.")
else:
    st.write("데이터에 '주소' 열이 없습니다.")