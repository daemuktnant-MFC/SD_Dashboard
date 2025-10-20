import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

# --- ตั้งค่าหน้าเว็บ (Page Config) ---
st.set_page_config(
    page_title="SD Monitoring Dashboard",
    page_icon="📊",
    layout="wide"
)

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
        
        # --- ส่วนหัวของ Dashboard ---
        st.title("📊 SD Monitoring Dashboard")

        # --- คำนวณ KPIs ---
        total_orders = df['Order ID'].nunique()
        total_value = df['Net Order Value'].sum()
        total_complete = df[df['Status'] == 'COMPLETE'].shape[0]
        total_unsuccessful = df[df['Status'] == 'UNSUCCESSFUL ON DEMAND DELIVERY'].shape[0]
        
        total_riders = df['Rider Name'].nunique()

        # --- แสดงผล KPIs (แถวบนสุด) - แก้ไขเป็น 5 คอลัมน์ ---
        kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

        with kpi_col1:
            st.metric(label="Total Order", value=f"{total_orders:,}")
        
        with kpi_col2:
            st.metric(label="Total Value", value=f"{total_value:,.2f}")
        
        with kpi_col3:
            st.metric(label="Total Complete", value=f"{total_complete:,}")
        
        with kpi_col4:
            st.metric(label="Total Cancel", value=f"{total_unsuccessful:,}")
        
        # --- (ส่วนที่เพิ่มใหม่) แสดงผล Total Rider ---
        with kpi_col5:
            st.metric(label="Total Rider", value=f"{total_riders:,}")


        # --- สร้าง Divider ---
        st.markdown("---")

        # --- เตรียมข้อมูลสำหรับกราฟ ---
        payment_counts = df['Payment Code'].value_counts().reset_index()
        payment_counts.columns = ['Payment Code', 'Count']
        
        rider_order_counts = df.groupby('Rider Name')['Order ID'].nunique().reset_index()
        rider_order_counts.columns = ['Rider Name', 'Total Orders']
        rider_order_counts = rider_order_counts.sort_values(by='Total Orders', ascending=False)
        rider_order_counts = rider_order_counts.dropna(subset=['Rider Name'])

        # --- แสดงผลกราฟ (แถวกลาง) - ปรับอัตราส่วนคอลัมน์เป็น (1, 2) ---
        chart_col1, chart_col2 = st.columns((1, 2)) 
        
        # กราฟที่ 1: Total Order by Payment (จะเล็กลง)
        with chart_col1:
            st.subheader("Total Order by Payment")
            fig_payment = px.pie(payment_counts, names='Payment Code', values='Count', hole=0.3)
            fig_payment.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_payment, use_container_width=True)

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
        st.subheader("Total Order by Hour (Stacked by SLA Status)")

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

            # --- กำหนดแผนที่สีใหม่ ---
            color_map = {
                'Within SLA': '#0066FF',     
                'Over SLA': '#FF3300',        
                'Dispatched': '#CC66FF',   
                'Pending': '#00FF00',        
                'Cancel': '#B2B2B2'         
            }

            fig_hourly = px.bar(
                df_hourly,
                x='Hours',
                y='Count',
                color='SLA STS',
                text='Count',
                labels={'Hours': 'Hour of Day', 'Count': 'Number of Orders'},
                color_discrete_map=color_map 
            )
            fig_hourly.update_traces(textposition='inside',textangle=0)

            fig_hourly.add_trace(go.Scatter(
                x=df_hourly_total['Hours'],
                y=df_hourly_total['TotalCount'],
                text=df_hourly_total['TotalCount'],
                mode='text',
                textposition='top center',
                textfont=dict(color='black', size=14),
                showlegend=False
            ))
            
            max_y = df_hourly_total['TotalCount'].max() * 1.15
            fig_hourly.update_layout(
                yaxis_range=[0, max_y],
                xaxis={
                    'type': 'category',
                    # 2. ใช้ sorted_hours_str เพื่อกำหนดลำดับหมวดหมู่
                    'categoryorder': 'array',
                    'categoryarray': sorted_hours_str 
                }
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
