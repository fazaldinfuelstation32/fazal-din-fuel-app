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
        .live-preview {
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
            border: 2px solid #1c8b4e; border-radius: 10px;
            padding: 14px 18px; margin: 10px 0 16px 0;
            box-shadow: 0 2px 8px rgba(28,139,78,.15);
        }
        .live-preview h5 {
            margin: 0 0 10px 0; color: #0b3d24; font-size: 13px;
            font-weight: 800; text-transform: uppercase; letter-spacing: .8px;
        }
        .live-preview table { width: 100%; border-collapse: collapse; }
        .live-preview td {
            padding: 5px 8px; font-size: 13.5px; color: #0b3d24;
            border-bottom: 1px dashed #a7d4b8;
        }
        .live-preview td:last-child { text-align: right; font-weight: 700; color: #0b5d34; }
        .live-preview td:first-child { color: #166534; font-weight: 600; }
        .live-preview tr:last-child td { border-bottom: none; }
        .live-preview .highlight td {
            background: #fef3c7; font-weight: 800; color: #92400e;
            border-bottom: 2px solid #f59e0b;
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

_db_lock = threading.Lock()


@st.cache_resource(show_spinner=False)
def get_db_connection():
    turso_url = st.secrets.get("turso", {}).get("TURSO_DATABASE_URL")
    turso_token = st.secrets.get("turso", {}).get("TURSO_AUTH_TOKEN")

    if HAS_TURSO and turso_url and turso_token:
        try:
            url = turso_url.replace("libsql://", "https://")
            conn = libsql.create_client_sync(url=url, auth_token=turso_token)
            return conn
        except Exception as e:
            st.error(f"⚠️ Turso Sync Error: {e}. Falling back to local SQLite.")

    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
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

    # Index for fast lookups
    try:
        execute_query("CREATE INDEX IF NOT EXISTS idx_ledger_party ON ledger(party_name, party_type)")
        execute_query("CREATE INDEX IF NOT EXISTS idx_ledger_date ON ledger(txn_date)")
        execute_query("CREATE INDEX IF NOT EXISTS idx_stock_date ON stock_register(entry_date, item_type)")
    except Exception:
        pass

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


def fetch_parties(p_type=None) -> pd.DataFrame:
    base = ("SELECT id, name AS [Party Name], type AS [Type], "
            "opening_balance AS [Opening Balance], phone AS [Phone] FROM parties ")
    if p_type:
        df = read_df(base + "WHERE type = ? ORDER BY name ASC", params=(p_type,))
    else:
        df = read_df(base + "ORDER BY type ASC, name ASC")
    return df


@st.cache_data(ttl=60, show_spinner=False)
def _cached_party_names(p_type: str):
    df = read_df("SELECT name FROM parties WHERE type = ? ORDER BY name ASC", params=(p_type,))
    return df["name"].tolist() if not df.empty else []


def fetch_party_names(p_type: str):
    return _cached_party_names(p_type)


def calculate_party_balances(party_type: str) -> pd.DataFrame:
    parties = read_df("SELECT name, opening_balance FROM parties WHERE type = ?", params=(party_type,))
    if parties.empty:
        return pd.DataFrame()
    parties["opening_balance"] = parties["opening_balance"].fillna(0.0)

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
    """Re-sequence IDs. Fast version with a single CASE-based UPDATE for SQLite."""
    date_col = "txn_date" if table == "ledger" else "entry_date"
    df = read_df(f"SELECT id FROM {table} ORDER BY {date_col} ASC, id ASC")
    if df.empty:
        return
    ids = df["id"].tolist()
    conn = get_db_connection()

    if _is_libsql(conn):
        with _db_lock:
            for old in ids:
                conn.execute(f"UPDATE {table} SET id = ? WHERE id = ?", (old + 1_000_000, old))
            for new, old in enumerate(ids, start=1):
                conn.execute(f"UPDATE {table} SET id = ? WHERE id = ?", (new, old + 1_000_000))
    else:
        with _db_lock:
            cur = conn.cursor()
            # Build single CASE statement to update all IDs at once
            case_sql = "CASE id " + " ".join(f"WHEN {old} THEN {new}" for new, old in enumerate(ids, start=1)) + " END"
            cur.execute(f"UPDATE {table} SET id = {case_sql} WHERE id IN ({','.join(map(str, ids))})")
            conn.commit()


def safe_float(raw, min_value=None):
    raw = (raw or "").strip()
    if raw == "":
        return 0.0
    try:
        val = float(raw)
    except ValueError:
        return 0.0
    if min_value is not None and val < min_value:
        return min_value
    return val


def blank_number(label: str, min_value=None, help=None, key=None) -> float:
    raw = st.text_input(label, value="", placeholder="0", help=help, key=key)
    raw = (raw or "").strip()
    if raw == "":
        return 0.0
    try:
        val = float(raw)
    except ValueError:
        st.error(f"⚠️ '{label}' must contain a number only (e.g. 123.45).")
        return 0.0
    if min_value is not None and val < min_value:
        st.warning(f"⚠️ '{label}' cannot be less than {min_value} — using {min_value}.")
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


def last_avg_rate(item_type: str) -> float:
    df = read_df("""SELECT avg_rate, rate, closing_amount, closing_stock
                    FROM stock_register
                    WHERE item_type = ? ORDER BY entry_date DESC, id DESC LIMIT 1""",
                 params=(item_type,))
    if df.empty:
        return 0.0
    row = df.iloc[0]

    avg_r = float(row["avg_rate"] or 0.0)
    if avg_r > 0:
        return avg_r

    op_r = float(row["rate"] or 0.0)
    if op_r > 0:
        return op_r

    cs = float(row["closing_stock"] or 0.0)
    ca = float(row["closing_amount"] or 0.0)
    if cs > 0 and ca > 0:
        return ca / cs

    return 0.0


def next_voucher_no() -> str:
    df = read_df("SELECT voucher_no FROM ledger WHERE voucher_no IS NOT NULL ORDER BY id DESC LIMIT 50")
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


def live_preview(rows):
    html = "<div class='live-preview'><h5>⚡ Live Preview</h5><table>"
    for k, v in rows:
        cls = " class='highlight'" if k.startswith("★") else ""
        k_clean = k.replace("★ ", "")
        html += f"<tr{cls}><td>{k_clean}</td><td>{v}</td></tr>"
    html += "</table></div>"
    st.markdown(html, unsafe_allow_html=True)


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
            window.onload = function () {{ window.focus(); window.print(); }};
            window.onafterprint = function () {{ window.close(); }};
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
            if (w) {{ w.document.open(); w.document.write(doc); w.document.close(); }}
        }};
    </script>
    """
    components.html(trigger_html, height=60)


def render_print_stock(from_date, to_date, item_filter="All"):
    q = """SELECT id, entry_date, item_type, opening_stock, rate, purchase_qty, purchase_rate,
                  sales_qty, sales_rate, avg_rate, closing_stock, actual_stock, dip_diff
           FROM stock_register WHERE entry_date BETWEEN ? AND ?"""
    params = [str(from_date), str(to_date)]
    if item_filter != "All":
        q += " AND item_type = ?"
        params.append(item_filter)
    q += " ORDER BY entry_date ASC, id ASC"

    df = read_df(q, params=params)

    rows_html = ""
    for i, (_, r) in enumerate(df.iterrows(), start=1):
        dip_color = "#dc2626" if (r['dip_diff'] or 0) < 0 else ("#16a34a" if (r['dip_diff'] or 0) > 0 else "#0b3d24")
        rows_html += f"""
        <tr>
            <td>{i}</td>
            <td>{fmt_ddmmyyyy(r['entry_date'])}</td>
            <td>{r['item_type']}</td>
            <td class="num">{(r['opening_stock'] or 0):,.2f}</td>
            <td class="num">{(r['rate'] or 0):,.2f}</td>
            <td class="num">{(r['purchase_qty'] or 0):,.2f}</td>
            <td class="num">{(r['purchase_rate'] or 0):,.2f}</td>
            <td class="num">{(r['sales_qty'] or 0):,.2f}</td>
            <td class="num">{(r['sales_rate'] or 0):,.2f}</td>
            <td class="num">{(r['avg_rate'] or 0):,.4f}</td>
            <td class="num">{(r['closing_stock'] or 0):,.2f}</td>
            <td class="num" style="color:{dip_color};font-weight:700;">{(r['dip_diff'] or 0):+,.2f}</td>
            <td class="num">{(r['actual_stock'] or 0):,.2f}</td>
        </tr>"""

    from_str = fmt_ddmmyyyy(from_date)
    to_str = fmt_ddmmyyyy(to_date)

    print_doc = f"""<!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <title>Stock Register {from_str} to {to_str}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: Arial, Helvetica, sans-serif; color:#0b3d24; margin:0; padding:0; }}
        .sheet {{ padding: 16px 20px; }}
        .head {{
            background: linear-gradient(90deg,#0b5d34,#2e7d32);
            color:#fff; padding:14px 18px; border-radius:8px; border-left:8px solid #f57c00;
            margin-bottom:14px;
        }}
        .head h2 {{ margin:0; font-size:20px; }}
        .head p {{ margin:2px 0 0; font-size:13px; opacity:.9; }}
        .info {{ display:flex; gap:20px; margin-bottom:12px; font-size:13px; }}
        .info div {{ background:#f4f7f5; border:1px solid #e3e8ef; border-radius:6px; padding:6px 12px; }}
        table {{ width:100%; border-collapse: collapse; font-size:11.5px; }}
        th {{ background:#0b3d24; color:#fff; padding:6px 6px; text-align:left; }}
        td {{ padding:5px 6px; border-bottom:1px solid #e3e8ef; }}
        td.num, th.num {{ text-align:right; }}
        tr:nth-child(even) {{ background:#f8faf9; }}
        @page {{ margin: 8mm; size: auto landscape; }}
    </style>
    </head>
    <body>
        <div class="sheet">
            <div class="head">
                <h2>⛽ FD CNG Fuel Station — Daily Stock Register</h2>
                <p>Report Period: {from_str} to {to_str} &nbsp;|&nbsp; Fuel Filter: {item_filter}</p>
            </div>
            <div class="info">
                <div><b>Total Entries:</b> {len(df)}</div>
                <div><b>Generated:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}</div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Sr.</th><th>Date</th><th>Fuel</th>
                        <th class="num">Opening</th><th class="num">Op Rate</th>
                        <th class="num">Purch Qty</th><th class="num">Purch Rate</th>
                        <th class="num">Sales Qty</th><th class="num">Sales Rate</th>
                        <th class="num">Avg Rate</th><th class="num">Closing</th>
                        <th class="num">Dip Diff</th><th class="num">Actual</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html if rows_html else '<tr><td colspan="13" style="text-align:center;">No entries in this range</td></tr>'}
                </tbody>
            </table>
        </div>
        <script>
            window.onload = function () {{ window.focus(); window.print(); }};
            window.onafterprint = function () {{ window.close(); }};
        </script>
    </body>
    </html>
    """

    safe_doc = json.dumps(print_doc).replace("</script>", "<\\/script>")

    trigger_html = f"""
    <button id="printStockBtn" style="
        background:linear-gradient(90deg,#1c8b4e,#2e7d32); color:#fff; border:none;
        padding:10px 22px; border-radius:8px; font-weight:bold; font-size:14px;
        cursor:pointer;">🖨️ Print Stock Register</button>
    <script>
        document.getElementById('printStockBtn').onclick = function () {{
            var doc = {safe_doc};
            var w = window.open('', '_blank');
            if (w) {{ w.document.open(); w.document.write(doc); w.document.close(); }}
        }};
    </script>
    """
    components.html(trigger_html, height=60)


# ==========================================
# 5. SIDEBAR NAVIGATION
# ==========================================
st.sidebar.markdown("## ⛽ FD CNG Station")

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
    plist = fetch_party_names(p_type)
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
# MODULE 4: DAILY STOCK REGISTER (Direct Save, No Review)
# ==========================================
elif module == "🛢️ Daily Stock Register":
    title("Daily Stock Register")

    st.caption("Dip Difference = Shortage/Excess during physical dip check. "
               "Opening Stock and Opening Rate are auto-filled from the last saved entry.")

    item_type = st.selectbox("Fuel Item", ["Petrol", "Diesel"], key="stock_item_type_pick")

    if "stock_form_version" not in st.session_state:
        st.session_state["stock_form_version"] = 0

    fver = st.session_state["stock_form_version"]

    cache_key = f"stk_cache_{item_type}_{fver}"
    if st.session_state.get("stk_last_key") != cache_key:
        st.session_state["stk_suggested_opening"] = last_closing_stock(item_type)
        st.session_state["stk_suggested_rate"] = last_avg_rate(item_type)
        st.session_state["stk_last_key"] = cache_key

    suggested_opening = st.session_state["stk_suggested_opening"]
    suggested_rate = st.session_state["stk_suggested_rate"]

    st.caption(f"Auto-filled Opening Stock = {suggested_opening:,.2f} Ltrs  |  "
               f"Auto Opening Rate = Rs. {suggested_rate:,.4f}")

    with st.form("stock_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            e_date = st.date_input("Entry Date", date.today(), format="DD-MM-YYYY", key=f"stk_date_{fver}")
            st.text_input("Fuel Item", value=item_type, disabled=True, key=f"stk_item_{fver}")
            op_stock = st.number_input("Opening Stock (Ltrs)", value=float(suggested_opening),
                                        step=1.0, key=f"stk_opstk_{fver}")
            op_rate_str = st.text_input("Opening Rate",
                                         value=f"{suggested_rate:.4f}" if suggested_rate else "",
                                         placeholder="0", key=f"stk_oprate_{fver}")
        with c2:
            p_qty_str = st.text_input("Purchase Qty (Ltrs)", value="", placeholder="0", key=f"stk_pqty_{fver}")
            p_rate_str = st.text_input("Purchase Rate", value="", placeholder="0", key=f"stk_prate_{fver}")
            s_qty_str = st.text_input("Sales Qty (Ltrs)", value="", placeholder="0", key=f"stk_sqty_{fver}")
            s_rate_str = st.text_input("Sales Rate", value="", placeholder="0", key=f"stk_srate_{fver}")
        with c3:
            dip_checked = st.checkbox("Physical Dip Check done today?", value=True, key=f"stk_dipchk_{fver}")
            dip_str = st.text_input("Dip Shortage / Excess (+/- Ltrs)", value="", placeholder="0", key=f"stk_dip_{fver}")

        submitted = st.form_submit_button("💾 Save Stock Entry", use_container_width=True)

    # Live parse
    op_rate = safe_float(op_rate_str)
    p_qty = safe_float(p_qty_str)
    p_rate = safe_float(p_rate_str)
    s_qty = safe_float(s_qty_str)
    s_rate = safe_float(s_rate_str)
    dip_input = safe_float(dip_str)

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

    k = stock_calc(op_stock, op_rate, p_qty, p_rate, s_qty, s_rate, dip_input, dip_checked)

    # Live Preview
    if any([op_stock, op_rate, p_qty, p_rate, s_qty, s_rate, dip_input]):
        sign = "SHORTAGE (-)" if k["dip_diff"] < 0 else ("EXCESS (+)" if k["dip_diff"] > 0 else "NO DIFFERENCE")
        live_preview([
            ("Date", fmt_ddmmyyyy(e_date)),
            ("Fuel Item", item_type),
            ("Opening Amount", f"Rs. {k['op_amount']:,.2f}"),
            ("Purchase Amount", f"Rs. {k['p_amount']:,.2f}"),
            ("Total Purchase Amount", f"Rs. {k['tot_p_amount']:,.2f}"),
            ("Available Stock", f"{k['avail']:,.2f} Ltrs"),
            ("★ Average Rate", f"Rs. {k['avg_rate']:,.4f}"),
            ("Sales Amount (at Sales Rate)", f"Rs. {k['s_amount']:,.2f}"),
            ("Total Sales Amount (at Avg)", f"Rs. {k['tot_s_amount']:,.2f}"),
            ("Closing Amount", f"Rs. {k['closing_amount']:,.2f}"),
            ("Closing Stock", f"{k['closing_stock']:,.2f} Ltrs"),
            ("Dip Difference", f"{k['dip_diff']:+,.2f} Ltrs  ({sign})"),
            ("Dip Diff Amount", f"Rs. {k['dip_amount']:+,.2f}"),
            ("Actual Stock", f"{k['actual_stock']:,.2f} Ltrs"),
            ("★ Final Closing Stock (Next Opening)", f"{k['final_closing']:,.2f} Ltrs"),
        ])

    if submitted:
        if op_stock == 0 and p_qty == 0 and s_qty == 0:
            st.warning("⚠️ Nothing to save — enter Opening Stock, Purchase Qty, or Sales Qty.")
        else:
            token = payload_token("stock", e_date, item_type, op_stock, op_rate, p_qty, p_rate,
                                   s_qty, s_rate, dip_input, dip_checked)
            dup_df = read_df("SELECT COUNT(*) c FROM stock_register WHERE entry_date=? AND item_type=?",
                             params=(str(e_date), item_type))
            dup = dup_df.iloc[0]["c"] if not dup_df.empty else 0

            if dup:
                st.warning(f"⚠️ {dup} entry already exists for {e_date} / {item_type}. Please delete the old entry first or change the date.")
            else:
                execute_query(
                    """INSERT INTO stock_register (
                        entry_date,item_type,opening_stock,rate,opening_amount,purchase_qty,purchase_rate,
                        purchase_amount,total_purchase_amount,avg_rate,available_stock,sales_qty,sales_rate,
                        sales_amount,total_sales_amount,closing_amount,closing_stock,dip_diff,actual_stock,actual_amount)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (str(e_date), item_type, op_stock, op_rate, k["op_amount"],
                     p_qty, p_rate, k["p_amount"], k["tot_p_amount"], k["avg_rate"],
                     k["avail"], s_qty, s_rate, k["s_amount"], k["tot_s_amount"],
                     k["closing_amount"], k["closing_stock"], k["dip_diff"], k["actual_stock"], k["act_amount"]),
                )
                st.session_state["stock_form_version"] += 1
                st.success("✅ Daily stock entry saved. Form cleared.")
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
           FROM stock_register ORDER BY entry_date ASC, id ASC""")

    if not stock_df.empty:
        stock_df["Dip Status"] = stock_df["Dip Difference"].apply(
            lambda x: "Shortage (-)" if x < 0 else ("Excess (+)" if x > 0 else "Balanced"))
        st.dataframe(sr_index(stock_df), use_container_width=True)
        download_csv(sr_index(stock_df), "stock_register.csv")

        st.markdown("---")
        st.markdown("### 🖨️ Print Stock Register (Date Range)")
        pp1, pp2, pp3 = st.columns(3)
        pr_from = pp1.date_input("Print From Date", date(date.today().year, 1, 1), format="DD-MM-YYYY", key="stk_pr_from")
        pr_to = pp2.date_input("Print To Date", date.today(), format="DD-MM-YYYY", key="stk_pr_to")
        pr_item = pp3.selectbox("Fuel Filter", ["All", "Petrol", "Diesel"], key="stk_pr_item")
        if st.button("🖨️ Generate Print Preview", key="stk_print_btn"):
            render_print_stock(pr_from, pr_to, pr_item)
    else:
        st.info("No stock records yet.")

# ==========================================
# MODULE 5: CUSTOMER ENTRY (Direct Save, No Review)
# ==========================================
elif module == "💳 Party Daily Sale & Credit Entry":
    title("Customer Credit Sale & Voucher Entry")

    customers = fetch_party_names("Customer")

    st.markdown("#### 1️⃣ Choose Entry Type")
    entry_kind = st.radio(
        "Entry Type",
        [
            "🧾 Fuel Sale Entry  —  Cash In (Debit)",
            "💵 Payment Received from Customer  —  Cash Out (Credit)",
            "🔄 Combined (sale + payment on the same day)",
        ],
        key="cust_entry_kind",
    )

    if "cust_form_ver" not in st.session_state:
        st.session_state["cust_form_ver"] = 0
    cver = st.session_state["cust_form_ver"]

    with st.form("credit_sale_form"):
        c1, c2 = st.columns(2)
        if entry_kind.startswith("🧾"):
            with c1:
                txn_date = st.date_input("Sale / Delivery Date", date.today(), format="DD-MM-YYYY", key=f"c_date_{cver}")
                party_name = st.selectbox("Customer Name", customers if customers else ["None"], key=f"c_party_{cver}")
                fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel"], key=f"c_fuel_{cver}")
                voucher_no = st.text_input("Voucher No.", value=next_voucher_no(), key=f"c_vno_{cver}")
            with c2:
                qty_str = st.text_input("Qty (Ltrs)", value="", placeholder="0", key=f"c_qty_{cver}")
                rate_str = st.text_input("Rate", value="", placeholder="0", key=f"c_rate_{cver}")
                desc = st.text_input("Description / Slip No.", key=f"c_desc_{cver}")
            payment = 0.0
        elif entry_kind.startswith("💵"):
            with c1:
                txn_date = st.date_input("Payment Date", date.today(), format="DD-MM-YYYY", key=f"c_date_{cver}")
                party_name = st.selectbox("Customer Name", customers if customers else ["None"], key=f"c_party_{cver}")
                voucher_no = st.text_input("Voucher No.", value=next_voucher_no(), key=f"c_vno_{cver}")
            with c2:
                pay_str = st.text_input("Amount Received (Rs.)", value="", placeholder="0", key=f"c_pay_{cver}")
                desc = st.text_input("Description / Slip No.", key=f"c_desc_{cver}")
            fuel = "Cash Payment/Voucher"
            qty_str, rate_str = "", ""
            payment = safe_float(pay_str)
        else:
            with c1:
                txn_date = st.date_input("Transaction Date", date.today(), format="DD-MM-YYYY", key=f"c_date_{cver}")
                party_name = st.selectbox("Customer Name", customers if customers else ["None"], key=f"c_party_{cver}")
                fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel"], key=f"c_fuel_{cver}")
                voucher_no = st.text_input("Voucher No.", value=next_voucher_no(), key=f"c_vno_{cver}")
            with c2:
                qty_str = st.text_input("Qty (Ltrs)", value="", placeholder="0", key=f"c_qty_{cver}")
                rate_str = st.text_input("Rate", value="", placeholder="0", key=f"c_rate_{cver}")
                pay_str = st.text_input("Amount Received (Rs.)", value="", placeholder="0", key=f"c_pay_{cver}")
                desc = st.text_input("Description / Slip No.", key=f"c_desc_{cver}")
            payment = safe_float(pay_str)
        submitted = st.form_submit_button("💾 Save Customer Entry", use_container_width=True)

    qty = safe_float(qty_str)
    rate = safe_float(rate_str)
    debit = qty * rate if fuel != "Cash Payment/Voucher" else 0.0
    credit = payment

    if any([qty, rate, payment]):
        live_preview([
            ("Date", fmt_ddmmyyyy(txn_date)),
            ("Customer", party_name),
            ("Fuel", fuel),
            ("Voucher No.", voucher_no),
            ("Qty (Ltrs)", f"{qty:,.2f}"),
            ("Rate", f"{rate:,.2f}"),
            ("★ Sale — Cash In (Debit)", f"Rs. {debit:,.2f}"),
            ("★ Received — Cash Out (Credit)", f"Rs. {credit:,.2f}"),
        ])

    if submitted:
        if party_name == "None":
            st.error("⚠️ Please select a customer.")
        elif debit == 0 and credit == 0:
            st.warning("⚠️ Nothing to save — enter Qty/Rate for a sale or a payment amount.")
        else:
            execute_query(
                """INSERT INTO ledger (txn_date,party_name,party_type,item_type,qty_ltrs,rate,debit,credit,description,voucher_no)
                   VALUES (?,?,'Customer',?,?,?,?,?,?,?)""",
                (str(txn_date), party_name,
                 None if fuel == "Cash Payment/Voucher" else fuel,
                 qty, rate, debit, credit, desc, voucher_no.strip() or None))
            st.session_state["cust_form_ver"] += 1
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
# MODULE 6: VENDOR ENTRY (Direct Save, No Review)
# ==========================================
elif module == "🚛 Vendor Purchasing & Dip Stock":
    title("Vendor Purchasing & Payments")

    vendors = fetch_party_names("Vendor")

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
            "🔄 Combined (purchase + payment on the same day)",
        ],
        key="vend_entry_kind",
    )

    if "vend_form_ver" not in st.session_state:
        st.session_state["vend_form_ver"] = 0
    vver = st.session_state["vend_form_ver"]

    with st.form("vendor_form"):
        c1, c2 = st.columns(2)
        if entry_kind.startswith("🚛"):
            with c1:
                txn_date = st.date_input("Tanker Unload / Bill Date", date.today(), format="DD-MM-YYYY", key=f"v_date_{vver}")
                fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel"], key=f"v_fuel_{vver}")
                voucher_no = st.text_input("Voucher No.", value=next_voucher_no(), key=f"v_vno_{vver}")
            with c2:
                qty_str = st.text_input("Qty Received (Ltrs)", value="", placeholder="0", key=f"v_qty_{vver}")
                rate_str = st.text_input("Purchase Rate", value="", placeholder="0", key=f"v_rate_{vver}")
                desc = st.text_input("Invoice / Tanker No.", key=f"v_desc_{vver}")
            paid = 0.0
        elif entry_kind.startswith("💵"):
            with c1:
                txn_date = st.date_input("Payment Date", date.today(), format="DD-MM-YYYY", key=f"v_date_{vver}")
                voucher_no = st.text_input("Voucher No.", value=next_voucher_no(), key=f"v_vno_{vver}")
            with c2:
                paid_str = st.text_input("Advance / Payment Paid (Rs.)", value="", placeholder="0", key=f"v_paid_{vver}")
                desc = st.text_input("Description", key=f"v_desc_{vver}")
            fuel = "Direct Payment"
            qty_str, rate_str = "", ""
            paid = safe_float(paid_str)
        else:
            with c1:
                txn_date = st.date_input("Date", date.today(), format="DD-MM-YYYY", key=f"v_date_{vver}")
                fuel = st.selectbox("Fuel Item", ["Petrol", "Diesel"], key=f"v_fuel_{vver}")
                voucher_no = st.text_input("Voucher No.", value=next_voucher_no(), key=f"v_vno_{vver}")
            with c2:
                qty_str = st.text_input("Qty Received (Ltrs)", value="", placeholder="0", key=f"v_qty_{vver}")
                rate_str = st.text_input("Purchase Rate", value="", placeholder="0", key=f"v_rate_{vver}")
                paid_str = st.text_input("Payment Paid (Rs.)", value="", placeholder="0", key=f"v_paid_{vver}")
                desc = st.text_input("Invoice / Tanker No.", key=f"v_desc_{vver}")
            paid = safe_float(paid_str)
        submitted = st.form_submit_button("💾 Save Vendor Entry", use_container_width=True)

    qty = safe_float(qty_str)
    rate = safe_float(rate_str)
    credit = qty * rate if fuel != "Direct Payment" else 0.0
    debit = paid

    if any([qty, rate, paid]):
        live_preview([
            ("Date", fmt_ddmmyyyy(txn_date)),
            ("Vendor", vendor_name),
            ("Fuel", fuel),
            ("Voucher No.", voucher_no),
            ("Qty (Ltrs)", f"{qty:,.2f}"),
            ("Rate", f"{rate:,.2f}"),
            ("★ Purchase — Cash In (Credit)", f"Rs. {credit:,.2f}"),
            ("★ Paid — Cash Out (Debit)", f"Rs. {debit:,.2f}"),
        ])

    if submitted:
        if vendor_name == "None":
            st.error("⚠️ Please select a vendor.")
        elif credit == 0 and debit == 0:
            st.warning("⚠️ Nothing to save — enter purchase Qty/Rate or a payment amount.")
        else:
            execute_query(
                """INSERT INTO ledger (txn_date,party_name,party_type,item_type,qty_ltrs,rate,debit,credit,description,voucher_no)
                   VALUES (?,?,'Vendor',?,?,?,?,?,?,?)""",
                (str(txn_date), vendor_name,
                 None if fuel == "Direct Payment" else fuel,
                 qty, rate, debit, credit, desc, voucher_no.strip() or None))
            st.session_state["vend_form_ver"] += 1
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
# MODULE 7: EDIT / DELETE ENTRIES (With Stock Register)
# ==========================================
elif module == "✏️ Edit / Manage Entries":
    title("Edit / Delete Entries")

    tab_ledger, tab_stock = st.tabs(["📒 Ledger Entries", "🛢️ Stock Register Entries"])

    # ========== LEDGER TAB ==========
    with tab_ledger:
        f1, f2, f3 = st.columns(3)
        p_type = f1.selectbox("Party Type", ["Customer", "Vendor"], key="edit_p_type")
        names = ["— All —"] + fetch_party_names(p_type)
        sel_party = f2.selectbox("Party Name", names, key="edit_party_sel2")
        search = f3.text_input("Search in Description / Date", key="edit_search")

        q = "SELECT * FROM ledger WHERE party_type = ?"
        params = [p_type]
        if sel_party != "— All —":
            q += " AND party_name = ?"
            params.append(sel_party)
        if search.strip():
            q += " AND (IFNULL(description,'') LIKE ? OR txn_date LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        q += " ORDER BY txn_date DESC, id DESC LIMIT 500"

        rows = read_df(q, params=params)

        if rows.empty:
            st.info("No ledger entries found for this selection.")
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
            picked_label = st.selectbox("Select ledger entry to edit/delete", list(labels.keys()), key="pick_ledger")
            entry_id = labels[picked_label]
            rec = rows[rows["id"] == entry_id].iloc[0]

            action = st.radio("Choose Action", ["✏️ Edit Entry", "🗑️ Delete Entry"],
                              horizontal=True, key=f"entry_action_{entry_id}")

            if action == "✏️ Edit Entry":
                with st.form(f"edit_form_{entry_id}"):
                    e1, e2 = st.columns(2)
                    with e1:
                        n_date = st.date_input("Date", datetime.strptime(rec["txn_date"], "%Y-%m-%d").date(),
                                                format="DD-MM-YYYY", key=f"ed_date_{entry_id}")
                        party_options = fetch_party_names(p_type)
                        n_party = st.selectbox("Party Name", party_options,
                                               index=party_options.index(rec["party_name"])
                                               if rec["party_name"] in party_options else 0,
                                               key=f"ed_party_{entry_id}")
                        fuel_options = ["Petrol", "Diesel", "None (Payment Only)"]
                        cur_fuel = rec["item_type"] if rec["item_type"] in ("Petrol", "Diesel") else "None (Payment Only)"
                        n_fuel = st.selectbox("Fuel Item", fuel_options, index=fuel_options.index(cur_fuel),
                                              key=f"ed_fuel_{entry_id}")
                        n_voucher = st.text_input("Voucher No.", value=rec["voucher_no"] or "", key=f"ed_vno_{entry_id}")
                    with e2:
                        n_qty = st.number_input("Ltrs", min_value=0.0, value=float(rec["qty_ltrs"]), step=1.0, key=f"ed_qty_{entry_id}")
                        n_rate = st.number_input("Rate", min_value=0.0, value=float(rec["rate"]), step=0.1, key=f"ed_rate_{entry_id}")
                        n_debit = st.number_input("Debit (Rs.)", min_value=0.0, value=float(rec["debit"]), step=100.0, key=f"ed_deb_{entry_id}")
                        n_credit = st.number_input("Credit (Rs.)", min_value=0.0, value=float(rec["credit"]), step=100.0, key=f"ed_cred_{entry_id}")
                        n_desc = st.text_input("Description", value=rec["description"] or "", key=f"ed_desc_{entry_id}")
                    auto = st.checkbox("Auto-calculate amount from Ltrs × Rate", value=False, key=f"ed_auto_{entry_id}")
                    do_update = st.form_submit_button("💾 Update Ledger Entry")

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
                    st.success(f"✅ Ledger Entry ID {entry_id} updated.")
                    st.rerun()

            else:
                st.warning(f"You are about to permanently delete: {picked_label}")
                sure = st.checkbox("Yes, I am sure — delete this entry permanently", key=f"sure_{entry_id}")
                if st.button("🗑️ Delete Ledger Entry", disabled=not sure, key=f"del_btn_{entry_id}"):
                    execute_query("DELETE FROM ledger WHERE id = ?", (entry_id,))
                    st.success(f"✅ Ledger Entry ID {entry_id} permanently deleted.")
                    st.rerun()

        st.markdown("---")
        if st.button("🔢 Re-sequence Ledger Entry IDs (1,2,3...)"):
            resequence_ids("ledger")
            st.success("Ledger IDs re-sequenced in date order.")
            st.rerun()

    # ========== STOCK TAB ==========
    with tab_stock:
        st.markdown("#### 🛢️ Stock Register Entries")

        sf1, sf2 = st.columns(2)
        stock_item_filter = sf1.selectbox("Fuel Filter", ["All", "Petrol", "Diesel"], key="stock_edit_item")
        stock_search = sf2.text_input("Search by Date (YYYY-MM-DD)", key="stock_edit_search")

        sq = "SELECT * FROM stock_register WHERE 1=1"
        sparams = []
        if stock_item_filter != "All":
            sq += " AND item_type = ?"
            sparams.append(stock_item_filter)
        if stock_search.strip():
            sq += " AND entry_date LIKE ?"
            sparams.append(f"%{stock_search}%")
        sq += " ORDER BY entry_date DESC, id DESC LIMIT 500"

        stock_rows = read_df(sq, params=sparams)

        if stock_rows.empty:
            st.info("No stock entries found for this selection.")
        else:
            sview = stock_rows.rename(columns={
                "id": "Entry ID", "entry_date": "Date", "item_type": "Fuel",
                "opening_stock": "Opening Stock", "rate": "Rate",
                "purchase_qty": "Purch Qty", "purchase_rate": "Purch Rate",
                "sales_qty": "Sales Qty", "sales_rate": "Sales Rate",
                "avg_rate": "Avg Rate", "closing_stock": "Closing Stock",
                "actual_stock": "Actual Stock", "dip_diff": "Dip Diff",
            })[["Entry ID", "Date", "Fuel", "Opening Stock", "Rate", "Purch Qty", "Purch Rate",
                "Sales Qty", "Sales Rate", "Avg Rate", "Closing Stock", "Actual Stock", "Dip Diff"]]
            st.dataframe(sr_index(sview), use_container_width=True)

            slabels = {
                f"ID {r.id} | {r.entry_date} | {r.item_type} | "
                f"Open {r.opening_stock:,.0f} | Purch {r.purchase_qty:,.0f} | Sales {r.sales_qty:,.0f}": int(r.id)
                for r in stock_rows.itertuples()
            }
            spicked = st.selectbox("Select stock entry to edit/delete", list(slabels.keys()), key="pick_stock")
            s_id = slabels[spicked]
            s_rec = stock_rows[stock_rows["id"] == s_id].iloc[0]

            s_action = st.radio("Choose Action", ["✏️ Edit Stock Entry", "🗑️ Delete Stock Entry"],
                                horizontal=True, key=f"stock_action_{s_id}")

            if s_action == "✏️ Edit Stock Entry":
                with st.form(f"edit_stock_form_{s_id}"):
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        s_date = st.date_input("Date", datetime.strptime(s_rec["entry_date"], "%Y-%m-%d").date(),
                                                format="DD-MM-YYYY", key=f"sd_date_{s_id}")
                        s_item = st.selectbox("Fuel Item", ["Petrol", "Diesel"],
                                               index=0 if s_rec["item_type"] == "Petrol" else 1,
                                               key=f"sd_item_{s_id}")
                        s_op_stock = st.number_input("Opening Stock (Ltrs)", min_value=0.0,
                                                      value=float(s_rec["opening_stock"] or 0.0), step=1.0,
                                                      key=f"sd_opstk_{s_id}")
                        s_op_rate = st.number_input("Opening Rate", min_value=0.0,
                                                     value=float(s_rec["rate"] or 0.0), step=0.1,
                                                     key=f"sd_oprate_{s_id}")
                    with sc2:
                        s_p_qty = st.number_input("Purchase Qty (Ltrs)", min_value=0.0,
                                                   value=float(s_rec["purchase_qty"] or 0.0), step=1.0,
                                                   key=f"sd_pqty_{s_id}")
                        s_p_rate = st.number_input("Purchase Rate", min_value=0.0,
                                                    value=float(s_rec["purchase_rate"] or 0.0), step=0.1,
                                                    key=f"sd_prate_{s_id}")
                        s_s_qty = st.number_input("Sales Qty (Ltrs)", min_value=0.0,
                                                   value=float(s_rec["sales_qty"] or 0.0), step=1.0,
                                                   key=f"sd_sqty_{s_id}")
                        s_s_rate = st.number_input("Sales Rate", min_value=0.0,
                                                    value=float(s_rec["sales_rate"] or 0.0), step=0.1,
                                                    key=f"sd_srate_{s_id}")
                    s_dip = st.number_input("Dip Difference (+/- Ltrs)", value=float(s_rec["dip_diff"] or 0.0),
                                             step=0.1, key=f"sd_dip_{s_id}")
                    s_update = st.form_submit_button("💾 Update Stock Entry")

                if s_update:
                    # Recalculate all derived values
                    s_op_amt = s_op_stock * s_op_rate
                    s_p_amt = s_p_qty * s_p_rate
                    s_tot_p = s_op_amt + s_p_amt
                    s_avail = s_op_stock + s_p_qty
                    s_avg = (s_tot_p / s_avail) if s_avail > 0 else 0.0
                    s_s_amt = s_s_qty * s_s_rate
                    s_tot_s_amt = s_s_qty * s_avg
                    s_close_amt = s_tot_p - s_tot_s_amt
                    s_close_stock = s_avail - s_s_qty
                    s_dip_amt = s_dip * s_avg
                    s_actual = s_close_stock + s_dip
                    s_act_amt = s_actual * s_avg

                    execute_query(
                        """UPDATE stock_register SET
                            entry_date=?, item_type=?, opening_stock=?, rate=?, opening_amount=?,
                            purchase_qty=?, purchase_rate=?, purchase_amount=?, total_purchase_amount=?,
                            avg_rate=?, available_stock=?, sales_qty=?, sales_rate=?, sales_amount=?,
                            total_sales_amount=?, closing_amount=?, closing_stock=?, dip_diff=?,
                            actual_stock=?, actual_amount=?
                           WHERE id=?""",
                        (str(s_date), s_item, s_op_stock, s_op_rate, s_op_amt,
                         s_p_qty, s_p_rate, s_p_amt, s_tot_p, s_avg, s_avail,
                         s_s_qty, s_s_rate, s_s_amt, s_tot_s_amt, s_close_amt,
                         s_close_stock, s_dip, s_actual, s_act_amt, s_id))
                    st.success(f"✅ Stock Entry ID {s_id} updated.")
                    st.rerun()

            else:
                st.warning(f"You are about to permanently delete Stock Entry ID {s_id} ({s_rec['entry_date']} / {s_rec['item_type']}).")
                s_sure = st.checkbox("Yes, I am sure — delete this stock entry permanently", key=f"ssure_{s_id}")
                if st.button("🗑️ Delete Stock Entry", disabled=not s_sure, key=f"sdel_{s_id}"):
                    execute_query("DELETE FROM stock_register WHERE id = ?", (s_id,))
                    st.success(f"✅ Stock Entry ID {s_id} permanently deleted.")
                    st.rerun()

        st.markdown("---")
        if st.button("🔢 Re-sequence Stock Entry IDs (1,2,3...)"):
            resequence_ids("stock_register")
            st.success("Stock IDs re-sequenced in date order.")
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
            lambda x: "Shortage (-)" if x < 0 else ("Excess (+)" if x > 0 else "Balanced"))
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
                try:
                    execute_query("INSERT INTO parties (name,type,opening_balance,phone) VALUES (?,?,?,?)",
                                  (name.strip(), p_type, op_bal, phone))
                    _cached_party_names.clear()
                    st.success(f"✅ Party '{name}' added.")
                    st.rerun()
                except Exception:
                    st.error("⚠️ A party with this name already exists.")

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
                        _cached_party_names.clear()
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
                _cached_party_names.clear()
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

            _cached_party_names.clear()
            st.success("✅ System restored successfully.")
            st.rerun()
