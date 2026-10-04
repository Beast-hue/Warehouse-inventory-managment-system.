# Warehouse Inventory Management System
**Stack:** Streamlit + Python + MySQL  
**Features:** login, Admin/Storekeeper roles, product and category management, stock IN/OUT transactions, low-stock website alerts, order tracking, and CSV reports.

## 1. Requirements
- Windows 10/11
- Python 3.10 or newer
- MySQL Server running locally
- VS Code (recommended)

## 2. Install and configure
1. Extract this ZIP into a folder, for example `C:\WarehouseIMS`.
2. Open that folder in VS Code.
3. Open Terminal in VS Code.
4. Create a virtual environment (recommended):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

5. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

6. Copy `.env.example` to a new file named `.env`.
7. Open `.env` and set `MYSQL_PASSWORD` to your MySQL root password. If your MySQL username is not `root`, update `MYSQL_USER` too.
8. Make sure the MySQL Server service is running.

## 3. Start the website
In the project folder, run:

```powershell
python -m streamlit run app.py
```

Streamlit will print a local URL, usually `http://localhost:8501`. Open it in your browser.

## 4. First login
On the first run, the app creates the database and tables automatically (the configured MySQL account must have permission to create a database). The first page asks you to create the first Admin account. There is no hard-coded default password.

After creating the Admin, log in with the account you just created. Use **User Management** to create Storekeeper accounts.

## 5. Low-stock alerts
- Each product has a `reorder_level`.
- The dashboard shows an alert when `quantity <= reorder_level`.
- The sidebar shows the number of products currently under the threshold.
- Alerts are website-only; no email, SMS, or external service is used.
- Alerts are based on the current database values and update when the Streamlit app reruns.

## 6. Main modules
- **Dashboard:** stock summary, category chart, recent transactions, low-stock alerts.
- **Inventory:** search, add products, categories, edit product details, CSV export.
- **Stock Transactions:** stock IN/OUT, prevent dispatching more than available stock, transaction history.
- **Order Tracking:** supplier shipment/customer dispatch logs and order status.
- **Reports:** download inventory, transaction and order reports as CSV.
- **User Management (Admin only):** add accounts and change roles.

## 7. Database tables
- `users`
- `categories`
- `products`
- `stock_transactions`
- `orders`

## 8. Troubleshooting
**MySQL connection error**
- Confirm the MySQL Server service is running.
- Check `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE` in `.env`.
- Do not include quotes unless needed as part of the password.
- Test that the account can connect to MySQL and create a database.

**`ModuleNotFoundError`**
Run `python -m pip install -r requirements.txt` in the same terminal/environment used to launch Streamlit.

**Port 8501 is already in use**
Run `python -m streamlit run app.py --server.port 8502`.

**Product SKU already exists**
Each SKU must be unique. Choose a different SKU.

## Notes
This is a student project starter intended for local/demo use. Before public deployment, add production-grade session controls, CSRF/security review, database least-privilege credentials, backups, HTTPS, and more detailed audit controls.
