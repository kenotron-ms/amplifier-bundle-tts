# Audiobook v2 — Project Plan

## Problems with v1 (OmniVoice)
1. **Inconsistency** — each clip is a fresh diffusion sample; same `instruct` string produces
   slightly different voice every call. No way to anchor identity across 184 segments.
2. **Click artifacts** — OmniVoice chokes on Unicode curly-quotes in short fragments.
3. **Weak child voice** — no dedicated child-voice capability; `"male, child, high pitch"` is
   only a rough proxy.
4. **Limited expression** — only 9 sound tags (`[laughter]`, `[sigh]` etc.); nothing like
   `[said in a hurry]` or `[whispered fearfully]`.

---

## Model Decision: Chatterbox (Resemble AI)

**Why Chatterbox wins for this project:**

| Need | Chatterbox | OmniVoice |
|------|-----------|-----------|
| Voice consistency | ✅ Clone any voice from 5-10 s ref audio | ❌ New sample every call |
| Expression tags | ✅ `[laugh]` `[chuckle]` `[cough]` + exaggeration slider | ⚠ 9 fixed tags |
| macOS MPS | ✅ Confirmed M1/M2/M3/M4, ~2-3x over CPU | ✅ Works |
| Child voice | ✅ Clone from any child reference | ⚠ Instruct guess only |
| License | ✅ MIT | ✅ MIT |
| Parameters | 350M (Turbo) / 500M (Original) | ~similar |

**Runner-up:** F5-TTS via MLX (fastest on M3, good cloning, zero emotion tags — good
fallback if Chatterbox MPS proves too slow for narration).

---

## Core Strategy: Voice Seeding + Cloning

```
Step A: generate seed clip (~12 s) for each character via OmniVoice instruct
             ↓
Step B: use each seed as audio_prompt_path in Chatterbox
             ↓
Step C: every segment of that character references the SAME seed → guaranteed consistency
```

OmniVoice already installed; it becomes a **seed factory** only. Chatterbox does all
final generation.

---

## Character Profiles v2

| Character | Seed strategy | exaggeration | cfg_weight | Notes |
|-----------|--------------|-------------|-----------|-------|
| NARRATOR  | OmniVoice seed `"male, middle-aged, low pitch"` | 0.30 | 0.55 | Measured, noir |
| CHASE     | OmniVoice seed `"male, middle-aged, moderate pitch"` | 0.45 | 0.45 | World-weary |
| LIA       | OmniVoice seed `"female, young adult, moderate pitch"` | 0.45 | 0.50 | Warm, worried |
| JACK      | OmniVoice seed `"male, child, high pitch"` **+ pitch-shift -2 semitones** | 0.55 | 0.45 | Very young |
| BLAZE     | OmniVoice seed `"male, middle-aged, very low pitch"` | 0.30 | 0.60 | Cold, flat |
| CRUM      | OmniVoice seed `"male, young adult, high pitch"` | 0.70 | 0.40 | Terrified |
| GANG_MEMBER | OmniVoice seed `"male, young adult, low pitch"` | 0.35 | 0.50 | Flat, pro |

**Jack note:** OmniVoice's child instruct + a pitch-shift in post (librosa or soundfile)
brings the voice down to a genuinely young child range without sounding synthetic.

---

## Expression Strategy

### Inline Chatterbox tags (placed directly in text)
```
[laugh]      — actual laugh sound
[chuckle]    — quiet, brief laugh
[cough]      — cough/throat clearing
```

### Text-level punctuation tricks (keep original words, change punctuation)
```
...          — hesitation / trailing off
—            — abrupt cut-off or interruption
ALL CAPS     — stressed / shouted word
!            — exclamation / urgency
? at end     — rising intonation (already in original)
```

### Per-segment overrides (in script metadata)
For emotionally extreme lines, override exaggeration/cfg per-segment:
```
# BLAZE discovering daughter: exaggeration=0.20, cfg_weight=0.65 (eerily flat)
# CRUM pleading: exaggeration=0.80, cfg_weight=0.35 (desperate, fast)
# CHASE [sigh] confession: exaggeration=0.50, cfg_weight=0.42
```

### What we cannot do with Chatterbox
- `[whispered]` — no whisper tag; workaround: lower `exaggeration`, add `...` pauses
- `[said in a hurry]` — lower `cfg_weight` to ~0.30 (speeds pacing), add `!`
- Truly free-form emotion directions (Orpheus V1 would, but runs slow on Mac)

---

## Milestones

### M1 — Install & Verify (est. 20 min)
- `pip install chatterbox-tts` in the .venv
- Smoke test: generate one clip on MPS, confirm no crash
- Measure speed: time one 10-word clip
- **Gate:** produces a WAV, MPS active, < 30 s per clip

### M2 — Voice Seeds (est. 1 hr)
- Script `make_seeds.py`: uses OmniVoice to generate 12–15 s seed clip per character
  speaking a paragraph of neutral prose (not story text)
- Seeds saved to `voices/seeds/{character}.wav`
- Manual listen: confirm each seed sounds right
- **Gate:** 7 seed WAVs, all pass human review

### M3 — Script v2 Annotation (est. 2 hrs)
- Go through `audiobook_script.md` and add:
  - Inline tags (`[laugh]`, `[chuckle]`, `[cough]`) where appropriate
  - Punctuation overrides (`...`, `—`, CAPS) for emotional beats
  - Per-segment metadata comments for exaggeration/cfg overrides
- **No text words changed** — only punctuation, tags, and metadata comments
- **Gate:** annotated script reviewed, changes make sense dramatically

### M4 — Generator v2 (est. 1.5 hrs)
- `generate_audiobook_v2.py`:
  - Reads annotated `audiobook_script.md`
  - Parses per-segment overrides from comments
  - Calls Chatterbox with correct ref audio + params per segment
  - Smart-quote normalisation (already solved)
  - RMS QA: if < 0.01, auto-retry up to 3×; log failures
  - Skip-if-exists
- Usage: `python generate_audiobook_v2.py 1` (same CLI as v1)
- **Gate:** runs Scene 1 end-to-end, all 56 clips pass RMS check

### M5 — Generate Scenes 1–8 (est. 6–10 hrs machine time)
- Run scene by scene
- Check logs after each; manual spot-listen
- **Gate:** all 184 segments on disk, < 5% flagged by RMS QA

### M6 — Final Stitch (est. 10 min)
- Same pause system from v1
- Output: `audio/audiobook_v2_FINAL.wav`
- **Gate:** full listen-through of stitched output

---

## File Layout

```
omnivoice/
├── audiobook_script.md          ← annotated script (M3 output)
├── make_seeds.py                ← M2: generates voice seeds
├── generate_audiobook_v2.py     ← M4: Chatterbox generator
├── voices/
│   └── seeds/
│       ├── NARRATOR.wav
│       ├── CHASE.wav
│       ├── LIA.wav
│       ├── JACK.wav
│       ├── BLAZE.wav
│       ├── CRUM.wav
│       └── GANG_MEMBER.wav
├── audio/
│   ├── segments_v2/             ← Chatterbox clip output
│   └── audiobook_v2_FINAL.wav   ← final stitch
└── PROJECT.md                   ← this file
```

---

## Open Questions (decide before M3)

1. **Jack's pitch shift**: do we pitch-shift in post, or try to get it right from the seed?
2. **GANG_MEMBER whisper** (S05-025): separate whispery reference, or lower exaggeration?
3. **Chatterbox Turbo vs Original**: Turbo has more paralinguistic tags; Original has the
   exaggeration slider. We may need both depending on the line.
4. **Dia (Nari Labs)**: research flagged this as a new dialogue-oriented model with
   `(laughs)`, `(gasps)` tags and voice cloning. Worth a 30-min evaluation before M1
   if richer tags matter.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-11 | Switch from OmniVoice to Chatterbox | Voice consistency (cloning), MIT, MPS confirmed |
| 2026-04-11 | Seed approach for characters | OmniVoice as seed factory, Chatterbox as generator |
| 2026-04-11 | Punctuation-based emotion where tags insufficient | Keeps original words, manipulates delivery |
| 2026-04-11 | Removed Dia from consideration | CUDA-only, 2-speaker max per call, Mac ARM is a TODO |
| 2026-04-11 | Deep Orpheus research — was underselling it | See model comparison section |
| 2026-04-11 | Under evaluation: Orpheus + Qwen3-TTS hybrid | Orpheus for adults (named voices = zero-effort consistency), Qwen3-TTS for Jack (voice design → child voice) |
