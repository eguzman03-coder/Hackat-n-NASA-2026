"""
Compatibilidad Espacial - Terra-Analog Explorer
NASA Space Apps Challenge 2026
Reto: "Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars"

Índice de similitud ambiental (0-100%) entre un lugar de la Tierra y la Luna o Marte, más un escaneo de lugares candidatos.

Ejecutar:  streamlit run aplicacion_nasa.py
"""
import base64
import math
import os
import re
import time
from html import escape

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Estilo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_file(nombre):
    """Busca el archivo en cualquier carpeta del proyecto, sin importar mayúsculas."""
    for root, _, files in os.walk(BASE_DIR):
        for f in files:
            if f.lower() == nombre.lower():
                return os.path.join(root, f)
    return None

def get_base64(bin_file):
    try:
        with open(bin_file, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

img_fondo = get_base64("fondo.png")
background_css = f'url("data:image/png;base64,{img_fondo}")' if img_fondo else "none"
img_logo = get_base64("logo_nasa.png")

st.set_page_config(page_title="Compatibilidad Espacial | NASA", page_icon="logo_nasa.png", layout="wide")

st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
    }}
    [data-testid="stAppViewContainer"] {{
        background-image: linear-gradient(rgba(5, 5, 5, 0.75), rgba(5, 5, 5, 0.85)), {background_css};
        background-size: cover;
        background-position: center top;
        background-attachment: fixed;
    }}
    [data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
    [data-testid="stSidebar"] {{
        background-color: rgba(14, 17, 23, 0.85) !important;
        backdrop-filter: blur(10px);
    }}
    .veredicto-box {{
        background-color: rgba(30, 33, 41, 0.9);
        padding: 25px;
        border-radius: 15px;
        border-left: 8px solid #C8102E;
        margin-top: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
    }}
    .veredicto-box h3 {{ margin-top: 0; color: #C8102E; font-weight: bold; }}
    .stButton>button {{
        background-color: #C8102E;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        transition: 0.3s;
    }}
    .stButton>button:hover {{ background-color: #E0213F; color: white; }}
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

#Título

if img_logo:
    logo_final = f"data:image/png;base64,{img_logo}"
else:
    logo_final = "https://upload.wikimedia.org/wikipedia/commons/e/e5/NASA_logo.svg"

st.markdown(
    f"""
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 15px; margin-top: 20px; margin-bottom: 20px;">
<img src="{logo_final}" style="height: 130px; width: auto;">
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

# Base de datos

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

T_BAS = "Basalto volcánico / lava"
T_DES = "Desierto árido / roca expuesta"
T_MON = "Montaña / roca alpina"
T_GLA = "Glaciar / hielo / permafrost"
T_SED = "Suelo sedimentario / vegetación"
T_COS = "Costa / humedal"
T_ACI = "Ácido / rico en hierro (sulfatos, hematita)"
T_CRA = "Cráter de impacto / roca fracturada"

GEOLOGIAS = [T_BAS, T_DES, T_MON, T_GLA, T_SED, T_COS, T_ACI, T_CRA]

GEO_MATRIZ = {
    T_BAS: {"Luna": 100, "Marte": 100},
    T_DES: {"Luna": 55,  "Marte": 85},
    T_MON: {"Luna": 70,  "Marte": 70},
    T_GLA: {"Luna": 40,  "Marte": 50},
    T_SED: {"Luna": 15,  "Marte": 30},
    T_COS: {"Luna": 5,   "Marte": 10},
    T_ACI: {"Luna": 15,  "Marte": 95},
    T_CRA: {"Luna": 90,  "Marte": 80},
}

REFERENCIAS = {
    "Desierto de Arizona": dict(  # Cinder Lake, Flagstaff
        lat=35.32, lon=-111.52, en_vivo=True,
        temp=8.2, rango_t=16.6,   # NOAA 1991-2020, Flagstaff
        elev=2100, presion=78.5, dosis=0.0019, precip=1.4,
        uv=None, agua=None, relieve=None,
        geologia=T_BAS,
        nota="Clima NOAA; relieve, UV y agua en vivo.",
    ),
    "LUNA (ESA-DLR)": dict(
        lat=50.85, lon=7.14,
        temp=20, rango_t=2, elev=60, presion=100.6, dosis=0.0007, uv=0, precip=0.0,
        agua=False, relieve=0, gravedad=1.62,
        geologia=T_BAS,
        nota="Publicados: simulante y gravedad. Supuestos: temperatura, presión, radiación.",
    ),
    "Habitat Marte": dict(  # supuesto: MDRS, Utah
        lat=38.41, lon=-110.79, en_vivo=True,
        temp=12, rango_t=20, elev=1400, presion=85.6, dosis=0.0013, precip=0.38,
        uv=None, agua=None, relieve=None,
        geologia=T_DES,
        nota="MDRS, Hanksville, Utah.",
    ),
}

AMBOS = ("Luna", "Marte")
SOLO_MARTE = ("Marte",)

# Lugares del escaneo. Coordenadas aproximadas.
# Tenemos 2 tipos de lugares:
#"analogo": lugar conocido como análogo (para los destinos indicados). Los cuales ya están validados
#"control": lugar que NO es análogo, son ciudades donde sus condiciones les impiden ser análogos.
# sirve para comprobar que el índice discrimina. La clasificación debe respaldarse con fuentes.
CANDIDATOS = [
    dict(nombre="Cráter Haughton (Isla Devon), Canadá", lat=75.37,  lon=-89.68,  geologia=T_CRA, tipo="analogo", destinos=SOLO_MARTE),
    dict(nombre="Meteor Crater, Arizona",               lat=35.03,  lon=-111.02, geologia=T_CRA, tipo="analogo", destinos=AMBOS),
    dict(nombre="Valle de la Muerte, EE. UU.",          lat=36.46,  lon=-116.87, geologia=T_DES, tipo="analogo", destinos=AMBOS),
    dict(nombre="Craters of the Moon, Idaho",           lat=43.42,  lon=-113.52, geologia=T_BAS, tipo="analogo", destinos=AMBOS),
    dict(nombre="Timanfaya (Lanzarote), España",        lat=29.00,  lon=-13.75,  geologia=T_BAS, tipo="analogo", destinos=AMBOS),
    dict(nombre="Krafla, Islandia",                     lat=65.71,  lon=-16.78,  geologia=T_BAS, tipo="analogo", destinos=AMBOS),
    dict(nombre="Dallol (Danakil), Etiopía",            lat=14.24,  lon=40.30,   geologia=T_ACI, tipo="analogo", destinos=SOLO_MARTE),
    dict(nombre="Río Tinto (Huelva), España",           lat=37.70,  lon=-6.57,   geologia=T_ACI, tipo="analogo", destinos=SOLO_MARTE),
    dict(nombre="Salar de Uyuni, Bolivia",              lat=-20.13, lon=-67.49,  geologia=T_DES, tipo="analogo", destinos=SOLO_MARTE),
    dict(nombre="Wadi Rum, Jordania",                   lat=29.57,  lon=35.42,   geologia=T_DES, tipo="analogo", destinos=SOLO_MARTE),
    dict(nombre="Londres, Reino Unido",                 lat=51.51,  lon=-0.13,   geologia=T_SED, tipo="control", destinos=()),
    dict(nombre="Manaos (Amazonas), Brasil",            lat=-3.12,  lon=-60.02,  geologia=T_SED, tipo="control", destinos=()),
    dict(nombre="Valdivia, Chile",                      lat=-39.81, lon=-73.25,  geologia=T_SED, tipo="control", destinos=()),
    dict(nombre="Punta Arenas, Chile",                  lat=-53.16, lon=-70.91,  geologia=T_SED, tipo="control", destinos=()),
]


CATEGORIAS = [
    "Temperatura", "Amplitud térmica", "Presión", "Radiación",
    "Gravedad", "Aridez/Agua", "Relieve", "Geología",
]
# Gravedad y presión terrestres no se pueden replicar en ningún sitio real: se muestran, pero no pesan en el índice.
PESOS = {
    "Temperatura": 0.5, "Amplitud térmica": 0.5, "Presión": 0.0, "Radiación": 1.0,
    "Gravedad": 0.0, "Aridez/Agua": 1.5, "Relieve": 1.0, "Geología": 2.0,
}
CATS_INDICE = [c for c in CATEGORIAS if PESOS[c] > 0]

# Si el valor del destino no existe en la Tierra, se compara con el valor terrestre más cercano.
ALCANCE_TERRESTRE = {
    "temp": (-55, 45),
    "rango_t": (0, 30),
    "dosis": (0.0007, 0.04),
}

COLORES_NIVEL = {"ALTO": "#22c55e", "MODERADO": "#f1c40f", "BAJO": "#e67e22", "MUY BAJO": "#ff5468"}

# APIs satelitales para la información

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
    except Exception:
        return []

@st.cache_data(show_spinner=False)
def obtener_clima(lat, lon):
    try:
        r = requests.get(
            "https://power.larc.nasa.gov/api/temporal/climatology/point",
            params={"parameters": "T2M,T2M_RANGE,PRECTOTCORR", "community": "RE",
                    "longitude": lon, "latitude": lat, "format": "JSON"}, timeout=20,
        ).json()["properties"]["parameter"]
        return tuple(None if r[k]["ANN"] == -999 else r[k]["ANN"] for k in ["T2M", "T2M_RANGE", "PRECTOTCORR"])
    except Exception:
        return None, None, None

@st.cache_data(show_spinner=False)
def obtener_elevacion(lat, lon):
    # Primero Open-Meteo (sin límite estricto) y, si falla, OpenTopoData (SRTM).
    try:
        r = requests.get("https://api.open-meteo.com/v1/elevation",
                         params={"latitude": lat, "longitude": lon}, timeout=8).json()
        if r.get("elevation") and r["elevation"][0] is not None:
            return r["elevation"][0]
    except Exception:
        pass
    try:
        r = requests.get(f"https://api.opentopodata.org/v1/srtm90m?locations={lat},{lon}", timeout=8).json()
        return r["results"][0]["elevation"]
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def obtener_relieve(lat, lon):
    if abs(lat) > 59:      # SRTM no cubre latitudes altas
        return None
    try:
        time.sleep(1.1)    # OpenTopoData público: ~1 consulta por segundo
        paso = 0.045
        pts = [f"{lat + i * paso},{lon + j * paso}" for i in (-1, 0, 1) for j in (-1, 0, 1)]
        r = requests.get("https://api.opentopodata.org/v1/srtm90m",
                         params={"locations": "|".join(pts)}, timeout=12).json()
        alts = [x["elevation"] for x in r["results"] if x["elevation"] is not None]
        if len(alts) >= 5:
            return max(alts) - min(alts)
    except Exception:
        pass
    return None

@st.cache_data(show_spinner=False)
def obtener_uv(lat, lon):
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "daily": "uv_index_clear_sky_max",
                    "timezone": "auto", "forecast_days": 7}, timeout=8,
        ).json()
        vals = [v for v in r["daily"]["uv_index_clear_sky_max"] if v is not None]
        return max(vals) if vals else None
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def buscar_agua(lat, lon):
    try:
        q = (f'[out:json][timeout:10];(way["natural"="water"](around:10000,{lat},{lon});'
             f'way["natural"="coastline"](around:10000,{lat},{lon}););out count;')
        r = requests.post("https://overpass-api.de/api/interpreter", data={"data": q}, timeout=14).json()
        return int(r["elements"][0]["tags"]["total"]) > 0
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def buscar_datasets_cmr(lat, lon):
    """Busca datasets de la NASA que cubren un punto."""
    try:
        url = "https://cmr.earthdata.nasa.gov/search/collections.json"
        params = {"point": f"{lon},{lat}", "page_size": 5, "sort_key": "-score"}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            items = r.json().get("feed", {}).get("entry", [])
            return [i.get("title", "Dataset sin título") for i in items]
    except Exception:
        pass
    return []

ANIO_FIN = 2025            # último año completo
ANIO_INI = ANIO_FIN - 19   # 20 años: 2006-2025

@st.cache_data(show_spinner=False)
def obtener_serie_anual(lat, lon, ini=ANIO_INI, fin=ANIO_FIN):
    """Serie anual de NASA POWER (datos mensuales promediados por año)."""
    try:
        r = requests.get(
            "https://power.larc.nasa.gov/api/temporal/monthly/point",
            params={"parameters": "T2M,T2M_RANGE,PRECTOTCORR", "community": "RE",
                    "longitude": lon, "latitude": lat, "start": ini, "end": fin, "format": "JSON"},
            timeout=30,
        ).json()["properties"]["parameter"]
    except Exception:
        return None
    filas = []
    for anio in range(ini, fin + 1):
        fila = {"Año": anio}
        for var in ("T2M", "T2M_RANGE", "PRECTOTCORR"):
            meses = [r[var].get(f"{anio}{m:02d}") for m in range(1, 13)]
            meses = [v for v in meses if v is not None and v != -999]
            fila[var] = sum(meses) / len(meses) if len(meses) >= 6 else None
        filas.append(fila)
    df = pd.DataFrame(filas)
    return df if df[["T2M", "T2M_RANGE", "PRECTOTCORR"]].notna().any().any() else None

def construir_sitio(lugar, geologia):
    lat, lon = lugar["lat"], lugar["lon"]
    temp, rango_t, precip = obtener_clima(lat, lon)
    elev = obtener_elevacion(lat, lon)
    presion = dosis = None
    if elev is not None:
        h = max(elev, 0)
        presion = 101.325 * (1 - 2.25577e-5 * h) ** 5.25588
        dosis = 0.0007 * 2 ** (h / 1500)
    sitio = dict(
        nombre=lugar["nombre"], lat=lat, lon=lon, temp=temp, rango_t=rango_t, precip=precip,
        elev=elev, presion=presion, dosis=dosis, uv=obtener_uv(lat, lon),
        agua=buscar_agua(lat, lon), relieve=obtener_relieve(lat, lon), geologia=geologia,
    )
    # Qué fuentes no respondieron (se muestra en el veredicto y en el informe)
    relieve_txt = "relieve (SRTM no cubre latitudes sobre 60°)" if abs(lat) > 59 else "relieve (OpenTopoData)"
    sitio["fallos"] = [txt for txt, ok in [
        ("clima (NASA POWER)", temp is not None or precip is not None),
        ("elevación", elev is not None),
        (relieve_txt, sitio["relieve"] is not None),
        ("UV (Open-Meteo)", sitio["uv"] is not None),
        ("agua (OpenStreetMap)", sitio["agua"] is not None),
    ] if not ok]
    return sitio

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

# Puntajes

def lineal(a, b, tol):
    if a is None or b is None:
        return None
    return max(0.0, 100 * (1 - abs(a - b) / tol))

def logaritmico(a, b, decadas, piso):
    if a is None or b is None:
        return None
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
        "Geología": GEO_MATRIZ.get(s.get("geologia"), {}).get(destino),
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
        if r < lo:
            sc["Relieve"] = 100 * r / lo
        elif r > hi:
            sc["Relieve"] = max(0.0, 100 * (1 - (r - hi) / hi))
        else:
            sc["Relieve"] = 100.0
    return sc

def puntaje_global(sc):
    num = sum(PESOS[c] * v for c, v in sc.items() if v is not None)
    den = sum(PESOS[c] for c, v in sc.items() if v is not None)
    return num / den if den else 0.0

def nivel(g):
    if g >= 60:
        return "Análogo ALTO", COLORES_NIVEL["ALTO"]
    if g >= 40:
        return "Análogo MODERADO", COLORES_NIVEL["MODERADO"]
    if g >= 20:
        return "Análogo BAJO", COLORES_NIVEL["BAJO"]
    return "Análogo MUY BAJO", COLORES_NIVEL["MUY BAJO"]

def nombre_nivel(g):
    return nivel(g)[0].replace("Análogo ", "")

def similitud_perfiles(sc_a, sc_b):
    """100 = mismo patrón de puntajes en las variables del índice (usa los mismos pesos).
    Mide qué tan parecido es el perfil, no qué tan alto es el índice."""
    num = den = 0.0
    for c in CATS_INDICE:
        a, b = sc_a.get(c), sc_b.get(c)
        if a is None or b is None:
            continue
        num += PESOS[c] * abs(a - b)
        den += PESOS[c]
    return None if den == 0 else 100 - num / den

def etiqueta_tipo(s, destino):
    if s["tipo"] == "control":
        return "Control"
    if destino in s["destinos"]:
        return "Análogo conocido"
    return "Análogo de " + " y ".join(s["destinos"])

def calcular_escaneo(sitios, destino):
    filas = []
    for s in sitios:
        sc = puntuar(s, destino)
        filas.append(dict(s=s, sc=sc, g=puntaje_global(sc),
                          datos=sum(1 for c in CATS_INDICE if sc[c] is not None)))
    filas.sort(key=lambda f: -f["g"])
    an = [f for f in filas if f["s"]["tipo"] == "analogo" and destino in f["s"]["destinos"]]
    co = [f for f in filas if f["s"]["tipo"] == "control"]
    prom = lambda lista: sum(f["g"] for f in lista) / len(lista) if lista else None
    return dict(
        filas=filas, prom_analogos=prom(an), prom_controles=prom(co),
        n_analogos=len(an), altos_analogos=sum(1 for f in an if f["g"] >= 60),
        n_controles=len(co), bajos_controles=sum(1 for f in co if f["g"] < 40),
    )

def generar_veredicto(sitio, destino, sc, glob, ranking):
    etiqueta, color = nivel(glob)
    fuertes = sorted([(c, v) for c, v in sc.items() if v is not None and PESOS[c] > 0 and v >= 60], key=lambda x: -x[1])
    debiles = sorted([(c, v) for c, v in sc.items() if v is not None and PESOS[c] > 0 and v <= 30], key=lambda x: x[1])
    sin_dato = [c for c, v in sc.items() if v is None]

    txt = f"<h3 style='color:{color}'>{etiqueta}: {glob:.0f}%</h3>"
    txt += f"<p><strong>{escape(sitio['nombre'])}</strong> frente a <strong>{destino}</strong>.</p>"
    if fuertes:
        txt += "<p><strong>Coincide en:</strong> " + ", ".join(f"{c} ({v:.0f})" for c, v in fuertes[:3]) + "</p>"
    if debiles:
        txt += "<p><strong>No coincide en:</strong> " + ", ".join(f"{c} ({v:.0f})" for c, v in debiles[:4]) + "</p>"

    otros = [(n, v) for n, v in ranking if n != sitio["nombre"]]
    supera = [escape(n) for n, v in otros if v < glob]
    if supera:
        txt += "<p><strong>Supera a:</strong> " + ", ".join(supera) + "</p>"
    else:
        txt += "<p>No supera a ninguno de los análogos de la base de referencia.</p>"
    mejor = max(otros, key=lambda x: x[1]) if otros else None
    if mejor:
        txt += f"<p>Mejor análogo de referencia: <strong>{escape(mejor[0])}</strong> ({mejor[1]:.0f}%).</p>"

    txt += ("<hr style='border-color:#333'><p><strong>Límites inevitables:</strong> la gravedad "
            "terrestre y la presión atmosférica no pueden replicarse en sitios reales, por eso no entran en el índice.</p>")
    if sin_dato:
        txt += f"<p style='color:#aaa'>Sin datos para: {', '.join(sin_dato)}.</p>"
    if sitio.get("fallos"):
        txt += f"<p style='color:#aaa'>Fuentes que no respondieron: {', '.join(sitio['fallos'])}.</p>"
    return f"<div class='veredicto-box'>{txt}</div>"

def generar_informe(sitio, destino, sc, glob):
    etiqueta, _ = nivel(glob)
    fuertes = [c for c, v in sc.items() if v is not None and PESOS[c] > 0 and v >= 60]
    debiles = [c for c, v in sc.items() if v is not None and PESOS[c] > 0 and v <= 30]
    sin_dato = [c for c, v in sc.items() if v is None]

    t = ["Informa de compatibilidad espacial (generado automáticamente)", "=" * 64,
         f"Lugar evaluado:    {sitio['nombre']} ({sitio['lat']:.2f}, {sitio['lon']:.2f})",
         f"Destino:           {destino}",
         f"Terreno declarado: {sitio['geologia']}",
         f"Índice:            {glob:.0f}% ({etiqueta})", ""]
    if fuertes:
        t.append("Coincide en (puntaje >= 60):    " + ", ".join(fuertes))
    if debiles:
        t.append("No coincide en (puntaje <= 30): " + ", ".join(debiles))
    if sin_dato:
        t.append("Sin datos para:                 " + ", ".join(sin_dato))
    if sitio.get("fallos"):
        t.append("Fuentes sin respuesta:          " + ", ".join(sitio["fallos"]))
    t += ["", "LECTURA DEL RESULTADO"]
    if glob >= 60:
        t.append(f"La similitud ambiental con {destino} es alta según las variables del índice. "
                 "Es un candidato razonable para evaluarlo con datos de campo.")
    elif glob >= 40:
        t.append(f"La similitud ambiental con {destino} es moderada: el lugar coincide en algunas variables y no en otras. "
                 "Podría servir para pruebas que dependan solo de las variables en que coincide.")
    else:
        t.append(f"La similitud ambiental con {destino} es baja según las variables del índice. "
                 "No es un candidato prioritario con la información disponible.")
    t += ["", "LIMITACIONES",
          "- El índice mide similitud ambiental; no mide mineralogía ni química (salvo por el terreno elegido).",
          "- La gravedad y la presión terrestres no pueden replicarse y no entran en el índice.",
          "- La radiación se estima solo por altitud. Los valores de la Luna y de Marte son aproximados.",
          "- Pesos y umbrales son decisiones de diseño; este informe no es una validación científica independiente.",
          "", "Fuentes de datos: NASA POWER, SRTM (vía OpenTopoData), Open-Meteo, OpenStreetMap."]
    return "\n".join(t)

def archivo_seguro(texto):
    return re.sub(r"[^\w\-]+", "_", texto).strip("_") or "lugar"

def fmt(d, k, f):
    v = d.get(k)
    return "s/d" if v is None else f.format(v)

def ejecutar_escaneo():
    barra = st.progress(0.0)
    estado = st.empty()
    sitios = []
    for i, c in enumerate(CANDIDATOS):
        estado.caption(f"Escaneando {i + 1} de {len(CANDIDATOS)}: {c['nombre']}")
        s = construir_sitio(dict(nombre=c["nombre"], lat=c["lat"], lon=c["lon"]), c["geologia"])
        s["tipo"], s["destinos"] = c["tipo"], c["destinos"]
        sitios.append(s)
        barra.progress((i + 1) / len(CANDIDATOS))
    barra.empty()
    estado.empty()
    return sitios

# Panel izquierdo

REFS = cargar_referencias()
destino = st.sidebar.radio("Destino espacial", list(DESTINOS.keys()))
st.sidebar.subheader("Buscar un lugar")
consulta = st.sidebar.text_input("Ciudad, desierto, volcán...", "Río Tinto")
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

st.sidebar.markdown("---")
st.sidebar.caption("Evalúa 14 lugares de una vez (análogos conocidos y lugares de control). Tarda unos minutos la primera vez.")
if st.sidebar.button("Escanear candidatos"):
    st.session_state["escaneo"] = ejecutar_escaneo()
    st.sidebar.success("Escaneo listo. Mira la pestaña «Escanear candidatos».")

# Resultados

tab_res, tab_scan, tab_db, tab_met = st.tabs(["Resultado", "Escanear candidatos", "Base de referencia", "Metodología"])

# ---------------------------------------------------------------- Resultado
with tab_res:
    sitio = st.session_state.get("sitio")
    if not sitio:
        st.markdown(
            "<div style=\"background: rgba(30, 33, 41, 0.6); padding: 40px; border-radius: 15px; text-align: center; "
            "backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 8px 32px rgba(0,0,0,0.3); margin-top: 20px;\">"
            "<h2 style=\"color: #ffffff; margin-bottom: 10px;\">Inicia tu análisis</h2>"
            "<p style=\"font-size: 1.1em; color: #ddd;\">Selecciona un destino (Luna o Marte) y busca cualquier ciudad, desierto o volcán "
            "en el panel izquierdo. Luego presiona <strong>Analizar Compatibilidad</strong>.</p></div>",
            unsafe_allow_html=True,
        )
    else:
        sc_sitio = puntuar(sitio, destino)
        glob = puntaje_global(sc_sitio)

        ranking = [(sitio["nombre"], glob)]
        sc_refs = {}
        for n, r in REFS.items():
            sc_refs[n] = puntuar(r, destino)
            ranking.append((n, puntaje_global(sc_refs[n])))
        ranking.sort(key=lambda x: -x[1])

        if sitio["geologia"] == T_DES and (sitio.get("precip") or 0) >= 1.5:
            st.warning(f"Elegiste terreno desértico, pero la precipitación de este lugar es {sitio['precip']:.1f} mm/día, "
                       "algo poco propio de un desierto. Revisa el terreno elegido: es la variable que más pesa en el índice.")

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
                polar=dict(radialaxis=dict(visible=True, range=[0, 100], color="#fff", gridcolor="#333"),
                           bgcolor="rgba(30,33,41,0.5)"),
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
        fig2 = go.Figure(go.Bar(x=vals[::-1], y=nombres[::-1], orientation="h", marker_color=colores[::-1],
                                text=[f"{v:.0f}%" for v in vals[::-1]], textposition="outside"))
        fig2.update_layout(
            xaxis=dict(range=[0, 110], gridcolor="#333"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Helvetica, Arial, sans-serif", color="#fff"), height=280, margin=dict(l=20, r=20, t=10, b=20))
        st.plotly_chart(fig2, use_container_width=True)

        # Perfiles más parecidos: usa las mismas variables y pesos del índice
        # --- NUEVO: comparación de las últimas dos décadas ---
        st.subheader(f"Últimos 20 años ({ANIO_INI}–{ANIO_FIN}): {sitio['nombre']} frente a los análogos")
        VARS_SERIE = {
            "Temperatura media (°C)": ("T2M", "temp"),
            "Amplitud térmica diaria (°C)": ("T2M_RANGE", "rango_t"),
            "Precipitación (mm/día)": ("PRECTOTCORR", None),
        }
        cs1, cs2 = st.columns([3, 2])
        with cs1:
            var_sel = st.radio("Variable", list(VARS_SERIE), horizontal=True, key="var_serie")
        with cs2:
            como_anomalia = st.checkbox("Ver como diferencia respecto al promedio del periodo", key="anom_serie")
        col_api, clave_dest = VARS_SERIE[var_sel]

        series = {sitio["nombre"]: obtener_serie_anual(sitio["lat"], sitio["lon"])}
        for n in comparar_con:
            series[n] = obtener_serie_anual(REFS[n]["lat"], REFS[n]["lon"])
        series = {n: d for n, d in series.items() if d is not None and d[col_api].notna().sum() >= 5}

        if not series:
            st.info("NASA POWER no devolvió la serie histórica para estos puntos. Intenta de nuevo en un momento.")
        else:
            colores_serie = ["#4da6ff", "#ffffff", "#f1c40f", "#9aa5b1"]
            figs = go.Figure()
            tendencias = []
            for i, (n, d) in enumerate(series.items()):
                d = d.dropna(subset=[col_api])
                y = d[col_api] - d[col_api].mean() if como_anomalia else d[col_api]
                figs.add_trace(go.Scatter(
                    x=d["Año"], y=y, mode="lines+markers", name=n,
                    line=dict(color=colores_serie[i % 4], width=3 if i == 0 else 2,
                              dash="solid" if i == 0 else "dot")))
                pend = float(np.polyfit(d["Año"], d[col_api], 1)[0]) * 10
                tendencias.append((n, pend))
            figs.update_layout(
                xaxis=dict(title="Año", dtick=2, gridcolor="#333"),
                yaxis=dict(title=var_sel + (" (diferencia)" if como_anomalia else ""), gridcolor="#333", zeroline=como_anomalia),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Helvetica, Arial, sans-serif", color="#fff"),
                legend=dict(orientation="h", y=1.12), height=380, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(figs, use_container_width=True)

            unidad = var_sel.split("(")[1].rstrip(")")
            for col, (n, p) in zip(st.columns(len(tendencias)), tendencias):
                col.metric(f"Tendencia: {n}", f"{p:+.2f} {unidad}/década")

            if clave_dest and clave_dest in DESTINOS[destino]:
                st.caption(f"Referencia: {destino} ≈ {DESTINOS[destino][clave_dest]} {unidad.split('/')[0]} "
                           f"(valor típico, sin variación apreciable en 20 años; no se grafica para no aplastar la escala).")
            st.caption("Fuente: NASA POWER (promedio anual de datos mensuales, comunidad RE). Los años sin al menos 6 meses de datos se omiten.")

        st.subheader("Perfiles más parecidos")
        pool = {n: sc_refs[n] for n in REFS}
        con_escaneo = False
        for s in st.session_state.get("escaneo", []):
            if s["tipo"] == "analogo" and destino in s["destinos"] and s["nombre"] != sitio["nombre"]:
                pool[s["nombre"]] = puntuar(s, destino)
                con_escaneo = True
        afines = [(n, similitud_perfiles(sc_sitio, sc)) for n, sc in pool.items()]
        afines = sorted([(n, v) for n, v in afines if v is not None], key=lambda x: -x[1])[:3]
        st.caption("Compara el patrón de puntajes por variable (no solo el nivel del índice) con los análogos de la base de referencia"
                   + (" y con los análogos conocidos de tu escaneo." if con_escaneo
                      else ". Usa «Escanear candidatos» para sumar más análogos conocidos a esta comparación."))
        if afines:
            for col, (n, v) in zip(st.columns(len(afines)), afines):
                color = "#22c55e" if v >= 80 else ("#f1c40f" if v >= 60 else "#e67e22")
                with col:
                    st.markdown(
                        f"<div style='background: rgba(30, 33, 41, 0.8); padding: 15px; border-radius: 10px; "
                        f"border-top: 5px solid {color}; text-align: center;'>"
                        f"<h4 style='margin: 0; color: #fff;'>{escape(n)}</h4>"
                        f"<h2 style='margin: 10px 0; color: {color};'>{v:.0f}%</h2>"
                        f"<p style='font-size: 0.8em; color: #aaa;'>Parecido de perfil</p></div>",
                        unsafe_allow_html=True)
        else:
            st.info("No hay datos suficientes para comparar perfiles.")

        st.subheader("Datos medidos")
        t = DESTINOS[destino]
        filas = [
            ("Temperatura media (°C)", "temp", "{:.1f}"), ("Amplitud térmica diaria (°C)", "rango_t", "{:.1f}"),
            ("Elevación (m)", "elev", "{:.0f}"), ("Presión (kPa)", "presion", "{:.3g}"),
            ("Dosis de radiación (mSv/día)", "dosis", "{:.3g}"), ("Índice UV máx.", "uv", "{:.1f}"),
            ("Precipitación (mm/día)", "precip", "{:.2f}"), ("Relieve en ~10 km (m)", "relieve", "{:.0f}"),
        ]
        si_no = {True: "Sí", False: "No", None: "s/d"}
        tabla = pd.DataFrame({
            "Variable": [f[0] for f in filas] + ["Agua a 10 km", "Terreno"],
            destino: [fmt(t, f[1], f[2]) if f[1] in t else "—" for f in filas] + ["Sí (polos/subsuelo)", "—"],
            sitio["nombre"]: [fmt(sitio, f[1], f[2]) for f in filas] + [si_no[sitio.get("agua")], sitio["geologia"]],
        })
        for n, r in REFS.items():
            tabla[n] = [fmt(r, f[1], f[2]) for f in filas] + [si_no[r.get("agua")], r["geologia"]]
        st.dataframe(tabla, use_container_width=True, hide_index=True)
        
        # --- NUEVA SECCIÓN: DATOS SATELITALES DE LA NASA (CMR) ---
        st.subheader("Datos Satelitales de NASA disponibles para esta zona")
        st.markdown(f"Catálogo de misiones de observación de la Tierra de la NASA que han cubierto las coordenadas de **{sitio['nombre']}**:")
        
        with st.spinner("Consultando catálogo CMR de la NASA..."):
            datasets = buscar_datasets_cmr(sitio["lat"], sitio["lon"])
            
        if datasets:
            for ds in datasets:
                st.markdown(f"- {ds}")
            st.caption("Metadatos obtenidos vía API CMR de la NASA. Los datos crudos pueden descargarse desde search.earthdata.nasa.gov.")
        else:
            st.info("No se encontraron datasets directos para este punto (o la API no respondió).")

            
        st.subheader("Informe generado")
        texto_informe = generar_informe(sitio, destino, sc_sitio, glob)
        st.code(texto_informe, language="text")
        base_archivo = f"{archivo_seguro(sitio['nombre'])}_{destino}"
        c_a, c_b = st.columns(2)
        with c_a:
            st.download_button("Descargar informe (.txt)", texto_informe.encode("utf-8"),
                               file_name=f"informe_{base_archivo}.txt", mime="text/plain", type="primary")
        with c_b:
            st.download_button("Descargar tabla de datos (CSV)", tabla.to_csv(index=False).encode("utf-8"),
                               file_name=f"datos_{base_archivo}.csv", mime="text/csv")

        st.subheader("Ubicaciones")
        df_mapa = pd.DataFrame({
            "Lugar": [sitio["nombre"]] + list(REFS.keys()),
            "Latitud": [sitio["lat"]] + [r["lat"] for r in REFS.values()],
            "Longitud": [sitio["lon"]] + [r["lon"] for r in REFS.values()],
            "Tipo": ["Buscado"] + ["Análogo de referencia"] * len(REFS),
        })
        fig3 = px.scatter_geo(
            df_mapa, lat="Latitud", lon="Longitud", color="Tipo", hover_name="Lugar",
            color_discrete_map={"Buscado": "#4da6ff", "Análogo de referencia": "#C8102E"},
            projection="natural earth")
        fig3.update_geos(showcoastlines=True, coastlinecolor="white", showland=True, landcolor="#1e2129",
                         showocean=True, oceancolor="#0e1117", showcountries=True, countrycolor="#333")
        fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#fff"),
                           margin=dict(l=0, r=0, t=0, b=0), height=400)
        st.plotly_chart(fig3, use_container_width=True)

        with st.expander("Glosario: ¿qué significan estas variables?"):
            st.markdown("""
- **Temperatura y amplitud térmica:** si el lugar sufre extremos parecidos a los del destino. Pesan poco porque pocos lugares de la Tierra se acercan a la Luna o a Marte.
- **Radiación:** dosis estimada solo por altitud. En la Tierra la atmósfera y el campo magnético reducen la dosis, por eso el puntaje suele ser bajo.
- **Aridez/Agua:** usa la precipitación media anual (NASA POWER) y reduce el puntaje si hay lagos o costa a menos de 10 km (OpenStreetMap).
- **Relieve:** desnivel en unos 10 km (SRTM). Ni demasiado plano ni extremo: la banda ideal es de 150 a 1500 m.
- **Geología:** el terreno que eliges versus el destino mediante una matriz de similitud. Es la variable que más peso tiene en la evaluación.
- **Presión y gravedad:** se muestran, pero no entran en el índice, porque ningún sitio terrestre puede igualar el vacío lunar, la atmósfera marciana ni su gravedad.
            """)

# ---------------------------------------------------------------- Escaneo
with tab_scan:
    st.subheader("Escaneo de candidatos")
    sitios_scan = st.session_state.get("escaneo")
    if not sitios_scan:
        st.markdown(
            "<div style=\"background: rgba(30, 33, 41, 0.6); padding: 40px; border-radius: 15px; text-align: center; "
            "border: 1px solid rgba(255,255,255,0.1); margin-top: 10px;\">"
            "<h2 style=\"color: #ffffff; margin-bottom: 10px;\">Descubre qué lugares se parecen más</h2>"
            f"<p style=\"font-size: 1.1em; color: #ddd;\">Presiona <strong>Escanear candidatos</strong> en el panel izquierdo. "
            f"Se evalúan {len(CANDIDATOS)} lugares (análogos conocidos y lugares de control) y se ordenan según su similitud "
            "con el destino elegido. La primera vez tarda unos minutos porque las fuentes públicas limitan las consultas.</p></div>",
            unsafe_allow_html=True,
        )
    else:
        r = calcular_escaneo(sitios_scan, destino)
        st.markdown(f"Evaluación de {len(sitios_scan)} lugares contra **{destino}**. Un lugar cuenta como análogo solo para el destino "
                    "con el que se lo asocia (por ejemplo, Río Tinto se conoce como análogo de Marte, no de la Luna).")
        pc = lambda v: "—" if v is None else f"{v:.0f}%"
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"Promedio de análogos de {destino}", pc(r["prom_analogos"]))
        m2.metric("Análogos con nivel ALTO", f"{r['altos_analogos']} de {r['n_analogos']}")
        m3.metric("Promedio de lugares de control", pc(r["prom_controles"]))
        m4.metric("Controles bajo 40%", f"{r['bajos_controles']} de {r['n_controles']}")

        df_scan = pd.DataFrame([{
            "#": i + 1,
            "Lugar": f["s"]["nombre"],
            "Tipo": etiqueta_tipo(f["s"], destino),
            "Terreno": f["s"]["geologia"],
            "Índice (%)": round(f["g"]),
            "Nivel": nombre_nivel(f["g"]),
            "Datos": f"{f['datos']}/{len(CATS_INDICE)}",
            "Elev. (m)": fmt(f["s"], "elev", "{:.0f}"),
            "Precip. (mm/día)": fmt(f["s"], "precip", "{:.2f}"),
        } for i, f in enumerate(r["filas"])])
        st.dataframe(
            df_scan, use_container_width=True, hide_index=True,
            column_config={"Índice (%)": st.column_config.ProgressColumn("Índice (%)", min_value=0, max_value=100, format="%d")})
        st.caption("Los pesos y umbrales del modelo se ajustaron mirando análogos conocidos, así que este escaneo no es una validación "
                   f"independiente. La columna «Datos» indica cuántas de las {len(CATS_INDICE)} variables del índice tuvieron información; "
                   "con menos, el índice es menos fiable. Las coordenadas son aproximadas.")

        fig4 = go.Figure(go.Bar(
            x=[f["g"] for f in r["filas"]][::-1], y=[f["s"]["nombre"] for f in r["filas"]][::-1], orientation="h",
            marker_color=[nivel(f["g"])[1] for f in r["filas"]][::-1],
            text=[f"{f['g']:.0f}%" for f in r["filas"]][::-1], textposition="outside"))
        fig4.update_layout(
            xaxis=dict(range=[0, 110], gridcolor="#333"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Helvetica, Arial, sans-serif", color="#fff"),
            height=max(300, 30 * len(r["filas"]) + 60), margin=dict(l=20, r=20, t=10, b=20))
        st.plotly_chart(fig4, use_container_width=True)

        df_map = pd.DataFrame({
            "Lugar": [f["s"]["nombre"] for f in r["filas"]],
            "Latitud": [f["s"]["lat"] for f in r["filas"]],
            "Longitud": [f["s"]["lon"] for f in r["filas"]],
            "Nivel": [nombre_nivel(f["g"]) for f in r["filas"]],
            "Índice (%)": [round(f["g"]) for f in r["filas"]],
        })
        fig5 = px.scatter_geo(
            df_map, lat="Latitud", lon="Longitud", color="Nivel", hover_name="Lugar", hover_data={"Índice (%)": True},
            color_discrete_map=COLORES_NIVEL, projection="natural earth")
        fig5.update_traces(marker=dict(size=11, line=dict(width=1, color="#ffffff")))
        fig5.update_geos(showcoastlines=True, coastlinecolor="white", showland=True, landcolor="#1e2129",
                         showocean=True, oceancolor="#0e1117", showcountries=True, countrycolor="#333")
        fig5.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#fff"),
                           margin=dict(l=0, r=0, t=0, b=0), height=420)
        st.plotly_chart(fig5, use_container_width=True)

        st.download_button("Descargar ranking (CSV)", df_scan.to_csv(index=False).encode("utf-8"),
                           file_name=f"escaneo_{destino}.csv", mime="text/csv")

# ---------------------------------------------------------------- Base de referencia
with tab_db:
    st.subheader("Base de datos de referencia")
    st.markdown("**Destinos**")
    st.dataframe(pd.DataFrame(DESTINOS).T.drop(columns=["relieve_ideal"]), use_container_width=True)
    st.markdown("**Análogos de referencia**")
    st.dataframe(pd.DataFrame(REFS).T.astype(str), use_container_width=True)
    st.markdown("**Candidatos del escaneo**")
    st.dataframe(pd.DataFrame([{
        "Lugar": c["nombre"], "Latitud": c["lat"], "Longitud": c["lon"], "Terreno": c["geologia"],
        "Tipo": "Análogo conocido" if c["tipo"] == "analogo" else "Control",
        "Análogo de": " y ".join(c["destinos"]) or "—",
    } for c in CANDIDATOS]), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- Metodología
with tab_met:
    st.markdown(
        """
**¿Qué mide el índice (0-100%)?**
Mide la similitud *ambiental* entre un lugar de la Tierra y la Luna o Marte. A cada variable se le asigna un puntaje de 0 a 100
y el índice final corresponde al promedio ponderado de las variables que tienen dato (valor numérico).

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

La presión y la gravedad terrestres no son equiparables a las de la Luna o Marte, por eso se muestran en los datos pero no entran en el índice (no lo usamos para el cálculo de similitud).

**Niveles:** ALTO >= 60 · MODERADO >= 40 · BAJO >= 20 · MUY BAJO < 20.

**Escaneo de candidatos:** aplica el mismo índice a una lista de lugares, entre ellos análogos conocidos y lugares de control
(que no son análogos), y los ordena. Sirve para comprobar que el índice discrimina y para ver qué sitios se parecen más al destino.
Como los pesos y umbrales se calibraron con análogos conocidos, no es una validación independiente.

**Perfiles más parecidos:** compara el patrón de puntajes por variable del lugar analizado con el de cada análogo,
usando las mismas variables y pesos del índice.

**Fuentes de datos:** NASA POWER (https://power.larc.nasa.gov), SRTM vía OpenTopoData (https://www.opentopodata.org),
Open-Meteo (https://open-meteo.com), OpenStreetMap y Overpass API (https://overpass-api.de).

**Limitaciones:** los valores de la Luna, Marte y de los análogos de referencia son aproximados. El índice no mide mineralogía
ni química (salvo a través del tipo de terreno elegido): por ejemplo, Río Tinto es un análogo de Marte por su química,
no por su clima. La radiación se estima solo por altitud. El perfil de la Luna es genérico y no describe un sitio específico de
base lunar. SRTM no cubre latitudes sobre unos 60°, por lo que el relieve falta en sitios polares. Los pesos y umbrales son
decisiones de diseño, calibradas con análogos conocidos, y no una medida científica absoluta.
        """
    )
