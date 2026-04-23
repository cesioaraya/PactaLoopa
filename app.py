import streamlit as st
import pandas as pd
from supabase import create_client, Client
import random
import string
from datetime import datetime, date, timedelta

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
    .days-badge { background-color: #e8f0fe; color: #1a73e8; padding: 5px 10px; border-radius: 10px; font-weight: bold; }
    .info-card { background-color: #f8f9fa; padding: 15px; border-radius: 15px; border-left: 5px solid #1a73e8; margin-bottom: 20px; }
    .status-ok { color: #28a745; font-weight: bold; }
    .status-wait { color: #ffc107; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")

if "grupo_id" not in st.session_state:
    st.session_state.update({"grupo_id": None, "vista": "inicio", "mi_nombre": ""})

# --- LÓGICA DE NAVEGACIÓN ---
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
    fecha_inicio = st.date_input("¿Cuándo inicia el primer pago?", value=date.today())
    pass_pacto = st.text_input("Contraseña", type="password")
    tu_nombre = st.text_input("Tu nombre (Admin)").strip()
    
    if st.button("🚀 Crear Pacto"):
        if nombre_pacto and tu_nombre and pass_pacto:
            codigo = generar_codigo()
            res = supabase.table("grupos").insert({
                "nombre": nombre_pacto, "monto_cuota": monto, 
                "frecuencia": frecuencia.lower(), "fecha_inicio": fecha_inicio.isoformat(),
                "codigo": codigo, "password": pass_pacto, "abierto": True
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
    g_db = supabase.table("grupos").select("abierto").eq("id", st.session_state.grupo_id).execute()
    grupo_abierto = g_db.data[0].get('abierto', True)
    
    nombres = [p['nombre_usuario'] for p in p_db.data]
    opciones = ["-- Seleccionar --"]
    if grupo_abierto: opciones.append("-- Nuevo Miembro --")
    opciones.extend(nombres)
    
    sel = st.selectbox("¿Quién eres?", opciones)
    
    if sel == "-- Nuevo Miembro --":
        nuevo = st.text_input("Tu nombre").strip()
        if st.button("Unirme") and nuevo:
            max_pos = max([p['posicion_orden'] for p in p_db.data]) if p_db.data else -1
            supabase.table("participantes").insert({"grupo_id": st.session_state.grupo_id, "nombre_usuario": nuevo, "posicion_orden": max_pos + 1}).execute()
            st.session_state.mi_nombre = nuevo; st.session_state.vista = "dashboard"; st.rerun()
    elif sel != "-- Seleccionar --":
        if st.button(f"Entrar como {sel}"):
            st.session_state.mi_nombre = sel; st.session_state.vista = "dashboard"; st.rerun()

# --- DASHBOARD PRINCIPAL ---
elif st.session_state.vista == "dashboard":
    g_res = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    if not g_res.data:
        st.session_state.update({"grupo_id": None, "vista": "inicio"}); st.rerun()
        
    grupo = g_res.data[0]
    p_res = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
    participantes = p_res.data
    
    admin_nombre = participantes[0]['nombre_usuario'] if participantes else ""
    es_admin = (st.session_state.mi_nombre == admin_nombre)

    # Lógica de fechas
    f_inicio = date.fromisoformat(grupo['fecha_inicio'])
    salto = {"semanal": 7, "quincenal": 15, "mensual": 30}[grupo['frecuencia']]
    
    # Identificar quién recibe el pozo este periodo (el primero que no ha marcado "completado")
    beneficiario_actual = next((p for p in participantes if not p['completado']), None)
    idx_periodo = participantes.index(beneficiario_actual) if beneficiario_actual else 0
    fecha_periodo = f_inicio + timedelta(days=idx_periodo * salto)

    with st.sidebar:
        st.write(f"### 🛡️ {grupo['nombre']}")
        st.caption(f"Código: {grupo['codigo']}")
        if st.button("🚪 Salir"):
            st.session_state.update({"grupo_id": None, "vista": "inicio"}); st.rerun()

    t1, t2, t3 = st.tabs(["🔄 El Loop", "💰 Mi Pago", "⚙️ Admin" if es_admin else "ℹ️ Info"])

    with t1:
        st.subheader("Estado del Mes Actual")
        st.markdown(f"""
        <div class="info-card">
            👤 Recibe el pozo: <b>{beneficiario_actual['nombre_usuario'] if beneficiario_actual else 'Ciclo Finalizado'}</b><br>
            📅 Fecha de entrega: <b>{fecha_periodo.strftime('%d %b %Y')}</b>
        </div>
        """, unsafe_allow_html=True)
        
        for p in participantes:
            col_u, col_s = st.columns([3, 1])
            with col_u:
                st.write(f"{'⭐ ' if p == beneficiario_actual else ''}{p['nombre_usuario']}")
            with col_s:
                if p['completado']: st.write("✅")
                elif p['aviso_pago']: st.write("🔔")
                else: st.write("⏳")

    with t2:
        yo = next(p for p in participantes if p['nombre_usuario'] == st.session_state.mi_nombre)
        st.subheader("Tu Cuota")
        
        dias = (fecha_periodo - date.today()).days
        st.markdown(f"Faltan <span class='days-badge'>{max(0, dias)} días</span> para el cierre de este periodo.", unsafe_allow_html=True)
        
        st.write("---")
        if yo['aviso_pago']:
            st.warning("Pago reportado. Esperando validación del administrador.")
            if st.button("❌ Cancelar Reporte"):
                supabase.table("participantes").update({"aviso_pago": False}).eq("id", yo['id']).execute()
                st.rerun()
        elif not yo['completado'] or (beneficiario_actual and yo['id'] != beneficiario_actual['id']):
            st.info(f"Monto a depositar: **${grupo['monto_cuota']}**")
            if st.button("📢 YA DEPOSITÉ"):
                supabase.table("participantes").update({"aviso_pago": True}).eq("id", yo['id']).execute()
                st.rerun()
        else:
            st.success("¡Felicidades! Ya recibiste tu pozo de este ciclo.")

    if es_admin:
        with t3:
            st.subheader("Validación de Depósitos")
            avisos = [p for p in participantes if p['aviso_pago']]
            
            if not avisos:
                st.caption("No hay reportes de pago pendientes.")
            else:
                for a in avisos:
                    if st.button(f"Confirmar pago de {a['nombre_usuario']} ✅"):
                        # Aquí solo marcamos que pagó su cuota
                        supabase.table("participantes").update({"aviso_pago": False, "completado": True}).eq("id", a['id']).execute()
                        st.rerun()
            
            st.write("---")
            st.subheader("Entrega de Pozo")
            todos_pagaron = all(p['completado'] or p == beneficiario_actual for p in participantes)
            
            if beneficiario_actual:
                if todos_pagaron:
                    st.success(f"¡Todos han pagado! Ya puedes entregar el pozo a **{beneficiario_actual['nombre_usuario']}**.")
                    if st.button(f"🎁 ENTREGAR POZO A {beneficiario_actual['nombre_usuario']} y pasar al siguiente mes"):
                        supabase.table("participantes").update({"completado": True}).eq("id", beneficiario_actual['id']).execute()
                        st.rerun()
                else:
                    st.warning("Faltan miembros por pagar su cuota para cerrar este periodo.")
            
            st.write("---")
            if st.button("♻️ Reiniciar Ciclo (Borrar todo)"):
                supabase.table("participantes").update({"completado": False, "aviso_pago": False}).eq("grupo_id", st.session_state.grupo_id).execute()
                st.rerun()
