import os
from datetime import datetime

from langchain_community.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, AIMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

from app.database import chat_history_collection
from app.services.translation_service import TranslationService
from app.config import settings
from app.utils.loggers import logger


class RAGService:

    def __init__(self):

        self.translator = TranslationService()

        self.llm = None
        self.vector_store = None
        self.retriever = None

        self.user_memories = {}

    # ==========================================================
    # Load Previous Chats
    # ==========================================================

    def get_memory(self, user_id: str):

        if user_id in self.user_memories:
            return self.user_memories[user_id]

        memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )

        chats = chat_history_collection.find({"user_id": user_id}).sort("timestamp", 1)

        for chat in chats:

            if chat["role"] == "user":

                memory.chat_memory.add_message(HumanMessage(content=chat["message"]))

            else:

                memory.chat_memory.add_message(AIMessage(content=chat["message"]))

        self.user_memories[user_id] = memory

        return memory

    # ==========================================================
    # Initialize Models
    # ==========================================================

    def initialize(self):

        try:

            logger.info("🚀 Initializing RAG...")

            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )

            self.vector_store = FAISS.load_local(
                "faiss_index", embeddings, allow_dangerous_deserialization=True
            )

            self.retriever = self.vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": 8,
                    "fetch_k": 20,
                    "lambda_mult": 0.6
                }
            )

            logger.info("✅ FAISS Loaded")

            self.llm = ChatOpenAI(
                model="meta-llama/llama-3.1-8b-instruct",
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                temperature=0,
            )

            logger.info("✅ LLM Ready")

        except Exception as e:

            logger.error(f"Initialization Failed: {e}")

            self.llm = None
            self.retriever = None
    # ==========================================================
    # Retrieve Context
    # ==========================================================

    def retrieve_context(self, question: str):

            docs = self.retriever.invoke(question)

            logger.info("Retrieved Documents:")

            context = ""

            for i, doc in enumerate(docs):

                logger.info(f"Doc {i+1}")

                logger.info(doc.page_content[:500])

                context += f"\nDocument {i+1}:\n"

                context += "\n\n"
                context += doc.page_content
                context += "\n\n"

                context += "\n"

            return context

        # ==========================================================
        # Prompt Builder
        # ==========================================================

    def build_prompt(self, context: str, question: str):

            return f"""
        You are an AI assistant for Galgotias College.

        You MUST answer ONLY using the CONTEXT below.

        Rules:

        1. Read ALL documents before answering.

        2. NEVER use outside knowledge.

        3. NEVER guess.

        4. If the answer exists anywhere in the context,
        return it.

        5. If multiple names exist,
        list ALL of them.

        6. If the question asks about:

        - faculty
        - committee
        - members
        - fees
        - hostel
        - placement
        - holidays
        - rotaract
        - clubs

        extract the exact names/details from the context.

        7. Do NOT summarize lists.

        8. If the answer is not present,
        reply exactly:

        I don't have that information.

        -----------------------

        CONTEXT

        {context}

        -----------------------

        QUESTION

        {question}

        -----------------------

        ANSWER
        """

    # ==========================================================
    # Ask LLM
    # ==========================================================

    def ask_llm(self, prompt: str):

        response = self.llm.invoke(prompt)

        return response.content.strip()
        # ==========================================================

    # Main Query Function
    # ==========================================================

    def query(self, text: str, user_id: str):

        try:

            if self.llm is None:
                return "System not ready."

            memory = self.get_memory(user_id)

            # ------------------------------------
            # Detect language
            # ------------------------------------

            source_lang = self.translator.detect_lang(text)

            logger.info(f"🌍 Language: {source_lang}")

            original_question = text

            # ------------------------------------
            # Translate to English
            # ------------------------------------

            if source_lang != "en":

                english_question = self.translator.translate(text, source_lang, "en")

            else:

                english_question = text

            english_question = english_question.strip()

            logger.info(f"🔄 English Question: {english_question}")

            # ------------------------------------
            # Retrieve Context
            # ------------------------------------

            context = self.retrieve_context(english_question)

            # ------------------------------------
            # Previous Chat History
            # ------------------------------------

            history = ""

            for msg in memory.chat_memory.messages[-6:]:

                if isinstance(msg, HumanMessage):

                    history += f"User: {msg.content}\n"

                else:

                    history += f"Assistant: {msg.content}\n"

            # ------------------------------------
            # Build Prompt
            # ------------------------------------

            prompt = f"""
Previous Conversation:

{history}

====================================

{self.build_prompt(context, english_question)}
"""

            logger.info("Prompt Built Successfully")

            # ------------------------------------
            # Ask LLM
            # ------------------------------------

            english_answer = self.ask_llm(prompt)

            logger.info(f"🤖 English Answer: {english_answer}")

            # ------------------------------------
            # Translate Answer
            # ------------------------------------

            if source_lang != "en":

                final_answer = self.translator.translate(
                    english_answer, "en", source_lang
                )

            else:

                final_answer = english_answer

            logger.info(f"🌍 Final Answer: {final_answer}")

            # ------------------------------------
            # Save English Memory
            # ------------------------------------

            memory.chat_memory.add_user_message(english_question)

            memory.chat_memory.add_ai_message(english_answer)

            # ------------------------------------
            # Save Original Conversation
            # ------------------------------------

            chat_history_collection.insert_many(
                [
                    {
                        "user_id": user_id,
                        "role": "user",
                        "message": original_question,
                        "timestamp": datetime.utcnow(),
                    },
                    {
                        "user_id": user_id,
                        "role": "assistant",
                        "message": final_answer,
                        "timestamp": datetime.utcnow(),
                    },
                ]
            )

            return final_answer

        except Exception as e:

            logger.error(f"❌ Query Failed: {e}")

            return "Error processing request."
        # ==========================================================


# Global Instance
# ==========================================================

rag_instance = None


def set_rag_instance(instance):
    """
    Store the global RAG service instance.
    """
    global rag_instance
    rag_instance = instance


def query_rag(text: str, user_id: str):
    """
    Wrapper used by FastAPI routes.
    """

    if rag_instance is None:
        return "System not ready"

    return rag_instance.query(text, user_id)
