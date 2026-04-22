to start the App:
python3 -m streamlit run ui/app.py

## AI Provider Setup (AWS Bedrock -> Groq)

This project uses Amazon Bedrock as the primary provider and Groq as fallback.

### 1) Configure AWS credentials for Bedrock

- Install AWS CLI and authenticate: aws login
- Or configure credentials manually: aws configure
- Ensure the IAM identity used by the app can call Bedrock runtime APIs.

### 2) Export required environment variables

```bash
export ENABLE_BEDROCK="true"
export BEDROCK_REGION="ap-south-1"
export BEDROCK_MODEL="apac.anthropic.claude-3-5-sonnet-20241022-v2:0"

export ENABLE_GROQ="true"
export GROQ_API_KEY="your_groq_api_key"
export GROQ_MODEL="llama-3.3-70b-versatile"
```

Notes:
- Bedrock uses IAM credentials, not a separate API token.
- In this account/region, Anthropic must be invoked via inference profile IDs.
- Groq is used only if Bedrock fails.

### 3) Run the app

```bash
python3 -m streamlit run ui/app.py
```