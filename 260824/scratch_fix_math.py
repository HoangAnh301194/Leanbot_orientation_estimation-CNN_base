import re

def main():
    try:
        with open('Readme.md', 'r', encoding='utf-8') as f:
            content = f.read()

        def repl(match):
            math_content = match.group(1).strip()
            return f'```math\n{math_content}\n```'

        new_content = re.sub(r'\$\$(.*?)\$\$', repl, content, flags=re.DOTALL)

        with open('Readme.md', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print('Successfully replaced math blocks.')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    main()
