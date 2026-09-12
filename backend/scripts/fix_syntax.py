import os

files = ['tests/test_golden_workflow.py', 'tests/test_malware_quarantine.py']
for f in files:
    filepath = os.path.join('d:/Vscode/VORTEXA 2/medflow/backend', f)
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
    
    content = content.replace('purpose=TREATMENT&headers=auth', 'purpose=TREATMENT", headers=auth')
    content = content.replace('purpose=treatment&headers={', 'purpose=treatment", headers={')
    
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(content)
print("Syntax fixed")
