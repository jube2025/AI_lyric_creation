import os
import io
from flask import Flask, request, render_template, send_file
from werkzeug.utils import secure_filename
import pretty_midi

app = Flask(__name__)
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def midi_to_lyric_template(midi_path, time_signature=(4, 4), rhyme_scheme="AABB", beat_threshold=0.75):
    pm = pretty_midi.PrettyMIDI(midi_path)
    melody = next((inst for inst in pm.instruments if (not inst.is_drum and inst.notes)), None)
    if melody is None:
        raise ValueError("No melodic notes found in MIDI.")
    beats = pm.get_beats()
    if len(beats) < 2:
        raise ValueError("Could not compute beat grid.")
    beat_durs = [beats[i+1] - beats[i] for i in range(len(beats)-1)]
    avg_beat = sum(beat_durs) / len(beat_durs)
    sec_per_beat = avg_beat
    beats_per_bar = time_signature[0]
    notes = sorted(melody.notes, key=lambda n: n.start)
    phrases, cur = [], []
    for i, note in enumerate(notes):
        if i > 0:
            gap = note.start - notes[i-1].end
            if gap > avg_beat:
                if cur: phrases.append(cur)
                cur = []
        cur.append(note)
    if cur: phrases.append(cur)
    templates = []
    for idx, phrase in enumerate(phrases):
        syllables, stress_slots, pos = 0, [], 1
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
            if stressed: stress_slots.append(pos)
            pos += 1
        rhyme_letter = rhyme_scheme[idx % len(rhyme_scheme)]
        templates.append({
            "phrase_index": idx + 1,
            "syllable_count": syllables,
            "stress_slots": stress_slots,
            "rhyme": rhyme_letter
        })
    return templates

def build_prompt_text(templates, title, topic, mood, rhyme_scheme):
    header = f\"""You are a professional lyricist. Write singable English lyrics that fit the given melody-derived template exactly.

SYSTEM GOALS
- Input: a prerecorded melody (already analyzed into a lyric template) + brief (title, topic, mood).
- Output: lyrics that fit the melody (syllable counts and stresses align with notes/accents), follow a rhyme scheme, and match the theme & tone.

MELODY→TEMPLATE RULES (already computed for you)
- Each phrase below has a target syllable count (exact).
- Stress masks: indices in 'stress' indicate where stressed syllables should ideally land.
- Rhyme letters: phrases with the same letter must rhyme.

GENERATION CONSTRAINTS
- Follow the syllable_count per phrase EXACTLY.
- Place stressed syllables at given stress indices where possible.
- Enforce rhyme by rhyme letter.
- Keep language singable and concise.

BRIEF
- Title: {title}
- Topic: {topic}
- Mood: {mood}
- Rhyme Scheme: {rhyme_scheme}

TEMPLATE:
\"""
    lines = [header, ""]
    for t in templates:
        lines.append(f"- Phrase {t['phrase_index']}: count={t['syllable_count']}, stress={t['stress_slots']}, rhyme={t['rhyme']}")
    lines += [
        "",
        "OUTPUT FORMAT:",
        "Phrase 1: ...",
        "Phrase 2: ...",
        "Phrase 3: ...",
        "..."
    ]
    return "\n".join(lines)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        title = (request.form.get('title') or 'Untitled').strip()
        topic = (request.form.get('topic') or 'general').strip()
        mood  = (request.form.get('mood') or 'neutral').strip()
        rhyme_scheme = (request.form.get('rhyme_scheme') or 'AABB').strip().upper()
        f = request.files.get('midi_file')
        if not f or f.filename == '':
            return 'Please upload a .mid/.midi file.', 400
        safe_name = secure_filename(f.filename)
        midi_path = os.path.join(UPLOAD_DIR, safe_name)
        f.save(midi_path)
        try:
            templates = midi_to_lyric_template(midi_path, rhyme_scheme=rhyme_scheme)
        except Exception as e:
            return f'Error analyzing MIDI: {e}', 500
        prompt_text = build_prompt_text(templates, title, topic, mood, rhyme_scheme)
        filename = f\"{title.replace(' ', '_')}_prompt.txt\"
        out = io.BytesIO(prompt_text.encode('utf-8'))
        out.seek(0)
        return send_file(out, as_attachment=True, download_name=filename, mimetype='text/plain')
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
