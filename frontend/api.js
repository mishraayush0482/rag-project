(function () {
  const demoStore = {
    sessions: [
      {
        id: "chat-1",
        title: "Welcome query",
        updatedAt: new Date().toISOString(),
        messages: [
          {
            role: "assistant",
            content:
              "Hello. I can answer using your RAG knowledge base and keep the reply language aligned with the user query.",
          },
        ],
      },
    ],
  };

  const API_BASE_URL = window.API_BASE_URL || "https://rag-project-1-4mwz.onrender.com";

  async function request(path, options = {}) {
    if (!API_BASE_URL) return null;

    const headers = options.body instanceof FormData ? {} : { "Content-Type": "application/json" };
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        ...headers,
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed: ${response.status}`);
    }

    return response.status === 204 ? null : response.json();
  }

  function buildDemoAnswer(query) {
    const devanagari = /[\u0900-\u097F]/.test(query);
    const spanish = /[¿¡]|\b(hola|gracias|por favor)\b/i.test(query);
    const french = /\b(bonjour|merci|s'il vous plait)\b/i.test(query);

    if (devanagari) {
      return "यह डेमो उत्तर है। बैकएंड जुड़ने के बाद यही प्रश्न RAG पाइपलाइन में जाएगा और उत्तर इसी भाषा में लौटेगा।";
    }
    if (spanish) {
      return "Esta es una respuesta de demostracion. Cuando conectes el backend, la consulta ira al flujo RAG y la respuesta volvera en el mismo idioma.";
    }
    if (french) {
      return "Ceci est une reponse de demonstration. Une fois le backend connecte, la question passera par le pipeline RAG.";
    }
    return "This is a demo response. After the backend is connected, this query will be sent to your RAG service and saved to MongoDB chat history.";
  }

  window.ragApi = {
    async signup({ name, email, password }) {
      return request("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
      });
    },

    async login({ email, password }) {
      const result = await request("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      return { token: result.access_token, user: { name: result.name, email } };
    },

    async ask({ token, query }) {
      const result = await request("/chat", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message: query }),
      });
      return result.answer;
    },

    async uploadText({ title, text }) {
      const result = await request("/knowledge/text", {
        method: "POST",
        body: JSON.stringify({ title, text }),
      });

      return result || { status: "queued", chunks: Math.max(1, Math.ceil(text.length / 900)) };
    },

    async uploadPdf(file) {
      const formData = new FormData();
      formData.append("file", file);

      const result = await request("/knowledge/pdf", {
        method: "POST",
        body: formData,
      });

      return result || { status: "queued", fileName: file.name };
    },
  };
})();
