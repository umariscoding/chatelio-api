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
store = {}

# Retrieve API keys from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY") 
if not openai_api_key:
    raise ValueError("OpenAI API key is not set in the environment variables.")

pinecone_api_key = os.getenv("PINECONE_API_KEY")
if not pinecone_api_key:
    raise ValueError("Pinecone API key is not set in the environment variables.")

# Initialize Pinecone
pc = Pinecone(api_key=pinecone_api_key)

index_name = "umar-azhar-index"

# Performance optimization: Cache frequently used objects
_vector_store_cache: Optional[PineconeVectorStore] = None
_rag_chains_cache: Dict[str, RunnableWithMessageHistory] = {}

def create_embeddings_and_store_text(doc_chunks: List[str]) -> PineconeVectorStore:
    """
    Creates embeddings from text chunks and stores them in Pinecone.
    
    Args:
        doc_chunks (List[str]): List of text chunks to embed.
    
    Returns:
        PineconeVectorStore: Pinecone vector store instance.
    """
    global _vector_store_cache, _rag_chains_cache
    
    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

    if index_name in existing_indexes:
        pc.delete_index(index_name)
    
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    while not pc.describe_index(index_name).status["ready"]:
        time.sleep(1)
    
    embedding_function = OpenAIEmbeddings()
    vector_store = PineconeVectorStore.from_texts(
        doc_chunks,
        embedding_function,
        index_name=index_name,
    )
    
    # Clear cache when new embeddings are created
    _vector_store_cache = None
    _rag_chains_cache.clear()
    
    return vector_store

def get_pinecone_vectorstore() -> PineconeVectorStore:
    """
    Loads the existing Pinecone vector store with caching for performance.
    
    Returns:
        PineconeVectorStore: Pinecone vector store instance.
    """
    global _vector_store_cache
    
    if _vector_store_cache is None:
        embedding_function = OpenAIEmbeddings()
        _vector_store_cache = PineconeVectorStore(
            index_name=index_name,
            embedding=embedding_function
        )
    
    return _vector_store_cache

def get_rag_chain(llm_model: str = "OpenAI", force_refresh: bool = False) -> RunnableWithMessageHistory:
    """
    Gets or creates a cached RAG chain for the specified model.
    
    Args:
        llm_model (str): The LLM model to use ("OpenAI" or "Gemini").
        force_refresh (bool): If True, forces recreation of the RAG chain even if cached.
    
    Returns:
        RunnableWithMessageHistory: Cached conversational RAG chain.
    """
    global _rag_chains_cache
    
    if force_refresh or llm_model not in _rag_chains_cache:
        # Create new RAG chain and cache it
        db = get_pinecone_vectorstore()
        retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 4})  # Reduced from 6 to 4
        
        if llm_model == "Gemini":
            llm = ChatGoogleGenerativeAI(
                model=MODEL_NAME, 
                google_api_key=GOOGLE_API_KEY
            )
        elif llm_model == "OpenAI":
            llm = ChatOpenAI()
        else:
            raise ValueError(f"Model {llm_model} not available")
        
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        history_aware_retriever = create_history_aware_retriever(
            llm, retriever, contextualize_q_prompt
        )
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qa_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
        
        def get_session_history(chat_id: str) -> BaseChatMessageHistory:
            # Always load fresh session history to prevent contamination
            # Don't cache in store to avoid session contamination
            # TODO: Need to get company_id from context - using temp default for now
            return load_session_history("default-company", chat_id)
        
        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
        
        _rag_chains_cache[llm_model] = conversational_rag_chain
    
    return _rag_chains_cache[llm_model]

def query_pinecone(db: PineconeVectorStore, llm_model: str = "OpenAI", chat_id: str = 'abc123'):
    """
    Gets the conversational RAG chain (now with caching for performance).
    
    Args:
        db (PineconeVectorStore): Pinecone vector store instance (kept for compatibility).
        llm_model (str): The LLM model to use ("OpenAI" or "Gemini").
        chat_id (str): The chat session ID.
    
    Returns:
        RunnableWithMessageHistory: Cached conversational RAG chain.
    """
    return get_rag_chain(llm_model)

async def stream_response(query: str, conversational_rag_chain, chat_id: str = 'abc123') -> AsyncGenerator[str, None]:
    """
    Streams the response from the conversational RAG chain with optimized performance.
    
    Args:
        query (str): The user's query.
        conversational_rag_chain: The configured conversational RAG chain.
        chat_id (str): The chat session ID.
    
    Yields:
        AsyncGenerator[str, None]: Streamed answer chunks.
    """
    try:
        resp = conversational_rag_chain.stream(
            {"input": query},
            config={"configurable": {"session_id": chat_id}},
        )
        for chunk in resp:
            if 'answer' in chunk:
                yield chunk['answer']
                # Removed artificial delay for better performance
                # await asyncio.sleep(0.05)  # Removed this line
    
    except Exception as e:
        yield f"Error: {str(e)}"

def clear_cache():
    """
    Clears all cached objects. Useful for testing or when vector store is updated.
    """
    global _vector_store_cache, _rag_chains_cache, store
    _vector_store_cache = None
    _rag_chains_cache.clear()
    store.clear()  # Clear any remaining contaminated session data
    print("All caches cleared including contaminated session store")

def force_refresh_all_rag_chains():
    """
    Forces recreation of all RAG chains with updated prompts.
    This is useful when prompts are updated and you want to ensure
    all cached chains use the new prompts.
    """
    global _rag_chains_cache
    # Clear existing cache first
    _rag_chains_cache.clear()
    
    # Pre-create fresh RAG chains for available models
    try:
        get_rag_chain("OpenAI", force_refresh=True)
    except Exception as e:
        print(f"Warning: Could not refresh OpenAI RAG chain: {e}")
    
    try:
        get_rag_chain("Gemini", force_refresh=True)
    except Exception as e:
        print(f"Warning: Could not refresh Gemini RAG chain: {e}")
        
    print("RAG chains cache cleared and available models refreshed")
