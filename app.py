import streamlit as st
import pandas as pd
import sqlite3
import datetime
from datetime import date
import json

# ==========================================
# 1. PAGE CONFIGURATION & SOFT LIGHT THEME
# ==========================================
st.set_page_config(
    page_title="FD CNG Fuel Station",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Soft Color Scheme & Styling
st.markdown("""
<style>
    /* Main App Background */
    .stApp {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Soft Light Navigation Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #E2E8F0 !important;
        border-right: 1px solid #CBD5E1;
    }
    
    /* Sidebar Text & Labels */
    section[data-testid="stSidebar"] *, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] p {
        color: #1E293B !important;
        font-weight: 600 !important;
    }
    
    /* Headers & High Contrast Titles */
    h1, h2, h3, h4, h5, h6 {
        color: #0F172A !important;
        font-weight: 700 !important;
    }
    
    /* Stat Cards Styling */
    .stat-card {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-left: 5px solid #0284C7 !important;
        border-radius: 8px !important;
        padding: 16px !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
        margin-bottom: 10px !important;
    }
    .stat-title {
        color: #64748B !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
    }
    .stat-value {
        color: #0F172A !important;
        font-size: 1.6rem !important;
        font-weight: 800 !important;
    }
    
    /* Section Headers */
    .section-header {
        border-left: 5px solid #0284C7 !important;
        padding-left: 10px !important;
        margin-bottom: 18px !important;
        font-weight: 800 !important;
        color: #0F172A !important;
        font-size: 1.4rem !important;
    }
    
    /* Action Buttons */
    .stButton>button {
        background-color: #0284C7 !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
        border: none !important;
        font-weight: 700 !important;
    }
    .stButton>button:hover {
        background-color: #0369A1 !important;
    }
    
    /* Table & DataFrame Custom Styling */
    div[data-testid="stDataFrame"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 6px !important;
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
        <div style='background-color:#FFFFFF; padding:28px; border-radius:10px; border:1px solid #CBD5E1; text-align:center;'>
            <h2 style='color:#0F172A;'>⛽ FD CNG Fuel Station</h2>
            <p style='color:#64748B;'>Please sign in to access management dashboard.</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("🔑 Login", use_container_width=True)
            
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
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        type TEXT CHECK(type IN ('Customer', 'Vendor')) NOT NULL,
        opening_balance REAL DEFAULT 0.0,
        phone TEXT
    )
    """)
    
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
    
    # Check existing parties and seed missing ones from Excel sheet
    existing = pd.read_sql_query("SELECT name FROM parties", conn)['name'].tolist()
    
    default_customers = [
        'Baba Farid Sugar Mill', 'Jalal Din', 'Fojdari', 'Nemat Mill', 
        'Feed Mill', 'Fatima Mill', 'Ravi Rice', 'R.J 39D', 'Malika Rice', 
        'Cadet College', '26/d Form', 'Ravi Trader(Atiq Sb)', 'AK Trader', 
        'Siddique Zarai Form', 'Zia ur Rehman', 'Arshad Protein', '27 Murabba', 
        'Aleem Khan', 'Umer Sb', 'M Transport', 'Sheraz+Shafqat', 
        'Nadeem Cashier (Cash Sale)'
    ]
    
    default_vendors = [
        'Zoom Petroleum', 'Mohaib(Sharoz)', 'Pervaiz Petroleum', 
        'Crown Pso', 'Ittifaq Petroleum'
    ]
    
    for cust in default_customers:
        if cust not in existing:
            cursor.execute("INSERT INTO parties (name, type, opening_balance, phone) VALUES (?, 'Customer', 0.0, '')", (cust,))
            
    for vend in default_vendors:
        if vend not in existing:
            cursor.execute("INSERT INTO parties (name, type, opening_balance, phone) VALUES (?, 'Vendor', 0.0, '')", (vend,))
            
    conn.commit()
    conn.close()

init_db()

def fetch_parties(p_type=None):
    conn = get_db_connection()
    if p_type:
        df = pd.read_sql_query("SELECT id, name AS [Party Name], type AS [Type], opening_balance AS [Opening Balance], phone AS [Phone] FROM parties WHERE type = ? ORDER BY name ASC", conn, params=(p_type,))
    else:
        df = pd.read_sql_query("SELECT id, name AS [Party Name], type AS [Type], opening_balance AS [Opening Balance], phone AS [Phone] FROM parties ORDER BY type ASC, name ASC", conn)
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
            'Opening Balance': op_bal,
            'Total Debit': tot_debit,
            'Total Credit': tot_credit,
            'Net Balance': net_balance
        })
    df_res = pd.DataFrame(result)
    if not df_res.empty:
        df_res.index = range(1, len(df_res) + 1)
        df_res.index.name = "Sr. No."
    return df_res

# ==========================================
# 4. SIDEBAR NAVIGATION
# ==========================================
st.sidebar.markdown("## ⛽ FD CNG Station")
st.sidebar.markdown("---")

module = st.sidebar.radio(
    "Navigation Menu",
    [
        "📊 Dashboard & Monthly Analytics",
        "📅 Daily Credit Sale & Day Totals",
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
# MODULE 1: DASHBOARD & MULTI-MONTH MATRIX
# ==========================================
if module == "📊 Dashboard & Monthly Analytics":
    st.markdown("<div class='section-header'>Dashboard & Multi-Month Party Sales Matrix</div>", unsafe_allow_html=True)
    
    cust_df = calculate_party_balances('Customer')
    vend_df = calculate_party_balances('Vendor')
    
    tot_receivables = cust_df['Net Balance'].sum() if not cust_df.empty else 0.0
    tot_payables = vend_df['Net Balance'].sum() if not vend_df.empty else 0.0
    
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
    st.markdown("### 📊 Multi-Month Party Sales Summary (Excel Dashboard View)")
    
    conn = get_db_connection()
    query = """
    SELECT party_name AS [Party Name], strftime('%Y-%m', txn_date) AS Month, item_type AS [Fuel Item], SUM(debit) AS [Total Amount]
    FROM ledger
    WHERE party_type = 'Customer' AND item_type IN ('Petrol', 'Diesel')
    GROUP BY party_name, Month, item_type
    """
    matrix_df = pd.read_sql_query(query, conn)
    conn.close()

    if not matrix_df.empty:
        pivoted = matrix_df.pivot_table(
            index="Party Name", 
            columns=["Month", "Fuel Item"], 
            values="Total Amount", 
            aggfunc="sum", 
            fill_value=0
        )
        st.dataframe(pivoted, use_container_width=True)
    else:
        st.info("No party sales transactions recorded yet.")

# ==========================================
# MODULE 2: DAILY CREDIT SALE REPORT WITH DAY TOTALS
# ==========================================
elif module == "📅 Daily Credit Sale & Day Totals":
    st.markdown("<div class='section-header'>Daily Credit Sale Report (Day-Wise Breakdown)</div>", unsafe_allow_html=True)
    
    selected_month = st.text_input("Filter Month (YYYY-MM Format e.g., 2026-08)", value=date.today().strftime('%Y-%m'))
    
    conn = get_db_connection()
    query = f"""
    SELECT txn_date as Date, party_name as [Party Name],
           SUM(CASE WHEN item_type = 'Petrol' THEN debit ELSE 0 END) as Petrol,
           SUM(CASE WHEN item_type = 'Diesel' THEN debit ELSE 0 END) as Diesel,
           SUM(credit) as [Payment Received],
           SUM(debit) as [Credit Total (Petrol+Diesel)]
    FROM ledger
    WHERE party_type = 'Customer' AND strftime('%Y-%m', txn_date) = '{selected_month}'
    GROUP BY txn_date, party_name
    ORDER BY txn_date ASC, id ASC
    """
    daily_df = pd.read_sql_query(query, conn)
    conn.close()
    
    if not daily_df.empty:
        daily_df.index = range(1, len(daily_df) + 1)
        daily_df.index.name = "Sr. No."
        st.dataframe(daily_df, use_container_width=True)
        
        st.markdown("### 📈 Day-Wise Totals Summary")
        day_totals = daily_df.groupby("Date")[["Petrol", "Diesel", "Credit Total (Petrol+Diesel)"]].sum().reset_index()
        day_totals.index = range(1, len(day_totals) + 1)
        day_totals.index.name = "Sr. No."
        st.dataframe(day_totals, use_container_width=True)
    else:
        st.info(f"No daily entries found for month {selected_month}.")

# ==========================================
# MODULE 3: PARTY STATEMENT & DIRECT PRINT
# ==========================================
elif module == "📄 Customer/Vendor Statements & Print":
    st.markdown("<div class='section-header'>Party Statement & Printable Ledger</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        p_type = st.selectbox("Select Party Type", ["Customer", "Vendor"])
    with col2:
        parties_list = fetch_parties(p_type)['Party Name'].tolist()
        selected_party = st.selectbox("Select Party Name", parties_list if parties_list else ["None"])

    if selected_party and selected_party != "None":
        conn = get_db_connection()
        party_info = conn.execute("SELECT opening_balance FROM parties WHERE name = ?", (selected_party,)).fetchone()
        op_bal = party_info['opening_balance'] if party_info else 0.0
        
        stmt_df = pd.read_sql_query(
            "SELECT txn_date as Date, item_type as Fuel, qty_ltrs as Ltrs, rate as Rate, debit as Debit, credit as Credit, description as Description FROM ledger WHERE party_name = ? ORDER BY txn_date ASC, id ASC",
            conn, params=(selected_party,)
        )
        conn.close()
        
        running_bal = op_bal
        balances = []
        for _, row in stmt_df.iterrows():
            if p_type == 'Customer':
                running_bal += (row['Debit'] - row['Credit'])
            else:
                running_bal += (row['Credit'] - row['Debit'])
            balances.append(running_bal)
            
        stmt_df['Running Balance'] = balances
        
        # Start Sr. No. Index from 1
        stmt_df.index = range(1, len(stmt_df) + 1)
        stmt_df.index.name = "Sr. No."
        
        st.info(f"**Party Name:** {selected_party} | **Type:** {p_type} | **Opening Balance:** Rs. {op_bal:,.2f}")
        
        # Print Button Action
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("🖨️ Print Statement"):
                st.components.v1.html("<script>window.print();</script>", height=0, width=0)
        
        st.dataframe(stmt_df, use_container_width=True)

# ==========================================
# MODULE 4: DAILY STOCK REGISTER
# ==========================================
elif module == "🛢️ Daily Stock Register":
    st.markdown("<div class='section-header'>Daily Stock Register</div>", unsafe_allow_html=True)

    with st.form("stock_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            e_date = st.date_input("Entry Date", date.today())
            item_type = st.selectbox("Fuel Item", ["Petrol", "Diesel"])
            op_stock = st.number_input("Opening Stock (Ltrs)", min_value=0.0, value=None)
            op_rate = st.number_input("Opening Rate", min_value=0.0, value=None)
        with c2:
            p_qty = st.number_input("Purchase Qty (Ltrs)", min_value=0.0, value=None)
            p_rate = st.number_input("Purchase Rate", min_value=0.0, value=None)
            s_qty = st.number_input("Sales Qty (Ltrs)", min_value=0.0, value=None)
            s_rate = st.number_input("Sales Rate", min_value=0.0, value=None)
        with c3:
            actual_stock = st.number_input("Actual Dip Stock (Ltrs)", min_value=0.0, value=None)

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
        st.success("Daily stock record updated successfully!")

    st.markdown("### 📊 Existing Stock Records")
    conn = get_db_connection()
    stock_df = pd.read_sql_query("""
    SELECT entry_date AS [Entry Date], item_type AS [Fuel Item], opening_stock AS [Opening Stock], 
           rate AS [Rate], purchase_qty AS [Purchase Qty], purchase_rate AS [Purchase Rate], 
           sales_qty AS [Sales Qty], sales_rate AS [Sales Rate], closing_stock AS [Closing Stock], 
           actual_stock AS [Actual Dip Stock], dip_diff AS [Dip Difference]
    FROM stock_register ORDER BY entry_date DESC, id DESC
    """, conn)
    conn.close()
    
    if not stock_df.empty:
        stock_df.index = range(1, len(stock_df) + 1)
        stock_df.index.name = "Sr. No."
        st.dataframe(stock_df, use_container_width=True)

# ==========================================
# MODULE 5: PARTY DAILY SALE ENTRY
# ==========================================
elif module == "💳 Party Daily Sale & Credit Entry":
    st.markdown("<div class='section-header'>Customer Credit Sale & Voucher Entry</div>", unsafe_allow_html=True)
    
    customers = fetch_parties('Customer')['Party Name'].tolist()
    
    with st.form("credit_sale_form"):
        c1, c2 = st.columns(2)
        with c1:
            txn_date = st.date_input("Transaction Date", date.today())
            party_name = st.selectbox("Customer Name", customers if customers else ["None"])
            fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel", "Cash Payment/Voucher"])
        with c2:
            qty = st.number_input("Qty (Ltrs)", min_value=0.0, value=None)
            rate = st.number_input("Rate", min_value=0.0, value=None)
            payment = st.number_input("Amount Received/Credit (Rs.)", min_value=0.0, value=None)
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
        st.success("Customer transaction saved successfully!")

# ==========================================
# MODULE 6: VENDOR PURCHASING
# ==========================================
elif module == "🚛 Vendor Purchasing & Dip Stock":
    st.markdown("<div class='section-header'>Vendor Purchasing & Payments</div>", unsafe_allow_html=True)
    
    vendors = fetch_parties('Vendor')['Party Name'].tolist()
    
    with st.form("vendor_form"):
        c1, c2 = st.columns(2)
        with c1:
            txn_date = st.date_input("Date", date.today())
            vendor_name = st.selectbox("Vendor Name", vendors if vendors else ["None"])
            fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel", "Direct Payment"])
        with c2:
            qty = st.number_input("Qty Received (Ltrs)", min_value=0.0, value=None)
            rate = st.number_input("Purchase Rate", min_value=0.0, value=None)
            paid_amount = st.number_input("Payment Paid to Vendor (Rs.)", min_value=0.0, value=None)
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
        st.success("Vendor transaction saved successfully!")

# ==========================================
# MODULE 7: EDIT / MANAGE ENTRIES
# ==========================================
elif module == "✏️ Edit / Manage Entries":
    st.markdown("<div class='section-header'>Editable Ledger Entries</div>", unsafe_allow_html=True)
    
    conn = get_db_connection()
    df_ledger = pd.read_sql_query("SELECT id AS [ID], txn_date AS [Date], party_name AS [Party Name], party_type AS [Party Type], item_type AS [Fuel Item], qty_ltrs AS [Ltrs], rate AS [Rate], debit AS [Debit], credit AS [Credit], description AS [Description] FROM ledger ORDER BY txn_date DESC, id DESC", conn)
    conn.close()
    
    edited_df = st.data_editor(df_ledger, num_rows="dynamic", use_container_width=True, key="ledger_editor")
    
    if st.button("💾 Save All Changes"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ledger")
        for _, row in edited_df.iterrows():
            if pd.notna(row['Party Name']) and str(row['Party Name']).strip() != '':
                cursor.execute("""
                INSERT INTO ledger (id, txn_date, party_name, party_type, item_type, qty_ltrs, rate, debit, credit, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (row['ID'], str(row['Date']), row['Party Name'], row['Party Type'], row['Fuel Item'], row['Ltrs'], row['Rate'], row['Debit'], row['Credit'], row['Description']))
        conn.commit()
        conn.close()
        st.success("Ledger records updated successfully!")

# ==========================================
# MODULE 8: RECONCILIATION
# ==========================================
elif module == "⚖️ Stock vs Sale Month-End Match":
    st.markdown("<div class='section-header'>Stock vs Sales Reconciliation</div>", unsafe_allow_html=True)
    
    conn = get_db_connection()
    stock_summary = pd.read_sql_query("""
    SELECT item_type AS [Fuel Item], SUM(purchase_qty) AS [Total Purchased], SUM(sales_qty) AS [Total Stock Sales], SUM(dip_diff) AS [Total Dip Variance]
    FROM stock_register GROUP BY item_type
    """, conn)
    
    ledger_summary = pd.read_sql_query("""
    SELECT item_type AS [Fuel Item], SUM(qty_ltrs) AS [Total Ledger Sales]
    FROM ledger WHERE party_type = 'Customer' AND item_type IS NOT NULL GROUP BY item_type
    """, conn)
    conn.close()
    
    reconcil = pd.merge(stock_summary, ledger_summary, on='Fuel Item', how='outer').fillna(0)
    reconcil['Sales Variance'] = reconcil['Total Stock Sales'] - reconcil['Total Ledger Sales']
    
    if not reconcil.empty:
        reconcil.index = range(1, len(reconcil) + 1)
        reconcil.index.name = "Sr. No."
        st.dataframe(reconcil, use_container_width=True)

# ==========================================
# MODULE 9: MASTER SETUP (ADD / REMOVE PARTIES)
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
                st.success(f"Party '{name}' added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding party: {e}")

    with tab_del:
        all_parties = fetch_parties()
        if not all_parties.empty:
            party_to_del = st.selectbox("Select Party to Remove", all_parties['Party Name'].tolist())
            if st.button("❌ Confirm Delete Party"):
                conn = get_db_connection()
                conn.execute("DELETE FROM parties WHERE name = ?", (party_to_del,))
                conn.commit()
                conn.close()
                st.success(f"Party '{party_to_del}' removed successfully!")
                st.rerun()

    st.markdown("### 📋 Active Master List")
    active_parties = fetch_parties()
    if not active_parties.empty:
        active_parties.index = range(1, len(active_parties) + 1)
        active_parties.index.name = "Sr. No."
        st.dataframe(active_parties, use_container_width=True)

# ==========================================
# MODULE 10: BACKUP & RECOVERY
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
        label="💾 Download JSON Backup File",
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
