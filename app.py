import streamlit as st
import sqlite3
import os
import urllib.parse
import base64
from datetime import datetime
from PIL import Image

# =====================================================================
# 1. SEITEN-EINSTELLUNGEN & MODERNES DESIGN (CSS)
# =====================================================================
st.set_page_config(page_title="Projekt-Zentrale", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Hintergrund & Grunddesign */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Moderne Projekt-Kacheln - Wackeln durch scale() behoben, sanftere Transition */
    .projekt-kachel {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 10px rgba(15, 23, 42, 0.04);
        border: 1px solid #e2e8f0;
        margin-bottom: 25px;
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .projekt-kachel:hover {
        transform: translateY(-3px); /* Reduziert von -6px und scale entfernt, verhindert Wackeln */
        box-shadow: 0 10px 20px rgba(15, 23, 42, 0.08);
        border-color: #3b82f6;
    }
    
    /* Gebäude-Erfassungskacheln */
    .erfassungs-verlauf-kachel {
        background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%);
        border-left: 5px solid #3b82f6;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    
    /* Kachelauswahl */
    .kachel-auswahl {
        background-color: #ffffff;
        border: 2px solid #e2e8f0;
        border-radius: 14px;
        padding: 30px;
        text-align: center;
        transition: all 0.2s ease;
    }
    .kachel-auswahl:hover {
        border-color: #3b82f6;
        box-shadow: 0 8px 20px rgba(59, 130, 246, 0.1);
        background-color: #fcfdfe;
    }
    
    /* Modernisierte Tabs */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 12px; 
        background-color: #f1f5f9;
        padding: 8px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        color: #64748b;
        transition: all 0.2s;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
        box-shadow: 0 4px 10px rgba(59, 130, 246, 0.25);
    }
    
    /* Formulare & Eingabefelder eleganter machen */
    .stTextInput input, .stSelectbox, .stNumberInput input, .stTextArea textarea {
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

# =====================================================================
# 2. DATENBANK-SETUP & TABELLEN
# =====================================================================
DB_FILE = "datenbank.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS benutzer (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, passwort TEXT, rolle TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS projekte (id INTEGER PRIMARY KEY AUTOINCREMENT, obj_nr TEXT UNIQUE, name TEXT, adresse TEXT, bild_url TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS eigentuemer (id INTEGER PRIMARY KEY AUTOINCREMENT, obj_nr TEXT, name TEXT, vorname TEXT, telefon TEXT, email TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS notizen (id INTEGER PRIMARY KEY AUTOINCREMENT, obj_nr TEXT, inhalt TEXT, datum TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stammdaten (obj_nr TEXT PRIMARY KEY, bauherr TEXT, strasse TEXT, plz_ort TEXT, telefon TEXT, email TEXT, baujahr TEXT, wohneinheiten INTEGER, flaeche TEXT, keller_vorhanden TEXT, denkmal TEXT, bemerkungen TEXT)''')
    
    # NEUE Tabelle für die detaillierte Gebäudeerfassung (v2)
    c.execute('''CREATE TABLE IF NOT EXISTS gebaeude_erfassung_v2 (
        obj_nr TEXT, erfassungs_datum TEXT,
        erfasser TEXT, datum_vorort TEXT, gebaeudetyp TEXT, vollgeschosse INTEGER, keller TEXT,
        dachform TEXT, dach_neueindeckung TEXT, spitzboden TEXT, dachueberstand TEXT, dachgauben TEXT, dachfenster TEXT, sparren TEXT, dach_infos TEXT, dach_daemmung TEXT,
        wanddicke TEXT, sockel TEXT, stockwerke TEXT, raumhoehe TEXT,
        fenstertyp TEXT, haustuer TEXT, fenster_sonst TEXT,
        heiz_typ TEXT, heiz_baujahr TEXT, heiz_ort TEXT, heiz_rohre TEXT, heiz_medium TEXT, ww_extra TEXT, ww_baujahr TEXT, ww_medium TEXT, ww_speicher TEXT, ww_pumpe TEXT, heiz_flaechen TEXT, heiz_frei TEXT,
        PRIMARY KEY (obj_nr, erfassungs_datum)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS sanierungen (id INTEGER PRIMARY KEY AUTOINCREMENT, obj_nr TEXT, gewerk TEXT, massnahme TEXT, prioritaet INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS dokumente (id INTEGER PRIMARY KEY AUTOINCREMENT, obj_nr TEXT, dateiname TEXT, hochgeladen_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute("SELECT COUNT(*) FROM benutzer")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO benutzer (username, passwort, rolle) VALUES ('admin', 'admin123', 'Admin')")
        c.execute("INSERT INTO benutzer (username, passwort, rolle) VALUES ('kunde', 'kunde123', 'Kunde')")
        conn.commit()
    conn.close()

init_db()

# Session States initialisieren
if "eingeloggt" not in st.session_state: st.session_state["eingeloggt"] = False
if "user_rolle" not in st.session_state: st.session_state["user_rolle"] = None
if "username" not in st.session_state: st.session_state["username"] = ""
if "aktives_projekt" not in st.session_state: st.session_state["aktives_projekt"] = None
if "ausgewaehlte_erfassung_datum" not in st.session_state: st.session_state["ausgewaehlte_erfassung_datum"] = None
if "temp_erfassungs_art" not in st.session_state: st.session_state["temp_erfassungs_art"] = None

# =====================================================================
# 3. BRANDING LOGIN-MASKE
# =====================================================================
if not st.session_state["eingeloggt"]:
    st.write("")
    st.write("")
    
    img_bs_base64 = get_base64_image("BS.jpg")
    img_h2_base64 = get_base64_image("logo-transparent-png.png")
    
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: center; gap: 20px; margin-bottom: 40px; width: 100%;">
        <div style="flex: 0 1 350px; text-align: right;">
            {f'<img src="data:image/jpeg;base64,{img_bs_base64}" style="width: 100%; max-width: 350px; height: auto; display: inline-block; vertical-align: middle;">' if img_bs_base64 else "<h3 style='margin:0;'>Energieberatung Braunschweig</h3>"}
        </div>
        <div style="font-size: 26px; font-weight: bold; color: #000000; user-select: none; padding: 0 10px; display: flex; align-items: center;">✖</div>
        <div style="flex: 0 1 420px; text-align: left;">
            {f'<img src="data:image/png;base64,{img_h2_base64}" style="width: 100%; max-width: 420px; height: auto; display: inline-block; vertical-align: middle;">' if img_h2_base64 else "<h3 style='margin:0;'>Hoch2 Beratung</h3>"}
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.2, 1.2, 1.2])
    with col2:
        with st.form("login_form"):
            st.markdown("<p style='text-align: center; font-weight: 500; color: #64748b;'>PROJEKT-ZENTRALE ANMELDUNG</p>", unsafe_allow_html=True)
            user_input = st.text_input("Benutzername")
            password_input = st.text_input("Passwort", type="password")
            if st.form_submit_button("Sicher Einloggen →", use_container_width=True):
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT rolle FROM benutzer WHERE username=? AND passwort=?", (user_input, password_input))
                result = c.fetchone()
                conn.close()
                if result:
                    st.session_state["eingeloggt"] = True
                    st.session_state["user_rolle"] = result[0]
                    st.session_state["username"] = user_input
                    st.rerun()
                else:
                    st.error("Zugangsdaten ungültig!")

# =====================================================================
# 4. HAUPTPROGRAMM (Eingeloggt)
# =====================================================================
else:
    with st.sidebar:
        st.markdown(f"<div style='background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 20px; border-radius: 12px; color: white; margin-bottom: 20px;'>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin:0; font-size:12px; color:#94a3b8;'>AKTUELLER BEARBEITER</p>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='margin:0; color:#3b82f6;'>✨ {st.session_state['username']}</h3>", unsafe_allow_html=True)
        st.markdown(f"<span style='background:#334155; padding:2px 8px; border-radius:4px; font-size:11px;'>{st.session_state['user_rolle']}</span>", unsafe_allow_html=True)
        st.markdown(f"</div>", unsafe_allow_html=True)
        
        if st.button("🏠 Zum Dashboard", use_container_width=True):
            st.session_state["aktives_projekt"] = None
            st.session_state["ausgewaehlte_erfassung_datum"] = None
            st.session_state["temp_erfassungs_art"] = None
            st.rerun()
        st.divider()
        if st.button("🚪 Abmelden", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # --- DASHBOARD ---
    if st.session_state["aktives_projekt"] is None:
        st.title("💼 Dashboard – Deine Projektübersicht")
        
        top_col1, top_col2 = st.columns([6, 1])
        with top_col2:
            neues_projekt = st.button("➕ Neues Projekt", use_container_width=True)
        
        if neues_projekt or st.session_state.get("zeige_formular", False):
            st.session_state["zeige_formular"] = True
            with st.expander("📝 Neues Projekt anlegen", expanded=True):
                with st.form("projekt_erstellen"):
                    obj_nr = st.text_input("Objektnummer (z.B. P2026-01)")
                    proj_name = st.text_input("Projektname")
                    adresse = st.text_input("Adresse (Straße, PLZ, Ort)")
                    bild = st.text_input("Bild-URL (z.B. Google StreetView / Optional)")
                    if st.form_submit_button("Projekt anlegen"):
                        if obj_nr and proj_name:
                            try:
                                conn = sqlite3.connect(DB_FILE)
                                c = conn.cursor()
                                c.execute("INSERT INTO projekte (obj_nr, name, adresse, bild_url, status) VALUES (?, ?, ?, ?, ?)",
                                          (obj_nr, proj_name, adresse, bild, "Aktiv"))
                                conn.commit()
                                conn.close()
                                st.success(f"Projekt '{proj_name}' erfolgreich angelegt!")
                                st.session_state["zeige_formular"] = False
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Diese Objektnummer existiert bereits!")
                        else:
                            st.error("Bitte Felder ausfüllen!")
        st.divider()

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT obj_nr, name, adresse, bild_url, status FROM projekte ORDER BY id DESC")
        alle_projekte = c.fetchall()
        conn.close()

        if not alle_projekte:
            st.info("Noch keine Projekte vorhanden.")
        else:
            cols = st.columns(3)
            for i, proj in enumerate(alle_projekte):
                with cols[i % 3]:
                    st.markdown('<div class="projekt-kachel">', unsafe_allow_html=True)
                    bild_pfad = proj[3] if proj[3] else "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=500"
                    st.image(bild_pfad, use_container_width=True)
                    st.markdown(f"### {proj[1]}")
                    st.markdown(f"**Nr:** `{proj[0]}` | **Status:** `{proj[4]}`")
                    st.markdown(f"📍 {proj[2]}")
                    
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        if st.button(f"🔎 Öffnen", key=f"open_{proj[0]}", use_container_width=True):
                            st.session_state["aktives_projekt"] = proj[0]
                            st.rerun()
                    with b_col2:
                        if st.session_state["user_rolle"] == "Admin":
                            if st.button(f"🗑️ Löschen", key=f"del_{proj[0]}", use_container_width=True):
                                conn = sqlite3.connect(DB_FILE)
                                c = conn.cursor()
                                c.execute("DELETE FROM projekte WHERE obj_nr=?", (proj[0],))
                                c.execute("DELETE FROM eigentuemer WHERE obj_nr=?", (proj[0],))
                                c.execute("DELETE FROM notizen WHERE obj_nr=?", (proj[0],))
                                c.execute("DELETE FROM stammdaten WHERE obj_nr=?", (proj[0],))
                                c.execute("DELETE FROM gebaeude_erfassung_v2 WHERE obj_nr=?", (proj[0],))
                                c.execute("DELETE FROM sanierungen WHERE obj_nr=?", (proj[0],))
                                conn.commit()
                                conn.close()
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # --- DETAILSEITE ---
    else:
        obj_nr_aktiv = st.session_state["aktives_projekt"]
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT obj_nr, name, adresse, bild_url, status FROM projekte WHERE obj_nr=?", (obj_nr_aktiv,))
        p_daten = c.fetchone()
        conn.close()
        
        if p_daten:
            tabs = st.tabs(["📋 Übersicht", "📝 Stammdaten", "🏗️ Gebäudeerfassung", "📊 Objektdaten", "📂 Dokumente"])
            
            # REITER 1: ÜBERSICHT
            with tabs[0]:
                st.title(f"Projekt: {p_daten[1]}")
                col_links, col_rechts = st.columns([2, 1])
                with col_links:
                    bild_pfad = p_daten[3] if p_daten[3] else "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=500"
                    st.image(bild_pfad, width=400)
                    adresse_verpackt = urllib.parse.quote(p_daten[2])
                    maps_url = f"https://www.google.com/maps/search/?api=1&query={adresse_verpackt}"
                    st.markdown(f"🗺️ **Adresse:** [{p_daten[2]}]({maps_url})")
                    st.write(f"🆔 **Objektnummer:** {p_daten[0]}")
                    
                    st.divider()
                    st.subheader("👥 Eigentümer")
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT name, vorname, telefon, email FROM eigentuemer WHERE obj_nr=?", (obj_nr_aktiv,))
                    owner = c.fetchone()
                    conn.close()
                    if owner:
                        st.info(f"**Name:** {owner[1]} {owner[0]} | 📞 {owner[2]} | ✉️ {owner[3]}")
                    else:
                        with st.expander("➕ Eigentümer hinzufügen"):
                            with st.form("add_owner"):
                                o_vname, o_name = st.text_input("Vorname"), st.text_input("Nachname")
                                o_tel, o_mail = st.text_input("Telefon"), st.text_input("E-Mail")
                                if st.form_submit_button("Speichern"):
                                    conn = sqlite3.connect(DB_FILE)
                                    c = conn.cursor()
                                    c.execute("INSERT INTO eigentuemer (obj_nr, name, vorname, telefon, email) VALUES (?,?,?,?,?)", (obj_nr_aktiv, o_name, o_vname, o_tel, o_mail))
                                    conn.commit()
                                    conn.close()
                                    st.rerun()
                                    
                    st.divider()
                    st.subheader("📌 Projektnotizen")
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    # FIX: "=" Zeichen bei obj_nr hinzugefügt
                    c.execute("SELECT inhalt, datum FROM notizen WHERE obj_nr=? ORDER BY datum DESC", (obj_nr_aktiv,))
                    alle_notizen = c.fetchall()
                    conn.close()
                    
                    for n in alle_notizen:
                        st.warning(f"🕒 {n[1]}\n\n{n[0]}")
                        
                    with st.expander("➕ Neue Notiz hinzufügen"):
                        neue_notiz_text = st.text_area("Inhalt der Notiz")
                        if st.button("Notiz speichern", key="save_note_dashboard"):
                            if neue_notiz_text:
                                conn = sqlite3.connect(DB_FILE)
                                c = conn.cursor()
                                c.execute("INSERT INTO notizen (obj_nr, inhalt) VALUES (?, ?)", (obj_nr_aktiv, neue_notiz_text))
                                conn.commit()
                                conn.close()
                                st.rerun()

            # REITER 2: STAMMDATEN
            with tabs[1]:
                st.subheader("📝 Stammdatenerfassung (Kundenformular)")
                # FIX: Info-Meldung für zukünftige Kunden-Link-Funktion
                st.info("🔗 **Demnächst:** Hier können Sie bald einen Link generieren, den Ihre Kunden bequem online ausfüllen können. Aktuell können die Daten hier manuell von Ihnen hinterlegt werden.")
                
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT * FROM stammdaten WHERE obj_nr=?", (obj_nr_aktiv,))
                sd = c.fetchone()
                conn.close()
                
                with st.form("stammdaten_form"):
                    s_bauherr = st.text_input("Bauherr / Auftraggeber", value=sd[1] if sd else "")
                    s_str = st.text_input("Straße, Hausnummer", value=sd[2] if sd else p_daten[2])
                    s_ort = st.text_input("PLZ, Ort", value=sd[3] if sd else "")
                    s_tel = st.text_input("Telefonnummer", value=sd[4] if sd else "")
                    s_mail = st.text_input("E-Mail-Adresse", value=sd[5] if sd else "")
                    
                    col_sd1, col_sd2 = st.columns(2)
                    with col_sd1:
                        s_jahr = st.text_input("Baujahr Gebäude", value=sd[6] if sd else "")
                        s_we = st.number_input("Anzahl Wohneinheiten", min_value=1, value=sd[7] if sd else 1)
                    with col_sd2:
                        s_flaeche = st.text_input("Wohnfläche ca. (m²)", value=sd[8] if sd else "")
                        s_keller = st.selectbox("Keller vorhanden?", ["Ja, beheizt", "Ja, unbeheizt", "Nein, Teilunterkellert", "Nein"], index=["Ja, beheizt", "Ja, unbeheizt", "Nein, Teilunterkellert", "Nein"].index(sd[9]) if sd else 1)
                    
                    s_denkmal = st.radio("Denkmalschutz / Ensembleschutz?", ["Nein", "Ja"], index=1 if sd and sd[10] == "Ja" else 0)
                    s_bemerk = st.text_area("Besondere Anmerkungen / Wünsche des Kunden", value=sd[11] if sd else "")
                    
                    if st.form_submit_button("Stammdaten speichern"):
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute('''INSERT OR REPLACE INTO stammdaten VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                                  (obj_nr_aktiv, s_bauherr, s_str, s_ort, s_tel, s_mail, s_jahr, s_we, s_flaeche, s_keller, s_denkmal, s_bemerk))
                        conn.commit()
                        conn.close()
                        st.success("Stammdaten gespeichert!")
                        st.rerun()

            # REITER 3: GEBÄUDEERFASSUNG (NEU STRUKTURIERT)
            with tabs[2]:
                st.subheader("📐 Technische Gebäudeaufnahme")
                
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT erfassungs_datum FROM gebaeude_erfassung_v2 WHERE obj_nr=?", (obj_nr_aktiv,))
                existierende_aufnahmen = c.fetchall()
                c.execute("SELECT * FROM stammdaten WHERE obj_nr=?", (obj_nr_aktiv,))
                sd_daten = c.fetchone()
                conn.close()
                
                if st.session_state["ausgewaehlte_erfassung_datum"] is None:
                    st.markdown("#### ➕ Eine neue Gebäudeaufnahme starten")
                    col_k1, col_k2 = st.columns(2)
                    with col_k1:
                        st.markdown('<div class="kachel-auswahl"><h3>📋 Standarderfassung</h3><p>Umfassende energetische Bestandsaufnahme</p>', unsafe_allow_html=True)
                        if st.button("Neue Standardaufnahme", use_container_width=True):
                            heute_str = datetime.now().strftime("%d.%m.%Y - %H:%M")
                            st.session_state["ausgewaehlte_erfassung_datum"] = heute_str
                            st.session_state["temp_erfassungs_art"] = "Standard"
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with col_k2:
                        st.markdown('<div class="kachel-auswahl"><h3>🔥 Heizlast-Berechnung</h3><p>Raumweise Erfassung für Wärmepumpenauslegung<br><small>(Demnächst verfügbar)</small></p>', unsafe_allow_html=True)
                        if st.button("Neue Heizlastaufnahme", use_container_width=True, disabled=False):
                            heute_str = datetime.now().strftime("%d.%m.%Y - %H:%M")
                            st.session_state["ausgewaehlte_erfassung_datum"] = heute_str
                            st.session_state["temp_erfassungs_art"] = "Heizlast"
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.divider()
                    st.markdown("#### 📂 Bisherige Gebäudeaufnahmen dieses Objekts:")
                    if not existierende_aufnahmen:
                        st.info("Für dieses Projekt wurde bisher noch keine Aufnahme durchgeführt.")
                    else:
                        for datum_erf_tuple in existierende_aufnahmen:
                            datum_erf = datum_erf_tuple[0]
                            st.markdown(f'<div class="erfassungs-verlauf-kachel">', unsafe_allow_html=True)
                            ec1, ec2 = st.columns([5, 1])
                            with ec1:
                                st.markdown(f"**📅 Standardaufnahme vom {datum_erf}**")
                            with ec2:
                                if st.button("📂 Öffnen", key=f"load_erf_{datum_erf}", use_container_width=True):
                                    st.session_state["ausgewaehlte_erfassung_datum"] = datum_erf
                                    st.session_state["temp_erfassungs_art"] = "Standard"
                                    st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                else:
                    aktuelles_datum = st.session_state["ausgewaehlte_erfassung_datum"]
                    st.info(f"Sie bearbeiten die Aufnahme vom: **{aktuelles_datum}**")
                    if st.button("Zurück zum Verlauf ↩️"):
                        st.session_state["ausgewaehlte_erfassung_datum"] = None
                        st.session_state["temp_erfassungs_art"] = None
                        st.rerun()
                        
                    if st.session_state["temp_erfassungs_art"] == "Heizlast":
                        st.warning("Heizlast-Modul befindet sich im Aufbau (kommt in einem späteren Update).")
                        
                    elif st.session_state["temp_erfassungs_art"] == "Standard":
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("SELECT * FROM gebaeude_erfassung_v2 WHERE obj_nr=? AND erfassungs_datum=?", (obj_nr_aktiv, aktuelles_datum))
                        g_data = c.fetchone()
                        conn.close()
                        
                        # Helper um None/Out of Bounds zu vermeiden
                        def get_val(idx, default=""):
                            return g_data[idx] if g_data and len(g_data) > idx and g_data[idx] is not None else default

                        sd_adresse = sd_daten[2] + ", " + sd_daten[3] if sd_daten else p_daten[2]
                        sd_bj = sd_daten[6] if sd_daten and len(sd_daten)>6 else ""
                        
                        # 5 NEUE REITER
                        erf_tabs = st.tabs(["📝 Allgemein", "🏠 Außen", "🛋️ Innen", "⚙️ Technik", "📋 Sanierungsplanung"])
                        
                        # -------------------------
                        # REITER 1: ALLGEMEIN
                        # -------------------------
                        with erf_tabs[0]:
                            st.markdown("#### 1. Allgemeine Daten")
                            col_a1, col_a2 = st.columns(2)
                            with col_a1:
                                erf_erfasser = st.text_input("Erfasser", value=get_val(2, st.session_state['username']))
                                erf_datum = st.text_input("Datum Vor-Ort Aufnahme", value=get_val(3, datetime.today().strftime('%d.%m.%Y')))
                                erf_adresse = st.text_input("Adresse (aus Stammdaten)", value=sd_adresse, disabled=True)
                            with col_a2:
                                erf_baujahr = st.text_input("Baujahr (aus Stammdaten)", value=sd_bj, disabled=True)
                                typ_list = ["Einfamilienhaus (EFH)", "Zweifamilienhaus (ZFH)", "Mehrfamilienhaus (MFH)", "Reihenmittelhaus (RMH)", "Reihenendhaus (REH)"]
                                curr_typ = get_val(4, "Einfamilienhaus (EFH)")
                                erf_typ = st.selectbox("Gebäudetyp", typ_list, index=typ_list.index(curr_typ) if curr_typ in typ_list else 0)
                                erf_geschosse = st.number_input("Anzahl Vollgeschosse", min_value=1, value=int(get_val(5, 1)) if str(get_val(5, 1)).isdigit() else 1)
                            
                            keller_check = get_val(6, "Ja") == "Ja"
                            erf_keller = "Ja" if st.checkbox("Keller vorhanden?", value=keller_check) else "Nein"

                        # -------------------------
                        # REITER 2: AUßEN (Dach, Wand, Fenster)
                        # -------------------------
                        with erf_tabs[1]:
                            st.markdown("#### 2.1 Dach & Oberste Geschossdecke")
                            d_form_list = ["Satteldach", "Walmdach", "Pultdach", "Flachdach", "Mansarddach"]
                            curr_form = get_val(7, "Satteldach")
                            a_dachform = st.selectbox("Dachform", d_form_list, index=d_form_list.index(curr_form) if curr_form in d_form_list else 0)
                            a_neueindeckung = st.text_input("Datum der letzten Neueindeckung", value=get_val(8))
                            
                            spitz_list = ["Spitzboden vorhanden (kalt)", "Spitzboden vorhanden (warm / ausgebaut)", "Kein Spitzboden"]
                            curr_spitz = get_val(9, spitz_list[0])
                            a_spitzboden = st.selectbox("Spitzboden Zustand", spitz_list, index=spitz_list.index(curr_spitz) if curr_spitz in spitz_list else 0)
                            
                            a_dachueberstand = st.text_input("Dachüberstand (minimal in cm oder pro Seite)", value=get_val(10))
                            a_gauben = st.text_input("Vorhandensein und Form von Dachgauben", value=get_val(11))
                            a_dachfenster = st.text_input("Dachflächenfenster (Anzahl, Baujahr)", value=get_val(12))
                            a_sparren = st.text_input("Sparrendicke / -breite", value=get_val(13))
                            a_dach_infos = st.text_area("Weitere Infos zum Dach", value=get_val(14))
                            a_dach_daemmung = st.text_area("Details der Dachdämmung / oberste Geschossdecke", value=get_val(15))
                            
                            st.markdown("#### 2.2 Wände")
                            a_wanddicke = st.text_input("Gesamtwanddicke incl. Putz (cm)", value=get_val(16))
                            
                            st.markdown("#### 2.3 Fenster & Türen")
                            a_fenstertyp = st.text_input("Fenstertyp / Verglasung", value=get_val(20))
                            a_haustuer = st.text_input("Angabe zur Haus-Tür", value=get_val(21))
                            a_fenster_sonst = st.text_area("Sonstiges (z.B. Infos zur Kellertür, 2. Eingang im MFH)", value=get_val(22))

                        # -------------------------
                        # REITER 3: INNEN
                        # -------------------------
                        with erf_tabs[2]:
                            st.markdown("#### 3. Innenausbau & Stockwerke")
                            i_raumhoehe = st.text_input("Standard-Raumhöhe", value=get_val(19))
                            i_sockel = st.text_input("Sockel (Höhe / Details)", value=get_val(17))
                            i_stockwerke = st.text_area("Weitere Stockwerke / Angaben (z.B. Höhe Spitzboden)", value=get_val(18))

                        # -------------------------
                        # REITER 4: TECHNIK
                        # -------------------------
                        with erf_tabs[3]:
                            st.markdown("#### 4.1 Heizung")
                            t_heiz_typ = st.text_input("Wärmeerzeuger (Manuelle Eingabe, z.B. Viessmann Vitodens 200)", value=get_val(23))
                            t_heiz_baujahr = st.text_input("Baujahr der Heizung", value=get_val(24))
                            t_heiz_ort = st.text_input("Aufstellungsort", value=get_val(25))
                            
                            rohr_list = ["gedämmt", "nicht gedämmt", "teilweise gedämmt"]
                            curr_rohr = get_val(26, rohr_list[0])
                            t_heiz_rohre = st.selectbox("Infos zu den Rohrleitungen", rohr_list, index=rohr_list.index(curr_rohr) if curr_rohr in rohr_list else 0)
                            
                            med_list = ["Öl", "Gas", "Elektro", "Holz/Pellets", "Fernwärme", "Wärmepumpe"]
                            curr_med = get_val(27, med_list[1])
                            t_heiz_medium = st.selectbox("Heizmedium", med_list, index=med_list.index(curr_med) if curr_med in med_list else 1)
                            
                            fl_list = ["Radiatoren / Heizkörper", "Flächenheizung (Fußboden/Wand)"]
                            curr_fl = get_val(33, fl_list[0])
                            t_heiz_flaechen = st.selectbox("Systemart / Heizflächen", fl_list, index=fl_list.index(curr_fl) if curr_fl in fl_list else 0)

                            st.markdown("#### 4.2 Warmwasser")
                            ww_ex_list = ["Nein", "Ja"]
                            curr_ww_ex = get_val(28, "Nein")
                            t_ww_extra = st.radio("Warmwasser zusätzlich über weiteren Wärmeerzeuger?", ww_ex_list, index=ww_ex_list.index(curr_ww_ex) if curr_ww_ex in ww_ex_list else 0)
                            
                            if t_ww_extra == "Ja":
                                t_ww_baujahr = st.text_input("Baujahr Warmwassererzeuger", value=get_val(29))
                                t_ww_medium = st.text_input("Medium Warmwassererzeuger", value=get_val(30))
                                t_ww_speicher = st.radio("Speicher vorhanden?", ["Ja", "Nein"], index=0 if get_val(31, "Ja") == "Ja" else 1)
                                t_ww_pumpe = st.radio("Umwälzpumpe vorhanden?", ["Ja", "Nein"], index=0 if get_val(32, "Ja") == "Ja" else 1)
                            else:
                                t_ww_baujahr, t_ww_medium, t_ww_speicher, t_ww_pumpe = "", "", "", ""
                                
                            st.markdown("#### 4.3 Weitere technische Infos")
                            t_heiz_frei = st.text_area("Freie Eingaben (z.B. Info, dass nur EG Fubo-Heizung hat)", value=get_val(34))

                        # -------------------------
                        # REITER 5: SANIERUNGSPLANUNG
                        # -------------------------
                        with erf_tabs[4]:
                            st.markdown("#### 5. Empfehlung & Priorisierung der Sanierungsmaßnahmen")
                            st.info("💡 **Tipp Vor-Ort:** Erfragen Sie 'Sowieso'-Maßnahmen des Kunden und bewerten Sie den Zustand, um hier direkt eine Empfehlung zur Reihenfolge zu geben.")
                            
                            with st.expander("➕ Neue Maßnahme zur Liste hinzufügen", expanded=True):
                                with st.form("add_sanierung_erfassung"):
                                    col_s1, col_s2, col_s3 = st.columns([2, 4, 1])
                                    with col_s1: s_gewerk = st.selectbox("Gewerk", ["Fassade", "Dach / OGD", "Fenster und Tür", "Anlagentechnik", "Kellerdecke", "Sonstiges"])
                                    with col_s2: s_mass = st.text_input("Konkrete Maßnahme (z.B. 'WP einbauen', 'Neueindeckung geplant')")
                                    with col_s3: s_prio = st.number_input("Priorität (1=Hoch)", min_value=1, max_value=10, value=1)
                                    
                                    if st.form_submit_button("Maßnahme aufnehmen"):
                                        if s_mass:
                                            conn = sqlite3.connect(DB_FILE)
                                            c = conn.cursor()
                                            c.execute("INSERT INTO sanierungen (obj_nr, gewerk, massnahme, prioritaet) VALUES (?, ?, ?, ?)", (obj_nr_aktiv, s_gewerk, s_mass, s_prio))
                                            conn.commit()
                                            conn.close()
                                            st.rerun()
                            
                            # Sanierungstabelle anzeigen
                            conn = sqlite3.connect(DB_FILE)
                            c = conn.cursor()
                            c.execute("SELECT id, gewerk, massnahme, prioritaet FROM sanierungen WHERE obj_nr=? ORDER BY prioritaet ASC", (obj_nr_aktiv,))
                            massnahmen_liste = c.fetchall()
                            conn.close()
                            
                            if not massnahmen_liste:
                                st.caption("Noch keine Sanierungsmaßnahmen für dieses Objekt erfasst.")
                            else:
                                st.markdown("##### 📋 Aktuelle Maßnahmenplanung")
                                for m_id, gew, mass, prio in massnahmen_liste:
                                    m_col1, m_col2, m_col3 = st.columns([1, 4, 1])
                                    m_col1.markdown(f"**Prio {prio}**")
                                    m_col2.write(f"**[{gew}]** {mass}")
                                    if m_col3.button("🗑️", key=f"del_san_erf_{m_id}"):
                                        conn = sqlite3.connect(DB_FILE)
                                        c = conn.cursor()
                                        c.execute("DELETE FROM sanierungen WHERE id=?", (m_id,))
                                        conn.commit()
                                        conn.close()
                                        st.rerun()

                        # --- SPEICHERN DER GEBÄUDEERFASSUNG ---
                        st.divider()
                        if st.button("💾 Alle Gebäude-Daten speichern", use_container_width=True, type="primary"):
                            conn = sqlite3.connect(DB_FILE)
                            c = conn.cursor()
                            c.execute('''INSERT OR REPLACE INTO gebaeude_erfassung_v2 
                                (obj_nr, erfassungs_datum, erfasser, datum_vorort, gebaeudetyp, vollgeschosse, keller, 
                                dachform, dach_neueindeckung, spitzboden, dachueberstand, dachgauben, dachfenster, sparren, dach_infos, dach_daemmung, 
                                wanddicke, sockel, stockwerke, raumhoehe, 
                                fenstertyp, haustuer, fenster_sonst, 
                                heiz_typ, heiz_baujahr, heiz_ort, heiz_rohre, heiz_medium, ww_extra, ww_baujahr, ww_medium, ww_speicher, ww_pumpe, heiz_flaechen, heiz_frei) 
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                (obj_nr_aktiv, aktuelles_datum, erf_erfasser, erf_datum, erf_typ, erf_geschosse, erf_keller,
                                 a_dachform, a_neueindeckung, a_spitzboden, a_dachueberstand, a_gauben, a_dachfenster, a_sparren, a_dach_infos, a_dach_daemmung,
                                 a_wanddicke, i_sockel, i_stockwerke, i_raumhoehe,
                                 a_fenstertyp, a_haustuer, a_fenster_sonst,
                                 t_heiz_typ, t_heiz_baujahr, t_heiz_ort, t_heiz_rohre, t_heiz_medium, t_ww_extra, t_ww_baujahr, t_ww_medium, t_ww_speicher, t_ww_pumpe, t_heiz_flaechen, t_heiz_frei))
                            conn.commit()
                            conn.close()
                            st.success("✅ Gebäudeerfassung erfolgreich gespeichert!")

            # REITER 4: OBJEKT- / ANALYSEDATEN (Ehemals Reiter 5)
            with tabs[3]:
                st.subheader("📊 Auswertungen & Energetische Kennzahlen")
                st.markdown("Hier werden die berechneten Daten grafisch aufbereitet (Soll-Ist-Vergleich für Wärmepumpeneffizienz).")
                
                # Berechnungssimulation
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT flaeche FROM stammdaten WHERE obj_nr=?", (obj_nr_aktiv,))
                sd_fl = c.fetchone()
                conn.close()
                
                if sd_fl and sd_fl[0]:
                    try:
                        flaeche_num = float(sd_fl[0].replace(",", "."))
                        heizlast_schaetzung = round(flaeche_num * 0.05, 2) # Grobe Abschätzung 50W/m²
                        st.metric(label="Geschätzte Heizlast für Wärmepumpenauslegung", value=f"{heizlast_schaetzung} kW")
                    except ValueError:
                        st.warning("Bitte trage unter 'Stammdaten' eine gültige Wohnfläche ein, um Berechnungen zu aktivieren.")
                else:
                    st.info("Trage Objektdaten in den Stammdaten ein, um eine Heizlast-Abschätzung zu generieren.")
                
                st.progress(65)
                st.caption("Bearbeitungsstand des energetischen Berichts: 65% abgeschlossen.")

            # REITER 5: DOKUMENTE & HOTTENROTH-EXPORT
            with tabs[4]:
                st.subheader("📂 Dokumentenverwaltung")
                st.info("Lade hier HottCAD/Hottgenroth Projektdateien (.bph / .hpt) oder Pläne hoch.")
                
                uploaded_file = st.file_uploader("Datei hochladen", type=["pdf", "xlsx", "bph", "hpt", "png", "jpg"])
                if uploaded_file is not None:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("INSERT INTO dokumente (obj_nr, dateiname) VALUES (?, ?)", (obj_nr_aktiv, uploaded_file.name))
                    conn.commit()
                    conn.close()
                    st.success(f"Datei '{uploaded_file.name}' erfolgreich archiviert!")
                
                # Vorhandene Dokumente anzeigen
                st.markdown("##### 📁 Hinterlegte Projektdokumente:")
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT id, dateiname, hochgeladen_am FROM dokumente WHERE obj_nr=?", (obj_nr_aktiv,))
                docs = c.fetchall()
                conn.close()
                
                if not docs:
                    st.caption("Keine Dokumente hochgeladen.")
                else:
                    for d_id, d_name, d_date in docs:
                        dc1, dc2 = st.columns([5, 1])
                        dc1.write(f"📄 {d_name} *(Hochgeladen: {d_date})*")
                        if dc2.button("🗑️", key=f"del_doc_{d_id}"):
                            conn = sqlite3.connect(DB_FILE)
                            c = conn.cursor()
                            c.execute("DELETE FROM dokumente WHERE id=?", (d_id,))
                            conn.commit()
                            conn.close()
                            st.rerun()