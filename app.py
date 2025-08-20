from flask import Flask, request, render_template, send_file
import openai
import os

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        prompt = request.form["prompt"]
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a lyric generator."},
                    {"role": "user", "content": prompt}
                ]
            )
            lyrics = response.choices[0].message.content
            output_path = "lyrics.txt"
            with open(output_path, "w") as f:
                f.write(lyrics)
            return send_file(output_path, as_attachment=True)
        except Exception as e:
            return f"Error generating lyrics: {e}"
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
