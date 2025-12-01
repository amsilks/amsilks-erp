import streamlit as st
import pandas as pd
import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
import base64
import time
import math # കണക്കുകൂട്ടലുകൾക്ക് ആവശ്യം

# --- APP CONFIGURATION ---
st.set_page_config(page_title="AMSilks ERP Pro", layout="wide", page_icon="🏢")

# --- CONSTANTS ---
OWNER_WHATSAPP = "97477070221"

# --- GOOGLE SHEET CONNECTION ---
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

# --- PDF GENERATORS ---
class PDF(FPDF):
    def header(self):
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

def create_receipt_pdf(date, r_no, name, amount, mode, ref, note):
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
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, 'PAYMENT RECEIPT', 1, 1, 'C', 1)
    pdf.ln(5)
    pdf.set_font('Arial', '', 11)
    pdf.cell(130, 8, f"No: {r_no}", 0, 0)
    pdf.cell(60, 8, f"Date: {date}", 0, 1, 'R')
    pdf.ln(10)
    pdf.set_font('Arial', '', 12)
    pdf.cell(50, 10, "Received From:", 0, 0)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, name, 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(50, 10, "Amount (QR):", 0, 0)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f"{amount:,.2f}", 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(50, 10, "Mode:", 0, 0)
    pdf.cell(0, 10, f"{mode} - {ref}", 0, 1)
    if note:
        pdf.cell(50, 10, "Note:", 0, 0)
        pdf.cell(0, 10, note, 0, 1)
    return pdf.output(dest='S').encode('latin-1')

def create_full_invoice_pdf(date, inv_no, name, phone, cart_items, total, discount, advance):
    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'INVOICE / ESTIMATE', 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 11)
    pdf.cell(120, 6, f"Customer: {name}", 0, 0)
    pdf.cell(0, 6, f"Date: {date}", 0, 1, 'R')
    pdf.cell(120, 6, f"Phone: {phone}", 0, 0)
    pdf.cell(0, 6, f"Ref: {inv_no}", 0, 1, 'R')
    pdf.ln(5)
    
    # Header
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(10, 10, "#", 1, 0, 'C', 1)
    pdf.cell(40, 10, "Location", 1, 0, 'C', 1)
    pdf.cell(60, 10, "Description", 1, 0, 'C', 1)
    pdf.cell(30, 10, "Size", 1, 0, 'C', 1)
    pdf.cell(15, 10, "Qty", 1, 0, 'C', 1)
    pdf.cell(35, 10, "Total", 1, 1, 'C', 1)
    
    pdf.set_font('Arial', '', 9)
    idx = 1
    for item in cart_items:
        # Location String
        loc = f"{item['Floor']}-{item['Room']}"
        if item.get('Tower'): loc = f"{item['Tower']} {loc}"
        
        # Description String
        desc = f"{item['Type']} {item.get('Note','')}"
        if item.get('Railroad'): desc += " (Railroad)"
        
        # Details: Cat/Fab
        details = f"{desc}\nCat: {item.get('Catalog','')} Fab: {item.get('FabNo','')}"
        
        size = f"{item['W']}x{item['H']}"
        
        # Multi-line cell handling (Simplified for FPDF)
        pdf.cell(10, 10, str(idx), 1, 0, 'C')
        pdf.cell(40, 10, loc[0:20], 1, 0, 'L') # Limit char
        pdf.cell(60, 10, details[0:35], 1, 0, 'L')
        pdf.cell(30, 10, size, 1, 0, 'C')
        pdf.cell(15, 10, str(item['Qty']), 1, 0, 'C')
        pdf.cell(35, 10, f"{item['TotalCost']:.2f}", 1, 1, 'R')
        idx += 1
        
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(155, 8, "Sub Total:", 1, 0, 'R')
    pdf.cell(35, 8, f"{total:.2f}", 1, 1, 'R')
    
    if discount > 0:
        pdf.cell(155, 8, "Discount:", 1, 0, 'R')
        pdf.cell(35, 8, f"-{discount:.2f}", 1, 1, 'R')
        
    net_total = total - discount
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(155, 10, "Grand Total:", 1, 0, 'R')
    pdf.cell(35, 10, f"{net_total:.2f}", 1, 1, 'R')
    
    if advance > 0:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(155, 8, "Advance Paid:", 1, 0, 'R')
        pdf.cell(35, 8, f"{advance:.2f}", 1, 1, 'R')
        pdf.cell(155, 8, "Balance Due:", 1, 0, 'R')
        pdf.cell(35, 8, f"{net_total - advance:.2f}", 1, 1, 'R')

    return pdf.output(dest='S').encode('latin-1')

# --- DATA FUNCTIONS ---
def add_transaction(date, name, phone, t_type, amount, mode, ref, c_date, status, note, user):
    ws = get_worksheet("Transactions")
    if ws:
        ws.append_row([str(date), name, phone, t_type, amount, mode, ref, str(c_date), status, note, user])
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
                    msg = f"🔔 CHEQUE: {c.get('Customer')} (QR {c.get('Amount')}) - {cd}"
                    st.warning(msg)
                    st.link_button("📲 WhatsApp Alert", f"https://wa.me/{OWNER_WHATSAPP}?text={msg}")
                    alert = True
            except: pass
    if alert: st.divider()

# --- MAIN APP ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
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
                else: st.error("Invalid Login")
    st.stop()

# --- DASHBOARD ---
show_cheque_alerts()

with st.sidebar:
    try: st.image("logo.png", width=200)
    except: pass
    st.write(f"User: **{st.session_state.user_name}**")
    menu = st.radio("Menu", ["📝 New Order", "💰 Payments", "💸 Expenses", "🚛 Suppliers", "🔍 History"])
    if st.button("Logout"): st.session_state.logged_in = False; st.rerun()

# 1. NEW ORDER (ADVANCED CALCULATOR FROM HTML)
if menu == "📝 New Order":
    st.title("New Order (Advanced)")
    
    # Customer Info
    c1, c2 = st.columns(2)
    cust_name = c1.text_input("Customer Name")
    cust_phone = c2.text_input("Phone")
    
    st.divider()
    st.subheader("Add Measurements")
    
    # --- Location Details ---
    col_loc1, col_loc2, col_loc3 = st.columns(3)
    b_type = col_loc1.selectbox("Building Type", ["House/Villa", "Tower/Building", "Other"])
    tower_name = ""
    if b_type == "Tower/Building":
        tower_name = col_loc1.text_input("Tower Name")
        
    floor = col_loc2.selectbox("Floor", ["Ground", "First", "Second", "Third", "Other"])
    if floor == "Other": floor = col_loc2.text_input("Type Floor")
    
    room = col_loc3.selectbox("Room", ["Living", "Master Bed", "Bed 1", "Bed 2", "Majlis", "Kitchen", "Other"])
    if room == "Other": room = col_loc3.text_input("Type Room")
    
    # --- Curtain Details ---
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    item_type = col_d1.selectbox("Type", ["Heavy Curtain", "Sheer Curtain", "Blackout", "Roller Blind", "Roman Blind", "Wooden Blind"])
    
    is_curtain = item_type in ["Heavy Curtain", "Sheer Curtain", "Blackout"]
    
    fullness = 3.0
    fab_width = 1.4
    railroad = False
    
    if is_curtain:
        # Fullness Logic
        full_opt = col_d2.selectbox("Fullness", ["Normal (1 x 3)", "Project (1 x 2)", "Custom"])
        if full_opt == "Custom":
            fullness = col_d2.number_input("Custom Ratio", 1.0, 5.0, 2.5)
        else:
            fullness = 3.0 if "Normal" in full_opt else 2.0
            
        # Fabric Width Logic
        fw_opt = col_d3.selectbox("Fabric Width", ["1.4 m (Standard)", "2.8 m (Wide)", "3.0 m (Wide)", "3.1 m (Wide)"])
        if "1.4" in fw_opt: fab_width = 1.4
        elif "2.8" in fw_opt: fab_width = 2.8
        elif "3.0" in fw_opt: fab_width = 3.0
        else: fab_width = 3.1
        
    # --- Item Specifics ---
    col_i1, col_i2 = st.columns(2)
    catalog = col_i1.text_input("Catalog Name")
    fab_no = col_i2.text_input("Fabric No")
    
    # --- Dimensions & Qty ---
    col_dim1, col_dim2, col_dim3 = st.columns(3)
    i_qty = col_dim1.number_input("Qty", 1, key="qty")
    w_cm = col_dim2.number_input("Width (cm)", 0.0)
    h_cm = col_dim3.number_input("Height (cm)", 0.0)
    note = st.text_input("Note / Remarks")
    
    # --- Pricing ---
    st.markdown("##### Pricing")
    col_p1, col_p2, col_p3 = st.columns(3)
    price_fab = col_p1.number_input("Fabric Price (per Unit)", 0.0)
    price_stitch = 0.0
    price_fix = 0.0
    
    if is_curtain:
        price_stitch = col_p2.number_input("Stitching (per Pcs)", 0.0)
        price_fix = col_p3.number_input("Fixing (per Pcs)", 0.0)
    
    # --- ADD BUTTON WITH HTML LOGIC ---
    if st.button("Calculate & Add Item", type="primary"):
        if w_cm > 0 and h_cm > 0:
            w_m = w_cm / 100
            h_m = h_cm / 100
            
            fab_req_cust = 0
            fab_req_supp = 0
            calc_note = ""
            
            # --- THE LOGIC FROM HTML ---
            if is_curtain:
                req_h = h_m + 0.20 # Extra for hemming
                
                # Railroading Check
                if fab_width > 2.0 and req_h <= fab_width:
                    # Railroading Applied
                    fab_req_cust = w_m * fullness
                    railroad = True
                    calc_note = f"Railroad (Wx{fullness})"
                else:
                    # Vertical Panels
                    panels = math.ceil((w_m * fullness) / fab_width)
                    if panels < 1: panels = 1
                    fab_req_cust = panels * req_h
                    calc_note = f"Vertical ({panels} Pcs x {req_h:.2f})"
                
                fab_req_supp = fab_req_cust # Supplier qty same for now
                
            else:
                # Blinds Logic
                raw_area = w_m * h_m
                fab_req_cust = 2.0 if raw_area < 2.0 else raw_area
                fab_req_supp = 1.5 if raw_area < 1.5 else raw_area
                calc_note = "Area Calc"
            
            # --- Cost Calculation ---
            total_fab_cost = fab_req_cust * i_qty * price_fab
            total_stitch = price_stitch * i_qty
            total_fix = price_fix * i_qty
            
            total_item_cost = total_fab_cost + total_stitch + total_fix
            
            # --- Add to Cart ---
            st.session_state.cart.append({
                "Building": b_type, "Tower": tower_name, "Floor": floor, "Room": room,
                "Type": item_type, "Catalog": catalog, "FabNo": fab_no,
                "W": w_cm, "H": h_cm, "Qty": i_qty, "Note": note,
                "Fullness": fullness, "FabWidth": fab_width, "Railroad": railroad,
                "CalcNote": calc_note, "FabReq": fab_req_cust,
                "PriceFab": price_fab, "PriceStitch": price_stitch, "PriceFix": price_fix,
                "TotalCost": total_item_cost
            })
            st.success(f"Added! Method: {calc_note}")
        else:
            st.error("Please enter Width and Height")

    # --- DRAFT TABLE ---
    if st.session_state.cart:
        st.divider()
        st.subheader("Items in Cart")
        
        # Display simplified table
        disp_data = []
        grand_total = 0
        for idx, item in enumerate(st.session_state.cart):
            grand_total += item['TotalCost']
            loc = f"{item['Floor']} - {item['Room']}"
            desc = f"{item['Type']} ({item['CalcNote']})"
            disp_data.append({
                "Loc": loc, "Desc": desc, 
                "Size": f"{item['W']}x{item['H']}", 
                "Qty": item['Qty'], 
                "Total": f"{item['TotalCost']:.2f}"
            })
        
        st.table(pd.DataFrame(disp_data))
        st.metric("Total Estimate", f"QR {grand_total:,.2f}")
        
        # --- Finalize ---
        c_fin1, c_fin2, c_fin3 = st.columns(3)
        disc = c_fin1.number_input("Discount", 0.0)
        adv = c_fin2.number_input("Advance Paid", 0.0)
        
        if st.button("💾 Save Order & Generate Invoice"):
            if cust_name:
                net_total = grand_total - disc
                
                # 1. Save to Sheet
                ws = get_worksheet("sheet1")
                ws.append_row([str(datetime.date.today()), cust_name, cust_phone, net_total, json.dumps(st.session_state.cart), st.session_state.user_name])
                
                # 2. Add to Ledger
                add_transaction(datetime.date.today(), cust_name, cust_phone, "Invoice", net_total, "Credit", "", "", "Cleared", "New Order", st.session_state.user_name)
                
                # 3. If Advance paid, add receipt
                if adv > 0:
                     add_transaction(datetime.date.today(), cust_name, cust_phone, "Receipt", adv, "Cash", "Advance", "", "Cleared", "Order Advance", st.session_state.user_name)

                # 4. Generate PDF
                inv_no = f"INV-{int(time.time())}"
                pdf = create_full_invoice_pdf(str(datetime.date.today()), inv_no, cust_name, cust_phone, st.session_state.cart, grand_total, disc, adv)
                b64 = base64.b64encode(pdf).decode()
                st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Invoice_{cust_name}.pdf" style="padding:10px; background-color:green; color:white; border-radius:5px;">📥 Download Invoice PDF</a>', unsafe_allow_html=True)
                
                # Clear
                clear_cache()
                st.session_state.cart = []
                st.success("Order Processed Successfully!")
            else:
                st.error("Customer Name is required!")
        
        if st.button("Clear Cart"):
            st.session_state.cart = []
            st.rerun()

# 2. PAYMENTS
elif menu == "💰 Payments":
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
    
    p_note = st.text_input("Note")
    
    if st.button("Save & Print Voucher"):
        if p_name and p_amt > 0:
            add_transaction(datetime.date.today(), p_name, p_phone, "Receipt", p_amt, p_mode, ref, c_date, status, p_note, st.session_state.user_name)
            st.success("Saved!")
            rec_no = f"REC-{int(time.time())}"
            pdf = create_receipt_pdf(str(datetime.date.today()), rec_no, p_name, p_amt, p_mode, ref, p_note)
            b64 = base64.b64encode(pdf).decode()
            st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Rec_{rec_no}.pdf">📥 Download Voucher</a>', unsafe_allow_html=True)

# 3. EXPENSES
elif menu == "💸 Expenses":
    st.title("Expenses")
    with st.form("exp"):
        dt = st.date_input("Date")
        cat = st.selectbox("Category", ["Rent", "Salary", "Purchase", "Other"])
        amt = st.number_input("Amount", min_value=0.0)
        note = st.text_input("Note")
        if st.form_submit_button("Save"):
            ws_exp = get_worksheet("Expenses")
            ws_exp.append_row([str(dt), cat, amt, note, st.session_state.user_name, "General"])
            clear_cache()
            st.success("Added")

# 4. SUPPLIERS
elif menu == "🚛 Suppliers":
    st.title("Suppliers")
    s_name = st.text_input("Supplier Name")
    s_amt = st.number_input("Amount")
    if st.button("Save Purchase (Credit)"):
        ws = get_worksheet("Suppliers")
        ws.append_row([str(datetime.date.today()), s_name, "Purchase", s_amt, "", "", st.session_state.user_name])
        clear_cache()
        st.success("Saved")

# 5. HISTORY
elif menu == "🔍 History":
    st.title("Search")
    ph = st.text_input("Phone")
    if st.button("Search"):
        data = get_cached_data("sheet1")
        res = [d for d in data if str(d['Phone']) == ph]
        if res: st.dataframe(pd.DataFrame(res))
        else: st.warning("Not Found")

