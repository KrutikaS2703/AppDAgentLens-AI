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

* Uses local LLMs via Groq
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

* No log data sent to external AI services
* Data is preserved only for a session and then deleted

---

## Technology Stack

| Component      | Technology                    |
| -------------- | ----------------------------- |
| Frontend       | Streamlit                     |
| Backend        | Python                        |
| AI Engine      | Groq, RAG                     |
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

<img width="1728" height="969" alt="sc1" src="https://github.com/user-attachments/assets/6c8a4072-60f2-4e42-83ec-2ec2e18718ab" />
<img width="1727" height="958" alt="sc2" src="https://github.com/user-attachments/assets/73401821-6526-4f62-9611-c846a93974a1" />
<img width="1727" height="962" alt="sc3" src="https://github.com/user-attachments/assets/1a0c95f9-1a02-42c4-bf9b-55024acbe88c" />
<img width="1727" height="965" alt="sc4" src="https://github.com/user-attachments/assets/e4e55b6a-6fdb-4c8a-abe2-20de6130193c" />
<img width="1386" height="924" alt="sc5" src="https://github.com/user-attachments/assets/963b933d-38eb-4e6f-8c35-9cc454b12522" />
<img width="1728" height="969" alt="sc6" src="https://github.com/user-attachments/assets/0194469c-67bd-476f-9e18-f2a32c927773" />
<img width="1728" height="963" alt="sc7" src="https://github.com/user-attachments/assets/499472a4-ebe3-4e0c-be68-db457b4380b9" />
<img width="1726" height="967" alt="sc8" src="https://github.com/user-attachments/assets/88522884-03cd-4d50-916e-bef13af3d775" />
<img width="1726" height="968" alt="sc9" src="https://github.com/user-attachments/assets/74ea1613-d6e7-491a-9a4b-a9bb85239eb2" />

