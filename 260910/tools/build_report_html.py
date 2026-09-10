import argparse
import re
from pathlib import Path

import markdown


IMAGE_PATTERN = re.compile(r'(<img\b[^>]*\bsrc="([^"]+)"[^>]*>)')


def make_images_clickable(html_body: str) -> str:
    def replace_image(match):
        image_tag = match.group(1).replace('<img ', '<img loading="lazy" ', 1)
        image_source = match.group(2)
        return (
            f'<a class="image-link" href="{image_source}" '
            f'target="_blank" rel="noopener noreferrer">{image_tag}</a>'
        )

    return IMAGE_PATTERN.sub(replace_image, html_body)


def build_html(markdown_path: Path, output_path: Path) -> None:
    source = markdown_path.read_text(encoding='utf-8')
    converter = markdown.Markdown(
        extensions=['tables', 'fenced_code', 'toc', 'sane_lists'],
        extension_configs={'toc': {'permalink': True}},
        output_format='html5',
    )
    body = make_images_clickable(converter.convert(source))
    title_match = re.search(r'^#\s+(.+)$', source, re.MULTILINE)
    title = title_match.group(1) if title_match else markdown_path.stem
    document = f'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, "Segoe UI", Arial, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; color: #172033; background: #eef2f7; line-height: 1.65; }}
    .layout {{ display: grid; grid-template-columns: minmax(220px, 290px) minmax(0, 1fr); gap: 24px; max-width: 1500px; margin: 0 auto; padding: 24px; }}
    nav {{ position: sticky; top: 24px; align-self: start; max-height: calc(100vh - 48px); overflow: auto; padding: 20px; background: white; border: 1px solid #d9e0ea; border-radius: 14px; box-shadow: 0 8px 30px rgba(27, 39, 64, 0.08); }}
    nav h2 {{ margin-top: 0; font-size: 1.05rem; }}
    nav ul {{ padding-left: 18px; }}
    nav a {{ color: #175cd3; text-decoration: none; }}
    nav a:hover {{ text-decoration: underline; }}
    main {{ min-width: 0; padding: 34px 44px; background: white; border: 1px solid #d9e0ea; border-radius: 14px; box-shadow: 0 8px 30px rgba(27, 39, 64, 0.08); }}
    h1, h2, h3, h4, h5 {{ color: #101828; line-height: 1.3; scroll-margin-top: 20px; }}
    h1 {{ margin-top: 0; }}
    h3 {{ margin-top: 2.2rem; padding-bottom: 0.45rem; border-bottom: 2px solid #e4eaf2; }}
    h4 {{ margin-top: 1.8rem; }}
    a {{ color: #175cd3; }}
    table {{ width: 100%; border-collapse: collapse; margin: 18px 0 28px; font-size: 0.94rem; }}
    th, td {{ border: 1px solid #cfd8e5; padding: 9px 11px; text-align: left; vertical-align: top; }}
    th {{ background: #edf4ff; }}
    tr:nth-child(even) td {{ background: #f8fafc; }}
    pre {{ overflow: auto; padding: 16px; color: #e6edf3; background: #0d1117; border-radius: 10px; }}
    code {{ font-family: "Cascadia Code", Consolas, monospace; }}
    :not(pre) > code {{ padding: 0.15rem 0.35rem; color: #9f1239; background: #fff1f2; border-radius: 5px; }}
    p[align="center"] {{ overflow-x: auto; padding: 12px 16px; font-size: 1.08rem; background: #f8fafc; border: 1px solid #d8e1ec; border-radius: 9px; }}
    .image-link {{ display: block; margin: 18px auto 28px; text-align: center; }}
    .image-link img {{ display: block; width: min(100%, 1100px); height: auto; margin: auto; border: 1px solid #cfd8e5; border-radius: 10px; box-shadow: 0 5px 18px rgba(27, 39, 64, 0.12); }}
    .source-link {{ display: inline-block; margin-bottom: 24px; padding: 8px 12px; background: #edf4ff; border-radius: 8px; text-decoration: none; }}
    @media (max-width: 900px) {{
      .layout {{ grid-template-columns: 1fr; padding: 12px; }}
      nav {{ position: static; max-height: none; }}
      main {{ padding: 24px 18px; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <nav>
      <h2>Table of contents</h2>
      {converter.toc}
    </nav>
    <main>
      <a class="source-link" href="{markdown_path.name}">Open Markdown source</a>
      {body}
    </main>
  </div>
</body>
</html>
'''
    output_path.write_text(document, encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description='Build an HTML report from Readme.md')
    parser.add_argument('--input', default='Readme.md', help='Input Markdown path')
    parser.add_argument('--output', default='report.html', help='Output HTML path')
    args = parser.parse_args()
    build_html(Path(args.input), Path(args.output))
    print(f'[DONE] HTML report: {Path(args.output).resolve()}')


if __name__ == '__main__':
    main()
