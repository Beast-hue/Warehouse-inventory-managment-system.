# Warehouse Inventory Management System

A beginner-friendly interactive warehouse inventory web app built with **Streamlit, Python, and MySQL**.

## Included features

- Admin and Storekeeper login roles
- Dashboard with stock metrics and category chart
- Product search, add/edit/delete and categories
- Stock IN / OUT transactions with protection against negative stock
- Low-stock alerts on the website
- Supplier shipment and customer dispatch order tracking
- CSV downloads for inventory, transactions and reports
- User management for administrators

## Run locally on Windows

### 1. Install prerequisites
Install Python 3.10+ and MySQL Server. Start the MySQL service.

### 2. Open the project folder
Extract the ZIP and open the extracted folder in VS Code.

### 3. Create and activate a virtual environment
In the VS Code terminal (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can skip activation and use `python -m pip` in your selected Python environment.

### 4. Install packages

```powershell
python -m pip install -r requirements.txt
```

### 5. Configure the database
Copy `.env.example` to a new file named `.env`. Update the database host, username, and password to match your MySQL setup.

The configured MySQL account must have permission to create the database and tables on first run. For a safer setup, create a dedicated database user instead of using the MySQL root account.

**Never upload `.env` or real database passwords to GitHub.** `.env` is ignored by Git.

### 6. Start the website

```powershell
python -m streamlit run app.py
```

Open the local URL printed in the terminal, usually `http://localhost:8501`.

### 7. Create your first account
On first run, create the initial administrator account in the app. There is no default login/password. After logging in, use **User Management** to create Storekeeper accounts.

## Publish online

You can deploy the app through [Streamlit Community Cloud](https://share.streamlit.io/) after pushing the project files to a GitHub repository.

Important: **a deployed website cannot connect to `localhost` on your own computer.** For public deployment, use a managed MySQL database with a network-accessible host and appropriate access controls. In Streamlit Cloud, set credentials in **App settings → Secrets**, using TOML syntax, for example:

```toml
MYSQL_HOST = "your-managed-database-host"
MYSQL_PORT = 3306
MYSQL_USER = "your_database_user"
MYSQL_PASSWORD = "Root"
MYSQL_DATABASE = "warehouse_inventory"
```

Do not commit real secrets to GitHub. Confirm that your database provider supports secure remote connections and restrict access where possible. Public deployment also requires HTTPS/session/security review, backups, and a least-privilege database user.

## Low-stock alert logic

A product is flagged when `quantity <= reorder_level`. Alerts appear in the website dashboard and sidebar when the app reruns. The project does not send email or SMS alerts.

## Troubleshooting

- **MySQL connection error:** confirm the MySQL service is running locally, or that your remote database host and firewall settings are correct. Check `.env` or Streamlit Secrets.
- **`ModuleNotFoundError`:** install dependencies using `python -m pip install -r requirements.txt` in the same Python environment used to run Streamlit.
- **Port 8501 is busy:** run `python -m streamlit run app.py --server.port 8502`.
- **Duplicate SKU or order code:** choose a unique value; both fields are constrained to be unique.
- **Password forgotten:** there is no default password or automatic password-reset flow in this starter; have the database administrator handle recovery securely.

## Database tables

- `users`
- `categories`
- `products`
- `stock_transactions`
- `orders`

## Project status and limitations

This is a student project starter, not a production-audited inventory platform. Before using it for real business data, review authorization on every operation, session expiration, password reset, audit logging, database permissions, backup/restore, input validation, and deployment security. Test with sample data before using live stock records.
