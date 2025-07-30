import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict, Any, Optional
from uuid import UUID
import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class VectorStoreService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chromadb_persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize vector store
        self.vector_store = Chroma(
            client=self.chroma_client,
            collection_name="chorus_conversations",
            embedding_function=self.embeddings
        )
        
        logger.info("Vector store initialized")
    
    async def store_conversation(
        self, 
        conversation_id: UUID, 
        messages: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store conversation messages in vector database"""
        try:
            # Combine messages into text chunks
            conversation_text = self._format_messages(messages)
            
            # Split text into chunks
            chunks = self.text_splitter.split_text(conversation_text)
            
            # Prepare metadata for each chunk
            chunk_metadata = []
            for i, chunk in enumerate(chunks):
                chunk_meta = {
                    "conversation_id": str(conversation_id),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    **(metadata or {})
                }
                chunk_metadata.append(chunk_meta)
            
            # Store in vector database
            self.vector_store.add_texts(
                texts=chunks,
                metadatas=chunk_metadata,
                ids=[f"{conversation_id}_{i}" for i in range(len(chunks))]
            )
            
            logger.info("Conversation stored in vector database", 
                       conversation_id=str(conversation_id),
                       chunks_count=len(chunks))
            return True
            
        except Exception as e:
            logger.error("Failed to store conversation", 
                        conversation_id=str(conversation_id),
                        error=str(e))
            return False
    
    async def search_similar(
        self,
        query: str,
        conversation_id: Optional[UUID] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar content in vector database"""
        try:
            # Prepare filter
            where_filter = {}
            if conversation_id:
                where_filter["conversation_id"] = str(conversation_id)
            
            # Perform similarity search
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=limit,
                filter=where_filter if where_filter else None
            )
            
            # Format results
            formatted_results = []
            for doc, score in results:
                if score >= similarity_threshold:
                    formatted_results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "similarity_score": score
                    })
            
            logger.info("Vector search completed", 
                       query_length=len(query),
                       results_count=len(formatted_results))
            
            return formatted_results
            
        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            return []
    
    def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into a single text for processing"""
        formatted = []
        for msg in messages:
            sender = msg.get("sender_type", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("created_at", "")
            
            formatted.append(f"[{timestamp}] {sender}: {content}")
        
        return "\n".join(formatted)
    
    async def delete_conversation(self, conversation_id: UUID) -> bool:
        """Delete conversation from vector database"""
        try:
            # Get all document IDs for this conversation
            collection = self.chroma_client.get_collection("chorus_conversations")
            results = collection.get(
                where={"conversation_id": str(conversation_id)}
            )
            
            if results and results["ids"]:
                collection.delete(ids=results["ids"])
                logger.info("Conversation deleted from vector database",
                           conversation_id=str(conversation_id))
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to delete conversation",
                        conversation_id=str(conversation_id),
                        error=str(e))
            return False