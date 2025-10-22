import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import math
import base64
import requests 
from plotly.subplots import make_subplots 
from PIL import Image
from io import BytesIO


# --- ตั้งค่าหน้าเว็บ (Page Config) ---
st.set_page_config(layout="wide")

# --- ✅ ส่วนที่แก้ไข: จัดรูปภาพและข้อความให้อยู่บรรทัดเดียวกัน ---
col1, col2 = st.columns([1, 10])

with col1:
    st.image("https://raw.githubusercontent.com/daemuktnant-MFC/streamlit-assets/main/Rider_pic.png", width=80)

with col2:
    # เปลี่ยนจาก st.title เป็น st.header เพื่อให้ขนาดใกล้เคียงกับรูปภาพที่จัดวาง
    # หรือใช้ st.markdown("<h1 style='margin-top: 0;'>MFC SD Monitoring Dashboard</h1>", unsafe_allow_html=True)
    # แต่ st.header น่าจะเหมาะสมที่สุดสำหรับการจัดวางแนวนอน
    st.header("MFC SD Monitoring Dashboard")

# 💥 แก้ไข: เพิ่ม verify=False ใน requests.get() เพื่อแก้ปัญหา SSL 💥
def get_base64_image(img_source): 
    data = None
    image_format = "png" # Default format

    if img_source.startswith("http"):
        # ถ้าเป็น URL (Web Link)
        try:
            # 💥 แก้ไข: เพิ่ม verify=False เพื่อหลีกเลี่ยง SSLError 💥
            response = requests.get(img_source, timeout=10, verify=False) 
            response.raise_for_status() # เช็คว่าดาวน์โหลดสำเร็จหรือไม่
            data = response.content
            # พยายามดึงนามสกุลไฟล์จาก URL
            format_ext = img_source.split('.')[-1].lower()
            if format_ext in ['png', 'jpg', 'jpeg', 'gif']:
                 image_format = format_ext.replace('jpg', 'jpeg')
        except requests.exceptions.RequestException as e:
            st.error(f"Error downloading image from URL: {img_source} - {e}") 
            st.warning("คำแนะนำ: หากยังเกิด Error อีก อาจต้องอัปโหลดรูปภาพผ่าน st.file_uploader แทน")
            return None, "png"
    else:
        # ถ้าเป็น Local Path
        try:
            with open(img_source, "rb") as f:
                data = f.read()
            format_ext = img_source.split('.')[-1].lower()
            if format_ext in ['png', 'jpg', 'jpeg', 'gif']:
                 image_format = format_ext.replace('jpg', 'jpeg')
        except FileNotFoundError:
            st.error(f"Error: Local image file not found at {img_source}")
            return None, "png"

    if data:
        # คืนค่า Base64 และรูปแบบภาพ
        return base64.b64encode(data).decode(), image_format
    return None, "png"


# --- ฝังรูปหุ่นยนต์ถาวร (ใส่ URL ของไฟล์ภาพที่คุณอัปโหลด) ---
# 💥 แก้ไข: ต้องใช้ Raw Link (รูปแบบ https://raw.githubusercontent.com/...)
ROBOT_IMAGE_URL = "https://raw.githubusercontent.com/daemuktnant-MFC/streamlit-assets/main/Robot_pic.png" 
robot_base64, robot_format = get_base64_image(ROBOT_IMAGE_URL) # 💥 รับค่า Base64 และ Format

# 💥 ส่วนที่เพิ่ม: Custom CSS สำหรับ KPI 💥
st.markdown("""
<style>
/* ปรับขนาดตัวเลข KPI */
div[data-testid="stMetricValue"] {
    font-size: 40px; /* 💥 ตัวเลข KPI ใหญ่ขึ้น */
    font-weight: bold;
}
/* ปรับขนาดชื่อหัวข้อ KPI */
div[data-testid="stMetricLabel"] {
    font-size: 16px; /* 💥 ชื่อหัวข้อ KPI ใหญ่ขึ้น */
}
</style>
""", unsafe_allow_html=True)
# 💥 สิ้นสุด Custom CSS 💥

# --- ฟังก์ชันสำหรับโหลดข้อมูลจากไฟล์ที่อัปโหลด ---
@st.cache_data
def load_data(uploaded_file):
    try:
        # อ่านไฟล์ Excel โดยตรง
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์ Excel: {e}")
        st.error("กรุณาตรวจสอบว่าไฟล์เป็น .xlsx หรือ .xls ที่ถูกต้อง")
        return None

# --- Sidebar สำหรับอัปโหลดไฟล์ ---
st.sidebar.header("Upload File")
uploaded_file = st.sidebar.file_uploader(
    "กรุณาเลือกไฟล์ Excel (.xlsx, .xls)", 
    type=["xlsx", "xls"]
)

# --- ตรวจสอบว่ามีการอัปโหลดไฟล์หรือไม่ ---
if uploaded_file is not None:
    
    df = load_data(uploaded_file)

    if df is not None:

        # --- คำนวณ KPIs ---
        total_orders = df['Order ID'].nunique()
        total_value = df['Net Order Value'].sum()
        rounded_total_value = math.ceil(total_value) # 💥 ปัด Total Value ขึ้น
        total_complete = df[df['Status'] == 'COMPLETE'].shape[0]
        total_on_process = total_orders - total_complete # 💥 คำนวณ On Process
        total_unsuccessful = df[df['Status'] == 'UNSUCCESSFUL ON DEMAND DELIVERY'].shape[0]
        total_riders = df['Rider Name'].nunique()

        # --- แสดงผล KPIs (แถวบนสุด) - แก้ไขเป็น 7 คอลัมน์ ---
        kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5, kpi_col6, kpi_col7 = st.columns(7)

        with kpi_col1:
            st.metric(label="Total Order", value=f"{total_orders:,}")
        with kpi_col2:
            st.metric(label="Total Complete", value=f"{total_complete:,}")
        with kpi_col3:
            st.metric(label="On Process", value=f"{total_on_process:,}")
        with kpi_col4:
            st.metric(label="Total Cancel", value=f"{total_unsuccessful:,}")
        with kpi_col5:
            st.metric(label="Total Rider", value=f"{total_riders:,}")
        with kpi_col6:
            st.metric(label="Total Value", value=f"{rounded_total_value:,}") # 💥 ใช้ค่าที่ปัดแล้ว
        with kpi_col7:
            # 💥 ส่วนนี้ใช้รูปหุ่นยนต์จากด้านบน แต่ปรับ width ให้เข้ากับ kpi_col7 (200px แทน 300px)
            if robot_base64:
                st.markdown(
                    f"""
                    <div style='text-align:center'>
                        <img src='data:image/{robot_format};base64,{robot_base64}' width='500'> 
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info("No Image")


        # --- สร้าง Divider ---
        st.markdown("---")

        # --- เตรียมข้อมูลสำหรับกราฟ ---
        
        # 1. คำนวณ Over SLA KPI (KPI DOT Chart)
        
        # กรอง Order ที่ไม่ใช่ 'CANCEL' เพื่อใช้ในการคำนวณ KPI และ Rider Chart
        df_non_cancel = df[df['Status'] != 'CANCEL'].copy()
        
        # คำนวณจำนวน Order ทั้งหมดที่ไม่ใช่ Cancel
        total_orders_non_cancel = df_non_cancel['Order ID'].nunique()
        
        # คำนวณจำนวน Order ที่ 'Over SLA' ในกลุ่มที่ไม่ใช่ Cancel
        over_sla_orders = df_non_cancel[df_non_cancel['SLA STS'] == 'Over SLA']['Order ID'].nunique()
        
        # คำนวณอัตราส่วน
        if total_orders_non_cancel > 0:
            over_sla_rate = (over_sla_orders / total_orders_non_cancel) * 100
        else:
            over_sla_rate = 0.0
            
        # กำหนดสีตามเงื่อนไข (Over SLA Rate มากกว่า 0 จะเป็นสีแดง ส่วนที่เหลือเป็นสีน้ำเงิน)
        display_color = 'red' if over_sla_rate > 0 else 'blue'
        
        # 2. เตรียมข้อมูลสำหรับกราฟ Rider (ใช้ df_non_cancel)
        rider_order_counts = df_non_cancel.groupby('Rider Name')['Order ID'].nunique().reset_index()
        rider_order_counts.columns = ['Rider Name', 'Total Orders']
        rider_order_counts = rider_order_counts.sort_values(by='Total Orders', ascending=False)
        rider_order_counts = rider_order_counts.dropna(subset=['Rider Name'])

        # --- แสดงผลกราฟ (แถวกลาง) - ปรับอัตราส่วนคอลัมน์เป็น (1, 2) ---
        chart_col1, chart_col2 = st.columns((1, 2))

        # กราฟวงกลมสำหรับ SLA Status ---
        with chart_col1:
            if 'SLA STS' in df.columns:
                
                # --- 1. กรองข้อมูล 'Cancel' ออก ---
                # เราจะใช้เฉพาะข้อมูลที่ไม่ใช่ 'Cancel' ในการสร้างกราฟนี้
                df_sla_filtered = df[df['SLA STS'] != 'Cancel']['SLA STS'].dropna()

                # --- 2. สร้าง Map เพื่อรวมกลุ่มสถานะ ---
                # กำหนดให้ 'Within SLA', 'Pending', 'Dispatched' ถูกรวมเป็น 'DOT'
                # 'Over SLA' จะยังคงเป็น 'Over SLA'
                replacement_map = {
                    'Within SLA': 'DOT',
                    'Pending': 'DOT',
                    'Dispatched': 'DOT'
                }
                
                # --- 3. ทำการ Map ข้อมูลและนับจำนวน ---
                # ใช้ .replace() เพื่อเปลี่ยนชื่อกลุ่ม แล้วจึง .value_counts()
                sla_mapped = df_sla_filtered.replace(replacement_map)
                sla_counts = sla_mapped.value_counts().reset_index()
                sla_counts.columns = ['SLA STS', 'Count']
                
                # --- 4. สร้าง Pie chart (จากข้อมูลที่ Map แล้ว) ---
                fig_sla_pie = px.pie(
                    sla_counts,
                    names='SLA STS',    # ตอนนี้จะมีแค่ '% DOT' และ 'Over SLA'
                    values='Count',
                    hole=0.4, # กราฟโดนัท
                    color='SLA STS',
                    color_discrete_map={ # อัปเดตสีให้ตรงกับกลุ่มใหม่
                        'DOT': '#0099FF',      # สีเขียว
                        'Over SLA': '#d62728'   # สีแดง
                    }
                )

                # ... (Code lines for creating fig_sla_pie)

                # --- 5. ปรับแต่งการแสดงผล ---
                fig_sla_pie.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    rotation=270,
                    pull=[0.05 if s == 'Over SLA' else 0 for s in sla_counts['SLA STS']],
                    textfont=dict(size=40),
                    marker=dict(
                        line=dict(color='#000000', width=1)
                    )
                )
                # ⬇️ ตรวจสอบให้แน่ใจว่าบรรทัดนี้มีจำนวนการเยื้อง (Indentation) เท่ากับบรรทัดด้านบน
                fig_sla_pie.update_layout(
                    legend_title_text='สถานะ',
                    margin=dict(t=0, b=0, l=0, r=0)
                )

                # 6. แสดงกราฟใน Streamlit
                st.plotly_chart(fig_sla_pie, use_container_width=True)

            else:
                st.warning("ไม่สามารถสร้างกราฟวงกลมได้ เนื่องจากไม่พบคอลัมน์ 'SLA STS'")

        # กราฟที่ 2: Total Order by Rider (จะกว้างขึ้น)
        with chart_col2:
            st.subheader("Total Order by Rider (Top 20)")
            
            top_riders = rider_order_counts.head(20)
            
            fig_rider_bar = px.bar(
                top_riders,
                x='Total Orders',  
                y='Rider Name',    
                orientation='h',    
                text='Total Orders', 
                labels={'Total Orders': 'Number of Orders', 'Rider Name': 'Rider Name'},
                color='Total Orders', 
                color_continuous_scale=px.colors.sequential.Teal
            )
            
            fig_rider_bar.update_layout(yaxis={'categoryorder':'total ascending'})
            
            fig_rider_bar.update_traces(
                textposition='inside',
                textangle=0,
                insidetextanchor='start', 
                insidetextfont=dict(color='#FF9933')
            )
            
            st.plotly_chart(fig_rider_bar, use_container_width=True)

        # --- สร้าง Divider ---
        st.markdown("---")

        # --- กราฟแท่งรายชั่วโมง (Stacked by SLA Status) ---
        st.subheader("Status Order by Hour")

        if 'Hours' in df.columns and 'SLA STS' in df.columns:
            
            # แปลงเป็น string เพื่อให้ Plotly มองเป็น category
            df['Hours'] = df['Hours'].astype(str)
            
            df_hourly = df.groupby(['Hours', 'SLA STS']).size().reset_index(name='Count')
            df_hourly_total = df_hourly.groupby('Hours')['Count'].sum().reset_index(name='TotalCount')

            # --- ส่วนที่แก้ไข: การจัดเรียงเวลา ---
            # 1. สร้างลิสต์ของชั่วโมงที่ต้องการเรียง (08, 09, 10, ... 18)
            # เราจะค้นหาค่าที่ไม่ซ้ำกันในคอลัมน์ 'Hours', แปลงเป็น int, เรียง, แล้วแปลงกลับเป็น str
            unique_hours = df['Hours'].unique()
            sorted_hours = sorted([int(h) for h in unique_hours])
            sorted_hours_str = [str(h) for h in sorted_hours]
            # 💥 เพิ่มบรรทัดนี้ เพื่อจัดเรียง df_hourly_total ให้ตรงกับแกน X
            df_hourly_total['Hours'] = pd.Categorical(df_hourly_total['Hours'], categories=sorted_hours_str, ordered=True)
            df_hourly_total = df_hourly_total.sort_values('Hours')

            # --- กำหนดแผนที่สีใหม่ ---
            color_map = {
                'Within SLA': '#0099FF',      
                'Over SLA': '#FF3300',        
                'Dispatched': '#CC00FF',    
                'Pending': '#8ED973',        
                'Cancel': '#B2B2B2'          
            }

            # 1. สร้าง Figure ด้วย Subplots เพื่อรองรับ Secondary Y-Axis
            fig_hourly = make_subplots(specs=[[{"secondary_y": True}]])

            # 2. เพิ่ม Bar Traces (Stacked Column) สำหรับ SLA Status
            sla_statuses = ['Within SLA', 'Over SLA', 'Dispatched', 'Pending', 'Cancel']
    
            for status in sla_statuses:
                df_status = df_hourly[df_hourly['SLA STS'] == status]
                if not df_status.empty:
                    fig_hourly.add_trace(
                        go.Bar(
                            x=df_status['Hours'],
                            y=df_status['Count'],
                            name=status,
                            marker_color=color_map.get(status, '#B2B2B2'),
                            text=df_status['Count'],
                            # ตั้งค่าเริ่มต้นของตัวเลขทั้งหมด
                            textposition='inside',
                            textangle=0
                        ),
                        secondary_y=False, # ใช้แกน Y หลัก (ซ้าย)
                    )

            # 3. เพิ่ม Line Trace (Scatter) สำหรับ Total Order (แกน Y รอง)
            fig_hourly.add_trace(
                go.Scatter(
                    x=df_hourly_total['Hours'],
                    y=df_hourly_total['TotalCount'],
                    name='Total',
                    mode='lines+markers+text',
                    line=dict(color='#FFCC66', width=4, shape='spline'),
                    marker=dict(size=10, color='white', line=dict(width=2, color='#00CCCC')),
                    text=df_hourly_total['TotalCount'],
                    textposition='top center',
                    textfont=dict(color='black', size=16), # 💥 แก้ไข: เพิ่มขนาดตัวอักษร Total
                ),
                secondary_y=True, # 💥 ใช้แกน Y รอง (ขวา)
            )

            # 4. ปรับแต่ง Layout และ Axes
    
            # 💥 ตั้งค่า Stacked Bar
            fig_hourly.update_layout(barmode='stack')
    
            # 💥 กำหนดขนาดตัวอักษรเฉพาะ 'Within SLA' (Trace ลำดับที่ 0 หาก Within SLA มีข้อมูล)
            # เราใช้ชื่อ trace เพื่อให้แน่ใจว่าถูกต้อง
            fig_hourly.update_traces(
                selector=dict(name='Within SLA', type='bar'), 
                textposition='inside',
                textfont=dict(size=20) # 💥 เพิ่มขนาดตัวอักษร Within SLA
            )

           # 💥 กำหนดลำดับ X-Axis และชื่อแกน
            fig_hourly.update_xaxes(
                type='category',
                categoryorder='array',
                categoryarray=sorted_hours_str,
                title_text='Hour of Day'
            )
    
           # 💥 กำหนดแกน Y หลัก (ซ้าย)
            fig_hourly.update_yaxes(
                title_text="Number of Orders (SLA Status)", 
                secondary_y=False,
                # ตั้งค่า Y-axis range ให้ Total Order อยู่ด้านบน (อาจจะต้องปรับ max_y อีกครั้ง)
                range=[0, df_hourly_total['TotalCount'].max() * 1.5] 
            )
    
            # 💥 กำหนดแกน Y รอง (ขวา)
            fig_hourly.update_yaxes(
                title_text="Total Order", 
                secondary_y=True,
                showgrid=False, # ซ่อน Grid line ของแกนรอง
                title_standoff=10,
                # กำหนด Range ให้ใกล้เคียงกับแกน Y หลัก เพื่อไม่ให้เส้นดูแบนเกินไป
                showticklabels=False, # 👈 ซ่อนตัวเลขกำกับแกน Y รอง
                range=[0, df_hourly_total['TotalCount'].max() * 1.15] 
            )
            
            # 💥 ปรับ Layout โดยรวม (เพิ่ม Legend)
            fig_hourly.update_layout(
                barmode='stack',
                # 💥 แก้ไข: ย้าย Legend ไปด้านบนขวา
                margin=dict(t=50, r=120),
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1, # ตำแหน่งบนสุด
                    xanchor="right",
                    x=1.1 # ตำแหน่งขวาสุด (นอกกราฟเล็กน้อย)
                )
            )

            st.plotly_chart(fig_hourly, use_container_width=True)

        else:
            st.warning("ไม่สามารถสร้างกราฟรายชั่วโมงได้ เนื่องจากไม่พบคอลัมน์ 'Hours' หรือ 'SLA STS'")

        # --- (ทางเลือก) แสดงตารางข้อมูลดิบ ---
        with st.expander("ดูข้อมูลดิบ (Raw Data)"):
            st.dataframe(df)

else:
    # --- หน้าจอเริ่มต้น เมื่อยังไม่มีการอัปโหลดไฟล์ ---
    st.info("👋 กรุณาอัปโหลดไฟล์ Excel ของคุณที่ Sidebar ด้านซ้ายเพื่อเริ่มต้นใช้งาน")




