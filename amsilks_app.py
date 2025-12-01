import streamlit as st
import pandas as pd
import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
import base64
import time

# --- APP CONFIG ---
st.set_page_config(page_title="AMSilks ERP", layout="wide", page_icon="🏢")

# --- OWNER SETTINGS ---
OWNER_WHATSAPP = "97477070221" # നിങ്ങളുടെ വാട്സാപ്പ് നമ്പർ ഇവിടെ മാറ്റുക

# --- CONNECTION ---
def get_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Cloud vs Local Check
        if "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        return gspread.authorize(creds)
    except Exception as e:
        return None

def get_worksheet(name):
    client = get_client()
    try: return client.open("AMSilks_Orders").worksheet(name) if client else None
    except: return None

# --- PDF GENERATORS ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'AMSilks Trading W.L.L.', 0, 1, 'C')
        self.ln(5)

def create_receipt_pdf(date, r_no, name, amount, mode, ref, note):
    pdf = FPDF(orientation='L', unit='mm', format='A5')
    pdf.add_page()
    pdf.rect(5, 5, 200, 138)
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'AMSilks Trading W.L.L.', 0, 1, 'C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, 'Doha - Qatar | Tel: 77070221', 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 10, 'PAYMENT RECEIPT VOUCHER', 1, 1, 'C', 1)
    pdf.ln(5)
    pdf.set_font('Arial', '', 11)
    pdf.cell(130, 8, f"Receipt No: {r_no}", 0, 0)
    pdf.cell(60, 8, f"Date: {date}", 0, 1, 'R')
    pdf.ln(10)
    pdf.set_font('Arial', '', 12)
    pdf.cell(50, 10, "Received From:", 0, 0)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, name, 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(50, 10, "The Sum of QR:", 0, 0)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f"{amount:,.2f}", 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(50, 10, "Mode:", 0, 0)
    pdf.cell(0, 10, f"{mode} {ref}", 0, 1)
    if note:
        pdf.cell(50, 10, "Note:", 0, 0)
        pdf.cell(0, 10, note, 0, 1)
    pdf.ln(15)
    pdf.set_font('Arial', 'I', 10)
    pdf.cell(95, 10, "Received By", 0, 0, 'C')
    pdf.cell(95, 10, "Authorized Signature", 0, 1, 'C')
    return pdf.output(dest='S').encode('latin-1')

def create_statement_pdf(name, data, is_supplier=False):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    title = "SUPPLIER STATEMENT" if is_supplier else "CUSTOMER STATEMENT"
    pdf.cell(0, 10, title, 0, 1, 'C')
    pdf.cell(0, 10, f"Name: {name} | Date: {datetime.date.today()}", 0, 1)
    pdf.ln(5)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(30, 10, "Date", 1, 0, 'C', 1)
    pdf.cell(80, 10, "Description", 1, 0, 'C', 1)
    pdf.cell(30, 10, "Debit/Pay", 1, 0, 'C', 1)
    pdf.cell(30, 10, "Credit/Buy", 1, 0, 'C', 1)
    pdf.cell(20, 10, "Bal", 1, 1, 'C', 1)
    
    bal = 0
    for row in data:
        if is_supplier:
            # Supplier: Purchase adds to balance, Payment reduces
            cr = float(str(row.get('Amount')).replace(',','')) if row['Type'] == 'Purchase' else 0
            dr = float(str(row.get('Amount')).replace(',','')) if row['Type'] == 'Payment' else 0
            bal = bal + cr - dr
        else:
            # Customer: Invoice adds to balance, Receipt reduces
            dr = float(str(row.get('Amount')).replace(',','')) if row['Type'] == 'Invoice' else 0
            cr = float(str(row.get('Amount')).replace(',','')) if row['Type'] in ['Receipt', 'Sales Return'] else 0
            bal = bal + dr - cr
            
        pdf.cell(30, 10, str(row['Date']), 1)
        pdf.cell(80, 10, f"{row['Type']} {row.get('Ref_No','')}", 1)
        pdf.cell(30, 10, f"{dr:,.2f}", 1, 0, 'R')
        pdf.cell(30, 10, f"{cr:,.2f}", 1, 0, 'R')
        pdf.cell(20, 10, f"{bal:,.2f}", 1, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# --- DATA FUNCTIONS ---
def add_transaction(date, name, phone, t_type, amount, mode, ref, c_date, status, note, user):
    ws = get_worksheet("Transactions")
    if ws:
        ws.append_row([str(date), name, phone, t_type, amount, mode, ref, str(c_date), status, note, user])
        return True
    return False

def get_customer_ledger(phone):
    ws = get_worksheet("Transactions")
    if not ws: return []
    data = ws.get_all_records()
    return [d for d in data if str(d.get('Phone')).strip() == str(phone).strip() and d.get('Status') != 'Bounced']

def check_login(u, p):
    ws = get_worksheet("Users")
    if ws:
        users = ws.get_all_records()
        for user in users:
            if str(user['Username']) == u and str(user['Password']) == p: return user
    return None

# --- ALERT SYSTEM ---
def show_cheque_alerts():
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    alert = False
    
    # Customer Cheques
    ws = get_worksheet("Transactions")
    if ws:
        data = ws.get_all_records()
        pending = [d for d in data if d.get('Mode') == 'Cheque' and d.get('Status') == 'Pending']
        for c in pending:
            try:
                cd = datetime.datetime.strptime(str(c.get('Cheque_Date')), "%Y-%m-%d").date()
                if cd == today or cd == tomorrow:
                    msg = f"🔔 CHEQUE ALERT: {c.get('Customer')} (QR {c.get('Amount')}) - {cd}"
                    st.warning(msg)
                    st.link_button(f"📲 WhatsApp Reminder", f"https://wa.me/{OWNER_WHATSAPP}?text={msg}")
                    alert = True
            except: pass
            
    # Supplier Payments
    ws2 = get_worksheet("Suppliers")
    if ws2:
        data = ws2.get_all_records()
        for s in data:
            if s.get('Type') == 'Payment':
                try:
                    pd = datetime.datetime.strptime(str(s.get('Date')), "%Y-%m-%d").date()
                    if pd == today or pd == tomorrow:
                        msg = f"💸 PAYMENT DUE: To {s.get('Supplier_Name')} (QR {s.get('Amount')}) - {pd}"
                        st.error(msg)
                        alert = True
                except: pass
    if alert: st.divider()

# --- MAIN APP LOGIC ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []

if not st.session_state.logged_in:
    st.title("AMSilks Login 🔒")
    c1, c2 = st.columns(2)
    u = c1.text_input("Username")
    p = c2.text_input("Password", type="password")
    if st.button("Login"):
        user = check_login(u, p)
        if user:
            st.session_state.logged_in = True
            st.session_state.user_name = user['Name']
            st.session_state.role = user['Role']
            st.rerun()
        else: st.error("Invalid Credentials")
    st.stop()

# --- DASHBOARD ---
show_cheque_alerts()

with st.sidebar:
    st.write(f"User: **{st.session_state.user_name}**")
    menu = st.radio("Menu", [
        "📝 New Order", 
        "💰 Payments/Receipts", 
        "💸 Expenses", 
        "🚛 Suppliers", 
        "↩️ Returns", 
        "🔍 CRM & History", 
        "📊 Reports"
    ])
    if st.button("Logout"): 
        st.session_state.logged_in = False
        st.rerun()

# 1. NEW ORDER (Calculator)
if menu == "📝 New Order":
    st.title("New Order / Estimate")
    col1, col2 = st.columns(2)
    cust_name = col1.text_input("Customer Name")
    cust_phone = col2.text_input("Phone")
    
    st.subheader("Add Items")
    c1, c2, c3 = st.columns(3)
    type_ = c1.selectbox("Type", ["Curtain", "Blind", "Upholstery"])
    w = c2.number_input("Width (cm)", 0.0)
    h = c3.number_input("Height (cm)", 0.0)
    qty = st.number_input("Qty", 1)
    price = st.number_input("Unit Price", 0.0)
    
    if st.button("Add to Cart"):
        # Logic: Curtain Calc
        total = 0
        note = ""
        if type_ == "Curtain":
            req_h = (h/100) + 0.2
            panels = ((w/100) * 3) / 1.4 # Approx 3x fullness
            fab_req = panels * req_h * qty
            total = fab_req * price 
            note = f"Fab: {fab_req:.2f}m"
        else:
            total = (w/100)*(h/100)*qty*price
        
        st.session_state.cart.append({"Type": type_, "W": w, "H": h, "Qty": qty, "Total": total, "Note": note})
        st.success("Added")
        
    if st.session_state.cart:
        df = pd.DataFrame(st.session_state.cart)
        st.dataframe(df)
        grand_total = df['Total'].sum()
        st.markdown(f"### Total: {grand_total:.2f}")
        
        if st.button("Save Order & Post Invoice"):
            if cust_name:
                # Save to Orders
                ws = get_worksheet("sheet1")
                ws.append_row([str(datetime.date.today()), cust_name, cust_phone, grand_total, json.dumps(st.session_state.cart), st.session_state.user_name])
                # Post to Ledger
                add_transaction(datetime.date.today(), cust_name, cust_phone, "Invoice", grand_total, "Credit", "", "", "Cleared", "New Order", st.session_state.user_name)
                st.session_state.cart = []
                st.success("Order Saved & Invoice Posted!")

# 2. PAYMENTS & RECEIPTS
elif menu == "💰 Payments/Receipts":
    st.title("Receive Payment")
    c1, c2 = st.columns(2)
    name = c1.text_input("Customer Name")
    phone = c2.text_input("Phone")
    amt = st.number_input("Amount", min_value=0.0)
    mode = st.selectbox("Mode", ["Cash", "Cheque", "Transfer"])
    
    ref = st.text_input("Ref/Cheque No")
    c_date = ""
    status = "Cleared"
    if mode == "Cheque":
        c_date = st.date_input("Cheque Date")
        status = "Pending"
    
    if st.button("Save & Generate Voucher"):
        if name and amt > 0:
            add_transaction(datetime.date.today(), name, phone, "Receipt", amt, mode, ref, c_date, status, "", st.session_state.user_name)
            st.success("Saved!")
            
            # PDF
            rec_no = f"REC-{int(time.time())}"
            pdf = create_receipt_pdf(str(datetime.date.today()), rec_no, name, amt, mode, ref, "")
            b64 = base64.b64encode(pdf).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="Rec_{rec_no}.pdf">📥 Download Voucher</a>'
            st.markdown(href, unsafe_allow_html=True)

# 3. EXPENSES
elif menu == "💸 Expenses":
    st.title("Add Expense")
    with st.form("exp"):
        dt = st.date_input("Date")
        cat = st.selectbox("Category", ["Rent", "Salary", "Purchase", "Other"])
        amt = st.number_input("Amount", min_value=0.0)
        note = st.text_input("Note")
        
        # Job Costing Link
        ws = get_worksheet("sheet1")
        cust_list = [f"{d['Name']}" for d in ws.get_all_records()] if ws else []
        proj = st.selectbox("Link to Project (Optional)", ["General"] + cust_list)
        
        if st.form_submit_button("Save"):
            ws_exp = get_worksheet("Expenses")
            ws_exp.append_row([str(dt), cat, amt, note, st.session_state.user_name, proj])
            st.success("Expense Added")

# 4. SUPPLIERS
elif menu == "🚛 Suppliers":
    st.title("Supplier Manager")
    t1, t2 = st.tabs(["New Purchase", "Payment"])
    with t1:
        s_name = st.text_input("Supplier Name")
        s_amt = st.number_input("Bill Amount", min_value=0.0)
        if st.button("Save Purchase (Credit)"):
            ws = get_worksheet("Suppliers")
            ws.append_row([str(datetime.date.today()), s_name, "Purchase", s_amt, "", "", st.session_state.user_name])
            st.success("Saved")
    with t2:
        p_name = st.text_input("Pay to Name")
        p_amt = st.number_input("Pay Amount", min_value=0.0)
        if st.button("Save Payment"):
            ws = get_worksheet("Suppliers")
            ws.append_row([str(datetime.date.today()), p_name, "Payment", p_amt, "", "", st.session_state.user_name])
            st.success("Payment Recorded")

# 5. RETURNS
elif menu == "↩️ Returns":
    st.title("Returns Manager")
    c1, c2 = st.columns(2)
    r_name = c1.text_input("Customer Name")
    r_amt = c2.number_input("Return Value", min_value=0.0)
    if st.button("Save Sales Return"):
        add_transaction(datetime.date.today(), r_name, "", "Sales Return", r_amt, "Credit Note", "", "", "Cleared", "", st.session_state.user_name)
        st.success("Return Recorded. Balance Updated.")

# 6. CRM
elif menu == "🔍 CRM & History":
    st.title("Search Customer")
    ph = st.text_input("Phone Number")
    if st.button("Search"):
        ws = get_worksheet("sheet1")
        data = ws.get_all_records()
        hist = [d for d in data if str(d['Phone']) == ph]
        if hist:
            st.write(f"Customer Found: {hist[-1]['Name']}")
            st.dataframe(pd.DataFrame(hist))
        else: st.warning("Not Found")

# 7. REPORTS
elif menu == "📊 Reports":
    st.title("Accounts & Reports")
    rpt = st.selectbox("Select Report", ["Customer Statement", "Shop P&L"])
    
    if rpt == "Customer Statement":
        ph = st.text_input("Phone")
        if st.button("Get PDF"):
            data = get_customer_ledger(ph)
            if data:
                pdf = create_statement_pdf(data[0]['Customer'], data)
                b64 = base64.b64encode(pdf).decode()
                st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Stmt.pdf">📥 Download PDF</a>', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(data))
    
    elif rpt == "Shop P&L":
        ws1 = get_worksheet("sheet1") # Income
        ws2 = get_worksheet("Expenses") # Exp
        inc = sum([float(str(d['Total']).replace(',','')) for d in ws1.get_all_records()])
        exp = sum([float(str(d['Amount']).replace(',','')) for d in ws2.get_all_records()])
        prof = inc - exp
        c1, c2, c3 = st.columns(3)
        c1.metric("Income", f"{inc:,.2f}")
        c2.metric("Expense", f"{exp:,.2f}")
        c3.metric("Net Profit", f"{prof:,.2f}")