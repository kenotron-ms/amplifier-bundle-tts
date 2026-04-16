---
bundle:
  name: omnivoice
  version: 2.0.0
  description: TTS for Amplifier — Dia (podcast), Qwen3-TTS (voice design/clone), Gemini TTS (cloud)

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: omnivoice:behaviors/dia
  - bundle: omnivoice:behaviors/qwen3-tts
  - bundle: omnivoice:behaviors/gemini-tts
---
