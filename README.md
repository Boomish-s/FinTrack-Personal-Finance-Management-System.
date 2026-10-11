# Fintrack — Personal Finance Management System

Fintrack is a personal finance management web application developed as part of the Database Management Systems (DBMS) project. It helps users organize their finances, track income and expenses, manage budgets, and monitor savings goals through a centralized dashboard.

## Features

- **User Authentication:** Register and log in to a personal account.
- **Dashboard:** View total account balance, income, and expenses.
- **Account Management:** Create and manage financial accounts.
- **Transaction Management:** Record, edit, and delete income and expense transactions.
- **Category Management:** Organize transactions using income and expense categories.
- **Budget Management:** Set budgets and allocate amounts across categories.
- **Savings Goals:** Create financial goals and track savings progress.

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, Flask |
| Database | PostgreSQL |
| Database Tool | pgAdmin |
| Version Control | Git and GitHub |

## Database Design

Fintrack uses a relational database designed to organize financial data and maintain relationships between users and their financial records.

The database consists of the following seven tables:

1. **users** — Stores user details and authentication information.
2. **accounts** — Stores financial accounts belonging to users.
3. **categories** — Stores income and expense categories.
4. **transactions** — Stores income and expense records.
5. **budgets** — Stores budget names and budgeting periods.
6. **budget_category** — A junction table connecting budgets and categories, including allocated amounts.
7. **savings_goals** — Stores savings targets, progress, and goal status.

The design uses primary keys, foreign keys, constraints, and a junction table to represent relationships and maintain data integrity.

The `schema.sql` file contains the PostgreSQL table definitions.

## Project Structure

```text
Fintrack/
├── backend/
│   ├── app.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── style.css
│   └── script.js
├── schema.sql
└── README.md
```

*The structure above represents the expected layout; update the filenames if your actual project differs.*

## Getting Started

### Prerequisites

- Python 3
- PostgreSQL
- pgAdmin (optional, for database management)
- Git

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Fintrack
```

Replace the placeholder with your actual GitHub repository URL.

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure PostgreSQL

Create a PostgreSQL database for Fintrack using pgAdmin or the PostgreSQL command line.

Execute `schema.sql` against the newly created database to create the tables.

Configure the database connection settings required by `backend/app.py`. Keep database passwords and secret keys in environment variables rather than committing them to GitHub.

**Note:** Run the schema against a fresh database. Do not run the table-creation script over an existing database containing project data.

### 5. Start the Application

From the project root, activate your virtual environment and run:

```bash
python backend/app.py
```

Open the local address displayed by Flask, usually:

```text
http://127.0.0.1:5000/
```

The application requires a working PostgreSQL connection to use its database-backed features.

## API Overview

The Flask backend provides REST-style endpoints for the application's functionality, including:

- Authentication: registration, login, and logout.
- Accounts: account management.
- Transactions: recording and managing financial transactions.
- Categories: retrieving and managing transaction categories.
- Budgets: managing budgets and category allocations.
- Savings Goals: creating, updating, deleting, and tracking goals.
- Dashboard: calculating account balances, income, and expenses.

Refer to `backend/app.py` for the exact endpoint paths and supported HTTP methods.

## Security Notes

- Passwords should be stored as hashes, not plain text.
- Keep secret keys and database credentials out of source control.
- Financial data should be filtered by the authenticated user's ID.
- Protect database-backed API endpoints against unauthenticated access.
- Use HTTPS and secure session configuration when deploying publicly.

## Future Improvements

- Deploy the application with a hosted PostgreSQL database.
- Add stronger authentication and session protections.
- Improve validation and error handling.
- Add charts and more detailed financial reports.
- Enhance responsive design and usability.

## Academic Context

**Course:** Database Management Systems (23CSE202)  
**Programme:** B.Tech Computer Science and Engineering  
**Institution:** Amrita School of Computing, Amritapuri Campus

## License

This project was developed for academic purposes. Add a license if you intend to distribute or reuse the project publicly.
