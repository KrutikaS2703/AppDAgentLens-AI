# RAG (Retrieval Augmented Generation) System Setup

## Architecture

The RAG system uses vector embeddings to intelligently retrieve relevant AppDynamics documentation based on parsed analysis data.

### Flow:
```
User uploads agent.log files
        ↓
Parsers extract structured data (BCT, BT, Agent analysis)
        ↓
System identifies issues (no interceptors, high drops, errors, etc.)
        ↓
Vector DB queries with identified issues
        ↓
Retrieves relevant AppDynamics documentation
        ↓
Send: [Parsed Analysis] + [Retrieved Documentation] → LLM
        ↓
LLM provides intelligent contextual answer
```

## Installation

### Required Packages

```bash
pip install sentence-transformers
```

### LLM Provider (Groq)

The response generation layer uses Groq.

Set the following environment variables before running the app:

```bash
export ENABLE_GROQ="true"
export GROQ_API_KEY="your_groq_api_key"
export GROQ_MODEL="llama-3.3-70b-versatile"
```

- Set a valid `GROQ_API_KEY` before starting the app.

### What it does:
- **sentence-transformers**: Provides embeddings for semantic similarity search
- Uses the "all-MiniLM-L6-v2" model by default (small, fast, CPU-friendly ~90MB)
- Automatically downloads the model on first use

### Optional: GPU Support

For faster embeddings with CUDA GPU:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## Knowledge Base

### Backend KB (Generic Documentation)

KB documents are defined in `ai/kb_seed.py` and include:
- BCT (Bytecode Transformation) best practices
- BT (Business Transaction) troubleshooting
- Agent configuration and controller connectivity
- JMX/MBean permission issues
- Kafka instrumentation
- JVM memory configuration
- Error recovery procedures

### Initialization

The KB is automatically initialized on first chatbot use:
```python
from ai.kb_seed import initialize_kb
initialize_kb()  # Loads KB into vector DB, one-time idempotent operation
```

### Storage

Vector DB documents and embeddings are stored in:
```
./kb_data/documents.json
```

This persists across sessions.

## Adding Custom Documentation

To add your own AppDynamics documentation or best practices:

1. Edit `ai/kb_seed.py`
2. Add to the `KB_DOCUMENTS` dictionary:

```python
KB_DOCUMENTS = {
    "your_doc_id": {
        "content": "Your documentation text here...",
        "category": "category_type"  # e.g., "bct-guide", "error-resolution", "controller-config"
    },
    # ... more docs
}
```

3. Categories can be: `bct-guide`, `bt-guide`, `controller-config`, `error-resolution`, `jvm-guide`, or `general`

## Smart Query Matching

The system automatically builds queries based on detected issues:

| Detected Issue | KB Query |
|---|---|
| No interceptors applied | BCT no interceptors applied |
| High BT drop rate (>10%) | Business transaction high drop rate |
| Controller timeout errors | Agent controller connection timeout |
| JMX permission denied | Agent JMX MBean permission |
| Kafka instrumentation errors | Kafka instrumentation error |
| >50 ERROR lines | Agent errors critical error recovery |

## Fallback Mode

If `sentence-transformers` is not installed:
- The system still functions for chatting
- KB documents are loaded but without vector embeddings
- Semantic search will not work
- Consider installing the dependency for full RAG capabilities

## Performance

- First use: ~2-3 seconds (model download + KB initialization + embedding computation)
- Subsequent uses: <1 second (KB cached, embeddings precomputed)
- LLM query time depends on model size and network latency to Groq endpoints

## Customization

### Change Embedding Model

In `ai/rag.py`, modify:
```python
def __init__(self, kb_dir: str = "./kb_data", model_name: str = "all-MiniLM-L6-v2"):
    # Change model_name to different sentence-transformers model
    # e.g., "all-mpnet-base-v2" (larger, more accurate but slower)
```

### Change KB Retrieval Count

In `ai/chatbot.py`, modify in `ask_chatbot()`:
```python
docs = db.retrieve(query, top_k=3)  # Change 3 to desired number
```

