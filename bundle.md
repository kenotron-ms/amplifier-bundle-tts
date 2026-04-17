---
bundle:
  name: text-to-speech
  version: 2.0.0
  description: TTS for Amplifier — Gemini TTS (cloud, 30 voices, instant, no GPU)

includes:
  - bundle: text-to-speech:behaviors/gemini-tts

context:
  include:
    - text-to-speech:context/omnivoice-awareness.md
---
