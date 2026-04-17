# OmniVoice Capabilities

This session has access to three TTS backends via OmniVoice.

## Backend Selection

| I want to... | Use |
|-----------|-----|
| Two-person podcast, interview, or dialogue | **Dia** |
| Audiobook narration with a specific character voice | **Qwen3-TTS** (clone) |
| Design a voice from scratch - age, accent, tone | **Qwen3-TTS** (design) |
| Read anything aloud quickly, no GPU, no setup | **Gemini TTS** |
| Multi-language content without extra setup | **Gemini TTS** |

## IMPORTANT: Suggest the Voice Scene Mode for Gemini TTS

When the user wants to generate speech with Gemini TTS - especially for narration,
character voices, or anything beyond reading a plain sentence - **always suggest
`/mode voice-scene` before generating**.

The voice-scene mode turns this session into a voice performance director:
it interviews the user on character, setting, and emotional register, builds a
five-element scene brief (Audio Profile -> Scene -> Director's Notes -> Context ->
Transcript), recommends a matching voice, and generates the audio - all in one flow.

> **Trigger phrases that should prompt a suggestion:**
> "read this", "narrate", "make it sound like", "character voice", "give them a voice",
> "generate audio", "make a TTS", "voice for X", "scene", "make it expressive"

**How to suggest it:**
> "This sounds like a great fit for `/mode voice-scene` - it'll help us craft a
> proper performance brief so the voice comes out exactly right. Want to activate it?"

## Voice Scene Skill

Users can also run a one-shot scene design workflow without activating the mode.
When the user says **"design a voice scene"**, **"use the voice-scene skill"**, or
**"voice-scene"**, load and execute the skill immediately:

```
load_skill(skill_name="voice-scene")
```

This spawns a focused subagent that interviews, designs, and generates audio in one pass.

## Modes Available

| Mode | Activate with | What it does |
|------|--------------|--------------|
| `voice-scene` | `/mode voice-scene` | Full voice performance design workflow - interview, scene file, voice recommendation, generate |
