import re

with open('Readme.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace ```math ... ``` with $$ ... $$
def repl(m):
    math_content = m.group(1).strip()
    return f'\n$$\n{math_content}\n$$\n'

content = re.sub(r'```math\n(.*?)\n```', repl, content, flags=re.DOTALL)

with open('Readme.md', 'w', encoding='utf-8') as f:
    f.write(content)
print('Reverted math blocks to $$')
