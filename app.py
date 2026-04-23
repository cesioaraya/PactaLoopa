import streamlit as st
import pandas as pd
from supabase import create_client, Client
import random
import string
from datetime import datetime, date

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

def calcular_fecha_base(dia_inicio):
    """Calcula la próxima fecha de pago basada en el día elegido."""
    hoy = date.today()
    if hoy.day <= dia_inicio:
        return date(hoy.year, hoy.month, dia_inicio)
    else:
        if hoy.month == 12:
            return date(hoy.year + 1, 1, dia_inicio)
        return date(hoy.year, hoy.month + 1, dia_inicio)

# 3. ESTILO
st.markdown("""
    <style>
    .stButton>button { border-radius: 20px; width: 100%; }
    .catch-up { background-color: #fff3cd; padding: 15px; border-radius: 10px; border: 1px solid #ffeeba; margin-bottom: 10px; }
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
    dia_inicio = st.number_input("Día de pago (1-28)", min_value=1, max_value=28, value=1)
    pass_pacto = st.text_input("Contraseña", type="password")
    tu_nombre = st.text_input("Tu nombre (Admin)").strip()
    
    if st.button("🚀 Crear Pacto"):
        if nombre_pacto and tu_nombre and pass_pacto:
            codigo = generar_codigo()
            res = supabase.table("grupos").insert({
                "nombre": nombre_pacto, 
                "monto_cuota": monto, 
                "frecuencia": frecuencia.lower(), 
                "dia_inicio": dia_inicio, # Nuevo campo
                "codigo": codigo, 
                "password": pass_pacto
            }).execute()
            gid = res.data[0]['id']
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
            max_pos = max([p['posicion_orden'] for p in p_db.data]) if p_db.data else -1
            supabase.table("participantes").insert({"grupo_id": st.session_state.grupo_id, "nombre_usuario": nuevo, "posicion_orden": max_pos + 1}).execute()
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
    
    p_admin_check = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("id").execute()
    admin_nombre = p_admin_check.data[0]['nombre_usuario']
    
    p_res = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
    participantes = p_res.data
    es_admin = (st.session_state.mi_nombre == admin_nombre)

    # Lógica de fechas
    dia_c = grupo.get('dia_inicio', 1)
    f_pago_inicial = calcular_fecha_base(dia_c)
    
    # Diferencia en días según frecuencia
    salto = {"semanal": 7, "quincenal": 15, "mensual": 30}[grupo['frecuencia']]

    with st.sidebar:
        st.write(f"### 🛡️ {grupo['nombre']}")
        st.info(f"Código: **{grupo['codigo']}**")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio"})
            st.rerun()

    t1, t2, t3 = st.tabs(["🔄 El Loop", "💰 Mi Pago", "⚙️ Admin" if es_admin else "ℹ️ Info"])

    with t1:
        st.subheader("Estado del Loop")
        for i, p in enumerate(participantes):
            # Cálculo de fecha progresiva
            days_add = i * salto
            f_pago = f_pago_inicial + pd.Timedelta(days=days_add)
            
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.write(f"**{i+1}. {p['nombre_usuario']}**")
                st.caption(f"📅 {f_pago.strftime('%d %b %Y')}")
            with col_b:
                if p['completado']: st.success("✅")
                elif p['aviso_pago']: st.warning("🔔")
                else: st.info("⏳")

    with t2:
        yo = next(p for p in participantes if p['nombre_usuario'] == st.session_state.mi_nombre)
        st.subheader(f"Resumen de {st.session_state.mi_nombre}")
        
        if not yo['completado']:
            if yo['aviso_pago']:
                st.info("Esperando validación del administrador...")
                if st.button("❌ Cancelar reporte"):
                    supabase.table("participantes").update({"aviso_pago": False}).eq("id", yo['id']).execute()
                    st.rerun()
            else:
                st.info(f"Cuota: **${grupo['monto_cuota']}**")
                if st.button("📢 REPORTAR PAGO REALIZADO"):
                    supabase.table("participantes").update({"aviso_pago": True}).eq("id", yo['id']).execute()
                    st.rerun()
        else:
            st.success("✅ Ya has recibido tu pozo.")

    if es_admin:
        with t3:
            st.subheader("Validar Pagos")
            avisos = [p for p in participantes if p['aviso_pago']]
            for a in avisos:
                if st.button(f"Validar pago de {a['nombre_usuario']} ✅", key=f"val_{a['id']}"):
                    supabase.table("participantes").update({"completado": True, "aviso_pago": False}).eq("id", a['id']).execute()
                    st.rerun()
            
            st.write("---")
            st.subheader("Reordenar Pendientes")
            # Filtramos solo los que NO han completado para poder moverlos
            pendientes = [p for p in participantes if not p['completado']]
            nombres_pend = [p['nombre_usuario'] for p in pendientes]
            
            if len(nombres_pend) > 1:
                nuevo_orden = st.multiselect("Nuevo orden de quienes no han cobrado:", nombres_pend, default=nombres_pend)
                if st.button("💾 Guardar Nuevo Orden"):
                    # Conservamos los completados al inicio
                    completados = [p for p in participantes if p['completado']]
                    orden_total = completados + [next(p for p in pendientes if p['nombre_usuario'] == n) for n in nuevo_orden]
                    
                    for i, p in enumerate(orden_total):
                        supabase.table("participantes").update({"posicion_orden": i}).eq("id", p['id']).execute()
                    st.success("Orden actualizado")
                    st.rerun()
            else:
                st.info("No hay suficientes miembros pendientes para reordenar.")

            st.write("---")
            st.subheader("Eliminar Miembros")
            opciones_eliminar = [p['nombre_usuario'] for p in participantes if p['nombre_usuario'] != admin_nombre]
            if opciones_eliminar:
                u_elim = st.selectbox("Seleccionar:", opciones_eliminar)
                if st.button("🗑️ Eliminar"):
                    supabase.table("participantes").delete().eq("grupo_id", st.session_state.grupo_id).eq("nombre_usuario", u_elim).execute()
                    st.rerun()

    else:
        with t3:
            st.write(f"Admin: {admin_nombre}")
            st.write(f"Día de pago base: día {dia_c} de cada mes")
