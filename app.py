import streamlit as st
import pandas as pd
from supabase import create_client, Client

# 1. CONFIGURACIÓN DE PÁGINA (Debe ser lo primero)
st.set_page_config(page_title="PactaLoopa", page_icon="🤝", layout="centered")

# 2. CONEXIÓN A SUPABASE
@st.cache_resource
def init_connection():
    try:
        # Extraemos y limpiamos: eliminamos espacios y la parte final de la ruta si existe
        url = st.secrets["SUPABASE_URL"].strip().replace("/rest/v1/", "").rstrip("/")
        key = st.secrets["SUPABASE_KEY"].strip()
        
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error al conectar: {e}")
        return None

supabase = init_connection()

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
    st.header("Configurar Pacto")
    nombre_pacto = st.text_input("Nombre del Pacto", placeholder="Ej. Familia y Amigos")
    monto = st.number_input("Cuota por persona ($)", min_value=1, value=100)
    frecuencia = st.selectbox("Frecuencia", ["Semanal", "Quincenal", "Mensual"])
    num_personas = st.slider("Número de participantes", 2, 20, 5)
    
    st.divider()
    
    # BOTÓN PARA GUARDAR EN BASE DE DATOS
    if st.button("🚀 Crear y Guardar Pacto"):
        if nombre_pacto:
            try:
                data = {
                    "nombre": nombre_pacto,
                    "monto_cuota": monto,
                    "frecuencia": frecuencia.lower()
                }
                # Insertar en la tabla 'grupos' de Supabase
                response = supabase.table("grupos").insert(data).execute()
                st.success(f"¡Pacto '{nombre_pacto}' guardado en la nube!")
                st.balloons()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
        else:
            st.warning("Por favor, ponle un nombre al pacto.")

# --- LÓGICA DE VISUALIZACIÓN ---
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
