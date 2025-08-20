# Lyric Generator (Render-ready)

## Files
- `app.py` — Flask app
- `requirements.txt` — dependencies
- `Procfile` — start command for Render
- `templates/index.html` — simple form

## Deploy on Render
1. Push these files to the **repo root** on GitHub.
2. On Render, create a **Web Service** from the repo.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`
5. Add environment variable: `OPENAI_API_KEY = <your key>`
6. Deploy.