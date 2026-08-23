"""Quick unit checks for JSON repair without LM Studio."""

from src.llm_client import extractJsonObject


def main() -> None:
  samples = [
    '{"rumor":"x","anger":0.2,"hoarding":0.1,"riotRisk":0.05,"moodText":"ok",}',
    'Here you go:\n```json\n{"panic":0.5,"rumor":"a","intent":"hoard","localBias":"b"}\n```',
    'True talk {"rumor":"y","anger":True,"hoarding":0.1,"riotRisk":0.0,"moodText":"z"} end',
  ]
  for text in samples:
    parsed = extractJsonObject(text)
    assert isinstance(parsed, dict)
    print("ok", list(parsed.keys())[:3])
  print("EXTRACT_OK")


if __name__ == "__main__":
  main()
