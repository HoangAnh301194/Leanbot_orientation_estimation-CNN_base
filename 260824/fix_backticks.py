import re

with open('Readme.md', 'r', encoding='utf-8') as f:
    content = f.read()

# The file currently has:
# ``
# 
# `math
# [content]
# `
# 
# ``
# We need to replace it with:
# ```math
# [content]
# ```

# Regex to match this exact broken pattern
pattern = re.compile(r'``\n+\`math\n(.*?)\n\`\n+``', re.DOTALL)

def repl(m):
    return f'\n```math\n{m.group(1).strip()}\n```\n'

new_content = pattern.sub(repl, content)

# Clean up multiple blank lines
new_content = re.sub(r'\n{3,}', '\n\n', new_content)

with open('Readme.md', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Fixed backticks.')
