from langdetect import detect_langs, DetectorFactory
from langchain_openai import ChatOpenAI
from app.config import settings

# ✅ Make detection deterministic
DetectorFactory.seed = 0


class TranslationService:

    def __init__(self):

        # ✅ OpenRouter LLM
        self.llm = ChatOpenAI(
            model="meta-llama/llama-3.1-8b-instruct",
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=settings.OPENROUTER_API_KEY,
            temperature=0,
            request_timeout=60,
            max_tokens=1024
        )

        # ✅ Supported languages
        self.supported_languages = {
            "en": "English",
            "hi": "Hindi",
            "bn": "Bengali",
            "ta": "Tamil",
            "te": "Telugu",
            "ml": "Malayalam",
            "kn": "Kannada",
            "gu": "Gujarati",
            "mr": "Marathi",
            "pa": "Punjabi",
            "or": "Odia",
            "as": "Assamese",
            "ur": "Urdu",
            "ne": "Nepali",
            "sd": "Sindhi",
            "mai": "Maithili",
            "sa": "Sanskrit",
            "kok": "Konkani",
            "mni": "Manipuri",
            "brx": "Bodo",
            "doi": "Dogri",
            "sat": "Santali",
            "ks": "Kashmiri"
        }

    # ✅ Better language detection
    def detect_lang(self, text: str) -> str:

        # Empty text fallback
        if not text or not text.strip():
            return "en"

        # Very short text fallback
        if len(text.strip()) < 3:
            return "en"

        try:

            detections = detect_langs(text.strip())

            print(f"🌍 Raw detections: {detections}")

            best = detections[0]

            lang = best.lang
            confidence = best.prob

            print(f"🌍 Detected: {lang} ({confidence})")

            # ✅ Reject low confidence guesses
            if confidence < 0.80:
                return "en"

            # ✅ Normalize languages
            normalization_map = {
                "en": "en",
                "hi": "hi",
                "bn": "bn",
                "mr": "mr",
                "ta": "ta",
                "te": "te",
                "ml": "ml",
                "kn": "kn",
                "gu": "gu",
                "pa": "pa",
                "ur": "ur",
                "or": "or",
                "as": "as",
                "ne": "ne"
            }

            normalized_lang = normalization_map.get(lang, lang)

            # ✅ Reject unsupported languages
            if normalized_lang not in self.supported_languages:
                return "en"

            return normalized_lang

        except Exception as e:
            print(f"❌ Language detection error: {e}")
            return "en"

    # ✅ Universal translation
    def translate(self, text: str, source="en", target="en"):

        # Empty text
        if not text or not text.strip():
            return text

        # Same language
        if source == target:
            return text

        try:

            print(f"🌍 Source Lang: {source}")
            print(f"🌍 Target Lang: {target}")

            source_name = self.supported_languages.get(source, source)
            target_name = self.supported_languages.get(target, target)

            prompt = f"""
You are a professional multilingual translator.

Translate the given text from {source_name} to {target_name}.

Rules:
- Return ONLY translated text
- Preserve exact meaning
- Preserve formatting
- Preserve bullet points
- Preserve numbers and dates
- Preserve URLs and code blocks
- Do NOT explain anything
- Do NOT add extra words

Text:
{text}
"""

            response = self.llm.invoke(prompt)

            translated_text = response.content.strip()

            # ✅ Empty response fallback
            if not translated_text:
                return text

            return translated_text

        except Exception as e:
            print(f"❌ Translation error: {e}")
            return text