import streamlit as pd_st 
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import requests
import io
import warnings

# 1. Silenciamos advertencias de rendimiento de fragmentación de memoria en la terminal
warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)
warnings.filterwarnings('ignore', message='.*Could not infer format.*')
warnings.filterwarnings('ignore', message='.*DtypeWarning.*')
warnings.filterwarnings('ignore', message='.*Pandas4Warning.*')
warnings.filterwarnings('ignore', message='.*UserWarning.*')

st = pd_st

# Configuración de pantalla de la aplicación (Diseño Institucional Los Lagos)
st.set_page_config(
    page_title="Los Lagos - Monitor de Alertas", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 📥 MOTOR DE INGESTA DIRECTO DESDE GOOGLE DRIVE
# ==========================================
df_alertas = pd.DataFrame()
el_error_fue_evadido = False

try:
    sesion_web = requests.Session()
    
    # 🎯 BLINDAJE ANTIBLOQUEO: Construcción segmentada inmune a alteraciones de red del chat
    servidor_uno = "docs."
    servidor_dos = "google"
    servidor_tres = ".com"
    dominio_real = "https://" + servidor_uno + servidor_dos + servidor_tres + "/spreadsheets/d/"
    
    # ID independiente exclusivo de tu libro de Alertas Waze
    id_alertas = "1OkI6V0lV89CqAUewSLO63UJp-vikIrjK9ykP3_mTSbY"
    ENLACE_ALERTAS_WAZE = dominio_real + id_alertas + "/export?format=csv&sheet=alertas_waze"
    
    # El programa descarga de forma transparente únicamente la planilla de siniestros
    descarga_a = sesion_web.get(ENLACE_ALERTAS_WAZE, timeout=20)
    
    # Lector elástico tolerante posicional
    df_a = pd.read_csv(io.StringIO(descarga_a.content.decode('utf-8', errors='ignore')), sep=',', engine='c', on_bad_lines='skip', low_memory=False)
    df_a = df_a.copy()

    # REESTRUCTURACIÓN CIEGA BLINDADA: Sobreescribimos títulos por llaves numéricas fijas
    df_a.columns = [f"Col_{i}" for i in range(len(df_a.columns))]
    
    # Asignación milimétrica calibrada en base a tu Drive (Col_6=Lat, Col_7=Lon)
    df_a['Latitud'] = pd.to_numeric(df_a['Col_6'], errors='coerce')
    df_a['Longitud'] = pd.to_numeric(df_a['Col_7'], errors='coerce')
    
    # Caída de respaldo si Google sheets condensa las coordenadas en Col_5
    if df_a['Latitud'].isna().all() and len(df_a.columns) >= 6:
        coords_split = df_a['Col_5'].astype(str).str.split(',', expand=True)
        if len(coords_split.columns) >= 2:
            df_a['Latitud'] = pd.to_numeric(coords_split.iloc[:, 0], errors='coerce')
            df_a['Longitud'] = pd.to_numeric(coords_split.iloc[:, 1], errors='coerce')

    df_a['Fecha_Hora'] = pd.to_datetime(df_a['Col_0'].astype(str).str.strip(), errors='coerce', format='mixed')
    df_a['Tipo_Incidente'] = df_a['Col_2'].astype(str).str.upper().str.strip()
    df_a['Subtipo'] = df_a['Col_3'].astype(str).str.upper().str.strip()
    df_a['Calle'] = df_a['Col_4'].astype(str).str.upper().str.strip()

    # Conservamos únicamente los registros válidos georreferenciadas para el plano urbano
    df_alertas = df_a.dropna(subset=['Latitud', 'Longitud'])

    # RASTREO MULTICOLUMNA DE SEMÁFOROS CON FALLA (Busca focos críticos UOCT)
    if not df_alertas.empty:
        columnas_texto = [c for c in df_alertas.columns if c in ['Tipo_Incidente', 'Subtipo', 'Calle']]
        if columnas_texto:
            condicion_semaforo = df_alertas[columnas_texto].apply(
                lambda row: row.astype(str).str.contains('SEMÁFORO|SEMAFORO|LIGHT|FAULT', na=False)
            ).any(axis=1)
            df_alertas.loc[condicion_semaforo, 'Tipo_Incidente'] = 'SEMÁFORO CON FALLA'
        
        # Homologación original al español para los gráficos institucionales
        df_alertas['Tipo_Incidente'] = df_alertas['Tipo_Incidente'].replace({
            'ACCIDENT': 'ACCIDENTE', 'HAZARD': 'PELIGRO EN LA VÍA', 'JAM': 'ATASCO / CONGESTIÓN', 'ROAD_CLOSED': 'CIERRE DE VÍA'
        })
        df_alertas['Tipo_Incidente'] = df_alertas['Tipo_Incidente'].str.replace('VÃA', 'VÍA').str.replace('CONGESTIÃN', 'CONGESTIÓN')

except Exception as e:
    st.error(f"⚠️ Detención del motor de red por desajuste: {e}")
    el_error_fue_evadido = True

df_alertas, el_error_fue_evadido = df_alertas, el_error_fue_evadido



# ==========================================
# 🎛️ FILTROS DE LA BARRA LATERAL (CONTROLES)
# ==========================================
st.sidebar.header("🗓️ Filtros Temporales y de Eventos")

if not el_error_fue_evadido and not df_alertas.empty:
    st.sidebar.success("✅ Sincronizado en vivo con Google Drive")

    # Extraemos fechas simples para los selectores gráficos
    df_alertas['Fecha_Solo'] = pd.to_datetime(df_alertas['Fecha_Hora'], errors='coerce').dt.date

    # Límites históricos reales basados en tu libro de incidentes
    fecha_minima = date(2026, 6, 5)
    fecha_maxima = date.today()

    st.sidebar.markdown("### Rango de Fechas")
    
    # 🎯 CALENDARIOS GRÁFICOS INDEPENDIENTES: Libres de congelamientos y textos raros en el navegador
    inicio_sel = st.sidebar.date_input("Desde el:", value=fecha_minima, min_value=fecha_minima, max_value=fecha_maxima)
    fin_sel = st.sidebar.date_input("Hasta el:", value=fecha_maxima, min_value=fecha_minima, max_value=fecha_maxima)

    if inicio_sel > fin_sel:
        st.sidebar.error("❌ La fecha de inicio no puede ser posterior a la de fin.")
        inicio_sel, fin_sel = fin_sel, inicio_sel

    # Categorías institucionales de la región
    opciones_fijas = ['ACCIDENTE', 'SEMÁFORO CON FALLA', 'ATASCO / CONGESTIÓN', 'PELIGRO EN LA VÍA', 'CIERRE DE VÍA']
    tipos_seleccionados = st.sidebar.multiselect("Categorías de Incidentes:", options=opciones_fijas, default=opciones_fijas)

    # FILTRADO DINÁMICO DE EXTREMOS POR PANDAS (Omitimos filtro de subtipo por solicitud)
    df_alertas_filtrado = df_alertas[(df_alertas['Fecha_Solo'] >= inicio_sel) & (df_alertas['Fecha_Solo'] <= fin_sel) & (df_alertas['Tipo_Incidente'].isin(tipos_seleccionados))]
else:
    df_alertas_filtrado = pd.DataFrame()
    inicio_sel = date(2026, 9, 1)
    fin_sel = date(2026, 9, 1)



# ==========================================
# 📊 DESPLIEGUE INTERFAZ DE PANELES (MAPA REGIONAL MAXIMIZADO)
# ==========================================
# 🎯 CONSTRUCCIÓN DE FECHAS DINÁMICAS PARA EL TÍTULO ÚNICO
fecha_inicio_txt = inicio_sel.strftime("%d/%m/%Y") if hasattr(inicio_sel, 'strftime') else str(inicio_sel)
fecha_fin_txt = fin_sel.strftime("%d/%m/%Y") if hasattr(fin_sel, 'strftime') else str(fin_sel)

if fecha_inicio_txt == fecha_fin_txt:
    texto_temporal = f"— Día: {fecha_inicio_txt}"
else:
    texto_temporal = f"— Período: {fecha_inicio_txt} al {fecha_fin_txt}"

# 🎯 ENCABEZADO ÚNICO INSTITUCIONAL (Sin la palabra SEREMI)
st.markdown(f"## 🗺️ Plataforma de Tendencias y Gestión Vial {texto_temporal}")
st.caption("🟢 **Visor Geoanalítico Regional** — Sincronización automática de incidentes y contingencias en la Región de Los Lagos")
st.write("")

# Indicadores de resumen institucional en la parte superior
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1: st.metric("Total Incidentes en Período", len(df_alertas_filtrado))
with col_m2:
    choques = len(df_alertas_filtrado[df_alertas_filtrado['Tipo_Incidente'].astype(str).str.contains('ACCIDENTE', na=False, case=False)]) if not df_alertas_filtrado.empty else 0
    st.metric("Siniestros Viales (Choques)", choques)
with col_m3:
    fallas_sem = len(df_alertas_filtrado[df_alertas_filtrado['Tipo_Incidente'] == 'SEMÁFORO CON FALLA']) if not df_alertas_filtrado.empty else 0
    st.metric("Fallas de Semáforos (Foco UOCT)", fallas_sem)
    
st.write("---")

# Lienzo a pantalla completa expandido al 100% de ancho
if not df_alertas_filtrado.empty:
    fig_mapa = px.scatter_map(
        df_alertas_filtrado, 
        lat="Latitud", 
        lon="Longitud", 
        color="Tipo_Incidente", 
        hover_name="Calle", 
        hover_data={"Latitud": False, "Longitud": False, "Fecha_Hora": True, "Subtipo": True}, 
        labels={"Fecha_Hora": "Fecha y Hora", "Tipo_Incidente": "Categoría"},
        zoom=11.5,          # Foco optimizado para las vías estructurantes
        height=720,         # Altura expandida para máxima definición en pantallas grandes
        center=dict(lat=-41.465, lon=-72.942),
        color_discrete_map={
            'ACCIDENTE': '#e63946', 
            'PELIGRO EN LA VÍA': '#ffb703', 
            'CIERRE DE VÍA': '#1d3557', 
            'ATASCO / CONGESTIÓN': '#7209b7', 
            'SEMÁFORO CON FALLA': '#2563eb'
        }
    )
    
    # 🎯 CONFIGURACIÓN DE LEYENDA CENTRADA: Alineamos horizontalmente el título y los pines abajo
    fig_mapa.update_layout(
        map=dict(style="open-street-map"), 
        margin={"r":10,"t":10,"l":10,"b":10}, 
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=-0.12, 
            xanchor="center", 
            x=0.5, 
            title=dict(
                text="Clasificación del Evento Operativo",
                side="top"
            )
        )
    )
    st.plotly_chart(fig_mapa, use_container_width=True, key="mapa_regional_los_lagos_final_puro")
else:
    st.info("Seleccione un rango histórico en la barra lateral que contenga registros para proyectar la cartografía regional.")
