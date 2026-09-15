"""
FD CNG Fuel Station - Management App (Turso Cloud Integrated)
=============================================================
Supports Turso Cloud Database via libsql-client with local fallback.

Run:  streamlit run app.py
"""

import json
import hashlib
import threading
from datetime import date, datetime
import sqlite3

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Turso Client Import
try:
    import libsql_client as libsql
    HAS_TURSO = True
except ImportError:
    HAS_TURSO = False

# ==========================================
# 1. PAGE CONFIG & THEME
# ==========================================
st.set_page_config(
    page_title="FD CNG Fuel Station",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded",
)

components.html(
    """<script>
    (function () {
        function fixTitle() {
            try { if (window.parent && window.parent.document) {
                window.parent.document.title = "FD CNG Fuel Station";
            } } catch (e) {}
        }
        fixTitle();
        setInterval(fixTitle, 800);
    })();
    </script>""",
    height=0, width=0,
)

st.markdown(
    """
    <style>
        .main { background-color: #f4f7f5; }
        .app-title {
            font-size: 26px; font-weight: 800; color: #ffffff;
            padding: 16px 22px; margin-bottom: 20px;
            background: linear-gradient(90deg, #0b5d34 0%, #1c8b4e 55%, #2e7d32 100%);
            border-left: 8px solid #f57c00;
            border-radius: 10px;
            box-shadow: 0 3px 10px rgba(11,93,52,.25);
            letter-spacing: .3px;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b3d24 0%, #14532d 100%);
        }
        section[data-testid="stSidebar"] * { color: #f0fdf4 !important; }
        section[data-testid="stSidebar"] .stRadio > label { color: #f0fdf4 !important; }
        section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.2); }
        .metric-card {
            background: #ffffff; border: 1px solid #e3e8ef; border-top: 4px solid #f57c00;
            border-radius: 12px; padding: 16px; text-align: center;
            box-shadow: 0 2px 6px rgba(0,0,0,.06);
        }
        .metric-card h4 { margin: 0; font-size: 13px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: .4px; }
        .metric-card p  { margin: 8px 0 0; font-size: 21px; font-weight: 800; color: #0b3d24; }
        .review-box {
            background:#fff7e6; border:1px solid #f57c00; border-left: 6px solid #f57c00;
            border-radius:10px; padding:14px; margin-bottom: 10px;
        }
        div.stButton > button, div.stFormSubmitButton > button, div.stDownloadButton > button {
            background: linear-gradient(90deg, #1c8b4e, #2e7d32);
            color: #ffffff; border: none; border-radius: 8px; font-weight: 700;
            box-shadow: 0 2px 4px rgba(0,0,0,.15);
        }
        div.stButton > button:hover, div.stFormSubmitButton > button:hover, div.stDownloadButton > button:hover {
            background: linear-gradient(90deg, #f57c00, #ef6c00); color:#fff;
        }
        button[data-baseweb="tab"] { font-weight: 700; }
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
# 3. TURSO / SQLITE DATABASE SETUP
# ==========================================
DB_FILE = "fd_cng_fuel_station.db"

# A single shared lock so concurrent Streamlit sessions don't hit the
# same underlying connection at once (sqlite3 connections aren't safe
# for concurrent use across threads).
_db_lock = threading.Lock()


@st.cache_resource(show_spinner=False)
def get_db_connection():
    """Turso Cloud connection using secrets with fallback to local SQLite.

    This is cached with st.cache_resource so the SAME connection/client is
    reused across every rerun and every query. Previously a brand-new
    connection (a fresh network round-trip for Turso) was opened and closed
    for every single query, which is what made the app feel slow.
    """
    turso_url = st.secrets.get("turso", {}).get("TURSO_DATABASE_URL")
    turso_token = st.secrets.get("turso", {}).get("TURSO_AUTH_TOKEN")

    if HAS_TURSO and turso_url and turso_token:
        try:
            url = turso_url.replace("libsql://", "https://")
            conn = libsql.create_client_sync(url=url, auth_token=turso_token)
            return conn
        except Exception as e:
            st.error(f"⚠️ Turso Sync Error: {e}. Falling back to local SQLite.")

    # Fallback to local SQLite
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _is_libsql(conn) -> bool:
    return type(conn).__module__.startswith("libsql")


def execute_query(query, params=()):
    conn = get_db_connection()
    with _db_lock:
        if _is_libsql(conn):
            return conn.execute(query, params)
        else:
            cur = conn.cursor()
            res = cur.execute(query, params)
            conn.commit()
            return res


def read_df(query, params=()):
    conn = get_db_connection()
    with _db_lock:
        if _is_libsql(conn):
            res = conn.execute(query, params)
            cols = res.columns
            rows = res.rows
            return pd.DataFrame(rows, columns=cols)
        else:
            return pd.read_sql_query(query, conn, params=params)


def init_db():
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT CHECK(type IN ('Customer','Vendor')) NOT NULL,
            opening_balance REAL DEFAULT 0.0,
            phone TEXT
        )"""
    )

    execute_query(
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

    execute_query(
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

    df_p = read_df("SELECT COUNT(*) c FROM parties")
    total_parties = df_p.iloc[0]["c"] if not df_p.empty else 0

    if total_parties == 0:
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
            execute_query("INSERT INTO parties (name, type, opening_balance, phone) VALUES (?, 'Customer', 0.0, '')", (c,))
        for v in default_vendors:
            execute_query("INSERT INTO parties (name, type, opening_balance, phone) VALUES (?, 'Vendor', 0.0, '')", (v,))


@st.cache_resource(show_spinner=False)
def _init_db_once():
    # Streamlit reruns the whole script on every click/interaction, so
    # without this guard init_db() (several CREATE TABLE + COUNT queries)
    # was re-running on every single rerun. It only needs to run once
    # per app process.
    init_db()
    return True


_init_db_once()


# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================
def sr_index(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    res = df.copy().reset_index(drop=True)
    res.index = range(1, len(res) + 1)
    res.index.name = "Sr. No."
    return res


def payload_token(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()


def already_saved(token: str) -> bool:
    saved = st.session_state.setdefault("saved_tokens", set())
    if token in saved:
        return True
    saved.add(token)
    return False


def fetch_parties(p_type=None) -> pd.DataFrame:
    base = ("SELECT id, name AS [Party Name], type AS [Type], "
            "opening_balance AS [Opening Balance], phone AS [Phone] FROM parties ")
    if p_type:
        df = read_df(base + "WHERE type = ? ORDER BY name ASC", params=(p_type,))
    else:
        df = read_df(base + "ORDER BY type ASC, name ASC")
    return df


def calculate_party_balances(party_type: str) -> pd.DataFrame:
    parties = read_df("SELECT name, opening_balance FROM parties WHERE type = ?", params=(party_type,))
    if parties.empty:
        return pd.DataFrame()
    parties["opening_balance"] = parties["opening_balance"].fillna(0.0)

    # Aggregate per-party totals in SQL instead of pulling every ledger row
    # and looping/filtering per party in Python — much faster as the
    # ledger grows.
    ledger_sums = read_df(
        """SELECT party_name, SUM(debit) AS total_debit, SUM(credit) AS total_credit
           FROM ledger WHERE party_type = ? GROUP BY party_name""",
        params=(party_type,))

    merged = parties.merge(ledger_sums, left_on="name", right_on="party_name", how="left")
    merged["total_debit"] = merged["total_debit"].fillna(0.0)
    merged["total_credit"] = merged["total_credit"].fillna(0.0)

    if party_type == "Customer":
        merged["Net Balance"] = merged["opening_balance"] + (merged["total_debit"] - merged["total_credit"])
    else:
        merged["Net Balance"] = merged["opening_balance"] + (merged["total_credit"] - merged["total_debit"])

    out = merged.rename(columns={
        "name": "Party Name", "opening_balance": "Opening Balance",
        "total_debit": "Total Debit", "total_credit": "Total Credit",
    })[["Party Name", "Opening Balance", "Total Debit", "Total Credit", "Net Balance"]]
    return sr_index(out)


def resequence_ids(table: str):
    date_col = "txn_date" if table == "ledger" else "entry_date"
    df = read_df(f"SELECT id FROM {table} ORDER BY {date_col} ASC, id ASC")
    if df.empty:
        return
    ids = df["id"].tolist()
    conn = get_db_connection()

    if _is_libsql(conn):
        # Turso client: no local executemany, keep the per-row calls but
        # they now reuse the single cached connection instead of opening
        # a brand-new one for every statement.
        with _db_lock:
            for old in ids:
                conn.execute(f"UPDATE {table} SET id = ? WHERE id = ?", (old + 1_000_000, old))
            for new, old in enumerate(ids, start=1):
                conn.execute(f"UPDATE {table} SET id = ? WHERE id = ?", (new, old + 1_000_000))
    else:
        # Local SQLite: batch everything into two executemany calls inside
        # one transaction instead of N individual round trips.
        with _db_lock:
            cur = conn.cursor()
            cur.executemany(
                f"UPDATE {table} SET id = ? WHERE id = ?",
                [(old + 1_000_000, old) for old in ids],
            )
            cur.executemany(
                f"UPDATE {table} SET id = ? WHERE id = ?",
                [(new, old + 1_000_000) for new, old in enumerate(ids, start=1)],
            )
            conn.commit()


def blank_number(label: str, min_value=None, help=None, key=None) -> float:
    raw = st.text_input(label, value="", placeholder="0", help=help, key=key)
    raw = (raw or "").strip()
    if raw == "":
        return 0.0
    try:
        val = float(raw)
    except ValueError:
        st.error(f"⚠️ '{label}' mein sirf number likhein (e.g. 123.45).")
        return 0.0
    if min_value is not None and val < min_value:
        st.warning(f"⚠️ '{label}' {min_value} se kam nahi ho sakta — {min_value} le liya gaya.")
        return min_value
    return val


def opening_balance_now(party_name: str, party_type: str) -> float:
    ob_df = read_df("SELECT opening_balance FROM parties WHERE name=? AND type=?", params=(party_name, party_type))
    base = ob_df.iloc[0]["opening_balance"] if not ob_df.empty else 0.0
    base = base or 0.0

    l_df = read_df("SELECT SUM(debit) d, SUM(credit) c FROM ledger WHERE party_name=? AND party_type=?", params=(party_name, party_type))
    d = l_df.iloc[0]["d"] if not l_df.empty and l_df.iloc[0]["d"] is not None else 0.0
    c = l_df.iloc[0]["c"] if not l_df.empty and l_df.iloc[0]["c"] is not None else 0.0

    return base + ((d - c) if party_type == "Customer" else (c - d))


def download_csv(df: pd.DataFrame, filename: str, label="⬇️ Download CSV"):
    if df is not None and not df.empty:
        st.download_button(label, df.to_csv(index=True).encode("utf-8"),
                           file_name=filename, mime="text/csv")


def last_closing_stock(item_type: str) -> float:
    df = read_df("""SELECT closing_stock, dip_diff FROM stock_register
                    WHERE item_type = ? ORDER BY entry_date DESC, id DESC LIMIT 1""", params=(item_type,))
    if df.empty:
        return 0.0
    row = df.iloc[0]
    return (row["closing_stock"] or 0.0) + (row["dip_diff"] or 0.0)


def next_voucher_no() -> str:
    df = read_df("SELECT voucher_no FROM ledger WHERE voucher_no IS NOT NULL")
    max_n = 0
    if not df.empty:
        for r in df["voucher_no"]:
            digits = "".join(ch for ch in str(r or "") if ch.isdigit())
            if digits:
                max_n = max(max_n, int(digits))
    return f"V-{max_n + 1:05d}"


def fmt_ddmmyyyy(d) -> str:
    try:
        return pd.to_datetime(d).strftime("%d-%m-%Y")
    except Exception:
        return str(d)


def render_print_statement(party: str, p_type: str, op_bal: float, closing_bal: float,
                            stmt: pd.DataFrame, from_date, to_date):
    from_str = fmt_ddmmyyyy(from_date)
    to_str = fmt_ddmmyyyy(to_date)

    rows_html = ""
    for i, (_, r) in enumerate(stmt.iterrows(), start=1):
        fuel_val = r['Fuel'] if pd.notna(r['Fuel']) else '-'
        v_num = r['Voucher No'] if pd.notna(r.get('Voucher No')) else ''
        desc = r['Description'] or ''
        rows_html += f"""
        <tr>
            <td>{i}</td>
            <td>{v_num}</td>
            <td>{fmt_ddmmyyyy(r['Date'])}</td>
            <td>{fuel_val}</td>
            <td class="num">{r['Ltrs']:,.2f}</td>
            <td class="num">{r['Rate']:,.2f}</td>
            <td class="num">{r['Debit']:,.2f}</td>
            <td class="num">{r['Credit']:,.2f}</td>
            <td>{desc}</td>
            <td class="num">{r['Running Balance']:,.2f}</td>
        </tr>"""

    print_doc = f"""<!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <title>{party} Statement</title>
    <style>
        * {{ box-sizing: border-box; }}
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
        @page {{ margin: 8mm; size: auto; }}
    </style>
    </head>
    <body>
        <div class="sheet">
            <div class="head">
                <h2>⛽ FD CNG Fuel Station</h2>
                <p>{p_type} Statement &nbsp;|&nbsp; {from_str} to {to_str}</p>
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
        <script>
            window.onload = function () {{
                window.focus();
                window.print();
            }};
            window.onafterprint = function () {{
                window.close();
            }};
        </script>
    </body>
    </html>
    """

    safe_doc = json.dumps(print_doc).replace("</script>", "<\\/script>")

    trigger_html = f"""
    <button id="printBtn" style="
        background:linear-gradient(90deg,#1c8b4e,#2e7d32); color:#fff; border:none;
        padding:10px 22px; border-radius:8px; font-weight:bold; font-size:14px;
        cursor:pointer;">🖨️ Print Statement Now</button>
    <script>
        document.getElementById('printBtn').onclick = function () {{
            var doc = {safe_doc};
            var w = window.open('', '_blank');
            if (w) {{
                w.document.open();
                w.document.write(doc);
                w.document.close();
            }}
        }};
    </script>
    """
    components.html(trigger_html, height=60)


# ==========================================
# 5. SIDEBAR NAVIGATION
# ==========================================
st.sidebar.markdown("## ⛽ FD CNG Station")

# Turso Status Indicator
turso_configured = bool(st.secrets.get("turso", {}).get("TURSO_DATABASE_URL"))
if turso_configured and HAS_TURSO:
    st.sidebar.success("☁️ Turso Cloud: Connected")
else:
    st.sidebar.warning("📁 Local SQLite Mode")

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

    fuel = read_df(
        "SELECT item_type, SUM(qty_ltrs) total FROM ledger "
        "WHERE party_type='Customer' AND item_type IS NOT NULL GROUP BY item_type")

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
    matrix = read_df(
        """SELECT party_name AS [Party Name], strftime('%Y-%m', txn_date) AS Month,
                  item_type AS [Fuel Item], SUM(debit) AS [Total Amount]
           FROM ledger
           WHERE party_type='Customer' AND item_type IN ('Petrol','Diesel')
           GROUP BY party_name, Month, item_type""")

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

    daily = read_df(
        """SELECT txn_date AS Date, party_name AS [Party Name],
                  SUM(CASE WHEN item_type='Petrol' THEN debit ELSE 0 END) AS Petrol,
                  SUM(CASE WHEN item_type='Diesel' THEN debit ELSE 0 END) AS Diesel,
                  SUM(credit) AS [Payment Received],
                  SUM(debit)  AS [Credit Total]
           FROM ledger
           WHERE party_type='Customer' AND strftime('%Y-%m', txn_date) = ?
           GROUP BY txn_date, party_name
           ORDER BY txn_date ASC, party_name ASC""", params=(month,))

    parties_ob = read_df("SELECT name AS [Party Name], opening_balance AS MasterOpening FROM parties WHERE type='Customer'")
    full_hist = read_df(
        """SELECT party_name AS [Party Name], txn_date AS Date,
                  SUM(debit) AS DebitDay, SUM(credit) AS CreditDay
           FROM ledger WHERE party_type='Customer'
           GROUP BY party_name, txn_date ORDER BY party_name, txn_date""")

    if not daily.empty:
        full_hist = full_hist.merge(parties_ob, on="Party Name", how="left")
        full_hist["MasterOpening"] = full_hist["MasterOpening"].fillna(0.0)
        full_hist["NetDay"] = full_hist["DebitDay"] - full_hist["CreditDay"]
        full_hist["Closing Balance"] = full_hist["MasterOpening"] + full_hist.groupby("Party Name")["NetDay"].cumsum()
        full_hist["Opening Balance"] = full_hist["Closing Balance"] - full_hist["NetDay"]

        daily = daily.merge(full_hist[["Party Name", "Date", "Opening Balance", "Closing Balance"]],
                            on=["Party Name", "Date"], how="left")
        daily = daily[["Date", "Party Name", "Opening Balance", "Petrol", "Diesel",
                       "Payment Received", "Credit Total", "Closing Balance"]]

        st.dataframe(sr_index(daily), use_container_width=True)
        download_csv(sr_index(daily), f"daily_credit_{month}.csv")

        st.markdown("### 📈 Day-Wise Totals")
        totals = daily.groupby("Date")[["Opening Balance", "Petrol", "Diesel", "Credit Total",
                                        "Payment Received", "Closing Balance"]].sum().reset_index()
        st.dataframe(sr_index(totals), use_container_width=True)

        st.markdown("### 🧾 Month Grand Total")
        month_start_ob = daily.sort_values("Date").groupby("Party Name").first()["Opening Balance"].sum()
        month_end_cb = daily.sort_values("Date").groupby("Party Name").last()["Closing Balance"].sum()
        g0, g1, g2, g3, g4 = st.columns(5)
        g0.metric("Opening Balance (Rs.)", f"{month_start_ob:,.2f}")
        g1.metric("Petrol (Rs.)", f"{daily['Petrol'].sum():,.2f}")
        g2.metric("Diesel (Rs.)", f"{daily['Diesel'].sum():,.2f}")
        g3.metric("Payments (Rs.)", f"{daily['Payment Received'].sum():,.2f}")
        g4.metric("Closing Balance (Rs.)", f"{month_end_cb:,.2f}")
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
    from_date = d1.date_input("From Date", date(date.today().year, 1, 1), format="DD-MM-YYYY")
    to_date = d2.date_input("To Date", date.today(), format="DD-MM-YYYY")

    if party != "None":
        row_df = read_df("SELECT opening_balance FROM parties WHERE name = ?", params=(party,))
        op_bal = row_df.iloc[0]["opening_balance"] if not row_df.empty else 0.0
        op_bal = op_bal or 0.0

        stmt = read_df(
            """SELECT id AS [Entry ID], voucher_no AS [Voucher No], txn_date AS Date, item_type AS Fuel,
                      qty_ltrs AS Ltrs, rate AS Rate, debit AS Debit, credit AS Credit, description AS Description
               FROM ledger WHERE party_name = ? AND txn_date BETWEEN ? AND ?
               ORDER BY txn_date ASC, id ASC""",
            params=(party, str(from_date), str(to_date)))

        bal, rows = op_bal, []
        for _, r in stmt.iterrows():
            bal += (r["Debit"] - r["Credit"]) if p_type == "Customer" else (r["Credit"] - r["Debit"])
            rows.append(bal)
        stmt["Running Balance"] = rows
        closing_bal = rows[-1] if rows else op_bal

        st.info(f"**{party}** | Type: {p_type} | Period: {from_date.strftime('%d-%m-%Y')} to "
                f"{to_date.strftime('%d-%m-%Y')} | Opening Balance: Rs. {op_bal:,.2f} | "
                f"Closing Balance: Rs. {closing_bal:,.2f}")

        stmt_display = stmt.copy()
        stmt_display["Date"] = stmt_display["Date"].apply(fmt_ddmmyyyy)
        stmt_view = sr_index(stmt_display)
        st.dataframe(stmt_view, use_container_width=True)
        download_csv(stmt_view, f"{party}_statement.csv", "⬇️ Download CSV")

        st.markdown("### 🖨️ Print Statement")
        st.caption("Click the green button below and use the browser's print dialog to send this statement straight to your printer.")
        render_print_statement(party, p_type, op_bal, closing_bal, stmt, from_date, to_date)

# ==========================================
# MODULE 4: DAILY STOCK REGISTER
# ==========================================
elif module == "🛢️ Daily Stock Register":
    title("Daily Stock Register")

    st.caption("Dip Difference = Shortage/Excess amount entered during physical dip check. Minus means shortage, plus means excess.")

    item_type = st.selectbox("Fuel Item", ["Petrol", "Diesel"], key="stock_item_type_pick")
    suggested_opening = last_closing_stock(item_type)
    st.caption(f"↪️ Auto-filled Opening Stock for **{item_type}** = last saved Final Closing Stock ({suggested_opening:,.2f} Ltrs).")

    with st.form("stock_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            e_date = st.date_input("Entry Date", date.today(), format="DD-MM-YYYY")
            st.text_input("Fuel Item", value=item_type, disabled=True)
            op_stock = st.number_input("Opening Stock (Ltrs)", value=float(suggested_opening), step=1.0)
            op_rate = blank_number("Opening Rate", min_value=0.0)
        with c2:
            p_qty = blank_number("Purchase Qty (Ltrs)", min_value=0.0)
            p_rate = blank_number("Purchase Rate", min_value=0.0)
            s_qty = blank_number("Sales Qty (Ltrs)", min_value=0.0)
            s_rate = blank_number("Sales Rate", min_value=0.0)
        with c3:
            dip_checked = st.checkbox("Physical Dip Check done today?", value=True)
            dip_input = blank_number("Dip Shortage / Excess (+/− Ltrs)")

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
        closing_stock = avail - s_qty
        dip_diff = dip_input if dip_checked else 0.0
        dip_amount = dip_diff * avg_rate
        actual_stock = closing_stock + dip_diff
        act_amount = actual_stock * avg_rate
        final_closing = closing_stock + dip_diff
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
        r2.write(f"**Actual Dip Stock:** {k['actual_stock']:,.2f} Ltrs")
        sign = "SHORTAGE (−)" if k["dip_diff"] < 0 else ("EXCESS (+)" if k["dip_diff"] > 0 else "NO DIFFERENCE")
        r3.write(f"**Dip Difference:** {k['dip_diff']:+,.2f} Ltrs  → {sign}")
        r3.write(f"**Dip Diff Amount:** Rs. {k['dip_amount']:+,.2f}")
        r3.write(f"**Closing Amount:** Rs. {k['closing_amount']:,.2f}")

        dup_df = read_df("SELECT COUNT(*) c FROM stock_register WHERE entry_date=? AND item_type=?", params=(pend["e_date"], pend["item_type"]))
        dup = dup_df.iloc[0]["c"] if not dup_df.empty else 0

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
                execute_query(
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
                st.session_state.pop("stock_pending", None)
                st.success("✅ Daily stock entry saved.")
                st.rerun()

    st.markdown("### 📊 Existing Stock Records")
    stock_df = read_df(
        """SELECT id AS [Entry ID], entry_date AS [Entry Date], item_type AS [Fuel Item],
                  opening_stock AS [Opening Stock], rate AS [Rate], purchase_qty AS [Purchase Qty],
                  purchase_rate AS [Purchase Rate], sales_qty AS [Sales Qty], sales_rate AS [Sales Rate],
                  avg_rate AS [Avg Rate], closing_stock AS [Closing Stock],
                  actual_stock AS [Actual Dip Stock], dip_diff AS [Dip Difference],
                  ROUND(dip_diff * avg_rate, 2) AS [Dip Diff Amount],
                  ROUND(closing_stock + dip_diff, 2) AS [Final Closing Stock (Next Opening)]
           FROM stock_register ORDER BY entry_date DESC, id DESC""")

    if not stock_df.empty:
        stock_df["Dip Status"] = stock_df["Dip Difference"].apply(
            lambda x: "Shortage (−)" if x < 0 else ("Excess (+)" if x > 0 else "Balanced"))
        st.dataframe(sr_index(stock_df), use_container_width=True)
        download_csv(sr_index(stock_df), "stock_register.csv")

        st.markdown("#### 🗑️ Delete a Stock Entry")
        ids = stock_df["Entry ID"].tolist()
        del_id = st.selectbox("Select Entry ID to delete", ids)
        if st.button("Delete Selected Stock Entry"):
            execute_query("DELETE FROM stock_register WHERE id = ?", (int(del_id),))
            resequence_ids("stock_register")
            st.success("Entry deleted and IDs re-sequenced.")
            st.rerun()
    else:
        st.info("No stock records yet.")

# ==========================================
# MODULE 5: CUSTOMER ENTRY
# ==========================================
elif module == "💳 Party Daily Sale & Credit Entry":
    title("Customer Credit Sale & Voucher Entry")

    customers = fetch_parties("Customer")["Party Name"].tolist()

    st.markdown("#### 1️⃣ Choose Entry Type")
    entry_kind = st.radio(
        "Entry Type",
        [
            "🧾 Fuel Sale Entry  —  Cash In (Debit)",
            "💵 Payment Received from Customer  —  Cash Out (Credit)",
            "🔄 Combined (sale + payment on the exact same day)",
        ],
        key="cust_entry_kind",
    )

    with st.form("credit_sale_form"):
        c1, c2 = st.columns(2)
        if entry_kind.startswith("🧾"):
            with c1:
                txn_date = st.date_input("Sale / Delivery Date", date.today(), format="DD-MM-YYYY")
                party_name = st.selectbox("Customer Name", customers if customers else ["None"])
                fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel"])
                voucher_no = st.text_input("Voucher No.", value=next_voucher_no())
            with c2:
                qty = blank_number("Qty (Ltrs)", min_value=0.0)
                rate = blank_number("Rate", min_value=0.0)
                desc = st.text_input("Description / Slip No.")
            payment = 0.0
        elif entry_kind.startswith("💵"):
            with c1:
                txn_date = st.date_input("Payment Date", date.today(), format="DD-MM-YYYY")
                party_name = st.selectbox("Customer Name", customers if customers else ["None"])
                voucher_no = st.text_input("Voucher No.", value=next_voucher_no())
            with c2:
                payment = blank_number("Amount Received (Rs.)", min_value=0.0)
                desc = st.text_input("Description / Slip No.")
            fuel = "Cash Payment/Voucher"
            qty, rate = 0.0, 0.0
        else:
            with c1:
                txn_date = st.date_input("Transaction Date", date.today(), format="DD-MM-YYYY")
                party_name = st.selectbox("Customer Name", customers if customers else ["None"])
                fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel"])
                voucher_no = st.text_input("Voucher No.", value=next_voucher_no())
            with c2:
                qty = blank_number("Qty (Ltrs)", min_value=0.0)
                rate = blank_number("Rate", min_value=0.0)
                payment = blank_number("Amount Received (Rs.)", min_value=0.0)
                desc = st.text_input("Description / Slip No.")
        review_cust = st.form_submit_button("👁️ Review Entry")

    if review_cust and party_name != "None":
        st.session_state["cust_pending"] = dict(
            txn_date=str(txn_date), party_name=party_name, fuel=fuel, voucher_no=voucher_no.strip(),
            qty=qty, rate=rate, payment=payment, desc=desc, entry_kind=entry_kind)

    pend = st.session_state.get("cust_pending")
    if pend:
        debit = pend["qty"] * pend["rate"] if pend["fuel"] != "Cash Payment/Voucher" else 0.0
        credit = pend["payment"]

        if debit == 0 and credit == 0:
            st.warning("⚠️ Nothing to save — enter either the Qty/Rate for a sale or a payment amount.")

        st.markdown("<div class='review-box'><b>🔎 Review before saving</b></div>", unsafe_allow_html=True)
        st.table(pd.DataFrame([{
            "Voucher No": pend["voucher_no"], "Date": fmt_ddmmyyyy(pend["txn_date"]), "Customer": pend["party_name"],
            "Fuel": pend["fuel"], "Ltrs": f"{pend['qty']:,.2f}", "Rate": f"{pend['rate']:,.2f}",
            "Sale — Cash In (Debit)": f"{debit:,.2f}",
            "Received — Cash Out (Credit)": f"{credit:,.2f}",
            "Description": pend["desc"],
        }]))
        b1, b2 = st.columns(2)
        if b2.button("❌ Cancel", use_container_width=True):
            st.session_state.pop("cust_pending", None)
            st.rerun()
        if b1.button("✅ Confirm & Save", use_container_width=True, disabled=(debit == 0 and credit == 0)):
            token = payload_token("cust", pend["txn_date"], pend["party_name"], pend["fuel"],
                                   pend["voucher_no"], pend["qty"], pend["rate"], pend["payment"], pend["desc"])
            if already_saved(token):
                st.warning("This transaction was already saved. Duplicate save blocked.")
            else:
                execute_query(
                    """INSERT INTO ledger (txn_date,party_name,party_type,item_type,qty_ltrs,rate,debit,credit,description,voucher_no)
                       VALUES (?,?,'Customer',?,?,?,?,?,?,?)""",
                    (pend["txn_date"], pend["party_name"],
                     None if pend["fuel"] == "Cash Payment/Voucher" else pend["fuel"],
                     pend["qty"], pend["rate"], debit, credit, pend["desc"], pend["voucher_no"] or None))
                st.session_state.pop("cust_pending", None)
                st.success("✅ Customer transaction saved.")
                st.rerun()

    st.markdown("### 🕒 Last 10 Customer Entries")
    recent = read_df(
        """SELECT id AS [Entry ID], voucher_no AS [Voucher No], txn_date AS Date, party_name AS Customer,
                  item_type AS Fuel, qty_ltrs AS Ltrs, rate AS Rate,
                  debit AS [Sale — Cash In], credit AS [Received — Cash Out],
                  description AS Description
           FROM ledger WHERE party_type='Customer' ORDER BY id DESC LIMIT 10""")

    if not recent.empty:
        recent["Date"] = recent["Date"].apply(fmt_ddmmyyyy)
        st.dataframe(sr_index(recent), use_container_width=True)

# ==========================================
# MODULE 6: VENDOR ENTRY
# ==========================================
elif module == "🚛 Vendor Purchasing & Dip Stock":
    title("Vendor Purchasing & Payments")

    vendors = fetch_parties("Vendor")["Party Name"].tolist()

    vendor_name = st.selectbox("Vendor Name", vendors if vendors else ["None"], key="vend_pick")
    if vendor_name != "None":
        ob = opening_balance_now(vendor_name, "Vendor")
        st.info(f"**Opening Balance for {vendor_name}:** Rs. {ob:,.2f}")

    st.markdown("#### 1️⃣ Choose Entry Type")
    entry_kind = st.radio(
        "Entry Type",
        [
            "🚛 Fuel Purchase / Bill Entry  —  Cash In (Credit)",
            "💵 Advance / Payment to Vendor  —  Cash Out (Debit)",
            "🔄 Combined (purchase + payment on the exact same day)",
        ],
        key="vend_entry_kind",
    )

    with st.form("vendor_form"):
        c1, c2 = st.columns(2)
        if entry_kind.startswith("🚛"):
            with c1:
                txn_date = st.date_input("Tanker Unload / Bill Date", date.today(), format="DD-MM-YYYY")
                fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel"])
                voucher_no = st.text_input("Voucher No.", value=next_voucher_no())
            with c2:
                qty = blank_number("Qty Received (Ltrs)", min_value=0.0)
                rate = blank_number("Purchase Rate", min_value=0.0)
                desc = st.text_input("Invoice / Tanker No.")
            paid = 0.0
        elif entry_kind.startswith("💵"):
            with c1:
                txn_date = st.date_input("Payment Date", date.today(), format="DD-MM-YYYY")
                voucher_no = st.text_input("Voucher No.", value=next_voucher_no())
            with c2:
                paid = blank_number("Advance / Payment Paid (Rs.)", min_value=0.0)
                desc = st.text_input("Description")
            fuel = "Direct Payment"
            qty, rate = 0.0, 0.0
        else:
            with c1:
                txn_date = st.date_input("Date", date.today(), format="DD-MM-YYYY")
                fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel"])
                voucher_no = st.text_input("Voucher No.", value=next_voucher_no())
            with c2:
                qty = blank_number("Qty Received (Ltrs)", min_value=0.0)
                rate = blank_number("Purchase Rate", min_value=0.0)
                paid = blank_number("Payment Paid (Rs.)", min_value=0.0)
                desc = st.text_input("Invoice / Tanker No.")
        review_vend = st.form_submit_button("👁️ Review Entry")

    if review_vend and vendor_name != "None":
        st.session_state["vend_pending"] = dict(
            txn_date=str(txn_date), vendor_name=vendor_name, fuel=fuel, voucher_no=voucher_no.strip(),
            qty=qty, rate=rate, paid=paid, desc=desc, entry_kind=entry_kind)

    pend = st.session_state.get("vend_pending")
    if pend:
        credit = pend["qty"] * pend["rate"] if pend["fuel"] != "Direct Payment" else 0.0
        debit = pend["paid"]

        if credit == 0 and debit == 0:
            st.warning("⚠️ Nothing to save — enter either the purchase Qty/Rate or a payment amount.")

        st.markdown("<div class='review-box'><b>🔎 Review before saving</b></div>", unsafe_allow_html=True)
        st.table(pd.DataFrame([{
            "Voucher No": pend["voucher_no"], "Date": fmt_ddmmyyyy(pend["txn_date"]), "Vendor": pend["vendor_name"],
            "Fuel": pend["fuel"], "Ltrs": f"{pend['qty']:,.2f}", "Rate": f"{pend['rate']:,.2f}",
            "Purchase — Cash In (Credit)": f"{credit:,.2f}",
            "Paid — Cash Out (Debit)": f"{debit:,.2f}",
            "Description": pend["desc"],
        }]))
        b1, b2 = st.columns(2)
        if b2.button("❌ Cancel", use_container_width=True):
            st.session_state.pop("vend_pending", None)
            st.rerun()
        if b1.button("✅ Confirm & Save", use_container_width=True, disabled=(credit == 0 and debit == 0)):
            token = payload_token("vend", pend["txn_date"], pend["vendor_name"], pend["fuel"],
                                   pend["voucher_no"], pend["qty"], pend["rate"], pend["paid"], pend["desc"])
            if already_saved(token):
                st.warning("This transaction was already saved. Duplicate save blocked.")
            else:
                execute_query(
                    """INSERT INTO ledger (txn_date,party_name,party_type,item_type,qty_ltrs,rate,debit,credit,description,voucher_no)
                       VALUES (?,?,'Vendor',?,?,?,?,?,?,?)""",
                    (pend["txn_date"], pend["vendor_name"],
                     None if pend["fuel"] == "Direct Payment" else pend["fuel"],
                     pend["qty"], pend["rate"], debit, credit, pend["desc"], pend["voucher_no"] or None))
                st.session_state.pop("vend_pending", None)
                st.success("✅ Vendor transaction saved.")
                st.rerun()

    st.markdown("### 🕒 Last 10 Vendor Entries")
    recent = read_df(
        """SELECT id AS [Entry ID], voucher_no AS [Voucher No], txn_date AS Date, party_name AS Vendor,
                  item_type AS Fuel, qty_ltrs AS Ltrs, rate AS Rate,
                  debit AS [Paid — Cash Out], credit AS [Purchase — Cash In],
                  description AS Description
           FROM ledger WHERE party_type='Vendor' ORDER BY id DESC LIMIT 10""")

    if not recent.empty:
        recent["Date"] = recent["Date"].apply(fmt_ddmmyyyy)
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

    rows = read_df(q, params=params)

    if rows.empty:
        st.info("No entries found for this selection.")
    else:
        view = rows.rename(columns={
            "id": "Entry ID", "voucher_no": "Voucher No", "txn_date": "Date", "party_name": "Party Name",
            "party_type": "Type", "item_type": "Fuel", "qty_ltrs": "Ltrs",
            "rate": "Rate", "debit": "Debit", "credit": "Credit", "description": "Description",
        })
        st.dataframe(sr_index(view), use_container_width=True)

        labels = {
            f"ID {r.id} | {r.voucher_no or '-'} | {r.txn_date} | {r.party_name} | {r.item_type or '-'} | "
            f"Dr {r.debit:,.0f} / Cr {r.credit:,.0f}": int(r.id)
            for r in rows.itertuples()
        }
        picked_label = st.selectbox("Select entry to edit/delete", list(labels.keys()))
        entry_id = labels[picked_label]
        rec = rows[rows["id"] == entry_id].iloc[0]

        action = st.radio("Choose Action", ["✏️ Edit Entry", "🗑️ Delete Entry"],
                          horizontal=True, key=f"entry_action_{entry_id}")

        if action == "✏️ Edit Entry":
            with st.form(f"edit_form_{entry_id}"):
                e1, e2 = st.columns(2)
                with e1:
                    n_date = st.date_input("Date", datetime.strptime(rec["txn_date"], "%Y-%m-%d").date(), format="DD-MM-YYYY")
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
                do_update = st.form_submit_button("💾 Update Entry")

            if do_update:
                d_val, c_val = n_debit, n_credit
                if auto and n_fuel != "None (Payment Only)":
                    if p_type == "Customer":
                        d_val = n_qty * n_rate
                    else:
                        c_val = n_qty * n_rate
                execute_query(
                    """UPDATE ledger SET txn_date=?, party_name=?, item_type=?, qty_ltrs=?, rate=?,
                              debit=?, credit=?, description=?, voucher_no=? WHERE id=?""",
                    (str(n_date), n_party,
                     None if n_fuel == "None (Payment Only)" else n_fuel,
                     n_qty, n_rate, d_val, c_val, n_desc, n_voucher.strip() or None, entry_id))
                st.success(f"✅ Entry ID {entry_id} updated.")
                st.rerun()

        else:
            st.warning(f"You are about to delete: {picked_label}")
            sure = st.checkbox("Yes, I am sure", key=f"sure_{entry_id}")
            if st.button("🗑️ Delete Entry", disabled=not sure):
                execute_query("DELETE FROM ledger WHERE id = ?", (entry_id,))
                resequence_ids("ledger")
                st.success("✅ Entry deleted and IDs re-sequenced.")
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

    stock_summary = read_df(
        """SELECT item_type AS [Fuel Item], SUM(purchase_qty) AS [Total Purchased],
                  SUM(sales_qty) AS [Total Stock Sales], SUM(dip_diff) AS [Total Dip Variance]
           FROM stock_register GROUP BY item_type""")
    ledger_summary = read_df(
        """SELECT item_type AS [Fuel Item], SUM(qty_ltrs) AS [Total Ledger Sales]
           FROM ledger WHERE party_type='Customer' AND item_type IS NOT NULL GROUP BY item_type""")

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

    action = st.radio("Choose Action", ["➕ Add Party", "✏️ Edit Party", "❌ Remove Party"],
                      horizontal=True, key="master_setup_action")

    if action == "➕ Add Party":
        with st.form("add_party_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Party / Vendor Name")
                p_type = st.selectbox("Type", ["Customer", "Vendor"])
            with c2:
                op_bal = blank_number("Opening Balance (Rs.)")
                phone = st.text_input("Phone Number")
            add_it = st.form_submit_button("➕ Save Party")

        if add_it:
            if not name.strip():
                st.error("⚠️ Party / Vendor Name is required.")
            else:
                token = payload_token("party", name.strip(), p_type, op_bal, phone)
                if already_saved(token):
                    st.warning("Already saved. Duplicate blocked.")
                else:
                    try:
                        execute_query("INSERT INTO parties (name,type,opening_balance,phone) VALUES (?,?,?,?)",
                                      (name.strip(), p_type, op_bal, phone))
                        st.success(f"✅ Party '{name}' added.")
                        st.rerun()
                    except Exception:
                        st.error("⚠️ A party with this name already exists or query error.")

    elif action == "✏️ Edit Party":
        allp = fetch_parties()
        if allp.empty:
            st.info("No parties yet — add one first.")
        else:
            sel = st.selectbox("Select Party", allp["Party Name"].tolist(), key="edit_party_sel")
            row = allp[allp["Party Name"] == sel].iloc[0]
            with st.form("edit_party_form"):
                c1, c2 = st.columns(2)
                new_name = c1.text_input("Name", value=row["Party Name"])
                new_type = c1.selectbox("Type", ["Customer", "Vendor"],
                                        index=0 if row["Type"] == "Customer" else 1)
                new_bal = c2.number_input("Opening Balance", value=float(row["Opening Balance"] or 0.0), step=100.0)
                new_phone = c2.text_input("Phone", value=row["Phone"] or "")
                upd = st.form_submit_button("💾 Update Party")

            if upd:
                if not new_name.strip():
                    st.error("⚠️ Name cannot be empty.")
                else:
                    try:
                        execute_query("UPDATE ledger SET party_name=?, party_type=? WHERE party_name=?",
                                      (new_name.strip(), new_type, sel))
                        execute_query("UPDATE parties SET name=?, type=?, opening_balance=?, phone=? WHERE name=?",
                                      (new_name.strip(), new_type, new_bal, new_phone, sel))
                        st.success(f"✅ Party '{sel}' updated.")
                        st.rerun()
                    except Exception:
                        st.error(f"⚠️ Another party is already named '{new_name.strip()}'.")

    else:
        allp = fetch_parties()
        if allp.empty:
            st.info("No parties yet.")
        else:
            to_del = st.selectbox("Select Party to Remove", allp["Party Name"].tolist(), key="del_party_sel")
            cnt_df = read_df("SELECT COUNT(*) c FROM ledger WHERE party_name=?", params=(to_del,))
            cnt = cnt_df.iloc[0]["c"] if not cnt_df.empty else 0
            if cnt:
                st.warning(f"⚠️ This party has {cnt} ledger entries. Deleting the party keeps those entries.")
            sure = st.checkbox(f"Yes, remove '{to_del}'", key=f"sure_party_{to_del}")
            if st.button("❌ Confirm Delete Party", disabled=not sure):
                execute_query("DELETE FROM parties WHERE name = ?", (to_del,))
                st.success(f"✅ Party '{to_del}' removed.")
                st.rerun()

    st.markdown("### 📋 Active Master List")
    st.dataframe(sr_index(fetch_parties()), use_container_width=True)

# ==========================================
# MODULE 10: BACKUP & RESTORE
# ==========================================
elif module == "💾 Backup & System Recovery":
    title("Database Backup & System Recovery")

    backup = {
        "parties": read_df("SELECT * FROM parties").to_dict(orient="records"),
        "stock_register": read_df("SELECT * FROM stock_register").to_dict(orient="records"),
        "ledger": read_df("SELECT * FROM ledger").to_dict(orient="records"),
    }

    st.download_button("💾 Download JSON Backup", json.dumps(backup, indent=2),
                       file_name=f"FD_CNG_Backup_{date.today()}.json", mime="application/json")

    st.markdown("---")
    st.markdown("### 📤 Restore System Data")
    up = st.file_uploader("Upload JSON Backup File", type=["json"])

    if up is not None:
        sure = st.checkbox("I understand this will replace all current data")
        if st.button("⚠️ Confirm System Restore", disabled=not sure):
            data = json.load(up)
            execute_query("DELETE FROM parties")
            execute_query("DELETE FROM stock_register")
            execute_query("DELETE FROM ledger")

            for p in data.get("parties", []):
                execute_query("INSERT INTO parties (id,name,type,opening_balance,phone) VALUES (?,?,?,?,?)",
                              (p.get("id"), p.get("name"), p.get("type"),
                               p.get("opening_balance") or 0.0, p.get("phone") or ""))

            stock_cols = ["id", "entry_date", "item_type", "opening_stock", "rate", "opening_amount",
                          "purchase_qty", "purchase_rate", "purchase_amount", "total_purchase_amount",
                          "avg_rate", "available_stock", "sales_qty", "sales_rate", "sales_amount",
                          "total_sales_amount", "closing_amount", "closing_stock", "dip_diff",
                          "actual_stock", "actual_amount"]
            for s in data.get("stock_register", []):
                execute_query(
                    f"INSERT INTO stock_register ({','.join(stock_cols)}) VALUES ({','.join('?' * len(stock_cols))})",
                    tuple(s.get(c) for c in stock_cols))

            for l in data.get("ledger", []):
                execute_query(
                    """INSERT INTO ledger (id,txn_date,party_name,party_type,item_type,qty_ltrs,rate,debit,credit,description,voucher_no)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (l.get("id"), l.get("txn_date"), l.get("party_name"), l.get("party_type"),
                     l.get("item_type"), l.get("qty_ltrs", 0.0), l.get("rate", 0.0),
                     l.get("debit", 0.0), l.get("credit", 0.0), l.get("description", ""),
                     l.get("voucher_no")))

            st.success("✅ System restored successfully.")
            st.rerun()
