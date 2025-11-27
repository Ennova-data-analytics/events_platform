from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import hashlib
from datetime import datetime 
from core.config import settings
from typing import BinaryIO
import logging

logger = logging.getLogger(__name__)

class DocumentVectorizationService:
    def __init__(self, qdrant_client: QdrantClient, collection_name: str = None):
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.OPENAI_API_KEY,
            model="text-embedding-3-small"
        )      
    
    def extract_text_with_structure(self, file: BinaryIO) -> str:
        """Extract text from DOCX file"""
        doc = Document(file)
        full_text = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if len(text) < 3:
                continue 
            full_text.append(text)
        
        return "\n\n".join(full_text)
    
    def get_parent_child_chunks(self, text: str) -> list[dict[str, str]]:
        """Chunk establishment, parent -> children relation"""
        parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        child_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)

        parent_docs = parent_splitter.split_text(text)
        chunks_to_vectorise = []

        for parent_doc in parent_docs:
            child_docs = child_splitter.split_text(parent_doc)
            for child_text in child_docs:
                chunks_to_vectorise.append({
                    "child_content": child_text,
                    "parent_content": parent_doc
                })
        
        return chunks_to_vectorise

    async def process_document(self, file: BinaryIO, filename: str, event_id: int = None, metadata: dict = None):
        """Main processing pipeline for document vectorization"""
        try:
            #Text Extraction
            clean_text = self.extract_text_with_structure(file)

            #Parent-child pairs
            chunk_pairs = self.get_parent_child_chunks(clean_text)

            #Embedding child content
            child_texts = [p["child_content"] for p in chunk_pairs]
            embeddings = await self.embeddings.aembed_documents(child_texts)

            #Points generation
            points = []

            for idx, (pair, embedding) in enumerate(zip(chunk_pairs, embeddings)):
                doc_id = hashlib.md5(f"{filename}_{idx}_{datetime.utcnow().timestamp()}".encode()).hexdigest()

                payload = {
                    "document_id": doc_id,
                    "filename": filename,
                    "content": pair["child_content"],
                    "full_context": pair["parent_content"],
                    "created_at": datetime.utcnow().isoformat(),
                    "chunk_index": idx,
                }

                #Add event_id if provided
                if event_id:
                    payload["event_id"] = event_id

                #Add custom metadata if provided
                if metadata:
                    payload["metadata"] = metadata
                
                points.append(PointStruct(
                    id=doc_id,
                    vector=embedding,
                    payload=payload
                ))
            
            #Load into Qdrant
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )

            logger.info(f"Successfully vectorized: {len(points)} chunks from {filename}")
            return len(points)
        
        except Exception as e:
            logger.error(f"Error processing document: {filename}: {e}")
            raise 