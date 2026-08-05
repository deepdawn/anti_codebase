import os
import re

def refactor_project_paths(base_dir):
    py_pattern = re.compile(r'([fF]?)([\'"])/Users/galaxy(?:\.jang)?(/.*?)\2')
    sh_pattern = re.compile(r'/Users/galaxy(?:\.jang)?')
    
    modified_py = 0
    modified_sh = 0

    for root, dirs, files in os.walk(base_dir):
        if '.venv' in root or '.git' in root or '.etc' in root or '.idea' in root:
            continue
            
        for file in files:
            file_path = os.path.join(root, file)
            
            if file.endswith('.py'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    if py_pattern.search(content):
                        def replacer(match):
                            prefix = match.group(1)
                            quote = match.group(2)
                            rest = match.group(3)
                            inner_quote = "'" if quote == '"' else '"'
                            return f'f{quote}{{os.path.expanduser({inner_quote}~{inner_quote})}}{rest}{quote}'
                            
                        new_content = py_pattern.sub(replacer, content)
                        
                        if 'import os' not in new_content:
                            new_content = 'import os\n' + new_content
                            
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        modified_py += 1
                        print(f"[PY] Refactored: {file_path}")
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    
            elif file.endswith('.sh'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    if sh_pattern.search(content):
                        new_content = sh_pattern.sub('$HOME', content)
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        modified_sh += 1
                        print(f"[SH] Refactored: {file_path}")
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    
    print(f"Refactoring complete. Modified {modified_py} Python files and {modified_sh} Bash files.")

if __name__ == '__main__':
    project_dir = f'{os.path.expanduser("~")}/anti_codebase'
    refactor_project_paths(project_dir)
