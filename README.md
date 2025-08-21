# Melody to Lyrics Generator

This is a simple Flask web app that lets you upload a MIDI file and input song details (title, topic, mood).  
It then generates lyrics using OpenAI's GPT API.

## Setup

1. Clone repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run locally:
   ```bash
   flask run
   ```

3. Deploy on Render with `Procfile` and environment variable `OPENAI_API_KEY` set.
