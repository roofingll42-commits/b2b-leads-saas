import streamlit as st
import sqlite3
import pandas as pd
import re
import os
import random
import hashlib
import smtplib
from email.message import EmailMessage
import requests

st.set_page_config(
    page_title="Global B2B Intelligence Portal | Verified US Leads",
    page_icon="🚀",
    layout="wide"
)

# Estilo CSS profesional tipo Apollo.io / ZoomInfo
st.markdown(
    """
    <style>
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.88rem !important;
    }
    .bloqueo-box {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 28px;
        border-radius: 14px;
        border: 1px solid #3B82F6;
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# ⚙️ CONFIGURACIÓN DE LÍMITES, PRECIOS Y CORREO OTP
# ==============================================================================
LIMITE_BUSQUEDAS_GRATIS = 5

PRECIO_MENSUAL = "$49 / mes"
PRECIO_ANUAL = "$195 / año"
LINK_PAGO_MENSUAL = "https://juanahez.gumroad.com/l/ywcomq"
LINK_PAGO_ANUAL = "https://juanahez.gumroad.com/l/rzzow"

CODIGOS_PLAN_MENSUAL = {"PRO-MONTHLY-2026", "VIP-STATE-2026"}
CODIGOS_PLAN_ANUAL = {"PRO-ANNUAL-2026", "VIP-ALL-2026"}

try:
    SMTP_EMAIL = st.secrets.get("SMTP_EMAIL", "")
    SMTP_PASSWORD = st.secrets.get("SMTP_PASSWORD", "")
except Exception:
    SMTP_EMAIL = ""
    SMTP_PASSWORD = ""

# ==============================================================================
# 📥 DESCARGADOR AUTOMÁTICO DE LA MEGA BASE DE DATOS (GITHUB RELEASES)
# ==============================================================================
DB_MEGA_PATH = "mega_base_b2b.db"

if not os.path.exists(DB_MEGA_PATH):
    st.info("⏳ Descargando la base de datos masiva desde el servidor (esto solo ocurre la primera vez)...")
    ENLACE_DIRECTO_DB = "https://github.com/roofingll42-commits/b2b-leads-saas/releases/download/v1.0/mega_base_b2b.db"
    try:
        response = requests.get(ENLACE_DIRECTO_DB, stream=True, timeout=120)
        if response.status_code == 200:
            with open(DB_MEGA_PATH, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
            st.rerun()
        else:
            st.error(f"No se pudo descargar la base de datos. Código: {response.status_code}")
    except Exception as e:
        st.error(f"Error en la descarga: {e}")

# ==============================================================================
# 🔐 BASE DE DATOS DE USUARIOS, OTP DE 6 DÍGITOS Y SUSCRIPCIONES
# ==============================================================================
USERS_DB = "usuarios_saas.db"

def inicializar_db_usuarios():
    conn = sqlite3.connect(USERS_DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            email TEXT PRIMARY KEY,
            nombre TEXT,
            password_hash TEXT,
            verificado INTEGER DEFAULT 0,
            otp_codigo TEXT,
            plan TEXT DEFAULT 'free',
            busquedas_usadas INTEGER DEFAULT 0,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

inicializar_db_usuarios()

def encriptar_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def enviar_correo_otp(destinatario, nombre, codigo_otp, motivo="confirmar tu correo electrónico"):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return False, f"📩 Código de confirmación de 6 dígitos generado: **{codigo_otp}** *(Configura SMTP_EMAIL en Streamlit Secrets para envío directo por email)*"
    try:
        msg = EmailMessage()
        msg["Subject"] = f"🔑 Tu código de confirmación es {codigo_otp} - Global B2B Portal"
        msg["From"] = SMTP_EMAIL
        msg["To"] = destinatario
        msg.set_content(
            f"Hola {nombre},\n\n"
            f"Tu código de seguridad de 6 dígitos para {motivo} es:\n\n"
            f"👉 {codigo_otp}\n\n"
            f"Ingresa este código en la aplicación para continuar.\n"
        )
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        return True, f"✅ Enviamos un código de 6 dígitos a **{destinatario}**. Revisa tu bandeja de entrada o Spam."
    except Exception as e:
        return False, f"Aviso SMTP ({e}). Tu código OTP de 6 dígitos es: **{codigo_otp}**"

def obtener_usuario(email):
    if not email:
        return None
    conn = sqlite3.connect(USERS_DB)
    c = conn.cursor()
    fila = c.execute(
        "SELECT email, nombre, password_hash, verificado, otp_codigo, plan, busquedas_usadas FROM usuarios WHERE email = ?",
        (email.lower().strip(),)
    ).fetchone()
    conn.close()
    if fila:
        return {
            "email": fila[0],
            "nombre": fila[1],
            "password_hash": fila[2],
            "verificado": fila[3],
            "otp_codigo": fila[4],
            "plan": fila[5],
            "busquedas_usadas": fila[6]
        }
    return None

def incrementar_busqueda_db(email):
    conn = sqlite3.connect(USERS_DB)
    conn.execute("UPDATE usuarios SET busquedas_usadas = busquedas_usadas + 1 WHERE email = ?", (email.lower().strip(),))
    conn.commit()
    conn.close()

def actualizar_plan_db(email, nuevo_plan):
    conn = sqlite3.connect(USERS_DB)
    conn.execute("UPDATE usuarios SET plan = ? WHERE email = ?", (nuevo_plan, email.lower().strip()))
    conn.commit()
    conn.close()

# ==============================================================================
# 🧠 VARIABLES DE SESIÓN (VISITANTE / USUARIO LOGUEADO / CONTADOR DE BÚSQUEDAS)
# ==============================================================================
if "usuario_activo" not in st.session_state:
    st.session_state.usuario_activo = None
if "mostrar_panel_auth" not in st.session_state:
    st.session_state.mostrar_panel_auth = None
if "email_pendiente_otp" not in st.session_state:
    st.session_state.email_pendiente_otp = ""
if "mensaje_otp_info" not in st.session_state:
    st.session_state.mensaje_otp_info = ""
if "busquedas_invitado" not in st.session_state:
    st.session_state.busquedas_invitado = 0
if "ultima_firma_busqueda" not in st.session_state:
    st.session_state.ultima_firma_busqueda = ""

usuario_actual = obtener_usuario(st.session_state.usuario_activo) if st.session_state.usuario_activo else None
es_suscriptor_pro = bool(usuario_actual and usuario_actual["plan"] in ("monthly", "annual"))

if usuario_actual:
    busquedas_usadas = usuario_actual["busquedas_usadas"]
else:
    busquedas_usadas = st.session_state.busquedas_invitado

busquedas_restantes = max(0, LIMITE_BUSQUEDAS_GRATIS - busquedas_usadas)

# ==============================================================================
# 📋 LISTADO DE LAS 95 INDUSTRIAS Y LIMPIEZA DE DATOS
# ==============================================================================
RUBROS_95 = [
    "Construction Company", "General Contractor", "Roofing Contractor", "Plumbing Service",
    "HVAC Repair", "Electrician", "Painting Company", "Landscaping Service", "Cleaning Service",
    "Water Damage Restoration", "Pest Control", "Flooring Contractor", "Home Remodeling",
    "Cabinet Shop", "Tree Service", "Pool Maintenance", "Fencing Company", "Moving Company",
    "Garage Door Repair", "Locksmith Service", "Carpet Cleaning", "Window Tinting",
    "Paving Contractor", "Excavation Company", "Asphalt Contractor", "Gutter Cleaning Service",
    "Junk Removal Service", "Interior Designer", "Handyman Service", "Appliance Repair",
    "Law Firm", "Accountant", "Architecture Firm", "Real Estate Agency", "Tax Preparation Service",
    "Financial Advisor", "Insurance Agency", "Business Consultant", "Property Management",
    "Private Investigator", "Notary Public", "Title Company", "Mortgage Broker",
    "Staffing Agency", "Public Relations Firm", "Commercial Real Estate",
    "Dentist Office", "Medical Clinic", "Chiropractor", "Physical Therapy Clinic",
    "Med Spa", "Veterinary Clinic", "Optometrist", "Fitness Center", "Yoga Studio",
    "Dermatologist Office", "Plastic Surgery Clinic", "Acupuncture Clinic", "Massage Therapy",
    "Hair Salon", "Barber Shop", "Orthodontist", "Home Health Care Service",
    "Trucking Company", "Logistics Service", "Auto Repair Shop", "Car Dealership",
    "Towing Service", "Auto Body Shop", "Mobile Car Detailing", "Tire Shop",
    "Auto Glass Repair", "Freight Forwarder", "Warehouse Storage",
    "Digital Marketing Agency", "IT Support Service", "Web Development Agency",
    "Software Company", "Cybersecurity Firm", "Managed Service Provider",
    "Graphic Design Studio", "Video Production Company", "SEO Agency", "Data Recovery Service",
    "Solar Energy Company", "Security Company", "Machine Shop", "Wholesale Supplier",
    "Catering Service", "Event Planner", "Wedding Photographer", "Boutique Hotel",
    "Commercial Printer", "Sign Shop", "Janitorial Service", "Equipment Rental Agency"
]

def ocultar_dato(val, visibles=5):
    s = str(val).strip()
    if not s or s in ["-", "N/A", "None", "nan"]:
        return "-"
    return (s[:visibles] + "••••• (Locked)") if len(s) > visibles else (s + "***")

def limpiar_dueno_en_vista(fila):
    emp = str(fila.get("Empresa_Legal") or "").strip()
    dueno = str(fila.get("Dueno_Principal") or "").strip()
    if not dueno or dueno in ("-", "N/A", "None", "nan", "Principal / Registered Officer"):
        return "Principal / Registered Officer"
    if any(ch.isdigit() for ch in dueno):
        return "Principal / Registered Officer"
    if emp and len(emp) >= 4 and dueno.lower().startswith(emp.lower()):
        resto = dueno[len(emp):].strip(" -|,.:;/")
        if len(resto.split()) >= 2:
            dueno = resto
        else:
            return "Principal / Registered Officer"
    palabras_no_humanas = {
        "inc", "llc", "corp", "company", "plumbing", "hvac", "mechanical", "services",
        "service", "contracting", "contractor", "group", "management", "solutions",
        "roofing", "electric", "construction", "auto", "realty", "clinic", "shop", "store",
        "school", "district", "library", "academy", "consortium", "university", "college", "city", "county"
    }
    palabras_d = re.findall(r'[a-z]+', dueno.lower())
    if any(p in palabras_no_humanas for p in palabras_d) or dueno.lower() in emp.lower():
        return "Principal / Registered Officer"
    return dueno.title()

def corregir_estado_en_vista(fila):
    st_val = str(fila.get("Estado") or "").strip().upper()
    if len(st_val) == 2 and st_val not in ("US", "NA", "N/"):
        return st_val
    z = str(fila.get("Codigo_Postal") or "").strip()
    if len(z) >= 5 and z[:5].isdigit():
        p2 = int(z[:2])
        if 32 <= p2 <= 34: return "FL"
        if 85 <= p2 <= 86: return "AZ"
        if 15 <= p2 <= 19: return "PA"
        if 10 <= p2 <= 14: return "NY"
        if 90 <= p2 <= 96: return "CA"
        if 75 <= p2 <= 79: return "TX"
        if 60 <= p2 <= 62: return "IL"
        if 30 <= p2 <= 31: return "GA"
        if 27 <= p2 <= 28: return "NC"
        if 98 <= p2 <= 99: return "WA"
        if 43 <= p2 <= 45: return "OH"
        if 68 <= p2 <= 69: return "NE"
        if 1 <= p2 <= 2: return "MA"
    return st_val if st_val else "US"

@st.cache_resource
def indexar_y_unificar_rubros_sql():
    if not os.path.exists(DB_MEGA_PATH):
        return
    try:
        conn = sqlite3.connect(DB_MEGA_PATH)
        c = conn.cursor()
        c.execute("CREATE INDEX IF NOT EXISTS idx_ind ON leads_b2b(industry)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sub ON leads_b2b(sub_category)")
        placeholders = ",".join(["?"] * len(RUBROS_95))
        c.execute(f"""
            UPDATE leads_b2b
            SET industry = sub_category
            WHERE sub_category IN ({placeholders})
              AND (industry IS NULL OR industry != sub_category)
        """, RUBROS_95)

        reglas_distribucion = [
            ("Plumbing Service", ["%plumb%", "%rooter%", "%drain%", "%sewer%", "%piping%"]),
            ("HVAC Repair", ["%hvac%", "%air condition%", "%heating%", "%cooling%", "%refrigerat%", "%furnace%", "%boiler%"]),
            ("Roofing Contractor", ["%roof%", "%shingle%"]),
            ("Electrician", ["%electric%", "%wiring%", "%lighting%", "%generator%"]),
            ("Solar Energy Company", ["%solar%", "%photovoltaic%"]),
            ("Painting Company", ["%paint%", "%coating%"]),
            ("Landscaping Service", ["%landscap%", "%lawn%", "%garden%", "%irrigat%", "%sprinkler%"]),
            ("Water Damage Restoration", ["%restoration%", "%water damage%", "%mold%", "%remediat%"]),
            ("Pest Control", ["%pest%", "%exterminat%", "%termite%"]),
            ("Flooring Contractor", ["%floor%", "%tile%", "%hardwood%", "%linoleum%"]),
            ("Home Remodeling", ["%remodel%", "%renovat%", "%kitchen%", "%bath%"]),
            ("Cabinet Shop", ["%cabinet%", "%millwork%", "%woodwork%", "%carpent%"]),
            ("Tree Service", ["%tree %", "%arborist%", "%stump%"]),
            ("Pool Maintenance", ["%pool%", "%aquatic%"]),
            ("Fencing Company", ["%fenc%", "%railing%"]),
            ("Moving Company", ["%moving%", "%mover%", "%relocat%", "%van lines%"]),
            ("Garage Door Repair", ["%garage door%", "%overhead door%"]),
            ("Locksmith Service", ["%locksmith%", "%lock %"]),
            ("Carpet Cleaning", ["%carpet%", "%upholster%"]),
            ("Window Tinting", ["%window%", "%glazing%", "%tint%", "%shutter%"]),
            ("Paving Contractor", ["%paving%", "%paver%", "%driveway%"]),
            ("Excavation Company", ["%excavat%", "%grading%", "%demolition%", "%earthwork%"]),
            ("Asphalt Contractor", ["%asphalt%", "%sealcoat%", "%blacktop%"]),
            ("Gutter Cleaning Service", ["%gutter%", "%downspout%"]),
            ("Junk Removal Service", ["%junk%", "%hauling%", "%debris%", "%waste%", "%dumpster%"]),
            ("Interior Designer", ["%interior design%", "%decor%", "%staging%"]),
            ("Handyman Service", ["%handyman%", "%home repair%"]),
            ("Appliance Repair", ["%appliance%"]),
            ("Janitorial Service", ["%janitor%", "%custodial%", "%sanitation%"]),
            ("Cleaning Service", ["%clean%", "%maid%", "%housekeep%"]),
            ("Equipment Rental Agency", ["%rental%", "%leasing%"]),
            ("Architecture Firm", ["%architect%", "%drafting%", "%engineering%"]),
            ("Law Firm", ["%law %", "%legal%", "%attorney%", "%lawyer%", "%pllc%"]),
            ("Accountant", ["%account%", "%cpa%", "%bookkeep%", "%audit%"]),
            ("Tax Preparation Service", ["%tax %", "%taxes%"]),
            ("Commercial Real Estate", ["%commercial real%", "%commercial prop%"]),
            ("Property Management", ["%property manag%", "%hoa %", "%apartments%"]),
            ("Real Estate Agency", ["%real estate%", "%realtor%", "%realty%", "%homes%"]),
            ("Title Company", ["%title %", "%escrow%", "%settlement%"]),
            ("Mortgage Broker", ["%mortgage%", "%lending%", "%lender%", "%loan%"]),
            ("Financial Advisor", ["%financial%", "%wealth%", "%investment%", "%capital%", "%asset%"]),
            ("Insurance Agency", ["%insur%", "%underwrit%", "%casualty%", "%indemnity%"]),
            ("Business Consultant", ["%consult%", "%advisory%", "%strategy%"]),
            ("Private Investigator", ["%investigat%", "%detective%"]),
            ("Notary Public", ["%notary%"]),
            ("Staffing Agency", ["%staffing%", "%recruit%", "%employment%", "%talent%"]),
            ("Public Relations Firm", ["%public relations%", "%communications%"]),
            ("Dentist Office", ["%dentist%", "%dental%", "%dds%", "%dmd%"]),
            ("Orthodontist", ["%orthodont%"]),
            ("Chiropractor", ["%chiropract%"]),
            ("Physical Therapy Clinic", ["%physical therap%", "%rehab%"]),
            ("Med Spa", ["%med spa%", "%medspa%", "%aesthetic%", "%laser%"]),
            ("Veterinary Clinic", ["%veterinar%", "%animal%", "%pet clinic%"]),
            ("Optometrist", ["%optometr%", "%optical%", "%vision%", "%eye %"]),
            ("Dermatologist Office", ["%dermatolog%", "%skin%"]),
            ("Plastic Surgery Clinic", ["%plastic surg%", "%cosmetic surg%"]),
            ("Acupuncture Clinic", ["%acupuncture%"]),
            ("Massage Therapy", ["%massage%", "%bodywork%"]),
            ("Fitness Center", ["%fitness%", "%gym%", "%crossfit%", "%athletic%"]),
            ("Yoga Studio", ["%yoga%", "%pilates%"]),
            ("Hair Salon", ["%salon%", "%beauty%", "%hair%"]),
            ("Barber Shop", ["%barber%"]),
            ("Home Health Care Service", ["%home health%", "%home care%", "%senior care%", "%nursing%", "%hospice%"]),
            ("Medical Clinic", ["%medical%", "%clinic%", "%physician%", "%doctor%", "%health%", "%hospital%", "%pharmacy%"]),
            ("Towing Service", ["%towing%", "%tow %", "%wrecker%"]),
            ("Auto Body Shop", ["%auto body%", "%body shop%", "%collision%"]),
            ("Mobile Car Detailing", ["%detailing%", "%car wash%"]),
            ("Tire Shop", ["%tire%", "%wheel%", "%alignment%"]),
            ("Auto Glass Repair", ["%auto glass%", "%windshield%"]),
            ("Car Dealership", ["%dealership%", "%auto sales%", "%motors%", "%used cars%"]),
            ("Auto Repair Shop", ["%auto%", "%mechanic%", "%brake%", "%transmission%", "%garage%"]),
            ("Freight Forwarder", ["%freight%", "%cargo%", "%import%", "%export%"]),
            ("Warehouse Storage", ["%warehouse%", "%storage%", "%distribution%"]),
            ("Logistics Service", ["%logistic%", "%supply chain%", "%dispatch%", "%courier%", "%delivery%"]),
            ("Trucking Company", ["%truck%", "%carrier%", "%transport%"]),
            ("SEO Agency", ["%seo%", "%search engine%"]),
            ("Web Development Agency", ["%web %", "%website%", "%ecommerce%"]),
            ("Digital Marketing Agency", ["%marketing%", "%advertising%", "%media%"]),
            ("Cybersecurity Firm", ["%cyber%", "%infosec%"]),
            ("Data Recovery Service", ["%data %", "%backup%"]),
            ("Managed Service Provider", ["%managed service%", "%msp%", "%it solutions%"]),
            ("Software Company", ["%software%", "%saas%", "%cloud%", "%systems%"]),
            ("IT Support Service", ["%tech%", "%computer%", "%network%", "%telecom%"]),
            ("Graphic Design Studio", ["%graphic%", "%branding%", "%design studio%", "%creative%"]),
            ("Video Production Company", ["%video%", "%film%", "%production%", "%studio%"]),
            ("Security Company", ["%security%", "%guard%", "%patrol%", "%alarm%"]),
            ("Machine Shop", ["%machine%", "%cnc%", "%fabricat%", "%welding%", "%metal%", "%mfg%", "%manufacturing%"]),
            ("Wholesale Supplier", ["%wholesale%", "%supplier%", "%distributor%", "%supply%", "%trading%"]),
            ("Catering Service", ["%cater%", "%banquet%", "%food%", "%restaurant%", "%bakery%", "%cafe%"]),
            ("Event Planner", ["%event%", "%party%", "%entertainment%"]),
            ("Wedding Photographer", ["%wedding%", "%photograph%", "%photo%"]),
            ("Boutique Hotel", ["%hotel%", "%inn%", "%resort%", "%hospitality%", "%motel%", "%lodging%"]),
            ("Commercial Printer", ["%print%", "%litho%", "%press%", "%publishing%"]),
            ("Sign Shop", ["%sign%", "%banner%", "%awning%"])
        ]

        for rubro_destino, patrones in reglas_distribucion:
            cond_like = " OR ".join(["LOWER(company_name) LIKE ?"] * len(patrones))
            c.execute(f"""
                UPDATE leads_b2b
                SET industry = ?, sub_category = ?
                WHERE industry IN ('General Contractor', 'Construction & Home Services', 'HVAC & Plumbing', 'Electrical, Solar & Security', 'Real Estate, Legal & Finance', 'Healthcare, Dental & Wellness', 'Auto, Towing & Logistics', 'Tech, Marketing & Commercial')
                  AND ({cond_like})
            """, [rubro_destino, rubro_destino] + patrones)

        conn.commit()
        conn.close()
    except Exception:
        pass

indexar_y_unificar_rubros_sql()

@st.cache_data(ttl=600)
def obtener_conteos_en_vivo():
    conteos = {r: 0 for r in RUBROS_95}
    total_fmcsa = 0
    total_mega = 0
    try:
        conn1 = sqlite3.connect("perfiles_fmcsa.db")
        total_fmcsa = conn1.execute("SELECT COUNT(*) FROM empresas").fetchone()[0]
        conn1.close()
    except Exception:
        pass
    conteos["Trucking & Logistics (FMCSA)"] = total_fmcsa

    try:
        conn2 = sqlite3.connect(DB_MEGA_PATH)
        total_mega = conn2.execute("SELECT COUNT(*) FROM leads_b2b").fetchone()[0]
        filas_ind = conn2.execute("""
            SELECT COALESCE(NULLIF(sub_category, ''), industry) AS cat, COUNT(*)
            FROM leads_b2b
            GROUP BY cat
        """).fetchall()
        for cat_name, cant in filas_ind:
            if cat_name in conteos:
                conteos[cat_name] += cant
        conn2.close()
    except Exception:
        pass

    total_global = total_fmcsa + total_mega
    conteos["🌐 All Categories (Global Search)"] = total_mega
    return total_global, conteos

total_general_en_vivo, conteos_por_industria = obtener_conteos_en_vivo()

# ==============================================================================
# 🏢 BARRA LATERAL IZQUIERDA (SIEMPRE VISIBLE CON LAS 96 BASES DE DATOS)
# ==============================================================================
st.sidebar.title("🏢 Select Industry (96 Total)")

st.sidebar.markdown(
    f"""
    <div style="background-color:#1E293B; padding:12px; border-radius:8px; text-align:center; margin-bottom:12px; border: 1px solid #334155;">
        <p style="color:#94A3B8; font-size:11px; margin:0; text-transform:uppercase; font-weight:bold;">Total Profiles Verified</p>
        <h2 style="color:#38BDF8; margin:4px 0 0 0; font-size:24px;">{total_general_en_vivo:,}</h2>
        <p style="color:#10B981; font-size:11px; margin:2px 0 0 0; font-weight:bold;">✅ 100% Verified Active</p>
    </div>
    """,
    unsafe_allow_html=True
)

if es_suscriptor_pro:
    st.sidebar.success(f"💎 Plan PRO Activo ({usuario_actual['plan'].upper()}) — Ilimitado")
else:
    st.sidebar.info(f"🎁 Búsquedas Gratis: **{busquedas_restantes} de {LIMITE_BUSQUEDAS_GRATIS}** disponibles")
    st.sidebar.progress(min(1.0, busquedas_usadas / LIMITE_BUSQUEDAS_GRATIS))

filtro_sidebar = st.sidebar.text_input("🔍 Filtrar industria en la lista:", placeholder="Ej: Plumbing, Law, Dental, Solar...")

rubros_ordenados = sorted(RUBROS_95, key=lambda r: conteos_por_industria.get(r, 0), reverse=True)
todas_las_opciones = ["Trucking & Logistics (FMCSA)", "🌐 All Categories (Global Search)"] + rubros_ordenados

if filtro_sidebar.strip():
    opciones_filtradas = [op for op in todas_las_opciones if filtro_sidebar.strip().lower() in op.lower()]
    if not opciones_filtradas:
        opciones_filtradas = todas_las_opciones
else:
    opciones_filtradas = todas_las_opciones

industria = st.sidebar.radio(
    "Available Databases (Verified Profile Count):",
    opciones_filtradas,
    format_func=lambda op: f"{op} ({conteos_por_industria.get(op, 0):,} Verified)"
)

# ==============================================================================
# 🔝 BARRA SUPERIOR DERECHA (ESTILO HUNTER.IO / APOLLO / ZOOMINFO)
# ==============================================================================
col_titulo, col_top_der = st.columns([6.2, 3.8])

with col_titulo:
    st.title(f"🚀 B2B Lead Database: {industria}")

with col_top_der:
    st.write("")
    if not usuario_actual:
        b_top1, b_top2, b_top3 = st.columns([1.2, 1.3, 1.2])
        if b_top1.button("🔐 Iniciar Sesión", use_container_width=True):
            st.session_state.mostrar_panel_auth = "login"
        if b_top2.button("✨ Crear Cuenta", use_container_width=True, type="primary"):
            st.session_state.mostrar_panel_auth = "registro"
        if b_top3.button("💎 Planes Pro", use_container_width=True):
            st.session_state.mostrar_panel_auth = "suscripcion"
    else:
        b_u1, b_u2, b_u3 = st.columns([1.6, 1.3, 1.0])
        if not es_suscriptor_pro:
            b_u1.markdown(f"**👤 {usuario_actual['nombre'][:15]}**\n`{busquedas_restantes}/{LIMITE_BUSQUEDAS_GRATIS} Gratis`")
        else:
            b_u1.markdown(f"**💎 {usuario_actual['nombre'][:15]}**\n`PRO ACTIVO`")
        if b_u2.button("💳 Suscripción", use_container_width=True, type="primary"):
            st.session_state.mostrar_panel_auth = "suscripcion"
        if b_u3.button("🚪 Salir", use_container_width=True):
            st.session_state.usuario_activo = None
            st.session_state.mostrar_panel_auth = None
            st.rerun()

# ==============================================================================
# 🪟 PANEL DESPLEGABLE DE CUENTA / OTP / SUSCRIPCIÓN
# ==============================================================================
def renderizar_panel_cuenta_y_suscripcion(forzar_paywall=False):
    modo = "suscripcion" if forzar_paywall else st.session_state.mostrar_panel_auth
    if not modo:
        return

    with st.container(border=True):
        c_head1, c_head2 = st.columns([8.5, 1.5])
        if not forzar_paywall:
            if c_head2.button("✖️ Cerrar Ventana", use_container_width=True):
                st.session_state.mostrar_panel_auth = None
                st.rerun()

        if modo == "login":
            c_head1.subheader("🔐 Iniciar Sesión en tu Cuenta")
            c1, c2 = st.columns(2)
            email_in = c1.text_input("Correo Electrónico:", placeholder="tu@empresa.com", key="login_email")
            pass_in = c2.text_input("Contraseña:", type="password", placeholder="••••••••", key="login_pass")

            b1, b2, b3 = st.columns(3)
            if b1.button("🚀 Entrar a mi Cuenta", type="primary", use_container_width=True):
                user = obtener_usuario(email_in)
                if not user or user["password_hash"] != encriptar_password(pass_in):
                    st.error("❌ Correo o contraseña incorrectos.")
                elif user["verificado"] == 0:
                    nuevo_otp = str(random.randint(100000, 999999))
                    conn = sqlite3.connect(USERS_DB)
                    conn.execute("UPDATE usuarios SET otp_codigo = ? WHERE email = ?", (nuevo_otp, user["email"]))
                    conn.commit()
                    conn.close()
                    _, msg_info = enviar_correo_otp(user["email"], user["nombre"], nuevo_otp)
                    st.session_state.email_pendiente_otp = user["email"]
                    st.session_state.mensaje_otp_info = msg_info
                    st.session_state.mostrar_panel_auth = "otp"
                    st.rerun()
                else:
                    st.session_state.usuario_activo = user["email"]
                    st.session_state.mostrar_panel_auth = None
                    st.rerun()

            if b2.button("✨ No tengo cuenta (Crear Cuenta)", use_container_width=True):
                st.session_state.mostrar_panel_auth = "registro"
                st.rerun()

            if b3.button("❓ Olvidé mi Contraseña", use_container_width=True):
                st.session_state.mostrar_panel_auth = "olvide"
                st.rerun()

        elif modo == "registro":
            c_head1.subheader("✨ Crear Cuenta Gratis (Desbloquea 5 Búsquedas de Prueba)")
            r1, r2 = st.columns(2)
            nombre_reg = r1.text_input("Nombre Completo:", placeholder="Juan Hernández")
            email_reg = r2.text_input("Correo Electrónico Corporativo o Personal:", placeholder="tu@correo.com")
            r3, r4 = st.columns(2)
            pass_reg1 = r3.text_input("Crear Contraseña:", type="password", placeholder="Mínimo 6 caracteres")
            pass_reg2 = r4.text_input("Confirmar Contraseña:", type="password", placeholder="Repite tu contraseña")

            br1, br2 = st.columns(2)
            if br1.button("📩 Crear Cuenta y Enviar Código OTP de 6 Dígitos", type="primary", use_container_width=True):
                email_clean = email_reg.lower().strip()
                if not nombre_reg.strip() or "@" not in email_clean or "." not in email_clean:
                    st.error("⚠️ Ingresa un nombre y correo electrónico válidos.")
                elif len(pass_reg1) < 6:
                    st.error("⚠️ La contraseña debe tener al menos 6 caracteres.")
                elif pass_reg1 != pass_reg2:
                    st.error("⚠️ Las contraseñas no coinciden.")
                elif obtener_usuario(email_clean):
                    st.error("⚠️ Este correo ya está registrado. Inicia sesión.")
                else:
                    codigo_otp = str(random.randint(100000, 999999))
                    conn = sqlite3.connect(USERS_DB)
                    conn.execute(
                        "INSERT INTO usuarios (email, nombre, password_hash, verificado, otp_codigo, plan, busquedas_usadas) VALUES (?, ?, ?, 0, ?, 'free', 0)",
                        (email_clean, nombre_reg.strip(), encriptar_password(pass_reg1), codigo_otp)
                    )
                    conn.commit()
                    conn.close()
                    _, msg_info = enviar_correo_otp(email_clean, nombre_reg.strip(), codigo_otp, "confirmar tu cuenta")
                    st.session_state.email_pendiente_otp = email_clean
                    st.session_state.mensaje_otp_info = msg_info
                    st.session_state.mostrar_panel_auth = "otp"
                    st.rerun()

            if br2.button("🔐 Ya tengo cuenta (Iniciar Sesión)", use_container_width=True):
                st.session_state.mostrar_panel_auth = "login"
                st.rerun()

        elif modo == "otp":
            c_head1.subheader("📩 Confirma tu Correo Electrónico (Código OTP de 6 Dígitos)")
            st.write(f"Verificando cuenta: **{st.session_state.email_pendiente_otp}**")
            if st.session_state.mensaje_otp_info:
                st.info(st.session_state.mensaje_otp_info)

            otp_in = st.text_input("Escribe el código de 6 dígitos enviado a tu correo:", max_chars=6, placeholder="123456")
            bo1, bo2 = st.columns(2)
            if bo1.button("✅ Confirmar Código OTP y Activar Cuenta", type="primary", use_container_width=True):
                user = obtener_usuario(st.session_state.email_pendiente_otp)
                if user and otp_in.strip() == user["otp_codigo"]:
                    conn = sqlite3.connect(USERS_DB)
                    conn.execute("UPDATE usuarios SET verificado = 1, otp_codigo = NULL WHERE email = ?", (user["email"],))
                    conn.commit()
                    conn.close()
                    st.session_state.usuario_activo = user["email"]
                    st.session_state.mostrar_panel_auth = None
                    st.success("🎉 ¡Cuenta confirmada! Ahora tienes 5 búsquedas gratuitas.")
                    st.rerun()
                else:
                    st.error("❌ Código OTP incorrecto. Verifica los 6 dígitos.")

            if bo2.button("🔄 Reenviar nuevo código de 6 dígitos", use_container_width=True):
                user = obtener_usuario(st.session_state.email_pendiente_otp)
                if user:
                    nuevo_otp = str(random.randint(100000, 999999))
                    conn = sqlite3.connect(USERS_DB)
                    conn.execute("UPDATE usuarios SET otp_codigo = ? WHERE email = ?", (nuevo_otp, user["email"]))
                    conn.commit()
                    conn.close()
                    _, msg_info = enviar_correo_otp(user["email"], user["nombre"], nuevo_otp)
                    st.session_state.mensaje_otp_info = msg_info
                    st.rerun()

        elif modo == "olvide":
            c_head1.subheader("🔑 Recuperar mi Contraseña")
            email_rec = st.text_input("Ingresa tu correo electrónico registrado:", value=st.session_state.email_pendiente_otp)
            if st.button("📨 Enviar Código de Recuperación (6 Dígitos)"):
                user = obtener_usuario(email_rec)
                if not user:
                    st.error("❌ Ese correo no está registrado en el sistema.")
                else:
                    nuevo_otp = str(random.randint(100000, 999999))
                    conn = sqlite3.connect(USERS_DB)
                    conn.execute("UPDATE usuarios SET otp_codigo = ? WHERE email = ?", (nuevo_otp, user["email"]))
                    conn.commit()
                    conn.close()
                    _, msg_info = enviar_correo_otp(user["email"], user["nombre"], nuevo_otp, "recuperar tu contraseña")
                    st.session_state.email_pendiente_otp = user["email"]
                    st.session_state.mensaje_otp_info = msg_info
                    st.rerun()

            if st.session_state.mensaje_otp_info:
                st.info(st.session_state.mensaje_otp_info)
                o1, o2, o3 = st.columns(3)
                otp_rec = o1.text_input("Código OTP de 6 dígitos:", max_chars=6)
                np1 = o2.text_input("Nueva Contraseña:", type="password")
                np2 = o3.text_input("Confirmar Contraseña:", type="password")
                if st.button("💾 Guardar Nueva Contraseña", type="primary"):
                    user = obtener_usuario(st.session_state.email_pendiente_otp)
                    if not user or otp_rec.strip() != user["otp_codigo"]:
                        st.error("❌ Código OTP incorrecto.")
                    elif len(np1) < 6 or np1 != np2:
                        st.error("⚠️ Las contraseñas deben coincidir y tener mínimo 6 caracteres.")
                    else:
                        conn = sqlite3.connect(USERS_DB)
                        conn.execute(
                            "UPDATE usuarios SET password_hash = ?, verificado = 1, otp_codigo = NULL WHERE email = ?",
                            (encriptar_password(np1), user["email"])
                        )
                        conn.commit()
                        conn.close()
                        st.session_state.mensaje_otp_info = ""
                        st.session_state.mostrar_panel_auth = "login"
                        st.success("✅ Contraseña actualizada. Ya puedes iniciar sesión.")
                        st.rerun()

        elif modo == "suscripcion":
            if forzar_paywall:
                st.markdown(
                    f"""
                    <div class="bloqueo-box">
                        <h2 style="color:#F8FAFC; margin:0;">🔒 Has consumido tus {LIMITE_BUSQUEDAS_GRATIS} búsquedas gratuitas</h2>
                        <p style="color:#94A3B8; font-size:16px; margin-top:8px;">
                            Para seguir buscando sin límites, ver los <b>Teléfonos Directos y Correos Electrónicos completos sin candado</b> y descargar archivos CSV/Excel para tu CRM, elige un plan de suscripción:
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                c_head1.subheader("💎 Planes de Suscripción Pro (Desbloquea Teléfonos, Emails y Búsquedas Ilimitadas)")

            if not usuario_actual:
                st.warning("💡 ¿Aún no has creado tu cuenta gratis? Crea una cuenta arriba a la derecha para obtener 5 búsquedas adicionales o activa tu suscripción.")
                c_inv1, c_inv2 = st.columns(2)
                if c_inv1.button("✨ Crear Cuenta Gratis (5 Búsquedas)", use_container_width=True, type="primary"):
                    st.session_state.mostrar_panel_auth = "registro"
                    st.rerun()
                if c_inv2.button("🔐 Ya tengo cuenta (Iniciar Sesión)", use_container_width=True):
                    st.session_state.mostrar_panel_auth = "login"
                    st.rerun()
                st.markdown("---")

            p_col1, p_col2 = st.columns(2)
            with p_col1:
                st.markdown(
                    f"""
                    <div style="background-color:#1E293B; padding:24px; border-radius:12px; border: 2px solid #3B82F6; text-align:center;">
                        <h3 style="color:#60A5FA; margin-bottom:5px;">📅 Plan Mensual Pro</h3>
                        <h1 style="color:white; margin:8px 0;">{PRECIO_MENSUAL}</h1>
                        <p style="color:#CBD5E1; font-size:14px;">
                            ✅ Búsquedas ilimitadas en las 96 Industrias<br>
                            ✅ <b>Teléfonos Directos y Emails 100% visibles (Sin Locked)</b><br>
                            ✅ Exportación directa a Excel / CSV<br>
                            ✅ Cancela en cualquier momento
                        </p>
                        <a href="{LINK_PAGO_MENSUAL}" target="_blank" style="background-color:#3B82F6; color:white; padding:12px 26px; border-radius:6px; text-decoration:none; font-weight:bold; display:inline-block; margin-top:10px;">Suscribirme al Plan Mensual ({PRECIO_MENSUAL})</a>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with p_col2:
                st.markdown(
                    f"""
                    <div style="background-color:#111827; padding:24px; border-radius:12px; border: 2px solid #EC4899; text-align:center;">
                        <h3 style="color:#F472B6; margin-bottom:5px;">🏆 Plan Anual VIP (Ahorra 65%)</h3>
                        <h1 style="color:white; margin:8px 0;">{PRECIO_ANUAL}</h1>
                        <p style="color:#CBD5E1; font-size:14px;">
                            ✅ Acceso Total durante 12 meses a los 409,530+ Perfiles<br>
                            ✅ <b>Todos los Teléfonos, Celulares y Correos desbloqueados</b><br>
                            ✅ Descargas masivas ilimitadas para llamadas y frío<br>
                            ✅ Actualizaciones estatales incluidas
                        </p>
                        <a href="{LINK_PAGO_ANUAL}" target="_blank" style="background-color:#EC4899; color:white; padding:12px 26px; border-radius:6px; text-decoration:none; font-weight:bold; display:inline-block; margin-top:10px;">Suscribirme al Plan Anual ({PRECIO_ANUAL})</a>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("##### 🔑 ¿Ya te suscribiste? Ingresa tu clave de activación para quitar todos los candados `(Locked)`:")
            k1, k2 = st.columns([3, 1.2])
            clave_sub = k1.text_input("Clave de Licencia Pro:", placeholder="Ej: PRO-MONTHLY-2026 o PRO-ANNUAL-2026", label_visibility="collapsed")
            if k2.button("⚡ Activar Plan Pro", type="primary", use_container_width=True):
                cod = clave_sub.strip().upper()
                if cod in CODIGOS_PLAN_MENSUAL or cod in CODIGOS_PLAN_ANUAL:
                    nuevo_p = "annual" if cod in CODIGOS_PLAN_ANUAL else "monthly"
                    if usuario_actual:
                        actualizar_plan_db(usuario_actual["email"], nuevo_p)
                    else:
                        st.session_state.usuario_activo = "vip@procustomer.com"
                        conn = sqlite3.connect(USERS_DB)
                        conn.execute("INSERT OR REPLACE INTO usuarios (email, nombre, password_hash, verificado, plan, busquedas_usadas) VALUES ('vip@procustomer.com', 'VIP Pro Member', '', 1, ?, 0)", (nuevo_p,))
                        conn.commit()
                        conn.close()
                    st.session_state.mostrar_panel_auth = None
                    st.success("🎉 ¡Suscripción Pro Activada! Todos los teléfonos, correos y descargas están desbloqueados.")
                    st.rerun()
                else:
                    st.error("❌ Clave inválida. Revisa el recibo de tu suscripción.")

if st.session_state.mostrar_panel_auth:
    renderizar_panel_cuenta_y_suscripcion(forzar_paywall=False)

# ==============================================================================
# 🔎 PANEL DE BÚSQUEDA AVANZADA DE 6 CAMPOS (VISIBLE PARA TODOS AL ENTRAR)
# ==============================================================================
st.markdown(
    "**Verified Active Commercial Profiles: Legal Company Name, Category, Owner/Principal, Direct Phone, Email, Street Address, City, State, Zip Code & Status.** *(Contact fields partially masked `••••• (Locked)` in Free Plan)*"
)

st.markdown("##### 🔎 Búsqueda Avanzada por Perfil Específico")
f1, f2, f3 = st.columns(3)
b_empresa = f1.text_input("🏢 Company Name:", placeholder="Ej: Express, Drain Genie, Signature...")
b_persona = f2.text_input("👤 Person / Owner Name:", placeholder="Ej: John, Carlos, Michael...")
b_telefono = f3.text_input("📞 Phone Number / Area Code:", placeholder="Ej: 305, 718, 480...")

f4, f5, f6 = st.columns(3)
b_ciudad = f4.text_input("🏙️ City:", placeholder="Ej: Miami, Orlando, Houston, Brooklyn...")
b_estado = f5.text_input("🗺️ State (e.g. FL, TX, NY, CA):", placeholder="Ej: FL, TX, NY, AZ...")
b_zip = f6.text_input("📮 Zip Code:", placeholder="Ej: 33101, 85201, 10001...")

# ==============================================================================
# 🧮 CONTROLADOR DE LAS 5 BÚSQUEDAS GRATIS (MODELO APOLLO / HUNTER / ZOOMINFO)
# ==============================================================================
firma_busqueda = f"{industria}|{b_empresa.strip()}|{b_persona.strip()}|{b_telefono.strip()}|{b_ciudad.strip()}|{b_estado.strip()}|{b_zip.strip()}"
uso_algun_filtro = any([b_empresa.strip(), b_persona.strip(), b_telefono.strip(), b_ciudad.strip(), b_estado.strip(), b_zip.strip()])

if not es_suscriptor_pro:
    if st.session_state.ultima_firma_busqueda == "":
        st.session_state.ultima_firma_busqueda = firma_busqueda
    elif firma_busqueda != st.session_state.ultima_firma_busqueda and uso_algun_filtro:
        st.session_state.ultima_firma_busqueda = firma_busqueda
        if usuario_actual:
            incrementar_busqueda_db(usuario_actual["email"])
            usuario_actual = obtener_usuario(usuario_actual["email"])
            busquedas_usadas = usuario_actual["busquedas_usadas"]
        else:
            st.session_state.busquedas_invitado += 1
            busquedas_usadas = st.session_state.busquedas_invitado

    if busquedas_usadas > LIMITE_BUSQUEDAS_GRATIS:
        renderizar_panel_cuenta_y_suscripcion(forzar_paywall=True)
        st.stop()

# ==============================================================================
# 1. TABLA DE PERFILES: TRUCKING & LOGISTICS (FMCSA - 111,073 CARRIERS)
# ==============================================================================
if industria == "Trucking & Logistics (FMCSA)":
    conn = sqlite3.connect("perfiles_fmcsa.db")
    cursor = conn.cursor()

    condiciones = ["1=1"]
    params = []

    if b_empresa.strip():
        condiciones.append("(Empresa_Legal LIKE ? OR Nombre_Comercial_DBA LIKE ? OR DOT_Numero LIKE ?)")
        p_emp = f"%{b_empresa.strip()}%"
        params.extend([p_emp, p_emp, p_emp])
    if b_persona.strip():
        condiciones.append("(Dueno_Principal LIKE ? OR Segundo_Directivo LIKE ?)")
        p_per = f"%{b_persona.strip()}%"
        params.extend([p_per, p_per])
    if b_telefono.strip():
        digs_tel = re.sub(r'\D', '', b_telefono.strip())
        p_tel = f"%{digs_tel if digs_tel else b_telefono.strip()}%"
        condiciones.append("(Celular_Directo LIKE ? OR Telefono_Oficina LIKE ?)")
        params.extend([p_tel, p_tel])
    if b_ciudad.strip():
        condiciones.append("Ciudad LIKE ?")
        params.append(f"%{b_ciudad.strip()}%")
    if b_estado.strip():
        condiciones.append("Estado LIKE ?")
        params.append(f"%{b_estado.strip().upper()}%")
    if b_zip.strip():
        condiciones.append("Codigo_Postal LIKE ?")
        params.append(f"%{b_zip.strip()}%")

    where_sql = " WHERE " + " AND ".join(condiciones)
    total_matching = cursor.execute(f"SELECT COUNT(*) FROM empresas {where_sql}", params).fetchone()[0]
    limite_filas = 10000 if es_suscriptor_pro else 250
    df = pd.read_sql_query(f"SELECT * FROM empresas {where_sql} LIMIT {limite_filas}", conn, params=params)
    conn.close()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Verified Active Carriers", f"{total_matching:,} Verified")
    m2.metric("Geographic Coverage", "All 50 US States")
    m3.metric("Data Depth", "17 Commercial Fields")
    m4.metric("Subscription Plans", f"{PRECIO_MENSUAL} | {PRECIO_ANUAL}")

    if "Celular_Directo" in df.columns and not es_suscriptor_pro:
        df["Celular_Directo"] = df["Celular_Directo"].apply(lambda x: ocultar_dato(x, 5))
        df["Telefono_Oficina"] = df["Telefono_Oficina"].apply(lambda x: ocultar_dato(x, 5))
        df["Email"] = df["Email"].apply(lambda x: ocultar_dato(x, 4))
    df["Estatus_Verificacion"] = "✅ Verified Active"

    if es_suscriptor_pro:
        st.download_button("📥 Descargar CSV Completo Desbloqueado (PRO)", data=df.to_csv(index=False).encode("utf-8"), file_name="FMCSA_Verified_Leads.csv", mime="text/csv")
    else:
        c_aviso, c_btn_unl = st.columns([7, 3])
        c_aviso.caption(f"Mostrando vista previa de {len(df)} registros de **{total_matching:,}** perfiles verificados. Teléfonos y correos parcialmente ocultos (`••••• (Locked)`).")
        if c_btn_unl.button("🔓 Desbloquear Teléfonos y Emails Completos", use_container_width=True):
            st.session_state.mostrar_panel_auth = "suscripcion"
            st.rerun()

    st.dataframe(df, use_container_width=True, height=450)

# ==============================================================================
# 2. TABLA DE PERFILES: LAS 95 INDUSTRIAS Y BÚSQUEDA GLOBAL
# ==============================================================================
else:
    conn = sqlite3.connect(DB_MEGA_PATH)
    cursor = conn.cursor()

    es_global = (industria == "🌐 All Categories (Global Search)")
    condiciones = []
    params = []

    if not es_global:
        condiciones.append("(industry = ? OR sub_category = ?)")
        params.extend([industria, industria])
    if b_empresa.strip():
        condiciones.append("company_name LIKE ?")
        params.append(f"%{b_empresa.strip()}%")
    if b_persona.strip():
        condiciones.append("contact_name LIKE ?")
        params.append(f"%{b_persona.strip()}%")
    if b_telefono.strip():
        digs_tel = re.sub(r'\D', '', b_telefono.strip())
        if len(digs_tel) == 3:
            condiciones.append("(phone LIKE ? OR phone LIKE ?)")
            params.extend([f"({digs_tel})%", f"%{digs_tel}%"])
        else:
            condiciones.append("phone LIKE ?")
            params.append(f"%{b_telefono.strip()}%")
    if b_ciudad.strip():
        condiciones.append("city LIKE ?")
        params.append(f"%{b_ciudad.strip()}%")
    if b_estado.strip():
        condiciones.append("state LIKE ?")
        params.append(f"%{b_estado.strip().upper()}%")
    if b_zip.strip():
        condiciones.append("zip_code LIKE ?")
        params.append(f"%{b_zip.strip()}%")

    where_sql = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
    total_matching_ind = cursor.execute(f"SELECT COUNT(*) FROM leads_b2b {where_sql}", params).fetchone()[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Verified Unique Businesses", f"{total_matching_ind:,} Verified")
    m2.metric("Geographic Coverage", "All 50 US States")
    m3.metric("Data Depth", "10 Commercial Fields")
    m4.metric("Subscription Plans", f"{PRECIO_MENSUAL} | {PRECIO_ANUAL}")

    rubro_columna = "COALESCE(sub_category, industry)" if es_global else f"'{industria}'"
    limite_filas = 15000 if es_suscriptor_pro else 500

    query = f"""
        SELECT company_name AS Empresa_Legal,
               {rubro_columna} AS Rubro,
               contact_name AS Dueno_Principal,
               phone AS Telefono_Directo,
               email AS Email,
               COALESCE(address, 'On File (State Registry)') AS Direccion_Calle,
               city AS Ciudad,
               state AS Estado,
               zip_code AS Codigo_Postal,
               '✅ Verified Active' AS Estatus_Verificacion
        FROM leads_b2b
        {where_sql}
        ORDER BY CASE WHEN contact_name NOT IN ('Principal / Registered Officer', 'N/A', '-') THEN 0 ELSE 1 END, id DESC
        LIMIT {limite_filas}
    """
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if not df.empty:
        df["Dueno_Principal"] = df.apply(limpiar_dueno_en_vista, axis=1)
        df["Estado"] = df.apply(corregir_estado_en_vista, axis=1)
        if not es_suscriptor_pro:
            df["Telefono_Directo"] = df["Telefono_Directo"].apply(lambda x: ocultar_dato(x, 6))
            df["Email"] = df["Email"].apply(lambda x: ocultar_dato(x, 4))

    if es_suscriptor_pro:
        st.download_button(f"📥 Descargar CSV Completo Desbloqueado ({len(df):,} Perfiles)", data=df.to_csv(index=False).encode("utf-8"), file_name=f"{industria.replace(' ', '_')}_Verified.csv", mime="text/csv")
    else:
        c_aviso, c_btn_unl = st.columns([7, 3])
        c_aviso.caption(f"Mostrando vista previa de {len(df)} registros de **{total_matching_ind:,}** perfiles verificados en **{industria}**. Datos de contacto parcialmente ocultos (`••••• (Locked)`).")
        if c_btn_unl.button("🔓 Desbloquear Información Completa (Suscribirse)", use_container_width=True):
            st.session_state.mostrar_panel_auth = "suscripcion"
            st.rerun()

    st.dataframe(df, use_container_width=True, height=450)
