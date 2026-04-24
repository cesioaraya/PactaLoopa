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

if "grupo_id" not in st.session_state:
    st.session_state.update({
        "grupo_id": None, 
        "vista": "inicio", 
        "mi_nombre": "", 
        "mostrar_exito": False, 
        "nuevo_codigo": "", 
        "periodo_seleccionado": None,
        "es_admin": False
    })

def generar_codigo():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def calcular_fecha_periodo(fecha_inicio, indice, frecuencia):
    if frecuencia == "mensual":
        meses = (fecha_inicio.month + indice - 1) % 12 + 1
        anios = fecha_inicio.year + (fecha_inicio.month + indice - 1) // 12
        dia = fecha_inicio.day
        try: return date(anios, meses, dia)
        except ValueError: return date(anios, meses, calendar.monthrange(anios, meses)[1])
    elif frecuencia == "quincenal": return fecha_inicio + timedelta(days=indice * 15)
    else: return fecha_inicio + timedelta(days=indice * 7)

def ha_pagado_periodo(p_data, idx_periodo):
    return str(idx_periodo) in str(p_data.get('periodos_pagados', "")).split(",")

def ha_avisado_periodo(p_data, idx_periodo):
    return str(idx_periodo) in str(p_data.get('periodos_avisados', "")).split(",")

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton>button { border-radius: 20px; width: 100%; }
    .info-card { background-color: #f8f9fa; padding: 15px; border-radius: 15px; border-left: 5px solid #1a73e8; margin-bottom: 20px; }
    .member-card { background-color: #ffffff; padding: 12px; border-radius: 12px; border: 1px solid #e0e0e0; margin-bottom: 10px; }
    .status-badge { padding: 2px 8px; border-radius: 5px; font-size: 0.8em; font-weight: bold; }
    .pago-si { background-color: #d4edda; color: #155724; }
    .pago-no { background-color: #fff3cd; color: #856404; }
    .danger-zone { border: 1px solid #ff4b4b; padding: 15px; border-radius: 10px; margin-top: 20px; background-color: #fff5f5; }
    </style>
    """, unsafe_allow_html=True)

# --- DIÁLOGOS ---
@st.dialog("🚀 ¡Pacto Creado!")
def mostrar_exito(codigo, password):
    st.write("Comparte los datos. Solo tú necesitas la contraseña.")
    st.code(f"Código: {codigo}\nPass Admin: {password}", language=None)
    if st.button("Ir al Dashboard"):
        st.session_state.mostrar_exito = False
        st.rerun()

@st.dialog("⚠️ ELIMINAR TODO EL LOOP")
def confirmar_borrado_total(grupo_id, pass_real):
    st.warning("Esta acción es irreversible.")
    confirmacion = st.text_input("Escribe 'ELIMINAR' para confirmar")
    pass_check = st.text_input("Contraseña de Administrador", type="password")
    if st.button("Confirmar Destrucción Total", type="primary"):
        if confirmacion == "ELIMINAR" and pass_check == pass_real:
            supabase.table("participantes").delete().eq("grupo_id", grupo_id).execute()
            supabase.table("grupos").delete().eq("id", grupo_id).execute()
            st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio"})
            st.rerun()
        else: st.error("Validación incorrecta.")

# --- NAVEGACIÓN ---
st.title("🤝 PactaLoopa")

if st.session_state.vista == "inicio":
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✨ Crear Nuevo Pacto"): st.session_state.vista = "crear"; st.rerun()
    with col2:
        if st.button("🤝 Entrar a un Pacto"): st.session_state.vista = "unirse"; st.rerun()

elif st.session_state.vista == "crear":
    if st.button("⬅️"): st.session_state.vista = "inicio"; st.rerun()
    nombre = st.text_input("Nombre del Pacto")
    monto = st.number_input("Cuota ($)", min_value=1, value=100)
    frecuencia = st.selectbox("Frecuencia", ["Semanal", "Quincenal", "Mensual"])
    fecha_inicio = st.date_input("Primer pozo", value=date.today())
    pwd = st.text_input("Pass Admin", type="password")
    admin_n = st.text_input("Tu nombre").strip()
    
    if st.button("Crear"):
        if nombre and admin_n and pwd:
            cod = generar_codigo()
            res = supabase.table("grupos").insert({"nombre": nombre, "monto_cuota": monto, "frecuencia": frecuencia.lower(), "fecha_inicio": fecha_inicio.isoformat(), "codigo": cod, "password": pwd, "abierto": True}).execute()
            gid = res.data[0]['id']
            # Se asigna posición 999 para que el admin sea el último por defecto, pero se puede editar después
            supabase.table("participantes").insert({"grupo_id": gid, "nombre_usuario": admin_n, "posicion_orden": 999}).execute()
            st.session_state.update({"grupo_id": gid, "mi_nombre": admin_n, "vista": "dashboard", "nuevo_codigo": cod, "nueva_pass": pwd, "mostrar_exito": True, "es_admin": True})
            st.rerun()

elif st.session_state.vista == "unirse":
    if st.button("⬅️"): st.session_state.vista = "inicio"; st.rerun()
    c_in = st.text_input("Código").upper().strip()
    if st.button("Buscar"):
        g = supabase.table("grupos").select("*").eq("codigo", c_in).execute()
        if g.data:
            st.session_state.grupo_id = g.data[0]['id']
            st.session_state.vista = "seleccionar_usuario"; st.rerun()
        else: st.error("No existe.")

elif st.session_state.vista == "seleccionar_usuario":
    p_db = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).execute()
    g_db = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    grupo = g_db.data[0]
    nombres = [p['nombre_usuario'] for p in p_db.data]
    
    # El admin es quien conoce la contraseña, lo identificamos por la tabla grupos
    sel = st.selectbox("¿Quién eres?", ["-- Seleccionar --", "-- Nuevo Miembro --"] + nombres)
    if sel == "-- Nuevo Miembro --":
        n = st.text_input("Nombre").strip()
        if st.button("Unirme") and n:
            max_p = max([p['posicion_orden'] for p in p_db.data]) if p_db.data else -1
            # Los nuevos se agregan después del último, el admin seguirá estando al final si su posición es 999
            supabase.table("participantes").insert({"grupo_id": st.session_state.grupo_id, "nombre_usuario": n, "posicion_orden": max_p + 1}).execute()
            st.session_state.update({"mi_nombre": n, "vista": "dashboard", "es_admin": False}); st.rerun()
    elif sel != "-- Seleccionar --":
        p_check = st.text_input("Pass Admin (Solo si eres el creador)", type="password")
        if st.button("Entrar"):
            if p_check == grupo['password']:
                st.session_state.update({"mi_nombre": sel, "vista": "dashboard", "es_admin": True}); st.rerun()
            elif not p_check:
                st.session_state.update({"mi_nombre": sel, "vista": "dashboard", "es_admin": False}); st.rerun()
            else: st.error("Contraseña incorrecta.")

# --- DASHBOARD ---
elif st.session_state.vista == "dashboard":
    if st.session_state.mostrar_exito:
        mostrar_exito(st.session_state.nuevo_codigo, st.session_state.nueva_pass)

    g_res = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    if not g_res.data: st.session_state.update({"grupo_id": None, "vista": "inicio"}); st.rerun()
    grupo = g_res.data[0]
    
    # Obtenemos participantes ordenados
    p_res = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
    participantes = p_res.data
    yo = next((p for p in participantes if p['nombre_usuario'] == st.session_state.mi_nombre), None)
    f_inicio_dt = date.fromisoformat(grupo['fecha_inicio'])

    with st.sidebar:
        st.write(f"### 👤 {st.session_state.mi_nombre}")
        if st.button("🚪 Salir"):
            st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio", "periodo_seleccionado": None}); st.rerun()

    st.write(f"### 🛡️ {grupo['nombre']}")
    
    opciones = [f"P{i+1}: {p['nombre_usuario']}" for i, p in enumerate(participantes)]
    if not opciones:
        st.info("Esperando a que se unan miembros...")
        st.stop()
        
    if st.session_state.periodo_seleccionado is None:
        st.session_state.periodo_seleccionado = 0

    st.session_state.periodo_seleccionado = min(st.session_state.periodo_seleccionado, len(opciones)-1)
    
    idx_p = st.selectbox("Seleccionar Periodo", range(len(opciones)), format_func=lambda x: opciones[x], index=int(st.session_state.periodo_seleccionado))
    st.session_state.periodo_seleccionado = idx_p

    t1, t2, t3 = st.tabs(["🔄 El Loop", "💰 Mi Pago", "⚙️ Admin" if st.session_state.es_admin else "ℹ️ Info"])

    with t1:
        benef = participantes[idx_p]
        fecha_p = calcular_fecha_periodo(f_inicio_dt, idx_p, grupo['frecuencia'])
        dias_restantes = (fecha_p - date.today()).days
        txt_restantes = f"{dias_restantes} días" if dias_restantes > 0 else "¡Hoy!" if dias_restantes == 0 else "Finalizado"

        st.markdown(f"""
        <div class="info-card">
            👤 <b>Recibe Pozo:</b> {benef['nombre_usuario']}<br>
            🗓️ <b>Fecha Estimada:</b> {fecha_p.strftime('%d/%m/%Y')}<br>
            ⏳ <b>Faltan:</b> {txt_restantes}<br>
        </div>
        """, unsafe_allow_html=True)

        for p in participantes:
            col_a, col_b = st.columns([3, 1])
            col_a.write(f"{'🎁' if p == benef else '👤'} {p['nombre_usuario']}")
            if p != benef:
                pagado = ha_pagado_periodo(p, idx_p)
                col_b.markdown(f"<span class='status-badge {'pago-si' if pagado else 'pago-no'}'>{'SÍ' if pagado else 'NO'}</span>", unsafe_allow_html=True)

    with t2:
        if yo:
            if yo['nombre_usuario'] == participantes[idx_p]['nombre_usuario']:
                st.success("¡Este periodo cobras tú!")
            else:
                if ha_pagado_periodo(yo, idx_p): st.success("✅ Pago confirmado.")
                elif ha_avisado_periodo(yo, idx_p): st.warning("🔔 Avisado al admin.")
                else:
                    if st.button("📢 YA PAGUÉ"):
                        avisos = str(yo.get('periodos_avisados', "")).split(",")
                        if str(idx_p) not in avisos:
                            avisos.append(str(idx_p))
                            supabase.table("participantes").update({"periodos_avisados": ",".join(filter(None, avisos))}).eq("id", yo['id']).execute(); st.rerun()

    with t3:
        if st.session_state.es_admin:
            st.subheader("Validar Pagos")
            pendientes = [p for p in participantes if ha_avisado_periodo(p, idx_p)]
            for p in pendientes:
                if st.button(f"Confirmar pago de {p['nombre_usuario']}"):
                    avisos = str(p.get('periodos_avisados', "")).split(",")
                    pagos = str(p.get('periodos_pagados', "")).split(",")
                    if str(idx_p) in avisos: avisos.remove(str(idx_p))
                    if str(idx_p) not in pagos: pagos.append(str(idx_p))
                    supabase.table("participantes").update({"periodos_avisados": ",".join(filter(None, avisos)), "periodos_pagados": ",".join(filter(None, pagos))}).eq("id", p['id']).execute(); st.rerun()
            
            st.write("---")
            st.subheader("Miembros (Orden de cobro)")
            for i, p in enumerate(participantes):
                with st.container():
                    st.markdown('<div class="member-card">', unsafe_allow_html=True)
                    st.write(f"{i+1}. {p['nombre_usuario']}")
                    c1, c2, c3 = st.columns(3)
                    if i > 0 and c1.button("↑", key=f"u{p['id']}"):
                        # Al intercambiar, usamos los valores de i actuales para normalizar las posiciones
                        supabase.table("participantes").update({"posicion_orden": i-1}).eq("id", p['id']).execute()
                        supabase.table("participantes").update({"posicion_orden": i}).eq("id", participantes[i-1]['id']).execute(); st.rerun()
                    if i < len(participantes)-1 and c2.button("↓", key=f"d{p['id']}"):
                        supabase.table("participantes").update({"posicion_orden": i+1}).eq("id", p['id']).execute()
                        supabase.table("participantes").update({"posicion_orden": i}).eq("id", participantes[i+1]['id']).execute(); st.rerun()
                    if p['nombre_usuario'] != st.session_state.mi_nombre and c3.button("❌", key=f"r{p['id']}"):
                        supabase.table("participantes").delete().eq("id", p['id']).execute(); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="danger-zone">', unsafe_allow_html=True)
            if st.button("🗑️ ELIMINAR TODO EL PACTO", type="secondary"):
                confirmar_borrado_total(st.session_state.grupo_id, grupo['password'])
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.subheader("ℹ️ Info del Pacto")
            st.write(f"**Código:** {grupo['codigo']}")
            st.write(f"**Cuota:** ${grupo['monto_cuota']}")
