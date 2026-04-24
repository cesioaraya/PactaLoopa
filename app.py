import streamlit as st
import pandas as pd
from supabase import create_client, Client
import random
import string
from datetime import datetime, date, timedelta
import calendar

# 1. CONFIGURACIÓN
st.set_page_config(page_title="PactaLoopa", page_icon="🤝", layout="centered")

# --- DICCIONARIO DE IDIOMAS ---
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
    },
    "Português": {
        "crear": "✨ Criar Novo Pacto", "unirse": "🤝 Entrar num Pacto", "volver": "⬅️ Voltar",
        "nombre_pacto": "Nome do Pacto", "cuota": "Quota ($)", "frecuencia": "Frequência",
        "primer_pozo": "Primeira Coleta", "tu_nombre": "Seu nome", "btn_crear": "Criar Pacto",
        "buscar": "Buscar Pacto", "quien_eres": "Quem é você?", "nuevo_miembro": "-- Novo Membro --",
        "seleccionar": "-- Selecionar --", "btn_unirme": "Participar", "pass_admin_label": "Senha (Admin)",
        "btn_entrar": "Entrar no Painel", "usuario": "Usuário", "salir": "🚪 Sair",
        "recibe": "Recebe o Fundo", "fecha_est": "Data Estimada", "estado": "Status", "pozo_total": "Total do Fundo",
        "activo": "Período Ativo!", "faltan": "Faltam", "dias": "dias", "ya_pague": "📢 JÁ PAGUEI",
        "admin_tag": "Admin", "tab_loop": "🔄 O Loop", "tab_pago": "💰 Meu Pagamento", "tab_gestion": "⚙️ Gestão", "tab_info": "ℹ️ Info"
    },
    "العربية": {
        "crear": "✨ إنشاء ميثاق جديد", "unirse": "🤝 انضمام للميثاق", "volver": "⬅️ عودة",
        "nombre_pacto": "اسم الميثاق", "cuota": "القسط ($)", "frecuencia": "التكرار",
        "primer_pozo": "موعد أول جمعية", "tu_nombre": "اسمك", "btn_crear": "إنشاء الميثاق",
        "buscar": "بحث عن ميثاق", "quien_eres": "من أنت؟", "nuevo_miembro": "-- عضو جديد --",
        "seleccionar": "-- اختر --", "btn_unirme": "انضمام", "pass_admin_label": "كلمة المرور (للمسؤول فقط)",
        "btn_entrar": "دخول لوحة التحكم", "usuario": "المستخدم", "salir": "🚪 خروج",
        "recibe": "يستلم الجمعية", "fecha_est": "التاريخ المتوقع", "estado": "الحالة", "pozo_total": "إجمالي المبلغ",
        "activo": "الفترة نشطة!", "faltan": "متبقي", "dias": "أيام", "ya_pague": "📢 لقد دفعت",
        "admin_tag": "مسؤول", "tab_loop": "🔄 الحلقة", "tab_pago": "💰 دفعي", "tab_gestion": "⚙️ إدارة", "tab_info": "ℹ️ معلومات"
    },
    "Tagalog": {
        "crear": "✨ Gumawa ng Paluwagan", "unirse": "🤝 Sumali sa Paluwagan", "volver": "⬅️ Bumalik",
        "nombre_pacto": "Pangalan ng Paluwagan", "cuota": "Hulog ($)", "frecuencia": "Dalas",
        "primer_pozo": "Unang Sahod", "tu_nombre": "Pangalan mo", "btn_crear": "Gumawa",
        "buscar": "Maghanap", "quien_eres": "Sino ka?", "nuevo_miembro": "-- Bagong Miyembro --",
        "seleccionar": "-- Pumili --", "btn_unirme": "Sali", "pass_admin_label": "Password (Admin)",
        "btn_entrar": "Pumasok sa Dashboard", "usuario": "User", "salir": "🚪 Logout",
        "recibe": "Tatanggap ng Sahod", "fecha_est": "Inaasahang Petsa", "estado": "Status", "pozo_total": "Kabuuang Sahod",
        "activo": "Aktibo ang Panahon!", "faltan": "Kulang ng", "dias": "araw", "ya_pague": "📢 NAGBAYAD NA AKO",
        "admin_tag": "Admin", "tab_loop": "🔄 Ang Loop", "tab_pago": "💰 Bayad Ko", "tab_gestion": "⚙️ Pamamahala", "tab_info": "ℹ️ Impormasyon"
    },
    "Bahasa Indonesia": {
        "crear": "✨ Buat Arisan Baru", "unirse": "🤝 Gabung Arisan", "volver": "⬅️ Kembali",
        "nombre_pacto": "Nama Arisan", "cuota": "Iuran ($)", "frecuencia": "Frekuensi",
        "primer_pozo": "Tanggal Kocokan Pertama", "tu_nombre": "Nama Anda", "btn_crear": "Buat Arisan",
        "buscar": "Cari Arisan", "quien_eres": "Siapa Anda?", "nuevo_miembro": "-- Anggota Baru --",
        "seleccionar": "-- Pilih --", "btn_unirme": "Gabung", "pass_admin_label": "Kata Sandi (Admin Saja)",
        "btn_entrar": "Masuk Dashboard", "usuario": "Pengguna", "salir": "🚪 Keluar",
        "recibe": "Penerima Arisan", "fecha_est": "Estimasi Tanggal", "estado": "Status", "pozo_total": "Total Dana",
        "activo": "Periode Aktif!", "faltan": "Kurang", "dias": "hari", "ya_pague": "📢 SAYA SUDAH BAYAR",
        "admin_tag": "Admin", "tab_loop": "🔄 Loop", "tab_pago": "💰 Pembayaran Saya", "tab_gestion": "⚙️ Kelola", "tab_info": "ℹ️ Info"
    },
    "Français": {
        "crear": "✨ Créer un Pacte", "unirse": "🤝 Rejoindre un Pacte", "volver": "⬅️ Retour",
        "nombre_pacto": "Nom du Pacte", "cuota": "Cotisation ($)", "frecuencia": "Fréquence",
        "primer_pozo": "Premier Collecte", "tu_nombre": "Votre Nom", "btn_crear": "Créer le Pacte",
        "buscar": "Chercher Pacte", "quien_eres": "Qui êtes-vous?", "nuevo_miembro": "-- Nouveau Membre --",
        "seleccionar": "-- Sélectionner --", "btn_unirme": "Rejoindre", "pass_admin_label": "Mot de Passe (Admin)",
        "btn_entrar": "Tableau de Bord", "usuario": "Utilisateur", "salir": "🚪 Quitter",
        "recibe": "Reçoit le Pot", "fecha_est": "Date Estimée", "estado": "État", "pozo_total": "Total du Pot",
        "activo": "Période Active!", "faltan": "Il reste", "jours": "jours", "ya_pague": "📢 J'AI PAYÉ",
        "admin_tag": "Admin", "tab_loop": "🔄 Le Loop", "tab_pago": "💰 Mon Paiement", "tab_gestion": "⚙️ Gestion", "tab_info": "ℹ️ Info"
    },
    "Tiếng Việt": {
        "crear": "✨ Tạo Nhóm Hụi", "unirse": "🤝 Tham Gia Nhóm", "volver": "⬅️ Quay lại",
        "nombre_pacto": "Tên Nhóm", "cuota": "Tiền Đóng ($)", "frecuencia": "Tần suất",
        "primer_pozo": "Ngày Hốt Đầu Tiên", "tu_nombre": "Tên của bạn", "btn_crear": "Tạo Nhóm",
        "buscar": "Tìm Nhóm", "quien_eres": "Bạn là ai?", "nuevo_miembro": "-- Thành viên mới --",
        "seleccionar": "-- Chọn --", "btn_unirme": "Tham gia", "pass_admin_label": "Mật khẩu (Admin)",
        "btn_entrar": "Vào Bảng Điều Khiển", "usuario": "Người dùng", "salir": "🚪 Thoát",
        "recibe": "Người Hốt Hụi", "fecha_est": "Ngày Dự Kiến", "estado": "Trạng thái", "pozo_total": "Tổng Tiền Hụi",
        "activo": "Giai Đoạn Đang Hoạt Động!", "faltan": "Còn lại", "dias": "ngày", "ya_pague": "📢 TÔI ĐÃ ĐÓNG TIỀN",
        "admin_tag": "Quản trị", "tab_loop": "🔄 Vòng Lặp", "tab_pago": "💰 Khoản Đóng", "tab_gestion": "⚙️ Quản lý", "tab_info": "ℹ️ Thông tin"
    },
    "Kiswahili": {
        "crear": "✨ Anzisha Chama", "unirse": "🤝 Jiunge na Chama", "volver": "⬅️ Rudia",
        "nombre_pacto": "Jina la Chama", "cuota": "Mchango ($)", "frecuencia": "Mzunguko",
        "primer_pozo": "Tarehe ya Kwanza", "tu_nombre": "Jina lako", "btn_crear": "Anzisha",
        "buscar": "Tafuta Chama", "quien_eres": "Wewe ni nani?", "nuevo_miembro": "-- Mwanachama Mpya --",
        "seleccionar": "-- Chagua --", "btn_unirme": "Jiunge", "pass_admin_label": "Nywila (Admin Pekee)",
        "btn_entrar": "Ingia Dashboard", "usuario": "Mtumiaji", "salir": "🚪 Ondoka",
        "recibe": "Anayepokea Fedha", "fecha_est": "Tarehe Inayotarajiwa", "estado": "Hali", "pozo_total": "Jumla ya Fedha",
        "activo": "Kipindi Kipo Wazi!", "faltan": "Zimebaki", "dias": "siku", "ya_pague": "📢 NIMELIPA",
        "admin_tag": "Admin", "tab_loop": "🔄 Mzunguko", "tab_pago": "💰 Malipo Yangu", "tab_gestion": "⚙️ Usimamizi", "tab_info": "ℹ️ Habari"
    },
    "中文": {
        "crear": "✨ 创建新协议", "unirse": "🤝 加入协议", "volver": "⬅️ 返回",
        "nombre_pacto": "协议名称", "cuota": "金额 ($)", "frecuencia": "频率",
        "primer_pozo": "首次日期", "tu_nombre": "您的名字", "btn_crear": "创建协议",
        "buscar": "搜索协议", "quien_eres": "您是谁？", "nuevo_miembro": "-- 新成员 --",
        "seleccionar": "-- 请选择 --", "btn_unirme": "加入", "pass_admin_label": "密码 (仅限管理员)",
        "btn_entrar": "进入仪表板", "usuario": "用户", "salir": "🚪 退出",
        "recibe": "收款人", "fecha_est": "预计日期", "estado": "状态", "pozo_total": "总金额",
        "activo": "期间有效！", "faltan": "剩余", "dias": "天", "ya_pague": "📢 我已付款",
        "admin_tag": "管理员", "tab_loop": "🔄 循环", "tab_pago": "💰 我的付款", "tab_gestion": "⚙️ 管理", "tab_info": "ℹ️ 信息"
    },
    "हिन्दी": {
        "crear": "✨ नया समझौता", "unirse": "🤝 समझौते में शामिल हों", "volver": "⬅️ वापस",
        "nombre_pacto": "समझौते का नाम", "cuota": "किस्त ($)", "frecuencia": "आवृत्ति",
        "primer_pozo": "पहला पूल", "tu_nombre": "आपका नाम", "btn_crear": "समझौता बनाएं",
        "buscar": "समझौता खोजें", "quien_eres": "आप कौन हैं?", "nuevo_miembro": "-- नया सदस्य --",
        "seleccionar": "-- चुनें --", "btn_unirme": "शामिल हों", "pass_admin_label": "पासवर्ड (केवल एडमिन)",
        "btn_entrar": "डैशबोर्ड खोलें", "usuario": "उपयोगकर्ता", "salir": "🚪 बाहर निकलें",
        "recibe": "प्राप्तकर्ता", "fecha_est": "अनुमानित तिथि", "estado": "स्थिति", "pozo_total": "कुल पूल",
        "activo": "अवधि सक्रिय!", "faltan": "शेष", "dias": "दिन", "ya_pague": "📢 मैंने भुगतान कर दिया",
        "admin_tag": "एडमिन", "tab_loop": "🔄 लूप", "tab_pago": "💰 मेरा भुगतान", "tab_gestion": "⚙️ प्रबंधन", "tab_info": "जानकारी"
    }
}

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
        "es_admin": False,
        "lang": "Español"
    })

# --- SELECTOR DE IDIOMA ENCABEZADO ---
header_col1, header_col2 = st.columns([3, 1])
with header_col2:
    st.session_state.lang = st.selectbox("🌐", list(LANGS.keys()), index=list(LANGS.keys()).index(st.session_state.lang), label_visibility="collapsed")
T = LANGS[st.session_state.lang]

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
    div[data-testid="stRadio"] > label { font-weight: bold; margin-bottom: 10px; }
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
        if st.button(T["crear"]): st.session_state.vista = "crear"; st.rerun()
    with col2:
        if st.button(T["unirse"]): st.session_state.vista = "unirse"; st.rerun()

elif st.session_state.vista == "crear":
    if st.button(T["volver"]): st.session_state.vista = "inicio"; st.rerun()
    nombre = st.text_input(T["nombre_pacto"])
    monto = st.number_input(T["cuota"], min_value=1, value=100)
    frecuencia = st.selectbox(T["frecuencia"], ["Semanal", "Quincenal", "Mensual"])
    fecha_inicio = st.date_input(T["primer_pozo"], value=date.today())
    pwd = st.text_input("Pass Admin", type="password")
    admin_n = st.text_input(T["tu_nombre"]).strip()
    
    if st.button(T["btn_crear"]):
        if nombre and admin_n and pwd:
            cod = generar_codigo()
            res = supabase.table("grupos").insert({"nombre": nombre, "monto_cuota": monto, "frecuencia": frecuencia.lower(), "fecha_inicio": fecha_inicio.isoformat(), "codigo": cod, "password": pwd, "abierto": True}).execute()
            gid = res.data[0]['id']
            supabase.table("participantes").insert({"grupo_id": gid, "nombre_usuario": admin_n, "posicion_orden": 999}).execute()
            st.session_state.update({"grupo_id": gid, "mi_nombre": admin_n, "vista": "dashboard", "nuevo_codigo": cod, "nueva_pass": pwd, "mostrar_exito": True, "es_admin": True})
            st.rerun()

elif st.session_state.vista == "unirse":
    if st.button(T["volver"]): st.session_state.vista = "inicio"; st.rerun()
    c_in = st.text_input("Código del Pacto").upper().strip()
    if st.button(T["buscar"]):
        g = supabase.table("grupos").select("*").eq("codigo", c_in).execute()
        if g.data:
            st.session_state.grupo_id = g.data[0]['id']
            st.session_state.vista = "seleccionar_usuario"; st.rerun()
        else: st.error("No se encontró ningún pacto con ese código.")

elif st.session_state.vista == "seleccionar_usuario":
    p_db = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).execute()
    g_db = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
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
        st.info("Deja la contraseña en blanco si eres un miembro normal.")
        p_check = st.text_input(T["pass_admin_label"], type="password")
        if st.button(T["btn_entrar"]):
            is_adm = (p_check == grupo['password'])
            st.session_state.update({"mi_nombre": sel, "vista": "dashboard", "es_admin": is_adm})
            st.rerun()

# --- DASHBOARD ---
elif st.session_state.vista == "dashboard":
    if st.session_state.mostrar_exito:
        mostrar_exito(st.session_state.nuevo_codigo, st.session_state.nueva_pass)

    g_res = supabase.table("grupos").select("*").eq("id", st.session_state.grupo_id).execute()
    if not g_res.data: st.session_state.update({"grupo_id": None, "vista": "inicio"}); st.rerun()
    grupo = g_res.data[0]
    p_res = supabase.table("participantes").select("*").eq("grupo_id", st.session_state.grupo_id).order("posicion_orden").execute()
    participantes = p_res.data
    yo = next((p for p in participantes if p['nombre_usuario'] == st.session_state.mi_nombre), None)
    f_inicio_dt = date.fromisoformat(grupo['fecha_inicio'])

    ucol1, ucol2 = st.columns([3, 1])
    ucol1.markdown(f"**👤 {T['usuario']}:** {st.session_state.mi_nombre} {' (🛡️ '+T['admin_tag']+')' if st.session_state.es_admin else ''}")
    if ucol2.button(T["salir"]):
        st.session_state.update({"grupo_id": None, "mi_nombre": "", "vista": "inicio", "periodo_seleccionado": None, "es_admin": False})
        st.rerun()
    
    st.markdown("---")
    st.write(f"### {grupo['nombre']}")

    hoy = date.today()
    if st.session_state.periodo_seleccionado is None:
        mejor_idx = 0
        menor_dif = float('inf')
        for i in range(len(participantes)):
            f_p = calcular_fecha_periodo(f_inicio_dt, i, grupo['frecuencia'])
            dif = abs((f_p - hoy).days)
            if dif < menor_dif:
                menor_dif = dif
                mejor_idx = i
        st.session_state.periodo_seleccionado = mejor_idx
    
    opciones = [f"P{i+1}: {p['nombre_usuario']}" for i, p in enumerate(participantes)]
    if not opciones:
        st.info("Waiting for members...")
        st.stop()
    
    with st.expander(f"📅 {opciones[int(st.session_state.periodo_seleccionado)]}", expanded=False):
        idx_p = st.radio("Period:", range(len(opciones)), format_func=lambda x: opciones[x], index=int(st.session_state.periodo_seleccionado), label_visibility="collapsed")
        if idx_p != st.session_state.periodo_seleccionado:
            st.session_state.periodo_seleccionado = idx_p
            st.rerun()

    t1, t2, t3 = st.tabs([T["tab_loop"], T["tab_pago"], T["tab_gestion"] if st.session_state.es_admin else T["tab_info"]])

    with t1:
        benef = participantes[idx_p]
        fecha_p = calcular_fecha_periodo(f_inicio_dt, idx_p, grupo['frecuencia'])
        dias_restantes = (fecha_p - hoy).days
        
        st.markdown(f"""
        <div class="info-card">
            👤 <b>{T['recibe']}:</b> {benef['nombre_usuario']}<br>
            🗓️ <b>{T['fecha_est']}:</b> {fecha_p.strftime('%d/%m/%Y')}<br>
            ⏳ <b>{T['estado']}:</b> {T['activo'] if dias_restantes <= 0 else f"{T['faltan']} {dias_restantes} {T['dias']}"}
            <br>💰 <b>{T['pozo_total']}:</b> ${grupo['monto_cuota'] * (len(participantes)-1)}
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
            fecha_p = calcular_fecha_periodo(f_inicio_dt, idx_p, grupo['frecuencia'])
            dias_para_el_pozo = (fecha_p - hoy).days
            puede_avisar = dias_para_el_pozo <= 5
            
            if not puede_avisar:
                fecha_apertura = fecha_p - timedelta(days=5)
                st.info(f"🛡️ Podrás avisar a partir del **{fecha_apertura.strftime('%d/%m/%Y')}**.")
            elif yo['nombre_usuario'] == participantes[idx_p]['nombre_usuario']:
                st.success("✨ You receive the pool!")
            else:
                if ha_pagado_periodo(yo, idx_p): 
                    st.success("✅ Confirmed.")
                elif ha_avisado_periodo(yo, idx_p): 
                    st.warning("🔔 Waiting validation.")
                else:
                    st.write(f"{T['cuota']}: **${grupo['monto_cuota']}**")
                    if st.button(T["ya_pague"]):
                        avisos = str(yo.get('periodos_avisados', "")).split(",")
                        if str(idx_p) not in avisos:
                            avisos.append(str(idx_p))
                            supabase.table("participantes").update({"periodos_avisados": ",".join(filter(None, avisos))}).eq("id", yo['id']).execute()
                            st.toast("Sent")
                            st.rerun()

    with t3:
        if st.session_state.es_admin:
            st.subheader("Validar Pagos")
            pendientes = [p for p in participantes if ha_avisado_periodo(p, idx_p)]
            for p in pendientes:
                if st.button(f"Confirm {p['nombre_usuario']}"):
                    avisos = str(p.get('periodos_avisados', "")).split(",")
                    pagos = str(p.get('periodos_pagados', "")).split(",")
                    if str(idx_p) in avisos: avisos.remove(str(idx_p))
                    if str(idx_p) not in pagos: pagos.append(str(idx_p))
                    supabase.table("participantes").update({"periodos_avisados": ",".join(filter(None, avisos)), "periodos_pagados": ",".join(filter(None, pagos))}).eq("id", p['id']).execute(); st.rerun()
            
            # --- NUEVA SECCIÓN: CANCELAR CONFIRMACIÓN ---
            st.write("---")
            st.subheader("Pagos Confirmados")
            confirmados = [p for p in participantes if ha_pagado_periodo(p, idx_p)]
            if not confirmados: st.caption("No hay pagos confirmados en este periodo.")
            for p in confirmados:
                col_c1, col_c2 = st.columns([3, 1])
                col_c1.write(f"✅ {p['nombre_usuario']}")
                if col_c2.button("Deshacer", key=f"undo_{p['id']}"):
                    pagos = str(p.get('periodos_pagados', "")).split(",")
                    if str(idx_p) in pagos: pagos.remove(str(idx_p))
                    # Opcionalmente lo devolvemos a "avisado" o simplemente lo quitamos de pagado
                    supabase.table("participantes").update({"periodos_pagados": ",".join(filter(None, pagos))}).eq("id", p['id']).execute(); st.rerun()
            
            st.write("---")
            st.subheader("Order")
            for i, p in enumerate(participantes):
                with st.container():
                    st.markdown('<div class="member-card">', unsafe_allow_html=True)
                    st.write(f"{i+1}. {p['nombre_usuario']}")
                    c1, c2, c3 = st.columns(3)
                    if i > 0 and c1.button("↑", key=f"u{p['id']}"):
                        supabase.table("participantes").update({"posicion_orden": i-1}).eq("id", p['id']).execute()
                        supabase.table("participantes").update({"posicion_orden": i}).eq("id", participantes[i-1]['id']).execute(); st.rerun()
                    if i < len(participantes)-1 and c2.button("↓", key=f"d{p['id']}"):
                        supabase.table("participantes").update({"posicion_orden": i+1}).eq("id", p['id']).execute()
                        supabase.table("participantes").update({"posicion_orden": i}).eq("id", participantes[i+1]['id']).execute(); st.rerun()
                    if p['nombre_usuario'] != st.session_state.mi_nombre and c3.button("❌", key=f"r{p['id']}"):
                        supabase.table("participantes").delete().eq("id", p['id']).execute(); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            if st.button("🗑️ DELETE PACT"): confirmar_borrado_total(st.session_state.grupo_id, grupo['password'])
        else:
            st.subheader(T["tab_info"])
            st.write(f"**Code:** `{grupo['codigo']}`")
            st.write(f"**{T['cuota']}:** ${grupo['monto_cuota']}")
