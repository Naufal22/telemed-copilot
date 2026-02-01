import streamlit as st
import requests
import pandas as pd
import os

# --- CONFIGURATION ---
BACKEND_URL = "http://127.0.0.1:8000"
CSV_PATH = os.path.join(os.path.dirname(__file__), "conversation_data.csv")

# Setup Page: Wide Layout & Dark Theme Preference
st.set_page_config(
    page_title="Telemed Copilot",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🩺"
)

# --- CUSTOM CSS (DARK MODE) ---
st.markdown("""
<style>
    /* Force Dark Background */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Typography */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Headers */
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #4FC3F7; /* Light Blue for Dark Mode */
        margin-bottom: 5px;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #B0BEC5;
        margin-bottom: 25px;
    }
    
    /* Metric Cards (Dark Grey) */
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 8px;
        color: #ffffff;
    }
    div[data-testid="stMetricLabel"] {
        color: #B0BEC5 !important;
    }
    
    /* Tabs Customization */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E1E1E;
        border-radius: 4px;
        color: #FAFAFA;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4FC3F7;
        color: #000000;
    }

    /* Expander in Dark Mode */
    .streamlit-expanderHeader {
        background-color: #262730;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNCTION: LOAD DATA ---
@st.cache_data
def load_conversations(file_path):
    if not os.path.exists(file_path):
        return None
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        st.error(f"Failed to read CSV file: {e}")
        return None

def build_transcript(df, patient_id):
    subset = df[df['ID'] == patient_id]
    full_transcript = ""
    for index, row in subset.iterrows():
        p_text = str(row['Patient_Answer']).strip()
        d_text = str(row['Doctor_response']).strip()
        if p_text and p_text != "nan":
            full_transcript += f"Patient: {p_text}\n"
        if d_text and d_text != "nan":
            full_transcript += f"Doctor: {d_text}\n"
        full_transcript += "\n"
    return full_transcript

# --- LOAD INITIAL DATA ---
df = load_conversations(CSV_PATH)

# --- SIDEBAR (SETTINGS) ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    if df is not None:
        patient_ids = df['ID'].unique().tolist()
        st.subheader("Select Patient Case")
        selected_id = st.selectbox(
            "Patient ID:", 
            patient_ids,
            help="Select a patient case from the CSV database"
        )
    else:
        st.error("CSV Database not found.")
        selected_id = None

    st.markdown("---")
    st.info("💡 **Tip:** Select a case to load the transcript, then click 'Run Analysis'.")
    st.caption("Telehealth AI Assistant v1.0")

# --- MAIN PAGE ---

# 1. DISCLAIMER
st.warning("⚠️ **DEMO MODE:** This tool uses DUMMY DATA. Do not use for real medical decisions.")

# 2. Header
st.markdown('<div class="main-header">Telemed Copilot</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Medical Documentation & Drug Safety Assistant</div>', unsafe_allow_html=True)

# 3. Layout
col_left, col_right = st.columns([1, 1.2], gap="medium")

# --- LEFT COLUMN: INPUT ---
with col_left:
    st.subheader("📄 Conversation Transcript")
    
    transcript_text = ""
    if selected_id and df is not None:
        transcript_text = build_transcript(df, selected_id)
        
        # Dark Text Area
        st.text_area(
            label="Full Text (Read-Only)",
            value=transcript_text,
            height=500,
            disabled=True
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        # Primary Action Button
        analyze_btn = st.button("🚀 Run AI Analysis", type="primary", use_container_width=True)
    else:
        st.info("Please select a Patient ID from the sidebar.")
        analyze_btn = False

# --- RIGHT COLUMN: OUTPUT ---
with col_right:
    st.subheader("📊 Analysis Results")

    # API Logic
    if analyze_btn:
        if not transcript_text:
            st.warning("Transcript is empty.")
        else:
            with st.spinner("Connecting to AI & Drug Database..."):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/generate-note", 
                        json={"transcript": transcript_text},
                        timeout=150 
                    )
                    
                    if response.status_code == 200:
                        st.session_state['result'] = response.json()
                        st.success("Analysis Complete.")
                    else:
                        st.error(f"Server Error: {response.text}")
                        
                except Exception as e:
                    st.error(f"Connection Failed: {e}")

    # Display Results
    if 'result' in st.session_state:
        data = st.session_state['result']
        
        # Dark Mode Tabs
        tab1, tab2, tab3 = st.tabs(["📝 Summary", "⚠️ Risks & Missing", "💊 Drugs"])
        
        # TAB 1: CLINICAL SUMMARY
        with tab1:
            st.markdown("#### Chief Complaint")
            # Metrics look good on dark mode with custom CSS above
            st.metric(label="Primary Issue", value=data.get('chief_complaint', '-'))
            st.metric(label="Duration", value=data.get('duration', '-'))
            
            st.divider()
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("##### Symptoms")
                for s in data.get('symptoms', []):
                    st.markdown(f"- {s}")
            
            with c2:
                st.markdown("##### Medical History")
                history = data.get('medical_history', [])
                if history:
                    for h in history:
                        st.markdown(f"- {h}")
                else:
                    st.markdown("- No significant history")

        # TAB 2: RISKS & MISSING INFO
        with tab2:
            st.markdown("#### Red Flags (Safety Alerts)")
            red_flags = data.get('red_flags', [])
            
            if red_flags:
                for rf in red_flags:
                    st.error(f"🚨 {rf}") 
            else:
                st.success("✅ No Red Flags detected.")

            st.divider()

            st.markdown("#### Missing Information")
            missing = data.get('missing_info', [])
            
            if missing:
                for m in missing:
                    st.warning(f"❓ {m}")
            else:
                st.info("Clinical information appears complete.")

        # TAB 3: DRUG DETAILS
        with tab3:
            st.markdown("#### Detected Medications")
            meds = data.get('medications_mentioned', [])
            
            if meds:
                for med in meds:
                    with st.expander(f"💊 Drug Info: {med}"):
                        try:
                            # Fetch Detail from Backend
                            res_drug = requests.get(f"{BACKEND_URL}/drugs/{med}")
                            if res_drug.status_code == 200:
                                d_info = res_drug.json()
                                st.markdown(f"**Dosage:** {d_info.get('dosage', 'Data not available')}")
                                st.markdown("**FDA Warnings:**")
                                # Using st.info in dark mode creates a nice blue box
                                st.info(d_info.get('warnings', 'No specific warnings.')[:500] + "...")
                            else:
                                st.text("Details not found in FDA database.")
                        except:
                            st.text("Failed to fetch drug data.")
            else:
                st.info("No medications detected in this conversation.")

    else:
        st.info("Select a patient from the left sidebar and click 'Run AI Analysis'.")