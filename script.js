let expenses = [];

const form = document.getElementById('expense-form');
const list = document.getElementById('expense-list');
const totalEl = document.getElementById('total');
const filterEl = document.getElementById('filter');

form.addEventListener('submit', function(e) {
    e.preventDefault();

    const expense = {
        id: Date.now(),
        description: document.getElementById('description').value,
        amount: parseFloat(document.getElementById('amount').value),
        category: document.getElementById('category').value
    };

    // These lines are necessary for the following reasons:
    // 1. `expenses.push(expense);` - Adds the newly submitted expense object to the main `expenses` array, so it is tracked and can be rendered.
    // 2. `form.reset();` - Clears the form fields after submission, providing a clean slate for the next entry and improving user experience.
    // 3. `render();` - Updates the displayed list of expenses and total, so the UI immediately reflects the most recent changes.
    expenses.push(expense);
    form.reset();
    render();

});

filterEl.addEventListener('change', render);

function render() {
    const filter =  filterEl.value;
    const visible = filter === 'all'
    ? expenses
    : expenses.filter(e => e.category === filter);

    list.innerHTML = '';

    visible.forEach(function(expense) {
        const li = document.createElement('li');
        li.innerHTML = `
        <span>${expense.description}</span>
        <span class="category-badge">${expense.category}</span>
        <span>$${expense.amount.toFixed(2)}</span>
        <button class="delete-btn" onclick="deleteExpense(${expense.id})">x</button>
        `;
        list.appendChild(li);
    });

    const total = expenses.reduce((sum, e) => sum + e.amount, 0);
    totalEl.textContent = '$' + total.toFixed(2);
};

function deleteExpense(id) {
    expenses = expenses.filter(e => e.id !== id);
    render();
}