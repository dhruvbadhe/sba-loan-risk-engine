# 🏦 SBA 7(a) Loan Credit Risk Assessment Engine & Decoupled Underwriting Portal

A production-grade, secure, and decoupled machine learning microservice application designed for SBA 7(a) commercial loan officers. The system predicts loan default probabilities, calculates Basel-compliant financial expected loss metrics, logs detailed prediction audit trails to a cloud database, and provides real-time explainability using SHAP.

---

## 🔗 Live Deployments
*   **Frontend Dashboard (Streamlit Cloud):** [Live App Link](https://sba-loan-risk-engine-aszwcpfzqmdffrrr4uhvvr.streamlit.app/)
*   **Backend API Documentation (FastAPI on Render):** [Swagger Docs Link](https://sba-loan-risk-api.onrender.com/docs)

---

## 🏗️ System Architecture
The project is built using a decoupled **Microservice Architecture** that keeps the machine learning model isolated from the user interface:

```
               [ Streamlit Web Frontend ] 
                           │
           (1. Auth & Predict HTTP Requests)
                           ▼
              [ FastAPI Backend (Render) ]
                 ├── (2. JWT Token Auth)
                 ├── (3. HistGradientBoosting Pipeline)
                 ├── (4. Redis Cache / Failover) ──► [ Redis Instance ]
                 └── (5. Audit Trail Logs) ────────► [ Supabase PostgreSQL ]
```

1.  **Streamlit Frontend:** A lightweight, model-free user interface. It handles user authentication sessions, triggers predictions via API requests, and reconstructs explainability charts locally from returned JSON metadata.
2.  **FastAPI Backend Service:** Served from a Docker container. It hosts the machine learning pipeline, manages JWT lifecycles, runs the SHAP explanation engine, and coordinates logging operations.
3.  **Supabase PostgreSQL Database:** Stores encrypted user credentials (hashed with `bcrypt`) and logs prediction audit records.
4.  **Redis Cache:** Caches prediction inputs to prevent redundant calculations and ensure sub-millisecond response latency. Runs with a try/except failover to prevent downtime if Redis goes offline.

---

## ⚡ Key Features

*   **Decoupled Machine Learning Serving:** The Streamlit app does not load the 1.1MB model pickle file. All inference and pre-processing are executed on the FastAPI server.
*   **Basel Expected Loss Framework:** Translates raw default probabilities into financial metrics:
    $$\text{Expected Loss (EL)} = \text{Probability of Default (PD)} \times \text{Loss Given Default (LGD)} \times \text{Exposure at Default (EAD)}$$
*   **Dynamic Authentication Database:** A complete signup and login portal connected to a Supabase `users` table. Passwords are encrypted using cryptographically secure `bcrypt` hashes.
*   **Prediction Audit Trails:** Automatically logs metadata (amount, term, interest rate, user, expected loss, and risk tiers) to a Supabase `predictions` table.
*   **Explainable AI (SHAP):** Calculates feature contributions on the backend and transmits the base value and contributions in JSON. The frontend dynamically reconstructs the SHAP waterfall plot using Matplotlib.
*   **What-If Scenario Simulation:** Simulates Expected Loss fluctuations against varying SBA Guarantee percentages (50% to 90%).

---

## 🛠️ Tech Stack

*   **Machine Learning:** Scikit-Learn, SHAP, Pandas, NumPy, Joblib, Matplotlib
*   **Backend API:** FastAPI, Uvicorn, Pydantic v2, PyJWT, Passlib (Bcrypt)
*   **Frontend Dashboard:** Streamlit, Requests
*   **Databases & Infrastructure:** Supabase (PostgreSQL), Redis, Docker, Render Blueprints (Infrastructure-as-Code)

---

## ⚙️ Environment Configuration (`.env`)
To run the project locally, create a `.env` file at the root directory:

```env
ENV=development
DEBUG=true
API_KEY=your-local-dev-api-key
JWT_SECRET_KEY=your-jwt-signing-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REDIS_URL=redis://localhost:6379/0

# Cloud Database Logging (Supabase)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-public-anon-key
```

---

## 🚀 How to Run Locally

### 1. Run the Backend API
```bash
# Clone the repository
git clone https://github.com/dhruvbadhe/sba-loan-risk-engine.git
cd sba-loan-risk-engine

# Activate virtual environment
source venv/bin/activate

# Start the FastAPI server
uvicorn app.main:app --reload
```
The API documentation will be available locally at `http://127.0.0.1:8000/docs`.

### 2. Run the Streamlit Dashboard
```bash
streamlit run app/streamlit_app.py
```
The dashboard will open automatically at `http://localhost:8501`.
