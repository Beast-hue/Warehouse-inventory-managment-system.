import os
import hmac
import hashlib
from datetime import date, datetime
from io import BytesIO

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from mysql.connector import Error

from database import (
    initialize_database, get_connection, create_first_admin, authenticate_user,
    get_user_count, get_dashboard_stats, get_low_stock_products, get_products,
    get_categories, add_category, add_product, update_product, delete_product,
    record_stock_transaction, get_transactions, get_orders, add_order,
    update_order_status, get_users, add_user, update_user_role
)

load_dotenv()

st.set_page_config(
    page_title="Warehouse Inventory Management",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------- Styling ---------------------------
st.markdown("""
<style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    .main-title {font-size: 2rem; font-weight: 750; margin-bottom: 0.15rem;}
    .sub-title {color: #6b7280; margin-bottom: 1.25rem;}
    div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.22); padding: 14px; border-radius: 12px;}
    .alert-banner {padding: 12px 16px; border-radius: 10px; border: 1px solid #e0a000; background: rgba(255,190,0,.10); margin-bottom: 8px;}
    .ok-banner {padding: 12px 16px; border-radius: 10px; border: 1px solid #159957; background: rgba(21,153,87,.08);}
</style>
""", unsafe_allow_html=True)

def page_header(title, subtitle=""):
    st.markdown(f'<div class="main-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="sub-title">{subtitle}</div>', unsafe_allow_html=True)

def init_state():
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("page", "Dashboard")

def show_database_error(err):
    st.error("Could not connect to MySQL. Check the settings in your `.env` file and make sure the MySQL server is running.")
    with st.expander("Technical details"):
        st.code(str(err))
    st.info("See README.md for setup instructions.")

@st.cache_resource
def setup_db():
    return initialize_database()

init_state()

try:
    setup_db()
except Exception as e:
    st.title("📦 Warehouse Inventory Management System")
    show_database_error(e)
    st.stop()

# --------------------------- First admin setup ---------------------------
if get_user_count() == 0:
    st.title("📦 Warehouse Inventory Management System")
    st.caption("Initial setup — create the first administrator account.")
    st.warning("No user accounts exist yet. Create your administrator account to start.")
    with st.form("first_admin_form"):
        name = st.text_input("Full name")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create administrator", type="primary")
    if submitted:
        if not name.strip() or not username.strip() or not password:
            st.error("Please fill in every field.")
        elif len(password) < 8:
            st.error("Use a password with at least 8 characters.")
        elif password != confirm:
            st.error("Passwords do not match.")
        else:
            try:
                create_first_admin(name.strip(), username.strip(), password)
                st.success("Administrator created. You can now log in.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not create administrator: {e}")
    st.stop()

# --------------------------- Login ---------------------------
if st.session_state.user is None:
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("# 📦 Warehouse Inventory")
        st.markdown("### Inventory, transactions and alerts in one place")
        st.write("A simple warehouse management website for administrators and storekeepers.")
        st.markdown("- Live inventory overview")
        st.markdown("- Automatic low-stock warnings")
        st.markdown("- Incoming and outgoing stock records")
        st.markdown("- Order tracking and downloadable reports")
    with right:
        st.subheader("Sign in")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
        if submitted:
            user = authenticate_user(username.strip(), password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Incorrect username or password.")
    st.stop()

user = st.session_state.user
is_admin = user["role"] == "Admin"

# --------------------------- Sidebar ---------------------------
with st.sidebar:
    st.markdown("## 📦 Warehouse IMS")
    st.caption("Inventory Management System")
    st.divider()
    st.write(f"**{user['full_name']}**")
    st.caption(f"Role: {user['role']}")
    st.divider()
    pages = ["Dashboard", "Inventory", "Stock Transactions", "Order Tracking", "Reports"]
    if is_admin:
        pages.append("User Management")
    selected_page = st.radio("Navigation", pages, index=pages.index(st.session_state.page) if st.session_state.page in pages else 0)
    st.session_state.page = selected_page
    low_count = len(get_low_stock_products())
    if low_count:
        st.warning(f"⚠️ {low_count} low-stock item(s)")
    else:
        st.success("✓ Stock levels OK")
    if st.button("Log out", use_container_width=True):
        st.session_state.user = None
        st.session_state.page = "Dashboard"
        st.rerun()

# --------------------------- Dashboard ---------------------------
if selected_page == "Dashboard":
    page_header("Dashboard", "A live overview of your warehouse inventory.")
    low_stock = get_low_stock_products()
    stats = get_dashboard_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Product types", stats["product_types"])
    c2.metric("Units in stock", f"{stats['units_in_stock']:,}")
    low_stock_count = len(low_stock)
    c3.metric("Low-stock items",low_stock_count,delta="Needs attention" if low_stock_count > 0 else "All good",delta_color="inverse" if low_stock_count > 0 else "normal")
    c4.metric("Categories", stats["categories"])
    st.divider()
    if not low_stock.empty:
        st.subheader("🔔 Low-stock alerts")
        st.caption("Website notifications appear whenever quantity is at or below the product's reorder level.")
        for _, item in low_stock.iterrows():
            st.markdown(
                f"<div class='alert-banner'><b>⚠️ {item['product_name']}</b> "
                f"({item['sku']}) — only <b>{item['quantity']}</b> unit(s) left; "
                f"reorder level: {item['reorder_level']}. Location: {item['bin_location'] or 'Not set'}.</div>",
                unsafe_allow_html=True
            )
    else:
        st.markdown('<div class="ok-banner">✓ No low-stock alerts. All products are above their reorder levels.</div>', unsafe_allow_html=True)
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Inventory by category")
        products = get_products()
        if not products.empty:
            chart = products.groupby("category_name", dropna=False)["quantity"].sum().reset_index()
            chart["category_name"] = chart["category_name"].fillna("Uncategorized")
            st.bar_chart(chart.set_index("category_name"))
        else:
            st.info("Add products to see category stock totals.")
    with right:
        st.subheader("Recent stock activity")
        tx = get_transactions(limit=8)
        if tx.empty:
            st.info("No stock transactions recorded yet.")
        else:
            st.dataframe(tx[["created_at", "product_name", "transaction_type", "quantity", "username", "notes"]], use_container_width=True, hide_index=True)

# --------------------------- Inventory ---------------------------
elif selected_page == "Inventory":
    page_header("Inventory", "Manage products, stock levels, categories and warehouse locations.")
    tab1, tab2, tab3 = st.tabs(["View & Search", "Add Product", "Categories"])
    with tab1:
        products = get_products()
        search = st.text_input("Search by product name, SKU, category or bin location")
        if not products.empty and search.strip():
            mask = products.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
            products = products[mask]
        if products.empty:
            st.info("No products found. Add your first product using the Add Product tab.")
        else:
            st.dataframe(products, use_container_width=True, hide_index=True)
            st.download_button("Download inventory CSV", products.to_csv(index=False).encode("utf-8-sig"),
                               file_name="warehouse_inventory.csv", mime="text/csv")
        if is_admin and not products.empty:
            st.markdown("#### Edit or delete a product")
            options = {f"{r['product_name']} ({r['sku']}) — ID {r['id']}": int(r["id"]) for _, r in products.iterrows()}
            chosen = st.selectbox("Choose product", list(options.keys()))
            pid = options[chosen]
            current = products[products["id"] == pid].iloc[0]
            with st.form("edit_product_form"):
                ename = st.text_input("Product name", str(current["product_name"]))
                esku = st.text_input("SKU", str(current["sku"]))
                ecats = get_categories()
                cat_options = {r["category_name"]: int(r["id"]) for _, r in ecats.iterrows()}
                cat_names = list(cat_options.keys())
                current_cat = str(current["category_name"]) if pd.notna(current["category_name"]) else ""
                ecat = st.selectbox("Category", ["Uncategorized"] + cat_names,
                                    index=(["Uncategorized"] + cat_names).index(current_cat) if current_cat in cat_names else 0)
                ereorder = st.number_input("Reorder level", min_value=0, value=int(current["reorder_level"]))
                elocation = st.text_input("Bin location", str(current["bin_location"] or ""))
                eprice = st.number_input("Unit price (₹)", min_value=0.0, value=float(current["unit_price"]), step=1.0)
                save_edit = st.form_submit_button("Save product details")
            if save_edit:
                try:
                    update_product(pid, ename.strip(), esku.strip(), cat_options.get(ecat), int(ereorder), elocation.strip(), float(eprice))
                    st.success("Product details updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not update product: {e}")
            with st.popover("Delete selected product"):
                st.warning("This permanently deletes the product and may be blocked if it has transaction history.")
                confirm_delete = st.checkbox("I understand and want to delete this product")
                if st.button("Confirm delete", type="primary", disabled=not confirm_delete):
                    try:
                        delete_product(pid)
                        st.success("Product deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not delete product: {e}")
    with tab2:
        categories = get_categories()
        cat_map = {r["category_name"]: int(r["id"]) for _, r in categories.iterrows()}
        with st.form("add_product_form", clear_on_submit=True):
            pname = st.text_input("Product name *")
            sku = st.text_input("SKU / item code *")
            cat_choice = st.selectbox("Category", ["Uncategorized"] + list(cat_map.keys()))
            quantity = st.number_input("Opening quantity", min_value=0, value=0, step=1)
            reorder = st.number_input("Low-stock alert threshold", min_value=0, value=10, step=1)
            location = st.text_input("Warehouse bin / shelf location", placeholder="e.g. A-01-03")
            unit_price = st.number_input("Unit price (₹)", min_value=0.0, value=0.0, step=1.0)
            add_submitted = st.form_submit_button("Add product", type="primary")
        if add_submitted:
            if not pname.strip() or not sku.strip():
                st.error("Product name and SKU are required.")
            else:
                try:
                    pid = add_product(pname.strip(), sku.strip(), cat_map.get(cat_choice), int(quantity), int(reorder), location.strip(), float(unit_price))
                    if quantity:
                        record_stock_transaction(pid, "IN", int(quantity), user["id"], "Opening stock")
                    st.success("Product added successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not add product: {e}")
    with tab3:
        st.subheader("Product categories")
        cats = get_categories()
        if not cats.empty:
            st.dataframe(cats, use_container_width=True, hide_index=True)
        with st.form("add_category_form", clear_on_submit=True):
            new_category = st.text_input("New category name")
            category_submitted = st.form_submit_button("Add category")
        if category_submitted:
            if not new_category.strip():
                st.error("Enter a category name.")
            else:
                try:
                    add_category(new_category.strip())
                    st.success("Category added.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not add category: {e}")

# --------------------------- Stock Transactions ---------------------------
elif selected_page == "Stock Transactions":
    page_header("Stock Transactions", "Record incoming stock and outgoing dispatches. Stock is updated automatically.")
    products = get_products()
    if products.empty:
        st.info("Add a product before recording stock transactions.")
    else:
        product_map = {f"{r['product_name']} ({r['sku']}) — available: {r['quantity']}": int(r["id"]) for _, r in products.iterrows()}
        with st.form("stock_tx_form", clear_on_submit=True):
            chosen_product = st.selectbox("Product", list(product_map.keys()))
            tx_type = st.selectbox("Transaction type", ["IN", "OUT"])
            tx_qty = st.number_input("Quantity", min_value=1, value=1, step=1)
            notes = st.text_input("Notes / reference", placeholder="e.g. supplier invoice or dispatch ID")
            tx_submit = st.form_submit_button("Save transaction", type="primary")
        if tx_submit:
            try:
                record_stock_transaction(product_map[chosen_product], tx_type, int(tx_qty), user["id"], notes.strip())
                st.success("Transaction recorded and inventory updated.")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    st.subheader("Transaction history")
    tx = get_transactions()
    if tx.empty:
        st.info("No transactions yet.")
    else:
        st.dataframe(tx, use_container_width=True, hide_index=True)
        st.download_button("Export transactions CSV", tx.to_csv(index=False).encode("utf-8-sig"),
                           file_name="stock_transactions.csv", mime="text/csv")

# --------------------------- Order Tracking ---------------------------
elif selected_page == "Order Tracking":
    page_header("Order Tracking", "Track supplier shipments and customer dispatches.")
    tab1, tab2 = st.tabs(["Orders", "Create order"])
    with tab1:
        orders = get_orders()
        if orders.empty:
            st.info("No orders have been recorded.")
        else:
            st.dataframe(orders, use_container_width=True, hide_index=True)
            order_options = {f"{r['order_code']} — {r['order_type']} — {r['product_name']}": int(r["id"]) for _, r in orders.iterrows()}
            selected_order = st.selectbox("Select order to update", list(order_options.keys()))
            status = st.selectbox("New status", ["Pending", "In Transit", "Completed", "Cancelled"])
            if st.button("Update order status"):
                try:
                    update_order_status(order_options[selected_order], status)
                    st.success("Order status updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not update order: {e}")
    with tab2:
        products = get_products()
        if products.empty:
            st.info("Add a product before creating an order.")
        else:
            product_map = {f"{r['product_name']} ({r['sku']})": int(r["id"]) for _, r in products.iterrows()}
            with st.form("create_order_form", clear_on_submit=True):
                order_type = st.selectbox("Order type", ["Supplier Shipment", "Customer Dispatch"])
                order_code = st.text_input("Order / reference number *")
                counterparty = st.text_input("Supplier or customer name")
                order_product = st.selectbox("Product", list(product_map.keys()))
                order_qty = st.number_input("Quantity", min_value=1, value=1, step=1)
                expected_date = st.date_input("Expected / order date", value=date.today())
                order_notes = st.text_input("Notes")
                order_submit = st.form_submit_button("Create order", type="primary")
            if order_submit:
                if not order_code.strip():
                    st.error("Order / reference number is required.")
                else:
                    try:
                        add_order(order_code.strip(), order_type, counterparty.strip(), product_map[order_product],
                                  int(order_qty), expected_date.isoformat(), order_notes.strip(), user["id"])
                        st.success("Order created.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not create order: {e}")

# --------------------------- Reports ---------------------------
elif selected_page == "Reports":
    page_header("Reports & Export", "Download inventory and transaction data for auditing.")
    products = get_products()
    tx = get_transactions()
    orders = get_orders()
    a, b, c = st.columns(3)
    a.metric("Product records", len(products))
    b.metric("Transactions", len(tx))
    c.metric("Orders", len(orders))
    if not products.empty:
        st.subheader("Inventory report")
        st.dataframe(products, use_container_width=True, hide_index=True)
        st.download_button("Download inventory report (CSV)", products.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"inventory_report_{date.today().isoformat()}.csv", mime="text/csv")
    if not tx.empty:
        st.subheader("Transaction report")
        st.download_button("Download transaction report (CSV)", tx.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"transaction_report_{date.today().isoformat()}.csv", mime="text/csv")
    if not orders.empty:
        st.subheader("Order report")
        st.download_button("Download order report (CSV)", orders.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"order_report_{date.today().isoformat()}.csv", mime="text/csv")

# --------------------------- User Management ---------------------------
elif selected_page == "User Management" and is_admin:
    page_header("User Management", "Create storekeeper accounts and manage user roles.")
    tab1, tab2 = st.tabs(["Users", "Add user"])
    with tab1:
        users = get_users()
        if not users.empty:
            st.dataframe(users[["id", "full_name", "username", "role", "created_at"]], use_container_width=True, hide_index=True)
            choices = {f"{r['full_name']} ({r['username']}) — {r['role']}": int(r["id"]) for _, r in users.iterrows() if int(r["id"]) != int(user["id"])}
            if choices:
                chosen_user = st.selectbox("Choose account to update", list(choices.keys()))
                new_role = st.selectbox("Role", ["Storekeeper", "Admin"])
                if st.button("Update role"):
                    try:
                        update_user_role(choices[chosen_user], new_role)
                        st.success("User role updated.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not update role: {e}")
    with tab2:
        with st.form("add_user_form", clear_on_submit=True):
            full_name = st.text_input("Full name")
            new_username = st.text_input("Username")
            new_password = st.text_input("Temporary password (minimum 8 characters)", type="password")
            new_role = st.selectbox("Role", ["Storekeeper", "Admin"])
            user_submit = st.form_submit_button("Create user", type="primary")
        if user_submit:
            if not full_name.strip() or not new_username.strip() or not new_password:
                st.error("Fill in all fields.")
            elif len(new_password) < 8:
                st.error("Password must contain at least 8 characters.")
            else:
                try:
                    add_user(full_name.strip(), new_username.strip(), new_password, new_role)
                    st.success("User account created.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not create user: {e}")


