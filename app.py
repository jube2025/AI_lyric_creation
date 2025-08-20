import os
import tempfile
from flask import Flask, request, render_template, send_file
from openai import OpenAI

app = Flask(__name__)

# Initialize OpenAI client from environment variable
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")
client = OpenAI(api_key=api_key)

@app.route("/", methods=["GET", "POST"])
def index():
    lyrics = None
    error = None

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        topic = (request.form.get("topic") or "").strip()
        mood = (request.form.get("mood") or "").strip()

        if not title or not topic or not mood:
            error = "Please provide Title, Topic, and Mood."
        else:
            prompt = (
                f"Write singable song lyrics.\n"
                f"Title: {title}\n"
                f"Topic: {topic}\n"
                f"Mood: {mood}\n"
                f"Constraints: Keep it clean, 2 verses and a chorus, ~8-12 syllables per line, end with a short outro.\n"
                f"Return only the lyrics."
            )
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a skilled lyricist."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.8,
                )
                lyrics = (resp.choices[0].message.content or "").strip()
            except Exception as e:
                error = f"Error generating lyrics: {e}"
                print("OpenAI API Error:", e)

        # Always return a downloadable text file (lyrics or error)
        content = lyrics if lyrics else (error or "Unknown error.")
        tmp = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt")
        tmp.write(content)
        tmp.close()
        return send_file(tmp.name, as_attachment=True, download_name=f"{title or 'lyrics'}.txt")

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))