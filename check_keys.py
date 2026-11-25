"""Shows which keys are filled in .env WITHOUT showing the keys themselves."""
from pathlib import Path

EXPECTED = ["GEMINI_API_KEY", "TAVILY_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY"]
env = Path(__file__).with_name(".env")
found = {}
for number, line in enumerate(env.read_text(encoding="utf-8-sig").splitlines(), 1):
    text = line.strip()
    if not text or text.startswith("#"):
        continue
    if "=" not in text:
        print(f"Line {number}: has no '=' sign, so it is ignored")
        continue
    name, value = text.split("=", 1)
    if name != name.strip():
        print(f"Line {number}: remove the space before '=' in {name.strip()}")
    value = value.strip().strip('"').strip("'")
    found[name.strip()] = value

print()
for name in EXPECTED:
    value = found.get(name, "")
    status = f"OK ({len(value)} characters)" if value else "MISSING"
    print(f"  {name:16} {status}")
others = [n for n in found if n not in EXPECTED and not n.startswith(("GEMINI_MODEL", "AI_", "GROQ_MODEL", "MISTRAL_MODEL"))]
if others:
    print("\n  Other names found:", ", ".join(others))
    if "GROK_API_KEY" in others:
        print("  -> 'GROK' should be spelled 'GROQ' (with a Q).")
print("\nYour keys were not shown. Close this window when done.")
