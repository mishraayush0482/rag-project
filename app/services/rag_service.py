import os

from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.services.translation_service import TranslationService
from app.config import settings
from app.utils.loggers import logger


class RAGService:
    def __init__(self):
        self.translator = TranslationService()
        self.qa_chain = None
        self.user_memories = {}

        # Paths
        self.knowledge_file = "knowledge/data.txt"
        self.vector_db_path = "knowledge/faiss_index"

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

            # ---------------------------------------------------
            # 1) Use OpenAI embeddings instead of HuggingFace
            #    This prevents Render OOM caused by loading
            #    sentence-transformers/all-MiniLM-L6-v2
            # ---------------------------------------------------
            embeddings = OpenAIEmbeddings(
                api_key=settings.OPENAI_API_KEY
            )

            # ---------------------------------------------------
            # 2) Load existing FAISS vector store if already built
            # ---------------------------------------------------
            if os.path.exists(self.vector_db_path):
                logger.info(f"📦 Loading existing vector DB from: {self.vector_db_path}")

                vector_store = FAISS.load_local(
                    self.vector_db_path,
                    embeddings,
                    allow_dangerous_deserialization=True
                )

                logger.info("✅ Existing FAISS vector DB loaded successfully")

            else:
                logger.info("📄 No FAISS index found. Building a new one...")

                # Load documents
                loader = TextLoader(self.knowledge_file, encoding="utf-8")
                docs = loader.load()

                print("\n✅ Loaded Documents:")
                for d in docs:
                    print(d.page_content[:200])

                # Chunking
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=500,
                    chunk_overlap=100
                )
                chunks = splitter.split_documents(docs)

                print(f"\n✅ Total Chunks Created: {len(chunks)}")

                # Create vector store
                vector_store = FAISS.from_documents(chunks, embeddings)

                # Save vector store locally
                vector_store.save_local(self.vector_db_path)
                logger.info(f"✅ New FAISS vector DB created and saved to: {self.vector_db_path}")

            # ---------------------------------------------------
            # 3) LLM (OpenRouter)
            # ---------------------------------------------------
            llm = ChatOpenAI(
                model="meta-llama/llama-3-8b-instruct",
                openai_api_base="https://openrouter.ai/api/v1",
                openai_api_key=settings.OPENROUTER_API_KEY,
                temperature=0,
                request_timeout=30
            )

            # ---------------------------------------------------
            # 4) Prompt
            # ---------------------------------------------------
            prompt_template = """
You are a helpful AI assistant.

Answer ONLY using the given context.
If answer is partially available, still answer.
Do NOT hallucinate.
If the answer is not present in the context, say clearly that the information is not available in the knowledge base.

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

            # ---------------------------------------------------
            # 5) Retriever
            # ---------------------------------------------------
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )

            # ---------------------------------------------------
            # 6) Conversational RAG Chain
            # ---------------------------------------------------
            self.qa_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                combine_docs_chain_kwargs={"prompt": PROMPT},
                return_source_documents=False,
            )

            logger.info("✅ RAG initialized successfully")

        except Exception as e:
            logger.exception(f"❌ RAG init failed: {e}")
            self.qa_chain = None

    # ✅ Query (MULTILINGUAL FIXED)
    def query(self, text: str, user_id: str):
        try:
            if not self.qa_chain:
                return "System not ready"

            memory = self.get_memory(user_id)

            # 🌍 Detect language
            source_lang = self.translator.detect_lang(text)
            print(f"\n🌍 Detected Language: {source_lang}")

            original_text = text

            # 🔄 Convert ANY language → English
            if source_lang != "en":
                text = self.translator.translate(text, source_lang, "en")

            text = text.lower().strip()
            print(f"🔄 Query (EN): {text}")

            # 🔍 Debug retrieval
            docs = self.qa_chain.retriever.invoke(text)

            print("\n🔍 Retrieved Docs:\n")
            for i, d in enumerate(docs):
                print(f"--- Doc {i+1} ---")
                print(d.page_content[:300])
                print()

            # 🤖 Ask LLM
            response = self.qa_chain.invoke({
                "question": text,
                "chat_history": memory.chat_memory.messages
            })

            answer = response["answer"]
            print("\n🤖 English Answer:", answer)

            # 🌍 Convert back to ORIGINAL language
            if source_lang != "en":
                answer = self.translator.translate(answer, "en", source_lang)

            print("\n🌍 Final Answer:", answer)

            # 💾 Save memory
            memory.chat_memory.add_user_message(original_text)
            memory.chat_memory.add_ai_message(answer)

            return answer

        except Exception as e:
            logger.exception(f"❌ Query failed: {e}")
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