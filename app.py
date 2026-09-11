import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ---------------- PAGE CONFIGURATION & THEME ----------------
st.set_page_config(
    page_title="Fazal Din Fuel Station - ERP",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Fuel Station Modern UI)
st.markdown("""
    <style>
    .main-header {
        font-size: 28px;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 50%, #0D9488 100%);
        color: #FFFFFF;
        padding: 18px;
        border-radius: 12px;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .metric-card {
        background-color: #F8FAFC;
        border-left: 5px solid #1E3A8A;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stButton>button {
        background: linear-gradient(90deg, #1E3A8A 0%, #0D9488 100%);
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        width: 100%;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #0D9488 0%, #1E3A8A 100%);
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------- SAFE DATABASE SETUP ----------------
conn = sqlite3.connect('fuel_station_v2.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS parties 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, party_name TEXT UNIQUE, opening_balance REAL DEFAULT 0)''')

c.execute('''CREATE TABLE IF NOT EXISTS vendors 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, vendor_name TEXT UNIQUE, opening_balance REAL DEFAULT 0)''')

c.execute('''CREATE TABLE IF NOT EXISTS party_sales 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, party_name TEXT, fuel_type TEXT, qty REAL, purchase_rate REAL, sale_rate REAL, total REAL, paid REAL, balance REAL, profit REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS vendor_purchases 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, vendor_name TEXT, fuel_type TEXT, qty REAL, rate REAL, total REAL, paid REAL, balance REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS vouchers 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, voucher_type TEXT, account_type TEXT, account_name TEXT, amount REAL, narration TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS daily_rates 
             (date TEXT PRIMARY KEY, petrol_buy REAL, petrol_sale REAL, diesel_buy REAL, diesel_sale REAL)''')
conn.commit()

# Default Data Seeding
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

# Header Banner
st.markdown('<div class="main-header">⛽ FAZAL DIN FUEL STATION ERP</div>', unsafe_allow_html=True)

# ---------------- NAVIGATION ----------------
st.sidebar.title("📌 Station Management")
menu = st.sidebar.radio("Modules:", [
    "📊 Executive Dashboard & Profit", 
    "⛽ Party Credit Sale & Billing", 
    "🚛 Vendor Purchasing & Dip Stock", 
    "🧾 Debit / Credit Voucher", 
    "📄 Customer Invoice / Bill Generator",
    "📑 Month-Wise Liabilities & Ledgers", 
    "⚙️ Master Setup (Party/Vendor/Rates)"
])

# ---------------- MODULE 1: DASHBOARD & PROFIT ----------------
if menu == "📊 Executive Dashboard & Profit":
    st.subheader("📊 Financial Overview & Profit Realization")
    
    # Calculate Total Customer Receivables (Previous Balances + Sales - Receipts)
    parties_df = pd.read_sql_query("SELECT party_name, opening_balance FROM parties", conn)
    sales_df = pd.read_sql_query("SELECT party_name, SUM(balance) as net_bal, SUM(profit) as total_profit FROM party_sales GROUP BY party_name", conn)
    party_summary = pd.merge(parties_df, sales_df, on="party_name", how="left").fillna(0)
    party_summary['Total Outstanding'] = party_summary['opening_balance'] + party_summary['net_bal']
    
    # Calculate Total Vendor Payables
    vendors_df = pd.read_sql_query("SELECT vendor_name, opening_balance FROM vendors", conn)
    purchases_df = pd.read_sql_query("SELECT vendor_name, SUM(balance) as net_bal FROM vendor_purchases GROUP BY vendor_name", conn)
    vendor_summary = pd.merge(vendors_df, purchases_df, on="vendor_name", how="left").fillna(0)
    vendor_summary['Total Payable'] = vendor_summary['opening_balance'] + vendor_summary['net_bal']
    
    total_receivables = party_summary['Total Outstanding'].sum()
    total_payables = vendor_summary['Total Payable'].sum()
    total_profit_realized = party_summary['total_profit'].sum()

    m1, m2, m3 = st.columns(3)
    m1.metric("💰 Total Party Receivables", f"Rs. {total_receivables:,.2f}")
    m2.metric("🛑 Total Vendor Liabilities", f"Rs. {total_payables:,.2f}")
    m3.metric("📈 Total Realized Profit/Margin", f"Rs. {total_profit_realized:,.2f}")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.write("### 👥 Top Customer Credit Balances")
        st.dataframe(party_summary[['party_name', 'Total Outstanding']].sort_values(by='Total Outstanding', ascending=False), use_container_width=True)
    with c2:
        st.write("### 🚛 Vendor Payable Liabilities")
        st.dataframe(vendor_summary[['vendor_name', 'Total Payable']].sort_values(by='Total Payable', ascending=False), use_container_width=True)

# ---------------- MODULE 2: PARTY CREDIT SALES ----------------
elif menu == "⛽ Party Credit Sale & Billing":
    st.subheader("⛽ Daily Credit Sale & Margin Capture")
    
    party_list = pd.read_sql_query("SELECT party_name FROM parties", conn)['party_name'].tolist()
    selected_party = st.selectbox("Select Customer / Party", party_list)
    
    # Auto fetch previous outstanding balance
    p_op = pd.read_sql_query("SELECT opening_balance FROM parties WHERE party_name=?", conn, params=(selected_party,)).iloc[0]['opening_balance']
    p_sales = pd.read_sql_query("SELECT SUM(balance) as bal FROM party_sales WHERE party_name=?", conn, params=(selected_party,)).iloc[0]['bal']
    prev_balance = p_op + (p_sales if p_sales else 0.0)
    
    st.warning(f"📌 Previous Outstanding Balance for *{selected_party}: **Rs. {prev_balance:,.2f}*")
    
    col1, col2, col3 = st.columns(3)
    entry_date = col1.date_input("Sale Date", datetime.now())
    fuel_type = col2.selectbox("Fuel Type", ["Petrol", "Diesel"])
    
    col4, col5 = st.columns(2)
    p_rate = col4.number_input("Purchase Cost Rate (Rs/Ltr)", value=250.0)
    s_rate = col5.number_input("Selling Rate (Rs/Ltr)", value=270.0)
    
    col6, col7 = st.columns(2)
    qty = col6.number_input("Quantity (Liters)", min_value=0.0, step=10.0)
    paid = col7.number_input("Cash Received Now", min_value=0.0, step=100.0)
    
    total_sale = qty * s_rate
    current_balance = total_sale - paid
    unit_profit = (s_rate - p_rate) * qty
    net_accumulated_balance = prev_balance + current_balance
    
    st.info(f"Bill Amount: *Rs. {total_sale:,.2f}* | Margin: *Rs. {unit_profit:,.2f}* | New Total Outstanding: *Rs. {net_accumulated_balance:,.2f}*")
    
    if st.button("Post Credit Sale Record"):
        c.execute("INSERT INTO party_sales (date, party_name, fuel_type, qty, purchase_rate, sale_rate, total, paid, balance, profit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (str(entry_date), selected_party, fuel_type, qty, p_rate, s_rate, total_sale, paid, current_balance, unit_profit))
        conn.commit()
        st.success("Transaction Posted Successfully!")

# ---------------- MODULE 3: VENDOR PURCHASING ----------------
elif menu == "🚛 Vendor Purchasing & Dip Stock":
    st.subheader("🚛 Vendor Fuel Purchase Entry")
    
    vendor_list = pd.read_sql_query("SELECT vendor_name FROM vendors", conn)['vendor_name'].tolist()
    selected_vendor = st.selectbox("Select Vendor", vendor_list)
    
    col1, col2, col3 = st.columns(3)
    p_date = col1.date_input("Purchase Date", datetime.now())
    p_fuel = col2.selectbox("Fuel Purchased", ["Petrol", "Diesel"])
    p_rate = col3.number_input("Cost Rate / Ltr", value=250.0)
    
    col4, col5 = st.columns(2)
    p_qty = col4.number_input("Liters Received", min_value=0.0, step=100.0)
    p_paid = col5.number_input("Payment Paid / Advance", min_value=0.0, step=100.0)
    
    p_total = p_qty * p_rate
    p_balance = p_total - p_paid
    
    if st.button("Post Vendor Invoice"):
        c.execute("INSERT INTO vendor_purchases (date, vendor_name, fuel_type, qty, rate, total, paid, balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (str(p_date), selected_vendor, p_fuel, p_qty, p_rate, p_total, p_paid, p_balance))
        conn.commit()
        st.success("Vendor Purchase Logged!")

# ---------------- MODULE 4: VOUCHER GENERATOR ----------------
elif menu == "🧾 Debit / Credit Voucher":
    st.subheader("🧾 Generate Payment Voucher / Receipt")
    
    v_type = st.radio("Voucher Type", ["Receipt Voucher (Cash Received)", "Payment Voucher (Cash Paid)"])
    account_type = st.selectbox("Account Category", ["Party / Customer", "Vendor"])
    
    if account_type == "Party / Customer":
        acc_list = pd.read_sql_query("SELECT party_name FROM parties", conn)['party_name'].tolist()
    else:
        acc_list = pd.read_sql_query("SELECT vendor_name FROM vendors", conn)['vendor_name'].tolist()
        
    acc_name = st.selectbox("Select Account Name", acc_list)
    v_date = st.date_input("Date", datetime.now())
    v_amount = st.number_input("Amount (PKR)", min_value=0.0, step=100.0)
    narration = st.text_area("Narration / Slip Details")
    
    if st.button("Post Voucher"):
        c.execute("INSERT INTO vouchers (date, voucher_type, account_type, account_name, amount, narration) VALUES (?, ?, ?, ?, ?, ?)",
                  (str(v_date), v_type, account_type, acc_name, v_amount, narration))
        
        if account_type == "Party / Customer":
            c.execute("INSERT INTO party_sales (date, party_name, fuel_type, qty, purchase_rate, sale_rate, total, paid, balance, profit) VALUES (?, ?, 'Cash Receipt', 0, 0, 0, 0, ?, ?, 0)",
                      (str(v_date), acc_name, v_amount, -v_amount))
        else:
            c.execute("INSERT INTO vendor_purchases (date, vendor_name, fuel_type, qty, rate, total, paid, balance) VALUES (?, ?, 'Cash Payment', 0, 0, 0, ?, ?)",
                      (str(v_date), acc_name, v_amount, -v_amount))
            
        conn.commit()
        st.success("Voucher Recorded & Balance Updated!")

# ---------------- MODULE 5: INVOICE GENERATOR ----------------
elif menu == "📄 Customer Invoice / Bill Generator":
    st.subheader("📄 Generate Printable Bill / Statement for Party")
    
    party_list = pd.read_sql_query("SELECT party_name FROM parties", conn)['party_name'].tolist()
    selected_party = st.selectbox("Select Party for Billing", party_list)
    
    c1, c2 = st.columns(2)
    s_date = c1.date_input("From Date", datetime(2026, 1, 1))
    e_date = c2.date_input("To Date", datetime.now())
    
    if st.button("Generate Invoice"):
        op_bal = pd.read_sql_query("SELECT opening_balance FROM parties WHERE party_name=?", conn, params=(selected_party,)).iloc[0]['opening_balance']
        sales_data = pd.read_sql_query("SELECT date, fuel_type, qty, sale_rate as rate, total, paid, balance FROM party_sales WHERE party_name=? AND date BETWEEN ? AND ?", 
                                       conn, params=(selected_party, str(s_date), str(e_date)))
        
        st.markdown(f"""
        ---
        ### ⛽ *FAZAL DIN FUEL STATION*
        *CUSTOMER STATEMENT OF ACCOUNT / BILL*  
        *Customer Name:* {selected_party} | *Period:* {s_date} to {e_date}  
        *Opening Balance:* Rs. {op_bal:,.2f}  
        ---
        """)
        
        st.dataframe(sales_data, use_container_width=True)
        net_period_bal = sales_data['balance'].sum() if not sales_data.empty else 0.0
        grand_total_due = op_bal + net_period_bal
        
        st.subheader(f"🔴 Total Payable Balance: *Rs. {grand_total_due:,.2f}*")

# ---------------- MODULE 6: MONTH-WISE LIABILITIES ----------------
elif menu == "📑 Month-Wise Liabilities & Ledgers":
    st.subheader("📑 Month-Wise Liabilities & Detailed Ledgers")
    
    tab1, tab2 = st.tabs(["🗓️ Month-Wise Breakdown", "📖 Full Detailed Ledger"])
    
    with tab1:
        st.write("### Month-Wise Customer Sales & Recoveries")
        df_party_m = pd.read_sql_query("SELECT strftime('%Y-%m', date) as Month, party_name, SUM(total) as Total_Sale, SUM(paid) as Total_Paid, SUM(balance) as Net_Outstanding FROM party_sales GROUP BY Month, party_name", conn)
        st.dataframe(df_party_m, use_container_width=True)
        
        st.write("### Month-Wise Vendor Purchases & Payments")
        df_vendor_m = pd.read_sql_query("SELECT strftime('%Y-%m', date) as Month, vendor_name, SUM(total) as Total_Purchase, SUM(paid) as Total_Paid, SUM(balance) as Net_Payable FROM vendor_purchases GROUP BY Month, vendor_name", conn)
        st.dataframe(df_vendor_m, use_container_width=True)
        
    with tab2:
        acc_type = st.selectbox("Category", ["Customer Party", "Vendor"])
        if acc_type == "Customer Party":
            p_name = st.selectbox("Party Name", pd.read_sql_query("SELECT party_name FROM parties", conn)['party_name'].tolist())
            df_det = pd.read_sql_query("SELECT date, fuel_type, qty, sale_rate, total, paid, balance, profit FROM party_sales WHERE party_name=?", conn, params=(p_name,))
        else:
            v_name = st.selectbox("Vendor Name", pd.read_sql_query("SELECT vendor_name FROM vendors", conn)['vendor_name'].tolist())
            df_det = pd.read_sql_query("SELECT date, fuel_type, qty, rate, total, paid, balance FROM vendor_purchases WHERE vendor_name=?", conn, params=(v_name,))
            
        st.dataframe(df_det, use_container_width=True)

# ---------------- MODULE 7: MASTER SETUP ----------------
elif menu == "⚙️ Master Setup (Party/Vendor/Rates)":
    st.subheader("⚙️ System Setup & Opening Balances")
    
    t1, t2 = st.tabs(["👥 Customer Master", "🚛 Vendor Master"])
    
    with t1:
        new_p = st.text_input("Customer Name")
        p_op = st.number_input("Opening Balance (Rs.)", value=0.0)
        if st.button("Save Customer"):
            c.execute("INSERT OR REPLACE INTO parties (party_name, opening_balance) VALUES (?, ?)", (new_p, p_op))
            conn.commit()
            st.success("Customer Added/Updated!")
            
    with t2:
        new_v = st.text_input("Vendor Name")
        v_op = st.number_input("Vendor Opening Balance (Rs.)", value=0.0)
        if st.button("Save Vendor"):
            c.execute("INSERT OR REPLACE INTO vendors (vendor_name, opening_balance) VALUES (?, ?)", (new_v, v_op))
            conn.commit()
            st.success("Vendor Added/Updated!")
