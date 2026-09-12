import streamlit as st
import pandas as pd
import sqlite3
import datetime
from datetime import date
import json

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM COLOR SCHEME
# ==========================================
st.set_page_config(
    page_title="FD CNG Fuel Station",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Contrast CSS Theme (Light Ice Blue, Navy Blue & Pure White Text)
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #F1F5F9 !important;
        color: #0F172A !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 2px solid #334155;
    }
    
    /* Sidebar Text & Navigation Labels - Pure White */
    section[data-testid="stSidebar"] *, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] p {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    
    /* Headers & Text High Contrast */
    h1, h2, h3, h4, h5, h6, label, p, span {
        color: #0F172A !important;
    }
    
    /* Stat Cards Styling */
    .stat-card {
        background: #FFFFFF !important;
        border: 2px solid #CBD5E1 !important;
        border-radius: 10px !important;
        padding: 18px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 12px !important;
    }
    .stat-title {
        color: #475569 !important;
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
    }
    .stat-value {
        color: #0F172A !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
    }
    
    /* Section Headers */
    .section-header {
        border-left: 6px solid #0284C7 !important;
        padding-left: 12px !important;
        margin-bottom: 20px !important;
        font-weight: 800 !important;
        color: #0F172A !important;
        font-size: 1.5rem !important;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #0284C7 !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
        border: none !important;
        font-weight: 700 !important;
        padding: 8px 18px !important;
    }
    .stButton>button:hover {
        background-color: #0369A1 !important;
    }
    
    /* Dataframes */
    div[data-testid="stDataFrame"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGIN AUTHENTICATION SYSTEM
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login_screen():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style='background-color:#FFFFFF; padding:30px; border-radius:12px; border:2px solid #CBD5E1; text-align:center;'>
            <h2 style='color:#0F172A;'>⛽ FD CNG Fuel Station</h2>
            <p style='color:#64748B;'>Please enter login credentials to access management app.</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("🔑 Login to Portal", use_container_width=True)
            
            if submit_login:
                if username == "Fdcngpump" and password == "Fazal661112@":
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Invalid Username or Password!")

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()

# ==========================================
# 3. DATABASE SETUP & MASTER SEEDING
# ==========================================
DB_FILE = "fd_cng_fuel_station.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Master Parties Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        type TEXT CHECK(type IN ('Customer', 'Vendor')) NOT NULL,
        opening_balance REAL DEFAULT 0.0,
        phone TEXT
    )
    """)
    
    # Daily Stock Register Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_register (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT NOT NULL,
        item_type TEXT CHECK(item_type IN ('Petrol', 'Diesel')) NOT NULL,
        opening_stock REAL DEFAULT 0.0,
        rate REAL DEFAULT 0.0,
        opening_amount REAL DEFAULT 0.0,
        purchase_qty REAL DEFAULT 0.0,
        purchase_rate REAL DEFAULT 0.0,
        purchase_amount REAL DEFAULT 0.0,
        total_purchase_amount REAL DEFAULT 0.0,
        avg_rate REAL DEFAULT 0.0,
        available_stock REAL DEFAULT 0.0,
        sales_qty REAL DEFAULT 0.0,
        sales_rate REAL DEFAULT 0.0,
        sales_amount REAL DEFAULT 0.0,
        total_sales_amount REAL DEFAULT 0.0,
        closing_amount REAL DEFAULT 0.0,
        closing_stock REAL DEFAULT 0.0,
        dip_diff REAL DEFAULT 0.0,
        actual_stock REAL DEFAULT 0.0,
        actual_amount REAL DEFAULT 0.0
    )
    """)
    
    # Master Ledger Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        txn_date TEXT NOT NULL,
        party_name TEXT NOT NULL,
        party_type TEXT CHECK(party_type IN ('Customer', 'Vendor')) NOT NULL,
        item_type TEXT,
        qty_ltrs REAL DEFAULT 0.0,
        rate REAL DEFAULT 0.0,
        debit REAL DEFAULT 0.0,
        credit REAL DEFAULT 0.0,
        description TEXT,
        FOREIGN KEY (party_name) REFERENCES parties (name)
    )
    """)
    
    # Seed Customers & Vendors List
    cursor.execute("SELECT COUNT(*) FROM parties")
    if cursor.fetchone()[0] == 0:
        default_parties = [
            ('Baba Farid Sugar Mill', 'Customer', 0.0, ''),
            ('Jalal Din', 'Customer', 0.0, ''),
            ('Fojdari', 'Customer', 0.0, ''),
            ('Nemat Mill', 'Customer', 0.0, ''),
            ('Feed Mill', 'Customer', 0.0, ''),
            ('Fatima Mill', 'Customer', 0.0, ''),
            ('Ravi Rice', 'Customer', 0.0, ''),
            ('R.J 39D', 'Customer', 0.0, ''),
            ('Zoom Petroleum', 'Vendor', 0.0, ''),
            ('Mohaib(Sharoz)', 'Vendor', 0.0, ''),
            ('Pervaiz Petroleum', 'Vendor', 0.0, ''),
            ('Crown Pso', 'Vendor', 0.0, ''),
            ('Ittifaq Petroleum', 'Vendor', 0.0, '')
        ]
        cursor.executemany("INSERT INTO parties (name, type, opening_balance, phone) VALUES (?, ?, ?, ?)", default_parties)
        
    conn.commit()
    conn.close()

init_db()

# Helper Query Functions
def fetch_parties(p_type=None):
    conn = get_db_connection()
    if p_type:
        df = pd.read_sql_query("SELECT id, name, type, opening_balance, phone FROM parties WHERE type = ? ORDER BY name ASC", conn, params=(p_type,))
    else:
        df = pd.read_sql_query("SELECT id, name, type, opening_balance, phone FROM parties ORDER BY type ASC, name ASC", conn)
    conn.close()
    return df

def calculate_party_balances(party_type):
    conn = get_db_connection()
    parties = pd.read_sql_query("SELECT name, opening_balance FROM parties WHERE type = ?", conn, params=(party_type,))
    ledger = pd.read_sql_query("SELECT party_name, debit, credit FROM ledger WHERE party_type = ?", conn, params=(party_type,))
    conn.close()
    
    result = []
    for _, party in parties.iterrows():
        p_name = party['name']
        op_bal = party['opening_balance']
        p_ledger = ledger[ledger['party_name'] == p_name]
        
        tot_debit = p_ledger['debit'].sum()
        tot_credit = p_ledger['credit'].sum()
        
        if party_type == 'Customer':
            net_balance = op_bal + tot_debit - tot_credit
        else:
            net_balance = op_bal + tot_credit - tot_debit
            
        result.append({
            'Party Name': p_name,
            'Op. Balance': op_bal,
            'Total Debit': tot_debit,
            'Total Credit': tot_credit,
            'Net Balance': net_balance
        })
    return pd.DataFrame(result)

def get_running_statement(party_name, party_type):
    conn = get_db_connection()
    party_info = conn.execute("SELECT opening_balance FROM parties WHERE name = ?", (party_name,)).fetchone()
    op_bal = party_info['opening_balance'] if party_info else 0.0
    
    df = pd.read_sql_query(
        "SELECT id, txn_date as Date, item_type as Fuel, qty_ltrs as Ltrs, rate as Rate, debit as Debit, credit as Credit, description as Description FROM ledger WHERE party_name = ? ORDER BY txn_date ASC, id ASC",
        conn, params=(party_name,)
    )
    conn.close()
    
    running_balance = op_bal
    balances = []
    for _, row in df.iterrows():
        if party_type == 'Customer':
            running_balance += (row['Debit'] - row['Credit'])
        else:
            running_balance += (row['Credit'] - row['Debit'])
        balances.append(running_balance)
        
    df['Running Balance'] = balances
    return op_bal, df

# ==========================================
# 4. SIDEBAR NAVIGATION
# ==========================================
st.sidebar.markdown("## ⛽ FD CNG Fuel Station")
st.sidebar.markdown("---")

module = st.sidebar.radio(
    "Navigation Menu",
    [
        "📊 Dashboard & Monthly Analytics",
        "📄 Customer/Vendor Statements & Print",
        "🛢️ Daily Stock Register",
        "💳 Party Daily Sale & Credit Entry",
        "🚛 Vendor Purchasing & Dip Stock",
        "✏️ Edit / Manage Entries",
        "⚖️ Stock vs Sale Month-End Match",
        "⚙️ Master Setup (Parties/Vendors)",
        "💾 Backup & System Recovery"
    ]
)

if st.sidebar.button("🚪 Logout"):
    st.session_state["authenticated"] = False
    st.rerun()

# ==========================================
# MODULE 1: DASHBOARD
# ==========================================
if module == "📊 Dashboard & Monthly Analytics":
    st.markdown("<div class='section-header'>Dashboard & Monthly Breakdown</div>", unsafe_allow_html=True)
    
    cust_df = calculate_party_balances('Customer')
    vend_df = calculate_party_balances('Vendor')
    
    tot_receivables = cust_df['Net Balance'].sum()
    tot_payables = vend_df['Net Balance'].sum()
    
    conn = get_db_connection()
    fuel_summary = pd.read_sql_query("SELECT item_type, SUM(qty_ltrs) as total_ltrs FROM ledger WHERE item_type IS NOT NULL GROUP BY item_type", conn)
    conn.close()
    
    petrol_ltrs = fuel_summary[fuel_summary['item_type']=='Petrol']['total_ltrs'].sum() if not fuel_summary.empty else 0
    diesel_ltrs = fuel_summary[fuel_summary['item_type']=='Diesel']['total_ltrs'].sum() if not fuel_summary.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='stat-card'><div class='stat-title'>Total Receivables</div><div class='stat-value'>Rs. {tot_receivables:,.2f}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='stat-card'><div class='stat-title'>Total Payables</div><div class='stat-value'>Rs. {tot_payables:,.2f}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='stat-card'><div class='stat-title'>Total Petrol Sold</div><div class='stat-value'>{petrol_ltrs:,.2f} Ltrs</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='stat-card'><div class='stat-title'>Total Diesel Sold</div><div class='stat-value'>{diesel_ltrs:,.2f} Ltrs</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🗓️ Monthly Breakdown (Petrol & Diesel Wise)")
    
    conn = get_db_connection()
    monthly_query = """
    SELECT strftime('%Y-%m', txn_date) as Month, party_type as Type, party_name as Party, item_type as Fuel, SUM(qty_ltrs) as Total_Ltrs, SUM(debit + credit) as Total_Amount
    FROM ledger WHERE item_type IN ('Petrol', 'Diesel') GROUP BY Month, party_type, party_name, item_type ORDER BY Month DESC, Party ASC
    """
    m_df = pd.read_sql_query(monthly_query, conn)
    conn.close()

    tab1, tab2 = st.tabs(["👥 Customer Monthly Summary", "🏢 Vendor Monthly Summary"])
    
    with tab1:
        cust_m = m_df[m_df['Type'] == 'Customer']
        if not cust_m.empty:
            pivot_cust = cust_m.pivot_table(index=['Month', 'Party'], columns='Fuel', values=['Total_Ltrs', 'Total_Amount'], aggfunc='sum', fill_value=0)
            st.dataframe(pivot_cust, use_container_width=True)
        else:
            st.info("No customer transaction records found.")

    with tab2:
        vend_m = m_df[m_df['Type'] == 'Vendor']
        if not vend_m.empty:
            pivot_vend = vend_m.pivot_table(index=['Month', 'Party'], columns='Fuel', values=['Total_Ltrs', 'Total_Amount'], aggfunc='sum', fill_value=0)
            st.dataframe(pivot_vend, use_container_width=True)
        else:
            st.info("No vendor transaction records found.")

# ==========================================
# MODULE 2: PARTY STATEMENT & DIRECT PRINT
# ==========================================
elif module == "📄 Customer/Vendor Statements & Print":
    st.markdown("<div class='section-header'>Party Statement & Printable Ledger</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        p_type = st.selectbox("Select Party Type", ["Customer", "Vendor"])
    with col2:
        parties_list = fetch_parties(p_type)['name'].tolist()
        selected_party = st.selectbox("Select Party Name", parties_list if parties_list else ["None"])

    if selected_party and selected_party != "None":
        op_bal, stmt_df = get_running_statement(selected_party, p_type)
        
        st.markdown(f"#### Statement Statement Header")
        st.info(f"**Party Name:** {selected_party} | **Type:** {p_type} | **Opening Balance:** Rs. {op_bal:,.2f}")
        
        st.dataframe(stmt_df, use_container_width=True)
        
        # Direct Print Logic
        print_html = f"""
        <html>
        <head>
        <title>FD CNG Fuel Station - Statement</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h2 {{ text-align: center; margin-bottom: 5px; }}
            p {{ text-align: center; margin-top: 0px; font-size: 14px; }}
            .header-table {{ width: 100%; margin-bottom: 20px; border-collapse: collapse; }}
            .header-table td {{ padding: 5px; font-weight: bold; }}
            .data-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            .data-table th, .data-table td {{ border: 1px solid #333; padding: 8px; text-align: left; font-size: 13px; }}
            .data-table th {{ background-color: #f2f2f2; }}
        </style>
        </head>
        <body>
            <h2>FD CNG FUEL STATION</h2>
            <p>Account Ledger Statement</p>
            <hr>
            <table class="header-table">
                <tr>
                    <td>Party Name: {selected_party}</td>
                    <td>Party Type: {p_type}</td>
                </tr>
                <tr>
                    <td>Opening Balance: Rs. {op_bal:,.2f}</td>
                    <td>Statement Date: {date.today().strftime('%Y-%m-%d')}</td>
                </tr>
            </table>
            {stmt_df.to_html(index=False, classes='data-table')}
            <script>
                window.onload = function() {{ window.print(); }}
            </script>
        </body>
        </html>
        """
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.download_button(
                label="🖨️ Direct Print / Save PDF",
                data=print_html,
                file_name=f"Statement_{selected_party}_{date.today()}.html",
                mime="text/html"
            )
        with col_btn2:
            st.download_button(
                label="📥 Export Excel CSV",
                data=stmt_df.to_csv(index=False).encode('utf-8'),
                file_name=f"Statement_{selected_party}_{date.today()}.csv",
                mime="text/csv"
            )

# ==========================================
# MODULE 3: DAILY STOCK REGISTER
# ==========================================
elif module == "🛢️ Daily Stock Register":
    st.markdown("<div class='section-header'>Daily Stock Register</div>", unsafe_allow_html=True)

    with st.form("stock_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            e_date = st.date_input("Entry Date", date.today())
            item_type = st.selectbox("Fuel Item", ["Petrol", "Diesel"])
            op_stock = st.number_input("Opening Stock (Ltrs)", min_value=0.0, step=1.0, value=None)
            op_rate = st.number_input("Opening Rate", min_value=0.0, step=0.01, value=None)
        with c2:
            p_qty = st.number_input("Purchase Qty (Ltrs)", min_value=0.0, step=1.0, value=None)
            p_rate = st.number_input("Purchase Rate", min_value=0.0, step=0.01, value=None)
            s_qty = st.number_input("Sales Qty (Ltrs)", min_value=0.0, step=1.0, value=None)
            s_rate = st.number_input("Sales Rate", min_value=0.0, step=0.01, value=None)
        with c3:
            actual_stock = st.number_input("Actual Dip Stock (Ltrs)", min_value=0.0, step=1.0, value=None)

        submit_stock = st.form_submit_button("💾 Save Daily Stock Entry")

    if submit_stock:
        v_op_stock = op_stock or 0.0
        v_op_rate = op_rate or 0.0
        v_p_qty = p_qty or 0.0
        v_p_rate = p_rate or 0.0
        v_s_qty = s_qty or 0.0
        v_s_rate = s_rate or 0.0
        v_actual_stock = actual_stock or 0.0

        op_amount = v_op_stock * v_op_rate
        p_amount = v_p_qty * v_p_rate
        tot_p_amount = op_amount + p_amount
        avail_stock = v_op_stock + v_p_qty
        avg_rate = (tot_p_amount / avail_stock) if avail_stock > 0 else 0.0
        
        s_amount = v_s_qty * v_s_rate
        tot_s_amount = v_s_qty * avg_rate
        closing_amount = tot_p_amount - tot_s_amount
        closing_stock = avail_stock - v_s_qty
        dip_diff = v_actual_stock - closing_stock
        act_amount = v_actual_stock * avg_rate

        conn = get_db_connection()
        conn.execute("""
        INSERT INTO stock_register (
            entry_date, item_type, opening_stock, rate, opening_amount, purchase_qty, purchase_rate,
            purchase_amount, total_purchase_amount, avg_rate, available_stock, sales_qty, sales_rate,
            sales_amount, total_sales_amount, closing_amount, closing_stock, dip_diff, actual_stock, actual_amount
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(e_date), item_type, v_op_stock, v_op_rate, op_amount, v_p_qty, v_p_rate,
            p_amount, tot_p_amount, avg_rate, avail_stock, v_s_qty, v_s_rate,
            s_amount, tot_s_amount, closing_amount, closing_stock, dip_diff, v_actual_stock, act_amount
        ))
        conn.commit()
        conn.close()
        st.success("Daily stock record updated!")

    st.markdown("### 📊 Existing Stock Records Log")
    conn = get_db_connection()
    stock_df = pd.read_sql_query("SELECT * FROM stock_register ORDER BY entry_date DESC, id DESC", conn)
    conn.close()
    st.dataframe(stock_df, use_container_width=True)

# ==========================================
# MODULE 4: PARTY DAILY SALE
# ==========================================
elif module == "💳 Party Daily Sale & Credit Entry":
    st.markdown("<div class='section-header'>Customer Credit Sale & Voucher Entry</div>", unsafe_allow_html=True)
    
    customers = fetch_parties('Customer')['name'].tolist()
    
    with st.form("credit_sale_form"):
        c1, c2 = st.columns(2)
        with c1:
            txn_date = st.date_input("Transaction Date", date.today())
            party_name = st.selectbox("Customer Name", customers if customers else ["None"])
            fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel", "Cash Payment/Voucher"])
        with c2:
            qty = st.number_input("Qty (Ltrs)", min_value=0.0, step=1.0, value=None)
            rate = st.number_input("Rate", min_value=0.0, step=0.01, value=None)
            payment = st.number_input("Amount Received/Credit (Rs.)", min_value=0.0, step=100.0, value=None)
            desc = st.text_input("Description / Slip No.")
            
        submit_credit = st.form_submit_button("💾 Save Customer Transaction")
        
    if submit_credit and party_name != "None":
        v_qty = qty or 0.0
        v_rate = rate or 0.0
        v_payment = payment or 0.0
        
        debit = v_qty * v_rate if fuel != "Cash Payment/Voucher" else 0.0
        credit = v_payment
        
        conn = get_db_connection()
        conn.execute("""
        INSERT INTO ledger (txn_date, party_name, party_type, item_type, qty_ltrs, rate, debit, credit, description)
        VALUES (?, ?, 'Customer', ?, ?, ?, ?, ?, ?)
        """, (str(txn_date), party_name, fuel if fuel != "Cash Payment/Voucher" else None, v_qty, v_rate, debit, credit, desc))
        conn.commit()
        conn.close()
        st.success("Customer transaction recorded successfully!")

# ==========================================
# MODULE 5: VENDOR PURCHASING
# ==========================================
elif module == "🚛 Vendor Purchasing & Dip Stock":
    st.markdown("<div class='section-header'>Vendor Purchasing & Payments</div>", unsafe_allow_html=True)
    
    vendors = fetch_parties('Vendor')['name'].tolist()
    
    with st.form("vendor_form"):
        c1, c2 = st.columns(2)
        with c1:
            txn_date = st.date_input("Date", date.today())
            vendor_name = st.selectbox("Vendor Name", vendors if vendors else ["None"])
            fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel", "Direct Payment"])
        with c2:
            qty = st.number_input("Qty Received (Ltrs)", min_value=0.0, step=1.0, value=None)
            rate = st.number_input("Purchase Rate", min_value=0.0, step=0.01, value=None)
            paid_amount = st.number_input("Payment Paid to Vendor (Rs.)", min_value=0.0, step=100.0, value=None)
            desc = st.text_input("Invoice / Tanker No.")
            
        submit_vendor = st.form_submit_button("💾 Save Vendor Transaction")
        
    if submit_vendor and vendor_name != "None":
        v_qty = qty or 0.0
        v_rate = rate or 0.0
        v_paid = paid_amount or 0.0
        
        credit = v_qty * v_rate if fuel != "Direct Payment" else 0.0
        debit = v_paid
        
        conn = get_db_connection()
        conn.execute("""
        INSERT INTO ledger (txn_date, party_name, party_type, item_type, qty_ltrs, rate, debit, credit, description)
        VALUES (?, ?, 'Vendor', ?, ?, ?, ?, ?, ?)
        """, (str(txn_date), vendor_name, fuel if fuel != "Direct Payment" else None, v_qty, v_rate, debit, credit, desc))
        conn.commit()
        conn.close()
        st.success("Vendor purchase transaction recorded!")

# ==========================================
# MODULE 6: EDIT / MANAGE ENTRIES
# ==========================================
elif module == "✏️ Edit / Manage Entries":
    st.markdown("<div class='section-header'>Editable Ledger & Record Management</div>", unsafe_allow_html=True)
    
    conn = get_db_connection()
    df_ledger = pd.read_sql_query("SELECT * FROM ledger ORDER BY txn_date DESC, id DESC", conn)
    conn.close()
    
    st.caption("Aap neeche kisi bhi row par double click karke uski entries directly update kar sakte hain.")
    
    edited_df = st.data_editor(df_ledger, num_rows="dynamic", use_container_width=True, key="ledger_editor")
    
    if st.button("💾 Save All Changes"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ledger")
        for _, row in edited_df.iterrows():
            if pd.notna(row['party_name']) and str(row['party_name']).strip() != '':
                cursor.execute("""
                INSERT INTO ledger (id, txn_date, party_name, party_type, item_type, qty_ltrs, rate, debit, credit, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (row['id'], str(row['txn_date']), row['party_name'], row['party_type'], row['item_type'], row['qty_ltrs'], row['rate'], row['debit'], row['credit'], row['description']))
        conn.commit()
        conn.close()
        st.success("All ledger updates saved!")

# ==========================================
# MODULE 7: RECONCILIATION
# ==========================================
elif module == "⚖️ Stock vs Sale Month-End Match":
    st.markdown("<div class='section-header'>Stock & Sales Month-End Reconciliation</div>", unsafe_allow_html=True)
    
    conn = get_db_connection()
    stock_summary = pd.read_sql_query("""
    SELECT item_type, SUM(purchase_qty) as total_purchased, SUM(sales_qty) as total_stock_sales, SUM(dip_diff) as total_dip_variance
    FROM stock_register GROUP BY item_type
    """, conn)
    
    ledger_summary = pd.read_sql_query("""
    SELECT item_type, SUM(qty_ltrs) as total_ledger_sales
    FROM ledger WHERE party_type = 'Customer' AND item_type IS NOT NULL GROUP BY item_type
    """, conn)
    conn.close()
    
    reconcil = pd.merge(stock_summary, ledger_summary, on='item_type', how='outer').fillna(0)
    reconcil['Sales Variance'] = reconcil['total_stock_sales'] - reconcil['total_ledger_sales']
    
    st.dataframe(reconcil, use_container_width=True)

# ==========================================
# MODULE 8: MASTER SETUP (ADD / REMOVE PARTIES)
# ==========================================
elif module == "⚙️ Master Setup (Parties/Vendors)":
    st.markdown("<div class='section-header'>Master Parties Setup & Management</div>", unsafe_allow_html=True)
    
    tab_add, tab_del = st.tabs(["➕ Add New Party/Vendor", "❌ Remove Existing Party"])
    
    with tab_add:
        with st.form("add_party_form"):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Party / Vendor Name")
                p_type = st.selectbox("Type", ["Customer", "Vendor"])
            with c2:
                op_bal = st.number_input("Opening Balance (Rs.)", value=None)
                phone = st.text_input("Phone Number")
            
            submit_party = st.form_submit_button("➕ Save Party")
            
        if submit_party and name:
            try:
                conn = get_db_connection()
                conn.execute("INSERT INTO parties (name, type, opening_balance, phone) VALUES (?, ?, ?, ?)", (name, p_type, op_bal or 0.0, phone))
                conn.commit()
                conn.close()
                st.success(f"Party '{name}' added!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding party: {e}")

    with tab_del:
        all_parties = fetch_parties()
        if not all_parties.empty:
            party_to_del = st.selectbox("Select Party to Remove", all_parties['name'].tolist())
            if st.button("❌ Confirm Delete Party"):
                conn = get_db_connection()
                conn.execute("DELETE FROM parties WHERE name = ?", (party_to_del,))
                conn.commit()
                conn.close()
                st.success(f"Party '{party_to_del}' removed!")
                st.rerun()

    st.markdown("### 📋 Active Master List")
    st.dataframe(fetch_parties(), use_container_width=True)

# ==========================================
# MODULE 9: BACKUP & RECOVERY
# ==========================================
elif module == "💾 Backup & System Recovery":
    st.markdown("<div class='section-header'>Database Backup & System Recovery</div>", unsafe_allow_html=True)
    
    conn = get_db_connection()
    parties_data = pd.read_sql_query("SELECT * FROM parties", conn).to_dict(orient="records")
    stock_data = pd.read_sql_query("SELECT * FROM stock_register", conn).to_dict(orient="records")
    ledger_data = pd.read_sql_query("SELECT * FROM ledger", conn).to_dict(orient="records")
    conn.close()
    
    backup_dict = {
        "parties": parties_data,
        "stock_register": stock_data,
        "ledger": ledger_data
    }
    
    json_backup = json.dumps(backup_dict, indent=4)
    
    st.download_button(
        label="💾 Download Full JSON Backup File",
        data=json_backup,
        file_name=f"FD_CNG_Backup_{date.today()}.json",
        mime="application/json"
    )
    
    st.markdown("---")
    st.markdown("### 📤 Restore System Data")
    uploaded_file = st.file_uploader("Upload JSON Backup File to Restore", type=["json"])
    
    if uploaded_file is not None:
        if st.button("⚠️ Confirm System Restore"):
            data = json.load(uploaded_file)
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM parties")
            cursor.execute("DELETE FROM stock_register")
            cursor.execute("DELETE FROM ledger")
            
            for p in data.get("parties", []):
                cursor.execute("INSERT INTO parties (id, name, type, opening_balance, phone) VALUES (?, ?, ?, ?, ?)", (p['id'], p['name'], p['type'], p['opening_balance'], p['phone']))
            for s in data.get("stock_register", []):
                cursor.execute("INSERT INTO stock_register VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", tuple(s.values()))
            for l in data.get("ledger", []):
                cursor.execute("INSERT INTO ledger (id, txn_date, party_name, party_type, item_type, qty_ltrs, rate, debit, credit, description) VALUES (?,?,?,?,?,?,?,?,?,?)", (l['id'], l['txn_date'], l['party_name'], l['party_type'], l['item_type'], l['qty_ltrs'], l['rate'], l['debit'], l['credit'], l['description']))
                
            conn.commit()
            conn.close()
            st.success("System restored successfully!")
