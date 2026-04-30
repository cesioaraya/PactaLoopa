import streamlit as st
import pandas as pd
from supabase import create_client, Client
import random
import string
from datetime import datetime, date, timedelta
import calendar
import urllib.parse 

# 1. CONFIGURACIÓN
st.set_page_config(page_title="PactaLoopa", page_icon="🤝", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    .stButton>button { border-radius: 20px; width: 100%; }
    .info-card { background-color: #f8f9fa; padding: 15px; border-radius: 15px; border-left: 5px solid #1a73e8; margin-bottom: 20px; }
    .member-card { background-color: #ffffff; padding: 12px; border-radius: 12px; border: 1px solid #e0e0e0; margin-bottom: 10px; }
    .status-badge { padding: 2px 8px; border-radius: 5px; font-size: 0.8em; font-weight: bold; }
    .pago-si { background-color: #d4edda; color: #155724; }
    .pago-no { background-color: #fff3cd; color: #856404; }
    </style>
    """, unsafe_allow_html=True)

# --- DICCIONARIO DE IDIOMAS (Simplificado para brevedad, mantén los tuyos) ---
LANGS = {
    "Español": {
        "crear": "✨ Crear Nuevo Pacto", "unirse": "🤝 Entrar a un Pacto", "volver": "⬅️ Volver",
        "nombre_pacto": "Nombre del Pacto", "cuota": "Cuota ($)", "frecuencia": "Frecuencia",
        "primer_pozo": "Primer pozo", "tu_nombre": "Tu nombre", "btn_crear": "Crear Pacto",
        "buscar": "Buscar Pacto", "quien_eres": "¿Quién eres?", "nuevo_miembro": "-- Nuevo Miembro --",
        "seleccionar": "-- Seleccionar --", "btn_unirme": "Unirme", "pass_admin_label": "Contraseña (Solo Administrador)",
        "btn_entrar": "Entrar al Dashboard", "usuario": "Usuario", "salir": "🚪 Salir",
        "recibe": "Recibe Pozo", "fecha_est": "Fecha Estimada", "estado": "Estado", "pozo_total": "Pozo Total",
        "activo": "¡Periodo Activo!", "faltan": "Faltan", "dias": "días", "ya_pague": "📢 YA PAGUÉ",
        "admin_tag": "Admin", "tab_loop": "🔄 El Loop", "tab_pago": "💰 Mi Pago", "tab_gestion": "⚙️ Gestión", "tab_info": "ℹ️ Info"
    },
    "English": {
        "crear": "✨ Create New Pact", "unirse": "🤝 Join a Pact", "volver": "⬅️ Back",
        "nombre_pacto": "Pact Name", "cuota": "Fee ($)", "frecuencia": "Frequency",
        "primer_pozo": "First Pool Date", "tu_nombre": "Your Name", "btn_crear": "Create Pact",
        "buscar": "Search Pact", "quien_eres": "Who are you?", "nuevo_miembro": "-- New Member --",
        "seleccionar": "-- Select --", "btn_unirme": "Join", "pass_admin_label": "Password (Admin Only)",
        "btn_entrar": "Enter Dashboard", "usuario": "User", "salir": "🚪 Logout",
        "recibe": "Receives Pool", "fecha_est": "Estimated Date", "estado": "Status", "pozo_total": "Total Pool",
        "activo": "Period Active!", "faltan": "Missing", "dias": "days", "ya_pague": "📢 I'VE PAID",
        "admin_tag": "Admin", "tab_loop": "🔄 The Loop", "tab_pago": "💰 My Payment", "tab_gestion": "⚙️ Manage", "tab_info": "ℹ️ Info"
    }
}

# 2. INICIALIZACIÓN DE ESTADO
if "grupo_id" not in st.session_state:
    query_params = st.query_params
    init_grupo = query_params.get("g", None)
    st.session_state.update({
        "grupo_id": init_grupo, 
        "vista": "inicio" if not init_grupo else "seleccionar_usuario", 
        "mi_nombre": "", 
        "mostrar_exito": False, 
        "nuevo_codigo": "", 
        "periodo_seleccionado": None,
        "es_admin": False,
        "lang": "Español"
    })

# 3. LÓGICA DE IDIOMA
header_col1, header_col2 = st.columns([3, 1])
with header_col2:
    st.session_state.lang = st.selectbox("🌐", list(LANGS.keys()), index=list(LANGS.keys()).index(st.session_state.lang), label_visibility="collapsed")
T = LANGS.get(st.session_state.lang, LANGS["Español"])

# 4. CONEXIÓN SUPABASE
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"].strip().replace("/rest/v1/", "").rstrip("/")
        key = st.secrets["SUPABASE_KEY"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error de conexión. Verifica secrets.")
        return None

supabase = init_connection()

# 5. FUNCIONES DE APOYO
def generar_codigo():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def calcular_fecha_periodo(fecha_inicio, indice, frecuencia):
    if frecuencia == "mensual":
        meses = (fecha_inicio.month + indice - 1) % 12 + 1
        anios = fecha_inicio.year + (fecha_inicio.month + indice - 1) // 12
        dia = min(fecha_inicio.day, calendar.monthrange(anios, meses)[1])
        return date(anios, meses, dia)
    elif frecuencia == "quincenal": return fecha_inicio + timedelta(days=indice * 15)
    else: return fecha_inicio + timedelta(days=indice * 7)

def ha_pagado_periodo(p_data, idx_periodo):
    return str(idx_periodo) in str(p_data.get('periodos_pagados', "")).split(",")

def ha_avisado_periodo(p_data, idx_periodo):
    return str(idx_periodo) in str(p_data.get('periodos_avisados', "")).split(",")

# 6. DIÁLOGOS
@st.dialog("🚀 ¡Pacto Creado!")
def mostrar_exito(codigo, password):
    st.write("Comparte el código con los miembros. Guarda tu contraseña de Admin.")
    st.code(f"Código: {codigo}\nPass Admin: {password}", language=None)
    if st.button("Ir al Dashboard"):
        st.session_state.mostrar_exito = False
        st.rerun()

@st.dialog("⚠️ ELIMINAR TODO")
def confirmar_borrado_total(grupo_id, pass_real):
    st.warning("Esta acción borrará a todos los miembros y el historial.")
    confirmacion = st.text_input("Escribe 'ELIMINAR'")
    pass_check = st.text_input("Contraseña Admin", type="password")
    if st.button("Confirmar", type="primary"):
        if confirmacion == "ELIMINAR" and pass_check == pass_real:
            supabase.table("participantes").delete().eq("grupo_id", grupo_id).execute()
            supabase.table("grupos").delete().eq("id", grupo_id).execute()
            st.query_params.clear()
            st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio"})
            st.rerun()

# 7. NAVEGACIÓN
st.title("🤝 PactaLoopa")

if st.session_state.vista == "inicio":
    col1, col2 = st.columns(2)
    if col1.button(T["crear"]): st.session_state.vista = "crear"; st.rerun()
    if col2.button(T["unirse"]): st.session_state.vista = "unirse"; st.rerun()

elif st.session_state.vista == "crear":
    if st.button(T["volver"]): st.session_state.vista = "inicio"; st.rerun()
    nombre = st.text_input(T["nombre_pacto"])
    monto = st.number_input(T["cuota"], min_value=1, value=100)
    frecuencia = st.selectbox(T["frecuencia"], ["Semanal", "Quincenal", "Mensual"])
    fecha_inicio = st.date_input(T["primer_pozo"], value=date.today())
    pwd = st.text_input("Pass Admin", type="password")
    admin_n = st.text_input(T["tu_nombre"]).strip()
    
    if st.button(T["btn_crear"]) and nombre and admin_n and pwd:
        cod = generar_codigo()
        res = supabase.table("grupos").insert({"nombre": nombre, "monto_cuota": monto, "frecuencia": frecuencia.lower(), "fecha_inicio": fecha_inicio.isoformat(), "codigo": cod, "password": pwd}).execute()
        gid = res.data[0]['id']
        supabase.table("participantes").insert({"grupo_id": gid, "nombre_usuario": admin_n, "posicion_orden": 0}).execute()
        st.query_params["g"] = gid
        st.session_state.update({"grupo_id": gid, "mi_nombre": admin_n, "vista": "dashboard", "nuevo_codigo": cod, "nueva_pass": pwd, "mostrar_exito": True, "es_admin": True})
        st.rerun()

elif st.session_state.vista == "unirse":
    if st.button(T["volver"]): st.session_state.vista = "inicio"; st.rerun()
    c_in = st.text_input("Código del Pacto").upper().strip()
    if st.button(T["buscar"]) and c_in:
        g = supabase.table("grupos").select("*").eq("codigo", c_in).execute()
        if g.data:
            st.query_params["g"] = g.data[0]['id']
            st.session_state.update({"grupo_id": g.data[0]['id'], "vista": "seleccionar_usuario"})
            st.rerun()
        else: st.error("Código no válido.")

elif st.session_state.vista == "seleccionar_usuario":
    p_db = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).execute()
    g_db = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    if not g_db.data: st.session_state.vista = "inicio"; st.rerun()
    
    grupo = g_db.data[0]
    nombres = [p['nombre_usuario'] for p in p_db.data]
    sel = st.selectbox(T["quien_eres"], [T["seleccionar"], T["nuevo_miembro"]] + nombres)
    
    if sel == T["nuevo_miembro"]:
        n = st.text_input(T["tu_nombre"]).strip()
        if st.button(T["btn_unirme"]) and n:
            max_p = max([p['posicion_orden'] for p in p_db.data]) if p_db.data else -1
            supabase.table("participantes").insert({"grupo_id": st.session_state.grupo_id, "nombre_usuario": n, "posicion_orden": max_p + 1}).execute()
            st.session_state.update({"mi_nombre": n, "vista": "dashboard", "es_admin": False}); st.rerun()
    elif sel != T["seleccionar"]:
        p_check = st.text_input(T["pass_admin_label"], type="password", help="Opcional para miembros")
        if st.button(T["btn_entrar"]):
            is_adm = (p_check == grupo['password']) and p_check != ""
            st.session_state.update({"mi_nombre": sel, "vista": "dashboard", "es_admin": is_adm}); st.rerun()

elif st.session_state.vista == "dashboard":
    if st.session_state.mostrar_exito: mostrar_exito(st.session_state.nuevo_codigo, st.session_state.nueva_pass)

    g_res = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    p_res = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
    
    if not g_res.data: st.session_state.vista = "inicio"; st.rerun()
    
    grupo, participantes = g_res.data[0], p_res.data
    yo = next((p for p in participantes if p['nombre_usuario'] == st.session_state.mi_nombre), None)
    f_inicio_dt = date.fromisoformat(grupo['fecha_inicio'])

    # Header Dashboard
    c1, c2 = st.columns([3, 1])
    c1.subheader(f"🏠 {grupo['nombre']}")
    if c2.button(T["salir"]):
        st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio", "periodo_seleccionado": None, "es_admin": False})
        st.rerun()

    # Selector de Periodo
    hoy = date.today()
    if st.session_state.periodo_seleccionado is None:
        st.session_state.periodo_seleccionado = 0 # Default al primero si no hay cálculo

    opciones = [f"P{i+1}: {p['nombre_usuario']}" for i, p in enumerate(participantes)]
    if opciones:
        idx_p = st.selectbox("Seleccionar Periodo", range(len(opciones)), format_func=lambda x: opciones[x], index=min(st.session_state.periodo_seleccionado, len(opciones)-1))
    else:
        st.info("Esperando miembros...")
        st.stop()

    t1, t2, t3 = st.tabs([T["tab_loop"], T["tab_pago"], T["tab_gestion"] if st.session_state.es_admin else T["tab_info"]])

    with t1:
        benef = participantes[idx_p]
        f_p = calcular_fecha_periodo(f_inicio_dt, idx_p, grupo['frecuencia'])
        dias = (f_p - hoy).days
        st.markdown(f"""<div class="info-card">
            👤 <b>{T['recibe']}:</b> {benef['nombre_usuario']}<br>
            🗓️ <b>{T['fecha_est']}:</b> {f_p.strftime('%d/%m/%Y')}<br>
            ⏳ <b>{T['estado']}:</b> {T['activo'] if dias <= 0 else f"{T['faltan']} {dias} {T['dias']}"}<br>
            💰 <b>{T['pozo_total']}:</b> ${grupo['monto_cuota'] * len(participantes)}
        </div>""", unsafe_allow_html=True)

        for p in participantes:
            col_a, col_b = st.columns([3, 1])
            col_a.write(f"{'🎁' if p == benef else '👤'} {p['nombre_usuario']}")
            if p != benef:
                pagado = ha_pagado_periodo(p, idx_p)
                col_b.markdown(f"<span class='status-badge {'pago-si' if pagado else 'pago-no'}'>{'Pago' if pagado else 'Sin Pago'}</span>", unsafe_allow_html=True)

    with t2:
        if yo:
            if yo['nombre_usuario'] == participantes[idx_p]['nombre_usuario']:
                st.success("✨ ¡Este periodo recibes tú!")
            elif ha_pagado_periodo(yo, idx_p): st.success("✅ Pago confirmado.")
            elif ha_avisado_periodo(yo, idx_p): st.warning("🔔 Esperando validación.")
            else:
                st.write(f"Monto a pagar: **${grupo['monto_cuota']}**")
                if st.button(T["ya_pague"]):
                    avisos = str(yo.get('periodos_avisados', "")).split(",")
                    if str(idx_p) not in avisos:
                        avisos.append(str(idx_p))
                        supabase.table("participantes").update({"periodos_avisados": ",".join(filter(None, avisos))}).eq("id", yo['id']).execute()
                        st.rerun()

    with t3:
        if st.session_state.es_admin:
            st.subheader("Validar Avisos")
            for p in [p for p in participantes if ha_avisado_periodo(p, idx_p)]:
                if st.button(f"Confirmar {p['nombre_usuario']}"):
                    avisos = str(p.get('periodos_avisados', "")).split(",")
                    pagos = str(p.get('periodos_pagados', "")).split(",")
                    if str(idx_p) in avisos: avisos.remove(str(idx_p))
                    if str(idx_p) not in pagos: pagos.append(str(idx_p))
                    supabase.table("participantes").update({"periodos_avisados": ",".join(filter(None, avisos)), "periodos_pagados": ",".join(filter(None, pagos))}).eq("id", p['id']).execute()
                    st.rerun()
            
            st.write("---")
            st.subheader("Reordenar Loop")
            for i, p in enumerate(participantes):
                col1, col2, col3, col4 = st.columns([2,1,1,1])
                col1.write(f"{i+1}. {p['nombre_usuario']}")
                if i > 0 and col2.button("↑", key=f"up{p['id']}"):
                    supabase.table("participantes").update({"posicion_orden": i-1}).eq("id", p['id']).execute()
                    supabase.table("participantes").update({"posicion_orden": i}).eq("id", participantes[i-1]['id']).execute()
                    st.rerun()
                if i < len(participantes)-1 and col3.button("↓", key=f"dw{p['id']}"):
                    supabase.table("participantes").update({"posicion_orden": i+1}).eq("id", p['id']).execute()
                    supabase.table("participantes").update({"posicion_orden": i}).eq("id", participantes[i+1]['id']).execute()
                    st.rerun()
                if p['nombre_usuario'] != st.session_state.mi_nombre and col4.button("❌", key=f"del{p['id']}"):
                    supabase.table("participantes").delete().eq("id", p['id']).execute(); st.rerun()
            
            if st.button("🗑️ ELIMINAR PACTO"): confirmar_borrado_total(st.session_state.grupo_id, grupo['password'])
        else:
            st.info(f"Código para invitar: `{grupo['codigo']}`")
            st.write(f"Cuota: ${grupo['monto_cuota']}")

# 8. FOOTER
st.markdown("---")
st.markdown("<div style='text-align: center;'><a href='https://ko-fi.com/cesioaraya' target='_blank'><img height='36' src='https://storage.ko-fi.com/cdn/kofi2.png?v=3' border='0' alt='Buy Me a Coffee' /></a></div>", unsafe_allow_html=True)
