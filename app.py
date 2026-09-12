"""
FD CNG Fuel Station - Management App (Fixed & Improved)
=======================================================
Fixes in this version:
1. No auto-save / no double-save  -> every save goes through a one-time token guard.
2. Review (preview) screen before saving customer & vendor entries.
3. Correct Dip Difference maths (keeps the minus/plus sign and applies it properly).
4. Full Edit / Delete module (choose Customer or Vendor, then the exact entry).
5. Sr. No. is always a clean 1,2,3... sequence; real DB IDs can be re-sequenced too.
6. Extra helpers: search filters, CSV export, delete stock entry, duplicate warning.

Run:  streamlit run app.py
"""

import json
import hashlib
from datetime import date, datetime
import sqlite3

import pandas as pd
import streamlit as st

# ==========================================
# 1. PAGE CONFIG & THEME
# ==========================================
st.set_page_config(
    page_title="FD CNG Fuel Station",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        /* ===== FD CNG Fuel Station Theme ===== */
        .main { background-color: #f4f7f5; }

        /* Title banner - fuel pump green/orange gradient */
        .app-title {
            font-size: 26px; font-weight: 800; color: #ffffff;
            padding: 16px 22px; margin-bottom: 20px;
            background: linear-gradient(90deg, #0b5d34 0%, #1c8b4e 55%, #2e7d32 100%);
            border-left: 8px solid #f57c00;
            border-radius: 10px;
            box-shadow: 0 3px 10px rgba(11,93,52,.25);
            letter-spacing: .3px;
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b3d24 0%, #14532d 100%);
        }
        section[data-testid="stSidebar"] * { color: #f0fdf4 !important; }
        section[data-testid="stSidebar"] .stRadio > label { color: #f0fdf4 !important; }
        section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.2); }

        /* Metric cards */
        .metric-card {
            background: #ffffff; border: 1px solid #e3e8ef; border-top: 4px solid #f57c00;
            border-radius: 12px; padding: 16px; text-align: center;
            box-shadow: 0 2px 6px rgba(0,0,0,.06);
        }
        .metric-card h4 { margin: 0; font-size: 13px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: .4px; }
        .metric-card p  { margin: 8px 0 0; font-size: 21px; font-weight: 800; color: #0b3d24; }

        /* Review / preview box */
        .review-box {
            background:#fff7e6; border:1px solid #f57c00; border-left: 6px solid #f57c00;
            border-radius:10px; padding:14px; margin-bottom: 10px;
        }

        /* Buttons */
        div.stButton > button, div.stFormSubmitButton > button, div.stDownloadButton > button {
            background: linear-gradient(90deg, #1c8b4e, #2e7d32);
            color: #ffffff; border: none; border-radius: 8px; font-weight: 700;
            box-shadow: 0 2px 4px rgba(0,0,0,.15);
        }
        div.stButton > button:hover, div.stFormSubmitButton > button:hover, div.stDownloadButton > button:hover {
            background: linear-gradient(90deg, #f57c00, #ef6c00); color:#fff;
        }

        /* Tabs */
        button[data-baseweb="tab"] { font-weight: 700; }

        /* Dataframe header tint */
        [data-testid="stDataFrame"] { border: 1px solid #e3e8ef; border-radius: 8px; overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


def title(text: str):
    st.markdown(f"<div class='app-title'>{text}</div>", unsafe_allow_html=True)


# ==========================================
# 2. LOGIN
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

USERNAME = "Fdcngpump"
PASSWORD = "Fazal661112@"


def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        title("⛽ FD CNG Fuel Station — Sign In")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("🔑 Login", use_container_width=True):
                if username == USERNAME and password == PASSWORD:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Invalid Username or Password!")


if not st.session_state["authenticated"]:
    login_screen()
    st.stop()

# ==========================================
# 3. DATABASE
# ==========================================
DB_FILE = "fd_cng_fuel_station.db"


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT CHECK(type IN ('Customer','Vendor')) NOT NULL,
            opening_balance REAL DEFAULT 0.0,
            phone TEXT
        )"""
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_register (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            item_type TEXT CHECK(item_type IN ('Petrol','Diesel')) NOT NULL,
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
        )"""
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            txn_date TEXT NOT NULL,
            party_name TEXT NOT NULL,
            party_type TEXT CHECK(party_type IN ('Customer','Vendor')) NOT NULL,
            item_type TEXT,
            qty_ltrs REAL DEFAULT 0.0,
            rate REAL DEFAULT 0.0,
            debit REAL DEFAULT 0.0,
            credit REAL DEFAULT 0.0,
            description TEXT,
            voucher_no TEXT
        )"""
    )

    # --- Migration: add voucher_no column if an older DB file already exists without it ---
    existing_cols = [r[1] for r in cur.execute("PRAGMA table_info(ledger)").fetchall()]
    if "voucher_no" not in existing_cols:
        cur.execute("ALTER TABLE ledger ADD COLUMN voucher_no TEXT")

    existing = pd.read_sql_query("SELECT name FROM parties", conn)["name"].tolist()

    default_customers = [
        "Baba Farid Sugar Mill", "Jalal Din", "Fojdari", "Nemat Mill",
        "Feed Mill", "Fatima Mill", "Ravi Rice", "R.J 39D", "Malika Rice",
        "Cadet College", "26/d Form", "Ravi Trader(Atiq Sb)", "AK Trader",
        "Siddique Zarai Form", "Zia ur Rehman", "Arshad Protein", "27 Murabba",
        "Aleem Khan", "Umer Sb", "M Transport", "Sheraz+Shafqat",
        "Nadeem Cashier (Cash Sale)",
    ]
    default_vendors = [
        "Zoom Petroleum", "Mohaib(Sharoz)", "Pervaiz Petroleum",
        "Crown Pso", "Ittifaq Petroleum",
    ]

    for c in default_customers:
        if c not in existing:
            cur.execute(
                "INSERT INTO parties (name, type, opening_balance, phone) VALUES (?, 'Customer', 0.0, '')",
                (c,),
            )
    for v in default_vendors:
        if v not in existing:
            cur.execute(
                "INSERT INTO parties (name, type, opening_balance, phone) VALUES (?, 'Vendor', 0.0, '')",
                (v,),
            )

    conn.commit()
    conn.close()


init_db()


# ==========================================
# 4. HELPERS
# ==========================================
def sr_index(df: pd.DataFrame) -> pd.DataFrame:
    """Always show a clean 1,2,3... Sr. No."""
    if df is None or df.empty:
        return df
    df = df.reset_index(drop=True)
    df.index = range(1, len(df) + 1)
    df.index.name = "Sr. No."
    return df


def payload_token(*parts) -> str:
    """Unique fingerprint of a save payload -> blocks duplicate / repeat saves."""
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()


def already_saved(token: str) -> bool:
    """True if this exact payload was saved in this session already."""
    saved = st.session_state.setdefault("saved_tokens", set())
    if token in saved:
        return True
    saved.add(token)
    return False


def fetch_parties(p_type=None) -> pd.DataFrame:
    conn = get_db_connection()
    base = ("SELECT id, name AS [Party Name], type AS [Type], "
            "opening_balance AS [Opening Balance], phone AS [Phone] FROM parties ")
    if p_type:
        df = pd.read_sql_query(base + "WHERE type = ? ORDER BY name ASC", conn, params=(p_type,))
    else:
        df = pd.read_sql_query(base + "ORDER BY type ASC, name ASC", conn)
    conn.close()
    return df


def calculate_party_balances(party_type: str) -> pd.DataFrame:
    conn = get_db_connection()
    parties = pd.read_sql_query(
        "SELECT name, opening_balance FROM parties WHERE type = ?", conn, params=(party_type,)
    )
    ledger = pd.read_sql_query(
        "SELECT party_name, debit, credit FROM ledger WHERE party_type = ?", conn, params=(party_type,)
    )
    conn.close()

    rows = []
    for _, p in parties.iterrows():
        pl = ledger[ledger["party_name"] == p["name"]]
        d, c = pl["debit"].sum(), pl["credit"].sum()
        net = p["opening_balance"] + (d - c) if party_type == "Customer" else p["opening_balance"] + (c - d)
        rows.append({
            "Party Name": p["name"], "Opening Balance": p["opening_balance"],
            "Total Debit": d, "Total Credit": c, "Net Balance": net,
        })
    return sr_index(pd.DataFrame(rows))


def resequence_ids(table: str):
    """Re-number the id column as 1,2,3... ordered by date then old id."""
    date_col = "txn_date" if table == "ledger" else "entry_date"
    conn = get_db_connection()
    cur = conn.cursor()
    ids = [r[0] for r in cur.execute(f"SELECT id FROM {table} ORDER BY {date_col} ASC, id ASC")]
    # move out of the way first to avoid PK clashes
    for old in ids:
        cur.execute(f"UPDATE {table} SET id = ? WHERE id = ?", (old + 1_000_000, old))
    for new, old in enumerate(ids, start=1):
        cur.execute(f"UPDATE {table} SET id = ? WHERE id = ?", (new, old + 1_000_000))
    cur.execute(f"UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (len(ids), table))
    conn.commit()
    conn.close()


def download_csv(df: pd.DataFrame, filename: str, label="⬇️ Download CSV"):
    if df is not None and not df.empty:
        st.download_button(label, df.to_csv(index=True).encode("utf-8"),
                           file_name=filename, mime="text/csv")


def last_closing_stock(item_type: str) -> float:
    """Fetch the FINAL closing stock (book closing stock adjusted by that day's
    dip difference) from the most recent saved stock-register entry for this
    fuel item. This is the correct value to carry forward as tomorrow's
    Opening Stock — NOT the raw dip reading and NOT the book closing alone."""
    conn = get_db_connection()
    row = conn.execute(
        """SELECT closing_stock, dip_diff FROM stock_register
           WHERE item_type = ? ORDER BY entry_date DESC, id DESC LIMIT 1""",
        (item_type,)).fetchone()
    conn.close()
    if row is None:
        return 0.0
    return (row["closing_stock"] or 0.0) + (row["dip_diff"] or 0.0)


def next_voucher_no() -> str:
    """Suggest the next voucher number as V-00001, V-00002 ... based on the highest
    numeric part already used (so it stays correct even after deletes)."""
    conn = get_db_connection()
    rows = conn.execute("SELECT voucher_no FROM ledger WHERE voucher_no IS NOT NULL").fetchall()
    conn.close()
    max_n = 0
    for r in rows:
        digits = "".join(ch for ch in (r["voucher_no"] or "") if ch.isdigit())
        if digits:
            max_n = max(max_n, int(digits))
    return f"V-{max_n + 1:05d}"


def render_print_statement(party: str, p_type: str, op_bal: float, closing_bal: float,
                            stmt: pd.DataFrame, from_date, to_date):
    """Builds a print-friendly HTML statement with a button that opens the browser's
    native print dialog directly (Ctrl/Cmd+P equivalent) - no PDF / file save step."""
    import streamlit.components.v1 as components

    rows_html = ""
    for i, (_, r) in enumerate(stmt.iterrows(), start=1):
        rows_html += f"""
        <tr>
            <td>{i}</td>
            <td>{r['Voucher No'] if pd.notna(r.get('Voucher No')) else ''}</td>
            <td>{r['Date']}</td>
            <td>{r['Fuel'] if pd.notna(r['Fuel']) else '-'}</td>
            <td class="num">{r['Ltrs']:,.2f}</td>
            <td class="num">{r['Rate']:,.2f}</td>
            <td class="num">{r['Debit']:,.2f}</td>
            <td class="num">{r['Credit']:,.2f}</td>
            <td>{r['Description'] or ''}</td>
            <td class="num">{r['Running Balance']:,.2f}</td>
        </tr>"""

    html = f"""
    <html>
    <head>
    <style>
        body {{ font-family: Arial, Helvetica, sans-serif; color:#0b3d24; margin:0; padding:0; }}
        .sheet {{ padding: 18px 22px; }}
        .head {{
            background: linear-gradient(90deg,#0b5d34,#2e7d32);
            color:#fff; padding:14px 18px; border-radius:8px; border-left:8px solid #f57c00;
            margin-bottom:14px;
        }}
        .head h2 {{ margin:0; font-size:20px; }}
        .head p {{ margin:2px 0 0; font-size:13px; opacity:.9; }}
        .info {{ display:flex; justify-content:space-between; margin-bottom:12px; font-size:14px; }}
        .info div {{ background:#f4f7f5; border:1px solid #e3e8ef; border-radius:6px; padding:8px 12px; }}
        table {{ width:100%; border-collapse: collapse; font-size:12.5px; }}
        th {{ background:#0b3d24; color:#fff; padding:6px 8px; text-align:left; }}
        td {{ padding:6px 8px; border-bottom:1px solid #e3e8ef; }}
        td.num, th.num {{ text-align:right; }}
        tr:nth-child(even) {{ background:#f8faf9; }}
        .totals {{ margin-top:12px; text-align:right; font-size:14px; font-weight:bold; }}
        .print-btn {{
            background:linear-gradient(90deg,#1c8b4e,#2e7d32); color:#fff; border:none;
            padding:10px 22px; border-radius:8px; font-weight:bold; font-size:14px;
            cursor:pointer; margin-bottom:14px;
        }}
        @media print {{ .print-btn {{ display:none; }} }}
    </style>
    </head>
    <body>
        <div class="sheet">
            <button class="print-btn" onclick="window.print()">🖨️ Print Statement Now</button>
            <div class="head">
                <h2>⛽ FD CNG Fuel Station</h2>
                <p>{p_type} Statement &nbsp;|&nbsp; {from_date} to {to_date}</p>
            </div>
            <div class="info">
                <div><b>Party:</b> {party}</div>
                <div><b>Opening Balance:</b> Rs. {op_bal:,.2f}</div>
                <div><b>Closing Balance:</b> Rs. {closing_bal:,.2f}</div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Sr.</th><th>Voucher No</th><th>Date</th><th>Fuel</th>
                        <th class="num">Ltrs</th><th class="num">Rate</th>
                        <th class="num">Debit</th><th class="num">Credit</th>
                        <th>Description</th><th class="num">Running Balance</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html if rows_html else '<tr><td colspan="10" style="text-align:center;">No entries in this range</td></tr>'}
                </tbody>
            </table>
            <div class="totals">Closing Balance: Rs. {closing_bal:,.2f}</div>
        </div>
    </body>
    </html>
    """
    components.html(html, height=650, scrolling=True)


# ==========================================
# 5. SIDEBAR
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
        "💾 Backup & System Recovery",
    ],
)

if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

# ==========================================
# MODULE 1: DASHBOARD
# ==========================================
if module == "📊 Dashboard & Monthly Analytics":
    title("Dashboard & Multi-Month Party Sales Matrix")

    cust_df = calculate_party_balances("Customer")
    vend_df = calculate_party_balances("Vendor")
    receivables = cust_df["Net Balance"].sum() if not cust_df.empty else 0.0
    payables = vend_df["Net Balance"].sum() if not vend_df.empty else 0.0

    conn = get_db_connection()
    fuel = pd.read_sql_query(
        "SELECT item_type, SUM(qty_ltrs) total FROM ledger "
        "WHERE party_type='Customer' AND item_type IS NOT NULL GROUP BY item_type", conn)
    conn.close()

    petrol = fuel.loc[fuel["item_type"] == "Petrol", "total"].sum() if not fuel.empty else 0.0
    diesel = fuel.loc[fuel["item_type"] == "Diesel", "total"].sum() if not fuel.empty else 0.0

    cards = [
        ("Total Receivables", f"Rs. {receivables:,.2f}"),
        ("Total Payables", f"Rs. {payables:,.2f}"),
        ("Total Petrol Sold", f"{petrol:,.2f} Ltrs"),
        ("Total Diesel Sold", f"{diesel:,.2f} Ltrs"),
    ]
    for col, (h, v) in zip(st.columns(4), cards):
        col.markdown(f"<div class='metric-card'><h4>{h}</h4><p>{v}</p></div>", unsafe_allow_html=True)

    st.markdown("### 📊 Multi-Month Party Sales Summary")
    conn = get_db_connection()
    matrix = pd.read_sql_query(
        """SELECT party_name AS [Party Name], strftime('%Y-%m', txn_date) AS Month,
                  item_type AS [Fuel Item], SUM(debit) AS [Total Amount]
           FROM ledger
           WHERE party_type='Customer' AND item_type IN ('Petrol','Diesel')
           GROUP BY party_name, Month, item_type""", conn)
    conn.close()

    if not matrix.empty:
        pivot = matrix.pivot_table(index="Party Name", columns=["Month", "Fuel Item"],
                                   values="Total Amount", aggfunc="sum", fill_value=0)
        st.dataframe(pivot, use_container_width=True)
    else:
        st.info("No party sales transactions recorded yet.")

    st.markdown("### 💰 Party Balances")
    t1, t2 = st.tabs(["Customers", "Vendors"])
    with t1:
        st.dataframe(cust_df, use_container_width=True)
        download_csv(cust_df, "customer_balances.csv")
    with t2:
        st.dataframe(vend_df, use_container_width=True)
        download_csv(vend_df, "vendor_balances.csv")

# ==========================================
# MODULE 2: DAILY CREDIT SALE
# ==========================================
elif module == "📅 Daily Credit Sale & Day Totals":
    title("Daily Credit Sale Report (Day-Wise Breakdown)")

    month = st.text_input("Filter Month (YYYY-MM)", value=date.today().strftime("%Y-%m"))

    conn = get_db_connection()
    daily = pd.read_sql_query(
        """SELECT txn_date AS Date, party_name AS [Party Name],
                  SUM(CASE WHEN item_type='Petrol' THEN debit ELSE 0 END) AS Petrol,
                  SUM(CASE WHEN item_type='Diesel' THEN debit ELSE 0 END) AS Diesel,
                  SUM(credit) AS [Payment Received],
                  SUM(debit)  AS [Credit Total]
           FROM ledger
           WHERE party_type='Customer' AND strftime('%Y-%m', txn_date) = ?
           GROUP BY txn_date, party_name
           ORDER BY txn_date ASC, party_name ASC""", conn, params=(month,))
    conn.close()

    if not daily.empty:
        st.dataframe(sr_index(daily), use_container_width=True)
        download_csv(sr_index(daily), f"daily_credit_{month}.csv")

        st.markdown("### 📈 Day-Wise Totals")
        totals = daily.groupby("Date")[["Petrol", "Diesel", "Credit Total", "Payment Received"]].sum().reset_index()
        st.dataframe(sr_index(totals), use_container_width=True)

        st.markdown("### 🧾 Month Grand Total")
        g1, g2, g3 = st.columns(3)
        g1.metric("Petrol (Rs.)", f"{daily['Petrol'].sum():,.2f}")
        g2.metric("Diesel (Rs.)", f"{daily['Diesel'].sum():,.2f}")
        g3.metric("Payments (Rs.)", f"{daily['Payment Received'].sum():,.2f}")
    else:
        st.info(f"No daily entries found for month {month}.")

# ==========================================
# MODULE 3: STATEMENTS
# ==========================================
elif module == "📄 Customer/Vendor Statements & Print":
    title("Party Statement & Printable Ledger")

    c1, c2 = st.columns(2)
    p_type = c1.selectbox("Party Type", ["Customer", "Vendor"])
    plist = fetch_parties(p_type)["Party Name"].tolist()
    party = c2.selectbox("Party Name", plist if plist else ["None"])

    d1, d2 = st.columns(2)
    from_date = d1.date_input("From Date", date(date.today().year, 1, 1))
    to_date = d2.date_input("To Date", date.today())

    if party != "None":
        conn = get_db_connection()
        row = conn.execute("SELECT opening_balance FROM parties WHERE name = ?", (party,)).fetchone()
        op_bal = row["opening_balance"] if row else 0.0
        stmt = pd.read_sql_query(
            """SELECT id AS [Entry ID], voucher_no AS [Voucher No], txn_date AS Date, item_type AS Fuel,
                      qty_ltrs AS Ltrs, rate AS Rate, debit AS Debit, credit AS Credit, description AS Description
               FROM ledger WHERE party_name = ? AND txn_date BETWEEN ? AND ?
               ORDER BY txn_date ASC, id ASC""",
            conn, params=(party, str(from_date), str(to_date)))
        conn.close()

        bal, rows = op_bal, []
        for _, r in stmt.iterrows():
            bal += (r["Debit"] - r["Credit"]) if p_type == "Customer" else (r["Credit"] - r["Debit"])
            rows.append(bal)
        stmt["Running Balance"] = rows
        closing_bal = rows[-1] if rows else op_bal

        st.info(f"**{party}** | Type: {p_type} | Opening Balance: Rs. {op_bal:,.2f} | "
                f"Closing Balance: Rs. {closing_bal:,.2f}")
        stmt_view = sr_index(stmt)
        st.dataframe(stmt_view, use_container_width=True)
        download_csv(stmt_view, f"{party}_statement.csv", "⬇️ Download CSV")

        st.markdown("### 🖨️ Print Statement")
        st.caption("Click the green button below and use the browser's print dialog to send this "
                   "statement straight to your printer — no need to save a file first.")
        render_print_statement(party, p_type, op_bal, closing_bal, stmt, from_date, to_date)

# ==========================================
# MODULE 4: DAILY STOCK REGISTER  (dip difference fixed)
# ==========================================
elif module == "🛢️ Daily Stock Register":
    title("Daily Stock Register")

    st.caption("Dip Difference = the shortage/excess amount YOU enter directly during the physical "
               "dip check (not the full tank reading). Minus means shortage (stock kam), plus means "
               "excess (stock zyada). The **Final Closing Stock** (book closing adjusted by that "
               "difference) is what carries forward as tomorrow's Opening Stock — auto-filled below.")

    item_type = st.selectbox("Fuel Item (select first — Opening Stock auto-fills from this)",
                             ["Petrol", "Diesel"], key="stock_item_type_pick")
    suggested_opening = last_closing_stock(item_type)
    st.caption(f"↪️ Auto-filled Opening Stock for **{item_type}** = last saved Final Closing Stock "
               f"({suggested_opening:,.2f} Ltrs). You can still edit it below if needed.")

    with st.form("stock_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            e_date = st.date_input("Entry Date", date.today())
            st.text_input("Fuel Item", value=item_type, disabled=True)
            op_stock = st.number_input("Opening Stock (Ltrs)", value=float(suggested_opening), step=1.0)
            op_rate = st.number_input("Opening Rate", min_value=0.0, value=0.0, step=0.1)
        with c2:
            p_qty = st.number_input("Purchase Qty (Ltrs)", min_value=0.0, value=0.0, step=1.0)
            p_rate = st.number_input("Purchase Rate", min_value=0.0, value=0.0, step=0.1)
            s_qty = st.number_input("Sales Qty (Ltrs)", min_value=0.0, value=0.0, step=1.0)
            s_rate = st.number_input("Sales Rate", min_value=0.0, value=0.0, step=0.1)
        with c3:
            dip_checked = st.checkbox("Physical Dip Check done today?", value=True)
            dip_input = st.number_input(
                "Dip Shortage / Excess (+/− Ltrs)", value=0.0, step=1.0,
                help="Enter ONLY the difference found in the physical dip check — e.g. type -93 "
                     "if 93 litres are SHORT, or 50 if 50 litres are EXCESS. Do NOT type the full "
                     "tank reading here; the app adds/subtracts this from the Book Closing Stock.")

        review_stock = st.form_submit_button("👁️ Review Entry")

    def stock_calc(op_stock, op_rate, p_qty, p_rate, s_qty, s_rate, dip_input, dip_checked):
        op_amount = op_stock * op_rate
        p_amount = p_qty * p_rate
        tot_p_amount = op_amount + p_amount
        avail = op_stock + p_qty
        avg_rate = (tot_p_amount / avail) if avail > 0 else 0.0
        s_amount = s_qty * s_rate
        tot_s_amount = s_qty * avg_rate
        closing_amount = tot_p_amount - tot_s_amount
        closing_stock = avail - s_qty                    # book closing stock (before dip adjustment)
        dip_diff = dip_input if dip_checked else 0.0      # signed: minus = shortage, plus = excess
        dip_amount = dip_diff * avg_rate                  # same sign as dip_diff
        actual_stock = closing_stock + dip_diff           # real litres in tank after adjustment
        act_amount = actual_stock * avg_rate
        final_closing = closing_stock + dip_diff          # <-- carried forward as next day's Opening Stock
        return dict(op_amount=op_amount, p_amount=p_amount, tot_p_amount=tot_p_amount,
                    avail=avail, avg_rate=avg_rate, s_amount=s_amount, tot_s_amount=tot_s_amount,
                    closing_amount=closing_amount, closing_stock=closing_stock,
                    dip_diff=dip_diff, dip_amount=dip_amount, act_amount=act_amount,
                    actual_stock=actual_stock, final_closing=final_closing)

    if review_stock:
        st.session_state["stock_pending"] = dict(
            e_date=str(e_date), item_type=item_type, op_stock=op_stock, op_rate=op_rate,
            p_qty=p_qty, p_rate=p_rate, s_qty=s_qty, s_rate=s_rate,
            dip_input=dip_input, dip_checked=dip_checked,
        )

    pend = st.session_state.get("stock_pending")
    if pend:
        k = stock_calc(pend["op_stock"], pend["op_rate"], pend["p_qty"], pend["p_rate"],
                       pend["s_qty"], pend["s_rate"], pend["dip_input"], pend["dip_checked"])
        st.markdown("<div class='review-box'><b>🔎 Review before saving</b></div>", unsafe_allow_html=True)
        r1, r2, r3 = st.columns(3)
        r1.write(f"**Date:** {pend['e_date']}")
        r1.write(f"**Fuel:** {pend['item_type']}")
        r1.write(f"**Available Stock:** {k['avail']:,.2f} Ltrs")
        r2.write(f"**Average Rate:** Rs. {k['avg_rate']:,.4f}")
        r2.write(f"**Book Closing Stock:** {k['closing_stock']:,.2f} Ltrs")
        r2.write(f"**Actual Dip Stock (after adjustment):** {k['actual_stock']:,.2f} Ltrs"
                 + ("" if pend["dip_checked"] else " (no dip taken)"))
        sign = "SHORTAGE (−)" if k["dip_diff"] < 0 else ("EXCESS (+)" if k["dip_diff"] > 0 else "NO DIFFERENCE")
        r3.write(f"**Dip Difference:** {k['dip_diff']:+,.2f} Ltrs  → {sign}")
        r3.write(f"**Dip Diff Amount:** Rs. {k['dip_amount']:+,.2f}")
        r3.write(f"**Closing Amount:** Rs. {k['closing_amount']:,.2f}")
        st.success(f"**✅ Final Closing Stock (→ tomorrow's Opening Stock for {pend['item_type']}): "
                   f"{k['final_closing']:,.2f} Ltrs**")

        conn = get_db_connection()
        dup = conn.execute("SELECT COUNT(*) c FROM stock_register WHERE entry_date=? AND item_type=?",
                           (pend["e_date"], pend["item_type"])).fetchone()["c"]
        conn.close()
        if dup:
            st.warning(f"⚠️ {dup} entry already exists for {pend['e_date']} / {pend['item_type']}.")

        b1, b2 = st.columns(2)
        confirm = b1.button("✅ Confirm & Save Stock Entry", use_container_width=True)
        cancel = b2.button("❌ Cancel", use_container_width=True)

        if cancel:
            st.session_state.pop("stock_pending", None)
            st.rerun()

        if confirm:
            token = payload_token("stock", *pend.values())
            if already_saved(token):
                st.warning("This entry was already saved. Duplicate save blocked.")
            else:
                conn = get_db_connection()
                conn.execute(
                    """INSERT INTO stock_register (
                        entry_date,item_type,opening_stock,rate,opening_amount,purchase_qty,purchase_rate,
                        purchase_amount,total_purchase_amount,avg_rate,available_stock,sales_qty,sales_rate,
                        sales_amount,total_sales_amount,closing_amount,closing_stock,dip_diff,actual_stock,actual_amount)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (pend["e_date"], pend["item_type"], pend["op_stock"], pend["op_rate"], k["op_amount"],
                     pend["p_qty"], pend["p_rate"], k["p_amount"], k["tot_p_amount"], k["avg_rate"],
                     k["avail"], pend["s_qty"], pend["s_rate"], k["s_amount"], k["tot_s_amount"],
                     k["closing_amount"], k["closing_stock"], k["dip_diff"], k["actual_stock"], k["act_amount"]),
                )
                conn.commit()
                conn.close()
                st.session_state.pop("stock_pending", None)
                st.success("✅ Daily stock entry saved.")
                st.rerun()

    st.markdown("### 📊 Existing Stock Records")
    conn = get_db_connection()
    stock_df = pd.read_sql_query(
        """SELECT id AS [Entry ID], entry_date AS [Entry Date], item_type AS [Fuel Item],
                  opening_stock AS [Opening Stock], rate AS [Rate], purchase_qty AS [Purchase Qty],
                  purchase_rate AS [Purchase Rate], sales_qty AS [Sales Qty], sales_rate AS [Sales Rate],
                  avg_rate AS [Avg Rate], closing_stock AS [Closing Stock],
                  actual_stock AS [Actual Dip Stock], dip_diff AS [Dip Difference],
                  ROUND(dip_diff * avg_rate, 2) AS [Dip Diff Amount],
                  ROUND(closing_stock + dip_diff, 2) AS [Final Closing Stock (Next Opening)]
           FROM stock_register ORDER BY entry_date DESC, id DESC""", conn)
    conn.close()

    if not stock_df.empty:
        stock_df["Dip Status"] = stock_df["Dip Difference"].apply(
            lambda x: "Shortage (−)" if x < 0 else ("Excess (+)" if x > 0 else "Balanced"))
        st.dataframe(sr_index(stock_df), use_container_width=True)
        download_csv(sr_index(stock_df), "stock_register.csv")

        st.markdown("#### 🗑️ Delete a Stock Entry")
        ids = stock_df["Entry ID"].tolist()
        del_id = st.selectbox("Select Entry ID to delete", ids)
        if st.button("Delete Selected Stock Entry"):
            conn = get_db_connection()
            conn.execute("DELETE FROM stock_register WHERE id = ?", (int(del_id),))
            conn.commit()
            conn.close()
            resequence_ids("stock_register")
            st.success("Entry deleted and IDs re-sequenced.")
            st.rerun()
    else:
        st.info("No stock records yet.")

# ==========================================
# MODULE 5: CUSTOMER ENTRY (with review)
# ==========================================
elif module == "💳 Party Daily Sale & Credit Entry":
    title("Customer Credit Sale & Voucher Entry")

    customers = fetch_parties("Customer")["Party Name"].tolist()

    with st.form("credit_sale_form"):
        c1, c2 = st.columns(2)
        with c1:
            txn_date = st.date_input("Transaction Date", date.today())
            party_name = st.selectbox("Customer Name", customers if customers else ["None"])
            fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel", "Cash Payment/Voucher"])
            voucher_no = st.text_input("Voucher No.", value=next_voucher_no())
        with c2:
            qty = st.number_input("Qty (Ltrs)", min_value=0.0, value=0.0, step=1.0)
            rate = st.number_input("Rate", min_value=0.0, value=0.0, step=0.1)
            payment = st.number_input("Amount Received (Rs.)", min_value=0.0, value=0.0, step=100.0)
            desc = st.text_input("Description / Slip No.")
        review_cust = st.form_submit_button("👁️ Review Entry")

    if review_cust and party_name != "None":
        st.session_state["cust_pending"] = dict(
            txn_date=str(txn_date), party_name=party_name, fuel=fuel, voucher_no=voucher_no.strip(),
            qty=qty, rate=rate, payment=payment, desc=desc)

    pend = st.session_state.get("cust_pending")
    if pend:
        debit = pend["qty"] * pend["rate"] if pend["fuel"] != "Cash Payment/Voucher" else 0.0
        credit = pend["payment"]
        st.markdown("<div class='review-box'><b>🔎 Review before saving</b></div>", unsafe_allow_html=True)
        st.table(pd.DataFrame([{
            "Voucher No": pend["voucher_no"], "Date": pend["txn_date"], "Customer": pend["party_name"],
            "Fuel": pend["fuel"], "Ltrs": f"{pend['qty']:,.2f}", "Rate": f"{pend['rate']:,.2f}",
            "Sale (Debit)": f"{debit:,.2f}", "Received (Credit)": f"{credit:,.2f}",
            "Description": pend["desc"],
        }]))
        b1, b2 = st.columns(2)
        if b2.button("❌ Cancel", use_container_width=True):
            st.session_state.pop("cust_pending", None)
            st.rerun()
        if b1.button("✅ Confirm & Save", use_container_width=True):
            token = payload_token("cust", *pend.values())
            if already_saved(token):
                st.warning("This transaction was already saved. Duplicate save blocked.")
            else:
                conn = get_db_connection()
                conn.execute(
                    """INSERT INTO ledger (txn_date,party_name,party_type,item_type,qty_ltrs,rate,debit,credit,description,voucher_no)
                       VALUES (?,?,'Customer',?,?,?,?,?,?,?)""",
                    (pend["txn_date"], pend["party_name"],
                     None if pend["fuel"] == "Cash Payment/Voucher" else pend["fuel"],
                     pend["qty"], pend["rate"], debit, credit, pend["desc"], pend["voucher_no"] or None))
                conn.commit()
                conn.close()
                st.session_state.pop("cust_pending", None)
                st.success("✅ Customer transaction saved.")
                st.rerun()

    st.markdown("### 🕒 Last 10 Customer Entries")
    conn = get_db_connection()
    recent = pd.read_sql_query(
        """SELECT id AS [Entry ID], voucher_no AS [Voucher No], txn_date AS Date, party_name AS Customer,
                  item_type AS Fuel, qty_ltrs AS Ltrs, rate AS Rate, debit AS Debit, credit AS Credit,
                  description AS Description
           FROM ledger WHERE party_type='Customer' ORDER BY id DESC LIMIT 10""", conn)
    conn.close()
    if not recent.empty:
        st.dataframe(sr_index(recent), use_container_width=True)

# ==========================================
# MODULE 6: VENDOR ENTRY (with review)
# ==========================================
elif module == "🚛 Vendor Purchasing & Dip Stock":
    title("Vendor Purchasing & Payments")

    vendors = fetch_parties("Vendor")["Party Name"].tolist()

    with st.form("vendor_form"):
        c1, c2 = st.columns(2)
        with c1:
            txn_date = st.date_input("Date", date.today())
            vendor_name = st.selectbox("Vendor Name", vendors if vendors else ["None"])
            fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel", "Direct Payment"])
            voucher_no = st.text_input("Voucher No.", value=next_voucher_no())
        with c2:
            qty = st.number_input("Qty Received (Ltrs)", min_value=0.0, value=0.0, step=1.0)
            rate = st.number_input("Purchase Rate", min_value=0.0, value=0.0, step=0.1)
            paid = st.number_input("Payment Paid (Rs.)", min_value=0.0, value=0.0, step=100.0)
            desc = st.text_input("Invoice / Tanker No.")
        review_vend = st.form_submit_button("👁️ Review Entry")

    if review_vend and vendor_name != "None":
        st.session_state["vend_pending"] = dict(
            txn_date=str(txn_date), vendor_name=vendor_name, fuel=fuel, voucher_no=voucher_no.strip(),
            qty=qty, rate=rate, paid=paid, desc=desc)

    pend = st.session_state.get("vend_pending")
    if pend:
        credit = pend["qty"] * pend["rate"] if pend["fuel"] != "Direct Payment" else 0.0
        debit = pend["paid"]
        st.markdown("<div class='review-box'><b>🔎 Review before saving</b></div>", unsafe_allow_html=True)
        st.table(pd.DataFrame([{
            "Voucher No": pend["voucher_no"], "Date": pend["txn_date"], "Vendor": pend["vendor_name"],
            "Fuel": pend["fuel"], "Ltrs": f"{pend['qty']:,.2f}", "Rate": f"{pend['rate']:,.2f}",
            "Purchase (Credit)": f"{credit:,.2f}", "Paid (Debit)": f"{debit:,.2f}",
            "Description": pend["desc"],
        }]))
        b1, b2 = st.columns(2)
        if b2.button("❌ Cancel", use_container_width=True):
            st.session_state.pop("vend_pending", None)
            st.rerun()
        if b1.button("✅ Confirm & Save", use_container_width=True):
            token = payload_token("vend", *pend.values())
            if already_saved(token):
                st.warning("This transaction was already saved. Duplicate save blocked.")
            else:
                conn = get_db_connection()
                conn.execute(
                    """INSERT INTO ledger (txn_date,party_name,party_type,item_type,qty_ltrs,rate,debit,credit,description,voucher_no)
                       VALUES (?,?,'Vendor',?,?,?,?,?,?,?)""",
                    (pend["txn_date"], pend["vendor_name"],
                     None if pend["fuel"] == "Direct Payment" else pend["fuel"],
                     pend["qty"], pend["rate"], debit, credit, pend["desc"], pend["voucher_no"] or None))
                conn.commit()
                conn.close()
                st.session_state.pop("vend_pending", None)
                st.success("✅ Vendor transaction saved.")
                st.rerun()

    st.markdown("### 🕒 Last 10 Vendor Entries")
    conn = get_db_connection()
    recent = pd.read_sql_query(
        """SELECT id AS [Entry ID], voucher_no AS [Voucher No], txn_date AS Date, party_name AS Vendor,
                  item_type AS Fuel, qty_ltrs AS Ltrs, rate AS Rate, debit AS [Paid], credit AS [Purchase],
                  description AS Description
           FROM ledger WHERE party_type='Vendor' ORDER BY id DESC LIMIT 10""", conn)
    conn.close()
    if not recent.empty:
        st.dataframe(sr_index(recent), use_container_width=True)

# ==========================================
# MODULE 7: EDIT / DELETE ENTRIES
# ==========================================
elif module == "✏️ Edit / Manage Entries":
    title("Edit / Delete Entries")

    f1, f2, f3 = st.columns(3)
    p_type = f1.selectbox("Party Type", ["Customer", "Vendor"])
    names = ["— All —"] + fetch_parties(p_type)["Party Name"].tolist()
    sel_party = f2.selectbox("Party Name", names)
    search = f3.text_input("Search in Description / Date")

    q = "SELECT * FROM ledger WHERE party_type = ?"
    params = [p_type]
    if sel_party != "— All —":
        q += " AND party_name = ?"
        params.append(sel_party)
    if search.strip():
        q += " AND (IFNULL(description,'') LIKE ? OR txn_date LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    q += " ORDER BY txn_date DESC, id DESC"

    conn = get_db_connection()
    rows = pd.read_sql_query(q, conn, params=params)
    conn.close()

    if rows.empty:
        st.info("No entries found for this selection.")
    else:
        view = rows.rename(columns={
            "id": "Entry ID", "voucher_no": "Voucher No", "txn_date": "Date", "party_name": "Party Name",
            "party_type": "Type", "item_type": "Fuel", "qty_ltrs": "Ltrs",
            "rate": "Rate", "debit": "Debit", "credit": "Credit", "description": "Description",
        }).drop(columns=[])
        st.dataframe(sr_index(view), use_container_width=True)

        labels = {
            f"ID {r.id} | {r.voucher_no or '-'} | {r.txn_date} | {r.party_name} | {r.item_type or '-'} | "
            f"Dr {r.debit:,.0f} / Cr {r.credit:,.0f}": int(r.id)
            for r in rows.itertuples()
        }
        picked_label = st.selectbox("Select the entry to edit or delete", list(labels.keys()))
        entry_id = labels[picked_label]
        rec = rows[rows["id"] == entry_id].iloc[0]

        tab_edit, tab_del = st.tabs(["✏️ Edit Entry", "🗑️ Delete Entry"])

        with tab_edit:
            with st.form(f"edit_form_{entry_id}"):
                e1, e2 = st.columns(2)
                with e1:
                    n_date = st.date_input("Date", datetime.strptime(rec["txn_date"], "%Y-%m-%d").date())
                    party_options = fetch_parties(p_type)["Party Name"].tolist()
                    n_party = st.selectbox("Party Name", party_options,
                                           index=party_options.index(rec["party_name"])
                                           if rec["party_name"] in party_options else 0)
                    fuel_options = ["Petrol", "Diesel", "None (Payment Only)"]
                    cur_fuel = rec["item_type"] if rec["item_type"] in ("Petrol", "Diesel") else "None (Payment Only)"
                    n_fuel = st.selectbox("Fuel Item", fuel_options, index=fuel_options.index(cur_fuel))
                    n_voucher = st.text_input("Voucher No.", value=rec["voucher_no"] or "")
                with e2:
                    n_qty = st.number_input("Ltrs", min_value=0.0, value=float(rec["qty_ltrs"]), step=1.0)
                    n_rate = st.number_input("Rate", min_value=0.0, value=float(rec["rate"]), step=0.1)
                    n_debit = st.number_input("Debit (Rs.)", min_value=0.0, value=float(rec["debit"]), step=100.0)
                    n_credit = st.number_input("Credit (Rs.)", min_value=0.0, value=float(rec["credit"]), step=100.0)
                    n_desc = st.text_input("Description", value=rec["description"] or "")
                auto = st.checkbox("Auto-calculate amount from Ltrs × Rate", value=False)
                do_update = st.form_submit_button("💾 Update This Entry")

            if do_update:
                d_val, c_val = n_debit, n_credit
                if auto and n_fuel != "None (Payment Only)":
                    if p_type == "Customer":
                        d_val = n_qty * n_rate
                    else:
                        c_val = n_qty * n_rate
                conn = get_db_connection()
                conn.execute(
                    """UPDATE ledger SET txn_date=?, party_name=?, item_type=?, qty_ltrs=?, rate=?,
                              debit=?, credit=?, description=?, voucher_no=? WHERE id=?""",
                    (str(n_date), n_party,
                     None if n_fuel == "None (Payment Only)" else n_fuel,
                     n_qty, n_rate, d_val, c_val, n_desc, n_voucher.strip() or None, entry_id))
                conn.commit()
                conn.close()
                st.success(f"✅ Entry ID {entry_id} updated.")
                st.rerun()

        with tab_del:
            st.warning(f"You are about to delete: {picked_label}")
            sure = st.checkbox("Yes, I am sure", key=f"sure_{entry_id}")
            if st.button("🗑️ Delete Entry", disabled=not sure):
                conn = get_db_connection()
                conn.execute("DELETE FROM ledger WHERE id = ?", (entry_id,))
                conn.commit()
                conn.close()
                resequence_ids("ledger")
                st.success("Entry deleted and IDs re-sequenced.")
                st.rerun()

    st.markdown("---")
    if st.button("🔢 Re-sequence all Entry IDs (1,2,3...)"):
        resequence_ids("ledger")
        resequence_ids("stock_register")
        st.success("All IDs re-sequenced in date order.")
        st.rerun()

# ==========================================
# MODULE 8: RECONCILIATION
# ==========================================
elif module == "⚖️ Stock vs Sale Month-End Match":
    title("Stock vs Sales Reconciliation")

    conn = get_db_connection()
    stock_summary = pd.read_sql_query(
        """SELECT item_type AS [Fuel Item], SUM(purchase_qty) AS [Total Purchased],
                  SUM(sales_qty) AS [Total Stock Sales], SUM(dip_diff) AS [Total Dip Variance]
           FROM stock_register GROUP BY item_type""", conn)
    ledger_summary = pd.read_sql_query(
        """SELECT item_type AS [Fuel Item], SUM(qty_ltrs) AS [Total Ledger Sales]
           FROM ledger WHERE party_type='Customer' AND item_type IS NOT NULL GROUP BY item_type""", conn)
    conn.close()

    rec = pd.merge(stock_summary, ledger_summary, on="Fuel Item", how="outer").fillna(0)
    if not rec.empty:
        rec["Sales Variance"] = rec["Total Stock Sales"] - rec["Total Ledger Sales"]
        rec["Dip Status"] = rec["Total Dip Variance"].apply(
            lambda x: "Shortage (−)" if x < 0 else ("Excess (+)" if x > 0 else "Balanced"))
        st.dataframe(sr_index(rec), use_container_width=True)
        download_csv(sr_index(rec), "reconciliation.csv")
    else:
        st.info("No data to reconcile yet.")

# ==========================================
# MODULE 9: MASTER SETUP
# ==========================================
elif module == "⚙️ Master Setup (Parties/Vendors)":
    title("Master Parties Setup & Management")

    tab_add, tab_edit, tab_del = st.tabs(["➕ Add Party", "✏️ Edit Party", "❌ Remove Party"])

    with tab_add:
        with st.form("add_party_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Party / Vendor Name")
                p_type = st.selectbox("Type", ["Customer", "Vendor"])
            with c2:
                op_bal = st.number_input("Opening Balance (Rs.)", value=0.0, step=100.0)
                phone = st.text_input("Phone Number")
            add_it = st.form_submit_button("➕ Save Party")

        if add_it and name.strip():
            token = payload_token("party", name.strip(), p_type, op_bal, phone)
            if already_saved(token):
                st.warning("Already saved. Duplicate blocked.")
            else:
                try:
                    conn = get_db_connection()
                    conn.execute("INSERT INTO parties (name,type,opening_balance,phone) VALUES (?,?,?,?)",
                                 (name.strip(), p_type, op_bal, phone))
                    conn.commit()
                    conn.close()
                    st.success(f"Party '{name}' added.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("A party with this name already exists.")

    with tab_edit:
        allp = fetch_parties()
        if not allp.empty:
            sel = st.selectbox("Select Party", allp["Party Name"].tolist(), key="edit_party_sel")
            row = allp[allp["Party Name"] == sel].iloc[0]
            with st.form("edit_party_form"):
                c1, c2 = st.columns(2)
                new_name = c1.text_input("Name", value=row["Party Name"])
                new_type = c1.selectbox("Type", ["Customer", "Vendor"],
                                        index=0 if row["Type"] == "Customer" else 1)
                new_bal = c2.number_input("Opening Balance", value=float(row["Opening Balance"]), step=100.0)
                new_phone = c2.text_input("Phone", value=row["Phone"] or "")
                upd = st.form_submit_button("💾 Update Party")
            if upd:
                conn = get_db_connection()
                conn.execute("UPDATE ledger SET party_name=?, party_type=? WHERE party_name=?",
                             (new_name, new_type, sel))
                conn.execute("UPDATE parties SET name=?, type=?, opening_balance=?, phone=? WHERE name=?",
                             (new_name, new_type, new_bal, new_phone, sel))
                conn.commit()
                conn.close()
                st.success("Party updated (ledger entries renamed too).")
                st.rerun()

    with tab_del:
        allp = fetch_parties()
        if not allp.empty:
            to_del = st.selectbox("Select Party to Remove", allp["Party Name"].tolist(), key="del_party_sel")
            conn = get_db_connection()
            cnt = conn.execute("SELECT COUNT(*) c FROM ledger WHERE party_name=?", (to_del,)).fetchone()["c"]
            conn.close()
            if cnt:
                st.warning(f"⚠️ This party has {cnt} ledger entries. Deleting the party keeps those entries.")
            sure = st.checkbox("Yes, remove this party", key="sure_party")
            if st.button("❌ Confirm Delete Party", disabled=not sure):
                conn = get_db_connection()
                conn.execute("DELETE FROM parties WHERE name = ?", (to_del,))
                conn.commit()
                conn.close()
                st.success(f"Party '{to_del}' removed.")
                st.rerun()

    st.markdown("### 📋 Active Master List")
    st.dataframe(sr_index(fetch_parties()), use_container_width=True)

# ==========================================
# MODULE 10: BACKUP & RESTORE
# ==========================================
elif module == "💾 Backup & System Recovery":
    title("Database Backup & System Recovery")

    conn = get_db_connection()
    backup = {
        "parties": pd.read_sql_query("SELECT * FROM parties", conn).to_dict(orient="records"),
        "stock_register": pd.read_sql_query("SELECT * FROM stock_register", conn).to_dict(orient="records"),
        "ledger": pd.read_sql_query("SELECT * FROM ledger", conn).to_dict(orient="records"),
    }
    conn.close()

    st.download_button("💾 Download JSON Backup", json.dumps(backup, indent=2),
                       file_name=f"FD_CNG_Backup_{date.today()}.json", mime="application/json")

    st.markdown("---")
    st.markdown("### 📤 Restore System Data")
    up = st.file_uploader("Upload JSON Backup File", type=["json"])

    if up is not None:
        sure = st.checkbox("I understand this will replace all current data")
        if st.button("⚠️ Confirm System Restore", disabled=not sure):
            data = json.load(up)
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM parties")
            cur.execute("DELETE FROM stock_register")
            cur.execute("DELETE FROM ledger")

            for p in data.get("parties", []):
                cur.execute("INSERT INTO parties (id,name,type,opening_balance,phone) VALUES (?,?,?,?,?)",
                            (p.get("id"), p.get("name"), p.get("type"),
                             p.get("opening_balance", 0.0), p.get("phone", "")))

            stock_cols = ["id", "entry_date", "item_type", "opening_stock", "rate", "opening_amount",
                          "purchase_qty", "purchase_rate", "purchase_amount", "total_purchase_amount",
                          "avg_rate", "available_stock", "sales_qty", "sales_rate", "sales_amount",
                          "total_sales_amount", "closing_amount", "closing_stock", "dip_diff",
                          "actual_stock", "actual_amount"]
            for s in data.get("stock_register", []):
                cur.execute(
                    f"INSERT INTO stock_register ({','.join(stock_cols)}) VALUES ({','.join('?' * len(stock_cols))})",
                    tuple(s.get(c) for c in stock_cols))

            for l in data.get("ledger", []):
                cur.execute(
                    """INSERT INTO ledger (id,txn_date,party_name,party_type,item_type,qty_ltrs,rate,debit,credit,description,voucher_no)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (l.get("id"), l.get("txn_date"), l.get("party_name"), l.get("party_type"),
                     l.get("item_type"), l.get("qty_ltrs", 0.0), l.get("rate", 0.0),
                     l.get("debit", 0.0), l.get("credit", 0.0), l.get("description", ""),
                     l.get("voucher_no")))

            conn.commit()
            conn.close()
            st.success("✅ System restored successfully.")
            st.rerun()
