from flask import Flask, render_template, request, send_file
import os
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        title = request.form["title"]
        topic = request.form["topic"]
        mood = request.form["mood"]
        midi_file = request.files.get("midi_file")

        # Save MIDI file if provided
        midi_path = None
        if midi_file:
            midi_path = os.path.join("uploads", midi_file.filename)
            os.makedirs("uploads", exist_ok=True)
            midi_file.save(midi_path)

        try:
            # Generate lyrics using GPT
            prompt = f"Write song lyrics with the title '{title}', about '{topic}', in a '{mood}' mood."
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            lyrics = response.choices[0].message["content"]
        except Exception as e:
            lyrics = f"Error generating lyrics: {e}"

        # Save lyrics to a file
        output_path = os.path.join("outputs", f"{title.replace(' ', '_')}_lyrics.txt")
        os.makedirs("outputs", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(f"Title: {title}\n")
            f.write(f"Topic: {topic}\n")
            f.write(f"Mood: {mood}\n\n")
            f.write(lyrics)

        return send_file(output_path, as_attachment=True)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
