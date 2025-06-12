import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
import json
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

# === Setup awal ===
st.set_page_config(page_title="Asian Games Dashboard", layout="wide")
st.title("🥇 Asian Games Medal Dashboard")

# === Load data dari Google Spreadsheet ===
@st.cache_resource
def load_data():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(json.dumps(creds_dict)), scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(st.secrets["sheet_url"]).sheet1
    df = get_as_dataframe(sheet).dropna(how="all")
    df['Country'] = df['NOC'].str.extract(r'^(.*?)\s\(')
    df['Year'] = df['Year'].astype(int)
    return df, sheet

df, sheet = load_data()

# === Sidebar Filter ===
st.sidebar.header("🎯 Filter Data")
years = sorted(df['Year'].unique())
countries = sorted(df['Country'].dropna().unique())
selected_years = st.sidebar.multiselect("Pilih Tahun", years, default=years)
selected_countries = st.sidebar.multiselect("Pilih Negara", countries, default=countries)

filtered_df = df[(df['Year'].isin(selected_years)) & (df['Country'].isin(selected_countries))]

# === Edit Data Langsung ===
st.subheader("📄 Edit Data Langsung")
edited_df = st.data_editor(filtered_df, num_rows="dynamic", use_container_width=True, key="edit")

if st.button("💾 Simpan Edit"):
    set_with_dataframe(sheet, edited_df)
    st.success("Perubahan berhasil disimpan ke Google Spreadsheet!")

# === Visualisasi 1: Bar Chart Total Medali ===
st.markdown("### 📊 Total Medali per Negara (Animasi per Tahun)")
fig1 = px.bar(
    filtered_df,
    x='Country', y='Total', color='Country',
    animation_frame='Year',
    labels={'Total': 'Total Medals'},
    title='Total Medals per Country (Animated by Year)',
    height=600
)
st.plotly_chart(fig1, use_container_width=True)

# === Visualisasi 2: Line Chart ===
st.markdown("### 📈 Tren Medali Gold, Silver, Bronze per Negara")
df_melt = filtered_df.melt(id_vars=['Year', 'Country'], value_vars=['Gold', 'Silver', 'Bronze'],
                           var_name='Medal', value_name='Count')
fig2 = px.line(df_melt, x='Year', y='Count', color='Country', line_dash='Medal',
               markers=True, title='Medal Count over the Years by Country')
st.plotly_chart(fig2, use_container_width=True)

# === Visualisasi 3: Top 3 Negara ===
st.markdown("### 🏆 Top 3 Negara dengan Total Medali (Rentang Terfilter)")
if not filtered_df.empty:
    top3_df = (
        filtered_df.groupby('Country')[['Gold', 'Silver', 'Bronze']]
        .sum()
        .assign(Total=lambda x: x.sum(axis=1))
        .sort_values('Total', ascending=False)
        .head(3)
        .reset_index()
    )

    radar_fig = go.Figure()
    for _, row in top3_df.iterrows():
        radar_fig.add_trace(go.Scatterpolar(
            r=[row['Gold'], row['Silver'], row['Bronze']],
            theta=['Gold', 'Silver', 'Bronze'],
            fill='toself',
            name=row['Country']
        ))

    radar_fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        title="Radar Chart Top 3 Negara - Komposisi Medali"
    )
    st.plotly_chart(radar_fig, use_container_width=True)

# === Visualisasi 4: Heatmap ===
st.markdown("### 🔥 Heatmap Total Medali per Negara dan Tahun")
heatmap_df = filtered_df.pivot_table(index='Country', columns='Year', values='Total', aggfunc='sum').fillna(0)
fig3 = go.Figure(data=go.Heatmap(
    z=heatmap_df.values,
    x=heatmap_df.columns,
    y=heatmap_df.index,
    colorscale='YlOrRd'
))
fig3.update_layout(title='Heatmap Total Medali per Negara dan Tahun', xaxis_title='Tahun', yaxis_title='Negara')
st.plotly_chart(fig3, use_container_width=True)

# === Visualisasi 5: Treemap Tahun Terbaru ===
st.markdown("### 🌳 Treemap Dominasi Medali Negara - Tahun Terbaru")
if not filtered_df.empty:
    latest_year_filtered = max(filtered_df['Year'].unique())
    latest_data_filtered = filtered_df[filtered_df['Year'] == latest_year_filtered]
    fig4 = px.treemap(latest_data_filtered, path=['Country'], values='Total',
                      color='Total', color_continuous_scale='sunsetdark',
                      title=f'Treemap Dominasi Medali – Tahun {latest_year_filtered}')
    st.plotly_chart(fig4, use_container_width=True)
