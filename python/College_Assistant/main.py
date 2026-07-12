import os
from typing import TypedDict, Annotated, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from langchain_groq import ChatGroq
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

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise RuntimeError(
        "GROQ_API_KEY not found. Add it to a .env file in this folder, e.g:\n"
        "GROQ_API_KEY=your_key_here"
    )

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
# NOTE: make sure these PDF files exist in this folder
# (or update the paths below to the correct location)
# ============================================
academic_retriever = build_retriever("academics_handbook.pdf")
fee_retriever = build_retriever("fee_structure.pdf")

# ============================================
# LLM
# ============================================
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=groq_api_key,
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
# ============================================uv add -r requirements.txt
def classifier(state: State) -> dict:
    """Look at the latest message and decide which path to take"""
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
# Router Function
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
# Building the Graph
# ============================================
graph = StateGraph(State)

graph.add_node("classifier", classifier)
graph.add_node("academic_rag", academic_rag_node)
graph.add_node("fee_rag", fee_rag_node)
graph.add_node("general", general_node)
graph.add_node("response", response_node)

graph.add_edge(START, "classifier")

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

college_app = graph.compile()

# ============================================
# FastAPI App
# ============================================
api = FastAPI(title="College Assistant API")

# Allow the frontend (index.html) to call this API from any origin.
# Tighten this in production to your actual frontend domain.
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    program: str
    message: str
    history: Optional[List[HistoryItem]] = None


class ChatResponse(BaseModel):
    reply: str
    query_type: Optional[str] = None


@api.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Main chat endpoint used by index.html.
    Runs one turn through the LangGraph pipeline and returns the AI reply.
    """
    result = college_app.invoke({
        "program": req.program,
        "message": [("user", req.message)],
    })

    reply_text = result["message"][-1].content
    query_type = result.get("query_type")

    return ChatResponse(reply=reply_text, query_type=query_type)


@api.get("/health")
def health():
    return {"status": "ok"}


# ============================================
# Serve index.html at the root ("/") if it's
# placed in the same folder as this file
# ============================================
@api.get("/")
def serve_ui():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "College Assistant API is running. Place index.html next to main.py to serve the UI here."}


# ============================================
# Run with: uvicorn main:api --reload
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:api", host="0.0.0.0", port=8000, reload=True)
