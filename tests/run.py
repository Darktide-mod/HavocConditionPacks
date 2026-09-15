from pathlib import Path
import subprocess,sys,os
root=Path(__file__).resolve().parents[1]
for name in ('diy_frenzied_assault_tests.py','native_melee_resource_tests.py','native_melee_installer_tests.py','resource_only_installer_tests.py'):
    subprocess.run([sys.executable,str(root/'tests'/name)],cwd=root,env={**os.environ,'PYTHONIOENCODING':'utf-8'},check=True)
print('HavocConditionPacks checks passed')
