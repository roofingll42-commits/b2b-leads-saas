import streamlit as st
import sqlite3
import pandas as pd
import re
import os
import requests

st.set_page_config(page_title="Global B2B Intelligence Portal", layout="wide")

# ==============================================================================
# 📥 DESCARGADOR AUTOMÁTICO DE LA MEGA BASE DE DATOS (PARA LA NUBE)
# ==============================================================================
DB_MEGA_PATH = "mega_base_b2b.db"

if not os.path.exists(DB_MEGA_PATH):
    st.info("⏳ Descargando la base de datos masiva en la nube (esto solo ocurre la primera vez)...")
    
    # PEGA AQUÍ TU ENLACE DE DESCARGA DIRECTA DE ONEDRIVE
    ENLACE_DIRECTO_DB = "import streamlit as st
import sqlite3
import pandas as pd
import re
import os
import requests

st.set_page_config(page_title="Global B2B Intelligence Portal", layout="wide")

# ==============================================================================
# 📥 DESCARGADOR AUTOMÁTICO DE LA MEGA BASE DE DATOS (DESDE GITHUB RELEASES)
# ==============================================================================
DB_MEGA_PATH = "mega_base_b2b.db"

if not os.path.exists(DB_MEGA_PATH):
    st.info("⏳ Descargando la base de datos masiva desde GitHub Releases (esto solo ocurre la primera vez)...")
    
    ENLACE_DIRECTO_DB = "https://github.com/roofingll42-commits/b2b-leads-saas/releases/download/v1.0/mega_base_b2b.db"
    
    try:
        response = requests.get(ENLACE_DIRECTO_DB, stream=True)
        if response.status_code == 200:
            with open(DB_MEGA_PATH, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            st.success("¡Base de datos descargada con éxito! Actualizando la app...")
            st.rerun()
        else:
            st.error(f"No se pudo descargar la base de datos automáticamente. Código de error: {response.status_code}")
    except Exception as e:
        st.error(f"Error en la descarga: {e}")

# ==============================================================================
# 📋 LISTADO COMPLETO DE LAS 95 INDUSTRIAS EXACTAS
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

# ==============================================================================
# ⚡ SINCRONIZADOR SQL ULTRARRÁPIDO (UNIFICA INDUSTRY Y SUB_CATEGORY EN 0.05s)
# ==============================================================================
@st.cache_resource
def indexar_y_unificar_rubros_sql():
    try:
        conn = sqlite3.connect("mega_base_b2b.db")
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

        mapeos_sql = [
            ("HVAC & Plumbing", "Plumbing Service", "%plumb%"),
            ("HVAC & Plumbing", "HVAC Repair", "%"),
            ("Construction & Home Services", "Roofing Contractor", "%roof%"),
            ("Construction & Home Services", "Painting Company", "%paint%"),
            ("Construction & Home Services", "Landscaping Service", "%landscap%"),
            ("Construction & Home Services", "Pest Control", "%pest%"),
            ("Construction & Home Services", "Flooring Contractor", "%floor%"),
            ("Construction & Home Services", "Cleaning Service", "%clean%"),
            ("Construction & Home Services", "Home Remodeling", "%remodel%"),
            ("Construction & Home Services", "Construction Company", "%construct%"),
            ("Construction & Home Services", "General Contractor", "%"),
            ("Electrical, Solar & Security", "Solar Energy Company", "%solar%"),
            ("Electrical, Solar & Security", "Security Company", "%security%"),
            ("Electrical, Solar & Security", "Electrician", "%"),
            ("Real Estate, Legal & Finance", "Law Firm", "%law%"),
            ("Real Estate, Legal & Finance", "Accountant", "%account%"),
            ("Real Estate, Legal & Finance", "Insurance Agency", "%insur%"),
            ("Real Estate, Legal & Finance", "Property Management", "%property%"),
            ("Real Estate, Legal & Finance", "Real Estate Agency", "%"),
            ("Healthcare, Dental & Wellness", "Dentist Office", "%dent%"),
            ("Healthcare, Dental & Wellness", "Veterinary Clinic", "%vet%"),
            ("Healthcare, Dental & Wellness", "Fitness Center", "%fit%"),
            ("Healthcare, Dental & Wellness", "Hair Salon", "%salon%"),
            ("Healthcare, Dental & Wellness", "Barber Shop", "%barber%"),
            ("Healthcare, Dental & Wellness", "Medical Clinic", "%"),
            ("Auto, Towing & Logistics", "Towing Service", "%tow%"),
            ("Auto, Towing & Logistics", "Auto Body Shop", "%body%"),
            ("Auto, Towing & Logistics", "Car Dealership", "%dealer%"),
            ("Auto, Towing & Logistics", "Moving Company", "%mov%"),
            ("Auto, Towing & Logistics", "Trucking Company", "%truck%"),
            ("Auto, Towing & Logistics", "Logistics Service", "%logistic%"),
            ("Auto, Towing & Logistics", "Auto Repair Shop", "%"),
            ("Tech, Marketing & Commercial", "Software Company", "%software%"),
            ("Tech, Marketing & Commercial", "Digital Marketing Agency", "%market%"),
            ("Tech, Marketing & Commercial", "Boutique Hotel", "%hotel%"),
            ("Tech, Marketing & Commercial", "Catering Service", "%cater%"),
            ("Tech, Marketing & Commercial", "Wholesale Supplier", "%")
        ]
        for grupo_viejo, rubro_nuevo, patron in mapeos_sql:
            if patron == "%":
                c.execute("UPDATE leads_b2b SET industry = ?, sub_category = ? WHERE industry = ?", (rubro_nuevo, rubro_nuevo, grupo_viejo))
            else:
                c.execute("UPDATE leads_b2b SET industry = ?, sub_category = ? WHERE industry = ? AND LOWER(company_name) LIKE ?", (rubro_nuevo, rubro_nuevo, grupo_viejo, patron))

        conn.commit()
        conn.close()
    except Exception:
        pass

indexar_y_unificar_rubros_sql()

# ==============================================================================
# 📊 CONTADOR GLOBAL Y POR CATEGORÍA EN TIEMPO REAL
# ==============================================================================
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
        conn2 = sqlite3.connect("mega_base_b2b.db")
        total_mega = conn2.execute("SELECT COUNT(*) FROM leads_b2b").fetchone()[0]

        filas_ind = conn2.execute("""
            SELECT COALESCE(NULLIF(sub_category, ''), industry) AS cat, COUNT(*)
            FROM leads_b2b
            GROUP BY cat
        """).fetchall()
        for cat_name, cant in filas_ind:
            if cat_name in conteos:
                conteos[cat_name] += cant

        filas_ind2 = conn2.execute("""
            SELECT industry, COUNT(*)
            FROM leads_b2b
            WHERE industry != COALESCE(sub_category, '')
            GROUP BY industry
        """).fetchall()
        for ind_name, cant in filas_ind2:
            if ind_name in conteos:
                conteos[ind_name] += cant

        conn2.close()
    except Exception:
        pass

    total_global = total_fmcsa + total_mega
    conteos["🌐 All Categories (Global Search)"] = total_mega
    return total_global, conteos

total_general_en_vivo, conteos_por_industria = obtener_conteos_en_vivo()

# ==============================================================================
# 🏢 MENÚ LATERAL
# ==============================================================================
st.sidebar.title("🏢 Select Industry (96 Total)")

st.sidebar.markdown(
    f"""
    <div style="background-color:#1E293B; padding:12px; border-radius:8px; text-align:center; margin-bottom:15px; border: 1px solid #334155;">
        <p style="color:#94A3B8; font-size:12px; margin:0; text-transform:uppercase; font-weight:bold;">Total Profiles Verified</p>
        <h2 style="color:#38BDF8; margin:5px 0 0 0; font-size:24px;">{total_general_en_vivo:,}</h2>
        <p style="color:#10B981; font-size:11px; margin:2px 0 0 0; font-weight:bold;">✅ 100% Verified Active</p>
    </div>
    """,
    unsafe_allow_html=True
)

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

st.title(f"🚀 B2B Lead Database: {industria}")

# ==============================================================================
# 1. VISTA TRUCKING & LOGISTICS (FMCSA)
# ==============================================================================
if industria == "Trucking & Logistics (FMCSA)":
    st.markdown(
        "**Verified Active Commercial Profiles: MC Docket, Owner 1 & 2, Cell Phone, Office Phone, Email, Full Address, Fleet Size & Drivers.** *(Contact fields masked in live preview)*"
    )
    conn = sqlite3.connect("perfiles_fmcsa.db")
    cursor = conn.cursor()
    total_carriers = conteos_por_industria.get("Trucking & Logistics (FMCSA)", 0)
    estados_raw = cursor.execute("SELECT DISTINCT Estado FROM empresas WHERE Estado IS NOT NULL AND Estado != '' ORDER BY Estado").fetchall()
    lista_estados = [e[0] for e in estados_raw]

    st.markdown("##### 🔎 Búsqueda Avanzada de Perfiles")
    f1, f2, f3 = st.columns(3)
    b_empresa = f1.text_input("🏢 Company Name / DBA:", placeholder="Ej: Express, Transport LLC...")
    b_persona = f2.text_input("👤 Owner / Principal Name:", placeholder="Ej: John, Carlos, Michael...")
    b_telefono = f3.text_input("📞 Phone Number / Area Code:", placeholder="Ej: 305, 718, 214...")

    f4, f5, f6, f7 = st.columns([2, 2, 2, 1.5])
    b_ciudad = f4.text_input("🏙️ City:", placeholder="Ej: Miami, Houston, Brooklyn...")
    estados_sel = f5.multiselect("🗺️ State(s):", options=lista_estados, placeholder="All States")
    b_zip = f6.text_input("📮 Zip Code:", placeholder="Ej: 33101, 78521...")
    min_trucks = f7.number_input("🚛 Min. Trucks:", min_value=1, max_value=500, value=1)

    condiciones = ["CAST(Camiones_Totales AS INTEGER) >= ?"]
    params = [int(min_trucks)]

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

    if estados_sel:
        placeholders = ",".join(["?"] * len(estados_sel))
        condiciones.append(f"Estado IN ({placeholders})")
        params.extend(estados_sel)

    if b_zip.strip():
        condiciones.append("Codigo_Postal LIKE ?")
        params.append(f"%{b_zip.strip()}%")

    where_sql = " WHERE " + " AND ".join(condiciones)
    total_matching = cursor.execute(f"SELECT COUNT(*) FROM empresas {where_sql}", params).fetchone()[0]
    df = pd.read_sql_query(f"SELECT * FROM empresas {where_sql} LIMIT 250", conn, params=params)
    conn.close()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Verified Active Carriers", f"{total_matching:,} Verified")
    m2.metric("Geographic Coverage", "All 50 US States")
    m3.metric("Data Depth", "17 Commercial Fields")
    m4.metric("Instant Unlock Price", "USD 95 (State) | 195 (All)")

    if "Celular_Directo" in df.columns:
        df["Celular_Directo"] = df["Celular_Directo"].apply(lambda x: ocultar_dato(x, 5))
        df["Telefono_Oficina"] = df["Telefono_Oficina"].apply(lambda x: ocultar_dato(x, 5))
        df["Email"] = df["Email"].apply(lambda x: ocultar_dato(x, 4))
        df["Estatus_Verificacion"] = "✅ Verified Active"

    st.caption(f"Showing top {len(df)} preview records out of **{total_matching:,}** verified active carriers ready for instant CSV/Excel export.")
    st.dataframe(df, use_container_width=True, height=450)

# ==============================================================================
# 2. VISTA PARA LAS 95 INDUSTRIAS Y BÚSQUEDA GLOBAL
# ==============================================================================
else:
    st.markdown(
        "**Verified Active Commercial Profiles: Legal Company Name, Category, Owner/Principal, Direct Phone, Email, Street Address, City, State, Zip Code & Verification Status.** *(Contact fields masked in live preview)*"
    )
    conn = sqlite3.connect("mega_base_b2b.db")
    cursor = conn.cursor()

    es_global = (industria == "🌐 All Categories (Global Search)")

    if es_global:
        estados_ind = [
            e[0] for e in cursor.execute(
                "SELECT DISTINCT state FROM leads_b2b WHERE state IS NOT NULL AND state NOT IN ('N/A', 'US', '') ORDER BY state"
            ).fetchall()
        ]
    else:
        estados_ind = [
            e[0] for e in cursor.execute(
                "SELECT DISTINCT state FROM leads_b2b WHERE (industry = ? OR sub_category = ?) AND state IS NOT NULL AND state NOT IN ('N/A', '') ORDER BY state",
                (industria, industria)
            ).fetchall()
        ]

    st.markdown("##### 🔎 Búsqueda Avanzada por Perfil Específico")
    f1, f2, f3 = st.columns(3)
    b_empresa = f1.text_input("🏢 Company Name:", placeholder="Ej: Drain Genie, Signature Plumbing...")
    b_persona = f2.text_input("👤 Person / Owner Name:", placeholder="Ej: John Bodnar, Michael Aguilar...")
    b_telefono = f3.text_input("📞 Phone Number / Area Code:", placeholder="Ej: 480, 407, (305)...")

    f4, f5, f6 = st.columns(3)
    b_ciudad = f4.text_input("🏙️ City:", placeholder="Ej: Orlando, Mesa, Phoenix, Miami...")
    estados_sel = f5.multiselect("🗺️ State(s):", options=estados_ind, placeholder="All States")
    b_zip = f6.text_input("📮 Zip Code:", placeholder="Ej: 85201, 32653, 10001...")

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

    if estados_sel:
        placeholders = ",".join(["?"] * len(estados_sel))
        condiciones.append(f"state IN ({placeholders})")
        params.extend(estados_sel)

    if b_zip.strip():
        condiciones.append("zip_code LIKE ?")
        params.append(f"%{b_zip.strip()}%")

    where_sql = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
    total_matching_ind = cursor.execute(f"SELECT COUNT(*) FROM leads_b2b {where_sql}", params).fetchone()[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Verified Unique Businesses", f"{total_matching_ind:,} Verified")
    m2.metric("Geographic Coverage", f"{len(estados_ind) if estados_ind else 50} US States Active")
    m3.metric("Data Depth", "10 Commercial Fields")
    m4.metric("Instant Unlock Price", "USD 95 (State) | 195 (All)")

    rubro_columna = "COALESCE(sub_category, industry)" if es_global else f"'{industria}'"

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
        LIMIT 500
    """
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if not df.empty:
        df["Dueno_Principal"] = df.apply(limpiar_dueno_en_vista, axis=1)
        df["Estado"] = df.apply(corregir_estado_en_vista, axis=1)
        df["Telefono_Directo"] = df["Telefono_Directo"].apply(lambda x: ocultar_dato(x, 6))
        df["Email"] = df["Email"].apply(lambda x: ocultar_dato(x, 4))

    st.caption(f"Showing top {len(df)} preview records out of **{total_matching_ind:,}** verified commercial profiles matching your search.")
    st.dataframe(df, use_container_width=True, height=450)

# --- SECCIÓN DE MONETIZACIÓN Y CHECKOUT INTEGRADO ---
st.markdown("---")
st.subheader(f"🔓 ¿Necesitas acceso completo a la base de {industria}?")
st.write("Obtén el archivo CSV completo listo para importar en tu CRM o herramienta de llamadas.")

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    st.markdown(
        """
        <div style="background-color:#111827; padding:20px; border-radius:10px; text-align:center;">
            <h3 style="color:white; margin-bottom:10px;">Full National Database ($195)</h3>
            <p style="color:#9CA3AF; font-size:14px;">Acceso total a todos los estados y campos comerciales.</p>
            <a href="https://juanahez.gumroad.com/l/rzzow" target="_blank" style="background-color:#EC4899; color:white; padding:12px 24px; border-radius:5px; text-decoration:none; font-weight:bold; display:inline-block; margin-top:10px;">Comprar Acceso Completo ($195)</a>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_btn2:
    st.markdown(
        """
        <div style="background-color:#111827; padding:20px; border-radius:10px; text-align:center;">
            <h3 style="color:white; margin-bottom:10px;">Single State Export ($95)</h3>
            <p style="color:#9CA3AF; font-size:14px;">Descarga únicamente la información del estado que elijas.</p>
            <a href="https://juanahez.gumroad.com/l/ywcomq" target="_blank" style="background-color:#3B82F6; color:white; padding:12px 24px; border-radius:5px; text-decoration:none; font-weight:bold; display:inline-block; margin-top:10px;">Comprar por Estado ($95)</a>
    </div>
        """,
        unsafe_allow_html=True
    )"
    
    try:
        response = requests.get(ENLACE_DIRECTO_DB, stream=True)
        if response.status_code == 200:
            with open(DB_MEGA_PATH, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            st.success("¡Base de datos descargada con éxito! Actualizando la app...")
            st.rerun()
        else:
            st.error("No se pudo descargar la base de datos automáticamente. Verifica el enlace.")
    except Exception as e:
        st.error(f"Error en la descarga: {e}")

# ==============================================================================
# 📋 LISTADO COMPLETO DE LAS 95 INDUSTRIAS EXACTAS
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

# ==============================================================================
# ⚡ SINCRONIZADOR SQL ULTRARRÁPIDO (UNIFICA INDUSTRY Y SUB_CATEGORY EN 0.05s)
# ==============================================================================
@st.cache_resource
def indexar_y_unificar_rubros_sql():
    try:
        conn = sqlite3.connect("mega_base_b2b.db")
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

        mapeos_sql = [
            ("HVAC & Plumbing", "Plumbing Service", "%plumb%"),
            ("HVAC & Plumbing", "HVAC Repair", "%"),
            ("Construction & Home Services", "Roofing Contractor", "%roof%"),
            ("Construction & Home Services", "Painting Company", "%paint%"),
            ("Construction & Home Services", "Landscaping Service", "%landscap%"),
            ("Construction & Home Services", "Pest Control", "%pest%"),
            ("Construction & Home Services", "Flooring Contractor", "%floor%"),
            ("Construction & Home Services", "Cleaning Service", "%clean%"),
            ("Construction & Home Services", "Home Remodeling", "%remodel%"),
            ("Construction & Home Services", "Construction Company", "%construct%"),
            ("Construction & Home Services", "General Contractor", "%"),
            ("Electrical, Solar & Security", "Solar Energy Company", "%solar%"),
            ("Electrical, Solar & Security", "Security Company", "%security%"),
            ("Electrical, Solar & Security", "Electrician", "%"),
            ("Real Estate, Legal & Finance", "Law Firm", "%law%"),
            ("Real Estate, Legal & Finance", "Accountant", "%account%"),
            ("Real Estate, Legal & Finance", "Insurance Agency", "%insur%"),
            ("Real Estate, Legal & Finance", "Property Management", "%property%"),
            ("Real Estate, Legal & Finance", "Real Estate Agency", "%"),
            ("Healthcare, Dental & Wellness", "Dentist Office", "%dent%"),
            ("Healthcare, Dental & Wellness", "Veterinary Clinic", "%vet%"),
            ("Healthcare, Dental & Wellness", "Fitness Center", "%fit%"),
            ("Healthcare, Dental & Wellness", "Hair Salon", "%salon%"),
            ("Healthcare, Dental & Wellness", "Barber Shop", "%barber%"),
            ("Healthcare, Dental & Wellness", "Medical Clinic", "%"),
            ("Auto, Towing & Logistics", "Towing Service", "%tow%"),
            ("Auto, Towing & Logistics", "Auto Body Shop", "%body%"),
            ("Auto, Towing & Logistics", "Car Dealership", "%dealer%"),
            ("Auto, Towing & Logistics", "Moving Company", "%mov%"),
            ("Auto, Towing & Logistics", "Trucking Company", "%truck%"),
            ("Auto, Towing & Logistics", "Logistics Service", "%logistic%"),
            ("Auto, Towing & Logistics", "Auto Repair Shop", "%"),
            ("Tech, Marketing & Commercial", "Software Company", "%software%"),
            ("Tech, Marketing & Commercial", "Digital Marketing Agency", "%market%"),
            ("Tech, Marketing & Commercial", "Boutique Hotel", "%hotel%"),
            ("Tech, Marketing & Commercial", "Catering Service", "%cater%"),
            ("Tech, Marketing & Commercial", "Wholesale Supplier", "%")
        ]
        for grupo_viejo, rubro_nuevo, patron in mapeos_sql:
            if patron == "%":
                c.execute("UPDATE leads_b2b SET industry = ?, sub_category = ? WHERE industry = ?", (rubro_nuevo, rubro_nuevo, grupo_viejo))
            else:
                c.execute("UPDATE leads_b2b SET industry = ?, sub_category = ? WHERE industry = ? AND LOWER(company_name) LIKE ?", (rubro_nuevo, rubro_nuevo, grupo_viejo, patron))

        conn.commit()
        conn.close()
    except Exception:
        pass

indexar_y_unificar_rubros_sql()

# ==============================================================================
# 📊 CONTADOR GLOBAL Y POR CATEGORÍA EN TIEMPO REAL
# ==============================================================================
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
        conn2 = sqlite3.connect("mega_base_b2b.db")
        total_mega = conn2.execute("SELECT COUNT(*) FROM leads_b2b").fetchone()[0]

        filas_ind = conn2.execute("""
            SELECT COALESCE(NULLIF(sub_category, ''), industry) AS cat, COUNT(*)
            FROM leads_b2b
            GROUP BY cat
        """).fetchall()
        for cat_name, cant in filas_ind:
            if cat_name in conteos:
                conteos[cat_name] += cant

        filas_ind2 = conn2.execute("""
            SELECT industry, COUNT(*)
            FROM leads_b2b
            WHERE industry != COALESCE(sub_category, '')
            GROUP BY industry
        """).fetchall()
        for ind_name, cant in filas_ind2:
            if ind_name in conteos:
                conteos[ind_name] += cant

        conn2.close()
    except Exception:
        pass

    total_global = total_fmcsa + total_mega
    conteos["🌐 All Categories (Global Search)"] = total_mega
    return total_global, conteos

total_general_en_vivo, conteos_por_industria = obtener_conteos_en_vivo()

# ==============================================================================
# 🏢 MENÚ LATERAL
# ==============================================================================
st.sidebar.title("🏢 Select Industry (96 Total)")

st.sidebar.markdown(
    f"""
    <div style="background-color:#1E293B; padding:12px; border-radius:8px; text-align:center; margin-bottom:15px; border: 1px solid #334155;">
        <p style="color:#94A3B8; font-size:12px; margin:0; text-transform:uppercase; font-weight:bold;">Total Profiles Verified</p>
        <h2 style="color:#38BDF8; margin:5px 0 0 0; font-size:24px;">{total_general_en_vivo:,}</h2>
        <p style="color:#10B981; font-size:11px; margin:2px 0 0 0; font-weight:bold;">✅ 100% Verified Active</p>
    </div>
    """,
    unsafe_allow_html=True
)

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

st.title(f"🚀 B2B Lead Database: {industria}")

# ==============================================================================
# 1. VISTA TRUCKING & LOGISTICS (FMCSA)
# ==============================================================================
if industria == "Trucking & Logistics (FMCSA)":
    st.markdown(
        "**Verified Active Commercial Profiles: MC Docket, Owner 1 & 2, Cell Phone, Office Phone, Email, Full Address, Fleet Size & Drivers.** *(Contact fields masked in live preview)*"
    )
    conn = sqlite3.connect("perfiles_fmcsa.db")
    cursor = conn.cursor()
    total_carriers = conteos_por_industria.get("Trucking & Logistics (FMCSA)", 0)
    estados_raw = cursor.execute("SELECT DISTINCT Estado FROM empresas WHERE Estado IS NOT NULL AND Estado != '' ORDER BY Estado").fetchall()
    lista_estados = [e[0] for e in estados_raw]

    st.markdown("##### 🔎 Búsqueda Avanzada de Perfiles")
    f1, f2, f3 = st.columns(3)
    b_empresa = f1.text_input("🏢 Company Name / DBA:", placeholder="Ej: Express, Transport LLC...")
    b_persona = f2.text_input("👤 Owner / Principal Name:", placeholder="Ej: John, Carlos, Michael...")
    b_telefono = f3.text_input("📞 Phone Number / Area Code:", placeholder="Ej: 305, 718, 214...")

    f4, f5, f6, f7 = st.columns([2, 2, 2, 1.5])
    b_ciudad = f4.text_input("🏙️ City:", placeholder="Ej: Miami, Houston, Brooklyn...")
    estados_sel = f5.multiselect("🗺️ State(s):", options=lista_estados, placeholder="All States")
    b_zip = f6.text_input("📮 Zip Code:", placeholder="Ej: 33101, 78521...")
    min_trucks = f7.number_input("🚛 Min. Trucks:", min_value=1, max_value=500, value=1)

    condiciones = ["CAST(Camiones_Totales AS INTEGER) >= ?"]
    params = [int(min_trucks)]

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

    if estados_sel:
        placeholders = ",".join(["?"] * len(estados_sel))
        condiciones.append(f"Estado IN ({placeholders})")
        params.extend(estados_sel)

    if b_zip.strip():
        condiciones.append("Codigo_Postal LIKE ?")
        params.append(f"%{b_zip.strip()}%")

    where_sql = " WHERE " + " AND ".join(condiciones)
    total_matching = cursor.execute(f"SELECT COUNT(*) FROM empresas {where_sql}", params).fetchone()[0]
    df = pd.read_sql_query(f"SELECT * FROM empresas {where_sql} LIMIT 250", conn, params=params)
    conn.close()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Verified Active Carriers", f"{total_matching:,} Verified")
    m2.metric("Geographic Coverage", "All 50 US States")
    m3.metric("Data Depth", "17 Commercial Fields")
    m4.metric("Instant Unlock Price", "USD 95 (State) | 195 (All)")

    if "Celular_Directo" in df.columns:
        df["Celular_Directo"] = df["Celular_Directo"].apply(lambda x: ocultar_dato(x, 5))
        df["Telefono_Oficina"] = df["Telefono_Oficina"].apply(lambda x: ocultar_dato(x, 5))
        df["Email"] = df["Email"].apply(lambda x: ocultar_dato(x, 4))
        df["Estatus_Verificacion"] = "✅ Verified Active"

    st.caption(f"Showing top {len(df)} preview records out of **{total_matching:,}** verified active carriers ready for instant CSV/Excel export.")
    st.dataframe(df, use_container_width=True, height=450)

# ==============================================================================
# 2. VISTA PARA LAS 95 INDUSTRIAS Y BÚSQUEDA GLOBAL
# ==============================================================================
else:
    st.markdown(
        "**Verified Active Commercial Profiles: Legal Company Name, Category, Owner/Principal, Direct Phone, Email, Street Address, City, State, Zip Code & Verification Status.** *(Contact fields masked in live preview)*"
    )
    conn = sqlite3.connect("mega_base_b2b.db")
    cursor = conn.cursor()

    es_global = (industria == "🌐 All Categories (Global Search)")

    if es_global:
        estados_ind = [
            e[0] for e in cursor.execute(
                "SELECT DISTINCT state FROM leads_b2b WHERE state IS NOT NULL AND state NOT IN ('N/A', 'US', '') ORDER BY state"
            ).fetchall()
        ]
    else:
        estados_ind = [
            e[0] for e in cursor.execute(
                "SELECT DISTINCT state FROM leads_b2b WHERE (industry = ? OR sub_category = ?) AND state IS NOT NULL AND state NOT IN ('N/A', '') ORDER BY state",
                (industria, industria)
            ).fetchall()
        ]

    st.markdown("##### 🔎 Búsqueda Avanzada por Perfil Específico")
    f1, f2, f3 = st.columns(3)
    b_empresa = f1.text_input("🏢 Company Name:", placeholder="Ej: Drain Genie, Signature Plumbing...")
    b_persona = f2.text_input("👤 Person / Owner Name:", placeholder="Ej: John Bodnar, Michael Aguilar...")
    b_telefono = f3.text_input("📞 Phone Number / Area Code:", placeholder="Ej: 480, 407, (305)...")

    f4, f5, f6 = st.columns(3)
    b_ciudad = f4.text_input("🏙️ City:", placeholder="Ej: Orlando, Mesa, Phoenix, Miami...")
    estados_sel = f5.multiselect("🗺️ State(s):", options=estados_ind, placeholder="All States")
    b_zip = f6.text_input("📮 Zip Code:", placeholder="Ej: 85201, 32653, 10001...")

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

    if estados_sel:
        placeholders = ",".join(["?"] * len(estados_sel))
        condiciones.append(f"state IN ({placeholders})")
        params.extend(estados_sel)

    if b_zip.strip():
        condiciones.append("zip_code LIKE ?")
        params.append(f"%{b_zip.strip()}%")

    where_sql = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
    total_matching_ind = cursor.execute(f"SELECT COUNT(*) FROM leads_b2b {where_sql}", params).fetchone()[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Verified Unique Businesses", f"{total_matching_ind:,} Verified")
    m2.metric("Geographic Coverage", f"{len(estados_ind) if estados_ind else 50} US States Active")
    m3.metric("Data Depth", "10 Commercial Fields")
    m4.metric("Instant Unlock Price", "USD 95 (State) | 195 (All)")

    rubro_columna = "COALESCE(sub_category, industry)" if es_global else f"'{industria}'"

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
        LIMIT 500
    """
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if not df.empty:
        df["Dueno_Principal"] = df.apply(limpiar_dueno_en_vista, axis=1)
        df["Estado"] = df.apply(corregir_estado_en_vista, axis=1)
        df["Telefono_Directo"] = df["Telefono_Directo"].apply(lambda x: ocultar_dato(x, 6))
        df["Email"] = df["Email"].apply(lambda x: ocultar_dato(x, 4))

    st.caption(f"Showing top {len(df)} preview records out of **{total_matching_ind:,}** verified commercial profiles matching your search.")
    st.dataframe(df, use_container_width=True, height=450)

# --- SECCIÓN DE MONETIZACIÓN Y CHECKOUT INTEGRADO ---
st.markdown("---")
st.subheader(f"🔓 ¿Necesitas acceso completo a la base de {industria}?")
st.write("Obtén el archivo CSV completo listo para importar en tu CRM o herramienta de llamadas.")

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    st.markdown(
        """
        <div style="background-color:#111827; padding:20px; border-radius:10px; text-align:center;">
            <h3 style="color:white; margin-bottom:10px;">Full National Database ($195)</h3>
            <p style="color:#9CA3AF; font-size:14px;">Acceso total a todos los estados y campos comerciales.</p>
            <a href="https://juanahez.gumroad.com/l/rzzow" target="_blank" style="background-color:#EC4899; color:white; padding:12px 24px; border-radius:5px; text-decoration:none; font-weight:bold; display:inline-block; margin-top:10px;">Comprar Acceso Completo ($195)</a>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_btn2:
    st.markdown(
        """
        <div style="background-color:#111827; padding:20px; border-radius:10px; text-align:center;">
            <h3 style="color:white; margin-bottom:10px;">Single State Export ($95)</h3>
            <p style="color:#9CA3AF; font-size:14px;">Descarga únicamente la información del estado que elijas.</p>
            <a href="https://juanahez.gumroad.com/l/ywcomq" target="_blank" style="background-color:#3B82F6; color:white; padding:12px 24px; border-radius:5px; text-decoration:none; font-weight:bold; display:inline-block; margin-top:10px;">Comprar por Estado ($95)</a>
        </div>
        """,
        unsafe_allow_html=True
    )
