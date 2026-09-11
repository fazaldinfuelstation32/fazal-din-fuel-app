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
        font-size: 28px;
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
    </style>
""", unsafe_allow_html=True)

# ---------------- DATABASE INIT & SCHEMA AUTO-FIXES ----------------
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
             (id INTEGER PRIMARY KEY AUTOINCREMENT, voucher_no TEXT, date TEXT, voucher_type TEXT, account_type TEXT, account_name TEXT, amount REAL, narration TEXT)''')
conn.commit()

# Ensure Missing Columns dynamically to fix SQLite operational errors
def auto_migrate_db():
    # Fix vouchers table if missing voucher_no
    c.execute("PRAGMA table_info(vouchers)")
    voucher_cols = [col[1] for col in c.fetchall()]
    if 'voucher_no' not in voucher_cols:
        try:
            c.execute("ALTER TABLE vouchers ADD COLUMN voucher_no TEXT")
            conn.commit()
        except:
            pass

    # Fix party_sales table if missing purchase_cost
    c.execute("PRAGMA table_info(party_sales)")
    ps_cols = [col[1] for col in c.fetchall()]
    if 'purchase_cost' not in ps_cols:
        try:
            c.execute("ALTER TABLE party_sales ADD COLUMN purchase_cost REAL DEFAULT 0")
            conn.commit()
        except:
            pass

auto_migrate_db()

# Populate Default Data
default_parties = ['Baba Farid Sugar Mill', 'Jalal Din', 'Fojdari', 'Nemat Mill', 'Feed Mill', 'Fatima Mill', 'Ravi Rice', 'R.J 39D', 'Malika Rice', 'Cadet College']
default_vendors = ['Zoom Petroleum', 'Mohaib(Sharoze)', 'Perviaz Petroleum', 'Crown Pso', 'Ittifaq Petroleum']

for p in default_parties:
    c.execute("INSERT OR IGNORE INTO parties (party_name, opening_balance) VALUES (?, 0)", (p,))
for v in default_vendors:
    c.execute("INSERT OR IGNORE INTO vendors (vendor_name, opening_balance) VALUES (?, 0)", (v,))
conn.commit()

# Helper Functions
def generate_voucher_no():
    today_str = datetime.now().strftime("%Y%m%d")
    c.execute("SELECT COUNT(*) FROM vouchers WHERE voucher_no LIKE ?", (f"VCH-{today_str}-%",))
    count = c.fetchone()[0] + 1
    return f"VCH-{today_str}-{count:04d}"

def get_avg_purchase_cost(fuel_type):
    res = pd.read_sql_query("SELECT AVG(rate) as avg_rate FROM vendor_purchases WHERE fuel_type=?", conn, params=(fuel_type,))
    val = res['avg_rate'].iloc[0]
    return val if val and val > 0 else (240.0 if fuel_type=="Petrol" else 250.0)

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

if 'petrol_sale_rate' not in st.session_state: st.session_state.petrol_sale_rate = 270.0
if 'diesel_sale_rate' not in st.session_state: st.session_state.diesel_sale_rate = 280.0

# ---------------- SIDEBAR NAVIGATION ----------------
st.sidebar.title("📌 Navigation Menu")
menu = st.sidebar.radio("Select Portal Module:", [
    "📊 Dashboard & Separate Fuel Breakdown", 
    "⛽ Party Daily Sale & Credit", 
    "🚛 Vendor Purchasing & Dip Stock", 
    "📦 Stock Matching & Monthly Reconciliation",
    "🧾 Debit / Credit Voucher", 
    "✏️ Edit / Delete Entries",
    "📑 Customer / Vendor Statements & Bills", 
    "⚙️ Master Setup (Parties/Vendors)",
    "💾 Backup & System Recovery"
])

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

# ---------------- MODULE 1: DASHBOARD ----------------
if menu == "📊 Dashboard & Separate Fuel Breakdown":
    st.subheader("📊 Station Dashboard & Fuel Wise Breakdown")
    
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

    # Fuel Liters Statistics
    p_purchased = pd.read_sql_query("SELECT SUM(qty) as total FROM vendor_purchases WHERE fuel_type='Petrol'", conn)['total'].iloc[0] or 0.0
    p_sold = pd.read_sql_query("SELECT SUM(qty) as total FROM party_sales WHERE fuel_type='Petrol'", conn)['total'].iloc[0] or 0.0
    
    d_purchased = pd.read_sql_query("SELECT SUM(qty) as total FROM vendor_purchases WHERE fuel_type='Diesel'", conn)['total'].iloc[0] or 0.0
    d_sold = pd.read_sql_query("SELECT SUM(qty) as total FROM party_sales WHERE fuel_type='Diesel'", conn)['total'].iloc[0] or 0.0

    # Summary Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Party Receivables", f"Rs. {p_summary['Total Outstanding'].sum():,.2f}")
    c2.metric("🛑 Total Vendor Payables", f"Rs. {v_summary['Total Payable'].sum():,.2f}")
    c3.metric("⛽ Petrol Net Stock", f"{(p_purchased - p_sold):,.2f} Ltrs", delta=f"In: {p_purchased:,.0f} L | Out: {p_sold:,.0f} L")
    c4.metric("🛢️ Diesel Net Stock", f"{(d_purchased - d_sold):,.2f} Ltrs", delta=f"In: {d_purchased:,.0f} L | Out: {d_sold:,.0f} L")

    st.divider()
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        st.write("### 👥 Customer Credit Ledger (Receivables)")
        st.dataframe(
            p_summary[['Sr. No.', 'party_name', 'opening_balance', 'Total Outstanding']].rename(
                columns={'party_name':'Party Name', 'opening_balance':'Op. Balance', 'Total Outstanding':'Net Balance'}
            ), 
            use_container_width=True, 
            hide_index=True
        )
        
    with c_col2:
        st.write("### 🚛 Vendor Liabilities (Payables)")
        st.dataframe(
            v_summary[['Sr. No.', 'vendor_name', 'opening_balance', 'Total Payable']].rename(
                columns={'vendor_name':'Vendor Name', 'opening_balance':'Op. Balance', 'Total Payable':'Net Payable'}
            ), 
            use_container_width=True, 
            hide_index=True
        )

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
        c.execute("INSERT INTO vendor_purchases (date, vendor_name, fuel_type, qty, rate, total, paid, balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (str(p_date), selected_vendor, p_fuel, p_qty, p_rate, p_total, p_paid, p_balance))
        conn.commit()
        st.success("Purchase Entry Posted!")

# ---------------- MODULE 4: STOCK RECONCILIATION ----------------
elif menu == "📦 Stock Matching & Monthly Reconciliation":
    st.subheader("📦 Monthly Purchase Stock vs Sale Matching Engine")
    
    s_col1, s_col2 = st.columns(2)
    m_start = s_col1.date_input("Start Date", datetime(2026, 9, 1))
    m_end = s_col2.date_input("End Date", datetime.now())
    
    st.divider()
    
    p_in = pd.read_sql_query("SELECT SUM(qty) as total FROM vendor_purchases WHERE fuel_type='Petrol' AND date BETWEEN ? AND ?", conn, params=(str(m_start), str(m_end)))['total'].iloc[0] or 0.0
    p_out = pd.read_sql_query("SELECT SUM(qty) as total FROM party_sales WHERE fuel_type='Petrol' AND date BETWEEN ? AND ?", conn, params=(str(m_start), str(m_end)))['total'].iloc[0] or 0.0
    
    d_in = pd.read_sql_query("SELECT SUM(qty) as total FROM vendor_purchases WHERE fuel_type='Diesel' AND date BETWEEN ? AND ?", conn, params=(str(m_start), str(m_end)))['total'].iloc[0] or 0.0
    d_out = pd.read_sql_query("SELECT SUM(qty) as total FROM party_sales WHERE fuel_type='Diesel' AND date BETWEEN ? AND ?", conn, params=(str(m_start), str(m_end)))['total'].iloc[0] or 0.0
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### ⛽ Petrol Reconciliation")
        st.write(f"- Total Purchased Stock: *{p_in:,.2f} Liters*")
        st.write(f"- Total Credit Sold Stock: *{p_out:,.2f} Liters*")
        diff_p = p_in - p_out
        if diff_p >= 0:
            st.success(f"Remaining Dip Stock Balance: *{diff_p:,.2f} Liters*")
        else:
            st.warning(f"Stock Deficit / Excess Sale: *{diff_p:,.2f} Liters*")
            
    with col_b:
        st.markdown("### 🛢️ Diesel Reconciliation")
        st.write(f"- Total Purchased Stock: *{d_in:,.2f} Liters*")
        st.write(f"- Total Credit Sold Stock: *{d_out:,.2f} Liters*")
        diff_d = d_in - d_out
        if diff_d >= 0:
            st.success(f"Remaining Dip Stock Balance: *{diff_d:,.2f} Liters*")
        else:
            st.warning(f"Stock Deficit / Excess Sale: *{diff_d:,.2f} Liters*")

# ---------------- MODULE 5: VOUCHER GENERATOR ----------------
elif menu == "🧾 Debit / Credit Voucher":
    st.subheader("🧾 Create Payment Receipt / Delivery Voucher")
    
    v_no = generate_voucher_no()
    st.write(f"#### Generated Voucher Number: *{v_no}*")
    
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
        c.execute("INSERT INTO vouchers (voucher_no, date, voucher_type, account_type, account_name, amount, narration) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (v_no, str(v_date), v_type, account_type, acc_name, v_amount, narration))
        
        if account_type == "Party / Customer":
            c.execute("INSERT INTO party_sales (date, party_name, fuel_type, qty, rate, purchase_cost, total, paid, balance) VALUES (?, ?, 'Voucher Payment', 0, 0, 0, 0, ?, ?)",
                      (str(v_date), acc_name, v_amount, -v_amount))
        else:
            c.execute("INSERT INTO vendor_purchases (date, vendor_name, fuel_type, qty, rate, total, paid, balance) VALUES (?, ?, 'Voucher Payment', 0, 0, 0, ?, ?)",
                      (str(v_date), acc_name, v_amount, -v_amount))
            
        conn.commit()
        st.success(f"Voucher {v_no} Posted and Ledger Updated!")

# ---------------- MODULE 6: EDIT / DELETE ENTRIES ----------------
elif menu == "✏️ Edit / Delete Entries":
    st.subheader("✏️ Manage, Edit & Delete Recorded Entries")
    
    tab_e1, tab_e2 = st.tabs(["⛽ Edit Party Sales", "🚛 Edit Vendor Purchases"])
    
    with tab_e1:
        st.write("#### Party Sales Records")
        ps_df = pd.read_sql_query("SELECT id, date, party_name, fuel_type, qty, rate, total, paid, balance FROM party_sales ORDER BY id DESC", conn)
        if not ps_df.empty:
            sel_sale_id = st.selectbox("Select Party Sale ID to Modify", ps_df['id'].tolist())
            curr_row = ps_df[ps_df['id'] == sel_sale_id].iloc[0]
            
            e_col1, e_col2, e_col3 = st.columns(3)
            e_qty = e_col1.number_input("Edit Qty", value=float(curr_row['qty']))
            e_rate = e_col2.number_input("Edit Rate", value=float(curr_row['rate']))
            e_paid = e_col3.number_input("Edit Paid Amount", value=float(curr_row['paid']))
            
            e_total = e_qty * e_rate
            e_bal = e_total - e_paid
            
            c_ed1, c_ed2 = st.columns(2)
            if c_ed1.button("Update Party Entry"):
                c.execute("UPDATE party_sales SET qty=?, rate=?, total=?, paid=?, balance=? WHERE id=?", 
                          (e_qty, e_rate, e_total, e_paid, e_bal, sel_sale_id))
                conn.commit()
                st.success("Record Updated Successfully!")
                st.rerun()
                
            if c_ed2.button("Delete Party Entry"):
                c.execute("DELETE FROM party_sales WHERE id=?", (sel_sale_id,))
                conn.commit()
                st.warning("Record Deleted!")
                st.rerun()
                
            st.dataframe(ps_df, use_container_width=True, hide_index=True)

    with tab_e2:
        st.write("#### Vendor Purchase Records")
        vp_df = pd.read_sql_query("SELECT id, date, vendor_name, fuel_type, qty, rate, total, paid, balance FROM vendor_purchases ORDER BY id DESC", conn)
        if not vp_df.empty:
            sel_pur_id = st.selectbox("Select Vendor Purchase ID to Modify", vp_df['id'].tolist())
            curr_v_row = vp_df[vp_df['id'] == sel_pur_id].iloc[0]
            
            ev_col1, ev_col2, ev_col3 = st.columns(3)
            ev_qty = ev_col1.number_input("Edit Vendor Qty", value=float(curr_v_row['qty']))
            ev_rate = ev_col2.number_input("Edit Vendor Rate", value=float(curr_v_row['rate']))
            ev_paid = ev_col3.number_input("Edit Vendor Paid", value=float(curr_v_row['paid']))
            
            ev_total = ev_qty * ev_rate
            ev_bal = ev_total - ev_paid
            
            cv_ed1, cv_ed2 = st.columns(2)
            if cv_ed1.button("Update Vendor Entry"):
                c.execute("UPDATE vendor_purchases SET qty=?, rate=?, total=?, paid=?, balance=? WHERE id=?", 
                          (ev_qty, ev_rate, ev_total, ev_paid, ev_bal, sel_pur_id))
                conn.commit()
                st.success("Vendor Record Updated!")
                st.rerun()
                
            if cv_ed2.button("Delete Vendor Entry"):
                c.execute("DELETE FROM vendor_purchases WHERE id=?", (sel_pur_id,))
                conn.commit()
                st.warning("Vendor Record Deleted!")
                st.rerun()
                
            st.dataframe(vp_df, use_container_width=True, hide_index=True)

# ---------------- MODULE 7: STATEMENTS & BILLS ----------------
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
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.metric("Net Receivable Balance", f"Rs. {(op_bal + df['Credit'].sum()):,.2f}")
        
    else:
        vendor_name = st.selectbox("Select Vendor", pd.read_sql_query("SELECT vendor_name FROM vendors", conn)['vendor_name'].tolist())
        op_bal = pd.read_sql_query("SELECT opening_balance FROM vendors WHERE vendor_name=?", conn, params=(vendor_name,)).iloc[0,0]
        df = pd.read_sql_query("SELECT date as Date, fuel_type as Fuel, qty as Qty, rate as Rate, total as Total, paid as Paid, balance as Payable FROM vendor_purchases WHERE vendor_name=? AND date BETWEEN ? AND ?", 
                               conn, params=(vendor_name, str(start_date), str(end_date)))
        
        df.insert(0, 'Sr. No.', range(1, 1 + len(df)))
        st.write(f"### Vendor Statement: *{vendor_name}* | Opening Balance: *Rs. {op_bal:,.2f}*")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.metric("Net Vendor Payable", f"Rs. {(op_bal + df['Payable'].sum()):,.2f}")

# ---------------- MODULE 8: MASTER SETUP ----------------
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

# ---------------- MODULE 9: BACKUP & RECOVERY ----------------
elif menu == "💾 Backup & System Recovery":
    st.subheader("💾 Data Backup & Recovery Center")
    st.write("Download your complete database backups anytime:")
    
    df_p = pd.read_sql_query("SELECT * FROM party_sales", conn)
    df_v = pd.read_sql_query("SELECT * FROM vendor_purchases", conn)
    
    st.download_button("📥 Download Customer Sales Backup (CSV)", data=df_p.to_csv(index=False), file_name="Party_Sales_Backup.csv", mime="text/csv")
    st.download_button("📥 Download Vendor Purchases Backup (CSV)", data=df_v.to_csv(index=False), file_name="Vendor_Purchases_Backup.csv", mime="text/csv")
