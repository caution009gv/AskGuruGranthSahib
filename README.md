# ☬ AskGuruGranthSahib

**AI-powered Q&A assistant based on Sri Guru Granth Sahib Ji**

Ask questions about the sacred scripture and receive answers grounded in Gurbani, with references to specific Angs (pages).

---

## 🏗️ Architecture

```
AskGuruGranthSahib/
├── HolyScripture/
│   └── SGGS-Eng.pdf        # Sri Guru Granth Sahib English Translation
├── backend/
│   ├── app.py              # FastAPI server
│   ├── ingest.py           # PDF → ChromaDB ingestion pipeline
│   ├── rag_engine.py       # RAG query engine (OpenAI + ChromaDB)
│   ├── requirements.txt    # Python dependencies
│   ├── .env                # API keys
│   └── data/
│       └── chroma_db/      # Auto-generated vector store
├── frontend/
│   ├── index.html          # Chat UI
│   ├── style.css           # Styling
│   └── script.js           # Frontend logic
└── README.md
```

## 🚀 Setup & Run

### Prerequisites
- Python 3.10+
- An OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### Step 1: Install Dependencies

```bash
cd AskGuruGranthSahib/backend
pip install -r requirements.txt
```

### Step 2: Configure API Key

```bash
# Create .env file from template
copy .env.example .env
# Edit .env and add your OpenAI API key
```

### Step 3: Ingest the PDF

Place your Sri Guru Granth Sahib PDF in `backend/data/sggs.pdf`, then run:

```bash
python ingest.py
# Or specify a custom path:
python ingest.py "C:\path\to\your\sggs.pdf"
```

This will:
- Extract text from all 1430 pages
- Split into overlapping chunks
- Generate embeddings via OpenAI
- Store in local ChromaDB

### Step 4: Start the Server

```bash
python app.py
```

Open your browser to **http://localhost:8000** 🙏

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Python |
| LLM | OpenAI GPT-4o |
| Embeddings | text-embedding-3-small |
| Vector DB | ChromaDB (local) |
| RAG Framework | LangChain |
| Frontend | Vanilla HTML/CSS/JS |

---

## 📝 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ask` | Ask a question |
| POST | `/api/reset` | Reset conversation history |
| GET | `/api/stats` | Get knowledge base stats |

---

## 🙏 Acknowledgement

This project is built with deep reverence for Sri Guru Granth Sahib Ji, the eternal Guru.
The AI responses are generated based on the text and should always be verified with the original scripture.

> ੴ ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ ਨਿਰਭਉ ਨਿਰਵੈਰੁ ਅਕਾਲ ਮੂਰਤਿ ਅਜੂਨੀ ਸੈਭੰ ਗੁਰ ਪ੍ਰਸਾਦਿ ॥
