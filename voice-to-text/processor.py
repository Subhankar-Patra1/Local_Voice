import anthropic

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a voice transcription post-processor.
The user just dictated text via voice. Clean it up:
1. Remove filler words (um, uh, like, you know, basically, so)
2. Fix grammar and capitalization
3. Add proper punctuation
4. Keep meaning and tone exactly as intended
5. Return ONLY the cleaned text — no explanation, no quotes
If already clean, return unchanged."""

def process(raw_text: str) -> str:
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": raw_text}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"[Processor] API error: {e} — using raw text")
        return raw_text
