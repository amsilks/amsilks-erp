import streamlit as st
import pandas as pd
import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
import base64
import time
import math

# --- APP CONFIG ---
st.set_page_config(page_title="AMSilks ERP Ultimate", layout="wide", page_icon="🏢")

# --- CONSTANTS ---
OWNER_WHATSAPP = "97477070221" 
LOGO_FILE = "1001002703.jpg"

# --- GOOGLE CONNECTION ---
def get_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        if "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        return gspread.authorize(creds)
    except Exception as e: return None

def get_worksheet(name):
    client = get_client()
    try: return client.open("AMSilks_Orders").worksheet(name) if client else None
    except: return None

# --- CACHING ---
@st.cache_data(ttl=600)
def get_cached_data(sheet_name):
    ws = get_worksheet(sheet_name)
    if ws: return ws.get_all_records()
    return []

def clear_cache():
    st.cache_data.clear()

# --- PDF GENERATOR ---
class PDF(FPDF):
    def header(self):
        try: self.image(LOGO_FILE, 10, 8, 35)
        except: 
            try: self.image('logo.png', 10, 8, 35)
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

def create_full_invoice_pdf(date, inv_no, name, phone, cart_items, total, discount, advance):
    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'INVOICE', 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font('Arial', '', 11)
    pdf.cell(120, 6, f"Customer: {name}", 0, 0)
    pdf.cell(0, 6, f"Date: {date}", 0, 1, 'R')
    pdf.cell(120, 6, f"Phone: {phone}", 0, 0)
    pdf.cell(0, 6, f"Ref: {inv_no}", 0, 1, 'R')
    pdf.ln(5)
    
    # Table
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(10, 10, "#", 1, 0, 'C', 1)
    pdf.cell(60, 10, "Description", 1, 0, 'C', 1)
    pdf.cell(30, 10, "Size", 1, 0, 'C', 1)
    pdf.cell(15, 10, "Qty", 1, 0, 'C', 1)
    pdf.cell(35, 10, "Rate", 1, 0, 'C', 1)
    pdf.cell(35, 10, "Total", 1, 1, 'C', 1)
    
    pdf.set_font('Arial', '', 9)
    idx = 1
    for item in cart_items:
        # Check if it's a Direct Item or Calculated Item
        if item.get('IsDirect'):
            desc = f"{item['ItemName']} {item.get('Note','')}"
            size = "-"
            rate = item['Price']
        else:
            desc = f"{item['Type']} {item.get('CalcNote','')}"
            size = f"{item['W']}x{item['H']}"
            rate = item.get('Price', 0) # This might be approx for calculated items
        
        pdf.cell(10, 10, str(idx), 1, 0, 'C')
        pdf.cell(60, 10, desc[0:35], 1, 0, 'L')
        pdf.cell(30, 10, size, 1, 0, 'C')
        pdf.cell(15, 10, str(item['Qty']), 1, 0, 'C')
        pdf.cell(35, 10, f"{rate:.2f}", 1, 0, 'R')
        pdf.cell(35, 10, f"{item['TotalCost']:.2f}", 1, 1, 'R')
        idx += 1
        
    pdf.ln(5)
    net = total - discount
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(150, 10, "Grand Total:", 1, 0, 'R')
    pdf.cell(35, 10, f"{net:.2f}", 1, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

def create_receipt_pdf(date, r_no, name, amount, mode, ref, note):
    pdf = FPDF(orientation='L', unit='mm', format='A5')
    pdf.add_page()
    pdf.rect(5, 5, 200, 138)
    try: pdf.image(LOGO_FILE, 10, 10, 25)
    except: pass
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(30)
    pdf.cell(0, 10, 'AMSilks Trading W.L.L.', 0, 1, 'L')
    pdf.ln(15)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 10, 'PAYMENT VOUCHER', 1, 1, 'C', 1)
    pdf.ln(5)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Receipt No: {r_no} | Date: {date}", 0, 1)
    pdf.ln(5)
    pdf.cell(50, 10, "Paid To / Recvd From:", 0, 0)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, name, 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(50, 10, "Amount (QR):", 0, 0)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f"{amount:,.2f}", 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(50, 10, "Description:", 0, 0)
    pdf.cell(0, 10, f"{note} ({mode}-{ref})", 0, 1)
    return pdf.output(dest='S').encode('latin-1')

# --- DATA FUNCTIONS ---
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

def check_login(u, p):
    ws = get_worksheet("Users")
    if ws:
        users = ws.get_all_records()
        for user in users:
            if str(user['Username']) == u and str(user['Password']) == p: return user
    return None

def show_cheque_alerts():
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    alert = False
    data = get_cached_data("Transactions")
    if data:
        pending = [d for d in data if d.get('Mode') == 'Cheque' and d.get('Status') == 'Pending']
        for c in pending:
            try:
                cd = datetime.datetime.strptime(str(c.get('Cheque_Date')), "%Y-%m-%d").date()
                if cd == today or cd == tomorrow:
                    st.warning(f"🔔 CHEQUE ALERT: {c.get('Customer')} (QR {c.get('Amount')}) - {cd}")
                    alert = True
            except: pass
    if alert: st.divider()

# --- MAIN APP ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        try: st.image(LOGO_FILE, width=200)
        except: st.title("AMSilks Login")
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                user = check_login(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_name = user['Name']
                    st.rerun()
                else: st.error("Invalid Credentials")
    st.stop()

show_cheque_alerts()

with st.sidebar:
    try: st.image(LOGO_FILE, width=200)
    except: st.header("AMSilks")
    st.write(f"User: **{st.session_state.user_name}**")
    menu = st.radio("Menu", [
        "📝 New Order", 
        "💰 Payments/Receipts", 
        "💸 Expenses (Projects)", 
        "👥 Partners Area", 
        "🚛 Suppliers", 
        "📊 Reports"
    ])
    st.divider()
    if st.button("Logout"): st.session_state.logged_in = False; st.rerun()

# 1. NEW ORDER (Direct & Calculated)
if menu == "📝 New Order":
    st.title("New Order & Billing")
    c1, c2 = st.columns(2)
    cust_name = c1.text_input("Customer Name")
    cust_phone = c2.text_input("Phone")
    
    st.divider()
    
    # Selection: Calculator or Direct Item
    mode_tab1, mode_tab2 = st.tabs(["🧮 Calculator Mode", "📦 Direct Item Entry"])
    
    # --- TAB 1: CALCULATOR ---
    with mode_tab1:
        st.subheader("Curtain/Blind Calculator")
        l1, l2 = st.columns(2)
        floor = l1.selectbox("Floor", ["Ground", "First", "Second", "Other"])
        room = l2.selectbox("Room", ["Living", "Master Bed", "Majlis", "Other"])
        
        d1, d2, d3 = st.columns(3)
        i_type = d1.selectbox("Type", ["Heavy Curtain", "Sheer", "Blinds"])
        is_curtain = "Curtain" in i_type or "Sheer" in i_type
        
        fullness = 2.5
        fab_width = 1.4
        
        if is_curtain:
            fullness = d2.number_input("Fullness Ratio", 1.5, 4.0, 3.0)
            fw_opt = d3.selectbox("Fab Width", ["1.4m", "2.8m", "3.0m"])
            fab_width = float(fw_opt.split('m')[0])
            
        cat = st.text_input("Catalog/Fab No")
        
        p1, p2, p3, p4 = st.columns(4)
        w_cm = p1.number_input("W (cm)", 0.0)
        h_cm = p2.number_input("H (cm)", 0.0)
        qty = p3.number_input("Qty", 1)
        price = p4.number_input("Price (Fab)", 0.0)
        
        stitch = st.number_input("Stitching Charge (Total)", 0.0)
        
        if st.button("Calculate & Add"):
            if w_cm > 0:
                w_m = w_cm/100; h_m = h_cm/100
                fab_req = 0; note = ""
                if is_curtain:
                    req_h = h_m + 0.2
                    if fab_width > 2.0 and req_h <= fab_width:
                        fab_req = w_m * fullness
                        note = "Railroad"
                    else:
                        panels = math.ceil((w_m * fullness)/fab_width)
                        fab_req = panels * req_h
                        note = f"Vertical ({panels} Pcs)"
                else:
                    fab_req = w_m * h_m # Simple Area
                    note = "Area"
                
                tot_cost = (fab_req * qty * price) + stitch
                
                st.session_state.cart.append({
                    "IsDirect": False, "Type": i_type, "Floor": floor, "Room": room,
                    "W": w_cm, "H": h_cm, "Qty": qty, "CalcNote": note,
                    "Price": price, "TotalCost": tot_cost, "Catalog": cat
                })
                st.success(f"Added! Fab Req: {fab_req:.2f}m")

    # --- TAB 2: DIRECT ENTRY (New Requirement) ---
    with mode_tab2:
        st.subheader("Direct Item Entry (No Calculation)")
        di_name = st.text_input("Item Name (e.g. Hooks, Rods)")
        di_col1, di_col2 = st.columns(2)
        di_qty = di_col1.number_input("Quantity", 1, key="di_qty")
        di_price = di_col2.number_input("Total Price", 0.0, key="di_price")
        di_note = st.text_input("Note", key="di_note")
        
        if st.button("Add Direct Item"):
            if di_name and di_price > 0:
                st.session_state.cart.append({
                    "IsDirect": True, "ItemName": di_name, "Qty": di_qty, 
                    "Price": di_price/di_qty, "TotalCost": di_price, "Note": di_note
                })
                st.success("Item Added Directly!")

    # --- CART DISPLAY ---
    if st.session_state.cart:
        st.divider()
        st.subheader("Order Summary")
        
        # Simple Display
        disp_data = []
        g_total = 0
        for item in st.session_state.cart:
            g_total += item['TotalCost']
            if item.get('IsDirect'):
                desc = item['ItemName']
            else:
                desc = f"{item['Type']} ({item['Room']})"
            disp_data.append({"Item": desc, "Qty": item['Qty'], "Cost": item['TotalCost']})
            
        st.table(pd.DataFrame(disp_data))
        
        c_fin1, c_fin2 = st.columns(2)
        disc = c_fin1.number_input("Discount", 0.0)
        adv = c_fin2.number_input("Advance", 0.0)
        
        net_total = g_total - disc
        st.metric("Net Total", f"QR {net_total:,.2f}")
        
        if st.button("💾 Save Order & Generate Invoice"):
            if cust_name:
                # Save Order
                ws = get_worksheet("sheet1")
                ws.append_row([str(datetime.date.today()), cust_name, cust_phone, net_total, json.dumps(st.session_state.cart), st.session_state.user_name])
                
                # Ledger
                add_transaction(datetime.date.today(), cust_name, cust_phone, "Invoice", net_total, "Credit", "", "", "Cleared", "New Order", st.session_state.user_name)
                
                if adv > 0:
                    add_transaction(datetime.date.today(), cust_name, cust_phone, "Receipt", adv, "Cash", "Advance", "", "Cleared", "Advance", st.session_state.user_name)
                
                # PDF
                inv_no = f"INV-{int(time.time())}"
                pdf = create_full_invoice_pdf(str(datetime.date.today()), inv_no, cust_name, cust_phone, st.session_state.cart, g_total, disc, adv)
                b64 = base64.b64encode(pdf).decode()
                st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Invoice_{cust_name}.pdf" style="padding:10px; background-color:green; color:white;">📥 Download Invoice PDF</a>', unsafe_allow_html=True)
                
                clear_cache()
                st.session_state.cart = []
                st.success("Order Processed!")

# 2. PAYMENTS
elif menu == "💰 Payments/Receipts":
    st.title("Payments & Receipts")
    name = st.text_input("Name (Customer/Supplier)")
    c1, c2 = st.columns(2)
    amt = c1.number_input("Amount", min_value=0.0)
    mode = c2.selectbox("Mode", ["Cash", "Cheque", "Transfer"])
    
    ref, c_date, status = "", "", "Cleared"
    if mode == "Cheque":
        ref = st.text_input("Cheque No")
        c_date = st.date_input("Cheque Date")
        status = "Pending"
    
    note = st.text_input("Note")
    
    if st.button("Save Receipt"):
        add_transaction(datetime.date.today(), name, "", "Receipt", amt, mode, ref, c_date, status, note, st.session_state.user_name)
        st.success("Receipt Saved")
        
        # Voucher PDF
        rec_no = f"RC-{int(time.time())}"
        pdf = create_receipt_pdf(str(datetime.date.today()), rec_no, name, amt, mode, ref, note)
        b64 = base64.b64encode(pdf).decode()
        st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Voucher_{rec_no}.pdf">📥 Download Voucher</a>', unsafe_allow_html=True)

# 3. EXPENSES (With Commission & Sub-Contract)
elif menu == "💸 Expenses (Projects)":
    st.title("Expenses & Job Costing")
    
    with st.form("exp_form"):
        dt = st.date_input("Date")
        # Added Commission & Sub-Contract here
        cat = st.selectbox("Category", [
            "Material Purchase", 
            "Sub-Contract / Labour",  # For Subcontractors
            "Commission / Brokerage", # For Commission
            "Rent", "Salary", "Transport", "Other"
        ])
        amt = st.number_input("Amount", min_value=0.0)
        note = st.text_input("Description / Sub-contractor Name")
        
        # Project Linking
        st.write("Link to Project? (Important for Profit Calc)")
        ws = get_cached_data("sheet1")
        cust_list = list(set([f"{d['Name']}" for d in ws])) if ws else []
        proj = st.selectbox("Select Project", ["General (Shop Expense)"] + cust_list)
        
        if st.form_submit_button("Save Expense"):
            add_expense(dt, cat, amt, note, st.session_state.user_name, proj)
            st.success(f"Saved! Linked to {proj}")

# 4. PARTNERS AREA (New Requirement)
elif menu == "👥 Partners Area":
    st.title("Partners Management")
    st.info("Record cash withdrawn by partners here.")
    
    with st.form("partner_form"):
        p_name = st.text_input("Partner Name")
        p_amt = st.number_input("Withdrawal Amount", min_value=0.0)
        p_mode = st.selectbox("Mode", ["Cash", "Transfer"])
        p_note = st.text_input("Note")
        
        if st.form_submit_button("Record Withdrawal"):
            # Save to Transactions but mark as Partner Withdrawal
            add_transaction(datetime.date.today(), p_name, "Partner", "Withdrawal", p_amt, p_mode, "", "", "Cleared", p_note, st.session_state.user_name)
            st.success(f"Recorded withdrawal by {p_name}")

# 5. SUPPLIERS
elif menu == "🚛 Suppliers":
    st.title("Supplier Management")
    t1, t2 = st.tabs(["New Purchase", "Payment"])
    with t1:
        s_name = st.text_input("Supplier Name")
        s_amt = st.number_input("Bill Amount")
        if st.button("Save Purchase"):
            ws = get_worksheet("Suppliers")
            ws.append_row([str(datetime.date.today()), s_name, "Purchase", s_amt, "", "", st.session_state.user_name])
            clear_cache()
            st.success("Saved")
    with t2:
        p_name = st.text_input("Pay to Name")
        p_amt = st.number_input("Pay Amount")
        if st.button("Save Payment"):
            ws = get_worksheet("Suppliers")
            ws.append_row([str(datetime.date.today()), p_name, "Payment", p_amt, "", "", st.session_state.user_name])
            clear_cache()
            st.success("Saved")

# 6. REPORTS
elif menu == "📊 Reports":
    st.title("Business Reports")
    
    type_ = st.selectbox("Report Type", ["Project Profit Analysis", "Shop Profit & Loss"])
    
    if type_ == "Project Profit Analysis":
        st.subheader("Select a Project to analyze")
        ws = get_cached_data("sheet1")
        cust_list = list(set([f"{d['Name']}" for d in ws])) if ws else []
        sel_proj = st.selectbox("Project Name", cust_list)
        
        if st.button("Analyze Project"):
            # Income
            inc_data = [d for d in ws if d['Name'] == sel_proj]
            tot_inc = sum([float(str(d['Total']).replace(',','')) for d in inc_data])
            
            # Expenses (Including Commission & Sub-contract)
            exp_ws = get_cached_data("Expenses")
            proj_exp = [d for d in exp_ws if str(d.get('Project_Ref')).strip() == sel_proj.strip()]
            tot_exp = sum([float(str(d['Amount']).replace(',','')) for d in proj_exp])
            
            profit = tot_inc - tot_exp
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Income", f"{tot_inc:,.2f}")
            c2.metric("Total Expense (Mat+Comm+Sub)", f"{tot_exp:,.2f}")
            c3.metric("Project Profit", f"{profit:,.2f}")
            
            st.write("### Expense Breakdown")
            if proj_exp:
                st.dataframe(pd.DataFrame(proj_exp)[['Date', 'Category', 'Amount', 'Note']])
            else: st.info("No expenses recorded yet.")
