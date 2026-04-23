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

# Función para generar código corto aleatorio
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

# --- CABECERA ---
st.title("🤝 PactaLoopa")
st.subheader("El loop de ahorro comunitario")

# --- SIDEBAR (Configuración) ---
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
                    st.info(f"Comparte este código con los demás:")
                    st.code(codigo_unico, language="text")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("Por favor, ponle un nombre al pacto.")
    
    else:
        st.subheader("Unirse a un Pacto")
        codigo_input = st.text_input("Introduce el código", placeholder="Ej. A7B2X9")
        tu_nombre = st.text_input("Tu nombre o alias")
        if st.button("🤝 Unirme al Loop"):
            if codigo_input and tu_nombre:
                st.info(f"Buscando el pacto {codigo_input}...")
                # Aquí conectaremos la lógica de inscripción en el siguiente paso
            else:
                st.warning("Escribe el código y tu nombre.")

# --- LÓGICA DE VISUALIZACIÓN ---
# Nota: Por ahora 'monto' y 'num_personas' se toman de la sidebar para la previsualización
st.info(f"**Total del pozo:** ${monto * num_personas} que se entregan en cada turno.")

# Simulación de participantes para la UI
participantes = [f"Participante {i+1}" for i in range(num_personas)]

# --- PANTALLA PRINCIPAL ---
tab1, tab2 = st.tabs(["🔄 El Loop Actual", "📋 Gestión de Pagos"])

with tab1:
    st.write("### 🏆 Beneficiario de esta ronda:")
    ronda_actual = 1
    ganador_hoy = participantes[ronda_actual - 1]
    
    st.success(f"🌟 **{ganador_hoy}** recibe hoy: **${monto * num_personas}**")
    st.progress(ronda_actual / num_personas)
    st.caption(f"Ronda {ronda_actual} de {num_personas}")

with tab2:
    st.write("### ✅ Confirmar Pagos")
    st.write("Marca a los miembros que ya entregaron su cuota:")
    
    for p in participantes:
        st.checkbox(f"Pago recibido de: {p}", key=f"pago_{p}")
    
    if st.button("Guardar progreso del día"):
        st.toast("Progreso guardado localmente")

# --- PIE DE PÁGINA ---
st.markdown("---")
st.caption("PactaLoopa no gestiona dinero. Los pagos se realizan de forma externa entre los usuarios.")
st.markdown("---")
st.caption("PactaLoopa no gestiona dinero. Los pagos se realizan de forma externa entre los usuarios.")
