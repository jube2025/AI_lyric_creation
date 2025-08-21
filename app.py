import os
import io
from flask import Flask, request, render_template, send_file, session, redirect, url_for
from werkzeug.utils import secure_filename
import pretty_midi
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me")
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- OpenAI client (reads OPENAI_API_KEY from environment) ---
if not os.environ.get("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable not set")
client = OpenAI()

def midi_to_lyric_template(midi_path, time_signature=(4, 4), rhyme_scheme="AABB", beat_threshold=0.75):
    """
    Convert a MIDI melody into a list of phrase templates.
    Each template contains: syllable_count, stress_slots, rhyme (A/B/...).
    Heuristics (MVP):
      - Phrases split when a rest > ~1 beat occurs.
      - Each note ~ one syllable; long notes (>= beat_threshold beats) add stress (melisma allowed).
      - Stress slots on long notes or strong beats (1 & 3 in 4/4).
    """
    pm = pretty_midi.PrettyMIDI(midi_path)

    # Choose first non-drum instrument with notes as melody
    melody = next((inst for inst in pm.instruments if (not inst.is_drum and inst.notes)), None)
    if melody is None:
        raise ValueError("No melodic notes found in MIDI. Please upload a clear lead melody.")

    beats = pm.get_beats()
    if len(beats) < 2:
        raise ValueError("Could not compute beat grid from MIDI.")
    beat_durs = [beats[i+1] - beats[i] for i in range(len(beats)-1)]
    avg_beat = sum(beat_durs) / len(beat_durs)
    sec_per_beat = avg_beat
    beats_per_bar = time_signature[0]

    # Segment phrases by rest length
    notes = sorted(melody.notes, key=lambda n: n.start)
    phrases, cur = [], []
    for i, note in enumerate(notes):
        if i > 0:
            gap = note.start - notes[i-1].end
            if gap > avg_beat:  # new phrase
                if cur:
                    phrases.append(cur)
                cur = []
        cur.append(note)
    if cur:
        phrases.append(cur)

    templates = []
    for idx, phrase in enumerate(phrases):
        syllables = 0
        stress_slots = []
        pos = 1
        for n in phrase:
            dur_beats = (n.end - n.start) / sec_per_beat
            syllables += 1
            stressed = False
            if dur_beats >= beat_threshold:
                stressed = True
            else:
                beat_idx = int((n.start / sec_per_beat) % beats_per_bar) + 1
                if beat_idx in (1, 3):
                    stressed = True
            if stressed:
                stress_slots.append(pos)
            pos += 1

        rhyme_letter = rhyme_scheme[idx % len(rhyme_scheme)]
        templates.append({
            "phrase_index": idx + 1,
            "syllable_count": syllables,
            "stress_slots": stress_slots,
            "rhyme": rhyme_letter
        })

    return templates

def build_prompt(templates, title, topic, mood):
    lines = []
    lines.append("You are a professional lyricist. Write singable English lyrics that fit this melody-derived template exactly.")
    lines.append("Constraints:")
    lines.append("- Follow syllable counts per phrase precisely.")
    lines.append("- Align stressed syllables to the given stress slots when natural.")
    lines.append("- Phrases with the same rhyme letter should rhyme by sound (phoneme), not only spelling.")
    lines.append("- Keep language clean and singable; avoid tongue-twisters and overly dense consonant clusters.")
    lines.append("")
    lines.append(f"Title: {title}")
    lines.append(f"Topic: {topic}")
    lines.append(f"Mood: {mood}")
    lines.append("")
    lines.append("Template (phrase_index, syllable_count, stress_slots, rhyme):")
    for t in templates:
        lines.append(f"- Phrase {t['phrase_index']}: count={t['syllable_count']}, stress={t['stress_slots']}, rhyme={t['rhyme']}")
    lines.append("")
    lines.append('Output one line per phrase, labeled exactly as "Phrase X: ...". No extra commentary.')
    return "\n".join(lines)

def generate_lyrics(templates, title, topic, mood, temperature=0.8):
    prompt = build_prompt(templates, title, topic, mood)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You produce tightly metered, rhymed, singable lyrics."},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()

@app.route("/", methods=["GET", "POST"])
def index():
    results, lyrics = None, None
    if request.method == "POST":
        title = (request.form.get("title") or "Untitled").strip()
        topic = (request.form.get("topic") or "general").strip()
        mood  = (request.form.get("mood") or "neutral").strip()
        rhyme_scheme = (request.form.get("rhyme_scheme") or "AABB").strip().upper()

        f = request.files.get("midi_file")
        if not f or f.filename == "":
            return "Please upload a .mid/.midi file.", 400

        safe_name = secure_filename(f.filename)
        midi_path = os.path.join(UPLOAD_DIR, safe_name)
        f.save(midi_path)

        try:
            results = midi_to_lyric_template(midi_path, rhyme_scheme=rhyme_scheme)
            lyrics = generate_lyrics(results, title, topic, mood)
        except Exception as e:
            return f"Error: {e}", 500

        # Save for regeneration & download
        session["template"] = results
        session["title"] = title
        session["topic"] = topic
        session["mood"] = mood

        # Prepare combined text for download
        out = io.StringIO()
        out.write(f"Title: {title}\nTopic: {topic}\nMood: {mood}\nRhyme scheme: {rhyme_scheme}\n\n")
        out.write("Template:\n")
        for t in results:
            out.write(f"Phrase {t['phrase_index']}: {t['syllable_count']} syllables, stress {t['stress_slots']}, rhyme {t['rhyme']}\n")
        out.write("\nGenerated Lyrics:\n")
        out.write(lyrics or "")
        session["download_text"] = out.getvalue()
        out.close()

    else:
        results = session.get("template")
        if "download_text" in session:
            txt = session["download_text"]
            if "\nGenerated Lyrics:\n" in txt:
                lyrics = txt.split("\nGenerated Lyrics:\n", 1)[1]

    return render_template("index.html", results=results, lyrics=lyrics)

@app.route("/regenerate", methods=["POST"])
def regenerate():
    if "template" not in session:
        return redirect(url_for("index"))
    templates = session["template"]
    title = session.get("title", "Untitled")
    topic = (request.form.get("topic") or session.get("topic", "general")).strip()
    mood  = (request.form.get("mood") or session.get("mood", "neutral")).strip()
    session["topic"] = topic
    session["mood"] = mood

    lyrics = generate_lyrics(templates, title, topic, mood)

    out = io.StringIO()
    out.write(f"Title: {title}\nTopic: {topic}\nMood: {mood}\n\n")
    out.write("Template:\n")
    for t in templates:
        out.write(f"Phrase {t['phrase_index']}: {t['syllable_count']} syllables, stress {t['stress_slots']}, rhyme {t['rhyme']}\n")
    out.write("\nGenerated Lyrics:\n")
    out.write(lyrics or "")
    session["download_text"] = out.getvalue()
    out.close()

    return redirect(url_for("index"))

@app.route("/download")
def download():
    txt = session.get("download_text")
    if not txt:
        return "Nothing to download yet.", 400
    bio = io.BytesIO(txt.encode("utf-8"))
    bio.seek(0)
    return send_file(bio, as_attachment=True, download_name="lyrics_output.txt", mimetype="text/plain")

if __name__ == "__main__":
    # Render binds a random port via the PORT env var; default to 10000 locally
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))