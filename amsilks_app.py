import streamlit as st
import pandas as pd
import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
import base64
import time

# --- APP CONFIGURATION ---
st.set_page_config(page_title="AMSilks ERP", layout="wide", page_icon="🏢")

# --- CONSTANTS ---
OWNER_WHATSAPP = "97477070221" # ഉടമയുടെ വാട്സാപ്പ് നമ്പർ (Country Code അടക്കം)

# --- GOOGLE SHEET CONNECTION ---
def get_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Cloud (Secrets) vs Local (JSON) Check
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

# --- CACHING (SPEED BOOSTER) 🚀 ---
@st.cache_data(ttl=60)
def get_cached_data(sheet_name):
    ws = get_worksheet(sheet_name)
    if ws: return ws.get_all_records()
    return []

def clear_cache():
    st.cache_data.clear()

# --- PDF GENERATORS (PROFESSIONAL) 📄 ---
class PDF(FPDF):
    def header(self):
        try: self.image('logo.png', 10, 8, 35) # Logo (A4 Standard)
        except: pass
        self.set_font('Arial', 'B', 20)
        self.cell(40)
        self.cell(0, 10, 'AMSilks Trading W.L.L.', 0, 1, 'L')
        self.set_font('Arial', '', 10)
        self.cell(40)
        self.cell(0, 5, 'Doha - Qatar | CR: 224866 | Tel: 77070221', 0, 1, 'L')
        self.ln(8)
        self.set_draw_color(200, 200, 200)
        self.line(10, 30, 200, 30)
        self.ln(5)

def create_receipt_pdf(date, r_no, name, amount, mode, ref, note):
    pdf = FPDF(orientation='L', unit='mm', format='A5')
    pdf.add_page()
    pdf.rect(5, 5, 200, 138)
    try: pdf.image('logo.png', 10, 10, 25) # Logo (A5 Standard)
    except: pass
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(30)
    pdf.cell(0, 10, 'AMSilks Trading W.L.L.', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(30)
    pdf.cell(0, 5, 'Doha - Qatar | Tel: 77070221', 0, 1, 'L')
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_fill_color(230, 230, 230)
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
    pdf.cell(50, 10, "Payment Mode:", 0, 0)
    pdf.cell(0, 10, f"{mode} - {ref}", 0, 1)
    if note:
        pdf.cell(50, 10, "Note:", 0, 0)
        pdf.cell(0, 10, note, 0, 1)
    pdf.ln(15)
    pdf.set_font('Arial', 'I', 10)
    pdf.cell(95, 10, "Received By", 0, 0, 'C')
    pdf.cell(95, 10, "Authorized Signature", 0, 1, 'C')
    return pdf.output(dest='S').encode('latin-1')

def create_quotation_pdf(date, q_no, name, cart_items, total, subject):
    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'QUOTATION / ESTIMATE', 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font('Arial', '', 11)
    pdf.cell(120, 7, f"To: {name}", 0, 0)
    pdf.cell(0, 7, f"Date: {date}", 0, 1, 'R')
    pdf.cell(120, 7, f"Subject: {subject}", 0, 0)
    pdf.cell(0, 7, f"Quote No: {q_no}", 0, 1, 'R')
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(10, 10, "#", 1, 0, 'C', 1)
    pdf.cell(80, 10, "Description", 1, 0, 'C', 1)
    pdf.cell(30, 10, "Size", 1, 0, 'C', 1)
    pdf.cell(20, 10, "Qty", 1, 0, 'C', 1)
    pdf.cell(25, 10, "Rate", 1, 0, 'C', 1)
    pdf.cell(25, 10, "Total", 1, 1, 'C', 1)
    pdf.set_font('Arial', '', 10)
    idx = 1
    for item in cart_items:
        desc = f"{item['Type']} {item.get('Note','')}"
        size = f"{item['W']}x{item['H']}"
        pdf.cell(10, 10, str(idx), 1, 0, 'C')
        pdf.cell(80, 10, desc, 1)
        pdf.cell(30, 10, size, 1, 0, 'C')
        pdf.cell(20, 10, str(item['Qty']), 1, 0, 'C')
        pdf.cell(25, 10, f"{item.get('Price',0):.2f}", 1, 0, 'R')
        pdf.cell(25, 10, f"{item['Total']:.2f}", 1, 1, 'R')
        idx += 1
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(165, 10, "Grand Total (QR):", 1, 0, 'R')
    pdf.cell(25, 10, f"{total:,.2f}", 1, 1, 'R')
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, "Terms & Conditions:", 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 5, "1. Valid for 15 days.", 0, 1)
    pdf.cell(0, 5, "2. 50% Advance required.", 0, 1)
    return pdf.output(dest='S').encode('latin-1')

def create_statement_pdf(name, data, is_supplier=False):
    pdf = PDF()
    pdf.add_page()
    title = "SUPPLIER STATEMENT" if is_supplier else "CUSTOMER STATEMENT"
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, title, 0, 1, 'C')
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 10, f"Account: {name} | Date: {datetime.date.today()}", 0, 1)
    pdf.ln(5)
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(30, 10, "Date", 1, 0, 'C', 1)
    pdf.cell(80, 10, "Description", 1, 0, 'C', 1)
    pdf.cell(30, 10, "Debit/Pay", 1, 0, 'C', 1)
    pdf.cell(30, 10, "Credit/Buy", 1, 0, 'C', 1)
    pdf.cell(20, 10, "Bal", 1, 1, 'C', 1)
    pdf.set_font('Arial', '', 10)
    bal = 0
    for row in data:
        amt = float(str(row.get('Amount')).replace(',',''))
        dr, cr = 0, 0
        if is_supplier:
            if row['Type'] == 'Purchase': cr = amt
            else: dr = amt
            bal = bal + cr - dr
        else:
            if row['Type'] == 'Invoice': dr = amt
            else: cr = amt
            bal = bal + dr - cr
        pdf.cell(30, 10, str(row['Date']), 1)
        pdf.cell(80, 10, f"{row['Type']} {row.get('Ref_No','')}", 1)
        pdf.cell(30, 10, f"{dr:,.2f}", 1, 0, 'R')
        pdf.cell(30, 10, f"{cr:,.2f}", 1, 0, 'R')
        pdf.cell(20, 10, f"{bal:,.2f}", 1, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

def create_credit_note_pdf(date, note_no, name, amount, reason):
    pdf = FPDF(orientation='L', unit='mm', format='A5')
    pdf.add_page()
    pdf.rect(5, 5, 200, 138)
    try: pdf.image('logo.png', 10, 10, 25)
    except: pass
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(30)
    pdf.cell(0, 10, 'AMSilks Trading W.L.L.', 0, 1, 'L')
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, 'CREDIT NOTE (RETURN)', 1, 1, 'C', 1)
    pdf.ln(5)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Ref: {note_no} | Date: {date}", 0, 1)
    pdf.cell(0, 10, f"Customer: {name}", 0, 1)
    pdf.ln(5)
    pdf.cell(0, 10, f"Return Amount: QR {amount:,.2f}", 0, 1)
    pdf.cell(0, 10, f"Reason: {reason}", 0, 1)
    return pdf.output(dest='S').encode('latin-1')

# --- DATA FUNCTIONS (CRUD) ---
def add_transaction(date, name, phone, t_type, amount, mode, ref, c_date, status, note, user):
    ws = get_worksheet("Transactions")
    if ws:
        ws.append_row([str(date), name, phone, t_type, amount, mode, ref, str(c_date), status, note, user])
        clear_cache()
        return True
    return False

def add_expense(date, cat, amount, note, user, proj):
    ws = get_worksheet("Expenses")
    if ws:
        ws.append_row([str(date), cat, amount, note, user, proj])
        clear_cache()
        return True
    return False

def get_customer_ledger(phone):
    data = get_cached_data("Transactions")
    return [d for d in data if str(d.get('Phone')).strip() == str(phone).strip() and d.get('Status') != 'Bounced']

def check_login(u, p):
    ws = get_worksheet("Users") # Not cached for security
    if ws:
        users = ws.get_all_records()
        for user in users:
            if str(user['Username']) == u and str(user['Password']) == p: return user
    return None

# --- ALERTS SYSTEM 🔔 ---
def show_cheque_alerts():
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    alert = False
    
    # 1. Incoming (Customer)
    data = get_cached_data("Transactions")
    if data:
        pending = [d for d in data if d.get('Mode') == 'Cheque' and d.get('Status') == 'Pending']
        for c in pending:
            try:
                cd = datetime.datetime.strptime(str(c.get('Cheque_Date')), "%Y-%m-%d").date()
                if cd == today or cd == tomorrow:
                    msg = f"🔔 CHEQUE ALERT: From {c.get('Customer')} (QR {c.get('Amount')}) - Date: {cd}"
                    st.warning(msg)
                    st.link_button(f"📲 WhatsApp Reminder", f"https://wa.me/{OWNER_WHATSAPP}?text={msg}")
                    alert = True
            except: pass
            
    # 2. Outgoing (Supplier)
    s_data = get_cached_data("Suppliers")
    if s_data:
        for s in s_data:
            if s.get('Type') == 'Payment':
                try:
                    pd = datetime.datetime.strptime(str(s.get('Date')), "%Y-%m-%d").date()
                    if pd == today or pd == tomorrow:
                        msg = f"💸 PAYMENT DUE: To {s.get('Supplier_Name')} (QR {s.get('Amount')}) - Date: {pd}"
                        st.error(msg)
                        alert = True
                except: pass
    if alert: st.divider()

# --- MAIN APP LOGIC ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []

# LOGIN SCREEN
if not st.session_state.logged_in:
    col_c1, col_c2, col_c3 = st.columns([1,2,1])
    with col_c2:
        try: st.image("logo.png", width=200)
        except: st.title("AMSilks Login")
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                user = check_login(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_name = user['Name']
                    st.session_state.role = user['Role']
                    st.rerun()
                else: st.error("Invalid Credentials")
    st.stop()

# DASHBOARD
show_cheque_alerts()

with st.sidebar:
    try: st.image("logo.png", width=200)
    except: st.header("AMSilks ERP")
    st.info(f"User: **{st.session_state.user_name}**")
    
    menu = st.radio("Main Menu", [
        "📝 New Order", 
        "💰 Payments/Receipts", 
        "💸 Expenses", 
        "🚛 Suppliers", 
        "↩️ Returns", 
        "📜 Quotation Maker",
        "🔍 CRM & History", 
        "📊 Reports"
    ])
    
    st.divider()
    if st.button("Logout"): 
        st.session_state.logged_in = False
        st.rerun()

# 1. NEW ORDER
if menu == "📝 New Order":
    st.title("New Order & Invoice")
    c1, c2 = st.columns(2)
    cust_name = c1.text_input("Customer Name")
    cust_phone = c2.text_input("Phone")
    
    st.subheader("Add Items")
    ic1, ic2, ic3, ic4 = st.columns(4)
    i_type = ic1.selectbox("Type", ["Curtain", "Blinds", "Upholstery", "Wallpaper"])
    i_w = ic2.number_input("W (cm)", 0.0)
    i_h = ic3.number_input("H (cm)", 0.0)
    i_qty = ic4.number_input("Qty", 1)
    i_price = st.number_input("Unit Price", 0.0)
    i_note = st.text_input("Desc/Note")
    
    if st.button("Add Item"):
        total = 0
        if i_type == "Curtain":
            # Basic Logic: (W * 3 Fullness)
            fab_req = ((i_w/100) * 3) * ((i_h/100) + 0.2) * i_qty
            total = fab_req * i_price
        else:
            total = (i_w/100)*(i_h/100)*i_qty*i_price
        
        st.session_state.cart.append({
            "Type": i_type, "W": i_w, "H": i_h, "Qty": i_qty, 
            "Price": i_price, "Total": total, "Note": i_note
        })
        st.success("Added")
        
    if st.session_state.cart:
        df = pd.DataFrame(st.session_state.cart)
        st.dataframe(df)
        g_total = df['Total'].sum()
        st.metric("Total Bill", f"{g_total:,.2f}")
        
        if st.button("Save Order & Post Invoice"):
            if cust_name:
                ws = get_worksheet("sheet1")
                ws.append_row([str(datetime.date.today()), cust_name, cust_phone, g_total, json.dumps(st.session_state.cart), st.session_state.user_name])
                add_transaction(datetime.date.today(), cust_name, cust_phone, "Invoice", g_total, "Credit", "", "", "Cleared", "New Order", st.session_state.user_name)
                clear_cache()
                st.session_state.cart = []
                st.success("Saved Successfully!")

# 2. PAYMENTS
elif menu == "💰 Payments/Receipts":
    st.title("Receive Payment")
    c1, c2 = st.columns(2)
    p_name = c1.text_input("Customer Name")
    p_phone = c2.text_input("Phone")
    p_amt = st.number_input("Amount", min_value=0.0)
    p_mode = st.selectbox("Mode", ["Cash", "Cheque", "Transfer"])
    
    ref, c_date, status = "", "", "Cleared"
    if p_mode == "Cheque":
        c1, c2 = st.columns(2)
        ref = c1.text_input("Cheque No")
        c_date = c2.date_input("Cheque Date")
        status = "Pending"
    elif p_mode == "Transfer":
        ref = st.text_input("Trans ID")
        
    p_note = st.text_input("Note")
    
    if st.button("Save & Print Voucher"):
        if p_name and p_amt > 0:
            add_transaction(datetime.date.today(), p_name, p_phone, "Receipt", p_amt, p_mode, ref, c_date, status, p_note, st.session_state.user_name)
            st.success("Saved!")
            rec_no = f"REC-{int(time.time())}"
            pdf = create_receipt_pdf(str(datetime.date.today()), rec_no, p_name, p_amt, p_mode, ref, p_note)
            b64 = base64.b64encode(pdf).decode()
            st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Rec_{rec_no}.pdf" style="padding:10px; background-color:green; color:white; text-decoration:none; border-radius:5px;">📥 Download Voucher PDF</a>', unsafe_allow_html=True)

# 3. EXPENSES
elif menu == "💸 Expenses":
    st.title("Expenses (Job Costing)")
    with st.form("exp"):
        dt = st.date_input("Date")
        cat = st.selectbox("Category", ["Rent", "Salary", "Material Purchase", "Labour", "Other"])
        amt = st.number_input("Amount", min_value=0.0)
        note = st.text_input("Note")
        
        # Link to Project
        ws = get_worksheet("sheet1") # Only fetching names for dropdown
        if ws: cust_list = [f"{d['Name']}" for d in ws.get_all_records()]
        else: cust_list = []
        proj = st.selectbox("Link to Project", ["General"] + cust_list)
        
        if st.form_submit_button("Save Expense"):
            add_expense(dt, cat, amt, note, st.session_state.user_name, proj)
            st.success("Expense Recorded")

# 4. SUPPLIERS
elif menu == "🚛 Suppliers":
    st.title("Supplier Management")
    t1, t2, t3 = st.tabs(["New Purchase", "Payment", "Statement"])
    with t1:
        s_name = st.text_input("Supplier Name")
        s_amt = st.number_input("Bill Amount", min_value=0.0)
        s_ref = st.text_input("Inv No")
        if st.button("Save Purchase"):
            ws = get_worksheet("Suppliers")
            ws.append_row([str(datetime.date.today()), s_name, "Purchase", s_amt, s_ref, "", st.session_state.user_name])
            clear_cache()
            st.success("Saved")
    with t2:
        p_name = st.text_input("Pay to Name")
        p_amt = st.number_input("Pay Amount", min_value=0.0)
        p_ref = st.text_input("Ref/Cheque")
        if st.button("Save Payment"):
            ws = get_worksheet("Suppliers")
            ws.append_row([str(datetime.date.today()), p_name, "Payment", p_amt, p_ref, "", st.session_state.user_name])
            clear_cache()
            st.success("Payment Recorded")
    with t3:
        sh_name = st.text_input("Search Supplier")
        if st.button("Get Statement"):
            data = get_cached_data("Suppliers")
            s_data = [d for d in data if str(d['Supplier_Name']).lower() == sh_name.lower()]
            if s_data:
                pdf = create_statement_pdf(sh_name, s_data, is_supplier=True)
                b64 = base64.b64encode(pdf).decode()
                st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Stmt_{sh_name}.pdf">📥 Download PDF</a>', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(s_data))

# 5. RETURNS
elif menu == "↩️ Returns":
    st.title("Returns Manager")
    t1, t2 = st.tabs(["Sales Return", "Purchase Return"])
    with t1:
        r_name = st.text_input("Customer Name")
        r_amt = st.number_input("Return Value", min_value=0.0)
        r_reason = st.text_input("Reason")
        if st.button("Save Sales Return"):
            cn_no = f"CN-{int(time.time())}"
            add_transaction(datetime.date.today(), r_name, "", "Sales Return", r_amt, "Credit Note", cn_no, "", "Cleared", r_reason, st.session_state.user_name)
            st.success("Return Saved")
            pdf = create_credit_note_pdf(str(datetime.date.today()), cn_no, r_name, r_amt, r_reason)
            b64 = base64.b64encode(pdf).decode()
            st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="CN_{cn_no}.pdf">📥 Download Credit Note</a>', unsafe_allow_html=True)
    with t2:
        pr_name = st.text_input("Supplier Name")
        pr_amt = st.number_input("Refund Amount", min_value=0.0)
        if st.button("Save Purchase Return"):
            add_expense(datetime.date.today(), "Purchase Return", -abs(pr_amt), pr_name, st.session_state.user_name, "Stock")
            st.success("Expense Reduced")

# 6. QUOTATION MAKER
elif menu == "📜 Quotation Maker":
    st.title("Quotation Maker")
    q_name = st.text_input("To Name")
    q_sub = st.text_input("Subject")
    
    ic1, ic2, ic3, ic4 = st.columns(4)
    q_type = ic1.selectbox("Item", ["Curtain", "Blinds", "Sofa"])
    q_w = ic2.number_input("W", 0.0, key="qw")
    q_h = ic3.number_input("H", 0.0, key="qh")
    q_qty = ic4.number_input("Qty", 1, key="qq")
    q_price = st.number_input("Price", 0.0, key="qp")
    
    if st.button("Add to Quote"):
        tot = q_qty * q_price # Simplified
        st.session_state.cart.append({"Type": q_type, "W": q_w, "H": q_h, "Qty": q_qty, "Price": q_price, "Total": tot})
        
    if st.session_state.cart:
        df = pd.DataFrame(st.session_state.cart)
        st.dataframe(df)
        gt = df['Total'].sum()
        if st.button("Generate Quote PDF"):
            q_no = f"QT-{int(time.time())}"
            pdf = create_quotation_pdf(str(datetime.date.today()), q_no, q_name, st.session_state.cart, gt, q_sub)
            b64 = base64.b64encode(pdf).decode()
            st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Quote_{q_name}.pdf" style="padding:10px; background-color:blue; color:white;">📥 Download Quote</a>', unsafe_allow_html=True)
            if st.button("Clear"): st.session_state.cart = []

# 7. CRM & HISTORY
elif menu == "🔍 CRM & History":
    st.title("CRM Search")
    ph = st.text_input("Phone")
    if st.button("Find"):
        ws = get_worksheet("sheet1")
        if ws:
            d = ws.get_all_records()
            f = [x for x in d if str(x['Phone']) == ph]
            if f:
                st.success(f"Customer: {f[-1]['Name']}")
                st.dataframe(pd.DataFrame(f))
            else: st.warning("Not Found")

# 8. REPORTS
elif menu == "📊 Reports":
    st.title("Reports")
    opt = st.selectbox("Type", ["Customer Statement", "Profit & Loss"])
    
    if opt == "Customer Statement":
        ph = st.text_input("Phone")
        if st.button("Get PDF"):
            data = get_customer_ledger(ph)
            if data:
                pdf = create_statement_pdf(data[0]['Customer'], data)
                b64 = base64.b64encode(pdf).decode()
                st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Stmt.pdf">📥 Download PDF</a>', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(data))
    
    elif opt == "Profit & Loss":
        # Simple Income - Expense
        ws1 = get_cached_data("sheet1")
        ws2 = get_cached_data("Expenses")
        inc = sum([float(str(d['Total']).replace(',','')) for d in ws1])
        exp = sum([float(str(d['Amount']).replace(',','')) for d in ws2])
        prof = inc - exp
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Income", f"{inc:,.2f}")
        c2.metric("Total Expense", f"{exp:,.2f}")
        c3.metric("Net Profit", f"{prof:,.2f}")
