const API = 'http://127.0.0.1:8000';

const form = document.getElementById('expense-form');
const list = document.getElementById('expense-list');
const totalEl = document.getElementById('total');
const filterEl = document.getElementById('filter');

async function loadExpenses() {
  const res = await fetch(`${API}/expenses`);
  const expenses = await res.json();

  const filter = filterEl.value;
  const visible = filter === 'all'
    ? expenses
    : expenses.filter(e => e.category === filter);

  list.innerHTML = '';

  visible.forEach(expense => {
    const li = document.createElement('li');
    li.innerHTML = `
      <span>${expense.description}</span>
      <span class="category-badge">${expense.category}</span>
      <span>$${parseFloat(expense.amount).toFixed(2)}</span>
      <button class="delete-btn" onclick="deleteExpense(${expense.id})">✕</button>
    `;
    list.appendChild(li);
  });

  const total = expenses.reduce((sum, e) => sum + parseFloat(e.amount), 0);
  totalEl.textContent = '$' + total.toFixed(2);
}

form.addEventListener('submit', async function(e) {
  e.preventDefault();
  await fetch(`${API}/expenses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      description: document.getElementById('description').value,
      amount: parseFloat(document.getElementById('amount').value),
      category: document.getElementById('category').value
    })
  });
  form.reset();
  loadExpenses();
});

async function deleteExpense(id) {
  await fetch(`${API}/expenses/${id}`, { method: 'DELETE' });
  loadExpenses();
}

filterEl.addEventListener('change', loadExpenses);

loadExpenses();