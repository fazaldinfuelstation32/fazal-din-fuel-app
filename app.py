import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Page Configuration
st.set_page_config(
    page_title="Fazal Din Fuel Station",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Professional UI
st.markdown("""
    <style>
    .main-header {
        font-size: 30px;
        font-weight: bold;
        color: #1E3A8A;
        text-align: center;
        padding: 10px;
        border-bottom: 3px solid #1E3A8A;
        margin-bottom: 20px;
    }
    .sub-header {
        color: #0D9488;
        font-weight: bold;
    }
    .stMetric {
        background-color: #F3F4F6;
        padding: 10px;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# Database Setup
conn = sqlite3.connect('fuel_station.db', check_same_thread=False)
c = conn.cursor()

# Create Tables
c.execute('''CREATE TABLE IF NOT EXISTS party_sales 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, party_name TEXT, fuel_type TEXT, qty REAL, rate REAL, total REAL, paid REAL, balance REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS vendor_purchases 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, vendor_name TEXT, fuel_type TEXT, qty REAL, rate REAL, total REAL, paid REAL, balance REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS vouchers 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, voucher_type TEXT, account_name TEXT, amount REAL, narration TEXT)''')
conn.commit()

# Header
st.markdown('<div class="main-header">⛽ FAZAL DIN FUEL STATION</div>', unsafe_allow_html=True)
st.caption("Complete Management System: Stock, Vendors, Party Ledgers & Vouchers")

# Sidebar Navigation
st.sidebar.title("📌 Main Menu")
menu = st.sidebar.radio("Navigate", ["📊 Dashboard", "⛽ Party Sale & Credit", "🚛 Vendor Purchasing", "🧾 Voucher Generator", "📑 Ledgers & Reports"])

# Default Rates Setup
if 'petrol_rate' not in st.session_state:
    st.session_state.petrol_rate = 270.0
if 'diesel_rate' not in st.session_state:
    st.session_state.diesel_rate = 280.0

# ---------------- MODULE 1: DASHBOARD ----------------
if menu == "📊 Dashboard":
    st.header("Daily Fuel Rates & Overview")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.petrol_rate = st.number_input("Super Petrol Rate (Rs/Ltr)", value=st.session_state.petrol_rate)
    with col2:
        st.session_state.diesel_rate = st.number_input("HSD Diesel Rate (Rs/Ltr)", value=st.session_state.diesel_rate)
        
    st.divider()
    
    # Overview Metrics
    df_party = pd.read_sql_query("SELECT SUM(total - paid) as total_credit FROM party_sales", conn)
    df_vendor = pd.read_sql_query("SELECT SUM(total - paid) as total_payable FROM vendor_purchases", conn)
    
    total_credit = df_party['total_credit'].iloc[0] if df_party['total_credit'].iloc[0] else 0.0
    total_payable = df_vendor['total_payable'].iloc[0] if df_vendor['total_payable'].iloc[0] else 0.0
    
    m1, m2 = st.columns(2)
    m1.metric("Total Customer Credit Outstanding", f"Rs. {total_credit:,.2f}")
    m2.metric("Total Vendor Payable", f"Rs. {total_payable:,.2f}")

# ---------------- MODULE 2: PARTY CREDIT SALES ----------------
elif menu == "⛽ Party Sale & Credit":
    st.header("Party Daily Credit & Cash Sale Entry")
    
    parties = ["Baba Farid Sugar Mill", "Jalal Din", "Other Cash Sale"]
    selected_party = st.selectbox("Select Party / Customer", parties)
    
    col1, col2, col3 = st.columns(3)
    entry_date = col1.date_input("Date", datetime.now())
    fuel_type = col2.selectbox("Fuel Type", ["Petrol", "Diesel"])
    rate = col3.number_input("Rate", value=st.session_state.petrol_rate if fuel_type=="Petrol" else st.session_state.diesel_rate)
    
    col4, col5 = st.columns(2)
    qty = col4.number_input("Quantity (Liters)", min_value=0.0, step=1.0)
    paid = col5.number_input("Amount Paid (Cash Received)", min_value=0.0, step=10.0)
    
    total = qty * rate
    balance = total - paid
    
    st.info(f"Total Amount: *Rs. {total:,.2f}* | Remaining Balance (Credit): *Rs. {balance:,.2f}*")
    
    if st.button("Save Sale Record"):
        c.execute("INSERT INTO party_sales (date, party_name, fuel_type, qty, rate, total, paid, balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (str(entry_date), selected_party, fuel_type, qty, rate, total, paid, balance))
        conn.commit()
        st.success("Entry Saved Successfully!")

# ---------------- MODULE 3: VENDOR PURCHASING ----------------
elif menu == "🚛 Vendor Purchasing":
    st.header("Vendor Purchasing & Dip Stock Ledger")
    
    vendors = ["Zoom Petroleum", "Pervaiz Petroleum", "Mohaib (Shoaib)", "Crown PSO", "Ittifaq Petroleum"]
    selected_vendor = st.selectbox("Select Vendor", vendors)
    
    col1, col2, col3 = st.columns(3)
    p_date = col1.date_input("Purchase Date", datetime.now())
    p_fuel = col2.selectbox("Fuel Purchased", ["Petrol", "Diesel"])
    p_rate = col3.number_input("Purchase Rate / Ltr", value=250.0)
    
    col4, col5 = st.columns(2)
    p_qty = col4.number_input("Purchased Quantity (Ltrs)", min_value=0.0, step=100.0)
    p_paid = col5.number_input("Payment Paid / Advance", min_value=0.0, step=100.0)
    
    p_total = p_qty * p_rate
    p_balance = p_total - p_paid
    
    st.info(f"Total Bill: *Rs. {p_total:,.2f}* | Remaining Payable: *Rs. {p_balance:,.2f}*")
    
    if st.button("Save Purchase Entry"):
        c.execute("INSERT INTO vendor_purchases (date, vendor_name, fuel_type, qty, rate, total, paid, balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (str(p_date), selected_vendor, p_fuel, p_qty, p_rate, p_total, p_paid, p_balance))
        conn.commit()
        st.success("Vendor Entry Recorded!")

# ---------------- MODULE 4: VOUCHER GENERATOR ----------------
elif menu == "🧾 Voucher Generator":
    st.header("Professional Debit / Credit Voucher")
    
    v_type = st.radio("Voucher Type", ["Receipt Voucher (Credit In)", "Payment Voucher (Debit Out)"])
    v_date = st.date_input("Voucher Date", datetime.now())
    account_name = st.text_input("Account / Party Name")
    v_amount = st.number_input("Amount (Rs.)", min_value=0.0, step=100.0)
    narration = st.text_area("Narration / Details")
    
    if st.button("Generate & Save Voucher"):
        c.execute("INSERT INTO vouchers (date, voucher_type, account_name, amount, narration) VALUES (?, ?, ?, ?, ?)",
                  (str(v_date), v_type, account_name, v_amount, narration))
        conn.commit()
        st.success("Voucher Created!")
        
        # Printable Voucher Slip Card
        st.markdown(f"""
        ---
        ### 📄 FAZAL DIN FUEL STATION - OFFICIAL VOUCHER
        *Type:* {v_type} | *Date:* {v_date}  
        *Account:* {account_name}  
        *Amount:* Rs. {v_amount:,.2f}  
        *Description:* {narration}  
        ---
        """)

# ---------------- MODULE 5: LEDGERS & REPORTS ----------------
elif menu == "📑 Ledgers & Reports":
    st.header("Ledgers & Financial Statements")
    
    report_type = st.selectbox("Select Report", ["Party Credit Statement", "Vendor Purchasing Ledger", "All Vouchers Log"])
    
    if report_type == "Party Credit Statement":
        df = pd.read_sql_query("SELECT * FROM party_sales", conn)
        st.dataframe(df, use_container_width=True)
    elif report_type == "Vendor Purchasing Ledger":
        df = pd.read_sql_query("SELECT * FROM vendor_purchases", conn)
        st.dataframe(df, use_container_width=True)
    elif report_type == "All Vouchers Log":
        df = pd.read_sql_query("SELECT * FROM vouchers", conn)
        st.dataframe(df, use_container_width=True)