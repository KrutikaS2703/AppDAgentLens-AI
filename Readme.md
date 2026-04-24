to start the App:
python3 -m streamlit run ui/app.py

## AI Provider Setup (Groq)

This project uses Groq as the LLM provider.

### 1) Export required environment variables

```bash
export ENABLE_GROQ="true"
export GROQ_API_KEY="your_groq_api_key"
export GROQ_MODEL="llama-3.3-70b-versatile"
```

Notes:
- Set a valid `GROQ_API_KEY` before starting the app.

### 2) Run the app

```bash
python3 -m streamlit run ui/app.py
```