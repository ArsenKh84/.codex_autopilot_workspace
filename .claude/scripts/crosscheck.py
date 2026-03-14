#!/usr/bin/env python3
"""
crosscheck.py — Generate with Claude, review with GPT + DeepSeek, retry on fail
Usage: python3 crosscheck.py "your request" --lang python --retries 3
"""
import os, sys, json, time, argparse
try: from colorama import Fore,Style,init; init(); G=Fore.GREEN;Y=Fore.YELLOW;R=Fore.RED;C=Fore.CYAN;W=Style.RESET_ALL
except: G=Y=R=C=W=""

def call_claude(prompt, system="You are an expert software engineer. Return only code, no explanation."):
    try:
        import anthropic
        c = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        r = c.messages.create(model="claude-sonnet-4-6", max_tokens=4096,
            system=system, messages=[{"role":"user","content":prompt}])
        return r.content[0].text
    except Exception as e: print(f"{R}Claude error: {e}{W}"); return ""

def call_openai(prompt, system):
    if not os.environ.get("OPENAI_API_KEY"): print(f"{Y}! OPENAI_API_KEY not set — skipping{W}"); return "SKIP"
    try:
        import openai
        c = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        r = c.chat.completions.create(model="gpt-4o",
            messages=[{"role":"system","content":system},{"role":"user","content":prompt}], max_tokens=2048)
        return r.choices[0].message.content
    except Exception as e: print(f"{R}OpenAI error: {e}{W}"); return ""

def call_deepseek(prompt, system):
    if not os.environ.get("DEEPSEEK_API_KEY"): print(f"{Y}! DEEPSEEK_API_KEY not set — skipping{W}"); return "SKIP"
    try:
        import openai
        c = openai.OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
        r = c.chat.completions.create(model="deepseek-coder",
            messages=[{"role":"system","content":system},{"role":"user","content":prompt}], max_tokens=2048)
        return r.choices[0].message.content
    except Exception as e: print(f"{R}DeepSeek error: {e}{W}"); return ""

REVIEW_SYS = 'Respond ONLY in JSON: {"verdict":"PASS"|"FAIL","score":0-100,"issues":[],"suggestions":[],"fixed_code":""}'

def parse_v(r):
    try:
        c = r.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(c)
    except: return {"verdict":"FAIL","score":0,"issues":["parse error"],"suggestions":[],"fixed_code":""}

def crosscheck(request, lang="python", max_retries=3):
    print(f"\n{C}{'─'*50}{W}\n{C}  Cross-Check: {request[:60]}{W}\n{C}{'─'*50}{W}")
    code = ""; all_issues = []; all_suggestions = []
    for attempt in range(1, max_retries+1):
        print(f"\n{C}Attempt {attempt}/{max_retries}{W}")
        if attempt == 1:
            prompt = f"Write {lang} code for: {request}\nReturn ONLY the code."
        else:
            fixes = "\n".join(f"- {i}" for i in all_issues)
            prompt = f"Fix this {lang} code for: {request}\nIssues:\n{fixes}\n\nOriginal:\n```\n{code}\n```\nReturn ONLY fixed code."
        print(f"{C}→ Generating with Claude...{W}")
        code = call_claude(prompt)
        if not code: print(f"{R}✗ Claude returned empty{W}"); continue
        print(code[:500] + ("\n..." if len(code)>500 else ""))
        all_issues = []; all_suggestions = []; all_passed = True
        rev_prompt = f'Review this {lang} code for: "{request}"\n```{lang}\n{code}\n```'
        for name, fn in [("GPT-4", call_openai), ("DeepSeek", call_deepseek)]:
            print(f"{C}→ Reviewing with {name}...{W}", end=" ")
            raw = fn(rev_prompt, REVIEW_SYS)
            if raw == "SKIP": print(f"{Y}skipped{W}"); continue
            v = parse_v(raw)
            badge = f"{G}PASS ✓{W}" if v["verdict"]=="PASS" else f"{R}FAIL ✗{W}"
            print(f"{badge}  score: {v.get('score',0)}/100")
            if v["verdict"]=="FAIL":
                all_passed = False
                all_issues += v.get("issues",[])
                all_suggestions += v.get("suggestions",[])
        if all_passed:
            print(f"\n{G}✓ All checks passed on attempt {attempt}!{W}")
            os.makedirs(os.path.expanduser("~/.claude/crosscheck_outputs"), exist_ok=True)
            from datetime import datetime
            fname = os.path.expanduser(f"~/.claude/crosscheck_outputs/{datetime.now().strftime('%Y%m%d_%H%M%S')}_PASS.{lang}")
            open(fname,"w").write(f"# {request}\n\n{code}")
            print(f"{G}Saved: {fname}{W}")
            return code
        else:
            print(f"{R}Issues: {all_issues}{W}")
            if attempt < max_retries: time.sleep(1)
    print(f"{Y}! Max retries reached. Best effort output above.{W}")
    return code

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("prompt", nargs="?")
    p.add_argument("--file", "-f")
    p.add_argument("--lang", "-l", default="python")
    p.add_argument("--retries", "-r", type=int, default=3)
    a = p.parse_args()
    txt = open(a.file).read() if a.file else a.prompt
    if not txt: p.print_help(); sys.exit(1)
    crosscheck(txt, lang=a.lang, max_retries=a.retries)
