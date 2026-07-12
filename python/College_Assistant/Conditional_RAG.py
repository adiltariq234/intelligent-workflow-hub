import os
from typing import TypedDict, Annotated
from dotenv import load_dotenv

from langchain_groq import ChatGroq
# FIXED: Capitalized StateGraph properly
from langgraph.graph import END, START, StateGraph 
from langgraph.graph.message import add_messages

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# ============================================
# Load Environment Variables
# ============================================
load_dotenv()

# ============================================
# Embedding Model
# ============================================
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# ============================================
# Build Retriever
# ============================================
def build_retriever(pdf_path: str):
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_documents(documents)

    vectorstore = FAISS.from_documents(
        documents=chunks,
        embedding=embeddings
    )

    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 4}
    )

    return retriever

# ============================================
# Create Retrievers
# ============================================
academic_retriever = build_retriever("academics_handbook.pdf")
fee_retriever = build_retriever("fee_structure.pdf")

# ============================================
# LLM
# ============================================
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.4
)

# ============================================
# LangGraph State
# ============================================
class State(TypedDict):
    program: str
    message: Annotated[list, add_messages]
    query_type: str
    retrieved_context: str

# ============================================
# Graph Nodes
# ============================================
def classifier(state: State) -> dict:
    """Look at the Latest Path and decide which path to take"""
    last_message = state['message'][-1].content
    prompt = f"""
You are a query classifier for a university AI assistant.

Classify the following student query into exactly ONE category.

Categories:
1. academic
- Attendance, Exams, Grading, GPA/CGPA, Credits, Promotion, Semester, Courses, Degree requirements, Academic calendar, Timetable, Registration, Summer training, Internship, University policies

2. fee
- Tuition fee, Payment, Challan, Refund, Scholarship, Fine, Late fee, Financial aid, Hostel fee, Transport fee, Any money-related question

3. general
- Greetings, Thanks, Goodbye, Casual conversation, Questions unrelated to academics or fees

Student Query:
{last_message}

Return ONLY one word.

Examples:
attendance policy -> academic
fee deadline -> fee
hello -> general
"""

    response = llm.invoke(prompt)
    category = response.content.strip().lower()

    if "academic" in category:
        category = "academic"
    elif "fee" in category:
        category = "fee"
    else:
        category = "general"

    return {"query_type": category}


def academic_rag_node(state: State) -> dict:
    """Academic RAG Node"""
    query = state['message'][-1].content
    retrieved_docs = academic_retriever.invoke(query)
    retrieved_context = "\n\n".join([doc.page_content for doc in retrieved_docs])
    return {"retrieved_context": retrieved_context}


def fee_rag_node(state: State) -> dict:
    """Fee RAG Node"""
    query = state['message'][-1].content
    retrieved_docs = fee_retriever.invoke(query)
    retrieved_context = "\n\n".join([doc.page_content for doc in retrieved_docs])
    return {"retrieved_context": retrieved_context}


def general_node(state: State) -> dict:
    """General Node"""
    return {"retrieved_context": "No relevant documents found for general queries."}


def response_node(state: State) -> dict:
    """Response Node"""
    query = state['message'][-1].content
    programme = state.get('program', 'N/A')
    retrieved_context = state['retrieved_context']

    if retrieved_context == "No relevant documents found for general queries.":
        prompt = f"""You are a helpful university AI assistant. A student has asked the following question:
{query} and talking to student from {programme} program."""
    else:
        prompt = (
            f"You are an AI-powered College Assistant designed to support students enrolled in the {programme} programme.\n\n"
            f"Your responsibility is to provide accurate, clear, and helpful answers using only the official college documentation provided in the context.\n\n"
            f"Guidelines:\n"
            f"- Carefully analyze the provided context before answering.\n"
            f"- If the context includes information for multiple programmes, only return information relevant to the {programme} programme.\n"
            f"- Do not generate or assume information that is not explicitly mentioned in the context.\n"
            f"- If the required information is unavailable, politely respond with: "
            f"'I couldn't find this information in the official college documentation.'\n"
            f"- Keep responses professional, concise, and student-friendly.\n"
            f"- Format the answer using bullet points whenever appropriate.\n\n"
            f"Official College Context:\n"
            f"{retrieved_context}\n\n"
            f"Student Question:\n"
            f"{query}\n\n"
            f"Answer:"
        )
    response = llm.invoke(prompt)
    return {"message": [("ai", response.content.strip())]}


# ============================================
# Step 4 Router Function (FIXED)
# ============================================
def route_query(state: State) -> str:
    """Route the query by returning the targeted node name string"""
    query_type = state['query_type']

    if query_type == "academic":
        return "academic_rag"
    elif query_type == "fee":
        return "fee_rag"
    else:
        return "general"


# ============================================
# Step 5 Building A Graph
# ============================================
graph = StateGraph(State)

# Add Nodes
graph.add_node("classifier", classifier)
graph.add_node("academic_rag", academic_rag_node)
graph.add_node("fee_rag", fee_rag_node)
graph.add_node("general", general_node)
graph.add_node("response", response_node)

# Add Edges
graph.add_edge(START, "classifier")

# FIXED: Passed node mapping dict matching the return values of route_query
graph.add_conditional_edges(
    "classifier",
    route_query,
    {
        "academic_rag": "academic_rag",
        "fee_rag": "fee_rag",
        "general": "general"
    }
) 

graph.add_edge("academic_rag", "response")
graph.add_edge("fee_rag", "response")
graph.add_edge("general", "response")
graph.add_edge("response", END)

app = graph.compile()

# ============================================
# Execution Flow
# ============================================
print("Welcome to The College Assistant\n\n ")
print("Which Program are you in?")
print("1: BBA")
print("2: BCA")
print("3: B.COM (h)")

choice = input("Enter 1, 2, or 3: ")

program_map = {
    "1": "BBA",
    "2": "BCA",
    "3": "B.COM (h)"
}

student_program = program_map.get(choice, "N/A")
print(f"You are in {student_program} program\n\n")

while True:
    user_input = input("Ask your question (or type 'exit' to quit): ")
    if user_input.lower() == 'exit':
        print("Thank you for using the College Assistant. Goodbye!")
        break
        
    result = app.invoke({"program": student_program, "message": [("user", user_input)]})    
    print(f"\nAI Assistant: {result['message'][-1].content}\n\n")