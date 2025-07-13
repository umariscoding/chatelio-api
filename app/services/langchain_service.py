import os
import time
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from pinecone import Pinecone, ServerlessSpec
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from typing import AsyncGenerator, List, Dict, Optional
from app.core.config import GOOGLE_API_KEY, MODEL_NAME
import asyncio
from app.services.prompts import contextualize_q_system_prompt, qa_system_prompt
from app.db.database import load_session_history

load_dotenv(dotenv_path='app/.env')

# Retrieve API keys from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY") 
if not openai_api_key:
    raise ValueError("OpenAI API key is not set in the environment variables.")

pinecone_api_key = os.getenv("PINECONE_API_KEY")
if not pinecone_api_key:
    raise ValueError("Pinecone API key is not set in the environment variables.")

# Initialize Pinecone
pc = Pinecone(api_key=pinecone_api_key)

# Base index name for all companies
BASE_INDEX_NAME = "chatelio-multi-tenant"

# Performance optimization: Cache frequently used objects
_company_vector_stores: Dict[str, PineconeVectorStore] = {}
_company_rag_chains: Dict[str, Dict[str, RunnableWithMessageHistory]] = {}

def get_company_index_name(company_id: str) -> str:
    """
    Generate a company-specific index name.
    For now, we use the same base index but with namespaces.
    """
    return BASE_INDEX_NAME

def get_company_namespace(company_id: str) -> str:
    """
    Generate a company-specific namespace within the index.
    """
    return f"company_{company_id}"

def ensure_base_index_exists():
    """
    Ensure the base multi-tenant index exists.
    """
    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
    
    if BASE_INDEX_NAME not in existing_indexes:
        pc.create_index(
            name=BASE_INDEX_NAME,
            dimension=1536,  # OpenAI embedding dimension
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        # Wait for index to be ready
        while not pc.describe_index(BASE_INDEX_NAME).status["ready"]:
            time.sleep(1)

def create_company_vector_store(company_id: str, doc_chunks: List[str]) -> PineconeVectorStore:
    """
    Create a company-specific vector store with the provided document chunks.
    
    Args:
        company_id (str): Company ID
        doc_chunks (List[str]): List of text chunks to embed
        
    Returns:
        PineconeVectorStore: Company-specific vector store
    """
    global _company_vector_stores, _company_rag_chains
    
    # Ensure base index exists
    ensure_base_index_exists()
    
    # Get company namespace
    namespace = get_company_namespace(company_id)
    
    # Create embeddings
    embedding_function = OpenAIEmbeddings()
    
    # Create vector store with company-specific namespace
    vector_store = PineconeVectorStore.from_texts(
        doc_chunks,
        embedding_function,
        index_name=BASE_INDEX_NAME,
        namespace=namespace
    )
    
    # Cache the vector store
    _company_vector_stores[company_id] = vector_store
    
    # Clear RAG chains cache for this company
    if company_id in _company_rag_chains:
        _company_rag_chains[company_id].clear()
    
    return vector_store

def get_company_vector_store(company_id: str) -> PineconeVectorStore:
    """
    Get or create a company-specific vector store.
    
    Args:
        company_id (str): Company ID
        
    Returns:
        PineconeVectorStore: Company-specific vector store
    """
    global _company_vector_stores
    
    # Check if we have a cached vector store
    if company_id in _company_vector_stores:
        return _company_vector_stores[company_id]
    
    # Ensure base index exists
    ensure_base_index_exists()
    
    # Get company namespace
    namespace = get_company_namespace(company_id)
    
    # Create embeddings
    embedding_function = OpenAIEmbeddings()
    
    # Create vector store connection with company-specific namespace
    vector_store = PineconeVectorStore(
        index_name=BASE_INDEX_NAME,
        embedding=embedding_function,
        namespace=namespace
    )
    
    # Cache the vector store
    _company_vector_stores[company_id] = vector_store
    
    return vector_store

def setup_company_knowledge_base(company_id: str, doc_chunks: List[str]):
    """
    Set up knowledge base for a company. For now, all companies get the same data.
    
    Args:
        company_id (str): Company ID
        doc_chunks (List[str]): Document chunks to store
    """
    return create_company_vector_store(company_id, doc_chunks)

def process_company_document(company_id: str, document_content: str, doc_id: Optional[str] = None) -> bool:
    """
    Process a document for a company's knowledge base.
    
    Args:
        company_id (str): Company ID
        document_content (str): Document content to process
        doc_id (str, optional): Document ID for tracking
    
    Returns:
        bool: True if processing was successful
    """
    try:
        # Split document into chunks
        from app.services.document_service import split_text_for_txt
        doc_chunks = split_text_for_txt(document_content)
        
        # Get or create company vector store
        vector_store = get_company_vector_store(company_id)
        
        # Add document chunks to vector store
        vector_store.add_texts(doc_chunks)
        
        # Clear RAG chain cache for this company to force refresh
        clear_company_cache(company_id)
        
        # Update document status if doc_id is provided
        if doc_id:
            import asyncio
            from app.db.database import update_document_embeddings_status
            asyncio.create_task(update_document_embeddings_status(doc_id, 'completed'))
        
        return True
        
    except Exception as e:
        print(f"Error processing document for company {company_id}: {str(e)}")
        
        # Update document status to failed if doc_id is provided
        if doc_id:
            import asyncio
            from app.db.database import update_document_embeddings_status
            asyncio.create_task(update_document_embeddings_status(doc_id, 'failed'))
        
        return False

def clear_company_knowledge_base(company_id: str):
    """
    Clear all knowledge base content for a company.
    
    Args:
        company_id (str): Company ID
    """
    try:
        # Get company namespace
        namespace = get_company_namespace(company_id)
        
        # Delete all vectors in the namespace
        index = pc.Index(BASE_INDEX_NAME)
        index.delete(delete_all=True, namespace=namespace)
        
        # Clear caches
        clear_company_cache(company_id)
        
        return True
        
    except Exception as e:
        print(f"Error clearing knowledge base for company {company_id}: {str(e)}")
        return False

def get_company_rag_chain(company_id: str, llm_model: str = "Gemini") -> RunnableWithMessageHistory:
    """
    Get or create a company-specific RAG chain.
    
    Args:
        company_id (str): Company ID
        llm_model (str): LLM model to use
        
    Returns:
        RunnableWithMessageHistory: Company-specific RAG chain
    """
    global _company_rag_chains
    
    # Initialize company cache if not exists
    if company_id not in _company_rag_chains:
        _company_rag_chains[company_id] = {}
    
    # Check if we have a cached RAG chain for this company and model
    if llm_model in _company_rag_chains[company_id]:
        return _company_rag_chains[company_id][llm_model]
    
    # Get company-specific vector store
    vector_store = get_company_vector_store(company_id)
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
    
    # Create LLM
    if llm_model == "Gemini":
        llm = ChatGoogleGenerativeAI(
            model=MODEL_NAME, 
            google_api_key=GOOGLE_API_KEY
        )
    elif llm_model == "OpenAI":
        llm = ChatOpenAI()
    else:
        raise ValueError(f"Model {llm_model} not available")
    
    # Create prompts
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    
    # Create chains
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    # Create session history function
    def get_session_history(chat_id: str) -> BaseChatMessageHistory:
        return load_session_history(company_id, chat_id)
    
    # Create conversational RAG chain
    conversational_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )
    
    # Cache the chain
    _company_rag_chains[company_id][llm_model] = conversational_rag_chain
    
    return conversational_rag_chain

async def stream_company_response(company_id: str, query: str, chat_id: str, llm_model: str = "Gemini") -> AsyncGenerator[str, None]:
    """
    Stream response from company-specific RAG chain.
    
    Args:
        company_id (str): Company ID
        query (str): User query
        chat_id (str): Chat ID
        llm_model (str): LLM model to use
        
    Yields:
        str: Response chunks
    """
    try:
        # Get company-specific RAG chain
        rag_chain = get_company_rag_chain(company_id, llm_model)
        
        # Stream response
        resp = rag_chain.stream(
            {"input": query},
            config={"configurable": {"session_id": chat_id}},
        )
        
        for chunk in resp:
            if 'answer' in chunk:
                yield chunk['answer']
    
    except Exception as e:
        yield f"Error: {str(e)}"

# Legacy compatibility functions (updated to use company context)
def create_embeddings_and_store_text(doc_chunks: List[str], company_id: str = "default") -> PineconeVectorStore:
    """
    Legacy function updated for company context.
    """
    return create_company_vector_store(company_id, doc_chunks)

def get_pinecone_vectorstore(company_id: str = "default") -> PineconeVectorStore:
    """
    Legacy function updated for company context.
    """
    return get_company_vector_store(company_id)

def get_rag_chain(llm_model: str = "Gemini", company_id: str = "default") -> RunnableWithMessageHistory:
    """
    Legacy function updated for company context.
    """
    return get_company_rag_chain(company_id, llm_model)

def query_pinecone(db: PineconeVectorStore, llm_model: str = "Gemini", chat_id: str = 'abc123', company_id: str = "default"):
    """
    Legacy function updated for company context.
    """
    return get_company_rag_chain(company_id, llm_model)

async def stream_response(query: str, conversational_rag_chain, chat_id: str = 'abc123', company_id: str = "default") -> AsyncGenerator[str, None]:
    """
    Legacy function - now redirects to company-specific streaming.
    """
    async for chunk in stream_company_response(company_id, query, chat_id):
        yield chunk

# Initialize default company knowledge base for backward compatibility
def initialize_default_knowledge_base(doc_chunks: List[str]):
    """
    Initialize the default knowledge base for backward compatibility.
    """
    create_company_vector_store("default", doc_chunks)

# Cache management functions
def clear_company_cache(company_id: str):
    """Clear cache for a specific company."""
    global _company_vector_stores, _company_rag_chains
    
    if company_id in _company_vector_stores:
        del _company_vector_stores[company_id]
    
    if company_id in _company_rag_chains:
        del _company_rag_chains[company_id]

def clear_all_cache():
    """Clear all cached data."""
    global _company_vector_stores, _company_rag_chains
    
    _company_vector_stores.clear()
    _company_rag_chains.clear()

# For backward compatibility
def clear_cache():
    """Legacy function for clearing cache."""
    clear_all_cache()

def force_refresh_all_rag_chains():
    """Legacy function for refreshing RAG chains."""
    clear_all_cache()
