#!/usr/bin/env python3
"""
Converts Research_Paper.md into a high-quality, academic publication-style PDF
using Chrome headless with customized CSS matching the ACM/IEEE paper layout.
"""

import os
import re
import subprocess

WORKSPACE_DIR = "/Users/kamran/Desktop/semister 5/Cloud_Computing_Project"
MD_PATH = os.path.join(WORKSPACE_DIR, "Research_Paper.md")
HTML_PATH = os.path.join(WORKSPACE_DIR, "Research_Paper.html")
PDF_PATH = os.path.join(WORKSPACE_DIR, "Research_Paper.pdf")

def md_to_html(md_text):
    lines = md_text.split("\n")
    html_lines = []
    in_table = False
    table_header = True
    in_code_block = False
    in_list = False
    list_type = None

    for line in lines:
        stripped = line.strip()

        # Handle code blocks
        if stripped.startswith("```"):
            if in_code_block:
                html_lines.append("</pre></div>")
                in_code_block = False
            else:
                lang = stripped[3:].strip()
                html_lines.append(f'<div class="code-block"><pre><code>')
                in_code_block = True
            continue

        if in_code_block:
            escaped = (line.replace("&", "&amp;")
                           .replace("<", "&lt;")
                           .replace(">", "&gt;"))
            html_lines.append(escaped)
            continue

        # Handle tables
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped[1:-1].split("|")]
            # Check if separator row
            if all(re.match(r'^:?-+:?$', c) for c in cells):
                table_header = False
                continue

            if not in_table:
                in_table = True
                table_header = True
                html_lines.append('<div class="table-container"><table>')
                html_lines.append('<thead><tr>')
                for c in cells:
                    html_lines.append(f'<th>{inline_format(c)}</th>')
                html_lines.append('</tr></thead><tbody>')
            else:
                html_lines.append('<tr>')
                for c in cells:
                    html_lines.append(f'<td>{inline_format(c)}</td>')
                html_lines.append('</tr>')
            continue
        else:
            if in_table:
                html_lines.append('</tbody></table></div>')
                in_table = False
                table_header = True

        # Handle lists
        if stripped.startswith("- ") or stripped.startswith("• "):
            content = stripped[2:]
            if not in_list or list_type != "ul":
                if in_list:
                    html_lines.append(f"</{list_type}>")
                html_lines.append("<ul>")
                in_list = True
                list_type = "ul"
            html_lines.append(f"<li>{inline_format(content)}</li>")
            continue
        elif re.match(r'^\d+\.\s+', stripped):
            match = re.match(r'^\d+\.\s+', stripped)
            content = stripped[len(match.group(0)):]
            if not in_list or list_type != "ol":
                if in_list:
                    html_lines.append(f"</{list_type}>")
                html_lines.append("<ol>")
                in_list = True
                list_type = "ol"
            html_lines.append(f"<li>{inline_format(content)}</li>")
            continue
        else:
            if in_list:
                html_lines.append(f"</{list_type}>")
                in_list = False
                list_type = None

        # Horizontal rule
        if stripped in ["---", "***", "___"]:
            html_lines.append("<hr/>")
            continue

        # Headings
        if stripped.startswith("# "):
            title_text = stripped[2:]
            html_lines.append(f'<h1 class="paper-title">{inline_format(title_text)}</h1>')
            continue
        elif stripped.startswith("## "):
            h2_text = stripped[3:]
            html_lines.append(f'<h2 class="section-title">{inline_format(h2_text)}</h2>')
            continue
        elif stripped.startswith("### "):
            h3_text = stripped[4:]
            html_lines.append(f'<h3 class="subsection-title">{inline_format(h3_text)}</h3>')
            continue

        # Blank lines
        if not stripped:
            continue

        # Mathematical display equations ($$...$$)
        if stripped.startswith("$$") and stripped.endswith("$$"):
            eq = stripped[2:-2].strip()
            html_lines.append(f'<div class="display-math">$$\\displaystyle {eq}$$</div>')
            continue

        # Authors block or metadata
        if "MD KAMRAN RAIS" in stripped:
            html_lines.append(f'<div class="author-block">{inline_format(stripped)}</div>')
            continue

        if stripped.startswith("*Course:*") or stripped.startswith("Course:"):
            html_lines.append(f'<div class="course-meta">{inline_format(stripped)}</div>')
            continue

        # Blockquote or note
        if stripped.startswith("> "):
            html_lines.append(f'<blockquote>{inline_format(stripped[2:])}</blockquote>')
            continue

        # Standard paragraph
        html_lines.append(f'<p>{inline_format(stripped)}</p>')

    if in_table:
        html_lines.append('</tbody></table></div>')
    if in_list:
        html_lines.append(f"</{list_type}>")

    return "\n".join(html_lines)

def inline_format(text):
    # Bold italic
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    # Inline code
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    # Markdown links
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
    return text

def build_full_html(body_html):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Research Paper - Md Kamran Rais</title>
<script>
window.MathJax = {{
  tex: {{
    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
    displayMath: [['$$', '$$']]
  }},
  svg: {{ fontCache: 'global' }}
}};
</script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<style>
@page {{
  size: A4;
  margin: 20mm 18mm 20mm 18mm;
  @bottom-center {{
    content: counter(page);
    font-family: "Times New Roman", Times, serif;
    font-size: 9pt;
    color: #444;
  }}
}}

body {{
  font-family: "Times New Roman", Times, Georgia, serif;
  font-size: 10pt;
  line-height: 1.42;
  color: #111;
  background: #fff;
  margin: 0;
  padding: 0;
}}

/* Typography */
.paper-title {{
  font-size: 18pt;
  font-weight: bold;
  text-align: center;
  margin: 10pt 0 14pt 0;
  line-height: 1.25;
  color: #000;
}}

.author-block {{
  text-align: center;
  font-size: 11pt;
  font-weight: bold;
  margin-bottom: 3pt;
}}

.course-meta {{
  text-align: center;
  font-size: 9.5pt;
  color: #333;
  margin-bottom: 14pt;
}}

.section-title {{
  font-size: 12pt;
  font-weight: bold;
  margin-top: 16pt;
  margin-bottom: 6pt;
  border-bottom: 0.75pt solid #222;
  padding-bottom: 2pt;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}}

.subsection-title {{
  font-size: 10.5pt;
  font-weight: bold;
  margin-top: 11pt;
  margin-bottom: 4pt;
  color: #111;
}}

p {{
  margin: 0 0 6pt 0;
  text-align: justify;
  text-justify: inter-word;
}}

/* Lists */
ul, ol {{
  margin: 4pt 0 8pt 18pt;
  padding: 0;
}}

li {{
  margin-bottom: 3pt;
  text-align: justify;
}}

/* Booktabs Academic Tables */
.table-container {{
  margin: 12pt 0;
  page-break-inside: avoid;
}}

table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 8.5pt;
  line-height: 1.3;
  margin: 6pt 0;
  border-top: 1.5pt solid #000;
  border-bottom: 1.5pt solid #000;
}}

th {{
  border-bottom: 1pt solid #000;
  padding: 5pt 4pt;
  font-weight: bold;
  text-align: left;
  background-color: #fcfcfc;
}}

td {{
  padding: 4pt 4pt;
  border-bottom: 0.5pt solid #e5e5e5;
  vertical-align: top;
}}

tr:last-child td {{
  border-bottom: none;
}}

/* Code Blocks */
.code-block {{
  background: #f8f9fa;
  border: 0.5pt solid #ddd;
  border-left: 2.5pt solid #4f46e5;
  border-radius: 3pt;
  padding: 6pt 8pt;
  margin: 8pt 0;
  font-family: "Courier New", Courier, monospace;
  font-size: 8pt;
  overflow-x: auto;
  page-break-inside: avoid;
}}

code {{
  font-family: "Courier New", Courier, monospace;
  background-color: #f3f4f6;
  padding: 1pt 3pt;
  border-radius: 2pt;
  font-size: 8.5pt;
}}

/* Math */
.display-math {{
  text-align: center;
  margin: 8pt 0;
  font-size: 10pt;
  page-break-inside: avoid;
}}

/* Horizontal Rule */
hr {{
  border: none;
  border-top: 0.5pt solid #ccc;
  margin: 12pt 0;
}}

/* Abstract Box */
blockquote {{
  margin: 8pt 18pt;
  padding: 4pt 12pt;
  border-left: 2pt solid #6b7280;
  background: #fbfbfb;
  font-size: 9.5pt;
}}
</style>
</head>
<body>
{body_html}
</body>
</html>
"""

def main():
    print(f"[INFO] Reading {MD_PATH}...")
    with open(MD_PATH, "r", encoding="utf-8") as f:
        md_text = f.read()

    body_html = md_to_html(md_text)
    full_html = build_full_html(body_html)

    print(f"[INFO] Writing rendered HTML to {HTML_PATH}...")
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"[INFO] Generating publication PDF with Google Chrome headless...")
    chrome_cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--user-data-dir=/tmp/chrome-pdf-user-dir",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_PATH}",
        HTML_PATH
    ]

    res = subprocess.run(chrome_cmd, capture_output=True, text=True)
    if os.path.exists(PDF_PATH) and os.path.getsize(PDF_PATH) > 0:
        pdf_size_kb = os.path.getsize(PDF_PATH) // 1024
        print(f"🎉 SUCCESS! PDF generated successfully: {PDF_PATH} ({pdf_size_kb} KB)")
    else:
        print(f"[ERROR] PDF generation failed: {res.stderr}")

if __name__ == "__main__":
    main()
