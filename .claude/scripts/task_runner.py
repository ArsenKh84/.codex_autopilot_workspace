#!/usr/bin/env python3
"""
task_runner.py — Build & execute project task trees with Claude
Usage: python3 task_runner.py --goal "build a Swift todo app"
       python3 task_runner.py --tree TASK_TREE.json --resume
"""
import os, sys, json, time, subprocess, argparse, shutil
from pathlib import Path
try: from colorama import Fore,Style,init; init(); G=Fore.GREEN;Y=Fore.YELLOW;R=Fore.RED;C=Fore.CYAN;B=Fore.BLUE;W=Style.RESET_ALL
except: G=Y=R=C=B=W=""

ICONS = {"pending":f"{Y}○{W}","running":f"{C}◉{W}","done":f"{G}✓{W}","failed":f"{R}✗{W}","skipped":f"−"}

class Task:
    def __init__(self, d, parent=None):
        self.id=d.get("id","t"); self.title=d.get("title",self.id)
        self.description=d.get("description",""); self.prompt=d.get("prompt",self.description)
        self.lang=d.get("lang",""); self.depends_on=d.get("depends_on",[])
        self.status=d.get("status","pending"); self.output=d.get("output","")
        self.retries=d.get("retries",0); self.max_retries=d.get("max_retries",2)
        self.children=[Task(c,self) for c in d.get("children",[])]
    def to_dict(self):
        return {"id":self.id,"title":self.title,"description":self.description,"prompt":self.prompt,
                "lang":self.lang,"depends_on":self.depends_on,"status":self.status,"output":self.output,
                "retries":self.retries,"max_retries":self.max_retries,"children":[c.to_dict() for c in self.children]}

def flat(t):
    r=[t]
    for c in t.children: r+=flat(c)
    return r

def print_tree(t, indent=0):
    pad="  "*indent; con="└─ " if indent>0 else ""
    print(f"{pad}{con}{ICONS.get(t.status,'?')} {B}{t.id}{W}: {t.title}")
    for c in t.children: print_tree(c, indent+1)

def save(root, path):
    json.dump(root.to_dict(), open(path,"w"), indent=2)

def run_task(task, work_dir):
    if shutil.which("claude"):
        prompt = f"[{task.lang}] {task.prompt}" if task.lang else task.prompt
        r = subprocess.run(["claude","--print","--dangerously-skip-permissions", prompt],
            cwd=work_dir, capture_output=True, text=True, timeout=120)
        return r.returncode==0, r.stdout+r.stderr
    else:
        # Fallback to crosscheck
        script=os.path.expanduser("~/.claude/scripts/crosscheck.py")
        r=subprocess.run([sys.executable,script,task.prompt,"--lang",task.lang or "python","--retries","2"],
            capture_output=True,text=True,timeout=180)
        return r.returncode==0, r.stdout

def gen_tree(goal):
    print(f"\n{C}Generating task tree for: {goal}{W}\n")
    SYS='Return ONLY valid JSON (no markdown) task tree: {"id":"root","title":"Project","description":"","prompt":"","lang":"","depends_on":[],"status":"pending","children":[{"id":"task_1","title":"","description":"","prompt":"<exact claude prompt>","lang":"python","depends_on":[],"status":"pending","max_retries":2,"children":[]}]}'
    try:
        import anthropic
        c=anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        r=c.messages.create(model="claude-sonnet-4-6",max_tokens=4096,system=SYS,
            messages=[{"role":"user","content":f"Task tree for: {goal}"}])
        raw=r.content[0].text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"{R}Error: {e}{W}")
        return {"id":"root","title":f"Project: {goal[:40]}","description":goal,"prompt":"","lang":"","depends_on":[],"status":"pending",
                "children":[{"id":"task_1","title":"Implement","description":goal,"prompt":goal,"lang":"python","depends_on":[],"status":"pending","max_retries":2,"children":[]}]}

def run_tree(root, work_dir, tree_file, dry=False):
    all_tasks=[t for t in flat(root) if t.id!="root"]
    print(f"\n{C}{'═'*50}\n  {root.title}\n{'═'*50}{W}")
    print_tree(root)
    if dry: print(f"\n{Y}Dry-run — no tasks executed{W}"); return
    for task in all_tasks:
        if task.status in ("done","skipped"): continue
        if any((next((t for t in all_tasks if t.id==d),None) or type('',(),{"status":"done"})()).status!="done" for d in task.depends_on):
            print(f"{Y}  ⏭ Skipping {task.id} — deps not ready{W}"); task.status="skipped"; continue
        print(f"\n{C}▶ {task.id}: {task.title}{W}")
        task.status="running"; save(root,tree_file)
        ok=False; out=""
        for i in range(task.max_retries+1):
            if i: print(f"  {Y}Retry {i}/{task.max_retries}...{W}")
            ok,out=run_task(task,work_dir)
            if ok: break
            task.retries+=1; time.sleep(2)
        task.output=out[:1000]; task.status="done" if ok else "failed"; save(root,tree_file)
        print(f"  {G}✓ Done{W}" if ok else f"  {R}✗ Failed{W}")
        if out.strip(): print(f"  {out[:150]}...")
    print(f"\n{C}{'═'*50}\n  Summary\n{'═'*50}{W}")
    print_tree(root)
    d=sum(1 for t in all_tasks if t.status=="done")
    f=sum(1 for t in all_tasks if t.status=="failed")
    print(f"\n  {G}Done: {d}/{len(all_tasks)}{W}   {R}Failed: {f}{W}\n")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--goal","-g"); p.add_argument("--tree","-t")
    p.add_argument("--dir","-d",default="."); p.add_argument("--resume",action="store_true")
    p.add_argument("--dry-run",action="store_true"); p.add_argument("--output","-o",default="TASK_TREE.json")
    a=p.parse_args()
    wd=os.path.abspath(a.dir); os.makedirs(wd,exist_ok=True)
    if a.tree and os.path.exists(a.tree):
        data=json.load(open(a.tree)); tf=a.tree
    elif a.goal:
        data=gen_tree(a.goal); tf=os.path.join(wd,a.output)
        save(Task(data),tf); print(f"{G}Tree saved: {tf}{W}")
    else:
        df=os.path.join(wd,"TASK_TREE.json")
        if os.path.exists(df): data=json.load(open(df)); tf=df
        else: p.print_help(); sys.exit(1)
    run_tree(Task(data), wd, tf, dry=a.dry_run)
