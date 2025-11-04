from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.messages import HumanMessage, AIMessage
from qdrant_client import QdrantClient
from typing import AsyncGenerator

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
    def __init__(self, qdrant_client: QdrantClient, openai_api_key: str, collection_name: str = "documents"):
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key, model="text-embedding-3-small")
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
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
        You are a helpful assistant for an events platform.
        Answer questions based on the provided context from documentation

        Context from documents:
        {context}

        If the context does not contain relevant information, say no politely
        and provide general assistance based on your knowledge of event platforms
        """        
    
    async def retrieve_context(self, query: str, top_k: int = 5) -> list[dict]:
        """Semantic search"""
        query_vectory = self.embeddings.embed_query(query)

        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vectory,
            limit=top_k,
            score_threshold=0.7
        )

        return [
            {
                "content": hit.payload["content"],
                "filename": hit.payload["filename"],
                "score": hit.score
            }
            for hit in results
        ]

    async def generate_response(self, user_message: str, chat_history: list[dict], db_session) -> AsyncGenerator[str, None]:
        """Main RAG pipeline with streaming"""
        #Retrieve relevant context 
        context_chunks = await self.retrieve_context(user_message)
        context_text = "\n\n".join([
            f"[{chunk['filename']}] {chunk['content']}"
            for chunk in context_chunks
        ])

        #Conversation history
        messages = []
        for msg in chat_history[-10]:
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

        #Stream LLM response
        full_response = ""
        async for chunk in self.llm.astream(prompt):
            content = chunk.content
            full_response += content
            yield content 
        
        #Store the response in the DB