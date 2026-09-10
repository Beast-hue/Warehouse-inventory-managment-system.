import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Warehouse Management System",
    page_icon="📦",
    layout="wide"
)

# Create login status
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


#  LOGIN PAGE 
def login_page():

    st.title("🔐 Login Page")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if username == "Warehouse" and password == "Warehouse@123":

            st.session_state.logged_in = True

            # Refresh the page
            st.rerun()

        else:
            st.error("❌ Invalid username or password")


# DASHBOARD 
def dashboard():

    st.title("📊 Warehouse Dashboard")

    st.success("✅ Login Successful!")

    st.write("Welcome to the Warehouse Management System.")

    # Dashboard information
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Products", "250")

    with col2:
        st.metric("Products in Stock", "180")

    with col3:
        st.metric("Low Stock", "20")

    st.subheader("Warehouse Management")

    st.write("You can manage your products, inventory and orders here.")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()


# PAGE CONTROL

if st.session_state.logged_in:
    dashboard()
else:
    login_page()