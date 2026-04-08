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

    # ✅ Better language detection
    def detect_lang(self, text: str) -> str:
        try:
            # Detect Hindi script
            if any("\u0900" <= c <= "\u097F" for c in text):
                return "hi"

            lang = detect(text)

            # ❗ Fix wrong detection (like "so", "af", etc.)
            if lang not in ["en", "hi"]:
                return "en"

            return lang
        except:
            return "en"

    # ✅ Safe translation (ONLY when needed)
    def translate(self, text: str, source="en", target="en"):
        if not text.strip() or source == target:
            return text

        try:
            prompt = f"""
Translate the text strictly from {source} to {target}.
Only return translated text. No explanation.

Text:
{text}
"""
            response = self.llm.invoke(prompt)
            return response.content.strip()

        except Exception as e:
            print(f"❌ Translation error: {e}")
            return text

    # ✅ Hinglish → English (ONLY when needed)
    def hinglish_to_english(self, text: str):
        try:
            prompt = f"""
Convert the following Hinglish/Hindi text into clear English.
Do not add anything extra.

Text:
{text}
"""
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            print(f"❌ Hinglish conversion error: {e}")
            return text

    def english_to_hindi(self, text: str):
        return self.translate(text, "en", "hi")