import streamlit as st
import pandas as pd
import streamlit as st
from supabase import create_client, Client
import os

# 1. Conexión segura a Supabase usando los Secretos de GitHub/Streamlit
try:
    # Cuando estés en local usará .env, en la web usará los Secrets
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Error al conectar con la base de datos. Verifica los Secretos.")

# --- Aquí seguiría el resto de tu código de la interfaz ---
st.title("🤝 PactaLoopa")


# Configuración de la página
st.set_page_config(page_title="PactaLoopa", page_icon="🤝", layout="centered")

# Estilo personalizado (Verde esmeralda y Azul)
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #10b981; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")
st.subheader("El loop de ahorro comunitario")

# --- SIDEBAR (Menú lateral) ---
with st.sidebar:
    st.header("Configurar Pacto")
    nombre_pacto = st.text_input("Nombre del Pacto", placeholder="Ej. Familia y Amigos")
    monto = st.number_input("Cuota por persona ($)", min_value=1, value=100)
    frecuencia = st.selectbox("Frecuencia", ["Semanal", "Quincenal", "Mensual"])
    num_personas = st.slider("Número de participantes", 2, 20, 5)

# --- LÓGICA BÁSICA ---
st.info(f"**Total del pozo:** ${monto * num_personas} que se entregan en cada turno.")

# Crear una lista de participantes ficticia para el ejemplo
participantes = [f"Participante {i+1}" for i in range(num_personas)]
turnos_df = pd.DataFrame({
    "Orden": list(range(1, num_personas + 1)),
    "Nombre": participantes,
    "Estado": ["Pendiente"] * num_personas
})

# --- PANTALLA PRINCIPAL ---
tab1, tab2 = st.tabs(["🔄 El Loop Actual", "📋 Gestión de Pagos"])

with tab1:
    st.write("### 🏆 Beneficiario de esta ronda:")
    # Simulamos que vamos en la ronda 1
    ronda_actual = 1
    ganador_hoy = participantes[ronda_actual - 1]
    
    st.success(f"🌟 **{ganador_hoy}** recibe hoy: **${monto * num_personas}**")
    
    st.progress(ronda_actual / num_personas)
    st.caption(f"Ronda {ronda_actual} de {num_personas}")

with tab2:
    st.write("### ✅ Confirmar Pagos")
    st.write("Marca a los miembros que ya entregaron su cuota:")
    
    for p in participantes:
        st.checkbox(f"Pago recibido de: {p}", key=p)
    
    if st.button("Guardar progreso del día"):
        st.balloons()
        st.success("¡Progreso actualizado!")

# --- PIE DE PÁGINA ---
st.markdown("---")
st.caption("PactaLoopa no gestiona dinero. Los pagos se realizan de forma externa entre los usuarios.")
