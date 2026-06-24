import os
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings

from app.services.translation_service import TranslationService
from app.config import settings
from app.utils.loggers import logger


class RAGService:
    def __init__(self):
        self.translator = TranslationService()
        self.qa_chain = None
        self.retriever = None
        self.user_memories = {}

    # =========================
    # Per-user memory
    # =========================
    def get_memory(self, user_id: str):
        if user_id not in self.user_memories:
            self.user_memories[user_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
        return self.user_memories[user_id]

    # =========================
    # Initialize RAG
    # =========================
    def initialize(self):
        try:
            logger.info("🚀 Initializing RAG service...")

            # -------------------------------------------------
            # 1) Load HuggingFace embeddings
            # -------------------------------------------------
            # IMPORTANT:
            # This MUST be the SAME embedding model that was used
            # while creating the FAISS index.
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )

            # -------------------------------------------------
            # 2) Load prebuilt FAISS index
            # -------------------------------------------------
            faiss_path = "faiss_index"

            if not os.path.exists(faiss_path):
                raise FileNotFoundError(
                    f"FAISS folder not found at '{faiss_path}'. "
                    f"Make sure faiss_index/index.faiss and index.pkl exist."
                )

            vector_store = FAISS.load_local(
                faiss_path,
                embeddings,
                allow_dangerous_deserialization=True
            )

            logger.info("✅ FAISS vector store loaded successfully")

            # -------------------------------------------------
            # 3) LLM via OpenRouter
            # -------------------------------------------------
            if not settings.OPENROUTER_API_KEY:
                raise ValueError("OPENROUTER_API_KEY is missing in environment variables")

            llm = ChatOpenAI(
                model="meta-llama/llama-3-8b-instruct",
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                temperature=0,
                timeout=30
            )

            logger.info("✅ OpenRouter LLM initialized successfully")

            # -------------------------------------------------
            # 4) Prompt template
            # -------------------------------------------------
            prompt_template = """
You are a helpful AI assistant.

Answer ONLY using the given context.
If the answer is partially available, still answer from the available context.
If the answer is not present in the context, say:
"I don't have that information."

Context:
{context}

Question:
{question}

Answer:
"""

            PROMPT = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )

            # -------------------------------------------------
            # 5) Retriever
            # -------------------------------------------------
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )

            self.retriever = retriever

            # -------------------------------------------------
            # 6) Conversational RAG chain
            # -------------------------------------------------
            self.qa_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                combine_docs_chain_kwargs={"prompt": PROMPT},
                return_source_documents=False
            )

            logger.info("✅ RAG initialized successfully")
            logger.info(f"OPENROUTER KEY PRESENT: {bool(settings.OPENROUTER_API_KEY)}")

        except Exception as e:
            logger.error(f"❌ RAG init failed: {e}")
            self.qa_chain = None
            self.retriever = None

    # =========================
    # Query RAG
    # =========================
    def query(self, text: str, user_id: str):
        try:
            if not self.qa_chain:
                return "System not ready"

            memory = self.get_memory(user_id)

            # 1) Detect language
            source_lang = self.translator.detect_lang(text)
            logger.info(f"🌍 Detected Language: {source_lang}")

            original_text = text

            # 2) Translate to English if needed
            if source_lang != "en":
                text = self.translator.translate(text, source_lang, "en")

            text = text.lower().strip()
            logger.info(f"🔄 Query (EN): {text}")

            # 3) Debug retrieval
            try:
                docs = self.retriever.invoke(text)

                logger.info("🔍 Retrieved Docs:")
                for i, d in enumerate(docs):
                    logger.info(f"--- Doc {i+1} ---")
                    logger.info(d.page_content[:300])

            except Exception as retrieval_error:
                logger.warning(f"⚠️ Retrieval debug failed: {retrieval_error}")

            # 4) Ask LLM
            response = self.qa_chain.invoke({
                "question": text,
                "chat_history": memory.chat_memory.messages
            })

            answer = response["answer"].strip()
            logger.info(f"🤖 English Answer: {answer}")

            # 5) Translate back to original language
            if source_lang != "en":
                answer = self.translator.translate(answer, "en", source_lang)

            logger.info(f"🌍 Final Answer: {answer}")

            # 6) Save conversation memory
            memory.chat_memory.add_user_message(original_text)
            memory.chat_memory.add_ai_message(answer)

            return answer

        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
            return "Error processing request"


# ================= GLOBAL RAG INSTANCE =================

rag_instance = None


def set_rag_instance(instance):
    global rag_instance
    rag_instance = instance


def query_rag(text: str, user_id: str):
    if rag_instance is None:
        return "System not ready"
    return rag_instance.query(text, user_id)