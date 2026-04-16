---
bundle:
  name: omnivoice
  version: 1.0.0
  description: TTS for Amplifier — generate speech via OmniVoice (local, free) or Gemini TTS (cloud, fast)

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: omnivoice:behaviors/omnivoice
---
