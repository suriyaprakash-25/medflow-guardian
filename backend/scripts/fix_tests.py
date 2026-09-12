import os
import re

directory = r'd:\Vscode\VORTEXA 2\medflow\backend\tests'
# Match kwarg with preceding comma
pattern = re.compile(r',\s*enforcement_state_id=[^,\)\n]+')
# Match kwarg as first arg (with or without trailing comma)
pattern2 = re.compile(r'enforcement_state_id=[^,\)\n]+\s*,?\s*')
# Match query param in URLs
pattern3 = re.compile(r'&enforcement_state_id=[^&"\'\\]*')
pattern4 = re.compile(r'\?enforcement_state_id=[^&"\'\\]*&')
pattern5 = re.compile(r'\?enforcement_state_id=[^&"\'\\]*')

# For dictionary entries
pattern6 = re.compile(r',\s*"enforcement_state_id":\s*[^,\}\n]+')

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = pattern.sub('', content)
            new_content = pattern2.sub('', new_content)
            new_content = pattern3.sub('', new_content)
            new_content = pattern4.sub('?', new_content)
            new_content = pattern5.sub('', new_content)
            new_content = pattern6.sub('', new_content)

            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {filepath}")
