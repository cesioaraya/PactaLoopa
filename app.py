import streamlit as st
import pandas as pd
from supabase import create_client, Client
import random
import string
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN
st.set_page_config(page_title="PactaLoopa", page_icon="🤝", layout="centered")

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

# 3. ESTILO
st.markdown("""
    <style>
    .stButton>button { border-radius: 20px; width: 100%; }
    .stat-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border: 1px solid #e1e4e8; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")

if "grupo_id" not in st.session_state:
    st.session_state.grupo_id = None
    st.session_state.vista = "inicio"
    st.session_state.mi_nombre = ""

# --- NAVEGACIÓN INICIAL ---
if st.session_state.vista == "inicio":
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✨ Crear Nuevo Pacto"): st.session_state.vista = "crear"; st.rerun()
    with col2:
        if st.button("🤝 Entrar a un Pacto"): st.session_state.vista = "unirse"; st.rerun()

elif st.session_state.vista == "crear":
    if st.button("⬅️ Volver"): st.session_state.vista = "inicio"; st.rerun()
    st.subheader("Configurar Pacto")
    nombre_pacto = st.text_input("Nombre del Pacto")
    monto = st.number_input("Cuota ($)", min_value=1, value=100)
    frecuencia = st.selectbox("Frecuencia", ["Semanal", "Quincenal", "Mensual"])
    pass_pacto = st.text_input("Contraseña", type="password")
    tu_nombre = st.text_input("Tu nombre (Admin)").strip()
    
    if st.button("🚀 Crear Pacto"):
        if nombre_pacto and tu_nombre and pass_pacto:
            codigo = generar_codigo()
            res = supabase.table("grupos").insert({"nombre": nombre_pacto, "monto_cuota": monto, "frecuencia": frecuencia.lower(), "codigo": codigo, "password": pass_pacto}).execute()
            gid = res.data[0]['id']
            # El primer participante insertado es el Admin por defecto
            supabase.table("participantes").insert({"grupo_id": gid, "nombre_usuario": tu_nombre, "posicion_orden": 0}).execute()
            st.session_state.update({"grupo_id": gid, "mi_nombre": tu_nombre, "vista": "dashboard"})
            st.rerun()

elif st.session_state.vista == "unirse":
    if st.button("⬅️ Volver"): st.session_state.vista = "inicio"; st.rerun()
    c_in = st.text_input("Código").upper().strip()
    p_in = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        g = supabase.table("grupos").select("*").eq("codigo", c_in).eq("password", p_in).execute()
        if g.data:
            st.session_state.grupo_id = g.data[0]['id']
            st.session_state.vista = "seleccionar_usuario"; st.rerun()
        else: st.error("Datos incorrectos")

elif st.session_state.vista == "seleccionar_usuario":
    p_db = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).execute()
    nombres = [p['nombre_usuario'] for p in p_db.data]
    sel = st.selectbox("¿Quién eres?", ["-- Nuevo --"] + nombres)
    if sel == "-- Nuevo --":
        nuevo = st.text_input("Tu nombre").strip()
        if st.button("Unirme") and nuevo:
            supabase.table("participantes").insert({"grupo_id": st.session_state.grupo_id, "nombre_usuario": nuevo, "posicion_orden": len(nombres)}).execute()
            st.session_state.mi_nombre = nuevo
            st.session_state.vista = "dashboard"; st.rerun()
    else:
        if st.button(f"Entrar como {sel}"):
            st.session_state.mi_nombre = sel
            st.session_state.vista = "dashboard"; st.rerun()

# --- DASHBOARD PRINCIPAL ---
elif st.session_state.vista == "dashboard":
    g_res = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    grupo = g_res.data[0]
    
    # Obtenemos participantes ordenados por ID para saber quién fue el primero (Admin)
    p_admin_check = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("id").execute()
    admin_nombre = p_admin_check.data[0]['nombre_usuario']
    
    # Obtenemos participantes para el orden del Loop
    p_res = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
    participantes = p_res.data
    
    # CORRECCIÓN CLAVE: El admin se identifica por nombre inicial, no por posición en el loop
    es_admin = (st.session_state.mi_nombre == admin_nombre)

    with st.sidebar:
        st.write(f"### 🛡️ {grupo['nombre']}")
        st.info(f"Código: **{grupo['codigo']}**")
        st.write("---")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.grupo_id = None
            st.session_state.mi_nombre = ""
            st.session_state.vista = "inicio"
            st.rerun()

    t1, t2, t3 = st.tabs(["🔄 El Loop", "💰 Mi Pago", "⚙️ Panel Admin" if es_admin else "ℹ️ Info"])

    with t1:
        st.subheader("Estado del Grupo")
        cobrados = [p for p in participantes if p['completado']]
        pendientes = [p for p in participantes if not p['completado']]
        
        c1, c2 = st.columns(2)
        c1.metric("Ya cobraron", len(cobrados))
        c2.metric("Faltan", len(pendientes))
        
        st.write("---")
        f_inicio = datetime.fromisoformat(grupo['creado_en'].split('T')[0])
        dias = {"semanal": 7, "quincenal": 15, "mensual": 30}[grupo['frecuencia']]
        
        for i, p in enumerate(participantes):
            f_pago = f_inicio + timedelta(days=i * dias)
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.write(f"**{i+1}. {p['nombre_usuario']}**")
                st.caption(f"📅 Recibe: {f_pago.strftime('%d %b %Y')}")
            with col_b:
                if p['completado']: st.success("✅")
                elif p['aviso_pago']: st.warning("🔔")
                else: st.info("⏳")

    with t2:
        yo = next(p for p in participantes if p['nombre_usuario'] == st.session_state.mi_nombre)
        st.subheader(f"Resumen de {st.session_state.mi_nombre}")
        
        # Pagos realizados por el grupo (quienes ya cobraron)
        pagos_realizados = len(cobrados)
        
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Cuotas cobradas", f"{pagos_realizados}")
        col_m2.metric("Restantes", f"{len(pendientes)}")

        st.write("---")
        if yo['completado']:
            st.success("🎉 Ya recibiste tu pozo de este ciclo.")
        elif yo['aviso_pago']:
            st.warning("Aviso enviado. Esperando validación del Admin.")
            if st.button("❌ Cancelar Aviso"):
                supabase.table("participantes").update({"aviso_pago": False}).eq("id", yo['id']).execute()
                st.rerun()
        else:
            st.info(f"Cuota: **${grupo['monto_cuota']}**")
            if st.button("📢 MARCAR COMO PAGADO"):
                supabase.table("participantes").update({"aviso_pago": True}).eq("id", yo['id']).execute()
                st.rerun()

    if es_admin:
        with t3:
            st.subheader("Gestión de Pagos")
            avisos = [p for p in participantes if p['aviso_pago'] and not p['completado']]
            if avisos:
                for a in avisos:
                    col1, col2 = st.columns([2, 1])
                    col1.write(f"¿Confirmar pago de **{a['nombre_usuario']}**?")
                    if col2.button("Confirmar ✅", key=f"admin_c_{a['id']}"):
                        supabase.table("participantes").update({"completado": True, "aviso_pago": False}).eq("id", a['id']).execute()
                        st.rerun()
            else:
                st.info("No hay avisos de pago pendientes.")

            st.write("---")
            st.subheader("Reordenar Pendientes")
            st.caption("Solo puedes mover a quienes no han recibido el dinero.")
            
            nombres_ya = [p['nombre_usuario'] for p in participantes if p['completado']]
            nombres_no = [p['nombre_usuario'] for p in participantes if not p['completado']]
            
            if len(nombres_no) > 1:
                nuevo_orden = st.multiselect("Nuevo orden para pendientes:", nombres_no, default=nombres_no)
                
                if st.button("💾 Guardar Nuevo Orden"):
                    if len(nuevo_orden) == len(nombres_no):
                        orden_final = nombres_ya + nuevo_orden
                        for idx, nombre in enumerate(orden_final):
                            supabase.table("participantes").update({"posicion_orden": idx}).eq("grupo_id", st.session_state.grupo_id).eq("nombre_usuario", nombre).execute()
                        st.success("¡Orden actualizado!")
                        st.rerun()
            else:
                st.write("No hay suficientes personas pendientes para reordenar.")

            st.write("---")
            with st.expander("⚠️ Zona de Peligro"):
                if st.button("ELIMINAR PACTO DEFINITIVAMENTE"):
                    supabase.table("participantes").delete().eq("grupo_id", st.session_state.grupo_id).execute()
                    supabase.table("grupos").delete().eq("id", st.session_state.grupo_id).execute()
                    st.session_state.vista = "inicio"
                    st.rerun()
    else:
        with t3:
            st.info("ℹ️ Esta sección contiene información general del grupo.")
            st.write(f"Administrador: **{admin_nombre}**")
            st.write(f"Frecuencia de pago: **{grupo['frecuencia'].capitalize()}**")
