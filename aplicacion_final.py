"""
Compatibilidad Espacial
"""
import math
import base64
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# 1. CONFIGURACIÓN Y ESTILO (Fondo, Colores, Fuente)

def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

# Leemos el fondo local
img_fondo = get_base64('fondo.png')
background_css = f'url("data:image/png;base64,{img_fondo}")' if img_fondo else 'none'

# Configuración de la página
st.set_page_config(
    page_title="Compatibilidad Espacial | NASA", 
    page_icon="logo_nasa.png", 
    layout="wide"
)

# Inyección de CSS
st.markdown(
    f"""
    <style>
    /* 1. FUENTE HELVETICA GLOBAL */
    html, body, [class*="css"] {{
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
    }}

    /* 2. IMAGEN DE FONDO */
    [data-testid="stAppViewContainer"] {{
        background-image: linear-gradient(rgba(5, 5, 5, 0.75), rgba(5, 5, 5, 0.85)), {background_css};
        background-size: cover;
        background-position: center top;
        background-attachment: fixed;
    }}

    [data-testid="stHeader"] {{
        background: rgba(0,0,0,0);
    }}

    [data-testid="stSidebar"] {{
        background-color: rgba(14, 17, 23, 0.85) !important;
        backdrop-filter: blur(10px);
    }}

    /* 3. CAJA DE VEREDICTO (Rojo Italiano) */
    .veredicto-box {{ 
        background-color: rgba(30, 33, 41, 0.9); 
        padding: 25px; 
        border-radius: 15px;
        border-left: 8px solid #C8102E;
        margin-top: 10px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
    }}
    .veredicto-box h3 {{ 
        margin-top: 0; 
        color: #C8102E;
        font-weight: bold;
    }}
    
    /* 4. BOTONES */
    .stButton>button {{ 
        background-color: #C8102E; 
        color: white; 
        font-weight: bold; 
        border-radius: 8px;
        border: none;
        transition: 0.3s;
    }}
    .stButton>button:hover {{ 
        background-color: #E0213F; 
        color: white;
    }}

    /* 5. ESTILOS PARA LAS PESTAÑAS (TABS) */
    button[data-baseweb="tab"] {{
        font-size: 1.1em !important;
        font-weight: bold !important;
        color: #aaa !important;
        background-color: transparent !important;
        border-bottom: 3px solid transparent !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: #ffffff !important;
        border-bottom: 3px solid #C8102E !important;
    }}
    div[data-baseweb="tab-list"] {{
        border-bottom: 1px solid rgba(255,255,255,0.1);
        margin-bottom: 20px;
    }}

    /* 6. ESTILOS DE LOS INPUTS DEL SIDEBAR */
    div[data-baseweb="select"] > div, .stTextInput > div > div > input {{
        background-color: rgba(0, 0, 0, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px !important;
        color: white !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# 2. ZONA DEL TÍTULO CON EL LOGO ARRIBA

logo_url = "https://upload.wikimedia.org/wikipedia/commons/e/e5/NASA_logo.svg"

st.markdown(
    f"""
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 15px; margin-top: 20px; margin-bottom: 20px;">
<img src="{logo_url}" style="height: 130px; width: auto;">
<h1 style="color: #C8102E; text-align: center; margin: 0; font-weight: 800; letter-spacing: 1px; text-shadow: 0px 4px 10px rgba(0,0,0,0.8);">
Compatibilidad Espacial
</h1>
</div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    "<p style='text-align:center; font-size: 1.2em; color: #ffffff;'>Encuentra el porcentaje de similitud de los diferentes lugares de la Tierra con la Luna o Marte "
    "para encontrar análogos de exploración.</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# 3. BASE DE DATOS DE REFERENCIA

DESTINOS = {
    "Luna": dict(
        lat=0.67, lon=23.47,
        temp=-23,        # 250 K, media ecuatorial (LRO Diviner)
        rango_t=295,     # 95 a 390 K (NASA Moon Fact Sheet / Diviner)
        presion=3e-13,   # kPa, 3e-15 bar nocturno (NASA Moon Fact Sheet)
        dosis=1.369,     # mSv/día (Chang'E-4 LND, Zhang et al. 2020)
        gravedad=1.62,
        relieve_ideal=(150, 1500),
    ),
    "Marte": dict(
        lat=-4.59, lon=137.44,
        temp=-59,        # ~214 K, media global (NASA Mars Fact Sheet)
        rango_t=80,      # amplitud diaria en Gale (REMS)
        presion=0.61,    # kPa, 610 Pa media global
        dosis=0.67,      # mSv/día (Curiosity RAD, Hassler et al. 2014)
        gravedad=3.73,
        relieve_ideal=(150, 1500),
    ),
}
GEOLOGIAS = [
    "Basalto volcánico / lava",
    "Desierto árido / roca expuesta",
    "Montaña / roca alpina",
    "Glaciar / hielo / permafrost",
    "Suelo sedimentario / vegetación",
    "Costa / humedal",
    "Ácido / rico en hierro (sulfatos, hematita)",
    "Cráter de impacto / roca fracturada",
]

GEO_MATRIZ = {
    "Basalto volcánico / lava":        {"Luna": 100, "Marte": 100},
    "Desierto árido / roca expuesta":  {"Luna": 55,  "Marte": 85},
    "Montaña / roca alpina":           {"Luna": 70,  "Marte": 70},
    "Glaciar / hielo / permafrost":    {"Luna": 40,  "Marte": 50},
    "Suelo sedimentario / vegetación": {"Luna": 15,  "Marte": 30},
    "Costa / humedal":                 {"Luna": 5,   "Marte": 10},
    "Ácido / rico en hierro (sulfatos, hematita)": {"Luna": 15, "Marte": 95},
    "Cráter de impacto / roca fracturada":         {"Luna": 90, "Marte": 80},
}

REFERENCIAS = {
    "Desierto de Arizona": dict(  # Cinder Lake, Flagstaff
        lat=35.32, lon=-111.52, en_vivo=True,
        temp=8.2, rango_t=16.6,   # NOAA 1991-2020, Flagstaff
        elev=2100, presion=78.5, dosis=0.0019, precip=1.4,
        uv=None, agua=None, relieve=None,
        geologia="Basalto volcánico / lava",
        nota="Clima NOAA; relieve, UV y agua en vivo.",
    ),
    "LUNA (ESA-DLR)": dict(
        lat=50.85, lon=7.14,
        temp=20, rango_t=2, elev=60, presion=100.6, dosis=0.0007, uv=0, precip=0.0,
        agua=False, relieve=0, gravedad=1.62,
        geologia="Basalto volcánico / lava",
        nota="Publicados: simulante y gravedad. Supuestos: temperatura, presión, radiación.",
    ),
    "Habitat Marte": dict(  # supuesto: MDRS, Utah
        lat=38.41, lon=-110.79, en_vivo=True,
        temp=12, rango_t=20, elev=1400, presion=85.6, dosis=0.0013, precip=0.38,
        uv=None, agua=None, relieve=None,
        geologia="Desierto árido / roca expuesta",
        nota="MDRS, Hanksville, Utah.",
    ),
}

CATEGORIAS = [
    "Temperatura", "Amplitud térmica", "Presión", "Radiación",
    "Gravedad", "Aridez/Agua", "Relieve", "Geología",
]
# Peso de cada categoría en el índice. Gravedad y presión terrestres no se pueden
# replicar en ningún sitio real, por eso no entran en el índice (peso 0).
PESOS = {
    "Temperatura": 0.5, "Amplitud térmica": 0.5, "Presión": 0.0, "Radiación": 1.0,
    "Gravedad": 0.0, "Aridez/Agua": 1.5, "Relieve": 1.0, "Geología": 2.0,
}
CATS_INDICE = [c for c in CATEGORIAS if PESOS[c] > 0]

# Valores del destino que existen en la Tierra. Si el destino queda fuera de este rango
# (p. ej. 295 °C de amplitud en la Luna), se compara contra el valor terrestre más cercano.
ALCANCE_TERRESTRE = {
    "temp": (-55, 45),        # media anual, de la meseta antártica a desiertos cálidos
    "rango_t": (0, 30),       # amplitud diaria media anual
    "dosis": (0.0007, 0.04),  # mSv/día, del nivel del mar a ~8800 m
}

# 4. APIS

@st.cache_data(show_spinner=False)
def buscar_lugares(nombre):
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": nombre, "count": 5, "language": "es", "format": "json"}, timeout=8,
        ).json()
        return [
            dict(etiqueta=f"{x['name']}, {x.get('admin1', '')} ({x.get('country', '')})",
                 nombre=x["name"], lat=x["latitude"], lon=x["longitude"])
            for x in r.get("results", [])
        ]
    except Exception: return []

@st.cache_data(show_spinner=False)
def obtener_clima(lat, lon):
    try:
        r = requests.get(
            "https://power.larc.nasa.gov/api/temporal/climatology/point",
            params={"parameters": "T2M,T2M_RANGE,PRECTOTCORR", "community": "RE",
                    "longitude": lon, "latitude": lat, "format": "JSON"}, timeout=15,
        ).json()["properties"]["parameter"]
        return tuple(None if r[k]["ANN"] == -999 else r[k]["ANN"] for k in ["T2M", "T2M_RANGE", "PRECTOTCORR"])
    except Exception: return None, None, None

@st.cache_data(show_spinner=False)
def obtener_elevacion(lat, lon):
    try:
        r = requests.get(f"https://api.opentopodata.org/v1/srtm90m?locations={lat},{lon}", timeout=8).json()
        if r["results"][0]["elevation"] is not None: return r["results"][0]["elevation"]
    except Exception: pass
    try:
        r = requests.get("https://api.open-meteo.com/v1/elevation", params={"latitude": lat, "longitude": lon}, timeout=8).json()
        return r["elevation"][0]
    except Exception: return None

@st.cache_data(show_spinner=False)
def obtener_relieve(lat, lon):
    try:
        paso = 0.045
        pts = [f"{lat + i * paso},{lon + j * paso}" for i in (-1, 0, 1) for j in (-1, 0, 1)]
        r = requests.get("https://api.opentopodata.org/v1/srtm90m", params={"locations": "|".join(pts)}, timeout=10).json()
        alts = [x["elevation"] for x in r["results"] if x["elevation"] is not None]
        if len(alts) >= 5: return max(alts) - min(alts)
    except Exception: pass
    return None

@st.cache_data(show_spinner=False)
def obtener_uv(lat, lon):
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "daily": "uv_index_clear_sky_max", "timezone": "auto", "forecast_days": 7}, timeout=8,
        ).json()
        return max(r["daily"]["uv_index_clear_sky_max"])
    except Exception: return None

@st.cache_data(show_spinner=False)
def buscar_agua(lat, lon):
    try:
        q = f'[out:json][timeout:10];(way["natural"="water"](around:10000,{lat},{lon});way["natural"="coastline"](around:10000,{lat},{lon}););out count;'
        r = requests.post("https://overpass-api.de/api/interpreter", data={"data": q}, timeout=12).json()
        return int(r["elements"][0]["tags"]["total"]) > 0
    except Exception: return None

def construir_sitio(lugar, geologia):
    lat, lon = lugar["lat"], lugar["lon"]
    temp, rango_t, precip = obtener_clima(lat, lon)
    elev = obtener_elevacion(lat, lon)
    presion = dosis = None
    if elev is not None:
        h = max(elev, 0)
        presion = 101.325 * (1 - 2.25577e-5 * h) ** 5.25588
        dosis = 0.0007 * 2 ** (h / 1500)
    return dict(
        nombre=lugar["nombre"], lat=lat, lon=lon, temp=temp, rango_t=rango_t, precip=precip,
        elev=elev, presion=presion, dosis=dosis, uv=obtener_uv(lat, lon),
        agua=buscar_agua(lat, lon), relieve=obtener_relieve(lat, lon), geologia=geologia,
    )


@st.cache_data(show_spinner=False)
def referencia_en_vivo(nombre, lat, lon, geologia):
    return construir_sitio(dict(nombre=nombre, lat=lat, lon=lon), geologia)


def cargar_referencias():
    out = {}
    for n, r in REFERENCIAS.items():
        r2 = dict(r)
        if r.get("en_vivo"):
            vivo = referencia_en_vivo(n, r["lat"], r["lon"], r["geologia"])
            for k in ("temp", "rango_t", "precip", "elev", "presion", "dosis", "uv", "agua", "relieve"):
                if vivo.get(k) is not None:
                    r2[k] = vivo[k]
        out[n] = r2
    return out

# 5. MOTOR DE PUNTAJES

def lineal(a, b, tol):
    if a is None or b is None: return None
    return max(0.0, 100 * (1 - abs(a - b) / tol))

def logaritmico(a, b, decadas, piso):
    if a is None or b is None: return None
    return max(0.0, 100 * (1 - abs(math.log10(max(a, piso)) - math.log10(max(b, piso))) / decadas))

def objetivo_terrestre(valor, clave):
    lo, hi = ALCANCE_TERRESTRE[clave]
    return min(max(valor, lo), hi)

def puntuar(s, destino):
    t = DESTINOS[destino]
    sc = {
        "Temperatura": lineal(s.get("temp"), objetivo_terrestre(t["temp"], "temp"), 90),
        "Amplitud térmica": lineal(s.get("rango_t"), objetivo_terrestre(t["rango_t"], "rango_t"), 40),
        "Presión": logaritmico(s.get("presion"), t["presion"], 2.5, 1e-6),
        "Gravedad": lineal(s.get("gravedad", 9.81), t["gravedad"], 9.81),
        "Geología": GEO_MATRIZ.get(s.get("geologia"), {}).get(destino)
    }
    
    sc["Radiación"] = logaritmico(s.get("dosis"), objetivo_terrestre(t["dosis"], "dosis"), 3, 1e-4)

    if s.get("precip") is not None:
        aridez = max(0.0, 100 - s["precip"] * 60)
        sc["Aridez/Agua"] = aridez * 0.75 if s.get("agua") else aridez
    else:
        sc["Aridez/Agua"] = None

    r = s.get("relieve")
    if r is None:
        sc["Relieve"] = None
    else:
        lo, hi = t["relieve_ideal"]
        if r < lo: sc["Relieve"] = 100 * r / lo
        elif r > hi: sc["Relieve"] = max(0.0, 100 * (1 - (r - hi) / hi))
        else: sc["Relieve"] = 100.0
    return sc

def puntaje_global(sc):
    num = sum(PESOS[c] * v for c, v in sc.items() if v is not None)
    den = sum(PESOS[c] for c, v in sc.items() if v is not None)
    return num / den if den else 0.0

def nivel(g):
    if g >= 60: return "Análogo ALTO", "#22c55e"
    if g >= 40: return "Análogo MODERADO", "#f1c40f"
    if g >= 20: return "Análogo BAJO", "#e67e22"
    return "Análogo MUY BAJO", "#C8102E"

def generar_veredicto(sitio, destino, sc, glob, ranking):
    etiqueta, color = nivel(glob)
    fuertes = sorted([(c, v) for c, v in sc.items() if v is not None and PESOS[c] > 0 and v >= 60], key=lambda x: -x[1])
    debiles = sorted([(c, v) for c, v in sc.items() if v is not None and PESOS[c] > 0 and v <= 30], key=lambda x: x[1])
    sin_dato = [c for c, v in sc.items() if v is None]

    txt = f"<h3 style='color:{color}'>{etiqueta}: {glob:.0f}%</h3>"
    txt += f"<p><strong>{sitio['nombre']}</strong> frente a <strong>{destino}</strong>.</p>"
    if fuertes: txt += "<p><strong>Coincide en:</strong> " + ", ".join(f"{c} ({v:.0f})" for c, v in fuertes[:3]) + "</p>"
    if debiles: txt += "<p><strong>No coincide en:</strong> " + ", ".join(f"{c} ({v:.0f})" for c, v in debiles[:4]) + "</p>"

    otros = [(n, v) for n, v in ranking if n != sitio["nombre"]]
    supera = [n for n, v in otros if v < glob]
    if supera: txt += "<p><strong>Supera a:</strong> " + ", ".join(supera) + "</p>"
    else: txt += "<p>No supera a ninguno de los análogos de la base de referencia.</p>"
    
    mejor = max(otros, key=lambda x: x[1]) if otros else None
    if mejor: txt += f"<p>Mejor análogo de referencia: <strong>{mejor[0]}</strong> ({mejor[1]:.0f}%).</p>"

    txt += ("<hr style='border-color:#333'><p><strong>Límites inevitables:</strong> la gravedad "
            "terrestre y la presión atmosférica no pueden replicarse en sitios reales, por eso no entran en el índice.</p>")
    if sin_dato: txt += f"<p style='color:#aaa'>Sin datos para: {', '.join(sin_dato)}.</p>"
    return f"<div class='veredicto-box'>{txt}</div>"

# 6. INTERFAZ PRINCIPAL

REFS = cargar_referencias()
destino = st.sidebar.radio("Destino espacial", list(DESTINOS.keys()))
st.sidebar.subheader("Buscar un lugar")
consulta = st.sidebar.text_input("Ciudad, desierto, volcán...", "Atacama")
candidatos = buscar_lugares(consulta) if consulta.strip() else []

lugar_sel = None
if consulta.strip() and not candidatos:
    st.sidebar.warning("No se encontró ese lugar.")
elif candidatos:
    idx = st.sidebar.selectbox("Resultados", range(len(candidatos)), format_func=lambda i: candidatos[i]["etiqueta"])
    lugar_sel = candidatos[idx]

geologia = st.sidebar.selectbox("Terreno predominante", GEOLOGIAS, index=1)
comparar_con = st.sidebar.multiselect("Superponer en el radar", list(REFERENCIAS.keys()), default=["Desierto de Arizona"])

if st.sidebar.button("Analizar Compatibilidad", type="primary", disabled=lugar_sel is None):
    with st.spinner("Consultando APIs de la NASA, OpenTopoData y OpenStreetMap..."):
        st.session_state["sitio"] = construir_sitio(lugar_sel, geologia)

# 7. PESTAÑAS DE RESULTADOS

tab_res, tab_db, tab_met = st.tabs(["Resultado", "Base de referencia", "Metodología"])

with tab_res:
    sitio = st.session_state.get("sitio")
    if not sitio:
        st.markdown("""
        <div style="background: rgba(30, 33, 41, 0.6); padding: 40px; border-radius: 15px; text-align: center; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 8px 32px rgba(0,0,0,0.3); margin-top: 20px;">
            <h2 style="color: #ffffff; margin-bottom: 10px;">Inicia tu análisis</h2>
            <p style="font-size: 1.1em; color: #ddd;">Selecciona un destino (Luna o Marte) y busca cualquier ciudad, desierto o volcán en el panel izquierdo. Luego presiona <strong>Analizar Compatibilidad</strong>.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        sc_sitio = puntuar(sitio, destino)
        glob = puntaje_global(sc_sitio)

        ranking = [(sitio["nombre"], glob)]
        sc_refs = {}
        for n, r in REFS.items():
            sc_refs[n] = puntuar(r, destino)
            ranking.append((n, puntaje_global(sc_refs[n])))
        ranking.sort(key=lambda x: -x[1])

        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader(f"{sitio['nombre']} vs. {destino}")
            valores = [sc_sitio[c] if sc_sitio[c] is not None else 0 for c in CATS_INDICE]
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=[100] * len(CATS_INDICE) + [100], theta=CATS_INDICE + [CATS_INDICE[0]], fill="toself",
                name=f"Objetivo: {destino}", line_color="#C8102E", fillcolor="rgba(200,16,46,0.12)"))
            
            fig.add_trace(go.Scatterpolar(
                r=valores + [valores[0]], theta=CATS_INDICE + [CATS_INDICE[0]], fill="toself",
                name=sitio["nombre"], line_color="#4da6ff", fillcolor="rgba(77,166,255,0.25)"))
            
            paleta = ["#ffffff", "#f1c40f", "#9aa5b1"]
            for i, n in enumerate(comparar_con):
                v = [sc_refs[n][c] or 0 for c in CATS_INDICE]
                fig.add_trace(go.Scatterpolar(
                    r=v + [v[0]], theta=CATS_INDICE + [CATS_INDICE[0]], name=n,
                    line=dict(color=paleta[i % 3], dash="dot")))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100], color="#fff", gridcolor="#333"), bgcolor="rgba(30,33,41,0.5)"),
                paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Helvetica, Arial, sans-serif", color="#fff"), 
                margin=dict(l=60, r=60, t=30, b=30))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Veredicto")
            st.markdown(generar_veredicto(sitio, destino, sc_sitio, glob, ranking), unsafe_allow_html=True)

        st.subheader("Ranking de análogos")
        nombres = [n for n, _ in ranking]
        vals = [v for _, v in ranking]
        colores = ["#4da6ff" if n == sitio["nombre"] else "#666" for n in nombres]
        fig2 = go.Figure(go.Bar(x=vals[::-1], y=nombres[::-1], orientation="h",
                                marker_color=colores[::-1], text=[f"{v:.0f}%" for v in vals[::-1]], textposition="outside"))
        fig2.update_layout(
            xaxis=dict(range=[0, 110], gridcolor="#333"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
            font=dict(family="Helvetica, Arial, sans-serif", color="#fff"), height=280, margin=dict(l=20, r=20, t=10, b=20))
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Datos medidos")
        t = DESTINOS[destino]
        filas = [
            ("Temperatura media (°C)", "temp", "{:.1f}"), ("Amplitud térmica diaria (°C)", "rango_t", "{:.1f}"),
            ("Elevación (m)", "elev", "{:.0f}"), ("Presión (kPa)", "presion", "{:.3g}"),
            ("Dosis de radiación (mSv/día)", "dosis", "{:.3g}"), ("Índice UV máx.", "uv", "{:.1f}"),
            ("Precipitación (mm/día)", "precip", "{:.2f}"), ("Relieve en ~10 km (m)", "relieve", "{:.0f}"),
        ]

        def fmt(d, k, f):
            v = d.get(k)
            return "s/d" if v is None else f.format(v)

        tabla = pd.DataFrame({
            "Variable": [f[0] for f in filas] + ["Agua a 10 km", "Terreno"],
            destino: [fmt(t, f[1], f[2]) if f[1] in t else "—" for f in filas] + ["Sí (polos/subsuelo)", "—"],
            sitio["nombre"]: [fmt(sitio, f[1], f[2]) for f in filas] + [{True: "Sí", False: "No", None: "s/d"}[sitio.get("agua")], sitio["geologia"]],
        })
        for n, r in REFS.items():
            tabla[n] = [fmt(r, f[1], f[2]) for f in filas] + [{True: "Sí", False: "No", None: "s/d"}[r.get("agua")], r["geologia"]]
        
        st.dataframe(tabla, use_container_width=True, hide_index=True)
        st.download_button("Descargar comparación (CSV)", tabla.to_csv(index=False).encode("utf-8"),
                           file_name=f"analogo_{sitio['nombre']}_{destino}.csv", mime="text/csv")

        st.subheader("Ubicaciones")
        mapa = pd.DataFrame([{"lat": sitio["lat"], "lon": sitio["lon"]}] + [{"lat": r["lat"], "lon": r["lon"]} for r in REFS.values()])
        st.map(mapa)

with tab_db:
    st.subheader("Base de datos de referencia")
    st.markdown("**Destinos**")
    st.dataframe(pd.DataFrame(DESTINOS).T.drop(columns=["relieve_ideal"]), use_container_width=True)
    st.markdown("**Análogos de referencia**")
    st.dataframe(pd.DataFrame(REFS).T, use_container_width=True)

with tab_met:
    st.markdown(
        """
**Qué mide el índice (0-100%)**
Mide la similitud *ambiental* entre un lugar de la Tierra y la Luna o Marte. Cada variable recibe un puntaje de 0 a 100
y el índice final es el promedio ponderado de las variables que tienen dato.

**Comparación con lo que existe en la Tierra:** si el valor del destino no existe en ningún lugar terrestre
(por ejemplo, 295 °C de amplitud térmica en la Luna), el lugar se compara con el valor terrestre más cercano.
Así el índice responde a *"¿qué tan bien aproxima este sitio al destino, dentro de lo que la Tierra permite?"*.

| Variable | Fuente | Regla | Peso |
|---|---|---|---|
| Geología | Selección del usuario | Matriz de similitud | 2.0 |
| Aridez/Agua | NASA POWER + OpenStreetMap | `100 - 60 x precipitación (mm/día)`; x0.75 si hay agua a 10 km | 1.5 |
| Radiación | Estimada por altitud | Logarítmica, 3 décadas | 1.0 |
| Relieve | OpenTopoData SRTM | Banda ideal 150-1500 m | 1.0 |
| Temperatura | NASA POWER | Lineal, tolerancia 90 °C | 0.5 |
| Amplitud térmica | NASA POWER | Lineal, tolerancia 40 °C | 0.5 |
| Presión | Calculada desde la elevación | Logarítmica (solo informativa) | 0 |
| Gravedad | Constante terrestre | Lineal (solo informativa) | 0 |

La presión y la gravedad terrestres no pueden replicarse en ningún sitio real, por eso se muestran en los datos pero no entran en el índice.

**Niveles:** ALTO ≥ 60 · MODERADO ≥ 40 · BAJO ≥ 20 · MUY BAJO < 20.

**Limitaciones:** los valores de Luna, Marte y de los análogos de referencia son aproximados. El índice no mide mineralogía
ni química (salvo a través del tipo de terreno elegido). La radiación se estima solo por altitud. Los pesos y umbrales son
decisiones de diseño, calibradas con análogos conocidos, y no una medida científica absoluta.
        """
    )
