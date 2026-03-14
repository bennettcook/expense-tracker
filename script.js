let expenses = [];

const form = document.getElementById('expense-form');
const list = document.getElementById('expense-list');
const totalEl = document.getElementById('total');
const filterEl = document.getElementById('filter');

// Fix: Ensure newly added expenses are displayed in the list upon submission by attaching the delete handler outside of inline HTML (better practice).

form.addEventListener('submit', function(e) {
    e.preventDefault();

    const expense = {
        id: Date.now(),
        description: document.getElementById('description').value,
        amount: parseFloat(document.getElementById('amount').value),
        category: document.getElementById('category').value
    };

    expenses.push(expense);       // Add new expense to array
    form.reset();                 // Reset the form fields
    render();                     // Update the visible list (will display the newly added record)
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