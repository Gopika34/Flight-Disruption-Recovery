# Flight Disruption Recovery Engine

**An AI-powered, regulation-grounded decision-support platform for flight disruption assistance under Indian DGCA guidelines.**

The Flight Disruption Recovery Engine helps passengers understand their potential rights and recovery options when affected by flight delays, cancellations, denied boarding, downgrades, and other disruptions.

Built using **React, FastAPI, MongoDB Atlas Vector Search, Retrieval-Augmented Generation (RAG), and deterministic rule evaluation**, the platform combines regulatory evidence with structured decision logic and LLM-powered conversational assistance.

The system is designed around one core principle:

> **The rule engine determines outcomes. The LLM explains them.**

---

## Live Application

| Component | Link |
|---|---|
| Frontend | [Flight Disruption Recovery](https://flight-disruption-recovery.vercel.app/) |
| Backend API | [Flight Disruption Recovery API](https://flight-disruption-recovery.onrender.com) |
| API Documentation | [Interactive Swagger Documentation](https://flight-disruption-recovery.onrender.com/docs) |
| Source Code | [GitHub Repository](https://github.com/Gopika34/Flight-Disruption-Recovery) |

**Disclaimer:** This platform provides regulatory information and decision support. It does not perform flight bookings, guarantee compensation, or replace official airline or regulatory decisions.

---

## Problem Statement

Passengers experiencing flight disruptions often struggle to identify the regulations applicable to their situation, understand eligibility conditions, and determine what assistance or recovery options may be available.

Regulatory documents are extensive, and interpreting them requires connecting specific passenger circumstances with the relevant provisions and conditions.

This project addresses that challenge through a system that:

- Interprets natural-language descriptions of flight disruptions.
- Retrieves relevant DGCA regulatory provisions using semantic search.
- Evaluates eligibility through deterministic business rules.
- Uses LLMs to explain structured outcomes and supporting policy evidence.
- Supports contextual conversations and real-time response streaming.

## Core Features

### 1. Regulation-Grounded RAG Pipeline

- Processes DGCA Civil Aviation Requirements (CAR) into structured policy chunks.
- Generates semantic embeddings using the Gemini Embedding API.
- Stores policy representations in MongoDB Atlas.
- Retrieves relevant regulatory provisions through Atlas Vector Search.
- Supplies retrieved policy evidence to the response-generation pipeline.

### 2. Deterministic Regulatory Rule Engine

- Evaluates supported flight disruption scenarios against structured regulatory conditions.
- Separates eligibility evaluation from language generation.
- Produces structured evaluation results.
- Prevents the LLM from independently determining regulatory outcomes or compensation amounts.
- Supports explainable decision-making through rule-based evaluation.

### 3. Conversational AI Assistant

- Accepts passenger scenarios in natural language.
- Extracts relevant flight and disruption details.
- Maintains session context across follow-up interactions.
- Requests additional information when required.
- Generates policy-grounded explanations.
- Streams responses using Server-Sent Events (SSE).

### 4. Multi-Provider LLM Orchestration

- Integrates Gemini, Groq, and Mistral providers.
- Uses a centralized LLM routing layer.
- Supports provider fallback mechanisms.
- Implements retry handling with jitter for transient failures.
- Separates provider-specific integrations from application logic.

### 5. Flight Recovery Guidance

- Evaluates passenger scenarios using retrieved policy evidence and structured rules.
- Presents applicable regulatory considerations.
- Explains potential assistance and recovery options.
- Distinguishes verified rule-engine outcomes from general AI-generated guidance.

### 6. Backend Reliability and Testing

- Modular FastAPI application architecture.
- MongoDB Atlas integration.
- Health and readiness endpoints.
- Automated testing with Pytest.
- Structured API responses and streaming endpoints.
- Separation of API, business logic, retrieval, database, and LLM components.

---

## System Architecture

```text
                 PASSENGER
                     |
                     v
          REACT + TAILWIND FRONTEND
                     |
                     v
                  FASTAPI
                     |
             SESSION MANAGEMENT
                     |
                     v
              QUERY PROCESSING
                     |
          +----------+----------+
          |                     |
          v                     v
     RAG RETRIEVAL          RULE ENGINE
          |                     |
          v                     |
    QUERY EMBEDDING              |
          |                     |
          v                     |
   MONGODB ATLAS                 |
   VECTOR SEARCH                |
          |                     |
          v                     |
   POLICY EVIDENCE               |
          |                     |
          +----------+----------+
                     |
                     v
                 LLM ROUTER
                     |
          +----------+----------+
          |          |          |
          v          v          v
        GEMINI      GROQ      MISTRAL
          |          |          |
          +----------+----------+
                     |
                     v
            RESPONSE GENERATION
                     |
                     v
               SSE STREAMING
                     |
                     v
             REACT CHAT INTERFACE
```

### Architectural Principle

**Deterministic decisions, probabilistic explanations.**

The rule engine evaluates structured regulatory conditions independently. The RAG pipeline retrieves supporting policy evidence, while the LLM converts the resulting information into understandable conversational guidance.

This separation reduces reliance on unconstrained language-model reasoning for regulatory eligibility decisions.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React.js, JavaScript, Tailwind CSS |
| Backend | Python, FastAPI |
| Database | MongoDB Atlas |
| Vector Database / Search | MongoDB Atlas Vector Search |
| Embeddings | Gemini Embedding API |
| LLM Providers | Gemini, Groq, Mistral |
| AI Architecture | Retrieval-Augmented Generation (RAG) |
| Response Streaming | Server-Sent Events (SSE) |
| Testing | Pytest |
| Backend Deployment | Render |
| Frontend Deployment | [Update after deployment] |

---

## Repository Structure

```text
Flight-Disruption-Recovery/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── llm/
│   │   ├── rag/
│   │   ├── rules/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── scripts/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── index.html
│
└── README.md
```

*This is a high-level representation of the repository. Individual modules contain the implementation details.*

---


## Application Screenshots

Explore the key interfaces of the Flight Disruption Recovery Engine, from flight disruption assessment to AI-powered passenger assistance.

### Landing Page

<p align="center">
  <img src="screenshots/landing-page.png" alt="Flight Disruption Recovery landing page" width="100%" />
</p>

### Platform Overview

<table>
  <tr>
    <td width="50%">
      <h4 align="center">Flight Disruption Dashboard</h4>
      <img src="screenshots/flight-disruption-dashboard.png" alt="Flight disruption dashboard" width="100%" />
      <p align="center">Centralized dashboard for flight disruption assistance.</p>
    </td>
    <td width="50%">
      <h4 align="center">AI Flight Assistant</h4>
      <img src="screenshots/ai-assistant.png" alt="AI flight assistant" width="100%" />
      <p align="center">Conversational AI interface for passenger queries.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h4 align="center">Disruption Evaluation</h4>
      <img src="screenshots/evalute-disruption.png" alt="Flight disruption evaluation interface" width="100%" />
      <p align="center">Evaluate disruption details and applicable passenger entitlements.</p>
    </td>
    <td width="50%">
      <h4 align="center">Alternative Flight Options</h4>
      <img src="screenshots/alternative-live-flight.png" alt="Alternative live flight options" width="100%" />
      <p align="center">Explore alternative flight and recovery options.</p>
    </td>
  </tr>
  <tr>
    <td colspan="2">
      <h4 align="center">DGCA Regulatory Reference</h4>
      <p align="center">
        <img src="screenshots/DGCA-regulations.png" alt="DGCA regulations interface" width="75%" />
      </p>
      <p align="center">Access aviation regulatory information supporting policy-grounded guidance.</p>
    </td>
  </tr>
</table>

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js and npm
- MongoDB Atlas account
- Gemini API credentials
- Optional Groq and Mistral API credentials

### 1. Clone the repository

```bash
git clone https://github.com/Gopika34/Flight-Disruption-Recovery.git

cd Flight-Disruption-Recovery
```

### 2. Configure the backend

```bash
cd backend

python -m venv venv
```

Activate the virtual environment.

**Windows:**

```powershell
venv\Scripts\activate
```

**macOS/Linux:**

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file using `.env.example` as a reference.

```env
MONGO_URL=your_mongodb_connection_string
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
MISTRAL_API_KEY=your_mistral_api_key
```

Configure the remaining environment variables required by the application.

Start the backend:

```bash
uvicorn app.main:app --reload
```

Backend: `http://127.0.0.1:8000`

API documentation: `http://127.0.0.1:8000/docs`

### 3. Configure the frontend

Open a separate terminal:

```bash
cd frontend

npm install
```

Configure the frontend environment variable for the backend API according to the application's configuration.

Start the development server:

```bash
npm run dev
```

Build for production:

```bash
npm run build
```

---

## API Reference

The backend exposes the following primary endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health/live` | Application liveness check |
| GET | `/health/ready` | Dependency readiness check |
| GET | `/search` | Regulatory policy retrieval |
| GET | `/flights/{flight_number}` | Flight information lookup |
| POST | `/evaluate` | Deterministic rule evaluation |
| POST | `/recover` | Flight recovery assistance |
| POST | `/ask` | Conversational AI interaction |
| POST | `/ask/stream` | Streaming conversational response |

Refer to the [Swagger API documentation](https://flight-disruption-recovery.onrender.com/docs) for request schemas, response formats, and endpoint details.

---

## Testing and Validation

The backend includes automated tests covering regulatory rules, policy processing, and application components.

Run the test suite:

```bash
python -m compileall -q app tests scripts

python -m pytest -q
```

The latest recorded test run:

- **141 passed**
- **1 skipped**
- **22 deselected**
- **2 warnings**

These results reflect the recorded test run and may change as the project evolves.

---

## Deployment Architecture

The application uses independently deployed frontend and backend services.

| Component | Platform |
|---|---|
| Frontend | [Update with actual hosting platform] |
| Backend API | Render |
| Database | MongoDB Atlas |

The frontend communicates with the backend through configured API endpoints, including the streaming response interface.

Production credentials and API keys are managed through environment variables and must not be committed to source control.

---

## Regulatory Reference

**Directorate General of Civil Aviation (DGCA)**

Civil Aviation Requirements (CAR), Section 3 – Air Transport, Series M, Part IV, Revision 4.

Effective date: 15 February 2023.

The regulatory document serves as the policy knowledge base for the implemented rules. Regulatory applicability should be validated against the latest official requirements before relying on any guidance.

---

## Future Enhancements

- Expanded regulatory coverage and automated policy updates.
- Integration with verified real-time flight information sources.
- Enhanced passenger recovery workflows.
- Passenger document ingestion and extraction.
- Multilingual conversational assistance.
- Retrieval quality evaluation and observability.
- Improved production monitoring and error analytics.

---

## Author

**Gopika S.**

B.Tech – Artificial Intelligence and Data Science, 2026

Full-Stack Developer | AI & RAG Systems

- **GitHub:** [Gopika34](https://github.com/Gopika34)
- **LinkedIn:** [Gopika S.](https://www.linkedin.com/in/gopika-s-2501b0244/)

---