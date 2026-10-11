
async function loadDashboard() {
    const message = document.getElementById("dashboard-message");

    try {
        const response = await fetch("/api/dashboard");
        if (!response.ok) throw new Error("Dashboard request failed");

        const data = await response.json();

        document.getElementById("total-balance").textContent =
            formatCurrency(data.total_balance);
        document.getElementById("total-income").textContent =
            formatCurrency(data.total_income);
        document.getElementById("total-expenses").textContent =
            formatCurrency(data.total_expenses);

        message.textContent = "";
        await loadTransactions();
    } catch (error) {
        message.textContent = "Unable to load dashboard data.";
        console.error(error);
    }
}

async function loadTransactions() {
    const list = document.getElementById("transaction-list");
    const message = document.getElementById("dashboard-message");

    try {
        const response = await fetch("/api/transactions");
        if (!response.ok) throw new Error("Could not load transactions.");

        const transactions = await response.json();

        if (transactions.length === 0) {
            list.innerHTML =
                '<tr><td colspan="7">No transactions found.</td></tr>';
            return;
        }

        list.innerHTML = transactions.map(tx => `
            <tr>
                <td>${escapeHTML(tx.description || "Transaction")}</td>
                <td>${escapeHTML(tx.category_name)}</td>
                <td>${escapeHTML(tx.account_name)}</td>
                <td>${escapeHTML(tx.transaction_date)}</td>
                <td class="${tx.transaction_type === "Income"
                    ? "type-income" : "type-expense"}">
                    ${escapeHTML(tx.transaction_type)}
                </td>
                <td>${formatCurrency(tx.amount)}</td>
                <td>
                    <button type="button" class="edit-btn"
                        onclick="editTransaction(${Number(tx.transaction_id)})">
                        Edit
                    </button>
                    <button type="button" class="delete-btn"
                        onclick="deleteTransaction(${Number(tx.transaction_id)})">
                        Delete
                    </button>
                </td>
            </tr>
        `).join("");

    } catch (error) {
        list.innerHTML =
            '<tr><td colspan="7">Could not load transactions.</td></tr>';
        message.textContent = error.message;
        console.error(error);
    }
}

async function loadAccounts() {
    const select = document.getElementById("account-id");
    const accountList = document.getElementById("account-list");

    const response = await fetch("/api/accounts");
    if (!response.ok) {
        throw new Error("Could not load accounts");
    }

    const accounts = await response.json();

    // Keep the transaction form's account dropdown working.
    select.innerHTML = '<option value="">Select account</option>';

    accounts.forEach(account => {
        const option = document.createElement("option");
        option.value = account.account_id;
        option.textContent = account.account_name;
        select.appendChild(option);
    });

    // Populate the Account Management table.
    if (accountList) {
        if (accounts.length === 0) {
            accountList.innerHTML =
                '<tr><td colspan="5">No accounts found.</td></tr>';
        } else {
            accountList.innerHTML = accounts.map(account => `
                <tr>
                    <td>${escapeHTML(account.account_name)}</td>
                    <td>${escapeHTML(account.account_type)}</td>
                    <td>${formatCurrency(Number(account.balance))}</td>
                    <td>${account.is_default ? "Yes" : "No"}</td>
                    <td>
                        <button type="button"
                            onclick="editAccount(${Number(account.account_id)})">
                            Edit
                        </button>
                        <button type="button"
                            onclick="setDefaultAccount(${Number(account.account_id)})"
                            ${account.is_default ? "disabled" : ""}>
                            Set Default
                        </button>
                        <button type="button"
                            onclick="deleteAccount(${Number(account.account_id)})">
                            Delete
                        </button>
                    </td>
                </tr>
            `).join("");
        }
    }
}

document.getElementById("account-form").addEventListener("submit", async function (event) {
    if (document.getElementById("edit-account-id").value) {
        return;
    }
    event.preventDefault();

    const form = this;
    const message = document.getElementById("account-form-message");
    const button = document.getElementById("account-submit");

    const accountData = {
        account_name: document.getElementById("account-name").value.trim(),
        account_type: document.getElementById("account-type").value
    };

    if (!accountData.account_name) {
        message.style.color = "#df5c68";
        message.textContent = "Please enter an account name.";
        return;
    }

    button.disabled = true;
    message.textContent = "";

    try {
        const response = await fetch("/api/accounts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(accountData)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not create account.");
        }

        form.reset();

        message.style.color = "#159b72";
        message.textContent = "Account created successfully.";

        await loadAccounts();
        await loadDashboard();
    } catch (error) {
        message.style.color = "#df5c68";
        message.textContent = error.message;
    } finally {
        button.disabled = false;
    }
});


async function editAccount(accountId) {
    try {
        const response = await fetch("/api/accounts");
        if (!response.ok) {
            throw new Error("Could not load accounts.");
        }

        const accounts = await response.json();
        const account = accounts.find(
            item => Number(item.account_id) === Number(accountId)
        );

        if (!account) {
            throw new Error("Account not found.");
        }

        document.getElementById("edit-account-id").value =
            account.account_id;
        document.getElementById("account-name").value =
            account.account_name;
        document.getElementById("account-type").value =
            account.account_type;

        document.getElementById("account-submit").textContent =
            "Save Changes";
        document.getElementById("account-cancel").hidden = false;

        document.getElementById("account-form-message").textContent =
            "Editing " + account.account_name;

        document.getElementById("accounts").scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    } catch (error) {
        document.getElementById("accounts-message").textContent =
            error.message;
    }
}

document.getElementById("account-form").addEventListener(
    "submit",
    async function (event) {
        const editId = document.getElementById("edit-account-id").value;

        // The existing Create Account handler handles new accounts.
        if (!editId) return;

        event.preventDefault();

        const message = document.getElementById("account-form-message");
        const button = document.getElementById("account-submit");

        const accountData = {
            account_name: document.getElementById("account-name").value.trim(),
            account_type: document.getElementById("account-type").value
        };

        if (!accountData.account_name) {
            message.style.color = "#df5c68";
            message.textContent = "Please enter an account name.";
            return;
        }

        button.disabled = true;

        try {
            const response = await fetch(`/api/accounts/${editId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(accountData)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Could not update account.");
            }

            resetAccountForm();
            message.style.color = "#159b72";
            message.textContent = "Account updated successfully.";

            await loadAccounts();
            await loadDashboard();
        } catch (error) {
            message.style.color = "#df5c68";
            message.textContent = error.message;
        } finally {
            button.disabled = false;
        }
    }
);

function resetAccountForm() {
    document.getElementById("account-form").reset();
    document.getElementById("edit-account-id").value = "";
    document.getElementById("account-submit").textContent = "Create Account";
    document.getElementById("account-cancel").hidden = true;
}

async function setDefaultAccount(accountId) {
    const message = document.getElementById("accounts-message");

    try {
        const response = await fetch(
            `/api/accounts/${accountId}/default`,
            { method: "PUT" }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not set default account.");
        }

        message.style.color = "#159b72";
        message.textContent = "Default account updated successfully.";

        await loadAccounts();
    } catch (error) {
        message.style.color = "#df5c68";
        message.textContent = error.message;
    }
}

async function deleteAccount(accountId) {
    const confirmed = confirm(
        "Are you sure you want to delete this account? This action cannot be undone."
    );

    if (!confirmed) return;

    const message = document.getElementById("accounts-message");

    try {
        const response = await fetch(`/api/accounts/${accountId}`, {
            method: "DELETE"
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not delete account.");
        }

        message.style.color = "#159b72";
        message.textContent = "Account deleted successfully.";

        await loadAccounts();
        await loadDashboard();
    } catch (error) {
        message.style.color = "#df5c68";
        message.textContent = error.message;
    }
}

document.getElementById("account-cancel").addEventListener("click", function () {
    resetAccountForm();
    document.getElementById("account-form-message").textContent = "";
});

async function loadCategories() {
    const select = document.getElementById("category-id");
    const type = document.getElementById("transaction-type").value;

    select.innerHTML = '<option value="">Loading categories...</option>';

    try {
        const response = await fetch(
            `/api/categories?type=${encodeURIComponent(type)}`
        );
        if (!response.ok) throw new Error("Could not load categories");

        const categories = await response.json();
        select.innerHTML = '<option value="">Select category</option>';

        categories.forEach(category => {
            const option = document.createElement("option");
            option.value = category.category_id;
            option.textContent = category.category_name;
            select.appendChild(option);
        });

        if (categories.length === 0) {
            select.innerHTML =
                '<option value="">No categories available</option>';
        }
    } catch (error) {
        select.innerHTML =
            '<option value="">Could not load categories</option>';
        console.error(error);
    }
}

function formatCurrency(amount) {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2
    }).format(Number(amount) || 0);
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[character]);
}

function setToday() {
    const now = new Date();
    const localDate = [
        now.getFullYear(),
        String(now.getMonth() + 1).padStart(2, "0"),
        String(now.getDate()).padStart(2, "0")
    ].join("-");

    document.getElementById("transaction-date").value = localDate;
}

async function refreshFinanceViews() {
    await loadDashboard();
    await loadBudgets();
    await loadGoals();
}

async function submitTransaction(event) {
    event.preventDefault();

    const form = document.getElementById("transaction-form");
    const message = document.getElementById("form-message");
    const button = form.querySelector('button[type="submit"]');

    message.textContent = "";

    const formData = new FormData(form);
    const transaction = {
        transaction_type: formData.get("transaction_type"),
        amount: formData.get("amount"),
        account_id: formData.get("account_id"),
        category_id: formData.get("category_id"),
        transaction_date: formData.get("transaction_date"),
        description: formData.get("description")
    };

    button.disabled = true;
    button.textContent = "Saving...";

    try {
        const response = await fetch("/api/transactions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(transaction)
        });

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || "Could not save transaction.");
        }

        message.style.color = "#159b72";
        message.textContent = "Transaction added successfully!";

        form.reset();
        setToday();
        await loadCategories();
        await refreshFinanceViews();
    } catch (error) {
        message.style.color = "#df5c68";
        message.textContent = error.message;
    } finally {
        button.disabled = false;
        button.textContent = "Add Transaction";
    }
}

async function editTransaction(transactionId) {
    try {
        const response = await fetch("/api/transactions");
        if (!response.ok) throw new Error("Could not load transaction.");

        const transactions = await response.json();
        const tx = transactions.find(
            item => Number(item.transaction_id) === Number(transactionId)
        );

        if (!tx) throw new Error("Transaction not found.");

        const form = document.getElementById("transaction-form");
        const message = document.getElementById("form-message");

        document.getElementById("transaction-type").value =
            tx.transaction_type;
        await loadCategories();

        document.getElementById("amount").value = tx.amount;
        document.getElementById("account-id").value = tx.account_id ?? "";
        document.getElementById("category-id").value = tx.category_id ?? "";
        document.getElementById("transaction-date").value =
            tx.transaction_date;
        document.getElementById("description").value = tx.description || "";

        // The current GET endpoint must return account_id and category_id
        // for this form to prefill those two dropdowns.
        if (tx.account_id == null || tx.category_id == null) {
            message.style.color = "#df5c68";
            message.textContent =
                "The transactions API must include account_id and category_id to edit.";
            return;
        }

        form.dataset.editingId = transactionId;
        form.querySelector('button[type="submit"]').textContent =
            "Save Changes";
        message.style.color = "#555";
        message.textContent =
            "Editing transaction #" + transactionId +
            ". Submit the form to save changes.";

        form.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
        document.getElementById("dashboard-message").textContent =
            error.message;
    }
}

async function deleteTransaction(transactionId) {
    if (!confirm(
        `Delete transaction #${transactionId}? This will also adjust the account balance.`
    )) return;

    const message = document.getElementById("dashboard-message");

    try {
        const response = await fetch(`/api/transactions/${transactionId}`, {
            method: "DELETE"
        });

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || "Could not delete transaction.");
        }

        message.textContent = "Transaction deleted successfully.";
        await refreshFinanceViews();
    } catch (error) {
        message.textContent = error.message;
    }
}

async function loadBudgets() {
    const container = document.getElementById("budget-list");
    const message = document.getElementById("budget-message");

    try {
        const response = await fetch("/api/budgets");
        if (!response.ok) throw new Error("Could not retrieve budgets.");

        const budgets = await response.json();
        message.textContent = "";

        if (budgets.length === 0) {
            container.textContent = "No budgets found.";
            return;
        }

        container.innerHTML = budgets.map(budget => {
            const allocated = Number(budget.allocated);
            const spent = Number(budget.spent);
            const percentage = allocated > 0 ? spent / allocated * 100 : 0;
            const barWidth = Math.min(percentage, 100);
            const overBudget = spent > allocated;

            return `
                <article class="budget-card">
                    <div class="budget-card-header">
                        <h3>${escapeHTML(budget.category)}</h3>
                        <span>${percentage.toFixed(0)}%</span>
                    </div>
                    <p class="budget-period">
                        ${escapeHTML(budget.budget_name)}
                        · ${escapeHTML(budget.start_date)}
                        to ${escapeHTML(budget.end_date)}
                    </p>
                    <div class="budget-amounts">
                        <span>Spent <strong>${formatCurrency(spent)}</strong></span>
                        <span>Limit ${formatCurrency(allocated)}</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill ${overBudget ? "over-budget" : ""}"
                             style="width: ${barWidth}%"></div>
                    </div>
                    <p class="budget-status">
                        ${overBudget
                            ? `Over budget by ${formatCurrency(spent - allocated)}`
                            : `${formatCurrency(allocated - spent)} remaining`}
                    </p>
                </article>
            `;
        }).join("");
    } catch (error) {
        container.textContent = "Unable to load budgets.";
        message.textContent = error.message;
        console.error(error);
    }
}


async function loadGoals() {
    const container = document.getElementById("goals-list");
    const message = document.getElementById("goals-message");

    try {
        const response = await fetch("/api/goals");
        if (!response.ok) {
            throw new Error("Could not retrieve savings goals.");
        }

        const goals = await response.json();
        message.textContent = "";

        if (goals.length === 0) {
            container.textContent = "No savings goals found.";
            return;
        }

        container.innerHTML = goals.map(goal => {
            const target = Number(goal.target_amount);
            const saved = Number(goal.saved_amount);
            const remaining = Math.max(target - saved, 0);
            const percentage = target > 0 ? saved / target * 100 : 0;
            const barWidth = Math.min(percentage, 100);

            return `
                <article class="goal-card">
                    <h3>${escapeHTML(goal.goal_name)}</h3>

                    <p class="goal-target">
                        Target: ${formatCurrency(target)}
                        ${goal.target_date
                            ? ` · Due ${escapeHTML(goal.target_date)}`
                            : ""}
                    </p>

                    <div class="goal-progress-text">
                        <strong>${formatCurrency(saved)} saved</strong>
                        <span>${percentage.toFixed(1)}%</span>
                    </div>

                    <div class="progress-track">
                        <div class="progress-fill"
                             style="width: ${barWidth}%"></div>
                    </div>

                    <p>Remaining: ${formatCurrency(remaining)}</p>
                    <span class="goal-status">${escapeHTML(goal.status)}</span>

                    <div class="form-actions">
                        <button type="button"
                            onclick="editGoal(${Number(goal.goal_id)})">
                            Edit
                        </button>
                        <button type="button"
                            onclick="deleteGoal(${Number(goal.goal_id)})">
                            Delete
                        </button>
                    </div>

                    ${goal.status === "Active" ? `
                        <div class="contribution-form">
                            <label for="contribution-${Number(goal.goal_id)}">
                                Add contribution (₹)
                            </label>
                            <input
                                id="contribution-${Number(goal.goal_id)}"
                                type="number"
                                min="0.01"
                                step="0.01"
                                max="${remaining}"
                                placeholder="Enter amount"
                            >
                            <button
                                type="button"
                                onclick="contributeToGoal(${Number(goal.goal_id)})">
                                Contribute
                            </button>
                        </div>
                    ` : ""}
                </article>
            `;
        }).join("");
    } catch (error) {
        container.textContent = "Unable to load savings goals.";
        message.textContent = error.message;
        console.error(error);
    }
}

async function deleteGoal(goalId) {
    const confirmed = confirm(
        "Are you sure you want to delete this savings goal? " +
        "Its contribution history will remain in transactions."
    );

    if (!confirmed) return;

    const message = document.getElementById("goals-message");

    try {
        const response = await fetch(`/api/goals/${goalId}`, {
            method: "DELETE"
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not delete goal.");
        }

        message.textContent = result.message;
        await loadGoals();

    } catch (error) {
        message.textContent = error.message;
        console.error(error);
    }
}

async function editGoal(goalId) {
    try {
        const response = await fetch("/api/goals");

        if (!response.ok) {
            throw new Error("Could not load goal details.");
        }

        const goals = await response.json();
        const goal = goals.find(item => Number(item.goal_id) === goalId);

        if (!goal) {
            throw new Error("Savings goal not found.");
        }

        document.getElementById("edit-goal-id").value = goal.goal_id;
        document.getElementById("goal-name").value = goal.goal_name;
        document.getElementById("goal-target").value = goal.target_amount;
        document.getElementById("goal-date").value = goal.target_date || "";

        document.getElementById("goal-form-heading").textContent = "Edit Savings Goal";
        document.getElementById("goal-submit").textContent = "Update Goal";
        document.getElementById("goal-cancel").hidden = false;
        document.getElementById("goal-form-message").textContent = "";

        await loadGoalAccounts(goal.account_id || "");

        document.getElementById("goal-form").scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    } catch (error) {
        document.getElementById("goals-message").textContent = error.message;
    }
}


async function contributeToGoal(goalId) {
    const input = document.getElementById(`contribution-${goalId}`);
    const message = document.getElementById("goals-message");
    const amount = Number(input.value);

    if (!Number.isFinite(amount) || amount <= 0) {
        message.textContent = "Enter a valid positive amount.";
        return;
    }

    try {
        const response = await fetch(
            `/api/goals/${goalId}/contribute`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ amount })
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Contribution failed.");
        }

        message.textContent =
            `Contribution added! Saved: ${formatCurrency(result.saved_amount)}.`;

        await loadGoals();
    } catch (error) {
        message.textContent = error.message;
        console.error(error);
    }
}


document.addEventListener("DOMContentLoaded", async () => {
    setToday();

    document.getElementById("transaction-type")
        .addEventListener("change", loadCategories);

    document.getElementById("transaction-form")
        .addEventListener("submit", async event => {
            const form = event.currentTarget;
            const editingId = form.dataset.editingId;

            if (!editingId) {
                await submitTransaction(event);
                return;
            }

            event.preventDefault();

            const message = document.getElementById("form-message");
            const button = form.querySelector('button[type="submit"]');
            const formData = new FormData(form);

            const transaction = {
                transaction_type: formData.get("transaction_type"),
                amount: formData.get("amount"),
                account_id: formData.get("account_id"),
                category_id: formData.get("category_id"),
                transaction_date: formData.get("transaction_date"),
                description: formData.get("description")
            };

            button.disabled = true;
            message.textContent = "";

            try {
                const response = await fetch(
                    `/api/transactions/${editingId}`,
                    {
                        method: "PUT",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(transaction)
                    }
                );

                const result = await response.json();
                if (!response.ok) {
                    throw new Error(result.error || "Could not update transaction.");
                }

                delete form.dataset.editingId;
                form.reset();
                setToday();
                await loadCategories();

                button.textContent = "Add Transaction";
                message.style.color = "#159b72";
                message.textContent = "Transaction updated successfully.";

                await refreshFinanceViews();
            } catch (error) {
                message.style.color = "#df5c68";
                message.textContent = error.message;
            } finally {
                button.disabled = false;
                if (!form.dataset.editingId) {
                    button.textContent = "Add Transaction";
                } else {
                    button.textContent = "Save Changes";
                }
            }
        });

    try {
        await loadAccounts();
        await loadCategories();
    } catch (error) {
        document.getElementById("form-message").textContent =
            "Could not load accounts or categories. Check Flask and the database.";
        console.error(error);
    }

    await loadDashboard();
    await loadBudgets();
    await loadGoals();
});


async function loadManagedCategories() {
    const table = document.getElementById("category-list");
    const message = document.getElementById("categories-message");

    if (!table) return;

    table.innerHTML = "";

    try {
        const types = ["Expense", "Income"];

        for (const type of types) {
            const response = await fetch(
                `/api/categories?type=${encodeURIComponent(type)}`
            );

            if (!response.ok) {
                throw new Error(`Could not load ${type} categories.`);
            }

            const categories = await response.json();

            for (const category of categories) {
                const row = document.createElement("tr");

                // Category name
                const nameCell = document.createElement("td");
                nameCell.textContent = category.category_name;

                // Category type
                const typeCell = document.createElement("td");
                typeCell.textContent = category.category_type || type;

                // Monthly spending limit
                const limitCell = document.createElement("td");

                if (type === "Expense") {
                    limitCell.textContent =
                        "₹" +
                        Number(category.monthly_limit || 0)
                            .toLocaleString("en-IN", {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                } else {
                    limitCell.textContent = "—";
                }

                // Description
                const descriptionCell = document.createElement("td");
                descriptionCell.textContent =
                    category.description || "—";

                // Actions
                const actionsCell = document.createElement("td");

                const editButton = document.createElement("button");
                editButton.type = "button";
                editButton.textContent = "Edit";

                editButton.addEventListener("click", () => {
                    document.getElementById("edit-category-id").value =
                        category.category_id;

                    document.getElementById("category-name").value =
                        category.category_name;

                    document.getElementById("category-type").value =
                        category.category_type || type;

                    document.getElementById("category-description").value =
                        category.description || "";

                    const limitInput =
                        document.getElementById("category-monthly-limit");

                    if (limitInput) {
                        limitInput.value =
                            type === "Expense"
                                ? Number(category.monthly_limit || 0)
                                : "";
                    }

                    document.getElementById("category-submit").textContent =
                        "Update Category";

                    const cancelButton =
                        document.getElementById("category-cancel");

                    if (cancelButton) {
                        cancelButton.hidden = false;
                    }

                    document.getElementById("category-form")
                        .scrollIntoView({
                            behavior: "smooth",
                            block: "center"
                        });
                });

                actionsCell.appendChild(editButton);

                row.append(
                    nameCell,
                    typeCell,
                    limitCell,
                    descriptionCell,
                    actionsCell
                );

                table.appendChild(row);
            }
        }

        if (message) {
            message.textContent = table.children.length
                ? ""
                : "No categories found.";
        }
    } catch (error) {
        console.error("Category loading error:", error);

        if (message) {
            message.textContent =
                "Could not load categories. Check the Flask terminal for errors.";
        }
    }
}


document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("category-form");

    if (!form) return;

    const message = document.getElementById("category-form-message");
    const cancelButton = document.getElementById("category-cancel");

    function resetCategoryForm() {
        form.reset();
        document.getElementById("edit-category-id").value = "";
        document.getElementById("category-submit").textContent =
            "Create Category";
        cancelButton.hidden = true;

        if (message) message.textContent = "";
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const categoryId =
            document.getElementById("edit-category-id").value;

        const payload = {
            category_name: document.getElementById("category-name").value.trim(),
            category_type: document.getElementById("category-type").value,
            description: document.getElementById("category-description").value.trim(),
            monthly_limit: document.getElementById("category-monthly-limit").value
        }
        try {
            const response = await fetch(
                categoryId
                    ? `/api/categories/${categoryId}`
                    : "/api/categories",
                {
                    method: categoryId ? "PUT" : "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(payload)
                }
            );

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Could not save category.");
            }

            if (message) {
                message.textContent = categoryId
                    ? "Category updated successfully!"
                    : "Category created successfully!";
            }

            resetCategoryForm();

            await loadManagedCategories();

            if (typeof loadCategories === "function") {
                await loadCategories();
            }
            if (typeof loadBudgets === "function") {
                await loadBudgets();
            }
        } catch (error) {
            if (message) message.textContent = error.message;
        }
    });

    cancelButton.addEventListener("click", resetCategoryForm);

    loadManagedCategories();
});

async function loadGoalAccounts(selectedAccountId = "") {
    const select = document.getElementById("goal-account");

    if (!select) return;

    try {
        const response = await fetch("/api/accounts");
        if (!response.ok) throw new Error("Could not load accounts.");

        const accounts = await response.json();

        select.innerHTML = '<option value="">Select an account</option>';

        accounts.forEach(account => {
            const option = document.createElement("option");
            option.value = account.account_id;
            option.textContent =
                `${account.account_name} — ₹${Number(account.balance).toLocaleString("en-IN")}`;

            if (String(account.account_id) === String(selectedAccountId)) {
                option.selected = true;
            }

            select.appendChild(option);
        });
    } catch (error) {
        console.error(error);
        select.innerHTML = '<option value="">Could not load accounts</option>';
    }
}

document.getElementById("goal-form")?.addEventListener("submit", async function (event) {
    event.preventDefault();

    const goalId = document.getElementById("edit-goal-id").value;

    const payload = {
        goal_name: document.getElementById("goal-name").value.trim(),
        target_amount: document.getElementById("goal-target").value,
        target_date: document.getElementById("goal-date").value || null,
        account_id: document.getElementById("goal-account").value
    };

    const message = document.getElementById("goal-form-message");
    const submitButton = document.getElementById("goal-submit");

    if (!payload.account_id) {
        message.textContent = "Please select a linked account.";
        return;
    }

    try {
        submitButton.disabled = true;

        const response = await fetch(
            goalId ? `/api/goals/${goalId}` : "/api/goals",
            {
                method: goalId ? "PUT" : "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not save goal.");
        }

        message.textContent = result.message || "Goal saved successfully.";

        this.reset();
        document.getElementById("edit-goal-id").value = "";
        submitButton.textContent = "Create Goal";
        document.getElementById("goal-cancel").hidden = true;

        await loadGoalAccounts();
        await loadGoals();
    } catch (error) {
        message.textContent = error.message;
    } finally {
        submitButton.disabled = false;
    }
});

document.getElementById("goal-cancel")?.addEventListener("click", function () {
    document.getElementById("goal-form").reset();
    document.getElementById("edit-goal-id").value = "";
    document.getElementById("goal-submit").textContent = "Create Goal";
    this.hidden = true;
    document.getElementById("goal-form-message").textContent = "";
});

loadGoalAccounts();

document.getElementById("logout-btn")?.addEventListener("click", async () => {
    try {
        const response = await fetch("/api/logout", {
            method: "POST",
            credentials: "same-origin"
        });

        if (response.ok) {
            window.location.replace("/login");
        } else {
            alert("Logout failed. Please try again.");
        }
    } catch (error) {
        alert("Could not connect to the server.");
    }
});


