# AI Lyric Generator 🎵

This is a simple Flask app deployed on Render that generates song lyrics using OpenAI's GPT models.

## 🚀 Features
- Input a theme or style, and generate AI-written lyrics.
- Download lyrics as a `.txt` file.
- Deployed easily on Render with GitHub integration.

## 📂 Project Structure
```
lyric_generator_project/
│── app.py              # Main Flask app
│── requirements.txt    # Python dependencies
│── Procfile            # Render startup command
│── templates/
│   └── index.html      # Frontend form
│── README.md           # Project documentation
```

## ⚙️ Setup Instructions

### 1. Clone the repo
```bash
git clone https://github.com/<your-username>/AI_lyric_creation.git
cd AI_lyric_creation
```

### 2. Add your OpenAI API key
Set your API key as an environment variable in Render:
```
OPENAI_API_KEY=your_api_key_here
```

### 3. Deploy on Render
- Push your repo to GitHub.
- Connect it to Render and deploy a **Web Service**.
- Ensure the **build command** is:
  ```
  pip install -r requirements.txt
  ```
- And the **start command** is:
  ```
  gunicorn app:app
  ```

Your app should now be live! 🎉

---
Made with ❤️ using Flask + OpenAI + Render.
