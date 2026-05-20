# # from typing import TypedDict, Annotated, NotRequired
# # from dotenv import load_dotenv
# # from pydantic import BaseModel, Field
# # from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
# # from langchain_core.prompts import ChatPromptTemplate
# # from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
# # from langgraph.graph import StateGraph, START, END
# # from langchain_core.vectorstores import InMemoryVectorStore
# # from langchain_core.documents import Document
# # from langchain_core.tools import tool
# # from langgraph.checkpoint.memory import MemorySaver
# # from operator import add

# # load_dotenv()
# # memory = MemorySaver()

# # class AgentState (TypedDict):
# #     messages: Annotated[list[BaseMessage], add] # Annotated allows us to add 'metadata' to our type-hint. Here 'add' tells langgraph that the next value is to be added instead of replaced
# #     user_intents: list[str]
# #     approvals: NotRequired[dict]

# # class RouterIntent (BaseModel):
# #     intent: list[str] = Field(description="A list containing 'take_action', 'get_information', or both depending on the user's request.")

# # # llm = ChatGoogleGenerativeAI(model="gemma-4-31b-it", temperature=0)
# # llm = ChatGoogleGenerativeAI(model="gemma-4-31b-it", temperature=0)
# # structured_supervisor = llm.with_structured_output(RouterIntent)

# # def supervisor_node (state: AgentState):
# #     user_message = state['messages'][-1].content
# #     system_prompt = """You are a routing supervisor. 
# #     If the user asks about policies, FAQs, or general info, output ['get_information'].
# #     If the user wants to check an order, refund, or do an account action, output ['take_action'].
# #     If they ask for BOTH, output ['take_action','get_information']"""

# #     prompt = ChatPromptTemplate([
# #         ("system", system_prompt),
# #         ("human", "{user_message}")
# #     ])

# #     chain = prompt | structured_supervisor
# #     result = chain.invoke({"user_message":user_message})
# #     print(f"\nThe result from supervisor: intent = {result.intent}")

# #     return {"user_intents": result.intent}

# # def route_to_worker (state: AgentState):
# #     routes = []
# #     if ("take_action" in state["user_intents"]):
# #         routes.append("action_reasoner")
# #     elif ("get_information" in state["user_intents"]):
# #         routes.append("knowledge_agent")
# #     return routes
    

# # mock_db = {
# #     '#12345':{'status':'shipped'},
# #     '#99999':{'status':'processing'}
# # }

# # # Helper Functions (Tools)
# # @tool
# # def get_order_status (order_id: str) -> str:
# #     """Use this to check the shipping status of a specific order. Order ID format #XXXXXX"""
    
# #     if (order_id in mock_db):
# #         return f"Order {order_id} is currently {mock_db[order_id]['status']}."
# #     else:
# #         return f"Order {order_id} not found in the database."

# # @tool
# # def cancel_order (order_id: str) -> str:
# #     """Use this to cancel an order. Only orders with status 'processing' can be canceled. Order ID format #XXXXXX"""
    
# #     if (order_id in mock_db):
# #         if (mock_db[order_id]['status'] == 'processing'):
# #             mock_db[order_id]['status'] = 'cancelled'
# #             return f"Successfully canceled order {order_id}."
# #         else:
# #             return f"Failed to cancel. Order {order_id} is already {mock_db[order_id]['status']}."
# #     else: 
# #         return f"Order {order_id} not found in the database."

# # @tool
# # def refund_order (order_id: str) -> str:
# #     """Use this to refund the order. Only orders with status 'shipped' can be refunded. Order ID format #XXXXXX"""

# #     if (order_id in mock_db):
# #         if (mock_db[order_id]['status'] == 'shipped'):
# #             mock_db[order_id]['status'] = 'refunded'
# #             return f"Order {order_id} refunded successfully!"
# #         else: 
# #             return f"Order {order_id} is currently {mock_db[order_id]['status']}."
# #     else:
# #         return f"Order {order_id} not found."

# # tools = [get_order_status, cancel_order, refund_order]
# # sensitive_tools = ["refund_order", "cancel_order"]
# # tools_map = {tool.name:tool for tool in tools}

# # action_llm = llm.bind_tools(tools)

# # def action_reasoner (state: AgentState):
# #     current_messages = state["messages"]
# #     response = action_llm.invoke(current_messages)
# #     return {"messages": [response]}
    
# # def tool_executor (state: AgentState):
# #     current_messages = state["messages"]
# #     response = current_messages[-1]
# #     tool_outputs = []

# #     approvals = state.get("approvals", {})
# #     print(f"Approvals inside executor: {approvals}")
    
# #     for tool_call in response.tool_calls:
# #         tool_name = tool_call["name"]
# #         tool_args = tool_call["args"]
# #         tool_id = tool_call["id"]

# #         if tool_name in sensitive_tools and approvals.get(tool_id) is False:
# #             tool_msg = "Error: Human Administrator DENIED this tool use."
# #         else:
# #             print(f"Tool {tool_name} was executed with args {tool_args}.")

# #             if (tool_name in tools_map):
# #                 tool_msg = f"{tools_map[tool_name].invoke(tool_args)}"
# #             else: 
# #                 tool_msg = f"No '{tool_name}' named tool available!"

# #         tool_outputs.append(ToolMessage(
# #             content=tool_msg,
# #             tool_call_id=tool_id,
# #             name=tool_name
# #         ))

# #     return {'messages': tool_outputs}

# # def tool_router (state: AgentState):
# #     last_message = state["messages"][-1]
    
# #     if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
# #         return END
    
# #     for tool_call in last_message.tool_calls:
# #         if tool_call["name"] in sensitive_tools:
# #             return "sensitive_tool_executor"
        
# #     return "safe_tool_executor"


# # # Setting up the RAG and knowledge agent

# # embedding = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
# # vector_store = InMemoryVectorStore(embedding)

# # mock_docs = [
# #     Document(page_content="Return Policy: Items can be returned within 30 days for a full refund. Custom items are non-refundable."),
# #     Document(page_content="Shipping: Standard shipping takes 3-5 business days. Expedited takes 1-2 days."),
# #     Document(page_content="Support Hours: We are available Monday to Friday, 9 AM to 5 PM EST.")
# # ]
# # vector_store.add_documents(mock_docs)

# # def knowledge_agent (state: AgentState):
# #     user_request = state["messages"][-1].content
# #     similar_docs = vector_store.similarity_search(user_request, k=2)
# #     context = "\n".join([doc.page_content for doc in similar_docs])
    
# #     system_prompt = """You are a helpful customer support agent. 
# #     Respond to the user query strictly using the following context.
# #     Context: 
# #     {context}
# #     """
# #     prompt = ChatPromptTemplate([("system", system_prompt), ("human", user_request)])
    
# #     chain = prompt | llm
# #     response = chain.invoke({"context": context})

# #     return {"messages": [response]}

# # workflow = StateGraph(AgentState)

# # workflow.add_node("supervisor", supervisor_node)
# # workflow.add_node("knowledge_agent", knowledge_agent)
# # workflow.add_node("action_reasoner", action_reasoner)

# # workflow.add_node("safe_tool_executor", tool_executor)
# # workflow.add_node("sensitive_tool_executor", tool_executor)

# # workflow.add_edge(START, "supervisor")
# # workflow.add_conditional_edges(source="supervisor",path=route_to_worker)
# # workflow.add_edge("knowledge_agent", END)

# # workflow.add_conditional_edges("action_reasoner", tool_router)
# # workflow.add_edge("safe_tool_executor", "action_reasoner")
# # workflow.add_edge("sensitive_tool_executor", "action_reasoner")


# # app = workflow.compile(checkpointer=memory, interrupt_before=["sensitive_tool_executor"])

# # config = {"configurable": {"thread_id": "user_123"}}

# # print("\n--- TEST ---")
# # test_1_state = {"messages": [HumanMessage(content="Can you please tell me your refund policies, and tell me the status of my order #99999 as well?")]}
# # final = app.invoke(test_1_state, config=config)

# # state = app.get_state(config)

# # if state.next == ('sensitive_tool_executor',):
# #     pending_actions = [tool for tool in state.values["messages"][-1].tool_calls if tool['name'] in sensitive_tools]
# #     approval_dict = {}
    
# #     for pend_act in pending_actions:
# #         print(f"Need approval for: {pend_act}")
# #         approval = input("Type 'approve' or 'deny': ")

# #         approval_dict[pend_act["id"]] = (approval.lower() == 'approve')

# #     app.update_state(config, {"approvals":approval_dict})
# #     final = app.invoke(None, config=config)

# # print(f"User:\t{test_1_state["messages"][-1].content}")
# # print(f"AI 1:\t{final["messages"][-1].content}")
# # print(f"AI 2:\t{final["messages"][-2].content}")








# # from fastapi import FastAPI, HTTPException
# # from pydantic import BaseModel
# # from langchain_core.messages import HumanMessage

# # # Import your compiled LangGraph app from your existing file!
# # # (Assuming your graph variable is named 'app' inside app.py)
# # from app import app as langgraph_app 

# # # 1. Initialize the FastAPI Web Server
# # api = FastAPI(title="AutoResolve AI Backend")

# # # 2. Define the Data Models (What the frontend is allowed to send us)
# # class ChatRequest(BaseModel):
# #     session_id: str
# #     message: str

# # class AdminApprovalRequest(BaseModel):
# #     session_id: str
# #     approvals: dict  # Example: {"tool_call_id_123": True}

# # # 3. Create the Waiter (Endpoint) for User Chats
# # @api.post("/chat")
# # async def chat_endpoint(request: ChatRequest):
# #     # Setup the memory configuration using the frontend's session_id
# #     config = {"configurable": {"thread_id": request.session_id}}
    
# #     # Format the user's message
# #     input_state = {"messages": [HumanMessage(content=request.message)]}
    
# #     # Send it to the Kitchen (LangGraph)
# #     final_state = langgraph_app.invoke(input_state, config=config)
    
# #     # Check if the graph paused for Human-in-the-Loop!
# #     current_state = langgraph_app.get_state(config)
# #     if current_state.next == ('tool_executor',):
# #         return {
# #             "status": "paused",
# #             "message": "Action requires administrator approval.",
# #             # Send the pending tools to the frontend so the Admin Dashboard can see them
# #             "pending_tools": current_state.values["messages"][-1].tool_calls 
# #         }
    
# #     # If it didn't pause, just return the AI's final text
# #     return {
# #         "status": "success",
# #         "ai_response": final_state["messages"][-1].content
# #     }

# # # 4. Create the Waiter (Endpoint) for the Admin Dashboard
# # @api.post("/admin/resolve")
# # async def resolve_endpoint(request: AdminApprovalRequest):
# #     config = {"configurable": {"thread_id": request.session_id}}
    
# #     # Make sure the graph is actually paused before we try to resume it
# #     current_state = langgraph_app.get_state(config)
# #     if current_state.next != ('tool_executor',):
# #         raise HTTPException(status_code=400, detail="No actions are currently pending approval for this session.")
    
# #     # Inject the frontend's approvals dictionary into the State
# #     langgraph_app.update_state(config, {"approvals": request.approvals})
    
# #     # Resume the graph (Invoke with None)
# #     final_state = langgraph_app.invoke(None, config=config)
    
# #     return {
# #         "status": "success",
# #         "ai_response": final_state["messages"][-1].content
# #     }

# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# from langchain_core.messages import HumanMessage

# from app import app as langchain_app

# api = FastAPI(title="AutoResolve Backend")

# class ChatRequest(BaseModel):
#     session_id: str
#     message: str

# class AdminApprovalRequest(BaseModel):
#     session_id: str
#     approvals: dict

# @api.post("/chat")
# async def chat_endpoint(request: ChatRequest):
#     config = {"configurable": {"thread_id": request.session_id}}
#     init_state = {"messages": [HumanMessage(content=request.message)]}
    
#     # Send to LangGraph
#     final_state = langchain_app.invoke(init_state, config=config)

#     # Check if the graph paused using the APP object, not the returned dictionary
#     state = langchain_app.get_state(config)

#     # If it paused at our sensitive executor, return the pending tools to the frontend
#     if state.next == ('tool_executor',): # Update this name if your node is still named sensitive_tool_executor
#         pending_tools = state.values["messages"][-1].tool_calls
#         return {
#             "status": "paused",
#             "message": "Action requires administrator approval.",
#             "pending_tools": pending_tools
#         }
    
#     # Helper to pull just the text if the model returned a list of thought blocks
#     content = final_state["messages"][-1].content
#     if isinstance(content, list):
#         ai_text = next((block["text"] for block in content if isinstance(block, dict) and block.get("type") == "text"), str(content))
#     else:
#         ai_text = content

#     return {
#         "status": "success",
#         "ai_response": ai_text
#     }

# # The endpoint where the Frontend sends the Admin's answers
# @api.post("/admin/resolve")
# async def resolve_endpoint(request: AdminApprovalRequest):
#     config = {"configurable": {"thread_id": request.session_id}}
    
#     # Inject the approvals dictionary
#     langchain_app.update_state(config, {"approvals": request.approvals})
    
#     # Resume the graph
#     final_state = langchain_app.invoke(None, config=config)
    
#     content = final_state["messages"][-1].content
#     if isinstance(content, list):
#         ai_text = next((block["text"] for block in content if isinstance(block, dict) and block.get("type") == "text"), str(content))
#     else:
#         ai_text = content

#     return {
#         "status": "success",
#         "ai_response": ai_text
#     }