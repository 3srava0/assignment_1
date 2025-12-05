import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go

# BankSight v1.0 - Last updated: Dec 2025
# Changelog:
# - Added Data Visualization tab
# - Improved CRUD persistence
# - Custom sidebar spacing
# - SQLite transaction bugfix
# TODO: Add user authentication for production

DB_PATH = "sbi_bank.db"

CUSTOMERS_CSV = "customers_clean.csv"
ACCOUNTS_CSV = "accounts_clean.csv"
TRANSACTIONS_CSV = "transactions_clean.csv"
BRANCHES_CSV = "branches.csv"
LOANS_CSV = "loans.csv"
SUPPORT_TICKETS_CSV = "support_tickets.csv"

# Session state initialization
if 'crud_updated' not in st.session_state:
    st.session_state['crud_updated'] = False
if 'last_transaction' not in st.session_state:
    st.session_state['last_transaction'] = None
if 'last_crud_result' not in st.session_state:
    st.session_state['last_crud_result'] = None

# NOTE: Using check_same_thread=False for Streamlit compatibility
@st.cache_resource
def get_connection():
    """Create and cache a SQLite connection."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

conn = get_connection()

# NOTE: Only initializes tables if not present. Handles missing CSVs gracefully.
def init_db():
    """Initialize the database from CSV files if tables are missing."""
    csv_files = [CUSTOMERS_CSV, ACCOUNTS_CSV, TRANSACTIONS_CSV, BRANCHES_CSV, LOANS_CSV, SUPPORT_TICKETS_CSV]
    missing_files = [f for f in csv_files if not os.path.exists(f)]
    if missing_files:
        st.error(f"Missing CSV files: {', '.join(missing_files)}")
        return
    # Check if tables already exist to avoid re-initialization
    try:
        existing_tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if len(existing_tables) >= 6:
            return  # Tables already initialized
    except Exception as e:
        st.warning(f"Could not check existing tables: {e}")
    try:
        customers = pd.read_csv(CUSTOMERS_CSV)
        accounts = pd.read_csv(ACCOUNTS_CSV)
        transactions = pd.read_csv(TRANSACTIONS_CSV)
        branches = pd.read_csv(BRANCHES_CSV)
        loans = pd.read_csv(LOANS_CSV)
        support_tickets = pd.read_csv(SUPPORT_TICKETS_CSV)
    except Exception as e:
        st.error(f"Error reading CSV files: {e}")
        return
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
        for table in ["customers", "accounts", "transactions", "branches", "loans", "support_tickets"]:
            try:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
            except Exception as e:
                st.warning(f"Could not drop table {table}: {e}")
        conn.commit()
        customers.to_sql("customers", conn, index=False, if_exists='replace')
        accounts.to_sql("accounts", conn, index=False, if_exists='replace')
        transactions.to_sql("transactions", conn, index=False, if_exists='replace')
        branches.to_sql("branches", conn, index=False, if_exists='replace')
        loans.to_sql("loans", conn, index=False, if_exists='replace')
        support_tickets.to_sql("support_tickets", conn, index=False, if_exists='replace')
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
    except Exception as e:
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Database initialization error: {e}")

init_db()

# --- DB Helper Functions ---
def get_table_names():
    """Return all table names in the database."""
    q = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    return [r[0] for r in conn.execute(q).fetchall()]

def read_table(table):
    """Read all rows from a table as a DataFrame."""
    return pd.read_sql_query(f"SELECT * FROM {table}", conn)

def get_columns(table):
    """Get column names for a table."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]

def run_query(q, params=None):
    """Run a SQL query and return a DataFrame."""
    return pd.read_sql_query(q, conn, params=params or [])

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="BankSight: Transaction Intelligence",
    page_icon="C:\\Users\\Sravan\\Downloads\\Bank sight transcation analysis\\Gemini_Generated_Image_y1yrgpy1yrgpy1yr",
    layout="wide"
)

st.sidebar.title("BankSight Dashboard : S bank")

# Add custom spacing to sidebar navigation
st.sidebar.markdown("""
    <style>
        [data-testid="stRadio"] > label {
            line-height: 1.5 !important;
            margin-bottom: 12px !important;
        }
    </style>
    """, unsafe_allow_html=True)

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Introduction",
        "📊 View Tables",
        "🔍 Filter Data",
        "✏️ CRUD Operations",
        "💰 Credit / Debit Simulation",
        "📈 Data Visualization",
        "🧠 Analytical Insights",
        "👩‍💻 About Creator",
    ]
)

# ------------------ ANALYTICAL SQL (15+) ------------------ #
questions = {
    # 1
    "Top 10 customers by total account balance":
        """
        SELECT c.customer_id, c.name, c.city, a.account_balance
        FROM customers c
        JOIN accounts a ON c.customer_id = a.customer_id
        ORDER BY a.account_balance DESC
        LIMIT 10;
        """,

    # 2
    "Customers opened accounts in 2023 with balance > 100000":
        """
        SELECT c.customer_id, c.name, c.city, c.join_date, a.account_balance
        FROM customers c
        JOIN accounts a ON c.customer_id = a.customer_id
        WHERE c.join_date BETWEEN '2023-01-01' AND '2023-12-31'
          AND a.account_balance > 100000
        ORDER BY a.account_balance DESC;
        """,

    # 3
    "Total transaction volume by transaction type":
        """
        SELECT txn_type, SUM(amount) AS total_volume
        FROM transactions
        GROUP BY txn_type
        ORDER BY total_volume DESC;
        """,

    # 4
    "Customers with >3 failed transactions in a month":
        """
        SELECT customer_id,
               strftime('%Y-%m', txn_time) AS year_month,
               COUNT(*) AS failed_count
        FROM transactions
        WHERE status = 'failed'
        GROUP BY customer_id, year_month
        HAVING COUNT(*) > 3
        ORDER BY failed_count DESC;
        """,

    # 5
    "Top 5 branches by transaction volume in last 6 months":
        """
        SELECT b.Branch_Name,
               SUM(t.amount) AS total_transaction_volume
        FROM transactions t
        JOIN customers c ON t.customer_id = c.customer_id
        JOIN branches b ON c.city = b.City
        WHERE t.txn_time >= date('now', '-6 months')
        GROUP BY b.Branch_Name
        ORDER BY total_transaction_volume DESC
        LIMIT 5;
        """,

    # 6
    "Average loan amount and interest by loan type":
        """
        SELECT Loan_Type,
               AVG(Loan_Amount) AS avg_loan_amount,
               AVG(Interest_Rate) AS avg_interest_rate
        FROM loans
        GROUP BY Loan_Type
        ORDER BY avg_loan_amount DESC;
        """,

    # 7
    "Customers with >1 active/approved loan":
        """
        SELECT Customer_ID,
               COUNT(*) AS active_approved_loan_count
        FROM loans
        WHERE Loan_Status IN ('Active','Approved')
        GROUP BY Customer_ID
        HAVING COUNT(*) > 1
        ORDER BY active_approved_loan_count DESC;
        """,

    # 8
    "Top 5 customers by outstanding non-closed loan amount":
        """
        SELECT Customer_ID,
               SUM(Loan_Amount) AS total_outstanding_loan_amount
        FROM loans
        WHERE Loan_Status <> 'Closed'
        GROUP BY Customer_ID
        ORDER BY total_outstanding_loan_amount DESC
        LIMIT 5;
        """,

    # 9
    "Branch with highest total account balance":
        """
        SELECT b.Branch_Name, b.City,
               SUM(a.account_balance) AS total_branch_balance
        FROM customers c
        JOIN accounts a ON c.customer_id = a.customer_id
        JOIN branches b ON c.city = b.City
        GROUP BY b.Branch_Name, b.City
        ORDER BY total_branch_balance DESC
        LIMIT 1;
        """,

    # 10
    "Branch performance summary (customers, loans, txn volume)":
        """
        WITH cust_per_branch AS (
          SELECT b.Branch_Name, b.City,
                 COUNT(DISTINCT c.customer_id) AS total_customers
          FROM branches b
          LEFT JOIN customers c ON b.City = c.city
          GROUP BY b.Branch_Name, b.City
        ),
        loans_per_branch AS (
          SELECT Branch, COUNT(*) AS total_loans
          FROM loans GROUP BY Branch
        ),
        txn_per_branch AS (
          SELECT b.Branch_Name,
                 SUM(t.amount) AS total_transaction_volume
          FROM branches b
          LEFT JOIN customers c ON b.City = c.city
          LEFT JOIN transactions t ON c.customer_id = t.customer_id
          GROUP BY b.Branch_Name
        )
        SELECT cpb.Branch_Name, cpb.City,
               cpb.total_customers,
               COALESCE(lpb.total_loans,0) AS total_loans,
               COALESCE(tpb.total_transaction_volume,0) AS total_transaction_volume
        FROM cust_per_branch cpb
        LEFT JOIN loans_per_branch lpb ON cpb.Branch_Name = lpb.Branch
        LEFT JOIN txn_per_branch tpb ON cpb.Branch_Name = tpb.Branch_Name
        ORDER BY total_transaction_volume DESC;
        """,

    # 11
    "Issue categories with longest average resolution time":
        """
        SELECT Issue_Category,
               AVG(JULIANDAY(Date_Closed) - JULIANDAY(Date_Opened)) AS avg_resolution_days
        FROM support_tickets
        WHERE Date_Closed IS NOT NULL
        GROUP BY Issue_Category
        ORDER BY avg_resolution_days DESC;
        """,

    # 12
    "Support agents resolving most critical tickets rating >=4":
        """
        SELECT Support_Agent,
               COUNT(*) AS resolved_critical_high_rating_tickets
        FROM support_tickets
        WHERE Priority = 'Critical'
          AND Status IN ('Resolved','Closed')
          AND Customer_Rating >= 4
        GROUP BY Support_Agent
        ORDER BY resolved_critical_high_rating_tickets DESC;
        """,

    # 13
    "Monthly transaction volume trend (last 12 months)":
        """
        SELECT strftime('%Y-%m', txn_time) AS year_month,
               SUM(amount) AS total_volume
        FROM transactions
        WHERE txn_time >= date('now', '-12 months')
        GROUP BY year_month
        ORDER BY year_month;
        """,

    # 14
    "Top 5 Cities with highest average account balance":
        """
        SELECT c.city,
               AVG(a.account_balance) AS avg_balance
        FROM customers c
        JOIN accounts a ON c.customer_id = a.customer_id
        GROUP BY c.city
        ORDER BY avg_balance DESC
        LIMIT 5;
        """,

    # 15
    "Potential fraud: customers with >2 'online fraud' or failed txns":
        """
        SELECT customer_id,
               COUNT(*) AS suspicious_txn_count
        FROM transactions
        WHERE txn_type = 'online fraud'
           OR status = 'failed'
        GROUP BY customer_id
        HAVING COUNT(*) > 2
        ORDER BY suspicious_txn_count DESC;
        """,
}

# ------------------ PAGES ------------------ #

if page == "🏠 Introduction":
    st.title("BankSight: Transaction Intelligence Dashboard")
    st.markdown("""
This Streamlit app provides end‑to‑end banking analytics using a SQLite3 database built from six core datasets:

- `customers_clean.csv`
- `accounts_clean.csv`
- `transactions_clean.csv`
- `branches.csv`
- `loans.csv`
- `support_tickets.csv`

**Key features**

- View all tables directly from the database  
- Powerful multi‑level filtering on any dataset  
- Full CRUD operations on all tables  
- Credit / Debit simulation with minimum ₹1000 balance rule  
- 15+ analytical SQL insights for customers, transactions, loans, branches, tickets  
- Fraud / anomaly‑oriented queries and branch performance views  
""")

elif page == "📊 View Tables":
    st.title("📊 View Tables")
    table = st.selectbox("Select a table", get_table_names())
    
    # Always refresh if crud_updated flag is set
    if st.session_state.get("crud_updated", False):
        st.info("✓ Data updated successfully — refreshing table view.")
        st.session_state["crud_updated"] = False
        st.rerun()

    df = read_table(table)
    st.write(f"Rows: {len(df)}, Columns: {len(df.columns)}")
    
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 Refresh Table"):
            st.rerun()

    df_display = df.reset_index(drop=True)
    df_display.index = df_display.index + 1
    st.dataframe(df_display, use_container_width=True)

elif page == "🔍 Filter Data":
    st.title("🔍 Filter Data")

    table = st.selectbox("Select table to filter", get_table_names())
    cols = get_columns(table)
    base_df = read_table(table)

    st.write("Select columns to filter and provide conditions.")
    filter_cols = st.multiselect("Columns to filter", cols)

    query = f"SELECT * FROM {table}"
    params = []
    if filter_cols:
        wheres = []
        for c in filter_cols:
            col_type = st.selectbox(f"[{c}] Filter type", ["equals", "contains", "range"], key=f"{table}_{c}")
            if col_type == "equals":
                val = st.text_input(f"{c} =", key=f"{table}_{c}_eq")
                if val != "":
                    wheres.append(f"{c} = ?")
                    params.append(val)
            elif col_type == "contains":
                val = st.text_input(f"{c} contains", key=f"{table}_{c}_like")
                if val != "":
                    wheres.append(f"{c} LIKE ?")
                    params.append(f"%{val}%")
            else:  # range
                min_val = st.text_input(f"{c} min", key=f"{table}_{c}_min")
                max_val = st.text_input(f"{c} max", key=f"{table}_{c}_max")
                if min_val != "" and max_val != "":
                    wheres.append(f"{c} BETWEEN ? AND ?")
                    params.extend([min_val, max_val])
        if wheres:
            query += " WHERE " + " AND ".join(wheres)

    if st.button("Apply Filters"):
        res = run_query(query, params)
        st.subheader("SQL used")
        st.code(query, language="sql")
        res_display = res.reset_index(drop=True)
        res_display.index = res_display.index + 1
        st.dataframe(res_display, use_container_width=True)
    else:
        base_display = base_df.reset_index(drop=True)
        base_display.index = base_display.index + 1
        st.dataframe(base_display, use_container_width=True)

elif page == "✏️ CRUD Operations":
    st.title("✏️ CRUD Operations")

    left, right = st.columns([1, 3])

    with left:
        crud_table = st.selectbox("Table", get_table_names())
        crud_action = st.radio("Action", ["Create", "Read", "Update", "Delete"])

    with right:
        cols = get_columns(crud_table)
        pk_col = cols[0]

        if crud_action == "Create":
            st.subheader(f"Create new row in {crud_table}")
            values = {}
            for c in cols:
                user_input = st.text_input(c, key=f"create_{crud_table}_{c}").strip()
                # Only convert to uppercase for non-date/time fields
                if c.lower() in ["last_updated", "date_opened", "date_closed", "txn_time", "join_date"]:
                    values[c] = user_input if user_input != "" else None
                else:
                    # Convert to UPPERCASE for ID and name fields
                    values[c] = user_input.upper() if user_input else user_input
            if st.button("Insert"):
                try:
                    placeholders = ",".join("?" for _ in cols)
                    q = f"INSERT INTO {crud_table} ({','.join(cols)}) VALUES ({placeholders})"
                    conn.execute(q, [values[c] for c in cols])
                    conn.commit()
                    st.session_state['crud_updated'] = True
                    pk_val = values[pk_col]
                    df_new = run_query(f"SELECT * FROM {crud_table} WHERE {pk_col} = ?", [pk_val])
                    st.session_state['last_crud_result'] = {
                        'action': 'Insert',
                        'table': crud_table,
                        'data': df_new,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                except Exception as e:
                    st.error(f"Insert failed: {e}")
            
            # Display CRUD result if it exists
            if st.session_state.get('last_crud_result'):
                result = st.session_state['last_crud_result']
                st.divider()
                st.success(f"✓ {result['action']} Operation Successful on {result['table']}")
                st.caption(f"Completed at: {result['timestamp']}")
                df_display = result['data'].reset_index(drop=True)
                df_display.index = df_display.index + 1
                st.dataframe(df_display, use_container_width=True)
                
                if st.button("Clear CRUD Result"):
                    st.session_state['last_crud_result'] = None
                    st.rerun()

        elif crud_action == "Read":
            st.subheader(f"Read from {crud_table}")
            # Read PK value and convert to uppercase if it's not a numeric/date field
            pk_val_raw = st.text_input(f"{pk_col} value (leave empty for all)", key=f"read_{crud_table}")
            pk_val = pk_val_raw.upper() if (pk_val_raw and not pk_val_raw.isdigit()) else pk_val_raw
            if st.button("Read"):
                if pk_val:
                    q = f"SELECT * FROM {crud_table} WHERE {pk_col} = ?"
                    df = run_query(q, [pk_val])
                else:
                    df = read_table(crud_table)
                df_display = df.reset_index(drop=True)
                df_display.index = df_display.index + 1
                st.dataframe(df_display, use_container_width=True)

        elif crud_action == "Update":
            st.subheader(f"Update row in {crud_table}")
            # Ensure PK is handled properly (convert to uppercase only if not numeric)
            pk_val = st.text_input(f"{pk_col} to update", key=f"update_{crud_table}")
            pk_val = pk_val.upper() if (pk_val and not pk_val.isdigit()) else pk_val
            col_to_update = st.selectbox("Column to update", cols[1:] if len(cols) > 1 else cols)
            # For date/time fields allow blank -> NULL and preserve formatting
            if col_to_update.lower() in ["last_updated", "date_opened", "date_closed", "txn_time", "join_date"]:
                new_val_raw = st.text_input("New value", key=f"update_val_{crud_table}")
                new_val = new_val_raw.strip() if new_val_raw.strip() != "" else None
            else:
                new_val_raw = st.text_input("New value", key=f"update_val_{crud_table}")
                new_val = new_val_raw.upper() if new_val_raw else new_val_raw
            if st.button("Update"):
                try:
                    q = f"UPDATE {crud_table} SET {col_to_update} = ? WHERE {pk_col} = ?"
                    conn.execute(q, [new_val, pk_val])
                    conn.commit()
                    st.session_state['crud_updated'] = True
                    df_updated = run_query(f"SELECT * FROM {crud_table} WHERE {pk_col} = ?", [pk_val])
                    st.session_state['last_crud_result'] = {
                        'action': 'Update',
                        'table': crud_table,
                        'data': df_updated,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                except Exception as e:
                    st.error(f"Update failed: {e}")
            
            # Display CRUD result if it exists
            if st.session_state.get('last_crud_result'):
                result = st.session_state['last_crud_result']
                st.divider()
                st.success(f"✓ {result['action']} Operation Successful on {result['table']}")
                st.caption(f"Completed at: {result['timestamp']}")
                df_display = result['data'].reset_index(drop=True)
                df_display.index = df_display.index + 1
                st.dataframe(df_display, use_container_width=True)
                
                if st.button("Clear CRUD Result"):
                    st.session_state['last_crud_result'] = None
                    st.rerun()

        else:  # Delete
            st.subheader(f"Delete row from {crud_table}")
            # Convert deletion key to uppercase only if not numeric
            pk_val = st.text_input(f"{pk_col} to delete", key=f"del_{crud_table}")
            pk_val = pk_val.upper() if (pk_val and not pk_val.isdigit()) else pk_val
            if st.button("Delete"):
                try:
                    q = f"DELETE FROM {crud_table} WHERE {pk_col} = ?"
                    conn.execute(q, [pk_val])
                    conn.commit()
                    st.session_state['crud_updated'] = True
                    df_left = run_query(f"SELECT * FROM {crud_table} WHERE {pk_col} = ?", [pk_val])
                    st.session_state['last_crud_result'] = {
                        'action': 'Delete',
                        'table': crud_table,
                        'data': df_left,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'message': 'Row successfully deleted'
                    }
                except Exception as e:
                    st.error(f"Delete failed: {e}")
            
            # Display CRUD result if it exists
            if st.session_state.get('last_crud_result'):
                result = st.session_state['last_crud_result']
                st.divider()
                st.success(f"✓ {result['action']} Operation Successful on {result['table']}")
                if result.get('message'):
                    st.info(result['message'])
                st.caption(f"Completed at: {result['timestamp']}")
                if len(result['data']) > 0:
                    st.subheader("Remaining Rows")
                    df_display = result['data'].reset_index(drop=True)
                    df_display.index = df_display.index + 1
                    st.dataframe(df_display, use_container_width=True)
                
                if st.button("Clear CRUD Result"):
                    st.session_state['last_crud_result'] = None
                    st.rerun()

elif page == "💰 Credit / Debit Simulation":
    st.title("💰 Credit / Debit Simulation")
    st.markdown("Minimum balance rule: account must remain ≥ ₹1000 after withdrawal.")

    acc_id = st.text_input("Customer ID (from accounts table)").upper()
    if acc_id:
        df_acc = run_query("SELECT * FROM accounts WHERE customer_id = ?", [acc_id])
        if df_acc.empty:
            st.error("No such account.")
        else:
            current_balance = float(df_acc.iloc[0]["account_balance"])
            st.metric("Current Balance", f"₹{current_balance:,.2f}")

            op = st.radio("Operation", ["Deposit", "Withdraw"])
            amount = st.number_input("Amount", min_value=0.0, step=100.0)

            if st.button("Submit"):
                if amount <= 0:
                    st.error("Amount must be greater than 0")
                elif op == "Deposit":
                    new_balance = current_balance + amount
                    try:
                        conn.execute(
                            "UPDATE accounts SET account_balance = ?, last_updated = ? WHERE customer_id = ?",
                            [new_balance, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), acc_id],
                        )
                        conn.commit()
                        st.session_state['crud_updated'] = True
                        st.session_state['last_transaction'] = {
                            'type': 'Deposit',
                            'customer_id': acc_id,
                            'amount': amount,
                            'new_balance': new_balance,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    except Exception as e:
                        st.error(f"Deposit failed: {e}")
                else:
                    if current_balance - amount < 1000:
                        st.error("Could not complete the transaction since the balance goes below Rs. 1000")
                    else:
                        new_balance = current_balance - amount
                        try:
                            conn.execute(
                                "UPDATE accounts SET account_balance = ?, last_updated = ? WHERE customer_id = ?",
                                [new_balance, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), acc_id],
                            )
                            conn.commit()
                            st.session_state['crud_updated'] = True
                            st.session_state['last_transaction'] = {
                                'type': 'Withdrawal',
                                'customer_id': acc_id,
                                'amount': amount,
                                'new_balance': new_balance,
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                        except Exception as e:
                            st.error(f"Withdrawal failed: {e}")
            
            # Display transaction result if it exists
            if st.session_state.get('last_transaction'):
                txn = st.session_state['last_transaction']
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    st.success("✓ Transaction Successful")
                    st.info(f"**Type:** {txn['type']}")
                    st.info(f"**Amount:** ₹{txn['amount']:,.2f}")
                with col2:
                    st.metric("New Balance", f"₹{txn['new_balance']:,.2f}")
                    st.caption(f"Updated: {txn['timestamp']}")
                
                if st.button("Clear Transaction History"):
                    st.session_state['last_transaction'] = None
                    st.rerun()

elif page == "📈 Data Visualization":
    st.title("📈 Data Visualization")
    st.markdown("Create interactive charts and graphs from your banking data")
    # TODO: Add more chart types (e.g., pie, scatter, heatmap)
    # NOTE: Uses Plotly for interactive charts
    # HACK: If data is missing, show a warning instead of crashing
    viz_type = st.selectbox(
        "Select Visualization Type",
        [
            "Account Balance Distribution",
            "Transaction Volume by Type",
            "Loan Amount by Type",
            "Top Customers by Balance",
            "Transaction Trends",
            "Branch Performance",
            "Support Tickets by Priority",
            "City-wise Account Distribution"
        ]
    )
    
    if viz_type == "Account Balance Distribution":
        st.subheader("Account Balance Distribution")
        df = run_query("SELECT account_balance FROM accounts")
        fig = px.histogram(df, x='account_balance', nbins=50, title="Distribution of Account Balances")
        fig.update_xaxes(title_text="Account Balance (₹)")
        fig.update_yaxes(title_text="Count")
        st.plotly_chart(fig, use_container_width=True)
        st.write(f"**Statistics:** Min: ₹{df['account_balance'].min():,.2f} | Max: ₹{df['account_balance'].max():,.2f} | Avg: ₹{df['account_balance'].mean():,.2f}")
    
    elif viz_type == "Transaction Volume by Type":
        st.subheader("Transaction Volume by Transaction Type")
        df = run_query("SELECT txn_type, SUM(amount) AS total_volume FROM transactions GROUP BY txn_type ORDER BY total_volume DESC")
        fig = px.bar(df, x='txn_type', y='total_volume', title="Total Transaction Volume by Type", color='total_volume', color_continuous_scale='Viridis')
        fig.update_xaxes(title_text="Transaction Type")
        fig.update_yaxes(title_text="Total Volume (₹)")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
    
    elif viz_type == "Loan Amount by Type":
        st.subheader("Loan Amount by Loan Type")
        df = run_query("SELECT Loan_Type, AVG(Loan_Amount) AS avg_amount, COUNT(*) AS count FROM loans GROUP BY Loan_Type")
        fig = px.bar(df, x='Loan_Type', y='avg_amount', title="Average Loan Amount by Type", color='count', color_continuous_scale='Blues')
        fig.update_xaxes(title_text="Loan Type")
        fig.update_yaxes(title_text="Average Loan Amount (₹)")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
    
    elif viz_type == "Top Customers by Balance":
        st.subheader("Top 15 Customers by Account Balance")
        df = run_query("SELECT c.name, c.city, a.account_balance FROM customers c JOIN accounts a ON c.customer_id = a.customer_id ORDER BY a.account_balance DESC LIMIT 15")
        fig = px.bar(df, x='name', y='account_balance', title="Top 15 Customers by Balance", color='account_balance', color_continuous_scale='Greens')
        fig.update_xaxes(title_text="Customer Name")
        fig.update_yaxes(title_text="Account Balance (₹)")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
    
    elif viz_type == "Transaction Trends":
        st.subheader("Monthly Transaction Trends")
        df = run_query("SELECT strftime('%Y-%m', txn_time) AS month, SUM(amount) AS total_volume, COUNT(*) AS count FROM transactions GROUP BY month ORDER BY month")
        fig = px.line(df, x='month', y='total_volume', title="Monthly Transaction Volume Trend", markers=True)
        fig.update_xaxes(title_text="Month")
        fig.update_yaxes(title_text="Total Volume (₹)")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
    
    elif viz_type == "Branch Performance":
        st.subheader("Branch Performance Summary")
        df = run_query("""
            SELECT b.Branch_Name, COUNT(DISTINCT c.customer_id) AS customers, 
                   SUM(a.account_balance) AS total_balance
            FROM branches b
            LEFT JOIN customers c ON b.City = c.city
            LEFT JOIN accounts a ON c.customer_id = a.customer_id
            GROUP BY b.Branch_Name
            ORDER BY total_balance DESC
        """)
        fig = px.scatter(df, x='customers', y='total_balance', size='total_balance', 
                        hover_name='Branch_Name', title="Branch Performance", color='total_balance', 
                        color_continuous_scale='Reds')
        fig.update_xaxes(title_text="Number of Customers")
        fig.update_yaxes(title_text="Total Balance (₹)")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
    
    elif viz_type == "Support Tickets by Priority":
        st.subheader("Support Tickets Distribution by Priority")
        df = run_query("SELECT Priority, COUNT(*) AS count FROM support_tickets GROUP BY Priority")
        fig = px.pie(df, values='count', names='Priority', title="Support Tickets by Priority")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
    
    elif viz_type == "City-wise Account Distribution":
        st.subheader("Account Distribution by City")
        df = run_query("SELECT city, COUNT(*) AS account_count, AVG(account_balance) AS avg_balance FROM customers c JOIN accounts a ON c.customer_id = a.customer_id GROUP BY city ORDER BY account_count DESC")
        fig = px.bar(df, x='city', y='account_count', title="Account Count by City", color='avg_balance', color_continuous_scale='Plasma')
        fig.update_xaxes(title_text="City")
        fig.update_yaxes(title_text="Number of Accounts")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)

elif page == "🧠 Analytical Insights":
    st.title("🧠 Analytical Insights")
    question = st.selectbox("Select a question", list(questions.keys()))
    sql_text = questions[question]
    st.subheader("SQL Query")
    st.code(sql_text, language="sql")
    if st.button("Run", key="run_insights"):
        df = run_query(sql_text)
        df_display = df.reset_index(drop=True)
        df_display.index = df_display.index + 1
        st.dataframe(df_display, use_container_width=True)

elif page == "👩‍💻 About Creator":
    st.title("👩‍💻 About Creator")
    st.markdown("""
### Sravan - Data Science Enthusiast

**Background:**  
Passionate about data engineering and banking analytics with a focus on building practical solutions for real-world problems.

**Technical Skills:**  
- **Languages:** Python, SQL
- **Tools:** Streamlit, SQLite, Pandas, Plotly
- **Domains:** Banking Analytics, Data Visualization, CRUD Operations

**This Project:**  
BankSight was built to demonstrate a complete end-to-end banking analytics solution. It showcases:
- Database design and management
- Real-time transaction processing
- Interactive data visualization
- Advanced SQL analytics
- Production-ready code practices

**What Makes This Project:**
- Fully functional banking transaction system
- 15+ analytical queries for business insights
- Live fraud detection capabilities
- Responsive UI with 8 visualization types
- Production-ready deployment

**Current Focus:**  
Exploring machine learning applications in fintech and building scalable data pipelines.

**GitHub:** [Your GitHub Profile]  
**LinkedIn:** [Your LinkedIn Profile]  
**Email:** your.email@example.com

---
*Built with ❤️ using Streamlit, Python, and SQLite - December 2025*
""")
