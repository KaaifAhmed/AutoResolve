// ==========================================
// CONFIGURATION
// ==========================================
const API_BASE_URL = 'http://127.0.0.1:8000';
const SESSION_ID = 'user_123';
const POLL_INTERVAL_MS = 3000;

// ==========================================
// DOM ELEMENTS
// ==========================================
const chatPage = document.getElementById('chat-page');
const adminPage = document.getElementById('admin-page');

// ==========================================
// CHAT INTERFACE LOGIC (index.html)
// ==========================================
if (chatPage) {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendButton = document.getElementById('send-button');

    let isPolling = false;

    // Helper: Appends a message bubble to the chat
    function appendMessage(content, role) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;
        
        // Special styling for the waiting animation
        if (role === 'system' && content.includes('Waiting')) {
            msgDiv.innerHTML = `<span class="loading-dots">${content}</span>`;
            msgDiv.id = 'waiting-message'; 
        } else {
            msgDiv.textContent = content;
        }
        
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Auto-scroll to bottom
    }

    // Helper: Removes the waiting animation message
    function removeWaitingMessage() {
        const waitingMsg = document.getElementById('waiting-message');
        if (waitingMsg) {
            waitingMsg.remove();
        }
    }

    // Polling logic: Checks the status endpoint every 3 seconds
    async function pollStatus() {
        if (!isPolling) return;

        try {
            const response = await fetch(`${API_BASE_URL}/chat/status/${SESSION_ID}`);
            const data = await response.json();

            if (data.status === 'success') {
                // Agent has finished execution!
                isPolling = false;
                removeWaitingMessage();
                
                // Display the final response
                const reply = data.ai_response || "Task completed successfully.";
                appendMessage(reply, 'assistant');
                
                // Re-enable user input
                chatInput.disabled = false;
                sendButton.disabled = false;
                chatInput.focus();
            } else if (data.status === 'paused') {
                // Agent is still waiting for admin approval, keep polling
                setTimeout(pollStatus, POLL_INTERVAL_MS);
            }
        } catch (error) {
            console.error('Error polling status:', error);
            // On network error, we silently retry to keep it robust
            setTimeout(pollStatus, POLL_INTERVAL_MS);
        }
    }

    // Main Submit Handler for User Chat
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const message = chatInput.value.trim();
        if (!message) return;

        // Display user message immediately
        appendMessage(message, 'user');
        chatInput.value = '';
        
        // Lock UI while processing
        chatInput.disabled = true;
        sendButton.disabled = true;

        try {
            // Send request to FastAPI
            const response = await fetch(`${API_BASE_URL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: SESSION_ID, message: message })
            });
            
            const data = await response.json();

            if (data.status === 'paused') {
                if (data.ai_response) {
                    appendMessage(data.ai_response, 'assistant');
                }
                // Agent hit a tool call and needs approval
                appendMessage("Waiting for Admin Approval...", 'system');
                isPolling = true;
                setTimeout(pollStatus, POLL_INTERVAL_MS);
            } else {
                // Agent resolved the query immediately without pausing
                const reply = data.ai_response || "Processed successfully.";
                appendMessage(reply, 'assistant');
                
                // Unlock UI
                chatInput.disabled = false;
                sendButton.disabled = false;
                chatInput.focus();
            }
        } catch (error) {
            console.error('Error sending message:', error);
            appendMessage("Error communicating with the server.", 'system');
            chatInput.disabled = false;
            sendButton.disabled = false;
        }
    });
}

// ==========================================
// ADMIN DASHBOARD LOGIC (admin.html)
// ==========================================
if (adminPage) {
    const container = document.getElementById('pending-sessions-container');

    // Fetch and render pending sessions from the backend
    async function loadPendingSessions() {
        try {
            const response = await fetch(`${API_BASE_URL}/admin/pending`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ admin_id: "kaaifahmed", admin_pwd: "kaaifahmed123" })
            });
            const data = await response.json();
            
            container.innerHTML = ''; // Clear loading state
            
            // Normalize backend data format. 
            const pendingData = data.pending_approvals || {};
            const sessions = Object.entries(pendingData).map(([id, toolsList]) => ({ session_id: id, tools: toolsList }));
            
            if (sessions.length === 0) {
                container.innerHTML = '<div class="message system">No pending requests at this time.</div>';
                return;
            }

            // Render a card for each pending session
            sessions.forEach(session => renderSessionCard(session));

        } catch (error) {
            console.error('Error fetching pending sessions:', error);
            container.innerHTML = '<div class="message system" style="color: var(--danger-color)">Error loading data. Check server connection.</div>';
        }
    }

    // Builds the HTML Card for a session and its tools
    function renderSessionCard(session) {
        const sessionId = session.session_id || session.id;
        const toolCalls = session.tools || session.tool_calls || [];
        
        const card = document.createElement('div');
        card.className = 'card';
        card.id = `card-${sessionId}`;
        
        let html = `
            <h2>Session: ${sessionId}</h2>
            <p class="text-muted">The following tools require approval.</p>
        `;

        if (toolCalls.length === 0) {
            html += `<p>No specific tools listed.</p>`;
        } else {
            // Loop through tools and generate UI for Approve/Deny
            toolCalls.forEach((tool, index) => {
                const toolId = tool.id || `tool_${index}`;
                const toolName = tool.name || tool.function?.name || 'Unknown Tool';
                const toolArgs = tool.args || tool.function?.arguments || {};
                
                // Pretty-print JSON arguments if it's an object
                const argsString = typeof toolArgs === 'string' 
                    ? toolArgs 
                    : JSON.stringify(toolArgs, null, 2);
                
                html += `
                    <div class="tool-call">
                        <div class="tool-header">
                            <span class="tool-name">${toolName}</span>
                            <span class="text-muted">ID: ${toolId}</span>
                        </div>
                        <div class="tool-args">${argsString}</div>
                        <div class="approval-actions">
                            <label class="radio-group">
                                <input type="radio" name="${sessionId}-${toolId}" value="approve" checked> Approve
                            </label>
                            <label class="radio-group">
                                <input type="radio" name="${sessionId}-${toolId}" value="deny"> Deny
                            </label>
                        </div>
                    </div>
                `;
            });
        }

        html += `
            <div class="admin-actions">
                <button class="btn-success submit-approval-btn" data-session="${sessionId}">Submit Decisions</button>
            </div>
        `;

        card.innerHTML = html;
        container.appendChild(card);

        // Bind submit button
        const submitBtn = card.querySelector('.submit-approval-btn');
        submitBtn.addEventListener('click', () => submitApprovals(sessionId, toolCalls));
    }

    // Gathers decisions and sends them to the backend
    async function submitApprovals(sessionId, toolCalls) {
        const approvals = {};
        
        // Extract boolean values from radio buttons
        toolCalls.forEach((tool, index) => {
            const toolId = tool.id || `tool_${index}`;
            const radios = document.getElementsByName(`${sessionId}-${toolId}`);
            for (let radio of radios) {
                if (radio.checked) {
                    approvals[toolId] = radio.value === 'approve'; // true or false
                    break;
                }
            }
        });

        try {
            // Send the decisions back to FastAPI
            const response = await fetch(`${API_BASE_URL}/admin/resolve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    admin_id: "kaaifahmed",
                    admin_pwd: "kaaifahmed123",
                    session_id: sessionId, 
                    approvals: approvals 
                })
            });

            if (response.ok) {
                // Success: remove the card and show a small success message
                const card = document.getElementById(`card-${sessionId}`);
                if (card) {
                    card.innerHTML = `<div class="message system" style="color: var(--success-color)">Decisions submitted successfully.</div>`;
                    setTimeout(() => card.remove(), 2000);
                }
            } else {
                alert("Failed to submit approvals. Server returned an error.");
            }
        } catch (error) {
            console.error("Error submitting approvals:", error);
            alert("Error communicating with the server.");
        }
    }

    // Initialize the dashboard on load
    loadPendingSessions();
}
