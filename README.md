# 🤖 AI Facebook Post Agent

### Built Using the CrewAI Agentic AI Framework

An AI-powered social media automation application that uses multiple AI agents to research topics, generate articles, create engaging Facebook posts, and publish content through the Meta Graph API with human approval.

## ✨ Features

- **Multi-Agent Architecture:** Separate AI agents for research, article writing, and Facebook post generation.
- **AI-Powered Content Generation:** Uses OpenAI models to create relevant articles and social media content.
- **Interactive Web Dashboard:** HTML, CSS, and JavaScript interface with a chat panel and agent workflow visualization.
- **Flask Backend:** Connects the frontend with the Python agent workflow.
- **Workflow Status Tracking:** Displays agent execution progress and results.
- **Human-in-the-Loop Approval:** Review the generated post before publishing.
- **Facebook Graph API Integration:** Publishes approved content to a Facebook Page.
- **Secure Configuration:** Stores API credentials in environment variables.

## 🏗️ Architecture

```text
                 User enters a topic
                         |
                         v
                 Flask Web Dashboard
                         |
                         v
                  CrewAI Orchestrator
                         |
              +----------+----------+
              |          |          |
              v          v          v
          Researcher   Writer    Facebook Post
             Agent      Agent       Agent
              |          |          |
              +----------+----------+
                         |
                         v
                 Generated Post Draft
                         |
                         v
                  Human Approval
                         |
                  +------+------+
                  |             |
                  v             v
               Approved      Rejected
                  |
                  v
           Meta Graph API
                  |
                  v
             Facebook Page
```

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application and agent logic |
| CrewAI | Multi-agent orchestration |
| OpenAI | Language model and content generation |
| Flask | Backend API and web application |
| HTML, CSS, JavaScript | Interactive dashboard |
| Meta Graph API | Facebook Page publishing |
| python-dotenv | Environment variable configuration |

## 📁 Project Structure

```text
crewai-facebook-post-agent/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── templates/
    └── index.html
```

## ⚙️ Prerequisites

- Python 3.12 or a compatible Python version
- An OpenAI API key
- A Facebook Page
- A valid Facebook Page access token with the required publishing permissions
- Meta Graph API access configured for your application

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/crewai-facebook-post-agent.git
cd crewai-facebook-post-agent
```

Replace `YOUR_USERNAME` with your GitHub username.

### 2. Create a virtual environment

**Windows:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root using `.env.example` as a template.

```env
OPENAI_API_KEY=your_openai_api_key
FACEBOOK_PAGE_ID=your_facebook_page_id
FACEBOOK_PAGE_ACCESS_TOKEN=your_facebook_page_access_token
