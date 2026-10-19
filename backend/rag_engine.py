"""
AskGuruGranthSahib - RAG Query Engine
Handles retrieval from ChromaDB and generation via OpenAI GPT-4o.
Compatible with LangChain 1.x and langchain-chroma.
"""

import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

# --- Configuration ---
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "data", "chroma_db")
COLLECTION_NAME = "guru_granth_sahib"

# System prompt that guides the AI's behavior
SYSTEM_PROMPT = """You are a deeply knowledgeable and respectful AI assistant specialized in Sri Guru Granth Sahib Ji, the eternal Guru of the Sikhs. You have access to the sacred text and your role is to help seekers understand its teachings.

GUIDELINES:
1. Always base your answers on the actual text from Sri Guru Granth Sahib Ji provided in the context below.
2. When quoting from the scripture, mention the Ang (page) number.
3. Be respectful, reverent, and accurate. This is a sacred text — treat it with utmost respect.
4. If the context doesn't contain relevant information to answer the question, say so honestly rather than making up an answer.
5. Provide explanations in simple, accessible language while preserving the depth of the teachings.
6. When appropriate, provide both the original text (Gurmukhi/transliteration) and its meaning.
7. You may draw connections between different parts of the scripture when relevant.
8. Always maintain a tone of humility and devotion befitting the sacred nature of the text.

CONTEXT FROM SRI GURU GRANTH SAHIB JI:
{context}"""

CONDENSE_PROMPT = """Given the following conversation history and a follow-up question, rephrase the follow-up question to be a standalone question that captures the full context needed to search Sri Guru Granth Sahib Ji.

Conversation History:
{chat_history}

Follow-Up Question: {question}

Standalone Question:"""


def format_docs(docs):
    """Format retrieved documents into a context string with Ang references."""
    formatted = []
    for doc in docs:
        ang = doc.metadata.get("ang", "Unknown")
        formatted.append(f"[Ang {ang}]\n{doc.page_content}")
    return "\n\n---\n\n".join(formatted)


class RAGEngine:
    """Retrieval-Augmented Generation engine for Sri Guru Granth Sahib Ji."""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. Set it in your .env file."
            )

        # Initialize embeddings (same model used during ingestion)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=api_key,
        )

        # Connect to existing ChromaDB store
        if not os.path.exists(CHROMA_PERSIST_DIR):
            raise FileNotFoundError(
                f"ChromaDB not found at {CHROMA_PERSIST_DIR}. "
                "Run ingest.py first to build the knowledge base."
            )

        self.vectorstore = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=self.embeddings,
            collection_name=COLLECTION_NAME,
        )

        # Retriever with MMR for diverse results
        self.retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 8,
                "fetch_k": 20,
            },
        )

        # Initialize the LLM
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.3,
            openai_api_key=api_key,
            max_tokens=2000,
        )

        # Conversation history (simple list of messages)
        self.chat_history: list = []
        self.max_history = 12  # Keep last 12 messages (6 exchanges)

        # Build prompts
        self.qa_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ])

        self.condense_prompt = ChatPromptTemplate.from_template(CONDENSE_PROMPT)

    def _condense_question(self, question: str) -> str:
        """Rephrase follow-up question using conversation history."""
        if not self.chat_history:
            return question

        # Format chat history for the condense prompt
        history_text = ""
        for msg in self.chat_history:
            if isinstance(msg, HumanMessage):
                history_text += f"Human: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                history_text += f"Assistant: {msg.content[:200]}...\n"

        chain = self.condense_prompt | self.llm | StrOutputParser()
        return chain.invoke({
            "chat_history": history_text,
            "question": question,
        })

    def ask(self, question: str) -> dict:
        """
        Ask a question and get an answer grounded in Sri Guru Granth Sahib Ji.

        Returns:
            dict with 'answer', 'sources' (list of {ang, text_snippet})
        """
        # Step 1: Condense the question if there's conversation history
        standalone_question = self._condense_question(question)

        # Step 2: Retrieve relevant documents
        docs = self.retriever.invoke(standalone_question)

        # Step 3: Format context
        context = format_docs(docs)

        # Step 4: Generate answer
        chain = self.qa_prompt | self.llm | StrOutputParser()
        answer = chain.invoke({
            "context": context,
            "chat_history": self.chat_history,
            "question": question,
        })

        # Step 5: Update conversation history
        self.chat_history.append(HumanMessage(content=question))
        self.chat_history.append(AIMessage(content=answer))

        # Trim history if too long
        if len(self.chat_history) > self.max_history:
            self.chat_history = self.chat_history[-self.max_history:]

        # Step 6: Extract source references
        sources = []
        seen_angs = set()
        for doc in docs:
            ang = doc.metadata.get("ang", "Unknown")
            if ang not in seen_angs:
                sources.append({
                    "ang": ang,
                    "text": doc.page_content[:300] + ("..." if len(doc.page_content) > 300 else ""),
                })
                seen_angs.add(ang)

        return {
            "answer": answer,
            "sources": sources,
        }

    def reset_memory(self):
        """Clear conversation history."""
        self.chat_history.clear()

    def get_collection_stats(self) -> dict:
        """Get stats about the ingested knowledge base."""
        collection = self.vectorstore._collection
        return {
            "total_chunks": collection.count(),
            "collection_name": COLLECTION_NAME,
        }
