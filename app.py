import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
import numpy as np
from pathlib import Path

#Page config
st.set_page_config(
    page_title="Bangladesh Population Dashboard",
    page_icon="🇧🇩",
    layout="wide",
)

# Custom CSS
def load_css(file_path: str = "styles.css") -> None:
    css = Path(file_path).read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


load_css()


#Name mapping (Doing it because there is naming problem)
NAME_MAP = {
    'Barishal': 'Barisal',
    'Chapai Nawabganj': 'Chapainawabganj',
    'Cumilla': 'Comilla',
    'Bogra': 'Bogura',
    'Netrakona': 'Netrokona',
    'Jaipurhat': 'Joypurhat',
}


# Load data 
@st.cache_data
def load_data():
    df = pd.read_csv('data.csv')
    df['geo_name'] = df['Name'].replace(NAME_MAP)
    for col in ['Population_1991', 'Population_2001', 'Population_2011', 'Population_2022']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['density_2022'] = (df['Population_2022'] / df['Area (km2)']).round(1)
    df['growth_91_22'] = (((df['Population_2022'] - df['Population_1991']) / df['Population_1991']) * 100).round(1)
    df['growth_11_22'] = (((df['Population_2022'] - df['Population_2011']) / df['Population_2011']) * 100).round(1)
    return df

@st.cache_data
def load_geo():
    with open('bangladesh.json') as f:
        return json.load(f)

df = load_data()
geo = load_geo()

YEAR_COLS = {
    '1991': 'Population_1991',
    '2001': 'Population_2001',
    '2011': 'Population_2011',
    '2022': 'Population_2022',
}

# Sidebar 
with st.sidebar:
    st.markdown('<div style="font-family:Playfair Display,serif;font-size:1.3rem;font-weight:700;color:#f0f6fc;margin-bottom:1rem;">🇧🇩 Controls</div>', unsafe_allow_html=True)

    selected_year = st.selectbox('Census Year', list(YEAR_COLS.keys()), index=3)
    pop_col = YEAR_COLS[selected_year]

    st.markdown("---")
    map_metric = st.radio('Map Colour By', ['Population', 'Population Density (per km²)', 'Growth Since 1991 (%)'])

    st.markdown("---")
    st.markdown('<div style="font-size:0.75rem;color:#8b949e;letter-spacing:1px;">DATA SOURCE</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.8rem;color:#6e7681;">Bangladesh Bureau of Statistics · Census 1991–2022</div>', unsafe_allow_html=True)


# Header 
st.markdown('<div class="hero-title">Bangladesh Population<br>Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">District-level Census Analysis · 1991 – 2022</div>', unsafe_allow_html=True)
st.markdown('<div class="green-line"></div>', unsafe_allow_html=True)

#  Top KPI cards
total_2022 = df['Population_2022'].sum()
total_2011 = df['Population_2011'].sum()
total_1991 = df['Population_1991'].sum()
total_area = df['Area (km2)'].sum()
avg_density = (total_2022 / total_area).round(1)
nat_growth = ((total_2022 - total_1991) / total_1991 * 100).round(1)
most_pop = df.loc[df['Population_2022'].idxmax()]

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Population ({selected_year})</div>
        <div class="metric-value">{df[pop_col].sum()/1e6:.1f}M</div>
        <div class="metric-delta">↑ Across 64 Districts</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Avg Population Density</div>
        <div class="metric-value">{avg_density:,.0f}</div>
        <div class="metric-delta">People per km² (2022)</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">National Growth 1991–2022</div>
        <div class="metric-value">{nat_growth:.1f}%</div>
        <div class="metric-delta">↑ {(total_2022 - total_1991)/1e6:.1f}M added</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Most Populous District (2022)</div>
        <div class="metric-value">{most_pop['Name']}</div>
        <div class="metric-delta">{most_pop['Population_2022']/1e6:.2f}M people</div>
    </div>""", unsafe_allow_html=True)

st.markdown('<hr class="styled">', unsafe_allow_html=True)

# Map 
st.markdown('<div class="section-title">Interactive District Map</div>', unsafe_allow_html=True)

# Build a driven map values so changing Census Year updates map and tooltip.
df_map = df[['geo_name', 'Area (km2)', pop_col]].copy()
df_map['population_selected'] = pd.to_numeric(df_map[pop_col], errors='coerce')
df_map['density_selected'] = (df_map['population_selected'] / df_map['Area (km2)']).round(1)
df_map['growth_since_1991_selected'] = (
    (df_map['population_selected'] - df['Population_1991']) / df['Population_1991'] * 100
).round(1)

if map_metric == 'Population':
    map_col = 'population_selected'
    legend_name = f'Population ({selected_year})'
elif map_metric == 'Population Density (per km²)':
    map_col = 'density_selected'
    legend_name = f'Population Density ({selected_year}) (per km²)'
else:
    map_col = 'growth_since_1991_selected'
    legend_name = f'Growth Since 1991 to {selected_year} (%)'

df_map[map_col] = pd.to_numeric(df_map[map_col], errors='coerce')
df_map[map_col] = df_map[map_col].where(np.isfinite(df_map[map_col]), np.nan)

df_map.set_index('geo_name', inplace=True)

# Pass only valid numeric values to choropleth.
choropleth_data = df_map.reset_index().dropna(subset=[map_col])

m = folium.Map(
    location=[23.8, 90.3],
    zoom_start=7,
    scrollWheelZoom=False,
    tiles='CartoDB dark_matter'
)

choropleth = folium.Choropleth(
    geo_data=geo,
    data=choropleth_data,
    columns=('geo_name', map_col),
    key_on='feature.properties.ADM2_EN',
    fill_color='YlOrRd',
    fill_opacity=0.8,
    line_opacity=0.4,
    line_color='#30363d',
    legend_name=legend_name,
    highlight=True,
    nan_fill_color='#21262d',
)
choropleth.geojson.add_to(m)

# Add tooltips
for feature in choropleth.geojson.data['features']:
    dist = feature['properties']['ADM2_EN']
    div = feature['properties']['ADM1_EN']
    if dist in df_map.index:
        row = df_map.loc[dist]
        feature['properties']['population_selected'] = f"{row['population_selected']:,.0f}"
        feature['properties']['density_selected'] = f"{row['density_selected']:,.1f} /km²"
        feature['properties']['growth_since_1991_selected'] = f"{row['growth_since_1991_selected']:+.1f}% since 1991"
        feature['properties']['area'] = f"{row['Area (km2)']:,.0f} km²"
        feature['properties']['div'] = div
    else:
        feature['properties']['population_selected'] = 'N/A'
        feature['properties']['density_selected'] = 'N/A'
        feature['properties']['growth_since_1991_selected'] = 'N/A'
        feature['properties']['area'] = 'N/A'
        feature['properties']['div'] = div

choropleth.geojson.add_child(
    folium.features.GeoJsonTooltip(
        fields=['ADM2_EN', 'div', 'population_selected', 'density_selected', 'growth_since_1991_selected', 'area'],
        aliases=['District', 'Division', f'Population ({selected_year})', f'Density ({selected_year})', f'Growth (1991 to {selected_year})', 'Area'],
        labels=True,
        style="background:#161b22;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;font-family:sans-serif;font-size:12px;"
    )
)

st_map = st_folium(m, width='100%', height=500)

# Capture clicked district
clicked_district = None
if st_map and st_map.get('last_active_drawing'):
    clicked_district = st_map['last_active_drawing']['properties'].get('ADM2_EN')


# District Detail (if clicked) 
if clicked_district:
    # reverse lookup
    csv_name = {v: k for k, v in NAME_MAP.items()}.get(clicked_district, clicked_district)
    row_match = df[df['Name'] == csv_name]
    if not row_match.empty:
        row = row_match.iloc[0]
        st.markdown(f'<div class="section-title">📍 {csv_name} — District Detail</div>', unsafe_allow_html=True)
        dc1, dc2, dc3, dc4 = st.columns(4)
        selected_pop_val = row[pop_col]
        selected_density_val = round(selected_pop_val / row['Area (km2)'], 1)
        selected_growth_from_1991 = round(((selected_pop_val - row['Population_1991']) / row['Population_1991']) * 100, 1)
        with dc1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Population {selected_year}</div><div class="metric-value">{selected_pop_val:,.0f}</div></div>', unsafe_allow_html=True)
        with dc2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Area</div><div class="metric-value">{row["Area (km2)"]:,} km²</div></div>', unsafe_allow_html=True)
        with dc3:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Growth 1991→{selected_year}</div><div class="metric-value">{selected_growth_from_1991:+.1f}%</div></div>', unsafe_allow_html=True)
        with dc4:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Density ({selected_year})</div><div class="metric-value">{selected_density_val:,.0f}/km²</div></div>', unsafe_allow_html=True)


st.markdown('<hr class="styled">', unsafe_allow_html=True)

# Rankings 
r1, r2 = st.columns(2)

with r1:
    st.markdown('<div class="section-title">🏆 Top 10 Most Populous Districts</div>', unsafe_allow_html=True)
    top10 = df.nlargest(10, 'Population_2022')[['Name', 'Population_2022']]
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    for i, (_, row) in enumerate(top10.iterrows(), 1):
        st.markdown(f"""
        <div class="rank-item">
            <span class="rank-num">#{i}</span>
            <span class="rank-name">{row['Name']}</span>
            <span class="rank-val">{row['Population_2022']/1e6:.2f}M</span>
        </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with r2:
    st.markdown('<div class="section-title">📈 Top 10 Fastest Growing Districts (1991–2022)</div>', unsafe_allow_html=True)
    top_growth = df.nlargest(10, 'growth_91_22')[['Name', 'growth_91_22']]
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    for i, (_, row) in enumerate(top_growth.iterrows(), 1):
        st.markdown(f"""
        <div class="rank-item">
            <span class="rank-num">#{i}</span>
            <span class="rank-name">{row['Name']}</span>
            <span class="rank-val" style="color:#56d364;">+{row['growth_91_22']:.1f}%</span>
        </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<hr class="styled">', unsafe_allow_html=True)

# Summary Report 
st.markdown('<div class="section-title">📋 Population Summary Report</div>', unsafe_allow_html=True)

# Compute report stats
fastest = df.loc[df['growth_91_22'].idxmax()]
densest = df.loc[df['density_2022'].idxmax()]
least_dense = df.loc[df['density_2022'].idxmin()]
top3 = df.nlargest(3, 'Population_2022')['Name'].tolist()
decline_districts = df[df['growth_91_22'] < 0]
high_growth = df[df['growth_91_22'] > 100]

report_html = f"""
<div class="report-card">

<p>
<span class="badge">Overview</span><br>
Bangladesh, one of the world's most densely populated nations, encompasses <strong>64 districts</strong> across 8 administrative divisions. 
Between 1991 and 2022, the country's total population grew from <strong>{total_1991/1e6:.1f} million</strong> to 
<strong>{total_2022/1e6:.1f} million</strong> — an increase of approximately <strong>{(total_2022-total_1991)/1e6:.1f} million people</strong> 
representing a <strong>{nat_growth:.1f}% overall growth rate</strong> over three decades.
</p>

<div class="highlight">
📌 With an average population density of <strong>{avg_density:,.0f} people per km²</strong> (2022), 
Bangladesh remains one of the most densely settled countries on Earth. The total land area of all 64 districts 
covers approximately <strong>{total_area:,.0f} km²</strong>.
</div>

<p>
<span class="badge">Urban Concentration</span><br>
Population remains heavily concentrated in a few districts. <strong>{top3[0]}</strong>, home to the national capital, 
is by far the most populous district with <strong>{df.loc[df['Name']==top3[0], 'Population_2022'].values[0]/1e6:.2f} million</strong> residents in 2022 
— and is also the densest district at <strong>{densest['density_2022']:,.0f} people per km²</strong>. 
Together, the three most populous districts (<strong>{", ".join(top3)}</strong>) account for a significant share of the national population, 
reflecting rapid urbanisation and rural-to-urban migration trends.
</p>

<p>
<span class="badge">Growth Patterns</span><br>
The fastest-growing district between 1991 and 2022 was <strong>{fastest['Name']}</strong>, 
which saw an extraordinary population increase of <strong>+{fastest['growth_91_22']:.1f}%</strong> over this period, 
driven primarily by economic activity and urban expansion. 
{f"A total of <strong>{len(high_growth)}</strong> districts more than doubled their population over these three decades." if len(high_growth) > 0 else ""}
</p>

<p>
<span class="badge">Demographic Pressure & Decline</span><br>
{"In contrast, <strong>" + str(len(decline_districts)) + " districts</strong> experienced population decline between 1991 and 2022 — notably " + ", ".join(f"<strong>{r['Name']}</strong>" for _, r in decline_districts.iterrows()) + " — suggesting outmigration, economic stagnation, or boundary changes over the period." if len(decline_districts) > 0 else "All districts recorded positive population growth across the observed period, though growth rates varied considerably."}
The least densely populated district is <strong>{least_dense['Name']}</strong> in the Chittagong Hill Tracts, 
with just <strong>{least_dense['density_2022']:,.1f} people per km²</strong>, reflecting its forested and hilly terrain.
</p>

<p>
<span class="badge">2011–2022 Decade</span><br>
The most recent intercensal period (2011–2022) reveals continued urbanisation pressure. 
Districts such as <strong>{df.nlargest(1, 'growth_11_22')['Name'].values[0]}</strong> recorded the highest growth 
of <strong>+{df['growth_11_22'].max():.1f}%</strong> in this single decade, 
while the national average growth rate for this period stood at 
<strong>{((total_2022 - total_2011) / total_2011 * 100):.1f}%</strong>.
</p>

<p>
<span class="badge">Outlook</span><br>
These trends highlight the dual challenge facing Bangladesh: managing rapid urban growth in already dense metropolitan 
districts while addressing depopulation and economic marginalisation in peripheral districts. 
Balanced regional development, infrastructure investment outside major cities, and climate resilience planning 
will be critical for equitable population distribution across all 64 districts in the coming decades.
</p>

</div>
"""

st.markdown(report_html, unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;color:#6e7681;font-size:0.8rem;margin-top:3rem;padding-bottom:2rem;">
    Bangladesh Population Dashboard · Data: Bangladesh Bureau of Statistics · Built with Streamlit & Folium
</div>
""", unsafe_allow_html=True)
