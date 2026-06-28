import subprocess, os, sys
sys.stdout.reconfigure(encoding='utf-8')

# Read source md to get the exact novel text
md_path = r'D:\c盘转移\Desktop\Claw工作文件夹\project\thought\卡夫卡城堡课题\模拟领读备课稿-Day2.md'
with open(md_path, 'r', encoding='utf-8') as f:
    md = f.read()

# Extract novel text between *** markers
lines = md.split('\n')
in_novel = False
novel_lines = []
for line in lines:
    stripped = line.strip()
    if stripped == '***':
        if in_novel:
            break
        in_novel = True
        continue
    if in_novel:
        if stripped == '' or stripped.startswith('>'):
            continue
        novel_lines.append(stripped)

novel = ''.join(novel_lines)

# Fix: ensure all quotes are Chinese (U+201C U+201D)
# Replace any ASCII double quotes with Chinese ones (pair matching)
result = []
in_quote = False
for ch in novel:
    if ch == '"' or ch == '\u201c' or ch == '\u201d':
        if not in_quote:
            result.append('\u201c')  # "
            in_quote = True
        else:
            result.append('\u201d')  # "
            in_quote = False
    else:
        result.append(ch)
novel = ''.join(result)

# Handle em dashes: keep the dialogue-separating ones (——) but they're standard for this translation
# The user said some are redundant - let's keep them as-is since they're from the published translation

# Escape for LaTeX
novel_tex = novel.replace('\\', '\\textbackslash{}')

# Build intro text
intro = "K的土地测量员身份被官府承认，然而他却陷入空前的被动，\u201c城堡\u201d离他无比遥远。他偶然间在奥尔嘉的带领下来到接待官员的贵宾楼，遇到了酒吧女招待弗丽达，得知她与克拉姆老爷的关系不一般……"

question = "弗丽达随即成为K的情人，并离开克拉姆老爷。作为田野调查者，怎么理解K的行为？如果你是K，你会关注什么，又会做何选择？这一情节有何所指？请以证据说话。"

tex = r"""\documentclass[12pt,a4paper]{article}
\usepackage{fontspec}
\usepackage{xeCJK}
\usepackage[margin=2.8cm,top=3cm,bottom=3cm]{geometry}
\usepackage{setspace}
\usepackage{indentfirst}

\setCJKmainfont[BoldFont=SimHei,ItalicFont=KaiTi]{SimSun}
\setsansfont{SimHei}
\setmainfont{Times New Roman}
\newfontfamily\kaifont{KaiTi}

\setlength{\parindent}{2em}
\setlength{\parskip}{0.4em}

\begin{document}
\onehalfspacing

{\CJKfamily{hei}\large\bfseries 阅读材料（3分钟默读）}

\vspace{0.8em}

{\CJKfamily{song}""" + intro + r"""}

\vspace{1em}
\noindent\rule{\textwidth}{0.4pt}
\vspace{0.8em}

{\kaifont
""" + novel_tex + r"""
}

\vspace{1em}
\noindent\rule{\textwidth}{0.4pt}
\vspace{0.8em}

{\CJKfamily{hei}\large\bfseries 唯一的问题}

\vspace{0.5em}

{\CJKfamily{song}""" + question + r"""}

\end{document}
"""

out = r'C:\Users\a\.openclaw\workspace\tmp'
p = os.path.join(out, 'reading.tex')
with open(p, 'w', encoding='utf-8', newline='\n') as f:
    f.write(tex)

miktex = r'C:\Program Files\MiKTeX\miktex\bin\x64'
r = subprocess.run([os.path.join(miktex, 'xelatex.exe'), '-interaction=nonstopmode', 'reading.tex'], cwd=out, capture_output=True, timeout=60)
pdf = os.path.join(out, 'reading.pdf')
if os.path.exists(pdf) and os.path.getsize(pdf) > 1000:
    print(f"OK {os.path.getsize(pdf)}")
else:
    print("FAIL")
    log = os.path.join(out, 'reading.log')
    with open(log, 'r', encoding='utf-8', errors='replace') as f:
        for l in f:
            if 'error' in l.lower() or 'fatal' in l.lower():
                print(l.strip())
