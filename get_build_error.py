import subprocess, os, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FRONTEND = r"e:\工作工作\text\person-info-system\frontend"
NODE = r"e:\工作工作\text\person-info-system\tools\node\node.exe"
VITE = os.path.join(FRONTEND, "node_modules", "vite", "bin", "vite.js")
OUT = os.path.join(r"e:\工作工作\text\person-info-system", "vite_build_output.txt")

env = os.environ.copy()
env["PATH"] = r"e:\工作工作\text\person-info-system\tools\node" + os.pathsep + env.get("PATH", "")

r = subprocess.run(
    [NODE, VITE, "build"],
    capture_output=True, text=True,
    encoding="utf-8", errors="replace",
    timeout=120, cwd=FRONTEND, env=env,
)

full_output = (r.stdout or "") + "\n==== STDERR ====\n" + (r.stderr or "")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(full_output)

print(f"EXIT CODE: {r.returncode}")
print(f"Full output saved to: {OUT}")
print()
print("=== FIRST 3000 chars (actual error messages usually here) ===")
print(full_output[:3000])
