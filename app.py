import streamlit as st
import pandas as pd
from supabase import create_client, Client
import random
import string
from datetime import datetime, date, timedelta
import calendar

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

def calcular_fecha_periodo(fecha_inicio, indice, frecuencia):
    if frecuencia == "mensual":
        meses = (fecha_inicio.month + indice - 1) % 12 + 1
        anios = fecha_inicio.year + (fecha_inicio.month + indice - 1) // 12
        dia = fecha_inicio.day
        try:
            return date(anios, meses, dia)
        except ValueError:
            ultimo_dia = calendar.monthrange(anios, meses)[1]
            return date(anios, meses, ultimo_dia)
    elif frecuencia == "quincenal":
        return fecha_inicio + timedelta(days=indice * 15)
    else:  # semanal
        return fecha_inicio + timedelta(days=indice * 7)

# FUNCIONES DE APOYO PARA LOGICA DE PERIODOS
def ha_pagado_periodo(p_data, idx_periodo):
    pagos = str(p_data.get('periodos_pagados', "")).split(",")
    return str(idx_periodo) in pagos

def ha_avisado_periodo(p_data, idx_periodo):
    avisos = str(p_data.get('periodos_avisados', "")).split(",")
    return str(idx_periodo) in avisos

# 3. ESTILO
st.markdown("""
    <style>
    .stButton>button { border-radius: 20px; width: 100%; }
    .info-card { background-color: #f8f9fa; padding: 15px; border-radius: 15px; border-left: 5px solid #1a73e8; margin-bottom: 20px; }
    .member-card { background-color: #ffffff; padding: 12px; border-radius: 12px; border: 1px solid #e0e0e0; margin-bottom: 10px; }
    .status-badge { padding: 2px 8px; border-radius: 5px; font-size: 0.8em; font-weight: bold; }
    .pago-si { background-color: #d4edda; color: #155724; }
    .pago-no { background-color: #fff3cd; color: #856404; }
    .danger-zone { border: 1px solid #ff4b4b; padding: 15px; border-radius: 10px; margin-top: 20px; }
    [data-testid="stSidebarNav"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

st.title("🤝 PactaLoopa")

if "grupo_id" not in st.session_state:
    st.session_state.update({"grupo_id": None, "vista": "inicio", "mi_nombre": "", "mostrar_exito": False, "nuevo_codigo": "", "periodo_seleccionado": None})

# --- DIÁLOGO DE ÉXITO ---
@st.dialog("🚀 ¡Pacto Creado con Éxito!")
def mostrar_credenciales_nuevas(codigo, password):
    st.write("Comparte estos datos con tu grupo:")
    st.code(f"Código: {codigo}", language=None)
    st.write("Solo tú (Admin) necesitas la contraseña para gestionar el grupo.")
    st.code(f"Contraseña Admin: {password}", language=None)
    if st.button("Entrar al Dashboard"):
        st.session_state.mostrar_exito = False
        st.rerun()

if st.session_state.mostrar_exito:
    mostrar_credenciales_nuevas(st.session_state.nuevo_codigo, st.session_state.nueva_pass)

# --- NAVEGACIÓN ---
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
    monto = st.number_input("Cuota Mensual ($)", min_value=1, value=100)
    frecuencia = st.selectbox("Frecuencia", ["Semanal", "Quincenal", "Mensual"])
    fecha_inicio = st.date_input("Fecha primer pozo", value=date.today())
    pass_pacto = st.text_input("Contraseña del administrador", type="password")
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
            supabase.table("participantes").insert({
                "grupo_id": gid, "nombre_usuario": tu_nombre, 
                "posicion_orden": 0, "recibio_pozo": False
            }).execute()
            st.session_state.update({"grupo_id": gid, "mi_nombre": tu_nombre, "vista": "dashboard", "mostrar_exito": True, "nuevo_codigo": codigo, "nueva_pass": pass_pacto})
            st.rerun()

elif st.session_state.vista == "unirse":
    if st.button("⬅️ Volver"): st.session_state.vista = "inicio"; st.rerun()
    c_in = st.text_input("Código de Grupo").upper().strip()
    if st.button("Buscar Grupo"):
        g = supabase.table("grupos").select("*").eq("codigo", c_in).execute()
        if g.data:
            st.session_state.grupo_id = g.data[0]['id']
            st.session_state.vista = "seleccionar_usuario"; st.rerun()
        else: st.error("Código no encontrado.")

elif st.session_state.vista == "seleccionar_usuario":
    p_db = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).execute()
    g_db = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    grupo = g_db.data[0]
    nombres = [p['nombre_usuario'] for p in p_db.data]
    admin_data = min(p_db.data, key=lambda x: x['id']) if p_db.data else None
    admin_nombre = admin_data['nombre_usuario'] if admin_data else ""

    opciones = ["-- Seleccionar --"]
    if grupo.get('abierto', True): opciones.append("-- Nuevo Miembro --")
    opciones.extend(nombres)
    
    sel = st.selectbox("¿Quién eres?", opciones)
    
    if sel == "-- Nuevo Miembro --":
        nuevo = st.text_input("Tu nombre").strip()
        if st.button("Unirme") and nuevo:
            max_pos = max([p['posicion_orden'] for p in p_db.data]) if p_db.data else -1
            supabase.table("participantes").insert({"grupo_id": st.session_state.grupo_id, "nombre_usuario": nuevo, "posicion_orden": max_pos + 1, "recibio_pozo": False}).execute()
            st.session_state.mi_nombre = nuevo; st.session_state.vista = "dashboard"; st.rerun()
    elif sel != "-- Seleccionar --":
        if sel == admin_nombre:
            pass_check = st.text_input("Contraseña de Administrador", type="password")
            if st.button("Acceder como Admin"):
                if pass_check == grupo['password']:
                    st.session_state.mi_nombre = sel; st.session_state.vista = "dashboard"; st.rerun()
                else: st.error("Contraseña incorrecta.")
        else:
            if st.button(f"Entrar como {sel}"):
                st.session_state.mi_nombre = sel; st.session_state.vista = "dashboard"; st.rerun()

# --- DASHBOARD ---
elif st.session_state.vista == "dashboard":
    g_res = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    if not g_res.data: st.session_state.update({"grupo_id": None, "vista": "inicio"}); st.rerun()
    grupo = g_res.data[0]
    p_res = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
    participantes = p_res.data
    admin_data = min(participantes, key=lambda x: x['id']) if participantes else None
    admin_nombre = admin_data['nombre_usuario'] if admin_data else ""
    es_admin = (st.session_state.mi_nombre == admin_nombre)
    yo = next((p for p in participantes if p['nombre_usuario'] == st.session_state.mi_nombre), None)
    f_inicio_dt = date.fromisoformat(grupo['fecha_inicio'])
    
    if st.session_state.periodo_seleccionado is None:
        hoy = date.today()
        periodo_actual = 0
        menor_dif = float('inf')
        for i in range(len(participantes)):
            f_p = calcular_fecha_periodo(f_inicio_dt, i, grupo['frecuencia'])
            dif = abs((f_p - hoy).days)
            if dif < menor_dif:
                menor_dif = dif
                periodo_actual = i
        st.session_state.periodo_seleccionado = periodo_actual

    with st.sidebar:
        st.write(f"### 👤 {st.session_state.mi_nombre}")
        st.caption("PactaLoopa v2.0")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio", "periodo_seleccionado": None})
            st.rerun()

    opciones_periodo = []
    for i, p in enumerate(participantes):
        f_p = calcular_fecha_periodo(f_inicio_dt, i, grupo['frecuencia'])
        opciones_periodo.append(f"P{i+1}: {p['nombre_usuario']} ({f_p.strftime('%d/%m')})")
    
    st.write(f"### 🛡️ {grupo['nombre']}")
    idx_p = st.selectbox("Seleccionar Periodo", range(len(opciones_periodo)), format_func=lambda x: opciones_periodo[x], index=st.session_state.periodo_seleccionado)
    st.session_state.periodo_seleccionado = idx_p

    beneficiario_p = participantes[idx_p]
    fecha_p = calcular_fecha_periodo(f_inicio_dt, idx_p, grupo['frecuencia'])
    dias_restantes = (fecha_p - date.today()).days
    txt_restantes = f"{dias_restantes} días" if dias_restantes > 0 else "¡Hoy!" if dias_restantes == 0 else "Finalizado"

    t1, t2, t3 = st.tabs(["🔄 El Loop", "💰 Reportar Pago", "⚙️ Admin" if es_admin else "ℹ️ Info"])

    with t1:
        st.subheader(f"Periodo {idx_p + 1}")
        st.markdown(f"""
        <div class="info-card">
            👤 <b>Recibe Pozo:</b> {beneficiario_p['nombre_usuario']}<br>
            🗓️ <b>Fecha Estimada:</b> {fecha_p.strftime('%d de %B de %Y')}<br>
            ⏳ <b>Faltan:</b> {txt_restantes}<br>
            💰 <b>Monto Pozo:</b> ${grupo['monto_cuota'] * (len(participantes)-1)}
        </div>
        """, unsafe_allow_html=True)
        
        for p in participantes:
            col_u, col_p = st.columns([2, 1])
            with col_u: st.write(f"{'🎁 ' if p == beneficiario_p else '👤 '}{p['nombre_usuario']}")
            with col_p:
                if p == beneficiario_p: st.caption("Beneficiario")
                else:
                    pagado = ha_pagado_periodo(p, idx_p)
                    status = "PAGADO" if pagado else "PENDIENTE"
                    clase = "pago-si" if pagado else "pago-no"
                    st.markdown(f"<span class='status-badge {clase}'>{status}</span>", unsafe_allow_html=True)

    with t2:
        st.subheader(f"Tu pago para el Periodo {idx_p + 1}")
        if yo:
            if yo['nombre_usuario'] == beneficiario_p['nombre_usuario']:
                st.success("En este periodo tú recibes el pozo. No debes reportar pago.")
            else:
                pagado = ha_pagado_periodo(yo, idx_p)
                avisado = ha_avisado_periodo(yo, idx_p)
                hoy = date.today()
                ultimo_dia_mes_actual = date(hoy.year, hoy.month, calendar.monthrange(hoy.year, hoy.month)[1])
                es_futuro = fecha_p > ultimo_dia_mes_actual

                if pagado: 
                    st.success("✅ Tu cuota ya está marcada como pagada para este periodo.")
                elif avisado:
                    st.warning("🔔 Pago reportado. Esperando validación.")
                    if st.button("Cancelar Reporte"):
                        avisos = str(yo.get('periodos_avisados', "")).split(",")
                        if str(idx_p) in avisos: avisos.remove(str(idx_p))
                        supabase.table("participantes").update({"periodos_avisados": ",".join(filter(None, avisos))}).eq("id", yo['id']).execute(); st.rerun()
                elif es_futuro:
                    st.info(f"📅 El reporte para este periodo se activará en **{fecha_p.strftime('%B')}**.")
                    st.button("📢 INFORMAR QUE YA PAGUÉ", disabled=True)
                else:
                    st.info(f"Monto: **${grupo['monto_cuota']}**")
                    if st.button("📢 INFORMAR QUE YA PAGUÉ"):
                        avisos = str(yo.get('periodos_avisados', "")).split(",")
                        if str(idx_p) not in avisos: avisos.append(str(idx_p))
                        supabase.table("participantes").update({"periodos_avisados": ",".join(filter(None, avisos))}).eq("id", yo['id']).execute(); st.rerun()

    with t3:
        if es_admin:
            st.subheader("🔑 Credenciales del Grupo")
            st.code(f"Código: {grupo['codigo']}\nContraseña: {grupo['password']}", language=None)
            st.write("---")
            
            # --- MEJORA 1: CONTROL DE PAGOS PRIMERO ---
            st.subheader(f"✅ Control de Pagos Periodo {idx_p + 1}")
            avisos_periodo = [p for p in participantes if ha_avisado_periodo(p, idx_p)]
            if avisos_periodo:
                for a in avisos_periodo:
                    if st.button(f"Confirmar pago de {a['nombre_usuario']}", key=f"conf_{a['id']}"):
                        avisos = str(a.get('periodos_avisados', "")).split(",")
                        pagos = str(a.get('periodos_pagados', "")).split(",")
                        if str(idx_p) in avisos: avisos.remove(str(idx_p))
                        if str(idx_p) not in pagos: pagos.append(str(idx_p))
                        supabase.table("participantes").update({
                            "periodos_avisados": ",".join(filter(None, avisos)),
                            "periodos_pagados": ",".join(filter(None, pagos))
                        }).eq("id", a['id']).execute(); st.rerun()
            
            pagados_periodo = [p for p in participantes if ha_pagado_periodo(p, idx_p)]
            if pagados_periodo:
                st.caption("Pagos ya confirmados:")
                for p_conf in pagados_periodo:
                    col_txt, col_btn = st.columns([2, 1])
                    col_txt.write(f"✓ {p_conf['nombre_usuario']}")
                    if col_btn.button("Anular", key=f"rev_{p_conf['id']}", type="secondary"):
                        pagos = str(p_conf.get('periodos_pagados', "")).split(",")
                        if str(idx_p) in pagos: pagos.remove(str(idx_p))
                        supabase.table("participantes").update({"periodos_pagados": ",".join(filter(None, pagos))}).eq("id", p_conf['id']).execute(); st.rerun()
            
            if not avisos_periodo and not pagados_periodo: st.caption("Sin actividad en este periodo.")
            st.write("---")

            # --- MEJORA 2: GESTIÓN DE MIEMBROS MÓVIL ---
            st.subheader("👥 Gestión de Miembros")
            for i, p in enumerate(participantes):
                with st.container():
                    st.markdown(f'<div class="member-card">', unsafe_allow_html=True)
                    st.write(f"**{i+1}. {p['nombre_usuario']}**")
                    c1, c2, c3 = st.columns(3)
                    if i > 0:
                        if c1.button("↑ Subir", key=f"up_{p['id']}"):
                            supabase.table("participantes").update({"posicion_orden": i-1}).eq("id", p['id']).execute()
                            supabase.table("participantes").update({"posicion_orden": i}).eq("id", participantes[i-1]['id']).execute()
                            st.rerun()
                    if i < len(participantes)-1:
                        if c2.button("↓ Bajar", key=f"dw_{p['id']}"):
                            supabase.table("participantes").update({"posicion_orden": i+1}).eq("id", p['id']).execute()
                            supabase.table("participantes").update({"posicion_orden": i}).eq("id", participantes[i+1]['id']).execute()
                            st.rerun()
                    if p['nombre_usuario'] != st.session_state.mi_nombre:
                        if c3.button("❌ Borrar", key=f"del_{p['id']}"):
                            supabase.table("participantes").delete().eq("id", p['id']).execute(); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="danger-zone">', unsafe_allow_html=True)
            if st.button("ELIMINAR TODO EL LOOP"):
                supabase.table("participantes").delete().eq("grupo_id", st.session_state.grupo_id).execute()
                supabase.table("grupos").delete().eq("id", st.session_state.grupo_id).execute()
                st.session_state.update({"grupo_id": None, "vista": "inicio"}); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.subheader("ℹ️ Info del Pacto")
            st.write(f"**Código:** {grupo['codigo']}\n**Frecuencia:** {grupo['frecuencia'].capitalize()}\n**Inicio:** {grupo['fecha_inicio']}")
