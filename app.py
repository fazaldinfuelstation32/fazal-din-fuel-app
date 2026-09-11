import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ---------------- PAGE CONFIGURATION ----------------
st.set_page_config(
    page_title="Fazal Din Fuel Station",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS Styling
st.markdown("""
    <style>
    .main-header {
        font-size: 32px;
        font-weight: bold;
        color: #0F172A;
        text-align: center;
        background: linear-gradient(90deg, #1E3A8A 0%, #0D9488 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .card-title {
        font-size: 16px;
        font-weight: 600;
        color: #475569;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #1E293B;
    }
    .stButton>button {
        background-color: #1E3A8A;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 8px 16px;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #0D9488;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------- DATABASE INITIALIZATION ----------------
conn = sqlite3.connect('fuel_station.db', check_same_thread=False)
c = conn.cursor()

# Tables Setup
c.execute('''CREATE TABLE IF NOT EXISTS parties 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, party_name TEXT UNIQUE, opening_balance REAL DEFAULT 0)''')

c.execute('''CREATE TABLE IF NOT EXISTS vendors 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, vendor_name TEXT UNIQUE, opening_balance REAL DEFAULT 0)''')

c.execute('''CREATE TABLE IF NOT EXISTS party_sales 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, party_name TEXT, fuel_type TEXT, qty REAL, rate REAL, total REAL, paid REAL, balance REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS vendor_purchases 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, vendor_name TEXT, fuel_type TEXT, qty REAL, rate REAL, total REAL, paid REAL, balance REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS vouchers 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, voucher_type TEXT, account_type TEXT, account_name TEXT, amount REAL, narration TEXT)''')
conn.commit()

# Populate Default Parties & Vendors from Excel Data if Empty
default_parties = [
    'Baba Farid Sugar Mill', 'Jalal Din', 'Fojdari', 'Nemat Mill', 'Feed Mill', 
    'Fatima Mill', 'Ravi Rice', 'R.J 39D', 'Malika Rice', 'Cadet College', 
    '26/d Form', 'Ravi Trader(Atiq Sb)', 'AK Trader', 'Siddique Zarai Form', 
    'Zia ur Rehman', 'Arshad Protein', '27 Murabba', 'Aleem Khan', 'Umer Sb', 
    'M Transport', 'Sheraz+Shafqat', 'Nadeem Cashier (Cash Sale)'
]
default_vendors = ['Zoom Petroleum', 'Mohaib(Sharoze)', 'Perviaz Petroleum', 'Crown Pso', 'Ittifaq Petroleum']

for p in default_parties:
    c.execute("INSERT OR IGNORE INTO parties (party_name, opening_balance) VALUES (?, 0)", (p,))
for v in default_vendors:
    c.execute("INSERT OR IGNORE INTO vendors (vendor_name, opening_balance) VALUES (?, 0)", (v,))
conn.commit()

# Header
st.markdown('<div class="main-header">⛽ FAZAL DIN FUEL STATION</div>', unsafe_allow_html=True)

# ---------------- SIDEBAR NAVIGATION ----------------
st.sidebar.title("📌 Main Navigation")
menu = st.sidebar.radio("Go To Module:", [
    "📊 Executive Dashboard", 
    "⛽ Party Daily Sale & Credit", 
    "🚛 Vendor Purchasing", 
    "🧾 Debit / Credit Voucher", 
    "📑 Date-Wise Statements", 
    "⚙️ Master Setup (Add Party/Vendor)"
])

# Default Rates
if 'petrol_rate' not in st.session_state:
    st.session_state.petrol_rate = 270.0
if 'diesel_rate' not in st.session_state:
    st.session_state.diesel_rate = 280.0

# ---------------- MODULE 1: EXECUTIVE DASHBOARD ----------------
if menu == "📊 Executive Dashboard":
    st.subheader("📊 Financial Overview & Rates")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.petrol_rate = st.number_input("Super Petrol Rate (Rs/Ltr)", value=st.session_state.petrol_rate)
    with col2:
        st.session_state.diesel_rate = st.number_input("HSD Diesel Rate (Rs/Ltr)", value=st.session_state.diesel_rate)
        
    st.divider()

    # Financial Calculations
    # 1. Total Customer Receivables (Assets)
    parties_df = pd.read_sql_query("SELECT party_name, opening_balance FROM parties", conn)
    sales_df = pd.read_sql_query("SELECT party_name, SUM(balance) as total_bal FROM party_sales GROUP BY party_name", conn)
    party_summary = pd.merge(parties_df, sales_df, on="party_name", how="left").fillna(0)
    party_summary['Total Outstanding'] = party_summary['opening_balance'] + party_summary['total_bal']
    total_receivables = party_summary['Total Outstanding'].sum()

    # 2. Total Vendor Payables (Liabilities)
    vendors_df = pd.read_sql_query("SELECT vendor_name, opening_balance FROM vendors", conn)
    purchases_df = pd.read_sql_query("SELECT vendor_name, SUM(balance) as total_bal FROM vendor_purchases GROUP BY vendor_name", conn)
    vendor_summary = pd.merge(vendors_df, purchases_df, on="vendor_name", how="left").fillna(0)
    vendor_summary['Total Payable'] = vendor_summary['opening_balance'] + vendor_summary['total_bal']
    total_payables = vendor_summary['Total Payable'].sum()

    m1, m2 = st.columns(2)
    m1.metric("💰 Total Customer Receivables (Aasani / Recovery)", f"Rs. {total_receivables:,.2f}")
    m2.metric("🛑 Total Liabilities & Vendor Payables (Dene Wahi Rqam)", f"Rs. {total_payables:,.2f}", delta_color="inverse")

    st.divider()
    c_col1, c_col2 = st.columns(2)
    
    with c_col1:
        st.write("### 👥 Daily Credit Parties Summary")
        st.dataframe(party_summary[['party_name', 'Total Outstanding']].rename(columns={'party_name':'Party Name'}), use_container_width=True)
        
    with c_col2:
        st.write("### 🚛 Vendor Liabilities Summary")
        st.dataframe(vendor_summary[['vendor_name', 'Total Payable']].rename(columns={'vendor_name':'Vendor Name'}), use_container_width=True)

# ---------------- MODULE 2: PARTY CREDIT SALES ----------------
elif menu == "⛽ Party Daily Sale & Credit":
    st.subheader("⛽ Party Daily Credit & Cash Sale Entry")
    
    party_list = pd.read_sql_query("SELECT party_name FROM parties", conn)['party_name'].tolist()
    selected_party = st.selectbox("Select Party / Customer Name", party_list)
    
    col1, col2, col3 = st.columns(3)
    entry_date = col1.date_input("Date", datetime.now())
    fuel_type = col2.selectbox("Fuel Type", ["Petrol", "Diesel"])
    rate = col3.number_input("Rate (Rs/Ltr)", value=st.session_state.petrol_rate if fuel_type=="Petrol" else st.session_state.diesel_rate)
    
    col4, col5 = st.columns(2)
    qty = col4.number_input("Quantity (Liters)", min_value=0.0, step=1.0)
    paid = col5.number_input("Cash Received (If Any)", min_value=0.0, step=10.0)
    
    total = qty * rate
    balance = total - paid
    
    st.info(f"Total Amount: *Rs. {total:,.2f}* | Remaining Credit Balance: *Rs. {balance:,.2f}*")
    
    if st.button("Save Credit Sale Record"):
        c.execute("INSERT INTO party_sales (date, party_name, fuel_type, qty, rate, total, paid, balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (str(entry_date), selected_party, fuel_type, qty, rate, total, paid, balance))
        conn.commit()
        st.success("Record Saved Successfully!")

# ---------------- MODULE 3: VENDOR PURCHASING ----------------
elif menu == "🚛 Vendor Purchasing":
    st.subheader("🚛 Vendor Fuel Purchasing Entry")
    
    vendor_list = pd.read_sql_query("SELECT vendor_name FROM vendors", conn)['vendor_name'].tolist()
    selected_vendor = st.selectbox("Select Vendor Name", vendor_list)
    
    col1, col2, col3 = st.columns(3)
    p_date = col1.date_input("Date", datetime.now())
    p_fuel = col2.selectbox("Fuel Purchased", ["Petrol", "Diesel"])
    p_rate = col3.number_input("Purchase Rate / Ltr", value=250.0)
    
    col4, col5 = st.columns(2)
    p_qty = col4.number_input("Quantity (Liters)", min_value=0.0, step=100.0)
    p_paid = col5.number_input("Amount Paid / Advance", min_value=0.0, step=100.0)
    
    p_total = p_qty * p_rate
    p_balance = p_total - p_paid
    
    st.info(f"Total Invoice: *Rs. {p_total:,.2f}* | Remaining Vendor Balance: *Rs. {p_balance:,.2f}*")
    
    if st.button("Save Purchase Entry"):
        c.execute("INSERT INTO vendor_purchases (date, vendor_name, fuel_type, qty, rate, total, paid, balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (str(p_date), selected_vendor, p_fuel, p_qty, p_rate, p_total, p_paid, p_balance))
        conn.commit()
        st.success("Vendor Purchase Recorded!")

# ---------------- MODULE 4: VOUCHER GENERATOR ----------------
elif menu == "🧾 Debit / Credit Voucher":
    st.subheader("🧾 Create Payment Receipt / Delivery Voucher")
    
    v_type = st.radio("Voucher Type", ["Receipt Voucher (Cash Received)", "Payment Voucher (Cash Paid)"])
    account_type = st.selectbox("Account Type", ["Party / Customer", "Vendor"])
    
    if account_type == "Party / Customer":
        acc_list = pd.read_sql_query("SELECT party_name FROM parties", conn)['party_name'].tolist()
    else:
        acc_list = pd.read_sql_query("SELECT vendor_name FROM vendors", conn)['vendor_name'].tolist()
        
    acc_name = st.selectbox("Select Account Name", acc_list)
    v_date = st.date_input("Voucher Date", datetime.now())
    v_amount = st.number_input("Amount (Rs.)", min_value=0.0, step=100.0)
    narration = st.text_area("Details / Slip No / Narration")
    
    if st.button("Generate & Post Voucher"):
        c.execute("INSERT INTO vouchers (date, voucher_type, account_type, account_name, amount, narration) VALUES (?, ?, ?, ?, ?, ?)",
                  (str(v_date), v_type, account_type, acc_name, v_amount, narration))
        
        # Auto update balance in ledgers
        if account_type == "Party / Customer":
            c.execute("INSERT INTO party_sales (date, party_name, fuel_type, qty, rate, total, paid, balance) VALUES (?, ?, 'Voucher Payment', 0, 0, 0, ?, ?)",
                      (str(v_date), acc_name, v_amount, -v_amount))
        else:
            c.execute("INSERT INTO vendor_purchases (date, vendor_name, fuel_type, qty, rate, total, paid, balance) VALUES (?, ?, 'Voucher Payment', 0, 0, 0, ?, ?)",
                      (str(v_date), acc_name, v_amount, -v_amount))
            
        conn.commit()
        st.success("Voucher Created and Ledger Updated Successfully!")

# ---------------- MODULE 5: DATE-WISE STATEMENTS ----------------
elif menu == "📑 Date-Wise Statements":
    st.subheader("📑 Date-Wise Ledger Statements")
    
    st_col1, st_col2 = st.columns(2)
    start_date = st_col1.date_input("Start Date", datetime(2026, 1, 1))
    end_date = st_col2.date_input("End Date", datetime.now())
    
    report_type = st.selectbox("Select Statement Category", ["Party Ledger", "Vendor Ledger", "All Vouchers Log"])
    
    if report_type == "Party Ledger":
        party_name = st.selectbox("Select Party", pd.read_sql_query("SELECT party_name FROM parties", conn)['party_name'].tolist())
        df = pd.read_sql_query("SELECT date, fuel_type, qty, rate, total, paid, balance FROM party_sales WHERE party_name=? AND date BETWEEN ? AND ?", 
                               conn, params=(party_name, str(start_date), str(end_date)))
        st.write(f"### Ledger for: *{party_name}*")
        st.dataframe(df, use_container_width=True)
        
    elif report_type == "Vendor Ledger":
        vendor_name = st.selectbox("Select Vendor", pd.read_sql_query("SELECT vendor_name FROM vendors", conn)['vendor_name'].tolist())
        df = pd.read_sql_query("SELECT date, fuel_type, qty, rate, total, paid, balance FROM vendor_purchases WHERE vendor_name=? AND date BETWEEN ? AND ?", 
                               conn, params=(vendor_name, str(start_date), str(end_date)))
        st.write(f"### Ledger for Vendor: *{vendor_name}*")
        st.dataframe(df, use_container_width=True)
        
    elif report_type == "All Vouchers Log":
        df = pd.read_sql_query("SELECT * FROM vouchers WHERE date BETWEEN ? AND ?", conn, params=(str(start_date), str(end_date)))
        st.dataframe(df, use_container_width=True)

# ---------------- MODULE 6: MASTER SETUP ----------------
elif menu == "⚙️ Master Setup (Add Party/Vendor)":
    st.subheader("⚙️ Add New Party / Vendor & Opening Balance")
    
    setup_tab1, setup_tab2 = st.tabs(["➕ Add New Party", "➕ Add New Vendor"])
    
    with setup_tab1:
        new_party = st.text_input("New Party / Customer Name")
        p_op_bal = st.number_input("Opening Balance (In Rs.)", value=0.0, key="party_op")
        if st.button("Add Party"):
            if new_party:
                c.execute("INSERT OR REPLACE INTO parties (party_name, opening_balance) VALUES (?, ?)", (new_party, p_op_bal))
                conn.commit()
                st.success(f"Party '{new_party}' Added Successfully!")
            else:
                st.warning("Please enter party name.")
                
    with setup_tab2:
        new_vendor = st.text_input("New Vendor / Pump Name")
        v_op_bal = st.number_input("Opening Balance (In Rs.)", value=0.0, key="vendor_op")
        if st.button("Add Vendor"):
            if new_vendor:
                c.execute("INSERT OR REPLACE INTO vendors (vendor_name, opening_balance) VALUES (?, ?)", (new_vendor, v_op_bal))
                conn.commit()
                st.success(f"Vendor '{new_vendor}' Added Successfully!")
            else:
                st.warning("Please enter vendor name.")
