# LangGraph Chat App

A single-page web application with LangGraph-powered chat integration and FastAPI backend.

## Features

- 🤖 AI chat powered by LangGraph and OpenAI
- ⚡ FastAPI backend with async support
- 🎨 Modern, responsive UI
- 💬 Real-time conversation history
- 🔄 Error handling and status updates

## Setup

### Prerequisites

- Python 3.8+
- OpenAI API key

### Installation

1. **Install Python dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key-here"
   ```

3. **Start the backend server:**
   ```bash
   cd backend
   python main.py
   ```
   The API will be available at `http://localhost:8000`

4. **Open the frontend:**
   Open `frontend/index.html` in your browser, or serve it with a simple HTTP server:
   ```bash
   cd frontend
   python -m http.server 3000
   ```
   Then visit `http://localhost:3000`

## API Endpoints

- `GET /` - API status
- `POST /chat` - Send chat message
- `GET /health` - Health check

## Project Structure

```
langgraph-chat-app/
├── backend/
│   ├── main.py          # FastAPI server
│   ├── chat_agent.py    # LangGraph chat agent
│   └── requirements.txt # Dependencies
├── frontend/
│   ├── index.html       # Single page app
│   ├── style.css        # Styling
│   └── script.js        # Frontend logic
└── README.md
```

## Usage

1. Start the backend server
2. Open the frontend in your browser
3. Start chatting with the AI assistant!

The app maintains conversation history and provides a smooth chat experience with typing indicators and error handling.