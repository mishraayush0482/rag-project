import os
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

from app.services.translation_service import TranslationService
from app.config import settings
from app.utils.loggers import logger


class RAGService:
    def __init__(self):
        self.translator = TranslationService()
        self.qa_chain = None
        self.user_memories = {}

    # ✅ Per-user memory
    def get_memory(self, user_id: str):
        if user_id not in self.user_memories:
            self.user_memories[user_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
        return self.user_memories[user_id]

    def initialize(self):
        try:
            logger.info("🚀 Initializing RAG service...")

            # =========================
            # 1) Load embeddings model
            # =========================
            # IMPORTANT:
            # Use the SAME embedding model/API that was used while creating faiss_index
            embeddings = OpenAIEmbeddings(
                api_key=settings.OPENAI_API_KEY
            )

            # =========================
            # 2) Load prebuilt FAISS index
            # =========================
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

            # =========================
            # 3) LLM (OpenRouter)
            # =========================
            llm = ChatOpenAI(
                model="meta-llama/llama-3-8b-instruct",
                openai_api_base="https://openrouter.ai/api/v1",
                openai_api_key=settings.OPENROUTER_API_KEY,
                temperature=0,
                request_timeout=30
            )

            # =========================
            # 4) Prompt template
            # =========================
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

            # =========================
            # 5) Retriever
            # =========================
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )

            # Save retriever separately for debug use
            self.retriever = retriever

            # =========================
            # 6) Conversational RAG chain
            # =========================
            self.qa_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                combine_docs_chain_kwargs={"prompt": PROMPT},
                return_source_documents=False
            )

            logger.info("✅ RAG initialized successfully")
            logger.info(f"OPENAI KEY PRESENT: {bool(settings.OPENAI_API_KEY)}")
        except Exception as e:
            logger.error(f"❌ RAG init failed: {e}")
            self.qa_chain = None

    # ✅ Query (multilingual)
    def query(self, text: str, user_id: str):
        try:
            if not self.qa_chain:
                return "System not ready"

            memory = self.get_memory(user_id)

            # =========================
            # 1) Detect language
            # =========================
            source_lang = self.translator.detect_lang(text)
            print(f"\n🌍 Detected Language: {source_lang}")

            original_text = text

            # =========================
            # 2) Translate to English if needed
            # =========================
            if source_lang != "en":
                text = self.translator.translate(text, source_lang, "en")

            text = text.lower().strip()
            print(f"🔄 Query (EN): {text}")

            # =========================
            # 3) Debug retrieval
            # =========================
            try:
                docs = self.retriever.invoke(text)

                print("\n🔍 Retrieved Docs:\n")
                for i, d in enumerate(docs):
                    print(f"--- Doc {i+1} ---")
                    print(d.page_content[:300])
                    print()
            except Exception as retrieval_error:
                print(f"⚠️ Retrieval debug failed: {retrieval_error}")

            # =========================
            # 4) Ask LLM
            # =========================
            response = self.qa_chain.invoke({
                "question": text,
                "chat_history": memory.chat_memory.messages
            })

            answer = response["answer"].strip()
            print("\n🤖 English Answer:", answer)

            # =========================
            # 5) Translate back to original language
            # =========================
            if source_lang != "en":
                answer = self.translator.translate(answer, "en", source_lang)

            print("\n🌍 Final Answer:", answer)

            # =========================
            # 6) Save conversation memory
            # =========================
            memory.chat_memory.add_user_message(original_text)
            memory.chat_memory.add_ai_message(answer)

            return answer

        except Exception as e:
            print(f"❌ Query failed: {e}")
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