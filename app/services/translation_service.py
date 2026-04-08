from langdetect import detect
from langchain_community.chat_models import ChatOpenAI
from app.config import settings


class TranslationService:

    def __init__(self):
        self.llm = ChatOpenAI(
            model="meta-llama/llama-3-8b-instruct",
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=settings.OPENROUTER_API_KEY,
            temperature=0,
            request_timeout=30
        )

    # ✅ Improved language detection (supports Bangla, Hindi, etc.)
    def detect_lang(self, text: str) -> str:
        try:
            lang = detect(text)

            # Normalize common codes
            if lang.startswith("en"):
                return "en"
            if lang.startswith("hi"):
                return "hi"
            if lang.startswith("bn"):
                return "bn"

            return lang  # allow all languages

        except:
            return "en"

    # ✅ Universal translation
    def translate(self, text: str, source="en", target="en"):
        if not text.strip() or source == target:
            return text

        try:
            prompt = f"""
Translate the following text from {source} to {target}.
Return ONLY the translated text. No explanation.

Text:
{text}
"""
            response = self.llm.invoke(prompt)
            return response.content.strip()

        except Exception as e:
            print(f"❌ Translation error: {e}")
            return text