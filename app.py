import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ---------------- PAGE CONFIGURATION ----------------
st.set_page_config(
    page_title="Fazal Din Fuel Station - Management Portal",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Theme: Navy Blue & Teak Green)
st.markdown("""
    <style>
    .main-header {
        font-size: 30px;
        font-weight: bold;
        color: white;
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 50%, #0D9488 100%);
        padding: 18px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
    }
    .stButton>button {
        background-color: #1E3A8A !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        border: none !important;
    }
    .stButton>button:hover {
        background-color: #0D9488 !important;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-left: 5px solid #1E3A8A;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------- DATABASE INIT & SCHEMA FIXES ----------------
conn = sqlite3.connect('fuel_station.db', check_same_thread=False)
c = conn.cursor()

# Tables Setup
c.execute('''CREATE TABLE IF NOT EXISTS parties 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, party_name TEXT UNIQUE, opening_balance REAL DEFAULT 0)''')

c.execute('''CREATE TABLE IF NOT EXISTS vendors 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, vendor_name TEXT UNIQUE, opening_balance REAL DEFAULT 0)''')

c.execute('''CREATE TABLE IF NOT EXISTS party_sales 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, party_name TEXT, fuel_type TEXT, qty REAL, rate REAL, purchase_cost REAL, total REAL, paid REAL, balance REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS vendor_purchases 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, vendor_name TEXT, fuel_type TEXT, qty REAL, rate REAL, total REAL, paid REAL, balance REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS vouchers 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, voucher_type TEXT, account_type TEXT, account_name TEXT, amount REAL, narration TEXT)''')
conn.commit()

# Ensure Missing Columns dynamically (Avoid OperationalError)
def ensure_columns():
    try:
        c.execute("ALTER TABLE party_sales ADD COLUMN purchase_cost REAL DEFAULT 0")
        conn.commit()
    except:
        pass
ensure_columns()

# Populate Default Data
default_parties = ['Baba Farid Sugar Mill', 'Jalal Din', 'Fojdari', 'Nemat Mill', 'Feed Mill', 'Fatima Mill', 'Cadet College']
default_vendors = ['Zoom Petroleum', 'Mohaib(Sharoze)', 'Perviaz Petroleum', 'Crown Pso', 'Ittifaq Petroleum']

for p in default_parties:
    c.execute("INSERT OR IGNORE INTO parties (party_name, opening_balance) VALUES (?, 0)", (p,))
for v in default_vendors:
    c.execute("INSERT OR IGNORE INTO vendors (vendor_name, opening_balance) VALUES (?, 0)", (v,))
conn.commit()

# ---------------- LOGIN AUTHENTICATION ----------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="main-header">🔑 FAZAL DIN FUEL STATION - SYSTEM LOGIN</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password")
        if st.button("Login To Station Portal"):
            if username == "admin" and password == "fazaldin123":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect Username or Password!")
    st.stop()

# Header
st.markdown('<div class="main-header">⛽ FAZAL DIN FUEL STATION - OFFICIAL MANAGEMENT PORTAL</div>', unsafe_allow_html=True)

# ---------------- SIDEBAR NAVIGATION ----------------
st.sidebar.title("📌 Navigation Menu")
menu = st.sidebar.radio("Select Portal Module:", [
    "📊 Executive Dashboard & Profit", 
    "⛽ Party Daily Sale & Credit", 
    "🚛 Vendor Purchasing & Dip Stock", 
    "🧾 Debit / Credit Voucher", 
    "📑 Customer / Vendor Statements & Bills", 
    "⚙️ Master Setup (Parties/Vendors)",
    "💾 Backup & System Recovery"
])

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

# Global Average Rates Calculation
def get_avg_purchase_cost(fuel_type):
    res = pd.read_sql_query("SELECT AVG(rate) as avg_rate FROM vendor_purchases WHERE fuel_type=?", conn, params=(fuel_type,))
    val = res['avg_rate'].iloc[0]
    return val if val and val > 0 else (240.0 if fuel_type=="Petrol" else 250.0)

# Default Rates
if 'petrol_sale_rate' not in st.session_state: st.session_state.petrol_sale_rate = 270.0
if 'diesel_sale_rate' not in st.session_state: st.session_state.diesel_sale_rate = 280.0

# ---------------- MODULE 1: DASHBOARD & PROFIT ----------------
if menu == "📊 Executive Dashboard & Profit":
    st.subheader("📊 Financial Overview & Profit / Loss Engine")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.petrol_sale_rate = st.number_input("Super Petrol Daily Selling Rate (Rs/Ltr)", value=st.session_state.petrol_sale_rate)
    with col2:
        st.session_state.diesel_sale_rate = st.number_input("HSD Diesel Daily Selling Rate (Rs/Ltr)", value=st.session_state.diesel_sale_rate)
        
    st.divider()

    # Receivables (Parties)
    parties_df = pd.read_sql_query("SELECT party_name, opening_balance FROM parties", conn)
    sales_df = pd.read_sql_query("SELECT party_name, SUM(balance) as total_bal FROM party_sales GROUP BY party_name", conn)
    p_summary = pd.merge(parties_df, sales_df, on="party_name", how="left").fillna(0)
    p_summary['Total Outstanding'] = p_summary['opening_balance'] + p_summary['total_bal']
    p_summary.insert(0, 'Sr. No.', range(1, 1 + len(p_summary)))

    # Payables (Vendors)
    vendors_df = pd.read_sql_query("SELECT vendor_name, opening_balance FROM vendors", conn)
    purchases_df = pd.read_sql_query("SELECT vendor_name, SUM(balance) as total_bal FROM vendor_purchases GROUP BY vendor_name", conn)
    v_summary = pd.merge(vendors_df, purchases_df, on="vendor_name", how="left").fillna(0)
    v_summary['Total Payable'] = v_summary['opening_balance'] + v_summary['total_bal']
    v_summary.insert(0, 'Sr. No.', range(1, 1 + len(v_summary)))

    # Real-time Profitability Calculation
    profit_df = pd.read_sql_query("SELECT SUM(total) as revenue, SUM(qty * purchase_cost) as cost_of_goods FROM party_sales", conn)
    rev = profit_df['revenue'].iloc[0] if profit_df['revenue'].iloc[0] else 0.0
    cog = profit_df['cost_of_goods'].iloc[0] if profit_df['cost_of_goods'].iloc[0] else 0.0
    est_profit = rev - cog

    m1, m2, m3 = st.columns(3)
    m1.metric("💰 Total Party Credit Outstanding", f"Rs. {p_summary['Total Outstanding'].sum():,.2f}")
    m2.metric("🛑 Total Vendor Liabilities", f"Rs. {v_summary['Total Payable'].sum():,.2f}")
    m3.metric("📈 Estimated Gross Profit", f"Rs. {est_profit:,.2f}", delta=f"{(est_profit/rev*100):.1f}% Margin" if rev>0 else "0%")

    st.divider()
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        st.write("### 👥 Customer Credit Ledger Summary")
        st.dataframe(p_summary[['Sr. No.', 'party_name', 'opening_balance', 'Total Outstanding']].rename(
            columns={'party_name':'Party Name', 'opening_balance':'Op. Balance', 'Total Outstanding':'Net Balance'}), use_container_width=True)
        
    with c_col2:
        st.write("### 🚛 Vendor Liabilities Summary")
        st.dataframe(v_summary[['Sr. No.', 'vendor_name', 'opening_balance', 'Total Payable']].rename(
            columns={'vendor_name':'Vendor Name', 'opening_balance':'Op. Balance', 'Total Payable':'Net Payable'}), use_container_width=True)

# ---------------- MODULE 2: PARTY CREDIT SALES ----------------
elif menu == "⛽ Party Daily Sale & Credit":
    st.subheader("⛽ Daily Party Sale Entry")
    
    party_list = pd.read_sql_query("SELECT party_name FROM parties", conn)['party_name'].tolist()
    selected_party = st.selectbox("Select Party / Customer", party_list)
    
    col1, col2, col3 = st.columns(3)
    entry_date = col1.date_input("Date", datetime.now())
    fuel_type = col2.selectbox("Fuel Type", ["Petrol", "Diesel"])
    sale_rate = col3.number_input("Selling Rate (Rs/Ltr)", value=st.session_state.petrol_sale_rate if fuel_type=="Petrol" else st.session_state.diesel_sale_rate)
    
    avg_cost = get_avg_purchase_cost(fuel_type)
    
    col4, col5 = st.columns(2)
    qty = col4.number_input("Quantity (Liters)", min_value=0.0, step=10.0)
    paid = col5.number_input("Amount Paid (Cash Received)", min_value=0.0, step=10.0)
    
    total = qty * sale_rate
    balance = total - paid
    unit_profit = (sale_rate - avg_cost) * qty
    
    st.info(f"Total Bill: *Rs. {total:,.2f}* | Remaining Credit: *Rs. {balance:,.2f}* | Delivery Est. Profit: *Rs. {unit_profit:,.2f}*")
    
    if st.button("Post Credit Sale Record"):
        c.execute("INSERT INTO party_sales (date, party_name, fuel_type, qty, rate, purchase_cost, total, paid, balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (str(entry_date), selected_party, fuel_type, qty, sale_rate, avg_cost, total, paid, balance))
        conn.commit()
        st.success("Entry Saved Successfully!")

# ---------------- MODULE 3: VENDOR PURCHASING ----------------
elif menu == "🚛 Vendor Purchasing & Dip Stock":
    st.subheader("🚛 Vendor Fuel Purchase & Dip Delivery")
    
    vendor_list = pd.read_sql_query("SELECT vendor_name FROM vendors", conn)['vendor_name'].tolist()
    selected_vendor = st.selectbox("Select Vendor", vendor_list)
    
    col1, col2, col3 = st.columns(3)
    p_date = col1.date_input("Purchase Date", datetime.now())
    p_fuel = col2.selectbox("Fuel Purchased", ["Petrol", "Diesel"])
    p_rate = col3.number_input("Purchase Invoice Rate (Rs/Ltr)", value=245.0)
    
    col4, col5 = st.columns(2)
    p_qty = col4.number_input("Quantity (Liters)", min_value=0.0, step=100.0)
    p_paid = col5.number_input("Payment Paid / Advance", min_value=0.0, step=1000.0)
    
    p_total = p_qty * p_rate
    p_balance = p_total - p_paid
    
    st.info(f"Invoice Total: *Rs. {p_total:,.2f}* | Remaining Vendor Balance: *Rs. {p_balance:,.2f}*")
    
    if st.button("Save Vendor Purchase Entry"):
        c.execute("INSERT INTO vendor_purchases (date, vendor_name, fuel_type, qty, rate, total, paid, balance) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (str(p_date), selected_vendor, p_fuel, p_qty, p_rate, p_total, p_paid, p_balance))
        conn.commit()
        st.success("Purchase Entry Posted!")

# ---------------- MODULE 4: VOUCHER GENERATOR ----------------
elif menu == "🧾 Debit / Credit Voucher":
    st.subheader("🧾 Create Payment Receipt / Delivery Voucher")
    
    v_type = st.radio("Voucher Type", ["Receipt Voucher (Cash In)", "Payment Voucher (Cash Out)"])
    account_type = st.selectbox("Account Category", ["Party / Customer", "Vendor"])
    
    if account_type == "Party / Customer":
        acc_list = pd.read_sql_query("SELECT party_name FROM parties", conn)['party_name'].tolist()
    else:
        acc_list = pd.read_sql_query("SELECT vendor_name FROM vendors", conn)['vendor_name'].tolist()
        
    acc_name = st.selectbox("Account Name", acc_list)
    v_date = st.date_input("Voucher Date", datetime.now())
    v_amount = st.number_input("Amount (Rs.)", min_value=0.0, step=500.0)
    narration = st.text_area("Details / Bank / Slip No / Narration")
    
    if st.button("Generate & Save Voucher"):
        c.execute("INSERT INTO vouchers (date, voucher_type, account_type, account_name, amount, narration) VALUES (?, ?, ?, ?, ?, ?)",
                  (str(v_date), v_type, account_type, acc_name, v_amount, narration))
        
        # Adjusting Ledger Table Balances
        if account_type == "Party / Customer":
            c.execute("INSERT INTO party_sales (date, party_name, fuel_type, qty, rate, purchase_cost, total, paid, balance) VALUES (?, ?, 'Voucher Payment', 0, 0, 0, 0, ?, ?)",
                      (str(v_date), acc_name, v_amount, -v_amount))
        else:
            c.execute("INSERT INTO vendor_purchases (date, vendor_name, fuel_type, qty, rate, total, paid, balance) VALUES (?, ?, 'Voucher Payment', 0, 0, 0, ?, ?)",
                      (str(v_date), acc_name, v_amount, -v_amount))
            
        conn.commit()
        st.success("Voucher Posted and Ledger Updated!")

# ---------------- MODULE 5: STATEMENTS & BILLS ----------------
elif menu == "📑 Customer / Vendor Statements & Bills":
    st.subheader("📑 Date-Wise Detailed Ledger Statements")
    
    st_col1, st_col2 = st.columns(2)
    start_date = st_col1.date_input("From Date", datetime(2026, 1, 1))
    end_date = st_col2.date_input("To Date", datetime.now())
    
    category = st.radio("Category", ["Customer Credit Ledger", "Vendor Ledger"])
    
    if category == "Customer Credit Ledger":
        party_name = st.selectbox("Select Party", pd.read_sql_query("SELECT party_name FROM parties", conn)['party_name'].tolist())
        
        op_bal = pd.read_sql_query("SELECT opening_balance FROM parties WHERE party_name=?", conn, params=(party_name,)).iloc[0,0]
        df = pd.read_sql_query("SELECT date as Date, fuel_type as Fuel, qty as Qty, rate as Rate, total as Bill, paid as Paid, balance as Credit FROM party_sales WHERE party_name=? AND date BETWEEN ? AND ?", 
                               conn, params=(party_name, str(start_date), str(end_date)))
        
        df.insert(0, 'Sr. No.', range(1, 1 + len(df)))
        st.write(f"### Statement for: *{party_name}* | Opening Balance: *Rs. {op_bal:,.2f}*")
        st.dataframe(df, use_container_width=True)
        st.metric("Net Receivable Balance", f"Rs. {(op_bal + df['Credit'].sum()):,.2f}")
        
    else:
        vendor_name = st.selectbox("Select Vendor", pd.read_sql_query("SELECT vendor_name FROM vendors", conn)['vendor_name'].tolist())
        op_bal = pd.read_sql_query("SELECT opening_balance FROM vendors WHERE vendor_name=?", conn, params=(vendor_name,)).iloc[0,0]
        df = pd.read_sql_query("SELECT date as Date, fuel_type as Fuel, qty as Qty, rate as Rate, total as Total, paid as Paid, balance as Payable FROM vendor_purchases WHERE vendor_name=? AND date BETWEEN ? AND ?", 
                               conn, params=(vendor_name, str(start_date), str(end_date)))
        
        df.insert(0, 'Sr. No.', range(1, 1 + len(df)))
        st.write(f"### Vendor Statement: *{vendor_name}* | Opening Balance: *Rs. {op_bal:,.2f}*")
        st.dataframe(df, use_container_width=True)
        st.metric("Net Vendor Payable", f"Rs. {(op_bal + df['Payable'].sum()):,.2f}")

# ---------------- MODULE 6: MASTER SETUP ----------------
elif menu == "⚙️ Master Setup (Parties/Vendors)":
    st.subheader("⚙️ Manage Parties, Vendors & Opening Balances")
    
    tab1, tab2 = st.tabs(["👥 Parties / Customers", "🚛 Vendors"])
    
    with tab1:
        st.write("#### Add / Delete Party")
        col_a, col_b = st.columns(2)
        new_p = col_a.text_input("New Party Name")
        p_op = col_b.number_input("Party Opening Balance (Rs.)", value=0.0)
        if st.button("Add Party Record"):
            if new_p:
                c.execute("INSERT OR REPLACE INTO parties (party_name, opening_balance) VALUES (?, ?)", (new_p, p_op))
                conn.commit()
                st.success(f"Party '{new_p}' Saved!")
                st.rerun()

        st.divider()
        del_p = st.selectbox("Delete Party", ["-- Select --"] + pd.read_sql_query("SELECT party_name FROM parties", conn)['party_name'].tolist())
        if st.button("Delete Selected Party"):
            if del_p != "-- Select --":
                c.execute("DELETE FROM parties WHERE party_name=?", (del_p,))
                conn.commit()
                st.success("Party Removed!")
                st.rerun()

    with tab2:
        st.write("#### Add / Delete Vendor")
        col_v1, col_v2 = st.columns(2)
        new_v = col_v1.text_input("New Vendor Name")
        v_op = col_v2.number_input("Vendor Opening Balance (Rs.)", value=0.0)
        if st.button("Add Vendor Record"):
            if new_v:
                c.execute("INSERT OR REPLACE INTO vendors (vendor_name, opening_balance) VALUES (?, ?)", (new_v, v_op))
                conn.commit()
                st.success(f"Vendor '{new_v}' Saved!")
                st.rerun()

        st.divider()
        del_v = st.selectbox("Delete Vendor", ["-- Select --"] + pd.read_sql_query("SELECT vendor_name FROM vendors", conn)['vendor_name'].tolist())
        if st.button("Delete Selected Vendor"):
            if del_v != "-- Select --":
                c.execute("DELETE FROM vendors WHERE vendor_name=?", (del_v,))
                conn.commit()
                st.success("Vendor Removed!")
                st.rerun()

# ---------------- MODULE 7: BACKUP & RECOVERY ----------------
elif menu == "💾 Backup & System Recovery":
    st.subheader("💾 Data Backup & Recovery Center")
    st.write("Agar aap chahain toh kisi bhi waqt apna mukammal data Excel sheets me download kar saktay hain taake safe rahey.")
    
    df_p = pd.read_sql_query("SELECT * FROM party_sales", conn)
    df_v = pd.read_sql_query("SELECT * FROM vendor_purchases", conn)
    
    st.download_button("📥 Download Customer Sales Backup (CSV)", data=df_p.to_csv(index=False), file_name="Party_Sales_Backup.csv", mime="text/csv")
    st.download_button("📥 Download Vendor Purchases Backup (CSV)", data=df_v.to_csv(index=False), file_name="Vendor_Purchases_Backup.csv", mime="text/csv")
