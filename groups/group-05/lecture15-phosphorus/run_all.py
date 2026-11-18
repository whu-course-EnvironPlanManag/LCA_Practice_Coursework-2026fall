from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parent
for script in ['run.py','scenarios.py','audit.py','finish.py']:
    subprocess.run([sys.executable,str(root/script),*sys.argv[1:]],check=True)
