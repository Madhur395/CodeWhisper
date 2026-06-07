# 🧠 CodeWhisper
### *One hint at a time — AI-powered progressive hints for DSA problems*

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)](https://flask.palletsprojects.com)
[![LLM Powered](https://img.shields.io/badge/LLM-Powered-orange?logo=openai)](https://openai.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📌 What is CodeWhisper?

**CodeWhisper** is an AI-powered progressive hint system designed for students and developers practicing Data Structures & Algorithms (DSA). Instead of giving away the full solution, it guides you step-by-step — one whisper at a time.

> Stuck on a LeetCode problem? Don't look at the solution.  
> Let CodeWhisper nudge you in the right direction. 💡

---

## ✨ Features

- 🔢 **Progressive Hints** — Get hints level by level (conceptual → approach → pseudocode → code nudge)
- 🤖 **LLM-Powered** — Uses a Large Language Model to generate context-aware hints
- 🧩 **DSA Focused** — Tailored for arrays, trees, graphs, DP, and more
- 🌐 **Web Interface** — Clean Flask-based UI to paste your problem and get hints
- 📊 **Hint History** — Track which hints you've used per problem

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, Flask |
| AI/LLM | OpenAI API / Claude API |
| Frontend | HTML, CSS, JavaScript |
| Storage | JSON / SQLite (lightweight) |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- pip
- An LLM API key (OpenAI or Anthropic)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Madhur395/CodeWhisper.git
cd CodeWhisper

# 2. Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Add your API key in .env

# 5. Run the app
python app.py
```

Then open `http://localhost:5000` in your browser.

---

## 📁 Project Structure

```
CodeWhisper/
├── app.py                  # Flask application entry point
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore
├── README.md
│
├── backend/
│   ├── hint_engine.py      # Core progressive hint logic
│   ├── llm_client.py       # LLM API wrapper
│   └── prompt_templates.py # Prompt engineering templates
│
├── frontend/
│   ├── templates/
│   │   └── index.html      # Main UI
│   └── static/
│       ├── style.css
│       └── script.js
│
└── uploads/
    ├── architecture.md
    ├── implementation_plan.md
    └── problem_statement.md
```

---

## 🎯 How It Works

1. **User pastes a DSA problem** into the interface
2. **Selects hint level** (1 = vague nudge, 5 = near-solution)
3. **CodeWhisper calls the LLM** with a carefully crafted prompt
4. **Progressive hint is returned** — no full solutions unless explicitly requested

```
Problem → [Hint Level 1] → Think about the data structure
        → [Hint Level 2] → Consider using a HashMap
        → [Hint Level 3] → Store frequency counts as you iterate
        → [Hint Level 4] → Check if (target - current) exists in the map
```

---

## 🔮 Roadmap

- [ ] User authentication & problem history
- [ ] Support for LeetCode URL auto-fetch
- [ ] Difficulty detection (Easy / Medium / Hard)
- [ ] VS Code extension integration
- [ ] Mobile-friendly UI

---

## 👨‍💻 Author

**Madhur Saini**  
B.Tech CSE, Chandigarh Group of Colleges, Landran  
[GitHub](https://github.com/Madhur395) • [LinkedIn](https://linkedin.com/in/madhursaini)

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

*Built with ❤️ for every developer who's ever been stuck on a DSA problem at 2 AM.*
