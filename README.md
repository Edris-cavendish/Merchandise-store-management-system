# Supermarket Attendance & Management System

This is a desktop application for running a supermarket from one place.
It helps with staff records, attendance, payroll, stock, suppliers, credit purchases, sales, receipts, expenses, analytics, profits, user accounts, permissions, themes, store branding, and currency settings.

The system uses:
- Python
- Tkinter for the desktop interface
- SQLite for local data storage

The footer and receipts include:
`Developed by Ssemujju Edris | Copyright 2026`

## How to start the app

Open the project folder and run:

```bash
python scripts/init_db.py
python main.py
```

## Default administrator login

When the database is new, the first administrator account is:

- Username: `admin`
- Password: `admin123`

After login, you can change the username and password in `Settings & Security`.

## What happens when the app opens

1. The login window opens first.
2. You sign in with an active account.
3. The system opens the correct dashboard for that user.
4. If you click `Log Out`, the app returns to the login screen without needing to run `python main.py` again.

## Main sections of the app

The application is divided into these parts:

1. Login
2. Dashboard
3. Inventory
4. Staff & Attendance
5. Sales & Billing
6. My Receipts
7. Receipt Archive
8. Analytics & Reports
9. Expenses & Suppliers
10. My Pay
11. Settings & Security

Each section is explained below in simple English.

## 1. Login

When the app starts, the login window appears first.

What happens here:
- Only active accounts can sign in.
- Wrong usernames or passwords are rejected.
- Disabled accounts are blocked automatically.
- The current supermarket name is shown on the login screen.

Why it matters:
- It protects the system from unauthorized access.
- It makes testing easier because you can log out and log in as another user without reopening the terminal.

## 2. Dashboard

The dashboard changes depending on who is signed in.

### Administrator dashboard

What the administrator sees:
- Active staff
- Sales for today
- Expenses for today
- Estimated profit for today
- Inventory value
- Low-stock count
- Low-stock products table
- Recent sales
- Recent attendance

Why it matters:
- The admin sees the overall business picture.
- The admin can monitor operations quickly.

### Employee or cashier dashboard

What non-admin users see:
- Their own receipts for today
- Their own sales total for today
- Count of newly added products
- Their recent sales activity
- Product updates

Important rule:
- Non-admin users do not see full business totals for everybody.
- The dashboard is scoped to their own work, plus product updates they need to know.

## 3. Inventory

This section is for product and stock management.

What you can do:
- Add a product
- Edit a product
- Delete a product
- Create categories
- Record supplier name
- Record cost price
- Record selling price
- Set stock quantity
- Set low-stock level
- Add a description

What the grid shows:
- SKU
- Product name
- Supplier
- Category
- Cost price
- Selling price
- Stock quantity
- Last purchase mode (`Cash` or `Credit`)
- Pending supplier amount from the latest purchase

Why it matters:
- It keeps product records clean.
- It helps the owner understand both selling and purchase side information.

## 4. Staff & Attendance

This section is for worker records, attendance, and payroll setup.

What you can do:
- Add an employee
- Edit employee information
- Delete an employee
- Clock an employee in
- Clock an employee out
- View recent attendance logs
- Calculate salary when calculation is needed

Pay type behavior:
- `hourly` staff can use the `Calculate Salary` button.
- `fixed` salary staff have the hourly rate field disabled.
- For fixed salary staff, `Calculate Salary` stays disabled unless an overtime rate is added.
- If fixed salary has overtime pay, the calculation includes overtime.

## 5. Sales & Billing

This is the POS area.

What you can do:
- Choose products from available stock
- Add products to the cart
- Set quantities
- Apply discount
- Apply tax rate
- Choose payment method
- Complete the sale
- Preview the receipt
- Save the current receipt as PDF or TXT

Important details:
- Stock reduces automatically after a sale is completed.
- Sale records now also keep cost information for profit reporting.
- Receipts are stored in the database for later viewing.

## 6. My Receipts

This section is for non-admin users.

What it does:
- Shows only the receipts created by the signed-in user
- Allows the user to preview their own saved receipts
- Does not allow editing or deleting receipts

Why it matters:
- It protects receipt integrity.
- It lets staff review only their own history without seeing everybody else's records.

## 7. Receipt Archive

This section is for administrators.

What the admin can do:
- View all receipts stored in the database
- Open an old receipt and preview it again
- Export any stored receipt as PDF or TXT

Important rule:
- This is the overall receipt history.
- It is not shown to normal employee accounts.

## 8. Analytics & Reports

This section is for administrators.

What it shows:
- Employee performance chart
- Product performance chart
- Daily net profit chart
- Revenue for today
- Expenses for today
- Net profit for today
- Outstanding supplier balance
- Profit report preview for the selected period

What you can do:
- Change start date and end date
- Refresh analytics
- Export the report as a text file

How profit is assessed:
- Revenue comes from saved sales
- Cost of goods sold comes from saved stock cost on sold items
- Expenses come from the expense manager
- Net profit = revenue - stock cost - expenses

Important note:
- Profit reports are more accurate when products have cost prices and stock purchases are recorded properly.

## 9. Expenses & Suppliers

This section is for administrators.

It has two main parts.

### Expenses

What you can do:
- Record business expenses such as rent, utilities, transport, and other costs
- View expense history
- Delete an expense record if needed

Why it matters:
- These expenses are used in profit reporting.

### Supplier Credit

What you can do:
- Record a stock purchase for an existing product
- Choose whether it was bought by `Cash` or `Credit`
- Record the amount paid immediately
- Track the remaining unpaid balance
- Select a supplier purchase and record more payments later
- View payment history for the selected supplier purchase

What the table shows:
- Supplier name
- Product
- Purchase date
- Payment mode
- Total stock cost
- Amount already paid
- Amount still pending

Important details:
- Cash purchases are treated as fully paid.
- Credit purchases can be partial.
- The system highlights which purchases are still pending.
- Recording a stock purchase also increases product stock automatically.

## 10. My Pay

This section is only for employee accounts.

What it shows:
- Employee name
- Pay type
- Selected payroll period
- Base pay
- Overtime pay
- Estimated gross pay
- Hours worked
- Recent attendance used for payroll

Important details:
- `My Pay` is not shown to administrators.
- Employee accounts open with `My Pay` as the default tab.
- Employees also see a payment snapshot on their dashboard.

## 11. Settings & Security

This section controls profile changes, theme changes, store branding, currency format, and user privileges.

It has three main parts.

### My Profile

This part is for the currently signed-in user.

What you can change:
- Full name
- Username
- Password

Security rules:
- Current password is required before profile changes are saved.
- New passwords must be strong.
- Weak passwords are rejected.

### Theme, Store Name & Currency

This part controls appearance and global business identity.

Theme options:
- Green & White
- Dark Blue & White
- Yellow & White
- Brown & White

Theme behavior:
- When a theme is selected, the whole app changes immediately.
- You do not need to click another button to apply the theme.
- The selected theme is saved to the current user account.

Store branding:
- An administrator can change the supermarket name.
- The new name appears in the app header.
- The new name appears in the login screen.
- The new name appears in new receipts.

Currency settings:
- An administrator can set the currency symbol or code.
- The administrator can choose whether decimal points are used.
- This format is used across the whole app.

### User Accounts & Privileges

This part is for administrators.

What you can do:
- Create login accounts for employees
- Link a login to an existing employee record
- Change usernames
- Reset passwords
- Activate or disable accounts
- Choose a theme for a user
- Choose a role
- Choose which core areas of the system a user can open

Important rules:
- Employee names are selected from existing staff records.
- You do not type employee names manually.
- One employee cannot be linked to multiple login accounts.
- Inactive users cannot log in.
- Access is enforced by the system.
- `My Pay` is enforced for employee accounts and removed from non-employee accounts.

## Roles and access behavior

The app supports roles, but access can also be adjusted per user.

Default roles are:
- `Administrator`
- `Manager`
- `Cashier`
- `Employee`

Important behavior:
- `Administrator` sees the overall system.
- `Administrator` gets `Receipt Archive`, `Analytics & Reports`, and `Expenses & Suppliers`.
- Non-admin users get `My Receipts` instead of the full receipt archive.
- Employee accounts get `My Pay`.
- Non-employee roles do not get the `My Pay` tab.

## Global currency formatting

The app supports global currency formatting.

What this means:
- Money values across the system use the same symbol or currency code.
- The owner can turn decimals on or off.
- This affects inventory prices, payroll values, sales totals, expense values, supplier balances, analytics, and receipts.

## Database information

The database file is created here:

`data/supermarket.db`

Main tables used:
- `employees`
- `users`
- `user_permissions`
- `attendance`
- `categories`
- `products`
- `sales`
- `sale_items`
- `stock_purchases`
- `supplier_payments`
- `expenses`
- `app_settings`

## Notes

- The system is for local desktop use.
- SQLite is used, so no server setup is required.
- Run `python scripts/init_db.py` after database changes.
- Use the `Expenses & Suppliers` tab to manage credit stock purchases and supplier balances.
- Use the `Analytics & Reports` tab to review charts and export profit reports.
- Use the `Log Out` button to switch between admin and employee views during testing.
