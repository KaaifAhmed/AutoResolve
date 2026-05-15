from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from app import app as langchain_app

api = FastAPI(title="AutoResolve Backend")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], # Allows GET, POST, etc.
    allow_headers=["*"], # Allows all headers
)

class ChatRequest(BaseModel):
    session_id: str
    message: str

class AdminApprovalRequest(BaseModel):
    admin_id: str
    admin_pwd: str
    session_id: str
    approvals: dict

class PendingApprovalRequest(BaseModel):
    admin_id: str
    admin_pwd: str

admin_ids = {"kaaifahmed": "kaaifahmed123"}
pending_approvals = {}
sensitive_tools = ["refund_order", "cancel_order"]

@api.post("/chat")
async def chat_endpoint (request: ChatRequest):
    config = {"configurable": {"thread_id": request.session_id}}
    init_state = {"messages": [HumanMessage(request.message)]}
    final = langchain_app.invoke(init_state, config=config)

    state = langchain_app.get_state(config)

    content = final["messages"][-1].content
    
    # If the model returned a list of blocks (like Gemma/Gemini Pro)
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                content = block['text']

    if (state.next == ('sensitive_tool_executor',)):
        pending_actions = [tool for tool in state.values["messages"][-1].tool_calls if tool['name'] in sensitive_tools]
        pending_approvals[request.session_id] = pending_actions
        return {
            "status": "paused",
        }
    
    return {
        "status": "success",
        "ai_response": content
    }

@api.post("/admin/pending")
async def give_pending_approvals(request: PendingApprovalRequest):
    if (request.admin_id in admin_ids) and (request.admin_pwd == admin_ids[request.admin_id]):
        return {
            "status": "success",
            "pending_approvals": pending_approvals
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin access denied."
        )

@api.post("/admin/resolve")
async def update_approvals (request: AdminApprovalRequest):
    if (request.admin_id in admin_ids) and (request.admin_pwd == admin_ids[request.admin_id]):
        config = {"configurable": {"thread_id": request.session_id}}
        langchain_app.update_state(config, {"approvals": request.approvals})
        langchain_app.invoke(None, config=config)

        if request.session_id in pending_approvals:
            del pending_approvals[request.session_id]

        return {
            "status": "success",
            "approvals": request.approvals
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin access denied."
        )
    
@api.get("/chat/status/{session_id}")
async def get_chat_status (session_id: str):
    config = {"configurable": {"thread_id": session_id}}
    app_state = langchain_app.get_state(config=config)

    if app_state.next == ('sensitive_tool_executor',):
        return {
            "status": "paused",
        }
    else:
        content = app_state.values["messages"][-1].content
    
        # If the model returned a list of blocks (like Gemma/Gemini Pro)
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    content = block['text']

        return {
            "status": "success",
            "ai_response": content
        }