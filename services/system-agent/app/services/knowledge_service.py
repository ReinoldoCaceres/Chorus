from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog
import uuid

from app.config import get_settings
from app.models.database import KnowledgeBase
from app.models.schemas import (
    KnowledgeBaseCreate, 
    KnowledgeBaseUpdate, 
    KnowledgeBaseResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    KnowledgeSearchResponse
)

logger = structlog.get_logger()
settings = get_settings()


class KnowledgeService:
    """Service for managing knowledge base and vector operations"""
    
    def __init__(self):
        self.settings = settings
        self._chroma_client = None
        self._collection = None
        
    @property
    def chroma_client(self):
        """Lazy initialization of ChromaDB client"""
        if self._chroma_client is None:
            try:
                # Configure ChromaDB client
                chroma_settings = ChromaSettings(
                    persist_directory=self.settings.chromadb_persist_directory,
                    allow_reset=True
                )
                
                self._chroma_client = chromadb.Client(chroma_settings)
                logger.info("ChromaDB client initialized", 
                           persist_dir=self.settings.chromadb_persist_directory)
            except Exception as e:
                logger.error("Failed to initialize ChromaDB client", error=str(e))
                raise
        return self._chroma_client
    
    @property
    def collection(self):
        """Get or create the knowledge base collection"""
        if self._collection is None:
            try:
                # Try to get existing collection
                self._collection = self.chroma_client.get_collection(
                    name="system_agent_knowledge"
                )
            except Exception:
                # Create new collection if it doesn't exist
                self._collection = self.chroma_client.create_collection(
                    name="system_agent_knowledge",
                    metadata={"description": "System Agent Knowledge Base"}
                )
                logger.info("Created new ChromaDB collection: system_agent_knowledge")
        return self._collection
    
    async def create_knowledge_entry(
        self, 
        db: AsyncSession, 
        knowledge_data: KnowledgeBaseCreate
    ) -> KnowledgeBaseResponse:
        """Create a new knowledge base entry"""
        try:
            # Create database entry
            db_knowledge = KnowledgeBase(**knowledge_data.model_dump())
            db.add(db_knowledge)
            await db.flush()  # Get the ID
            
            # Create embedding and store in ChromaDB
            embedding_id = str(db_knowledge.id)
            
            # Add to vector store
            self.collection.add(
                documents=[knowledge_data.content],
                metadatas=[{
                    "category": knowledge_data.category,
                    "title": knowledge_data.title,
                    "tags": knowledge_data.tags,
                    **knowledge_data.metadata
                }],
                ids=[embedding_id]
            )
            
            # Update database with embedding ID
            db_knowledge.embedding_id = embedding_id
            await db.commit()
            await db.refresh(db_knowledge)
            
            logger.info("Created knowledge entry", 
                       id=str(db_knowledge.id), 
                       category=knowledge_data.category)
            
            return KnowledgeBaseResponse.model_validate(db_knowledge)
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to create knowledge entry", error=str(e))
            raise
    
    async def get_knowledge_entry(
        self, 
        db: AsyncSession, 
        entry_id: uuid.UUID
    ) -> Optional[KnowledgeBaseResponse]:
        """Get a knowledge base entry by ID"""
        try:
            result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == entry_id)
            )
            knowledge = result.scalar_one_or_none()
            
            if knowledge:
                return KnowledgeBaseResponse.model_validate(knowledge)
            return None
            
        except Exception as e:
            logger.error("Failed to get knowledge entry", 
                        entry_id=str(entry_id), error=str(e))
            raise
    
    async def update_knowledge_entry(
        self, 
        db: AsyncSession, 
        entry_id: uuid.UUID, 
        update_data: KnowledgeBaseUpdate
    ) -> Optional[KnowledgeBaseResponse]:
        """Update a knowledge base entry"""
        try:
            result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == entry_id)
            )
            knowledge = result.scalar_one_or_none()
            
            if not knowledge:
                return None
            
            # Update database fields
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(knowledge, field, value)
            
            # If content was updated, update the vector store
            if "content" in update_dict:
                if knowledge.embedding_id:
                    # Update existing embedding
                    self.collection.update(
                        ids=[knowledge.embedding_id],
                        documents=[knowledge.content],
                        metadatas=[{
                            "category": knowledge.category,
                            "title": knowledge.title,
                            "tags": knowledge.tags,
                            **knowledge.metadata
                        }]
                    )
            
            await db.commit()
            await db.refresh(knowledge)
            
            logger.info("Updated knowledge entry", 
                       id=str(entry_id), 
                       updated_fields=list(update_dict.keys()))
            
            return KnowledgeBaseResponse.model_validate(knowledge)
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to update knowledge entry", 
                        entry_id=str(entry_id), error=str(e))
            raise
    
    async def delete_knowledge_entry(
        self, 
        db: AsyncSession, 
        entry_id: uuid.UUID
    ) -> bool:
        """Delete a knowledge base entry"""
        try:
            result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == entry_id)
            )
            knowledge = result.scalar_one_or_none()
            
            if not knowledge:
                return False
            
            # Remove from vector store
            if knowledge.embedding_id:
                try:
                    self.collection.delete(ids=[knowledge.embedding_id])
                except Exception as e:
                    logger.warning("Failed to delete from vector store", 
                                  embedding_id=knowledge.embedding_id, 
                                  error=str(e))
            
            # Remove from database
            await db.delete(knowledge)
            await db.commit()
            
            logger.info("Deleted knowledge entry", id=str(entry_id))
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to delete knowledge entry", 
                        entry_id=str(entry_id), error=str(e))
            raise
    
    async def search_knowledge(
        self, 
        db: AsyncSession, 
        search_request: KnowledgeSearchRequest
    ) -> KnowledgeSearchResponse:
        """Search knowledge base using vector similarity"""
        try:
            # Prepare query filters
            where_filters = {}
            if search_request.category:
                where_filters["category"] = search_request.category
            
            # Perform vector search
            search_results = self.collection.query(
                query_texts=[search_request.query],
                n_results=search_request.limit,
                where=where_filters if where_filters else None
            )
            
            results = []
            if search_results["ids"] and search_results["ids"][0]:
                for i, doc_id in enumerate(search_results["ids"][0]):
                    distance = search_results["distances"][0][i]
                    similarity_score = 1 - distance  # Convert distance to similarity
                    
                    # Skip results below threshold
                    if similarity_score < search_request.similarity_threshold:
                        continue
                    
                    # Get metadata
                    metadata = search_results["metadatas"][0][i]
                    document = search_results["documents"][0][i]
                    
                    result = KnowledgeSearchResult(
                        id=uuid.UUID(doc_id),
                        title=metadata.get("title", ""),
                        content=document,
                        category=metadata.get("category", ""),
                        similarity_score=similarity_score,
                        metadata={k: v for k, v in metadata.items() 
                                if k not in ["title", "category", "tags"]},
                        tags=metadata.get("tags", [])
                    )
                    results.append(result)
            
            logger.info("Knowledge search completed", 
                       query=search_request.query, 
                       results_count=len(results))
            
            return KnowledgeSearchResponse(
                query=search_request.query,
                results=results,
                total_found=len(results)
            )
            
        except Exception as e:
            logger.error("Failed to search knowledge base", 
                        query=search_request.query, error=str(e))
            raise
    
    async def get_knowledge_entries(
        self, 
        db: AsyncSession, 
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[KnowledgeBaseResponse]:
        """Get knowledge base entries with optional filtering"""
        try:
            query = select(KnowledgeBase).where(KnowledgeBase.is_active == True)
            
            if category:
                query = query.where(KnowledgeBase.category == category)
            
            query = query.offset(offset).limit(limit).order_by(KnowledgeBase.created_at.desc())
            
            result = await db.execute(query)
            entries = result.scalars().all()
            
            return [KnowledgeBaseResponse.model_validate(entry) for entry in entries]
            
        except Exception as e:
            logger.error("Failed to get knowledge entries", error=str(e))
            raise