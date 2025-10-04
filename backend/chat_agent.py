from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage
import os

class ChatState(TypedDict):
    messages: list
    user_input: str
    response: str

def chat_node(state: ChatState):
    """Main chat node that processes user input with LLM"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Debug: Print API key status (first few characters only for security)
    if api_key:
        print(f"API Key found: {api_key[:10]}...")
    else:
        print("No API key found in environment")
    
    # Check if API key is available and valid
    if not api_key:
        # Fallback mock response for demo purposes
        user_input = state["user_input"].lower()
        
        # Simple rule-based responses for demo
        if "hello" in user_input or "hi" in user_input:
            mock_response = "Hello! I'm a demo AI assistant. To use the full OpenAI integration, please set your OPENAI_API_KEY environment variable."
        elif "how are you" in user_input:
            mock_response = "I'm doing well, thank you! I'm currently running in demo mode. Set your OpenAI API key to unlock full AI capabilities."
        elif "help" in user_input:
            mock_response = "I can help you test this LangGraph chat application! To get real AI responses, you'll need to:\n1. Get an OpenAI API key from https://platform.openai.com/\n2. Set it as an environment variable: export OPENAI_API_KEY='your-key'"
        elif "weather" in user_input:
            mock_response = "I'd love to help with weather information! In demo mode, I can't access real weather data, but with a proper OpenAI API key, I could help you with that and much more."
        elif "time" in user_input:
            import datetime
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            mock_response = f"The current time is {current_time}. This is a demo response - with OpenAI integration, I could provide much more detailed assistance!"
        else:
            mock_response = f"You said: '{state['user_input']}'. I'm currently in demo mode - set your OPENAI_API_KEY to get real AI responses powered by GPT-3.5!"
        
        return {
            "messages": state.get("messages", []) + [
                {"role": "user", "content": state["user_input"]},
                {"role": "assistant", "content": mock_response}
            ],
            "response": mock_response
        }
    
    try:
        # Initialize OpenAI LLM with real API key
        print("I reached here Sid")
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            api_key=api_key
        )
        print("Am I here Sid1")
        # Convert messages to LangChain format
        messages = []
        for msg in state.get("messages", []):
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        print("Am I here Sid2")

        # Add current user input
        messages.append(HumanMessage(content=state["user_input"]))
        print("Am I here Sid3")

        # Get LLM response
        response = llm.invoke(messages)
        print("Am I here Sid4")

        return {
            "messages": state.get("messages", []) + [
                {"role": "user", "content": state["user_input"]},
                {"role": "assistant", "content": response.content}
            ],
            "response": response.content
        }
    except Exception as e:
        error_msg = f"OpenAI API Error: {str(e)}. Please check your API key and try again."
        return {
            "messages": state.get("messages", []) + [
                {"role": "user", "content": state["user_input"]},
                {"role": "assistant", "content": error_msg}
            ],
            "response": error_msg
        }

# Create the graph
def create_chat_graph():
    workflow = StateGraph(ChatState)
    workflow.add_node("chat", chat_node)
    workflow.set_entry_point("chat")
    workflow.add_edge("chat", END)
    return workflow.compile()

# Global graph instance
chat_graph = create_chat_graph()