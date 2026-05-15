from typing import TypedDict, Annotated, NotRequired
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langgraph.graph import StateGraph, START, END
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from operator import add

load_dotenv()
memory = MemorySaver()

class AgentState (TypedDict):
    messages: Annotated[list[BaseMessage], add] # Annotated allows us to add 'metadata' to our type-hint. Here 'add' tells langgraph that the next value is to be added instead of replaced
    approvals: NotRequired[dict]

llm = ChatGoogleGenerativeAI(model="gemma-4-31b-it", temperature=0)

mock_db = {
    '#12345':{'status':'shipped'},
    '#99999':{'status':'processing'}
}


# Tools

@tool
def get_order_status (order_id: str) -> str:
    """Use this to check the shipping status of a specific order. Order ID format #XXXXX"""
    
    if (order_id in mock_db):
        return f"Order {order_id} is currently {mock_db[order_id]['status']}."
    else:
        return f"Order {order_id} not found in the database."

@tool
def cancel_order (order_id: str) -> str:
    """Use this to cancel an order. Only orders with status 'processing' can be canceled. Order ID format #XXXXX"""
    
    if (order_id in mock_db):
        if (mock_db[order_id]['status'] == 'processing'):
            mock_db[order_id]['status'] = 'cancelled'
            return f"Successfully canceled order {order_id}."
        else:
            return f"Failed to cancel. Order {order_id} is already {mock_db[order_id]['status']}."
    else: 
        return f"Order {order_id} not found in the database."

@tool
def refund_order (order_id: str) -> str:
    """Use this to refund the order. Only orders with status 'shipped' can be refunded. Order ID format #XXXXX"""

    if (order_id in mock_db):
        if (mock_db[order_id]['status'] == 'shipped'):
            mock_db[order_id]['status'] = 'refunded'
            return f"Order {order_id} refunded successfully!"
        else: 
            return f"Order {order_id} is currently {mock_db[order_id]['status']}."
    else:
        return f"Order {order_id} not found."

embedding = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
vector_store = InMemoryVectorStore(embedding)

mock_docs = [
    Document(page_content="Return Policy: Items can be returned within 30 days for a full refund. Custom items are non-refundable."),
    Document(page_content="Shipping: Standard shipping takes 3-5 business days. Expedited takes 1-2 days."),
    Document(page_content="Support Hours: We are available Monday to Friday, 9 AM to 5 PM EST.")
]
vector_store.add_documents(mock_docs)

@tool
def search_company_info (user_request: str) -> str:
    """Use this tool to retrieve information about company policies and other info."""
    similar_docs = vector_store.similarity_search(user_request, k=2)
    info = "\n".join([doc.page_content for doc in similar_docs])
    return info

tools = [get_order_status, cancel_order, refund_order, search_company_info]
sensitive_tools = ["refund_order", "cancel_order"]
tools_map = {tool.name:tool for tool in tools}

action_llm = llm.bind_tools(tools)


# All Nodes & Conditional Edges

def assistant_node (state: AgentState):
    current_msgs = state["messages"]
    system_prompt = """You are a customer support agent. You have a list of tools available.
    Rules:
    - If the user asks about orders, refunds, cancellations, or company info, use the appropriate tool.
    - If you already received a tool result, use it to generate a final answer.
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

    approvals = state.get("approvals", {})
    
    for tool_call in response.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

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


def print_clean_ai_message(ai_message: AIMessage):
    """Extracts only the text response from an LLM, hiding its internal thoughts."""
    content = ai_message.content
    
    # If the model returned a list of blocks (like Gemma/Gemini Pro)
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                print(f"AI:\t{block['text']}")
                return
            
    # If the model returned a standard string (like standard GPT-4o or Claude)
    elif isinstance(content, str):
        print(f"AI Assistant:\n{content}")

# MAIN PROGRAM

# config = {"configurable": {"thread_id": "user_123"}}
# user_query = input("Human:\t")

# while (user_query.lower() != "quit"):

#     init_state = {"messages": [HumanMessage(content=user_query)]}
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

    # print_clean_ai_message(final["messages"][-1])
#     print(f"{'-'*100}")
#     user_query = input("Human:\t")
