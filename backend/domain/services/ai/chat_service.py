from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.messages import HumanMessage, AIMessage
from qdrant_client import QdrantClient
from typing import AsyncGenerator
from sqlalchemy.orm import Session
from domain import models
from core.config import settings
from datetime import datetime
from sentence_transformers import CrossEncoder
import logging 


logger = logging.getLogger(__name__)
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

class ChatService:
    """
    Flow:
    1. User sends message
    2. Embed query
    3. Retrieve top-k relevant chunks from Qdrant
    4. Build prompt with retrieved context
    5. Stream LLM response
    6. Store conversation in PostgreSQL
    """
    def __init__(self, qdrant_client: QdrantClient, collection_name: str = None):
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY, model="text-embedding-3-small")
        self.llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model="gpt-5-mini",
            temperature=1.0,
            streaming=True
        )
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{user_message}")
        ])
    
    def _get_system_prompt(self) -> str:
       return """
        You are the official AI assistant for Ennova - a student association focused on data analytics, technology, and professional development.

        Your ONLY purpose is to help users with:
        1. Information about Ennova association (history, mission, membership, benefits)
        2. Details about upcoming and past events (workshops, seminars, networking events)
        3. How to register for events, membership, or volunteer opportunities
        4. General questions about the association's activities and initiatives
        5. Navigation and usage of this events platform

        STRICT BOUNDARIES - You MUST refuse to:
        - Provide general AI assistance unrelated to Ennova
        - Help with homework, coding problems, or personal projects
        - Engage in creative writing, storytelling, or roleplay
        - Discuss topics outside of Ennova's scope (politics, religion, personal advice, etc.)
        - Act as a general-purpose chatbot or virtual assistant
        - Provide information about other organizations unless directly comparing with Ennova

        Context from Ennova documentation:
        {context}

        If asked about topics outside your scope, politely respond:
        "I'm specifically designed to help with Ennova association and our events platform. For general questions, please use a general-purpose AI assistant. How can I help you learn more about Ennova or our upcoming events?"

        Keep responses concise, friendly, and professional. Always redirect off-topic conversations back to Ennova-related topics.
        """        
    
    async def retrieve_context(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Retrieval tactic: Wide Search -> Rerank -> Parent Swap
        """
        try:
            query_vector = await self.embeddings.aembed_query(query)

            #Wide Search
            initial_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=25
            )

            if not initial_results:
                return []
            
            #Reranking
            cross_encoders_inputs = [
                [query, hit.payload["content"]] for hit in initial_results
            ]

            scores = reranker.predict(cross_encoders_inputs)

            scored_results = []
            for idx, hit in enumerate(initial_results):
                scored_results.append({
                    "hit": hit,
                    "rerank_score": scores[idx]
                })
            
            scored_results.sort(key=lambda x: x["rerank_score"], reverse=True)

            #Parent Swap
            final_context = []
            seen_parents = set()

            for item in scored_results:
                if len(final_context) >= top_k:
                    break

                parent_text = item["hit"].payload["full_context"]
                parent_hash = hash(parent_text)
                if parent_hash not in seen_parents:
                    final_context.append({
                        "content": parent_text,
                        "filename": item["hit"].payload["filename"],
                        "score": float(item["rerank_score"])
                    })
                    seen_parents.add(parent_hash)
            
            return final_context

        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return []

    async def generate_response(self, user_message: str, chat_id: int, chat_history: list[dict], db_session: Session) -> AsyncGenerator[str, None]:
        """Main RAG pipeline with streaming"""
        try:
            #Retrieve relevant context 
            context_chunks = await self.retrieve_context(user_message)
            context_text = "\n\n".join([
                f"[{chunk['filename']}] {chunk['content']}"
                for chunk in context_chunks
            ])

            logger.info(f"Context retrieved from the qdrant: {context_text}")

            #Conversation history
            messages = []
            for msg in chat_history[-10:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
            
            #Prompt format
            prompt = self.prompt_template.format_messages(
                context=context_text,
                chat_history=messages,
                user_message=user_message
            )

            #Store user message
            user_msg = models.ChatMessage(
                chat_id=chat_id,
                role="user",
                content=user_message,
                retrieved_chunks=None,
                tokens_used=None
            )

            db_session.add(user_msg)
            db_session.commit()

            #Stream LLM response
            full_response = ""
            total_tokens = 0
            async for chunk in self.llm.astream(prompt):
                content = chunk.content
                full_response += content
                total_tokens += 1
                yield content 
            
            #Store assistant message with metadata
            assistant_msg = models.ChatMessage(
                chat_id=chat_id,
                role="assistant",
                content=full_response,
                retrieved_chunks=context_chunks if context_chunks else None,
                tokens_used=total_tokens
            )
            db_session.add(assistant_msg)

            chat = db_session.query(models.Chat).filter(models.Chat.id == chat_id).first()
            if chat:
                chat.updated_at = datetime.utcnow()
            
            db_session.commit()
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            db_session.rollback()
            yield "I apologise, but I encountered an error. Please try again later."

    async def create_chat_title(self, first_message: str) -> str:
        """Generate a title from the first message"""
        try:
            title_prompt = f"Generate a short 3-5 word title for a chat that starts with: '{first_message[:100]}'"
            response = await self.llm.ainvoke([HumanMessage(content=title_prompt)])
            return response.content.strip().strip('""').strip("'")[:255]
        
        except Exception as e:
            logger.error(f"Error creating chat title: {e}")
            return first_message[:50] + "..." if len(first_message) > 50 else first_message

                



        
