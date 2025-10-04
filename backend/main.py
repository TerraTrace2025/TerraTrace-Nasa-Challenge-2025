from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from chat_agent import chat_graph
import os

app = FastAPI(title="LangGraph Chat App")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# Serve the main HTML file at root
from fastapi.responses import FileResponse

@app.get("/app")
async def serve_frontend():
    return FileResponse("../frontend/index.html")

@app.get("/analytics-data")
async def get_analytics_data():
    """Provide analytics data for the frontend"""
    import random
    from datetime import datetime, timedelta
    
    # Generate dummy analytics data
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30, 0, -1)]
    
    return {
        "chat_volume": {
            "dates": dates,
            "values": [random.randint(10, 100) for _ in range(30)]
        },
        "response_times": {
            "dates": dates,
            "values": [round(random.uniform(0.5, 3.0), 2) for _ in range(30)]
        },
        "topics": {
            "labels": ["Technical Support", "General Questions", "Product Info", "Troubleshooting", "Feature Requests"],
            "values": [random.randint(50, 200) for _ in range(5)]
        },
        "hourly_usage": {
            "hours": list(range(24)),
            "values": [random.randint(5, 50) if 9 <= h <= 17 else random.randint(1, 15) for h in range(24)]
        },
        "kpis": {
            "total_conversations": 2847,
            "avg_response_time": "1.8s",
            "user_satisfaction": "4.7/5",
            "success_rate": "94.2%"
        }
    }

class ChatRequest(BaseModel):
    message: str
    conversation_history: list = []

class ChatResponse(BaseModel):
    response: str
    conversation_history: list

@app.get("/")
async def root():
    return FileResponse("../frontend/index.html")

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Prepare state for LangGraph
        state = {
            "user_input": request.message,
            "messages": request.conversation_history
        }
        
        # Run the chat graph
        result = chat_graph.invoke(state)
        
        return ChatResponse(
            response=result["response"],
            conversation_history=result["messages"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)