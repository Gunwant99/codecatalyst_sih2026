# MPLADS AI Investigator

## AI-powered project risk & investigation assistant

> **Smart India Hackathon 2026 — SIH26102**

MPLADS AI Investigator is an AI-assisted system for screening MPLADS projects, identifying contextual risk indicators, comparing projects with similar projects, and providing investigation guidance.

The system is designed to help investigators **prioritize which projects deserve attention first and understand why**.

> **Important:** A risk score is an investigation-priority signal. It does NOT establish fraud, corruption, or wrongdoing. Final conclusions require human verification and official records.

---

# 🚀 What Does This Project Do?

MPLADS contains a large number of development projects. Manually reviewing every project with the same level of attention is inefficient.

MPLADS AI Investigator helps solve this by analyzing projects and providing:

- Risk score from 0–100
- Risk level: LOW / MEDIUM / HIGH
- Explainable risk indicators
- Contextual cost analysis
- Similar-project comparison
- Evidence availability
- Recommended verification actions
- AI Investigation Copilot
- National-level project overview

The goal is:

```text
Thousands of Projects
        ↓
Automated Risk Screening
        ↓
Investigation Priority
        ↓
Contextual Evidence
        ↓
AI Investigation Guidance
        ↓
Human Investigator

🎯 Core Principle

The system does NOT work like:

Anomaly → Fraud

Instead:

Anomaly
   ↓
Risk Signal
   ↓
Investigation Priority
   ↓
Human Verification
   ↓
Final Conclusion

This distinction is important because an unusual project is not automatically fraudulent.

⭐ Key Features
1. Project Risk Assessment

Each project receives a risk score:

0 – 100

Current risk levels:

Score	Risk Level	Interpretation
0–19	LOW	Low investigation priority
20–39	MEDIUM	Additional contextual verification recommended
40–100	HIGH	High investigation priority

The risk score is generated using transparent analytical indicators.

2. Contextual Cost Analysis

Project amounts are compared with contextual projects using:

State
+
House
+
Category

This allows the system to detect projects whose cost is unusually high compared with relevant projects.

The system does not simply compare every project against a national average.

It attempts to provide a more meaningful contextual comparison.

3. Explainable Risk Indicators

The risk engine can consider indicators such as:

Strong cost anomaly compared with contextual projects
High-value project
Limited project description
Very small constituency comparison group
High project concentration in the same period
Lack of image evidence

Each indicator contributes to investigation priority.

The system explains why a project received its score.

4. Similar Project Analysis

The similarity engine identifies projects that are contextually similar.

It considers:

Project description
State
House
Category
Constituency context

The result contains:

Work ID
Description
Contextual similarity
Project amount
Target vs comparable amount
Constituency

This gives investigators concrete projects for comparison.

5. Evidence Status

The system identifies whether project image evidence is available.

Example:

Images Available

or:

No Images Available

Image availability can be used as one of the investigation indicators.

6. AI Investigation Copilot

The AI Investigation Copilot allows the investigator to ask questions about the selected project.

Example questions:

Compare with similar projects
Explain the risk score
What should I verify?

The Copilot can provide:

Risk explanation
Comparative analysis
Investigation interpretation
Recommended verification order

The AI layer is intended to synthesize the evidence produced by the analytical system and convert it into investigator-friendly guidance.

7. National Overview

The dashboard provides an overview of the dataset.

It can show:

Total projects
Total project amount
LOW / MEDIUM / HIGH distribution
Projects with images
Projects without images
State-wise project distribution
🏗️ System Architecture
                    ┌──────────────────────┐
                    │      React UI        │
                    │      Frontend        │
                    └──────────┬───────────┘
                               │
                               │ REST API
                               ▼
                    ┌──────────────────────┐
                    │      FastAPI         │
                    │      Backend         │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼─────────────────┐
              │                │                 │
              ▼                ▼                 ▼
      ┌──────────────┐ ┌───────────────┐ ┌───────────────┐
      │ Risk Engine  │ │ Similarity    │ │ AI            │
      │              │ │ Engine        │ │ Copilot       │
      └──────────────┘ └───────────────┘ └───────────────┘
              │                │                 │
              └────────────────┼─────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │     MPLADS Data      │
                    │        CSV           │
                    └──────────────────────┘
🛠️ Technology Stack
Backend
Python
FastAPI
Uvicorn
Pandas
NumPy
Scikit-learn
RapidFuzz
Groq API
Frontend
React
Vite
JavaScript
CSS
Data
CSV-based MPLADS project dataset
📁 Project Structure
mplads-ai-investigator/
│
├── README.md
├── .gitignore
│
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── main.py
│   ├── agent.py
│   ├── tools.py
│   ├── risk_engine.py
│   ├── similarity_engine.py
│   ├── context_profile.py
│   ├── data_profile.py
│   ├── inspect_data.py
│   └── ...
│
├── data/
│   ├── mplads_data.csv
│   └── risk_scored_projects.csv
│
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── vite.config.js
    ├── src/
    └── public/
💻 Running the Project on Another Laptop

This section is for teammates who are setting up the project for the first time.

1. Install Required Software

Install the following:

Git

Check installation:

git --version
Python

Python 3.10+ is recommended.

Check:

python --version
Node.js

Install Node.js LTS.

Check:

node --version

Then:

npm --version
📥 2. Clone the GitHub Repository

Open PowerShell.

Run:

git clone https://github.com/Gunwant99/codecatalyst_sih2026.git

Then:

cd codecatalyst_sih2026

You now have the complete project on your laptop.

🐍 3. Create Backend Virtual Environment

From the project root:

python -m venv backend\venv

This creates a local Python environment.

The venv folder is intentionally NOT stored in GitHub.

Every teammate creates their own environment.

▶️ 4. Activate the Backend Environment

On Windows PowerShell:

.\backend\venv\Scripts\Activate.ps1

You should see:

(venv) PS C:\...\codecatalyst_sih2026>

The (venv) means the environment is active.

📦 5. Install Backend Dependencies

With (venv) active:

python -m pip install -r backend\requirements.txt

This installs the packages required by the backend.

🔐 6. Set Up the API Key

The repository contains:

backend/.env.example

This file does NOT contain the real API key.

Each developer must create their own:

backend/.env

Put this inside:

GROQ_API_KEY=your_groq_api_key_here

Replace:

your_groq_api_key_here

with the developer's own API key.

⚠️ IMPORTANT

Never commit:

backend/.env

Never put a real API key inside:

backend/.env.example

Never upload API keys to GitHub.

The .gitignore already protects .env.

🔒 API Key Rule for the Team

Each teammate should use their own API key.

Do NOT share the project owner's API key.

Do NOT put API keys in:

GitHub
Git commits
README
WhatsApp
Screenshots
Public documents

If an API key is accidentally pushed to GitHub, it should be revoked/rotated immediately.

🖥️ 7. Start the Backend

Open Terminal 1.

From the project root:

.\backend\venv\Scripts\Activate.ps1
cd backend
python -m uvicorn main:app --reload

The backend should run at:

http://localhost:8000

Keep this terminal running.

🌐 8. Start the Frontend

Open a SECOND terminal.

Go to the project:

cd codecatalyst_sih2026

Then:

cd frontend

Install frontend packages:

npm install

Start the frontend:

npm run dev

Vite will show a URL such as:

http://localhost:5173

Open that URL in your browser.

🚀 Complete Startup — Quick Version

You need two terminals.

Terminal 1 — Backend
cd codecatalyst_sih2026
.\backend\venv\Scripts\Activate.ps1
cd backend
python -m uvicorn main:app --reload
Terminal 2 — Frontend
cd codecatalyst_sih2026
cd frontend
npm install
npm run dev

Then open:

http://localhost:5173
🩺 Backend Health Check

Open:

http://localhost:8000/health

You can also open the FastAPI API documentation:

http://localhost:8000/docs
🔌 Main API Endpoints
GET /

Main backend endpoint.

GET /health

Backend health check.

GET /projects

Get project information.

GET /projects/{work_id}

Get a specific project.

Example:

/projects/193991
GET /projects/{work_id}/similar

Find similar projects.

Example:

/projects/193991/similar
GET /investigate/{work_id}

Run project investigation.

Example:

/investigate/193991
GET /agent/investigate?query=...

AI Investigation Copilot endpoint.

GET /dashboard

National dashboard information.

🧪 Demo Work IDs

Use these projects to test the system.

🟢 LOW-Risk Demo
Work ID: 134703
Risk: LOW
Score: 0/100

This is useful for demonstrating that the system does not flag every project.

🟡 MEDIUM-Risk Demo
Work ID: 225857
Risk: MEDIUM
Score: 38/100

Useful for demonstrating:

Risk indicators
Similar projects
Investigation recommendations
AI Copilot
🟡 MEDIUM-Risk Demo
Work ID: 193991
Risk: MEDIUM
Score: approximately 39/100

Useful for demonstrating contextual cost anomaly analysis.

🎬 Recommended Hackathon Demo Flow
Step 1

Open:

http://localhost:5173
Step 2

Search:

193991
Step 3

Show:

Project details
Risk score
Risk level
Risk indicators
Evidence status
Step 4

Show the comparable-project table.

Explain:

The system does not evaluate the project in isolation. It compares it with contextual projects to identify unusual patterns.

Step 5

Use:

Explain the risk score
Step 6

Use:

What should I verify?
Step 7

Use:

Compare with similar projects
Step 8

Show LOW-risk project:

134703

Explain:

The system can also identify projects with no major automated risk indicators. This demonstrates that the system is a risk-based triage system, not a system that labels every project as suspicious.

📊 Current Dataset

The current prototype uses an MPLADS project dataset containing project-level information such as:

Work ID
Work Description
Category
MP Name
Constituency
State
House
Final Amount
Completed Date
Image availability
Average Rating
IDA

The project currently works with CSV data.

⚠️ Data Limitations

The current dataset does not reliably contain every field required for a complete investigation.

Examples of additional information that could improve the system:

Sanction/start dates
Detailed procurement information
Contractor information
Complete payment records
Detailed expenditure records
Site inspection records
Detailed project specifications

Therefore:

The current system should be considered an investigation-support and risk-screening prototype.

It is not a complete automated audit system.

🧠 Why Explainable Risk Rules?

The current prototype uses transparent risk indicators instead of depending entirely on a black-box ML model.

Advantages:

Easy to explain
Easy to audit
Investigator-friendly
Transparent reasoning
Easier human verification
Suitable for government decision-support scenarios

The AI layer works on top of this analytical evidence.

Project Data
     ↓
Risk Engine
     ↓
Similarity Engine
     ↓
Evidence
     ↓
AI Investigation Copilot
     ↓
Human Investigator
🤖 AI Design Principle

The AI should not independently invent accusations.

The intended flow is:

Tools / Analytics
       ↓
Evidence
       ↓
AI Synthesis
       ↓
Investigation Guidance

The AI provides decision support based on the available evidence.

🔄 Team Git Workflow

For team development, avoid directly making experimental changes on main.

First time

Clone the repository:

git clone https://github.com/Gunwant99/codecatalyst_sih2026.git
cd codecatalyst_sih2026
🌿 Create Your Own Branch

Example:

git checkout -b feature/copilot

Other examples:

feature/dashboard
feature/frontend
feature/risk-engine
feature/agent
fix/ui
fix/api
🔍 Check Your Changes
git status
➕ Add Changes
git add .
💾 Commit

Example:

git commit -m "Improve investigation copilot"
☁️ Push Your Branch
git push -u origin feature/copilot

Then create a Pull Request on GitHub.

🔄 Before Starting New Work

Update your local main:

git checkout main
git pull origin main

Then create a new branch:

git checkout -b feature/your-feature
⚠️ Do Not Push Randomly to Main

Preferred workflow:

main
  │
  ├── feature/frontend
  │
  ├── feature/backend
  │
  ├── feature/copilot
  │
  └── feature/dashboard
           │
           ▼
       Pull Request
           │
           ▼
          main

This reduces the chance of breaking the working version.

🧹 Important Files That Are NOT Uploaded

The following local files/folders are intentionally excluded from Git:

.env
venv/
.venv/
node_modules/
__pycache__/
logs
temporary files

This prevents secrets and machine-specific files from being committed.

🛠️ Troubleshooting
Problem: (venv) does not appear

Run:

.\backend\venv\Scripts\Activate.ps1
Problem: PowerShell blocks activation

Run:

Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

Then:

.\backend\venv\Scripts\Activate.ps1
Problem: Python package is missing

Activate the environment:

.\backend\venv\Scripts\Activate.ps1

Then:

python -m pip install -r backend\requirements.txt
Problem: Frontend packages are missing

Go to:

cd frontend

Then:

npm install
Problem: AI Copilot does not work

Check:

backend/.env

Make sure it contains:

GROQ_API_KEY=your_api_key

After changing .env, restart the backend.

Problem: Port 8000 is already in use

Run:

python -m uvicorn main:app --reload --port 8001

If the frontend expects port 8000, update the frontend API configuration accordingly.

Problem: Port 5173 is already in use

Vite may automatically choose another available port.

Use the URL displayed in the terminal.

👥 Team Setup Checklist

Every teammate should complete:

[ ] Install Git
[ ] Install Python
[ ] Install Node.js
[ ] Clone repository
[ ] Create backend virtual environment
[ ] Activate venv
[ ] Install requirements.txt
[ ] Create backend/.env
[ ] Add personal GROQ_API_KEY
[ ] Start FastAPI backend
[ ] Run npm install
[ ] Start React frontend
[ ] Open localhost:5173
[ ] Test Work ID 134703
[ ] Test Work ID 225857
[ ] Test Work ID 193991
🔐 Security Checklist

Before every Git push:

[ ] No real API key
[ ] No .env file
[ ] No passwords
[ ] No tokens
[ ] No private credentials
[ ] No unnecessary personal data

Check:

git status

The real .env should never appear as a file to commit.

You can also verify:

git check-ignore -v backend\.env
📌 Project Status

Current prototype includes:

 MPLADS dataset integration
 Project lookup
 Risk scoring
 Explainable risk indicators
 Contextual cost analysis
 Similar-project analysis
 Evidence availability
 Investigation recommendations
 AI Investigation Copilot
 National Overview
 React frontend
 FastAPI backend
 GitHub repository
 Environment-variable API key protection
 Requirements file for reproducible setup
🚀 Future Improvements

Possible future extensions:

Agentic investigation workflow
Investigation execution trail
More official MPLADS data sources
Procurement analysis
Contractor analysis
Payment/expenditure analysis
Temporal anomaly detection
Advanced semantic similarity
Vector database
Investigator case management
Audit logs
Role-based access control
Production database
Automated investigation reports
Human feedback loop
Additional official evidence sources
