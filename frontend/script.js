// ==========================================
// CONFIGURATION & STATE
// ==========================================
const API_BASE_URL = 'http://127.0.0.1:8000';
const SESSION_ID = `user_${Math.floor(Math.random() * 100000)}`;
const POLL_INTERVAL_MS = 3000;

let isPolling = false;
let pollingIntervalId = null;
let currentPendingTools = [];

// ==========================================
// DOM ELEMENTS
// ==========================================
// Chat
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatMessages = document.getElementById('chat-messages');
const sendButton = document.getElementById('send-button');
const customerSelect = document.getElementById('customer-select');

// Database
const dbCardsContainer = document.getElementById('db-cards-container');
const refreshDbBtn = document.getElementById('refresh-db');
const resetDbBtn = document.getElementById('reset-db-btn');

// Modal
const adminModal = document.getElementById('admin-modal');
const adminPendingDetails = document.getElementById('admin-pending-details');
const modalApproveBtn = document.getElementById('modal-approve');
const modalDenyBtn = document.getElementById('modal-deny');

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    fetchDatabase();
});

// ==========================================
// DATABASE LOGIC
// ==========================================
refreshDbBtn.addEventListener('click', fetchDatabase);

if (resetDbBtn) {
    resetDbBtn.addEventListener('click', async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/database/reset`, { method: 'POST' });
            if (response.ok) fetchDatabase();
        } catch (e) {
            console.error("Error resetting database:", e);
        }
    });
}

async function fetchDatabase() {
    try {
        const response = await fetch(`${API_BASE_URL}/database/orders`);
        if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
        
        const data = await response.json();
        renderDatabaseCards(data.orders || data);
    } catch (error) {
        console.error("Error fetching database:", error);
        dbCardsContainer.innerHTML = '<p class="text-secondary">Error loading database records.</p>';
    }
}

function renderDatabaseCards(orders) {
    dbCardsContainer.innerHTML = '';
    
    if (!orders || orders.length === 0) {
        dbCardsContainer.innerHTML = '<p class="text-secondary">No records found.</p>';
        return;
    }

    const groupedOrders = {};
    orders.forEach(order => {
        const custId = order.customer_id || 'Unknown';
        if (!groupedOrders[custId]) groupedOrders[custId] = [];
        groupedOrders[custId].push(order);
    });

    Object.keys(groupedOrders).forEach(custId => {
        const groupContainer = document.createElement('div');
        groupContainer.className = 'customer-group';
        
        const groupHeader = document.createElement('div');
        groupHeader.className = 'customer-group-header';
        groupHeader.textContent = `Customer: ${custId}`;
        
        const cardsWrapper = document.createElement('div');
        cardsWrapper.className = 'customer-cards-wrapper';

        groupedOrders[custId].forEach(order => {
            const card = document.createElement('div');
            card.className = 'card update-flash';
            card.id = `order-${order.id}`;

            let statusClass = 'status-processing';
            const statusText = (order.status || 'Processing').toLowerCase();
            
            if (statusText === 'shipped' || statusText === 'delivered') {
                statusClass = 'status-shipped';
            } else if (statusText === 'cancelled' || statusText === 'refunded') {
                statusClass = 'status-cancelled';
            }

            card.innerHTML = `
                <div class="card-header">
                    <div>
                        <div class="card-title">Order ${order.id}</div>
                    </div>
                    <div class="status-pill ${statusClass}">${order.status}</div>
                </div>
                <div class="card-body">
                    <div class="card-row">
                        <span class="card-label">Item</span>
                        <span class="card-value">${order.item_summary.substring(0, 20) + '...'}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Amount</span>
                        <span class="card-value">$${(order.amount || 0).toFixed(2)}</span>
                    </div>
                </div>
            `;
            cardsWrapper.appendChild(card);
        });

        groupContainer.appendChild(groupHeader);
        groupContainer.appendChild(cardsWrapper);
        dbCardsContainer.appendChild(groupContainer);
    });

    setTimeout(() => {
        document.querySelectorAll('.update-flash').forEach(el => el.classList.remove('update-flash'));
    }, 1000);
}

// ==========================================
// CHAT LOGIC
// ==========================================
function appendMessage(content, role) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    
    if (role === 'system' && content.includes('Waiting')) {
        msgDiv.innerHTML = `<span class="loading-dots">${content}</span>`;
        msgDiv.id = 'waiting-message';
    } else {
        msgDiv.textContent = content;
    }
    
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeWaitingMessage() {
    const waitingMsg = document.getElementById('waiting-message');
    if (waitingMsg) waitingMsg.remove();
}

function setInputState(disabled) {
    chatInput.disabled = disabled;
    sendButton.disabled = disabled;
    if (!disabled) chatInput.focus();
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;

    const customerId = customerSelect.value;
    
    appendMessage(message, 'user');
    chatInput.value = '';
    setInputState(true);

    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: SESSION_ID, customer_id: customerId, message: message })
        });

        const data = await response.json();

        if (data.status === 'paused') {
            if (data.ai_response) appendMessage(data.ai_response, 'assistant');
            appendMessage("Waiting for Admin Approval...", 'system');
            startPolling();
        } else {
            appendMessage(data.ai_response || "Processed successfully.", 'assistant');
            setInputState(false);
            fetchDatabase(); // Refresh DB after successful action
        }
    } catch (error) {
        console.error('Chat error:', error);
        appendMessage("Error communicating with the server.", 'system');
        setInputState(false);
    }
});

// ==========================================
// POLLING LOGIC
// ==========================================
function startPolling() {
    if (isPolling) return;
    isPolling = true;
    checkPendingAdmin(); // Trigger immediate check
    pollingIntervalId = setInterval(pollStatus, POLL_INTERVAL_MS);
}

function stopPolling() {
    isPolling = false;
    if (pollingIntervalId) {
        clearInterval(pollingIntervalId);
        pollingIntervalId = null;
    }
}

async function pollStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/chat/status/${SESSION_ID}`);
        if (!response.ok) return;
        const data = await response.json();

        if (data.status === 'success') {
            stopPolling();
            removeWaitingMessage();
            appendMessage(data.ai_response || "Task completed.", 'assistant');
            setInputState(false);
            fetchDatabase(); // Refresh DB when task completes
        } else if (data.status === 'paused') {
            // Still paused, fetch details if modal is not open
            if (adminModal.classList.contains('hidden')) {
                checkPendingAdmin();
            }
        }
    } catch (error) {
        console.error('Polling error:', error);
    }
}

// ==========================================
// ADMIN OVERRIDE LOGIC
// ==========================================
async function checkPendingAdmin() {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/pending`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ admin_id: "kaaifahmed", admin_pwd: "kaaifahmed123" })
        });
        
        const data = await response.json();
        const pendingData = data.pending_approvals || {};
        const toolsList = pendingData[SESSION_ID];

        if (toolsList && toolsList.length > 0) {
            currentPendingTools = toolsList;
            showAdminModal(toolsList);
        }
    } catch (error) {
        console.error('Error fetching admin pending:', error);
    }
}

function showAdminModal(tools) {
    adminPendingDetails.textContent = JSON.stringify(tools, null, 2);
    adminModal.classList.remove('hidden');
}

function hideAdminModal() {
    adminModal.classList.add('hidden');
    currentPendingTools = [];
}

async function submitAdminDecision(isApproved) {
    const approvals = {};
    currentPendingTools.forEach((tool, index) => {
        const toolId = tool.id || `tool_${index}`;
        approvals[toolId] = isApproved;
    });

    try {
        const response = await fetch(`${API_BASE_URL}/admin/resolve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                admin_id: "kaaifahmed",
                admin_pwd: "kaaifahmed123",
                session_id: SESSION_ID,
                approvals: approvals
            })
        });

        if (response.ok) {
            hideAdminModal();
            // Polling will catch the success state shortly
        } else {
            console.error("Failed to submit decision");
        }
    } catch (error) {
        console.error('Error submitting decision:', error);
    }
}

modalApproveBtn.addEventListener('click', () => submitAdminDecision(true));
modalDenyBtn.addEventListener('click', () => submitAdminDecision(false));
