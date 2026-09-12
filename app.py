import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# --- 1. Excel File se Parties Load Karna ---
@st.cache_data
def load_excel_parties(file_path):
    try:
        # Excel file ki sabhi sheet names ya specific sheet me se Party names read karna
        excel_data = pd.read_excel(file_path, sheet_name=None)
        parties = set()
        
        for sheet_name, df in excel_data.items():
            # Column headers ko clean aur lower case me check karen
            cols = [str(c).strip().lower() for c in df.columns]
            for col_name in df.columns:
                if 'party' in str(col_name).lower() or 'customer' in str(col_name).lower():
                    parties.update(df[col_name].dropna().unique())
        
        # Unique and cleaned list return karen
        party_list = sorted(list(set([str(p).strip() for p in parties if str(p).strip()])))
        return party_list
    except Exception as e:
        return ["Baba Farid Sugar Mill"] # Fallback default

# Streamlit App - Statement & Ledger Section
st.title("FD CNG Station")
st.subheader("Party Statement & Printable Ledger")

# Load parties from uploaded Excel file
excel_file_path = "Party_Daily_Credit_Sale_FD new (1).xlsx"
all_parties = load_excel_parties(excel_file_path)

# Dropdowns Layout
col1, col2 = st.columns(2)
with col1:
    party_type = st.selectbox("Select Party Type", ["Customer", "Vendor"])
with col2:
    selected_party = st.selectbox("Select Party Name", all_parties if all_parties else ["Baba Farid Sugar Mill"])

# Opening Balance Display Header
opening_balance = 0.00
st.info(f"**Party:** {selected_party} | **Type:** {party_type} | **Opening Balance:** Rs. {opening_balance:.2f}")

# --- Sample Data (Replace this part with your actual Database Query) ---
data = [
    {"Date": "2026-09-12", "Fuel": "Petrol", "Ltrs": 500, "Rate": None, "Debit": 0, "Credit": 0, "Description": ""},
    {"Date": "2026-09-12", "Fuel": "Petrol", "Ltrs": 500, "Rate": 350, "Debit": 175000, "Credit": 0, "Description": ""},
]

# DataFrame Build Karna
df = pd.DataFrame(data)

# --- 2. Serial Number (1 se Start karna) & Headers Capitalize Karna ---
# Calculate Running Balance
df['Running Balance'] = (df['Debit'] - df['Credit']).cumsum()

# Serial Number Column Index 1 se Start Karna
df.insert(0, 'Sr #', range(1, len(df) + 1))

# Headers Title Case / Capitalize Ensure Karna
df.columns = [col.title() for col in df.columns]

# --- Table Display ---
# hide_index=True se streamlit ka default '0, 1' index hide ho jayega
st.dataframe(df, hide_index=True, use_container_width=True)

# --- 3. Custom Print Button & Printable View Section ---
st.markdown("---")
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    # Print Button through JavaScript trigger
    if st.button("🖨️ Print Ledger Statement"):
        components.html(
            """
            <script>
                window.parent.print();
            </script>
            """,
            height=0,
            width=0
        )

# Printable CSS styling Inject (Taake Print me extra UI elements hide ho jayen)
st.markdown("""
    <style>
    @media print {
        /* Print press karne par Sidebar, Buttons aur Header hide kar dega */
        section[data-testid="stSidebar"], 
        header, 
        footer, 
        .stButton {
            display: none !important;
        }
        .main .block-container {
            padding-top: 1rem !important;
            max-width: 100% !important;
        }
    }
    </style>
""", unsafe_html=True)
