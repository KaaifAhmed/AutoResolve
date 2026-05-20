from datetime import datetime
from typing import TypedDict, Annotated, NotRequired
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langgraph.graph import StateGraph, START, END
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain_core.tools import tool, InjectedToolArg
from langgraph.checkpoint.memory import MemorySaver
from langchain_chroma import Chroma
from operator import add
from database import SessionLocal, Order

load_dotenv()
memory = MemorySaver()

class AgentState (TypedDict):
    messages: Annotated[list[BaseMessage], add] # Annotated allows us to add 'metadata' to our type-hint. Here 'add' tells langgraph that the next value is to be added instead of replaced
    approvals: NotRequired[dict]
    customer_id: str 

llm = ChatGoogleGenerativeAI(model="gemma-4-26b-a4b-it", temperature=0)


# Tools

@tool
def place_order(item_name: str, customer_id: Annotated[str, InjectedToolArg], price: str) -> str:
    """Use this to place a new order for the customer. Provide the item_name they want to buy, and its market price in dollars (closest guess)."""
    db = SessionLocal()
    try:
        # Find the highest existing order ID to auto-increment
        last_order = db.query(Order).filter(Order.customer_id == customer_id).order_by(Order.id.desc()).first()
        if last_order:
            last_num = int(last_order.id.replace("#", ""))
            new_id = f"#{last_num + 1}"
        else:
            new_id = "#10001"

        new_order = Order(
            id=new_id,
            customer_id=customer_id,
            status="processing",
            amount=price,
            created_at=datetime.utcnow(),
            item_summary=item_name
        )
        db.add(new_order)
        db.commit()
        return f"Successfully placed order {new_id} for '{item_name}'. The total is ${price}."
    finally:
        db.close()

@tool
def get_order_details(order_id: str, customer_id: Annotated[str, InjectedToolArg]) -> str:
    """Use this to get specific details (items, price, date) of a single order. Order ID format #XXXXX"""
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id, Order.customer_id == customer_id).first()
        if order:
            date_str = order.created_at.strftime("%Y-%m-%d")
            return f"Order {order.id}: '{order.item_summary}' costing ${order.amount:.2f}, placed on {date_str}. Status: {order.status}."
        return f"Order {order_id} not found."
    finally:
        db.close()

@tool
def get_user_orders(status_filter: str, customer_id: Annotated[str, InjectedToolArg]) -> str:
    """Use this to get a list of the user's orders. Provide a status_filter ('all', 'processing', 'shipped', 'cancelled', 'refunded')."""
    db = SessionLocal()
    try:
        query = db.query(Order).filter(Order.customer_id == customer_id)
        
        if status_filter.lower() != "all":
            query = query.filter(Order.status == status_filter.lower())
            
        orders = query.all()
        
        if not orders:
            return f"No orders found matching status '{status_filter}'."
            
        response_lines = [f"Found {len(orders)} order(s):"]
        for o in orders:
            response_lines.append(f"- {o.id}: {o.item_summary} ({o.status})")
            
        return "\n".join(response_lines)
    finally:
        db.close()

@tool
def get_order_status (order_id: str, customer_id: Annotated[str, InjectedToolArg]) -> str:
    """Use this to check the shipping status of a specific order. Order ID format #XXXXX"""
    db = SessionLocal()
    try:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.customer_id == customer_id
        ).first()
        if order:
            return f"Order {order.id} status is {order.status}."
        else:
            return f"Order {order_id} not found or unauthorized."
    finally:
        db.close()


@tool
def cancel_order (order_id: str, customer_id: Annotated[str, InjectedToolArg]) -> str:
    """Use this to cancel an order. Only orders with status 'processing' can be canceled. Order ID format #XXXXX"""
    db = SessionLocal()
    try:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.customer_id == customer_id
        ).first()
        
        if order:
            if order.status == "processing":
                order.status = "cancelled"
                db.commit()
                return f"Successfully cancelled order {order_id}."
            else:
                return f"Cannot cancel order {order_id} in status {order.status}."
        else:
            return f"Order {order_id} not found or unauthorized."
    finally:
        db.close()

@tool
def refund_order (order_id: str, customer_id: Annotated[str, InjectedToolArg]) -> str:
    """Use this to refund the order. Only orders with status 'shipped' can be refunded. Order ID format #XXXXX"""

    db = SessionLocal()
    try:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.customer_id == customer_id
        ).first()

        if order:
            if order.status == "shipped":
                order.status = "refunded"
                db.commit()
                return f"Successfully refunded order {order_id}."
            else:
                return f"Cannot refund order {order_id} in status {order.status}."

        else:
            return f"Order {order_id} not found or unauthorized."
    finally:
        db.close()


embedding = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
vector_store = Chroma(
    persist_directory='./chroma_db',
    embedding_function=embedding
)

@tool
def search_company_info (user_request: str) -> str:
    """Use this tool to retrieve information about company policies and other info."""
    similar_docs = vector_store.similarity_search(user_request, k=2)
    info = "\n".join([doc.page_content for doc in similar_docs])
    return info

tools = [get_order_status, cancel_order, refund_order, search_company_info, place_order, get_order_details, get_user_orders]
sensitive_tools = ["refund_order", "cancel_order"]
tools_map = {tool.name:tool for tool in tools}

action_llm = llm.bind_tools(tools)


# All Nodes & Conditional Edges

def assistant_node (state: AgentState):
    current_msgs = state["messages"]
    system_prompt = """You are a customer support agent. You have a list of tools available.
    Rules:
    - If the user asks about orders, refunds, cancellations, or company info, use the appropriate tool.
    - Once you have received a tool result, respond DIRECTLY to the customer. Do NOT call any more tools.
    - Be polite and helpful.
    - Do not call tools unnecessarily."""

    prompt = ChatPromptTemplate([
        ("system", system_prompt),
        MessagesPlaceholder("messages")
    ])

    chain = prompt | action_llm
    response = chain.invoke({"messages":current_msgs})
    return {"messages": [response]}
    
def tool_executor (state: AgentState):
    current_messages = state["messages"]
    response = current_messages[-1]
    tool_outputs = []

    customer_id = state["customer_id"]
    approvals = state.get("approvals", {})
    
    for tool_call in response.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        needs_customer_id = [
            "get_order_status", "cancel_order", "refund_order", "place_order", "get_order_details", "get_user_orders"
        ]
        
        if tool_name in needs_customer_id:
            tool_args["customer_id"] = customer_id

        if tool_name in sensitive_tools and approvals.get(tool_id) is False:
            tool_msg = "Error: Human Administrator DENIED this tool use."
        else:
            if (tool_name in tools_map):
                tool_msg = f"{tools_map[tool_name].invoke(tool_args)}"
            else: 
                tool_msg = f"No '{tool_name}' named tool available!"

        tool_outputs.append(ToolMessage(
            content=tool_msg,
            tool_call_id=tool_id,
            name=tool_name
        ))

    return {'messages': tool_outputs}

def tool_router (state: AgentState):
    last_message = state["messages"][-1]
    
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return END
    
    for tool_call in last_message.tool_calls:
        if tool_call["name"] in sensitive_tools:
            return "sensitive_tool_executor"
        
    return "safe_tool_executor"


# Graph Creation (Workflow)

workflow = StateGraph(AgentState)

workflow.add_node("assistant", assistant_node)
workflow.add_node("safe_tool_executor", tool_executor)
workflow.add_node("sensitive_tool_executor", tool_executor)

workflow.add_edge(START, "assistant")
workflow.add_conditional_edges(source="assistant",path=tool_router)

workflow.add_edge("safe_tool_executor", "assistant")
workflow.add_edge("sensitive_tool_executor", "assistant")

app = workflow.compile(checkpointer=memory, interrupt_before=["sensitive_tool_executor"])







# Testing Ground

# config = {"configurable": {"thread_id": "user_123"}}
# user_query = input("Human:\t")

# while (user_query.lower() != "quit"):

#     init_state = {"messages": [HumanMessage(content=user_query)], "customer_id": "cust_001"}
#     final = app.invoke(init_state, config=config)

#     state = app.get_state(config)

#     if state.next == ('sensitive_tool_executor',):
#         pending_actions = [tool for tool in state.values["messages"][-1].tool_calls if tool['name'] in sensitive_tools]
#         approval_dict = {}
        
#         for pend_act in pending_actions:
#             print(f"Need approval for: {pend_act}")
#             approval = input("Type 'approve' or 'deny': ")

#             approval_dict[pend_act["id"]] = (approval.lower() == 'approve')

#         app.update_state(config, {"approvals":approval_dict})
#         final = app.invoke(None, config=config)

#     print(final["messages"][-1].content)
#     print(f"{'-'*100}")
#     user_query = input("Human:\t")
