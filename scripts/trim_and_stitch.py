#!/usr/bin/env python3
"""
Trim both ends of each clip then stitch — performance-aware pausing.

Pauses come from PAUSE_MAP below, which was authored with a performer's eye:
each value reflects the dramatic weight of that moment, not a fixed rule.
Attribution micro-lines ("Lia said,") are kept tight (0.20s).
Revelations, confessions, and deaths get breathing room.

Fallback for any clip not in PAUSE_MAP: DEFAULT_PAUSE (0.40s).

Usage:
  .venv/bin/python trim_and_stitch.py 1             # Scene 1
  .venv/bin/python trim_and_stitch.py 1 2 3         # Scenes 1–3
  .venv/bin/python trim_and_stitch.py --all         # Full audiobook
"""
import re
import sys
import numpy as np
import soundfile as sf
from pathlib import Path

BASE   = Path(__file__).parent
SCRIPT = BASE / "audiobook_script.md"
SEGS   = BASE / "audio" / "segments_qwen"
OUT    = BASE / "audio"

SR = 24_000
DEFAULT_PAUSE = 0.40   # fallback for any clip not in PAUSE_MAP

# ── Trim tuning ───────────────────────────────────────────────────────────────
FRAME_MS = 5

# HEAD (leading)
H_SPEECH_FRAC    = 0.12
H_SPEECH_SUS_MS  = 30
H_SILENCE_FRAC   = 0.05
H_LOOKBACK_MS    = 300
H_PAD_MS         = 3

# TAIL (trailing) — conservative so quiet trailing words aren't clipped
T_SPEECH_FRAC    = 0.07
T_SPEECH_SUS_MS  = 15
T_SILENCE_FRAC   = 0.03
T_SILENCE_SUS_MS = 80
T_LOOKFWD_MS     = 400

_fn = int(SR * FRAME_MS / 1000)

def _sus(ms):  return int(ms / FRAME_MS)
def _pad(ms):  return int(SR * ms / 1000)

def _rms_frames(audio):
    n = (len(audio) // _fn) * _fn
    return np.sqrt(np.mean(audio[:n].reshape(-1, _fn) ** 2, axis=1))

# ── Performance-aware pause map ───────────────────────────────────────────────
# Each value = seconds of silence BEFORE that clip.
# Authored with a performer's eye — silence is an instrument.
PAUSE_MAP = {
    # ── Scene 1 — The Apartment ───────────────────────────────────────────────
    "S01_001_LIA.wav":      0.50,  # story opens — let the listener arrive
    "S01_002_NARRATOR.wav": 0.20,  # attribution glue
    "S01_003_CHASE.wav":    0.40,  # dismissive deflection
    "S01_004_NARRATOR.wav": 0.20,  # attribution glue
    "S01_005_NARRATOR.wav": 0.45,  # world-building — listener needs to SEE the city
    "S01_006_LIA.wav":      0.65,  # she's been stewing — weight of concern
    "S01_007_NARRATOR.wav": 0.20,  # attribution glue
    "S01_008_CHASE.wav":    0.40,  # confrontational pivot
    "S01_009_NARRATOR.wav": 0.20,  # attribution glue
    "S01_010_CHASE.wav":    0.65,  # "What I want doesn't matter" — self-sacrifice
    "S01_011_LIA.wav":      0.60,  # tenderness answering pain — let his words settle
    "S01_012_CHASE.wav":    0.45,  # stone-wall grunt + deflection
    "S01_013_LIA.wav":      0.90,  # BOMBSHELL — "I know you've been working for the Scavs"
    "S01_014_NARRATOR.wav": 0.25,  # she cuts him off — tight, urgent
    "S01_015_LIA.wav":      0.55,  # plea — "how do you think Jack feels"
    "S01_016_CHASE.wav":    0.70,  # "a little late to stop" — admission of being trapped
    "S01_017_NARRATOR.wav": 0.20,  # attribution glue
    "S01_018_LIA.wav":      0.65,  # "It's never too late" — hope against despair
    "S01_019_NARRATOR.wav": 0.45,  # sigh, head in palm — body language of defeat
    "S01_020_CHASE.wav":    1.10,  # CONFESSION — "I've killed people, Lia" — maximum dread
    "S01_021_LIA.wav":      0.80,  # "I've seen the blood" — she already knew, devastating calm
    "S01_022_CHASE.wav":    0.60,  # "powerful people" — raising the stakes
    "S01_023_NARRATOR.wav": 0.20,  # attribution glue (mid-sentence bridge)
    "S01_024_CHASE.wav":    0.15,  # continuation — tight with attribution
    "S01_025_LIA.wav":      0.60,  # hopeful pivot — "So we'll move"
    "S01_026_NARRATOR.wav": 0.20,  # attribution glue
    "S01_027_LIA.wav":      0.15,  # continuation — same breath as attribution
    "S01_028_CHASE.wav":    0.55,  # vulnerable — "You really think so?" first crack in armor
    "S01_029_LIA.wav":      0.40,  # reassurance — gentle
    "S01_030_NARRATOR.wav": 0.20,  # attribution glue
    "S01_031_CHASE.wav":    0.40,  # practical — easing tension
    "S01_032_LIA.wav":      0.40,  # practical — planning mode
    "S01_033_CHASE.wav":    0.40,  # alarmed at "dolls"
    "S01_034_NARRATOR.wav": 0.20,  # attribution glue
    "S01_035_CHASE.wav":    0.15,  # continuation — tight
    "S01_036_LIA.wav":      0.55,  # self-sacrifice — mirror of his earlier line
    "S01_037_CHASE.wav":    0.40,  # quiet agreement
    "S01_038_NARRATOR.wav": 0.20,  # attribution glue
    "S01_039_CHASE.wav":    0.15,  # continuation — tight
    "S01_040_LIA.wav":      0.55,  # emotional gratitude — argument resolving, warmth
    "S01_041_NARRATOR.wav": 0.35,  # the hug — physical tenderness, gentle
    "S01_042_JACK.wav":     0.90,  # TONAL SHIFT — child's voice breaks the adult world open
    "S01_043_NARRATOR.wav": 0.20,  # attribution glue
    "S01_044_CHASE.wav":    0.40,  # parental reflex
    "S01_045_NARRATOR.wav": 0.20,  # attribution glue
    "S01_046_JACK.wav":     0.40,  # sweet complaint
    "S01_047_NARRATOR.wav": 0.60,  # loaded glance — FEEL what that look between parents means
    "S01_048_CHASE.wav":    0.40,  # warm parenting — covering the darkness
    "S01_049_NARRATOR.wav": 0.35,  # THE STUFFED ANIMAL appears — foreshadowing planted
    "S01_050_CHASE.wav":    0.35,  # "found this at work" — dramatic irony, keep breezy
    "S01_051_NARRATOR.wav": 0.35,  # transition — leading Jack to bed
    "S01_052_JACK.wav":     0.35,  # innocent wonder
    "S01_053_CHASE.wav":    0.35,  # warm continuation
    "S01_054_NARRATOR.wav": 0.65,  # BLOOD STAINS on jacket — child sees it; dramatic irony
    "S01_055_JACK.wav":     0.40,  # quiet "Yes." — innocence unaware
    "S01_056_CHASE.wav":    0.55,  # "want me to tell you a story?" — fatherly warmth before the storm

    # ── Scene 2 — The Execution ───────────────────────────────────────────────
    "S02_001_NARRATOR.wav":    1.15,  # SCENE CUT — from bedtime to gun barrel; whiplash needs space
    "S02_002_BLAZE.wav":       0.70,  # first words from a killer — gun-to-head image must burn
    "S02_003_NARRATOR.wav":    0.20,  # attribution glue
    "S02_004_CRUM.wav":        0.35,  # terrified stammering — panicked, quick
    "S02_005_NARRATOR.wav":    0.20,  # attribution glue
    "S02_006_BLAZE.wav":       0.60,  # "I remember you saying you could handle him" — noose tightening
    "S02_007_NARRATOR.wav":    0.20,  # trigger squeeze — tight, mechanical
    "S02_008_CRUM.wav":        0.25,  # desperate plea — urgent, comes fast
    "S02_009_NARRATOR.wav":    0.20,  # attribution glue
    "S02_010_NARRATOR.wav":    1.15,  # EXECUTION — bullet through skull; silence before violence
    "S02_011_BLAZE.wav":       0.95,  # first words after murder — let the death ring in listener's ears
    "S02_012_NARRATOR.wav":    0.20,  # attribution glue
    "S02_013_NARRATOR.wav":    0.55,  # new character steps forward — tension of who speaks next
    "S02_014_GANG_MEMBER.wav": 0.35,  # intel — careful not to end up like Crum
    "S02_015_NARRATOR.wav":    0.30,  # Blaze turns — physical menace
    "S02_016_BLAZE.wav":       0.60,  # "Where." one word — let the silence sharpen it
    "S02_017_GANG_MEMBER.wav": 0.35,  # answering fast — survival instinct
    "S02_018_NARRATOR.wav":    0.35,  # holstering gun — slight release
    "S02_019_BLAZE.wav":       0.65,  # "We have a Daemon to catch" — ominous closer

    # ── Scene 3 — The Search ─────────────────────────────────────────────────
    "S03_001_NARRATOR.wav":    1.00,  # SCENE CUT — tactical sweep begins
    "S03_002_NARRATOR.wav":    0.45,  # building search — continuation of tactical narration
    "S03_003_BLAZE.wav":       0.40,  # phone call — businesslike
    "S03_004_NARRATOR.wav":    0.20,  # attribution glue
    "S03_005_GANG_MEMBER.wav": 0.35,  # tactical report
    "S03_006_BLAZE.wav":       0.40,  # command
    "S03_007_GANG_MEMBER.wav": 0.55,  # "There's something else, sir" — hesitation signals dread
    "S03_008_NARRATOR.wav":    0.20,  # attribution glue
    "S03_009_GANG_MEMBER.wav": 0.25,  # "bloodsoaked cloth" — hesitation built the tension; this lands tight
    "S03_010_NARRATOR.wav":    0.75,  # Blaze's rage — internal earthquake; listener sits with it
    "S03_011_BLAZE.wav":       0.55,  # controlled response — rage through gritted teeth
    "S03_012_NARRATOR.wav":    0.20,  # attribution glue
    "S03_013_GANG_MEMBER.wav": 0.45,  # "it's a match" — confirmation of worst fears

    # ── Scene 4 — The Bedtime Story ───────────────────────────────────────────
    "S04_001_CHASE.wav":       1.05,  # SCENE CUT — whiplash: blood evidence → bedtime story
    "S04_002_NARRATOR.wav":    0.20,  # attribution glue
    "S04_003_CHASE.wav":       0.60,  # "worst thing he did was have a daughter" — story turns dark
    "S04_004_JACK.wav":        0.40,  # innocent question — child logic
    "S04_005_NARRATOR.wav":    0.20,  # attribution glue
    "S04_006_CHASE.wav":       0.55,  # "tried to sell her" — heavy delivered gently
    "S04_007_JACK.wav":        0.35,  # "That's so mean!" — quick, visceral child horror
    "S04_008_NARRATOR.wav":    0.20,  # attribution glue
    "S04_009_JACK.wav":        0.50,  # "not a good dad like YOU" — dramatic irony stabs
    "S04_010_NARRATOR.wav":    0.20,  # attribution glue
    "S04_011_CHASE.wav":       0.35,  # bittersweet laughter — light, weight underneath
    "S04_012_NARRATOR.wav":    0.20,  # "He paused" — attribution; next segment carries the beat
    "S04_013_CHASE.wav":       0.55,  # "the story has a hero" — Chase recasting himself
    "S04_014_JACK.wav":        0.35,  # "Angel!" — excited, quick
    "S04_015_NARRATOR.wav":    0.20,  # attribution glue
    "S04_016_CHASE.wav":       0.55,  # the rescue — listener knows this IS the story
    "S04_017_JACK.wav":        0.35,  # "Yaaay!" — pure joy, quick
    "S04_018_NARRATOR.wav":    0.20,  # attribution glue
    "S04_019_CHASE.wav":       0.75,  # THE STUFFED ANIMAL — "missing an ear" — fuse is lit
    "S04_020_JACK.wav":        0.65,  # "That's like my one" — goosebumps; listener connects dots
    "S04_021_NARRATOR.wav":    0.20,  # attribution glue
    "S04_022_CHASE.wav":       0.40,  # "The end!" — wrapping up, light
    "S04_023_NARRATOR.wav":    0.20,  # attribution glue
    "S04_024_CHASE.wav":       0.60,  # "I'll be here all day tomorrow" — promise he cannot keep

    # ── Scene 5 — The Chamber ─────────────────────────────────────────────────
    "S05_001_NARRATOR.wav":    1.00,  # SCENE CUT — back to Blaze, hunter mode
    "S05_002_NARRATOR.wav":    0.45,  # footage review — procedural
    "S05_003_NARRATOR.wav":    0.40,  # arrival at building — transition
    "S05_004_GANG_MEMBER.wav": 0.35,  # tactical report
    "S05_005_NARRATOR.wav":    0.20,  # attribution glue
    "S05_006_GANG_MEMBER.wav": 0.50,  # "location of Daemon's house" — stakes raised
    "S05_007_BLAZE.wav":       0.40,  # command — controlled
    "S05_008_GANG_MEMBER.wav": 0.35,  # acknowledgment
    "S05_009_NARRATOR.wav":    0.40,  # moving through building — building tension
    "S05_010_BLAZE.wav":       0.55,  # "Blood, smells like it" — ominous sensory
    "S05_011_NARRATOR.wav":    0.20,  # attribution glue
    "S05_012_GANG_MEMBER.wav": 0.35,  # theory about cloth
    "S05_013_BLAZE.wav":       0.40,  # "No, this is different" — correction
    "S05_014_NARRATOR.wav":    0.30,  # walking to bathroom — physical transition
    "S05_015_BLAZE.wav":       0.35,  # "More of it here" — building
    "S05_016_GANG_MEMBER.wav": 0.35,  # pushback
    "S05_017_BLAZE.wav":       0.35,  # "And?" — terse
    "S05_018_GANG_MEMBER.wav": 0.30,  # "Nothing" — quick
    "S05_019_BLAZE.wav":       0.35,  # superiority
    "S05_020_NARRATOR.wav":    0.25,  # wall investigation — follows his line directly
    "S05_021_BLAZE.wav":       0.40,  # "Told you" — satisfied, brief
    "S05_022_NARRATOR.wav":    0.55,  # cannon arm + blast — spectacle needs buildup
    "S05_023_NARRATOR.wav":    1.20,  # THE CORPSE — mutilated child in blood; MAXIMUM space before horror
    "S05_024_NARRATOR.wav":    0.70,  # men whisper — aftermath; horror settling
    "S05_025_GANG_MEMBER.wav": 0.60,  # "How old was she?" — question no one wants answered
    "S05_026_NARRATOR.wav":    0.20,  # attribution glue
    "S05_027_BLAZE.wav":       1.10,  # "She was only eight years old" — eerily flat, devastating
    "S05_028_NARRATOR.wav":    0.20,  # attribution glue
    "S05_029_BLAZE.wav":       0.75,  # pivot to revenge — grief → mission; tone shift
    "S05_030_GANG_MEMBER.wav": 0.35,  # practical response
    "S05_031_BLAZE.wav":       0.55,  # "don't mess with the Daemon" — menacing restraint
    "S05_032_NARRATOR.wav":    0.20,  # attribution glue + carrying the corpse
    "S05_033_BLAZE.wav":       0.80,  # "He's all mine." — cold promise of personal violence

    # ── Scene 6 — Insomnia ────────────────────────────────────────────────────
    "S06_001_NARRATOR.wav":    1.10,  # SCENE CUT — from a father holding his dead child to a father
                                      #              lying awake. The parallel is devastating.

    # ── Scene 7 — The Knock ───────────────────────────────────────────────────
    "S07_001_NARRATOR.wav":    1.05,  # SCENE CUT — child's POV, ominous awakening
    "S07_002_CHASE.wav":       0.60,  # "I've never seen her!" — desperation, bad lying
    "S07_003_NARRATOR.wav":    0.25,  # Jack's thought — "Why was he lying?" quick, child
    "S07_004_BLAZE.wav":       0.80,  # BLAZE AT THE DOOR — "Don't do this, Daemon" — worlds collide
    "S07_005_NARRATOR.wav":    0.20,  # attribution glue
    "S07_006_CHASE.wav":       0.35,  # continued denial — urgent, quick
    "S07_007_NARRATOR.wav":    0.25,  # Jack's thought — "such a bad liar" — innocent read
    "S07_008_NARRATOR.wav":    0.40,  # footsteps — Lia waking, tension spreading
    "S07_009_LIA.wav":         0.35,  # whispered question — hushed, alert
    "S07_010_NARRATOR.wav":    0.20,  # attribution glue
    "S07_011_JACK.wav":        0.30,  # "I don't know" — simple, child
    "S07_012_NARRATOR.wav":    0.35,  # Lia moves to door — stepping into danger
    "S07_013_BLAZE.wav":       0.70,  # "well well well, you're married?" — predator finding more prey
    "S07_014_NARRATOR.wav":    0.20,  # attribution glue
    "S07_015_LIA.wav":         0.40,  # Lia challenges — bravery or naivety
    "S07_016_BLAZE.wav":       0.65,  # "just a friend from work" — sinister irony
    "S07_017_NARRATOR.wav":    0.20,  # "he paused" — atmospheric beat
    "S07_018_BLAZE.wav":       0.20,  # continuation — calculated, tight
    "S07_019_NARRATOR.wav":    0.55,  # door opens, heavy footsteps — the home is violated
    "S07_020_BLAZE.wav":       0.65,  # "You have a kid too?" — predatory observation
    "S07_021_NARRATOR.wav":    0.20,  # attribution glue
    "S07_022_BLAZE.wav":       0.45,  # "You've been busy" — dark amusement
    "S07_023_NARRATOR.wav":    0.35,  # takes seat at head of table — power positioning
    "S07_024_NARRATOR.wav":    0.30,  # family sits at other end
    "S07_025_CHASE.wav":       0.55,  # "let me put the kid to sleep, Blaze" — protective desperation
    "S07_026_NARRATOR.wav":    0.20,  # attribution glue
    "S07_027_BLAZE.wav":       0.90,  # "No, the kid stays." — absolute power, chilling

    # ── Scene 8 — The End ─────────────────────────────────────────────────────
    "S08_001_NARRATOR.wav":    1.15,  # FINAL SCENE — brace the listener; everything converges
    "S08_002_BLAZE.wav":       0.70,  # eyes on the stuffed animal — recognition dawning
    "S08_003_NARRATOR.wav":    0.20,  # attribution glue
    "S08_004_JACK.wav":        0.55,  # "My dad brought it from work!" — innocent words seal a death sentence
    "S08_005_NARRATOR.wav":    1.10,  # "Rage." — one word; maximum silence before detonation
    "S08_006_NARRATOR.wav":    0.60,  # turns toward the Daemon — predator locks on
    "S08_007_BLAZE.wav":       0.90,  # "You monster" — accusation from monster to monster
    "S08_008_NARRATOR.wav":    0.70,  # memory flood — 3rd birthday, joy, then the mutilated corpse
    "S08_009_NARRATOR.wav":    1.20,  # THE MURDERS — wife shot, Chase killed; silence absorbs violence
    "S08_010_NARRATOR.wav":    1.10,  # turns to the boy — will he kill a child? heart stops
    "S08_011_BLAZE.wav":       1.20,  # "Come with me, boy" — final line; devastating mercy; let it echo
}

# ── Head trim ─────────────────────────────────────────────────────────────────
def find_onset(audio):
    rms  = _rms_frames(audio)
    peak = rms.max()
    if peak < 1e-6: return 0
    sp_thr  = peak * H_SPEECH_FRAC
    sil_thr = peak * H_SILENCE_FRAC
    sus     = _sus(H_SPEECH_SUS_MS)
    run, sf_ = 0, None
    for i, r in enumerate(rms):
        if r >= sp_thr:
            run += 1
            if run >= sus: sf_ = i - sus + 1; break
        else: run = 0
    if sf_ is None: return 0
    for i in range(sf_, max(0, sf_ - _sus(H_LOOKBACK_MS)), -1):
        if rms[i] < sil_thr:
            return min(i * _fn + _pad(H_PAD_MS), len(audio) - 1)
    return sf_ * _fn

# ── Tail trim ─────────────────────────────────────────────────────────────────
def find_tail(audio):
    rms  = _rms_frames(audio)
    peak = rms.max()
    if peak < 1e-6: return len(audio)
    sp_thr   = peak * T_SPEECH_FRAC
    sil_thr  = peak * T_SILENCE_FRAC
    sp_sus   = _sus(T_SPEECH_SUS_MS)
    sil_sus  = _sus(T_SILENCE_SUS_MS)
    run, se  = 0, None
    for i in range(len(rms) - 1, -1, -1):
        if rms[i] >= sp_thr:
            run += 1
            if run >= sp_sus: se = i + sp_sus - 1; break
        else: run = 0
    if se is None: return len(audio)
    run, end = 0, min(len(rms), se + _sus(T_LOOKFWD_MS))
    for i in range(se, end):
        if rms[i] < sil_thr:
            run += 1
            if run >= sil_sus:
                cut = (i - sil_sus + 1) * _fn - _pad(3)
                return max(se * _fn, cut)
        else: run = 0
    return se * _fn

def silence(sec): return np.zeros(int(SR * sec), dtype=np.float32)

# ── Core ──────────────────────────────────────────────────────────────────────
def stitch_scenes(scenes, out_path):
    all_clips = sorted(SEGS.glob("S*.wav"))
    if scenes:
        all_clips = [f for f in all_clips if int(f.name[1:3]) in scenes]
    if not all_clips:
        print(f"No clips for scenes {scenes}"); return

    print(f"Processing {len(all_clips)} clips → {out_path.name}\n")
    chunks   = [silence(1.0)]
    head_log = []
    tail_log = []

    for path in all_clips:
        audio, _ = sf.read(str(path), dtype="float32")
        if audio.ndim > 1: audio = audio.mean(axis=1)

        onset    = find_onset(audio)
        tail_end = find_tail(audio)
        head_ms  = onset / SR * 1000
        tail_ms  = (len(audio) - tail_end) / SR * 1000
        clipped  = audio[onset:tail_end]

        head_log.append((path.name, head_ms))
        tail_log.append((path.name, tail_ms))

        pause = PAUSE_MAP.get(path.name, DEFAULT_PAUSE)
        chunks.append(silence(pause))
        chunks.append(clipped)

        parts = []
        if head_ms > 10: parts.append(f"head -{head_ms:.0f}ms")
        if tail_ms > 10: parts.append(f"tail -{tail_ms:.0f}ms")
        detail = f"  {'|'.join(parts)}" if parts else ""
        print(f"  [{pause:.2f}s] {path.name}{detail}")

    chunks.append(silence(2.0))
    full = np.concatenate(chunks)
    sf.write(str(out_path), full, SR)

    dur = len(full) / SR
    mb  = out_path.stat().st_size / 1_048_576
    print(f"\n  ✓ {out_path.name}  —  {int(dur//60)}m {int(dur%60)}s  ({mb:.1f} MB)")
    h = [(n, ms) for n, ms in head_log if ms > 10]
    t = [(n, ms) for n, ms in tail_log if ms > 10]
    print(f"\n  Head trimmed: {len(h)}/{len(all_clips)}  avg {sum(m for _,m in h)/max(len(h),1):.0f}ms  max {max((m for _,m in h), default=0):.0f}ms")
    print(f"  Tail trimmed: {len(t)}/{len(all_clips)}  avg {sum(m for _,m in t)/max(len(t),1):.0f}ms  max {max((m for _,m in t), default=0):.0f}ms")

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(1)
    if args == ["--all"]:
        scenes, name = list(range(1,9)), "audiobook_trimmed_FINAL.wav"
    elif all(a.isdigit() for a in args):
        scenes = [int(a) for a in args]
        name   = f"scene{'_'.join(args)}_trimmed.wav"
    else:
        print("Usage: trim_and_stitch.py <scene> [...] | --all"); sys.exit(1)
    stitch_scenes(scenes, OUT / name)

if __name__ == "__main__":
    main()
