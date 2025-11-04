from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import hashlib
from pathlib import Path 
from datetime import datetime

class DocxVectoriser:
    def __init__(self, qdrant_url: str, qdrant_api_key: str, openai_api_key: str, collection_name: str = "documents", chunk_size: int = 500, chunk_overlap: int = 50):
        self.qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key, model="text-embedding-3-small")
        self.collection_name = collection_name
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=["\n\n", "\n", ". ", " ", ""])
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Create collection if not exists"""
        collections = self.qdrant_client.get_collections().collections
        if self.collection_name not in [c.name for c in collections]:
            self.qdrant_client.create_collection(collection_name=self.collection_name, vectors_config=VectorParams(size=1536, distance=Distance.COSINE))
    
    def extract_text_from_docx(self, file_path: Path) -> list[dict]:
        """Extract text with metadata from DOCX"""
        doc = Document(file_path)
        chunks = []

        for i, para in enumerate(doc.paragraphs):
            if para.text.strip():
                chunks.append({
                    "content": para.text,
                    "paragraph_index": i,
                    "filename": file_path.name
                })
        
        return chunks 
    
    def process_document(self, file_path: Path) -> int:
        """Main processing pipeline"""
        #Text extraction
        raw_chunks = self.extract_text_from_docx(file_path)

        #Splitting into semantic chunks
        texts = [chunk["content"] for chunk in raw_chunks]
        split_texts = self.text_splitter.split_text("\n\n".join(texts))

        #Embed
        embeddings = self.embeddings.embed_documents(split_texts)

        #Points generation
        points = []
        for idx, (text, embedding) in enumerate(zip(split_texts, embeddings)):
            doc_id = hashlib.md5(f"{file_path.name}_{idx}".encode()).hexdigest()

            points.append(PointStruct(
                id=doc_id,
                vector=embedding,
                payload={
                    "document_id": doc_id,
                    "filename": file_path.name,
                    "chunk_index": idx,
                    "content": text,
                    "metadata": {
                        "created_at": datetime.utcnow().isoformat()
                    }
                }
            ))

        #Load into Qdrant
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        return len(points)