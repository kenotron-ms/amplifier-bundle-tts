    ---
    bundle:
      name: text-to-speech
      version: 2.0.0
      description: TTS for Amplifier — Dia (podcast), Qwen3-TTS (voice design/clone), Gemini TTS (cloud)

    includes:
      - bundle: text-to-speech:behaviors/dia
      - bundle: text-to-speech:behaviors/qwen3-tts
      - bundle: text-to-speech:behaviors/gemini-tts

    context:
      include:
        - text-to-speech:context/omnivoice-awareness.md
    ---