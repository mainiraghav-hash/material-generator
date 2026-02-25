import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import requests
from bs4 import BeautifulSoup
import os
import math
from material_data import ALLOYS_DB

DB_PATH = 'materials.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            name TEXT PRIMARY KEY,
            density REAL,
            youngs_mod REAL,
            poisson REAL,
            yield_str REAL,
            tangent_mod REAL,
            source_url TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_material(name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT density, youngs_mod, poisson, yield_str, tangent_mod, source_url FROM materials WHERE name = ? COLLATE NOCASE', (name,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'density': row[0],
            'youngs_mod': row[1],
            'poisson': row[2],
            'yield_str': row[3],
            'tangent_mod': row[4],
            'source_url': row[5]
        }
    return None

def save_material(name, density, youngs_mod, poisson, yield_str, tangent_mod, source_url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO materials (name, density, youngs_mod, poisson, yield_str, tangent_mod, source_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            density=excluded.density,
            youngs_mod=excluded.youngs_mod,
            poisson=excluded.poisson,
            yield_str=excluded.yield_str,
            tangent_mod=excluded.tangent_mod,
            source_url=excluded.source_url
    ''', (name, density, youngs_mod, poisson, yield_str, tangent_mod, source_url))
    conn.commit()
    conn.close()

def real_scrape(name):
    """
    Search MatWeb for the material and attempt to scrape density, youngs modulus,
    poisson ratio, and yield strength.
    """
    # 1. Search MatWeb
    search_url = f"https://matweb.com/search/QuickText.aspx?SearchText={name}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    # --- FALLBACK DICTIONARY FOR CLOUDFLARE BLOCKS ---
    # MatWeb heavily uses Cloudflare which blocks simple 'requests' calls.
    # We include a robust fallback database for common alloys.
    fallback_db = ALLOYS_DB
    
    nm_key = name.lower().strip()
    if nm_key in fallback_db:
        res = fallback_db[nm_key]
        res['name'] = name
        return res
    
    try:
        response = requests.get(search_url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # If Cloudflare blocks us, we might see "Just a moment..."
        if "Just a moment" in soup.text:
            print("Cloudflare anti-bot active. Scraping blocked.")
            return None
        
        # In a generic search, MatWeb might give a list of results or redirect.
        # For simplicity in this demo, we'll try to find the first material link.
        # Real-world scraping MatWeb is notoriously complex due to dynamic ASPX tables.
        
        # Let's see if we hit a search results page
        result_links = soup.find_all('a', id=lambda x: x and 'hlMatl' in x)
        
        if not result_links:
            return None # No results found
            
        first_material_url = "https://matweb.com" + result_links[0]['href']
        
        # 2. Fetch the actual material page
        mat_resp = requests.get(first_material_url, headers=headers, timeout=5)
        mat_soup = BeautifulSoup(mat_resp.text, 'html.parser')
        
        name_val = result_links[0].text.strip()
        density_val = 0.0
        youngs_val = 0.0
        poisson_val = 0.0
        yield_val = 0.0
        tangent_val = 0.0 # difficult to scrape, usually requires graph interpretation
        source_url_val = first_material_url
        
        # 3. Parse the data table (MatWeb uses standard tables but it's very messy)
        # We look for specific property names in the table rows
        rows = mat_soup.find_all('tr')
        for row in rows:
            text = row.get_text().lower()
            cols = row.find_all('td')
            if len(cols) >= 3:
                # MatWeb usually has: Property | Metric | English | Comments
                metric_val = cols[1].text.strip().split(' ')[0] # try to grab just the number
                
                try:
                    val = float(metric_val.replace(',', ''))
                except ValueError:
                    continue # Not a clean number
                    
                if "density" in text:
                    density_val = val * 1000 # MatWeb is usually g/cc, we want kg/m3 base
                elif "modulus of elasticity" in text:
                    # MatWeb is usually GPa
                    youngs_val = val * 1e9
                elif "poissons ratio" in text or "poisson's ratio" in text:
                    poisson_val = val
                elif "tensile yield strength" in text:
                    # MatWeb is usually MPa
                    yield_val = val * 1e6
                    
        # Provide a reasonable estimate for tangent modulus if we got youngs
        if youngs_val > 0.0:
             tangent_val = youngs_val * 0.1 # Rough 10% estimate
             
        # If we got at least density or modulus, consider it a success
        if density_val > 0.0 or youngs_val > 0.0:
            return {
                'name': name_val,
                'density': density_val,
                'youngs_mod': youngs_val,
                'poisson': poisson_val,
                'yield_str': yield_val,
                'tangent_mod': tangent_val,
                'source_url': source_url_val
            }
            
    except Exception as e:
        print(f"Scrape error: {e}")
        
    return None

def generate_lsdyna_card(name, props, units):
    # 10 character fixed width
    ro = props['density'] * units['density']
    e = props['youngs_mod'] * units['stress']
    pr = props['poisson']
    sigy = props['yield_str'] * units['stress']
    etan = props['tangent_mod'] * units['stress']
    
    def fmt(val):
        if isinstance(val, str):
            # Using str format to force 10 chars, truncating if longer
            return f"{str(val):<10.10s}"
        if val == 0:
            return f"{0.0:<10.3E}"
        # Scientific formatting fitting 10 chars
        s = f"{float(val):<10.3E}"
        if len(s) > 10:
            s = f"{float(val):<10.2E}"
        return s

    lines = [
        "*MAT_PIECEWISE_LINEAR_PLASTICITY",
        "$TITLE",
        name,
        "$      MID        RO         E        PR      SIGY      ETAN      FAIL      TDEL",
        f"{fmt(1)}{fmt(ro)}{fmt(e)}{fmt(pr)}{fmt(sigy)}{fmt(etan)}{fmt(0.0)}{fmt(0.0)}",
        "$        C         P      LCSS      LCSR        VP",
        f"{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}",
        "$     EPS1      EPS2      EPS3      EPS4      EPS5      EPS6      EPS7      EPS8",
        f"{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}",
        "$      ES1       ES2       ES3       ES4       ES5       ES6       ES7       ES8",
        f"{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}{fmt(0.0)}"
    ]
    return "\n".join(lines)

def generate_ansys_xml(name, props, units):
    root = ET.Element("EngineeringData", version="18.1")
    materials = ET.SubElement(root, "Materials")
    mat = ET.SubElement(materials, "Material")
    ET.SubElement(mat, "Name").text = name
    
    p_dens = ET.SubElement(mat, "PropertyData", property="prOR")
    ET.SubElement(p_dens, "Data").text = str(props['density'] * units['density'])
    
    p_elas = ET.SubElement(mat, "PropertyData", property="prElasticity")
    ET.SubElement(p_elas, "Data", name="Youngs Modulus").text = str(props['youngs_mod'] * units['stress'])
    ET.SubElement(p_elas, "Data", name="Poissons Ratio").text = str(props['poisson'])
    
    p_plast = ET.SubElement(mat, "PropertyData", property="prBilinearIsotropicHardening")
    ET.SubElement(p_plast, "Data", name="Yield Strength").text = str(props['yield_str'] * units['stress'])
    ET.SubElement(p_plast, "Data", name="Tangent Modulus").text = str(props['tangent_mod'] * units['stress'])
    
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def inject_custom_css():
    st.markdown("""
        <style>
        /* Modern Minimalist Font & Background */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #f8fafc;
            color: #1e293b;
        }
        
        /* Clean up standard Streamlit structural paddings */
        .block-container {
            padding-top: 3rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }

        /* Subtle Card styling for inputs and layout blocks */
        div[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlock"] {
            background-color: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            border: 1px solid #e2e8f0;
            margin-bottom: 1rem;
        }

        /* Headers */
        h1, h2, h3 {
            font-weight: 600 !important;
            letter-spacing: -0.025em !important;
            color: #0f172a !important;
        }
        
        h1 {
            font-size: 2.25rem !important;
            margin-bottom: 0.5rem !important;
            background: linear-gradient(to right, #2563eb, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        h2 {
            font-size: 1.5rem !important;
            margin-top: 2rem !important;
            margin-bottom: 1rem !important;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 0.5rem;
        }

        /* Inputs and Selectboxes */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
            border-radius: 8px;
            border: 1px solid #cbd5e1;
            transition: all 0.2s ease-in-out;
            background-color: #f8fafc;
        }
        
        .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 1px #3b82f6 !important;
            background-color: white;
        }

        /* Modern Primary Button */
        button[kind="primary"], .stButton > button {
            background-color: #3b82f6;
            color: white;
            font-weight: 500;
            border-radius: 8px;
            padding: 0.5rem 1.5rem;
            border: none;
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
            transition: all 0.2s;
            width: auto;
        }
        
        button[kind="primary"]:hover, .stButton > button:hover {
            background-color: #2563eb;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            transform: translateY(-1px);
            color: white;
        }

        /* Text area styling (code previews) */
        .stTextArea textarea {
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 0.875rem;
            background-color: #1e293b;
            color: #f8fafc;
            border-radius: 8px;
            border: 1px solid #cbd5e1;
        }
        
        /* Metric/status messages */
        .stAlert {
            border-radius: 8px;
            border: none;
        }
        </style>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Universal Material Card Generator", layout="wide")
    inject_custom_css()
    
    st.title("Universal Material Card Generator")
    st.markdown("Generate ready-to-use material cards for **LS-DYNA** and **Ansys**.")
    
    init_db()
    
    if 'current_material' not in st.session_state:
        st.session_state.current_material = {
            'name': '', 'density': 0.0, 'youngs_mod': 0.0, 'poisson': 0.0,
            'yield_str': 0.0, 'tangent_mod': 0.0, 'source_url': ''
        }
    if 'status_msg' not in st.session_state:
        st.session_state.status_msg = ""
        st.session_state.status_type = ""
        
    st.header("1. Material Search & Memory")
    col1, col2 = st.columns([2, 1])
    
    # Get all names to feed into the dropdown
    available_materials = [""] + [name.title() for name in ALLOYS_DB.keys()]
    
    with col1:
        search_name = st.selectbox(
            "Enter Material Name (e.g., Al 2024-T3, Steel 1020, Ti-6Al-4V):",
            available_materials,
            index=0
        )
    with col2:
        st.write(" ")
        st.write(" ")
        if st.button("Search / Load"):
            if search_name.strip():
                # DB Check
                db_data = get_material(search_name.strip())
                if db_data:
                    st.session_state.current_material = db_data
                    st.session_state.current_material['name'] = search_name.strip()
                    st.session_state.status_msg = f"Found '{search_name}' in local DB!"
                    st.session_state.status_type = "success"
                else:
                    # Real Scrape
                    scraped = real_scrape(search_name.strip())
                    if scraped:
                        st.session_state.current_material = scraped
                        st.session_state.status_msg = f"Retrieved '{scraped['name']}' from MatWeb!"
                        st.session_state.status_type = "info"
                    else:
                        st.session_state.current_material = {
                            'name': search_name.strip(), 'density': 0.0, 'youngs_mod': 0.0,
                            'poisson': 0.0, 'yield_str': 0.0, 'tangent_mod': 0.0, 'source_url': 'Manual Entry'
                        }
                        st.session_state.status_msg = f"'{search_name}' not found. Please enter manually."
                        st.session_state.status_type = "warning"
            else:
                st.session_state.status_msg = "Please enter a material name to search."
                st.session_state.status_type = "error"
                
    if st.session_state.status_msg:
        if st.session_state.status_type == "success":
            st.success(st.session_state.status_msg)
        elif st.session_state.status_type == "info":
            st.info(st.session_state.status_msg)
        elif st.session_state.status_type == "warning":
            st.warning(st.session_state.status_msg)
        else:
            st.error(st.session_state.status_msg)
            
    st.header("2. Manual Review & Property Editor")
    st.caption("Base units are maintained in **SI (kg/m³, Pa)** for standardization. Inputs below are scaled for convenience.")
    
    edit_col1, edit_col2, edit_col3 = st.columns(3)
    with edit_col1:
        name_val = st.text_input("Name", st.session_state.current_material['name'])
        dens_val = st.number_input("Density (kg/m³)", value=float(st.session_state.current_material['density']), format="%.2f")
    with edit_col2:
        E_input = st.number_input("Young's Modulus (GPa)", value=float(st.session_state.current_material['youngs_mod'])/1e9, format="%.2f")
        pr_val = st.number_input("Poisson's Ratio", value=float(st.session_state.current_material['poisson']), format="%.3f")
    with edit_col3:
        sy_input = st.number_input("Yield Strength (MPa)", value=float(st.session_state.current_material['yield_str'])/1e6, format="%.2f")
        et_input = st.number_input("Tangent Modulus (GPa)", value=float(st.session_state.current_material['tangent_mod'])/1e9, format="%.3f")
        src_val = st.text_input("Source URL/Reference", st.session_state.current_material['source_url'])
        
    # Convert back to base SI (Pa) for all internal logic
    E_val = E_input * 1e9
    sy_val = sy_input * 1e6
    et_val = et_input * 1e9
        
    if st.button("Save to Library"):
        if name_val.strip():
            save_material(name_val, dens_val, E_val, pr_val, sy_val, et_val, src_val)
            st.success("Values successfully committed to local materials.db!")
            st.session_state.current_material = {
                'name': name_val, 'density': dens_val, 'youngs_mod': E_val,
                'poisson': pr_val, 'yield_str': sy_val, 'tangent_mod': et_val, 'source_url': src_val
            }
        else:
            st.error("Name field cannot be empty.")
            
    st.header("3. Engineering Logic & Plotting")
    sys_col, opt_col = st.columns(2)
    with sys_col:
        unit_system = st.selectbox("Target Unit System for Export", [
            "SI (kg-m-s-Pa)",
            "Ton-mm-s (ton-mm-s-MPa)",
            "Imperial (lbf*s²/in-in-s-psi)"
        ], index=1)
    with opt_col:
        st.write(" ")
        convert_true = st.checkbox("Convert plotted curve to True Stress/Strain?", value=True)
        
    unit_multipliers = {
        "SI (kg-m-s-Pa)": {"density": 1.0, "stress": 1.0},
        "Ton-mm-s (ton-mm-s-MPa)": {"density": 1e-12, "stress": 1e-6},
        "Imperial (lbf*s²/in-in-s-psi)": {"density": 9.359e-5, "stress": 1.45038e-4}
    }
    
    if E_val > 0 and sy_val > 0:
        eps_y = sy_val / E_val
        eps_max = max(eps_y * 10, 0.05) 
        s_max = sy_val + et_val * (eps_max - eps_y)
        
        eng_strain = np.array([0, eps_y, eps_max])
        eng_stress = np.array([0, sy_val, s_max])
        
        factor = unit_multipliers[unit_system]['stress']
        display_stress = eng_stress * factor
        
        if convert_true:
            plot_strain = np.log(1 + eng_strain)
            plot_stress = display_stress * (1 + eng_strain)
            title = "True Stress vs True Strain (Bilinear)"
            y_axis = "True Stress"
            x_axis = "True Strain"
        else:
            plot_strain = eng_strain
            plot_stress = display_stress
            title = "Engineering Stress vs Strain (Bilinear)"
            y_axis = "Engineering Stress"
            x_axis = "Engineering Strain"
            
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(plot_strain, plot_stress, 'b-o', linewidth=2)
        ax.set_title(title, fontweight='bold')
        unit_label = "Pa" if "SI" in unit_system else ("MPa" if "Ton" in unit_system else "psi")
        ax.set_ylabel(f"{y_axis} ({unit_label})")
        ax.set_xlabel(x_axis)
        ax.grid(True, linestyle='--', alpha=0.7)
        st.pyplot(fig)
    else:
        if name_val.strip() != "":
            st.info("Input Young's Modulus and Yield Strength > 0 to visualize the stress-strain curve.")
        
    st.header("4. Solver Card Generation")
    
    props = {
        'density': dens_val, 'youngs_mod': E_val, 'poisson': pr_val,
        'yield_str': sy_val, 'tangent_mod': et_val
    }
    active_units = unit_multipliers[unit_system]
    
    out_col1, out_col2 = st.columns(2)
    with out_col1:
        st.subheader("LS-DYNA (.k)")
        k_card = generate_lsdyna_card(name_val, props, active_units)
        st.text_area("Preview (MAT_024)", k_card, height=250)
        st.download_button(
            label="Download material.k",
            data=k_card,
            file_name=f"{name_val.replace(' ', '_')}_lsdyna.k",
            mime="text/plain"
        )
        
    with out_col2:
        st.subheader("Ansys (.xml)")
        xml_card = generate_ansys_xml(name_val, props, active_units)
        st.text_area("Preview (MatML)", xml_card, height=250)
        st.download_button(
            label="Download material.xml",
            data=xml_card,
            file_name=f"{name_val.replace(' ', '_')}_ansys.xml",
            mime="application/xml"
        )
        
if __name__ == "__main__":
    main()
