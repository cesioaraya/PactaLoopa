import streamlit as st
import pandas as pd
from supabase import create_client, Client
import random
import string

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PactaLoopa", page_icon="🤝", layout="centered")

# 2. CONEXIÓN A SUPABASE
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"].strip().replace("/rest/v1/", "").rstrip("/")
        key = st.secrets["SUPABASE_KEY"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error al conectar: {e}")
        return None

supabase = init_connection()

def generar_codigo():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# 3. ESTILO PERSONALIZADO
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #10b981; color: white; border: none; }
    .stButton>button:hover { background-color: #059669; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")
st.subheader("El loop de ahorro comunitario")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Menú Principal")
    modo = st.radio("¿Qué deseas hacer?", ["Crear Nuevo Pacto", "Unirse a un Pacto"])
    
    st.divider()

    if modo == "Crear Nuevo Pacto":
        st.subheader("Configurar Pacto")
        nombre_pacto = st.text_input("Nombre del Pacto", placeholder="Ej. Familia y Amigos")
        monto = st.number_input("Cuota por persona ($)", min_value=1, value=100)
        frecuencia = st.selectbox("Frecuencia", ["Semanal", "Quincenal", "Mensual"])
        num_personas = st.slider("Número de participantes", 2, 20, 5)
        
        if st.button("🚀 Crear y Generar Código"):
            if nombre_pacto:
                try:
                    codigo_unico = generar_codigo()
                    data = {
                        "nombre": nombre_pacto,
                        "monto_cuota": monto,
                        "frecuencia": frecuencia.lower(),
                        "codigo": codigo_unico
                    }
                    supabase.table("grupos").insert(data).execute()
                    st.success(f"¡Pacto '{nombre_pacto}' creado!")
                    st.code(codigo_unico, language="text")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("Por favor, ponle un nombre al pacto.")
    
    else:
        st.subheader("Unirse a un Pacto")
        codigo_input = st.text_input("Introduce el código", placeholder="Ej. A7B2X9").upper().strip()
        tu_nombre = st.text_input("Tu nombre o alias")
        
        if st.button("🤝 Unirme al Loop"):
            if codigo_input and tu_nombre:
                # 1. Buscar si el código existe
                grupo = supabase.table("grupos").select("id, nombre").eq("codigo", codigo_input).execute()
                
                if len(grupo.data) > 0:
                    id_grupo = grupo.data[0]['id']
                    nombre_g = grupo.data[0]['nombre']
                    
                    # 2. Insertar al participante
                    nuevo_p = {
                        "grupo_id": id_grupo,
                        "nombre_usuario": tu_nombre,
                        "completado": False
                    }
                    supabase.table("participantes").insert(nuevo_p).execute()
                    st.success(f"¡Te has unido a: {nombre_g}!")
                    st.balloons()
                else:
                    st.error("Código no encontrado. Verifica e intenta de nuevo.")
            else:
                st.warning("Escribe el código y tu nombre.")

# --- LÓGICA DE VISUALIZACIÓN ---
# Aquí es donde el Administrador verá a la gente que se une en tiempo real
st.divider()
st.write("### 👥 Participantes en este Pacto")

# Para fines de este paso, buscaremos el último pacto creado o unido para mostrarlo
# (En el futuro esto será más dinámico)
st.info("Aquí aparecerán los nombres de quienes usen tu código.")

# --- PANTALLA PRINCIPAL (Tabs) ---
tab1, tab2 = st.tabs(["🔄 El Loop Actual", "📋 Gestión de Pagos"])

with tab1:
    st.write("Visualización del orden de turnos...")

with tab2:
    st.write("Control de quién ha pagado esta ronda...")

st.markdown("---")
st.caption("PactaLoopa no gestiona dinero. Los pagos se realizan de forma externa.")
