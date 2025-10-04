class ChatApp {
    constructor() {
        this.conversationHistory = [];
        this.apiUrl = 'http://localhost:8000';
        this.messageCount = 0;
        this.initializeElements();
        this.attachEventListeners();
        this.updateStats();
    }

    initializeElements() {
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.chatMessages = document.getElementById('chat-messages');
        this.status = document.getElementById('status');
        this.clearButton = document.getElementById('clear-chat');
        this.messageCountEl = document.getElementById('message-count');
    }

    attachEventListeners() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.clearButton.addEventListener('click', () => this.clearChat());
        
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });

        // Auto-resize input
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
        });
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        // Disable input while processing
        this.setInputState(false);
        this.showStatus('AI is thinking...', 'typing');

        // Add user message to chat
        this.addMessage(message, 'user');
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';

        const startTime = Date.now();

        try {
            const response = await fetch(`${this.apiUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    conversation_history: this.conversationHistory
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const responseTime = Date.now() - startTime;
            
            // Add bot response to chat
            this.addMessage(data.response, 'bot');
            
            // Update conversation history
            this.conversationHistory = data.conversation_history;
            
            // Update stats
            this.messageCount += 2; // user + bot message
            this.updateStats();
            this.updateResponseTime(responseTime);
            
            this.clearStatus();
        } catch (error) {
            console.error('Error:', error);
            this.addMessage('Sorry, I encountered an error. Please check if the backend server is running and try again.', 'bot');
            this.showStatus('Connection error - Check backend server', 'error');
        } finally {
            this.setInputState(true);
        }
    }

    addMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        
        if (sender === 'user') {
            avatar.innerHTML = '<i class="fas fa-user"></i>';
        } else {
            avatar.innerHTML = '<i class="fas fa-robot"></i>';
        }
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = content;
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        this.chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    clearChat() {
        // Keep only the initial bot message
        const initialMessage = this.chatMessages.querySelector('.message.bot-message');
        this.chatMessages.innerHTML = '';
        if (initialMessage) {
            this.chatMessages.appendChild(initialMessage.cloneNode(true));
        }
        
        this.conversationHistory = [];
        this.clearStatus();
        this.messageInput.focus();
    }

    setInputState(enabled) {
        this.messageInput.disabled = !enabled;
        this.sendButton.disabled = !enabled;
        if (enabled) {
            this.messageInput.focus();
        }
    }

    showStatus(message, type = '') {
        this.status.textContent = message;
        this.status.className = `status ${type}`;
    }

    clearStatus() {
        this.status.textContent = '';
        this.status.className = 'status';
    }

    updateStats() {
        if (this.messageCountEl) {
            this.messageCountEl.textContent = this.messageCount;
        }
    }

    updateResponseTime(responseTime) {
        const avgResponseEl = document.getElementById('avg-response');
        if (avgResponseEl) {
            const seconds = (responseTime / 1000).toFixed(1);
            avgResponseEl.textContent = `~${seconds}s`;
        }
    }

    // Add some interactivity to nav items
    initializeNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Remove active class from all items
                navItems.forEach(nav => nav.classList.remove('active'));
                
                // Add active class to clicked item
                item.classList.add('active');
                
                // Switch views based on the clicked nav item
                const text = item.querySelector('span').textContent;
                if (text === 'Dashboard') {
                    this.showDashboard();
                } else if (text === 'Analytics') {
                    this.showAnalytics();
                } else if (text === 'Settings') {
                    this.showSettings();
                }
            });
        });
    }

    showDashboard() {
        document.getElementById('dashboard-view').style.display = 'block';
        document.getElementById('analytics-view').style.display = 'none';
    }

    showAnalytics() {
        document.getElementById('dashboard-view').style.display = 'none';
        document.getElementById('analytics-view').style.display = 'block';
        
        // Load analytics data and render charts
        this.loadAnalyticsData();
    }

    showSettings() {
        // Placeholder for settings functionality
        this.addMessage('Settings panel would open here. This is a demo feature.', 'bot');
    }

    async loadAnalyticsData() {
        try {
            const response = await fetch(`${this.apiUrl}/analytics-data`);
            const data = await response.json();
            
            // Update KPIs
            document.getElementById('kpi-conversations').textContent = data.kpis.total_conversations;
            document.getElementById('kpi-response-time').textContent = data.kpis.avg_response_time;
            document.getElementById('kpi-satisfaction').textContent = data.kpis.user_satisfaction;
            document.getElementById('kpi-success-rate').textContent = data.kpis.success_rate;
            
            // Render charts
            this.renderCharts(data);
        } catch (error) {
            console.error('Error loading analytics data:', error);
        }
    }

    renderCharts(data) {
        // Chat Volume Chart
        const chatVolumeCtx = document.getElementById('chat-volume-chart').getContext('2d');
        new Chart(chatVolumeCtx, {
            type: 'line',
            data: {
                labels: data.chat_volume.dates,
                datasets: [{
                    label: 'Daily Conversations',
                    data: data.chat_volume.values,
                    borderColor: '#4299e1',
                    backgroundColor: 'rgba(66, 153, 225, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Response Time Chart
        const responseTimeCtx = document.getElementById('response-time-chart').getContext('2d');
        new Chart(responseTimeCtx, {
            type: 'line',
            data: {
                labels: data.response_times.dates,
                datasets: [{
                    label: 'Response Time (s)',
                    data: data.response_times.values,
                    borderColor: '#48bb78',
                    backgroundColor: 'rgba(72, 187, 120, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Topics Distribution Chart
        const topicsCtx = document.getElementById('topics-chart').getContext('2d');
        new Chart(topicsCtx, {
            type: 'doughnut',
            data: {
                labels: data.topics.labels,
                datasets: [{
                    data: data.topics.values,
                    backgroundColor: [
                        '#4299e1',
                        '#48bb78',
                        '#ed8936',
                        '#9f7aea',
                        '#f56565'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        // Hourly Usage Chart
        const hourlyUsageCtx = document.getElementById('hourly-usage-chart').getContext('2d');
        new Chart(hourlyUsageCtx, {
            type: 'bar',
            data: {
                labels: data.hourly_usage.hours.map(h => `${h}:00`),
                datasets: [{
                    label: 'Conversations',
                    data: data.hourly_usage.values,
                    backgroundColor: '#4299e1',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
}

// Initialize the chat app when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const app = new ChatApp();
    app.initializeNavigation();
    
    // Focus on input when page loads
    setTimeout(() => {
        document.getElementById('message-input').focus();
    }, 100);
});