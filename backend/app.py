
import os
import math
import psycopg
from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory, request, session
from werkzeug.security import generate_password_hash, check_password_hash
load_dotenv()

app = Flask(__name__)
@app.route("/login")
def login_page():
    return send_from_directory("../frontend", "login.html")
import os

app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32)


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or len(password) < 6:
        return jsonify({
            "error": "Name, email, and a password of at least 6 characters are required."
        }), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (name, email, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING user_id
                    """,
                    (name, email, generate_password_hash(password))
                )
                user_id = cur.fetchone()[0]

            conn.commit()

        session["user_id"] = user_id
        return jsonify({"message": "Account created successfully."}), 201

    except Exception:
        return jsonify({
            "error": "Registration failed. This email may already be registered."
        }), 400


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, password_hash FROM users WHERE email = %s",
                (email,)
            )
            user = cur.fetchone()

    if not user or not check_password_hash(user[1], password):
        return jsonify({"error": "Invalid email or password."}), 401

    session.clear()
    session["user_id"] = user[0]
    return jsonify({"message": "Login successful."})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."})
from flask import redirect, url_for

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login_page"))

    return send_from_directory("../frontend", "index.html")


@app.route("/<path:filename>")
def frontend_files(filename):
    return send_from_directory("../frontend", filename)
def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "fintrack"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


@app.route("/api/health", methods=["GET"])
def health():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user")
                database, username = cur.fetchone()

        return jsonify({
            "status": "connected",
            "database": database,
            "user": username
        })

    except Exception:
        app.logger.exception("Database connection failed")
        return jsonify({
            "status": "error",
            "message": "Database connection failed. Check backend configuration."
        }), 500


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:

                # 1. Calculate total account balance
                cur.execute("""
                    SELECT COALESCE(SUM(balance), 0)
                    FROM accounts
                    WHERE user_id = %s
                """,(session["user_id"],))
                total_balance = cur.fetchone()[0]

                # 2. Calculate total income and expenses
                cur.execute("""
                    SELECT
                        COALESCE(SUM(amount) FILTER (
                            WHERE transaction_type = 'Income'
                        ), 0),
                        COALESCE(SUM(amount) FILTER (
                            WHERE transaction_type = 'Expense'
                        ), 0)
                    FROM transactions
                    WHERE user_id = %s
                """,(session["user_id"],))
                total_income, total_expenses = cur.fetchone()

                # 3. Fetch the five most recent transactions
                cur.execute("""
                    SELECT
                        t.transaction_id,
                        t.transaction_type,
                        t.amount,
                        t.transaction_date,
                        t.description,
                        c.category_name,
                        a.account_name
                    FROM transactions t
                    JOIN categories c
                        ON t.category_id = c.category_id
                    JOIN accounts a
                        ON t.account_id = a.account_id
                    ORDER BY t.transaction_date DESC,
                             t.transaction_id DESC
                    LIMIT 5
                """)

                rows = cur.fetchall()

                recent_transactions = [
                    {
                        "transaction_id": row[0],
                        "type": row[1],
                        "amount": float(row[2]),
                        "date": row[3].isoformat(),
                        "description": row[4],
                        "category": row[5],
                        "account": row[6]
                    }
                    for row in rows
                ]

        return jsonify({
            "total_balance": float(total_balance),
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "recent_transactions": recent_transactions
        })

    except Exception:
        app.logger.exception("Dashboard query failed")
        return jsonify({
            "error": "Could not load dashboard data."
        }), 500


DEMO_EMAIL = "demo@fintrack.test"



def get_demo_user_id(cur):
    user_id = session.get("user_id")

    if user_id is None:
        return None

    cur.execute(
        "SELECT user_id FROM users WHERE user_id = %s",
        (user_id,)
    )

    row = cur.fetchone()
    return row[0] if row else None




@app.route("/api/accounts", methods=["GET"])
def get_accounts():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                cur.execute("""
                    SELECT
                        a.account_id,
                        a.account_name,
                        a.account_type,
                        a.balance,
                        (u.default_account_id = a.account_id) AS is_default
                    FROM accounts a
                    JOIN users u ON u.user_id = a.user_id
                    WHERE a.user_id = %s
                    ORDER BY a.account_name
                """, (user_id,))

                accounts = [
                    {
                        "account_id": row[0],
                        "account_name": row[1],
                        "account_type": row[2],
                        "balance": float(row[3]),
                        "is_default": row[4] or False
                    }
                    for row in cur.fetchall()
                ]

        return jsonify(accounts)

    except Exception:
        app.logger.exception("Could not load accounts")
        return jsonify({"error": "Could not load accounts."}), 500


@app.route("/api/accounts", methods=["POST"])
def add_account():
    data = request.get_json(silent=True) or {}

    account_name = (data.get("account_name") or "").strip()
    account_type = (data.get("account_type") or "").strip()
    allowed_types = {"Cash", "Bank", "Savings", "Credit"}

    if not account_name:
        return jsonify({"error": "Account name is required."}), 400

    if len(account_name) > 100:
        return jsonify({"error": "Account name must be 100 characters or fewer."}), 400

    if account_type not in allowed_types:
        return jsonify({
            "error": "Account type must be Cash, Bank, Savings, or Credit."
        }), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                cur.execute("""
                    INSERT INTO accounts
                        (user_id, account_name, account_type, balance)
                    VALUES (%s, %s, %s, 0)
                    RETURNING account_id, account_name, account_type, balance
                """, (user_id, account_name, account_type))

                row = cur.fetchone()

        return jsonify({
            "account_id": row[0],
            "account_name": row[1],
            "account_type": row[2],
            "balance": float(row[3]),
            "message": "Account created successfully."
        }), 201

    except Exception:
        app.logger.exception("Could not create account")
        return jsonify({"error": "Could not create account."}), 500


@app.route("/api/accounts/<int:account_id>", methods=["PUT"])
def update_account(account_id):
    data = request.get_json(silent=True) or {}

    account_name = (data.get("account_name") or "").strip()
    account_type = (data.get("account_type") or "").strip()
    allowed_types = {"Cash", "Bank", "Savings", "Credit"}

    if not account_name:
        return jsonify({"error": "Account name is required."}), 400

    if len(account_name) > 100:
        return jsonify({
            "error": "Account name must be 100 characters or fewer."
        }), 400

    if account_type not in allowed_types:
        return jsonify({
            "error": "Account type must be Cash, Bank, Savings, or Credit."
        }), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                cur.execute("""
                    UPDATE accounts
                    SET account_name = %s,
                        account_type = %s
                    WHERE account_id = %s
                      AND user_id = %s
                    RETURNING account_id, account_name, account_type, balance
                """, (account_name, account_type, account_id, user_id))

                row = cur.fetchone()

                if row is None:
                    return jsonify({"error": "Account not found."}), 404

        return jsonify({
            "account_id": row[0],
            "account_name": row[1],
            "account_type": row[2],
            "balance": float(row[3]),
            "message": "Account updated successfully."
        })

    except Exception:
        app.logger.exception("Could not update account")
        return jsonify({"error": "Could not update account."}), 500

@app.route("/api/accounts/<int:account_id>", methods=["DELETE"])
def delete_account(account_id):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                cur.execute("""
                    SELECT account_id
                    FROM accounts
                    WHERE account_id = %s AND user_id = %s
                    FOR UPDATE
                """, (account_id, user_id))

                account = cur.fetchone()

                if account is None:
                    return jsonify({"error": "Account not found."}), 404

                cur.execute("""
                    SELECT 1
                    FROM transactions
                    WHERE account_id = %s AND user_id = %s
                    LIMIT 1
                """, (account_id, user_id))

                if cur.fetchone():
                    return jsonify({
                        "error": "This account has transactions and cannot be deleted."
                    }), 409

                cur.execute("""
                    SELECT 1
                    FROM savings_goals
                    WHERE account_id = %s AND user_id = %s
                    LIMIT 1
                """, (account_id, user_id))

                if cur.fetchone():
                    return jsonify({
                        "error": "This account is linked to a savings goal. Unlink it first."
                    }), 409

                cur.execute("""
                    SELECT 1
                    FROM users
                    WHERE user_id = %s AND default_account_id = %s
                """, (user_id, account_id))

                if cur.fetchone():
                    return jsonify({
                        "error": "This is your default account. Change the default account first."
                    }), 409

                cur.execute("""
                    DELETE FROM accounts
                    WHERE account_id = %s AND user_id = %s
                """, (account_id, user_id))

        return jsonify({
            "message": "Account deleted successfully."
        })

    except Exception:
        app.logger.exception("Could not delete account")
        return jsonify({"error": "Could not delete account."}), 500

@app.route("/api/accounts/<int:account_id>/default", methods=["PUT"])
def set_default_account(account_id):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                cur.execute("""
                    SELECT account_id
                    FROM accounts
                    WHERE account_id = %s AND user_id = %s
                """, (account_id, user_id))

                if cur.fetchone() is None:
                    return jsonify({"error": "Account not found."}), 404

                cur.execute("""
                    UPDATE users
                    SET default_account_id = %s
                    WHERE user_id = %s
                """, (account_id, user_id))

        return jsonify({
            "message": "Default account updated successfully.",
            "default_account_id": account_id
        })

    except Exception:
        app.logger.exception("Could not set default account")
        return jsonify({"error": "Could not set default account."}), 500

@app.route("/api/categories", methods=["GET"])
def get_categories():
    try:
        transaction_type = request.args.get("type", "").strip()

        if transaction_type not in ("Income", "Expense"):
            return jsonify({
                "error": "Type must be Income or Expense."
            }), 400

        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({
                        "error": "Demo user not found."
                    }), 404

                cur.execute("""
                    SELECT
                        c.category_id,
                        c.category_name,
                        c.category_type,
                        c.description,
                        COALESCE(
                            bc.allocated_amount, 0
                        ) AS monthly_limit
                    FROM categories c
                    LEFT JOIN budget_category bc
                        ON bc.category_id = c.category_id
                    LEFT JOIN budgets b
                        ON b.budget_id = bc.budget_id
                       AND b.user_id = %s
                       AND b.start_date <= CURRENT_DATE
                       AND b.end_date >= CURRENT_DATE
                    WHERE c.category_type = %s
                      AND (c.user_id = %s OR c.user_id IS NULL)
                      AND (
                          bc.budget_id IS NULL
                          OR b.budget_id IS NOT NULL
                      )
                    ORDER BY c.category_name
                """, (user_id, transaction_type, user_id))

                categories = [
                    {
                        "category_id": row[0],
                        "category_name": row[1],
                        "category_type": row[2],
                        "description": row[3],
                        "monthly_limit": float(row[4])
                    }
                    for row in cur.fetchall()
                ]

        return jsonify(categories)

    except Exception:
        app.logger.exception("Could not load categories")
        return jsonify({
            "error": "Could not load categories."
        }), 500



@app.route("/api/categories", methods=["POST"])
def create_category():
    data = request.get_json(silent=True) or {}

    category_name = (data.get("category_name") or "").strip()
    category_type = (data.get("category_type") or "").strip()
    description = (data.get("description") or "").strip() or None
    raw_limit = data.get("monthly_limit")

    if not category_name:
        return jsonify({"error": "Category name is required."}), 400

    if len(category_name) > 100:
        return jsonify({
            "error": "Category name must be 100 characters or fewer."
        }), 400

    if category_type not in ("Income", "Expense"):
        return jsonify({
            "error": "Type must be Income or Expense."
        }), 400

    monthly_limit = None

    if category_type == "Expense":
        if raw_limit is None or str(raw_limit).strip() == "":
            return jsonify({
                "error": "Monthly spending limit is required."
            }), 400

        try:
            monthly_limit = float(raw_limit)
        except (ValueError, TypeError):
            return jsonify({
                "error": "Monthly limit must be a valid number."
            }), 400

        if not math.isfinite(monthly_limit) or monthly_limit < 0:
            return jsonify({
                "error": "Monthly limit must be a non-negative number."
            }), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({
                        "error": "Demo user not found."
                    }), 404

                # Prevent duplicate categories.
                cur.execute("""
                    SELECT 1
                    FROM categories
                    WHERE user_id = %s
                      AND LOWER(category_name) = LOWER(%s)
                      AND category_type = %s
                """, (user_id, category_name, category_type))

                if cur.fetchone():
                    return jsonify({
                        "error": "You already have a category with this name and type."
                    }), 409

                # Create the category.
                cur.execute("""
                    INSERT INTO categories
                        (user_id, category_name, category_type, description)
                    VALUES (%s, %s, %s, %s)
                    RETURNING category_id, category_name,
                              category_type, description
                """, (user_id, category_name, category_type, description))

                row = cur.fetchone()
                category_id = row[0]
                budget_id = None

                if category_type == "Expense":
                    # Find the budget covering today's date.
                    cur.execute("""
                        SELECT budget_id
                        FROM budgets
                        WHERE user_id = %s
                          AND start_date <= CURRENT_DATE
                          AND end_date >= CURRENT_DATE
                        ORDER BY start_date DESC
                        LIMIT 1
                    """, (user_id,))

                    budget_row = cur.fetchone()

                    # Create this month's budget if none exists.
                    if budget_row is None:
                        cur.execute("""
                            INSERT INTO budgets
                                (user_id, budget_name, start_date, end_date)
                            VALUES (
                                %s,
                                TO_CHAR(CURRENT_DATE, 'FMMonth')
                                    || ' Monthly Budget',
                                DATE_TRUNC('month', CURRENT_DATE)::date,
                                (
                                    DATE_TRUNC('month', CURRENT_DATE)
                                    + INTERVAL '1 month - 1 day'
                                )::date
                            )
                            RETURNING budget_id
                        """, (user_id,))

                        budget_id = cur.fetchone()[0]
                    else:
                        budget_id = budget_row[0]

                    # Connect the category to the budget with its limit.
                    cur.execute("""
                        INSERT INTO budget_category
                            (budget_id, category_id, allocated_amount)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (budget_id, category_id)
                        DO UPDATE SET
                            allocated_amount = EXCLUDED.allocated_amount
                    """, (budget_id, category_id, monthly_limit))

        return jsonify({
            "category_id": row[0],
            "category_name": row[1],
            "category_type": row[2],
            "description": row[3],
            "monthly_limit": monthly_limit,
            "budget_id": budget_id
        }), 201

    except Exception:
        app.logger.exception("Could not create category")
        return jsonify({
            "error": "Could not create category."
        }), 500



@app.route("/api/categories/<int:category_id>", methods=["PUT"])
def update_category(category_id):
    data = request.get_json(silent=True) or {}

    category_name = (data.get("category_name") or "").strip()
    description = (data.get("description") or "").strip() or None
    raw_limit = data.get("monthly_limit")

    if not category_name:
        return jsonify({"error": "Category name is required."}), 400

    if len(category_name) > 100:
        return jsonify({
            "error": "Category name must be 100 characters or fewer."
        }), 400

    try:
        monthly_limit = None

        if raw_limit is not None and str(raw_limit).strip() != "":
            monthly_limit = float(raw_limit)

            if not 0 <= monthly_limit < float("inf"):
                return jsonify({
                    "error": "Monthly limit must be a valid non-negative amount."
                }), 400

        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                # Update the category itself.
                cur.execute("""
                    UPDATE categories
                    SET category_name = %s,
                        description = %s
                    WHERE category_id = %s
                      AND user_id = %s
                    RETURNING category_id, category_name,
                              category_type, description
                """, (category_name, description, category_id, user_id))

                row = cur.fetchone()

                if row is None:
                    return jsonify({
                        "error": "Category not found or cannot be edited."
                    }), 404

                # Update the allocation for the current month's budget.
                if monthly_limit is not None and row[2] == "Expense":
                    cur.execute("""
                        SELECT budget_id
                        FROM budgets
                        WHERE user_id = %s
                          AND start_date <= CURRENT_DATE
                          AND end_date >= CURRENT_DATE
                        ORDER BY start_date DESC
                        LIMIT 1
                    """, (user_id,))

                    budget_row = cur.fetchone()

                    if budget_row is not None:
                        cur.execute("""
                            INSERT INTO budget_category
                                (budget_id, category_id, allocated_amount)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (budget_id, category_id)
                            DO UPDATE SET
                                allocated_amount = EXCLUDED.allocated_amount
                        """, (budget_row[0], category_id, monthly_limit))

        return jsonify({
            "category_id": row[0],
            "category_name": row[1],
            "category_type": row[2],
            "description": row[3],
            "monthly_limit": monthly_limit
        })

    except (ValueError, TypeError):
        return jsonify({
            "error": "Monthly limit must be a valid number."
        }), 400

    except Exception:
        app.logger.exception("Could not update category")
        return jsonify({
            "error": "Could not update category."
        }), 500

@app.route("/api/transactions", methods=["POST"])
def add_transaction():
    data = request.get_json(silent=True) or {}

    transaction_type = data.get("transaction_type")
    description = (data.get("description") or "").strip() or None
    transaction_date = data.get("transaction_date")

    try:
        amount = float(data.get("amount", 0))
        account_id = int(data.get("account_id", 0))
        category_id = int(data.get("category_id", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Enter a valid amount, account, and category."}), 400

    if transaction_type not in ("Income", "Expense"):
        return jsonify({"error": "Invalid transaction type."}), 400

    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero."}), 400

    if len(description or "") > 500:
        return jsonify({"error": "Description is too long."}), 400

    if not transaction_date:
        return jsonify({"error": "Transaction date is required."}), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                cur.execute("""
                    SELECT balance
                    FROM accounts
                    WHERE account_id = %s AND user_id = %s
                    FOR UPDATE
                """, (account_id, user_id))

                account = cur.fetchone()

                if account is None:
                    return jsonify({"error": "Invalid account."}), 400

                cur.execute("""
                    SELECT category_id
                    FROM categories
                    WHERE category_id = %s
                      AND category_type = %s
                      AND (user_id = %s OR user_id IS NULL)
                """, (category_id, transaction_type, user_id))

                if cur.fetchone() is None:
                    return jsonify({
                        "error": "Choose a category matching the transaction type."
                    }), 400

                current_balance = account[0]

                if transaction_type == "Expense" and amount > current_balance:
                    return jsonify({
                        "error": "Insufficient account balance."
                    }), 400

                balance_change = amount if transaction_type == "Income" else -amount

                cur.execute("""
                    UPDATE accounts
                    SET balance = balance + %s
                    WHERE account_id = %s AND user_id = %s
                """, (balance_change, account_id, user_id))

                cur.execute("""
                    INSERT INTO transactions
                        (user_id, account_id, category_id, amount,
                         transaction_type, transaction_date, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING transaction_id
                """, (
                    user_id, account_id, category_id, amount,
                    transaction_type, transaction_date, description
                ))

                transaction_id = cur.fetchone()[0]

        return jsonify({
            "message": "Transaction added successfully.",
            "transaction_id": transaction_id
        }), 201

    except Exception:
        app.logger.exception("Could not add transaction")
        return jsonify({
            "error": "Could not save transaction. Check the input and database."
        }), 500

@app.route("/api/transactions/<int:transaction_id>", methods=["PUT"])
def edit_transaction(transaction_id):
    data = request.get_json(silent=True) or {}

    transaction_type = data.get("transaction_type")
    description = (data.get("description") or "").strip() or None
    transaction_date = data.get("transaction_date")

    try:
        amount = float(data.get("amount", 0))
        account_id = int(data.get("account_id", 0))
        category_id = int(data.get("category_id", 0))
    except (TypeError, ValueError):
        return jsonify({
            "error": "Enter a valid amount, account, and category."
        }), 400

    if transaction_type not in ("Income", "Expense"):
        return jsonify({"error": "Invalid transaction type."}), 400

    if amount <= 0:
        return jsonify({
            "error": "Amount must be greater than zero."
        }), 400

    if len(description or "") > 500:
        return jsonify({"error": "Description is too long."}), 400

    if not transaction_date:
        return jsonify({
            "error": "Transaction date is required."
        }), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                # Lock and retrieve the original transaction.
                cur.execute("""
                    SELECT account_id, category_id, amount,
                           transaction_type
                    FROM transactions
                    WHERE transaction_id = %s AND user_id = %s
                    FOR UPDATE
                """, (transaction_id, user_id))

                old = cur.fetchone()

                if old is None:
                    return jsonify({
                        "error": "Transaction not found."
                    }), 404

                old_account_id, old_category_id, old_amount, old_type = old

                # Lock both accounts in a consistent order.
                account_ids = sorted(set([old_account_id, account_id]))

                cur.execute("""
                    SELECT account_id, balance
                    FROM accounts
                    WHERE account_id = ANY(%s) AND user_id = %s
                    ORDER BY account_id
                    FOR UPDATE
                """, (account_ids, user_id))

                balances = {
                    row[0]: float(row[1])
                    for row in cur.fetchall()
                }

                if account_id not in balances:
                    return jsonify({"error": "Invalid account."}), 400

                # Validate that the category matches the transaction type.
                cur.execute("""
                    SELECT category_id
                    FROM categories
                    WHERE category_id = %s
                      AND category_type = %s
                      AND (user_id = %s OR user_id IS NULL)
                """, (category_id, transaction_type, user_id))

                if cur.fetchone() is None:
                    return jsonify({
                        "error": "Choose a category matching the transaction type."
                    }), 400

                # Reverse the original transaction's balance effect.
                if old_type == "Income":
                    balances[old_account_id] -= float(old_amount)
                else:
                    balances[old_account_id] += float(old_amount)

                # Apply the edited transaction's balance effect.
                if transaction_type == "Income":
                    balances[account_id] += amount
                else:
                    if balances[account_id] < amount:
                        return jsonify({
                            "error": "Insufficient account balance."
                        }), 400
                    balances[account_id] -= amount

                if any(balance < 0 for balance in balances.values()):
                    return jsonify({
                        "error": "This edit would make an account balance negative."
                    }), 400

                # Save the corrected account balances.
                for acc_id, balance in balances.items():
                    cur.execute("""
                        UPDATE accounts
                        SET balance = %s
                        WHERE account_id = %s AND user_id = %s
                    """, (balance, acc_id, user_id))

                # Update the transaction record itself.
                cur.execute("""
                    UPDATE transactions
                    SET account_id = %s,
                        category_id = %s,
                        amount = %s,
                        transaction_type = %s,
                        transaction_date = %s,
                        description = %s
                    WHERE transaction_id = %s AND user_id = %s
                """, (
                    account_id, category_id, amount,
                    transaction_type, transaction_date, description,
                    transaction_id, user_id
                ))

        return jsonify({
            "message": "Transaction updated successfully.",
            "transaction_id": transaction_id
        })

    except Exception:
        app.logger.exception("Could not update transaction")
        return jsonify({
            "error": "Could not update transaction."
        }), 500

@app.route("/api/transactions/<int:transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                cur.execute("""
                    SELECT account_id, amount, transaction_type
                    FROM transactions
                    WHERE transaction_id = %s AND user_id = %s
                    FOR UPDATE
                """, (transaction_id, user_id))

                transaction = cur.fetchone()

                if transaction is None:
                    return jsonify({"error": "Transaction not found."}), 404

                account_id, amount, transaction_type = transaction

                cur.execute("""
                    SELECT balance
                    FROM accounts
                    WHERE account_id = %s AND user_id = %s
                    FOR UPDATE
                """, (account_id, user_id))

                account = cur.fetchone()

                if account is None:
                    return jsonify({"error": "Account not found."}), 404

                # Reverse the original transaction's balance effect.
                if transaction_type == "Income":
                    new_balance = account[0] - amount
                else:
                    new_balance = account[0] + amount

                if new_balance < 0:
                    return jsonify({
                        "error": "Cannot delete this income because it would make the account balance negative."
                    }), 400

                cur.execute("""
                    UPDATE accounts
                    SET balance = %s
                    WHERE account_id = %s AND user_id = %s
                """, (new_balance, account_id, user_id))

                cur.execute("""
                    DELETE FROM transactions
                    WHERE transaction_id = %s AND user_id = %s
                """, (transaction_id, user_id))

        return jsonify({
            "message": "Transaction deleted successfully.",
            "transaction_id": transaction_id
        })

    except Exception:
        app.logger.exception("Could not delete transaction")
        return jsonify({"error": "Could not delete transaction."}), 500


@app.route("/api/budgets", methods=["GET"])
def get_budgets():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                cur.execute("""
                    SELECT
                        b.budget_id,
                        b.budget_name,
                        b.start_date,
                        b.end_date,
                        c.category_name,
                        bc.allocated_amount,
                        COALESCE(SUM(t.amount), 0) AS spent
                    FROM budgets b
                    JOIN budget_category bc
                        ON b.budget_id = bc.budget_id
                    JOIN categories c
                        ON bc.category_id = c.category_id
                    LEFT JOIN transactions t
                        ON t.user_id = b.user_id
                        AND t.category_id = bc.category_id
                        AND t.transaction_type = 'Expense'
                        AND t.transaction_date
                            BETWEEN b.start_date AND b.end_date
                    WHERE b.user_id = %s
                    GROUP BY
                        b.budget_id,
                        b.budget_name,
                        b.start_date,
                        b.end_date,
                        c.category_name,
                        bc.allocated_amount
                    ORDER BY b.start_date DESC, c.category_name
                """, (user_id,))

                rows = cur.fetchall()

        budgets = [
            {
                "budget_id": row[0],
                "budget_name": row[1],
                "start_date": row[2].isoformat(),
                "end_date": row[3].isoformat(),
                "category": row[4],
                "allocated": float(row[5]),
                "spent": float(row[6]),
                "remaining": float(row[5]) - float(row[6])
            }
            for row in rows
        ]

        return jsonify(budgets)

    except Exception:
        app.logger.exception("Could not load budgets")
        return jsonify({"error": "Could not load budgets."}), 500

@app.route("/api/goals", methods=["POST"])
def create_goal():
    from decimal import Decimal, InvalidOperation
    from datetime import date

    data = request.get_json(silent=True) or {}

    goal_name = (data.get("goal_name") or "").strip()
    target_date_value = data.get("target_date")
    account_id_value = data.get("account_id")

    if not goal_name:
        return jsonify({"error": "Goal name is required."}), 400

    if len(goal_name) > 100:
        return jsonify({"error": "Goal name must be 100 characters or fewer."}), 400

    try:
        target_amount = Decimal(str(data.get("target_amount", "")))

        if not target_amount.is_finite() or target_amount <= 0:
            return jsonify({
                "error": "Target amount must be a positive number."
            }), 400

        target_date = None
        if target_date_value:
            target_date = date.fromisoformat(target_date_value)

        account_id = None
        if account_id_value not in (None, ""):
            account_id = int(account_id_value)
            if account_id <= 0:
                raise ValueError

    except (InvalidOperation, ValueError, TypeError):
        return jsonify({
            "error": "Enter a valid target amount, date, and account."
        }), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                # Verify that the selected account belongs to this user.
                if account_id is not None:
                    cur.execute("""
                        SELECT account_id
                        FROM accounts
                        WHERE account_id = %s AND user_id = %s
                    """, (account_id, user_id))

                    if cur.fetchone() is None:
                        return jsonify({
                            "error": "Selected account was not found."
                        }), 404

                cur.execute("""
                    INSERT INTO savings_goals (
                        user_id,
                        account_id,
                        goal_name,
                        target_amount,
                        saved_amount,
                        target_date,
                        status
                    )
                    VALUES (%s, %s, %s, %s, 0, %s, 'Active')
                    RETURNING goal_id, goal_name, target_amount,
                              saved_amount, target_date, status, account_id
                """, (
                    user_id,
                    account_id,
                    goal_name,
                    target_amount,
                    target_date
                ))

                row = cur.fetchone()

        return jsonify({
            "message": "Savings goal created successfully.",
            "goal_id": row[0],
            "goal_name": row[1],
            "target_amount": float(row[2]),
            "saved_amount": float(row[3]),
            "target_date": row[4].isoformat() if row[4] else None,
            "status": row[5],
            "account_id": row[6]
        }), 201

    except Exception:
        app.logger.exception("Could not create savings goal")
        return jsonify({
            "error": "Could not create savings goal."
        }), 500

@app.route("/api/goals/<int:goal_id>", methods=["PUT"])
def update_goal(goal_id):
    from decimal import Decimal, InvalidOperation
    from datetime import date

    data = request.get_json(silent=True) or {}

    goal_name = (data.get("goal_name") or "").strip()
    target_date_value = data.get("target_date")
    account_id_value = data.get("account_id")

    if not goal_name:
        return jsonify({"error": "Goal name is required."}), 400

    if len(goal_name) > 100:
        return jsonify({"error": "Goal name must be 100 characters or fewer."}), 400

    try:
        target_amount = Decimal(str(data.get("target_amount", "")))

        if not target_amount.is_finite() or target_amount <= 0:
            return jsonify({"error": "Target amount must be positive."}), 400

        target_date = date.fromisoformat(target_date_value) if target_date_value else None

        if account_id_value in (None, ""):
            return jsonify({"error": "Please select a linked account."}), 400

        account_id = int(account_id_value)

        if account_id <= 0:
            raise ValueError

    except (InvalidOperation, ValueError, TypeError):
        return jsonify({"error": "Enter valid goal details."}), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                cur.execute("""
                    SELECT saved_amount, status
                    FROM savings_goals
                    WHERE goal_id = %s AND user_id = %s
                    FOR UPDATE
                """, (goal_id, user_id))

                goal = cur.fetchone()

                if goal is None:
                    return jsonify({"error": "Savings goal not found."}), 404

                saved_amount = Decimal(str(goal[0]))
                status = goal[1]

                if target_amount < saved_amount:
                    return jsonify({
                        "error": "Target amount cannot be less than the amount already saved."
                    }), 400

                cur.execute("""
                    SELECT account_id
                    FROM accounts
                    WHERE account_id = %s AND user_id = %s
                """, (account_id, user_id))

                if cur.fetchone() is None:
                    return jsonify({"error": "Selected account was not found."}), 404

                new_status = (
                    "Completed" if saved_amount == target_amount
                    else "Active" if status == "Completed"
                    else status
                )

                cur.execute("""
                    UPDATE savings_goals
                    SET goal_name = %s,
                        target_amount = %s,
                        target_date = %s,
                        account_id = %s,
                        status = %s
                    WHERE goal_id = %s AND user_id = %s
                """, (
                    goal_name, target_amount, target_date,
                    account_id, new_status, goal_id, user_id
                ))

        return jsonify({"message": "Savings goal updated successfully."}), 200

    except Exception:
        app.logger.exception("Could not update savings goal")
        return jsonify({"error": "Could not update savings goal."}), 500

@app.route("/api/goals", methods=["GET"])
def get_goals():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                cur.execute("""
                    SELECT
                        goal_id,
                        goal_name,
                        target_amount,
                        saved_amount,
                        target_date,
                        status
                    FROM savings_goals
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (user_id,))

                rows = cur.fetchall()

        goals = [
            {
                "goal_id": row[0],
                "goal_name": row[1],
                "target_amount": float(row[2]),
                "saved_amount": float(row[3]),
                "target_date": row[4].isoformat() if row[4] else None,
                "status": row[5]
            }
            for row in rows
        ]

        return jsonify(goals)

    except Exception:
        app.logger.exception("Could not load savings goals")
        return jsonify({"error": "Could not load savings goals."}), 500
    


@app.route("/api/goals/<int:goal_id>/contribute", methods=["POST"])
def contribute_to_goal(goal_id):
    from decimal import Decimal, InvalidOperation
    from datetime import date

    data = request.get_json(silent=True) or {}

    try:
        amount = Decimal(str(data.get("amount", "")))

        if not amount.is_finite() or amount <= 0:
            return jsonify({
                "error": "Contribution must be a positive amount."
            }), 400

    except (InvalidOperation, ValueError, TypeError):
        return jsonify({
            "error": "Enter a valid contribution amount."
        }), 400

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({
                        "error": "Demo user not found."
                    }), 404

                # Lock the goal.
                cur.execute("""
                    SELECT account_id, goal_name, saved_amount,
                           target_amount, status
                    FROM savings_goals
                    WHERE goal_id = %s AND user_id = %s
                    FOR UPDATE
                """, (goal_id, user_id))

                goal = cur.fetchone()

                if goal is None:
                    return jsonify({
                        "error": "Savings goal not found."
                    }), 404

                account_id = goal[0]
                goal_name = goal[1]
                saved_amount = Decimal(str(goal[2]))
                target_amount = Decimal(str(goal[3]))
                status = goal[4]

                if status != "Active":
                    return jsonify({
                        "error": "Only active goals can receive contributions."
                    }), 400

                if account_id is None:
                    return jsonify({
                        "error": "Link this goal to an account before contributing."
                    }), 400

                remaining = target_amount - saved_amount

                if amount > remaining:
                    return jsonify({
                        "error": "Contribution exceeds the remaining goal amount.",
                        "remaining": float(remaining)
                    }), 400

                # Lock and verify the linked account.
                cur.execute("""
                    SELECT balance
                    FROM accounts
                    WHERE account_id = %s AND user_id = %s
                    FOR UPDATE
                """, (account_id, user_id))

                account = cur.fetchone()

                if account is None:
                    return jsonify({
                        "error": "Linked account was not found."
                    }), 404

                balance = Decimal(str(account[0]))

                if amount > balance:
                    return jsonify({
                        "error": "Insufficient account balance.",
                        "available_balance": float(balance)
                    }), 400

                # Find a matching Expense category.
                cur.execute("""
                    SELECT category_id
                    FROM categories
                    WHERE category_type = 'Expense'
                      AND (user_id = %s OR user_id IS NULL)
                    ORDER BY
                        CASE
                            WHEN LOWER(category_name) = 'savings' THEN 1
                            WHEN LOWER(category_name) = 'savings goal' THEN 2
                            ELSE 3
                        END,
                        category_id
                    LIMIT 1
                """, (user_id,))

                category = cur.fetchone()

                if category is None:
                    return jsonify({
                        "error": (
                            "Create an Expense category first to record "
                            "savings contributions."
                        )
                    }), 400

                category_id = category[0]

                new_saved_amount = saved_amount + amount
                new_balance = balance - amount
                new_status = (
                    "Completed"
                    if new_saved_amount == target_amount
                    else "Active"
                )

                # 1. Deduct money from the linked account.
                cur.execute("""
                    UPDATE accounts
                    SET balance = %s
                    WHERE account_id = %s AND user_id = %s
                """, (new_balance, account_id, user_id))

                # 2. Update the savings goal.
                cur.execute("""
                    UPDATE savings_goals
                    SET saved_amount = %s, status = %s
                    WHERE goal_id = %s AND user_id = %s
                """, (
                    new_saved_amount, new_status, goal_id, user_id
                ))

                # 3. Record the contribution as an Expense transaction.
                cur.execute("""
                    INSERT INTO transactions (
                        user_id, account_id, category_id, amount,
                        transaction_type, transaction_date, description
                    )
                    VALUES (%s, %s, %s, %s, 'Expense', %s, %s)
                    RETURNING transaction_id
                """, (
                    user_id,
                    account_id,
                    category_id,
                    amount,
                    date.today(),
                    f"Savings goal contribution: {goal_name}"
                ))

                transaction_id = cur.fetchone()[0]

        return jsonify({
            "message": "Contribution added and transaction recorded successfully.",
            "transaction_id": transaction_id,
            "goal_id": goal_id,
            "contribution": float(amount),
            "saved_amount": float(new_saved_amount),
            "target_amount": float(target_amount),
            "remaining": float(target_amount - new_saved_amount),
            "account_balance": float(new_balance),
            "status": new_status
        }), 200

    except Exception:
        app.logger.exception("Could not add savings contribution")
        return jsonify({
            "error": "Could not add savings contribution."
        }), 500


@app.route("/api/goals/<int:goal_id>", methods=["DELETE"])
def delete_goal(goal_id):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({
                        "error": "Demo user not found."
                    }), 404

                cur.execute("""
                    DELETE FROM savings_goals
                    WHERE goal_id = %s AND user_id = %s
                    RETURNING goal_id
                """, (goal_id, user_id))

                deleted_goal = cur.fetchone()

                if deleted_goal is None:
                    return jsonify({
                        "error": "Savings goal not found."
                    }), 404

        return jsonify({
            "message": "Savings goal deleted successfully."
        }), 200

    except Exception:
        app.logger.exception("Could not delete savings goal")
        return jsonify({
            "error": "Could not delete savings goal."
        }), 500

@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                user_id = get_demo_user_id(cur)

                if user_id is None:
                    return jsonify({"error": "Demo user not found."}), 404

                cur.execute("""
                    SELECT
                        t.transaction_id,
                        t.amount,
                        t.transaction_type,
                        t.transaction_date,
                        t.description,
                        a.account_name,
                        c.category_name,
                        t.account_id,
                        t.category_id
                    FROM transactions t
                    JOIN accounts a
                        ON t.account_id = a.account_id
                    JOIN categories c
                        ON t.category_id = c.category_id
                    WHERE t.user_id = %s
                    ORDER BY t.transaction_date DESC,
                             t.transaction_id DESC
                """, (user_id,))

                rows = cur.fetchall()

        transactions = [
            {
                "transaction_id": row[0],
                "amount": float(row[1]),
                "transaction_type": row[2],
                "transaction_date": row[3].isoformat(),
                "description": row[4],
                "account_name": row[5],
                "category_name": row[6],
                "account_id": row[7],
                "category_id": row[8]
            }
            for row in rows
        ]

        return jsonify(transactions)

    except Exception:
        app.logger.exception("Could not load transactions")
        return jsonify({
            "error": "Could not load transactions."
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
