# AgentLens AI

## AI-Powered Java Agent Log Analyzer

AgentLens AI is an intelligent troubleshooting platform designed to automate the analysis of AppDynamics Java Agent logs using Artificial Intelligence. The platform combines automated log parsing, issue detection, and Large Language Models (LLMs) to help support engineers quickly identify instrumentation, configuration, and startup issues without manually reviewing thousands of log lines.

Built using Python, Streamlit, and Ollama, AgentLens AI transforms raw Java Agent logs into actionable diagnostics, reducing investigation time and accelerating root cause analysis.

---

## Problem Statement

Troubleshooting Java Agent issues often requires engineers to manually analyze large log files to identify:

* Agent startup failures
* Controller connectivity issues
* Instrumentation failures
* Configuration errors
* JVM compatibility problems
* License and authentication issues

This process can be time-consuming and heavily dependent on domain expertise.

AgentLens AI was created to simplify and automate this process using AI-driven diagnostics.

---

## Key Features

### Intelligent Log Parsing

* Automatically processes Java Agent logs
* Extracts relevant errors, warnings, and configuration details
* Detects known failure patterns

### AI-Powered Analysis

* Uses local LLMs via Ollama
* Generates human-readable troubleshooting insights
* Provides potential root causes and recommendations

### Issue Classification

Automatically identifies:

* Agent registration failures
* SSL and connectivity issues
* Instrumentation problems
* Controller communication errors
* Configuration mismatches
* Unsupported JVM versions

### Interactive Dashboard

* Built with Streamlit
* Easy log upload and analysis
* Visual presentation of findings
* Faster troubleshooting workflow

### Privacy Friendly

* Uses locally hosted LLMs through Ollama
* No log data sent to external AI services

---

## Technology Stack

| Component      | Technology                    |
| -------------- | ----------------------------- |
| Frontend       | Streamlit                     |
| Backend        | Python                        |
| AI Engine      | Ollama                        |
| Log Processing | Python Regex & Parsing Engine |
| Visualization  | Streamlit Components          |
| Deployment     | AWS                           |

---

## Solution Architecture

```text
Java Agent Log
       |
       v
Log Parser Engine
       |
       v
Issue Detection Layer
       |
       v
LLM Analysis (Ollama)
       |
       v
Root Cause Suggestions
       |
       v
Streamlit Dashboard
```

---

## Benefits

* Reduces manual log analysis effort
* Accelerates root cause analysis (RCA)
* Improves troubleshooting consistency
* Helps engineers identify issues faster
* Reduces dependency on deep product expertise

---

## Impact

* Reduced troubleshooting effort by approximately 50%
* Accelerated Java Agent issue identification
* Improved support engineer productivity
* Demonstrated globally as an AI-driven observability initiative

---

## Future Enhancements

* Multi-log correlation
* Automated remediation recommendations
* Support for machine agents and database agents
* Integration with AppDynamics Controller APIs
* RAG-based knowledge base integration
* Support for OpenTelemetry diagnostics

---

## Use Cases

### Support Engineers

Quickly identify Java Agent deployment and instrumentation issues.

### Observability Teams

Analyze agent health and configuration problems at scale.

### DevOps Engineers

Validate monitoring agent installations across environments.

### Platform Teams

Reduce mean time to resolution (MTTR) through AI-assisted diagnostics.

---
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
### Deployed on AWS 
Link to access: http://agentlens-ai-alb-1978754015.ap-south-1.elb.amazonaws.com/

## Author

**Krutika Sakharwade**

Software Consulting Engineering Technical Leader
Cisco Splunk AppDynamics

Passionate about Observability, AI Automation, Java Diagnostics, and Developer Productivity.

<img width="1728" height="969" alt="Screenshot 2026-06-18 at 11 49 41 AM" src="https://github.com/user-attachments/assets/9f1206df-7ac2-4ff4-8929-440b115007ba" />

<img width="1727" height="958" alt="Screenshot 2026-06-18 at 11 50 05 AM" src="https://github.com/user-attachments/assets/6490aa73-dde6-4bb6-bdc9-6fcf4b57ca5a" />

<img width="1727" height="962" alt="Screenshot 2026-06-18 at 11 50 50 AM" src="https://github.com/user-attachments/assets/cd028fe3-2510-4f83-82f7-7d5ec29cd52c" />

<img width="1727" height="965" alt="Screenshot 2026-06-18 at 11 51 41 AM" src="https://github.com/user-attachments/assets/297e34db-b416-4a59-b835-1395e5b3e1ac" />

<img width="1386" height="924" alt="Screenshot 2026-06-18 at 11 51 24 AM" src="https://github.com/user-attachments/assets/69bf2512-8ae3-4b8f-ae86-832d71c7c96c" />

<img width="1728" height="969" alt="Screenshot 2026-06-18 at 11 52 30 AM" src="https://github.com/user-attachments/assets/8ef283b8-7c94-4ffd-b7d1-c083753f73ff" />

<img width="1728" height="963" alt="Screenshot 2026-06-18 at 11 53 15 AM" src="https://github.com/user-attachments/assets/0f7240e6-3ba9-4574-bd8b-1fa535296b45" />

<img width="1726" height="967" alt="Screenshot 2026-06-18 at 11 55 02 AM" src="https://github.com/user-attachments/assets/6a6afc37-50dc-4369-a72c-d4c3f282e0f7" />

<img width="1726" height="968" alt="Screenshot 2026-06-18 at 11 55 40 AM" src="https://github.com/user-attachments/assets/96900a60-2de7-4093-97e6-a33400c163fb" />




