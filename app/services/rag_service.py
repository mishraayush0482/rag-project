from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_models import ChatOpenAI

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
            # ✅ Load documents
            loader = TextLoader("knowledge/data.txt", encoding="utf-8")
            docs = loader.load()

            print("\n✅ Loaded Documents:")
            for d in docs:
                print(d.page_content[:200])

            # ✅ Chunking
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=100
            )
            chunks = splitter.split_documents(docs)

            print(f"\n✅ Total Chunks Created: {len(chunks)}")

            # ✅ Embeddings
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )

            # ✅ Vector store
            vector_store = FAISS.from_documents(chunks, embeddings)

            # ✅ LLM (OpenRouter)
            llm = ChatOpenAI(
                model="meta-llama/llama-3-8b-instruct",
                openai_api_base="https://openrouter.ai/api/v1",
                openai_api_key=settings.OPENROUTER_API_KEY,
                temperature=0,
                request_timeout=30
            )

            # ✅ Strong prompt
            prompt_template = """
You are a helpful AI assistant.

Answer ONLY using the given context.
If answer is partially available, still answer.
Do NOT hallucinate.

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

            # ✅ Cleaner retriever (LESS NOISE)
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )

            # ✅ Build chain
            self.qa_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                combine_docs_chain_kwargs={"prompt": PROMPT},
                return_source_documents=False,
            )

            logger.info("✅ RAG initialized successfully")

        except Exception as e:
            logger.error(f"❌ RAG init failed: {e}")

    # ✅ Query
    def query(self, text: str, user_id: str):
        try:
            if not self.qa_chain:
                return "System not ready"

            memory = self.get_memory(user_id)

            # ✅ Detect language
            lang = self.translator.detect_lang(text)
            print(f"\n🌍 Detected Language: {lang}")

            original_text = text

            # ❗ ONLY translate if Hindi
            if lang == "hi":
                text = self.translator.hinglish_to_english(text)

            text = text.lower().strip()

            print(f"🔄 Query: {text}")

            # ✅ Debug retrieval
            docs = self.qa_chain.retriever.get_relevant_documents(text)

            print("\n🔍 Retrieved Docs:\n")
            for i, d in enumerate(docs):
                print(f"--- Doc {i+1} ---")
                print(d.page_content[:200])
                print()

            # ✅ Ask LLM
            response = self.qa_chain.invoke({
                "question": text,
                "chat_history": memory.chat_memory.messages
            })

            answer = response["answer"]
            print("\n🤖 English Answer:", answer)

            # ✅ Translate back if needed
            if lang == "hi":
                answer = self.translator.translate(answer, "en", "hi")

            print("\n🌍 Final Answer:", answer)

            # ✅ Save memory
            memory.chat_memory.add_user_message(original_text)
            memory.chat_memory.add_ai_message(answer)

            return answer

        except Exception as e:
            print(f"❌ Query failed: {e}")
            return "Error processing request"