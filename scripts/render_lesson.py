"""
readfield 教案渲染器 v2
将 Day 目录下的 md 模块文件组合渲染为 LaTeX PDF 教案。

模块发现策略：
1. 读取 day_dir/README.md，从 YAML 风格元信息提取 day_title、day_number
2. 扫描目录下所有 md 文件，按文件名自然排序生成模块列表
3. 模块类型从文件内容自动判定

用法：
    python render_lesson.py <day-dir> [--output output.pdf]
"""

import os, re, subprocess, sys, argparse
from pathlib import Path

# ── 常量 ──────────────────────────────────────

def make_preamble(day_number, day_title):
    return rf"""\documentclass[12pt,a4paper]{{article}}
\usepackage[scheme=plain]{{ctex}}
\usepackage[margin=2.5cm]{{geometry}}
\usepackage{{indentfirst}}
\usepackage{{setspace}}
\usepackage{{fontspec}}
\setCJKmainfont[BoldFont=SimHei,ItalicFont=KaiTi]{{SimSun}}
\newCJKfontfamily\kaifont{{KaiTi}}[AutoFakeBold]
\usepackage{{newpxtext,newpxmath}}

\usepackage{{lastpage}}
\usepackage{{fancyhdr}}
\pagestyle{{fancy}}
\renewcommand{{\headrulewidth}}{{0pt}}
\fancyhf{{}}
\fancyhead[C]{{\small\itshape 重返城堡 · Day {day_number}}}
\fancyfoot[C]{{\small \thepage}}
\AtBeginDocument{{\thispagestyle{{fancy}}}}

\usepackage[nobottomtitles*]{{titlesec}}
\titleformat{{\section}}{{\Large\bfseries}}{{}}{{0em}}{{ }}
\titlespacing*{{\section}}{{0pt}}{{3ex}}{{1.5ex}}

\usepackage{{xcolor}}
\usepackage{{needspace}}

\setlength{{\parindent}}{{2em}}
\setlength{{\parskip}}{{0.4em}}

\doublespacing

\title{{\bfseries {esc(day_title, latex_mode=True)}}}
\author{{}}
\date{{}}

\begin{{document}}
\maketitle
\thispagestyle{{fancy}}
\vspace{{-2em}}

\vspace{{1em}}
"""

TEX_POSTAMBLE = r"\end{document}"

# ── 工具函数 ──────────────────────────────────

def esc(text, latex_mode=False):
    """LaTeX 特殊字符转义"""
    s = text
    for ch in ['\\','&','%','$','#','_','{','}','^','~']:
        s = s.replace(ch, '\\'+ch)
    return s


def discover_modules(day_dir):
    """扫描目录下所有 md 文件，按语义顺序排列（原文→媒介→信），跳过 README.md 和 STYLE-GUIDE.md"""
    files = []
    for f in os.listdir(day_dir):
        if f.endswith('.md') and f not in ('README.md', 'STYLE-GUIDE.md'):
            files.append(f)

    # 排除非模块文件
    exclude_prefixes = ('README', 'STYLE-GUIDE', 'prompt', 'voice', 'role')
    files = [f for f in files if not f.startswith(exclude_prefixes)]
    # 也排除中文名过程文件
    files = [f for f in files if not any(kw in f for kw in ['复盘', '试讲', '教案', 'STYLE'])]
    excerpts = sorted([f for f in files if f.startswith('excerpt-')])
    catalysts = sorted([f for f in files if f.startswith('catalyst-')])
    letters = sorted([f for f in files if f.startswith('scout-letter')])
    others = sorted([f for f in files if f not in excerpts + catalysts + letters])

    return letters + excerpts + catalysts + others


def read_metadata(day_dir):
    """从 README.md 提取 day_number 和 day_title"""
    readme_path = os.path.join(day_dir, 'README.md')
    if not os.path.exists(readme_path):
        return 1, 'Untitled'

    with open(readme_path, encoding='utf-8') as f:
        content = f.read()

    # 提取 Day 编号
    day_num = 1
    m = re.search(r'Day\s*(\d+)', content)
    if m:
        day_num = int(m.group(1))

    # 提取标题（第一行 # 开头）
    title = 'Untitled'
    for line in content.split('\n'):
        if line.startswith('# '):
            title = line[2:].strip()
            break

    return day_num, title


def parse_md_to_latex(raw, is_catalog=False):
    """将 md 正文转为 LaTeX 段落"""
    lines = raw.split('\n')
    result = []
    in_blockquote = False
    bq_lines = []

    for line in lines:
        s = line.strip()

        if not s:
            if in_blockquote:
                result.append(
                    '\\begin{quotation}\\kaifont\\noindent '
                    + '\n\n'.join(bq_lines) + '\\end{quotation}'
                )
                bq_lines = []
                in_blockquote = False
            result.append('')
            continue

        if s.startswith('> '):
            in_blockquote = True
            bq_lines.append(esc(s[2:]))
            continue

        if in_blockquote:
            result.append(
                '\\begin{quotation}\\kaifont\\noindent '
                + '\n\n'.join(bq_lines) + '\\end{quotation}'
            )
            bq_lines = []
            in_blockquote = False

        if s.startswith('#'):
            continue

        if s == '---':
            result.append('\\vspace{0.3em}')
            result.append('\\noindent\\rule{\\textwidth}{0.4pt}')
            result.append('\\vspace{0.3em}')
            continue

        if s.startswith('**引导语**'):
            continue

        if s == '……':
            result.append('\\vspace{0.2em}')
            continue

        if is_catalog:
            t = s
            while t.startswith('\u3000'):
                t = t[1:]
            s_esc = esc(t).replace('（', '(').replace('）', ')')
            if s_esc.startswith('第') and ('章' in s_esc):
                result.append(f'\\vspace{{0.3em}}\\textbf{{{s_esc}}}')
            elif t.startswith(tuple(f'{n}、' for n in '一二三四五六七八九十')):
                result.append(f'\\noindent\\hspace{{1em}}{s_esc}')
            elif t.startswith('（'):
                result.append(f'\\noindent\\hspace{{2.5em}}{s_esc}')
            else:
                result.append(f'\\noindent\\hspace{{3.5em}}{s_esc}')
        else:
            # 处理 Markdown 加粗 **text** -> \textbf{text}
            s_escaped = esc(s)
            s_bold = re.sub(r'\*\*([^*]+)\*\*', r'\\textbf{\1}', s_escaped)
            result.append(s_bold)

    if in_blockquote:
        result.append(
            '\\begin{quotation}\\kaifont\\noindent '
            + '\n\n'.join(bq_lines) + '\\end{quotation}'
        )

    return '\n\n'.join(result)


def extract_section(raw):
    """从 md 文件原始内容中提取：标题、引导语、正文、出处"""
    parts = raw.split('---', 1)
    header = parts[0].strip() if parts else ''

    title = ''
    for l in header.split('\n'):
        if l.strip().startswith('# '):
            title = l.strip()[2:]

    body = parts[1].strip() if len(parts) > 1 else ''

    # 提取引导语
    guide_text = ''
    guide_m = re.search(r'\*\*引导语\*\*\s*\n(.*?)(?=\n\S|$)', body, re.DOTALL)
    if guide_m:
        guide_text = guide_m.group(1).strip()
        body = body[guide_m.end():].strip()

    # 提取最后一行括号出处
    source_line = ''
    body_lines = body.split('\n')
    if body_lines and (body_lines[-1].strip().startswith('（') and '）' in body_lines[-1]) or (body_lines[-1].strip().startswith('(') and ')' in body_lines[-1]):
        source_line = body_lines[-1].strip()
        body_lines = body_lines[:-1]
        body = '\n'.join(body_lines).strip()

    return title, guide_text, body, source_line


def build_tex(day_dir, modules):
    """从 day 目录读取所有模块文件，构建完整 TeX 字符串"""
    day_num, day_title = read_metadata(day_dir)
    sections = []

    for fname in modules:
        filepath = os.path.join(day_dir, fname)
        with open(filepath, encoding='utf-8') as f:
            raw = f.read()

        title, guide, body, source = extract_section(raw)

        # 判断是否目录页（文件名含 catalog 或 标题含"目录"）
        is_cat = ('catalog' in fname.lower()) or ('目录' in title)

        body_latex = parse_md_to_latex(body, is_catalog=is_cat)

        guide_latex = ''
        if guide:
            # 引导语整体不缩进，多段时保持格式一致
            guide_lines = guide.split('\n')
            guide_escaped_lines = [esc(line) if line.strip() else '' for line in guide_lines]
            guide_noindent = '\n\n'.join([f'\\noindent {line}' if line else '' for line in guide_escaped_lines])
            guide_latex = (
                f'\\vspace{{-0.3em}}'
                f'{{\\color{{gray}}\\small\\kaifont {guide_noindent}}}'
                f'\\vspace{{0.5em}}'
            )

        source_latex = ''
        if source:
            s = source
            s = re.sub(r'\*([^*]+)\*', r'<<ITALIC>>\1<</ITALIC>>', s)
            s = esc(s)
            s = s.replace('<<ITALIC>>', '\\textit{').replace('<</ITALIC>>', '}')
            source_latex = (
                f'\\par\\vspace{{0.3em}}'
                f'{{\\footnotesize\\color{{gray}}{s}}}'
            )

        sections.append({
            'title': esc(title),
            'guide': guide_latex,
            'body': body_latex,
            'source': source_latex,
        })

    tex = [make_preamble(day_num, day_title)]

    for i, sec in enumerate(sections):
        tex.append(f'\\section{{{sec["title"]}}}')
        tex.append(sec['guide'])
        tex.append(sec['body'])
        tex.append(sec['source'])
        if i < len(sections) - 1:
            tex.append(r'\newpage')

    tex.append(TEX_POSTAMBLE)
    return '\n'.join(tex)


def compile_pdf(tex_content, output_path, work_dir=None):
    """调用 xelatex 编译 PDF"""
    if work_dir is None:
        work_dir = os.path.dirname(output_path)

    tex_path = os.path.join(work_dir, '_lesson.tex')
    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(tex_content)

    result = subprocess.run(
        ['cmd', '/c', f'cd /d "{work_dir}" && xelatex -interaction=nonstopmode _lesson.tex && xelatex -interaction=nonstopmode _lesson.tex'],
        capture_output=True, text=True, timeout=120
    )

    tmp_pdf = os.path.join(work_dir, '_lesson.pdf')
    if os.path.exists(tmp_pdf):
        os.replace(tmp_pdf, output_path)
        return output_path

    # 编译失败
    log_path = os.path.join(work_dir, '_lesson.log')
    if os.path.exists(log_path):
        with open(log_path, encoding='utf-8', errors='replace') as f:
            for line in f.read().split('\n'):
                if line.startswith('!'):
                    print(f'  LaTeX ERROR: {line.strip()[:150]}')
    print(f'  stdout: {result.stdout[-500:]}')
    return None


def render_lesson(day_dir, output_path=None):
    """主入口"""
    if output_path is None:
        output_path = os.path.join(day_dir, '教案.pdf')

    print(f'Rendering: {day_dir}')
    modules = discover_modules(day_dir)
    print(f'  Modules: {modules}')
    tex_content = build_tex(day_dir, modules)
    result = compile_pdf(tex_content, output_path)
    if result:
        print(f'Done: {result}')
    else:
        print('Failed to compile PDF')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='readfield 教案渲染器 v2')
    parser.add_argument('day_dir', help='Day 目录路径')
    parser.add_argument('--output', '-o', help='输出 PDF 路径（默认 day_dir/教案.pdf）')
    args = parser.parse_args()
    render_lesson(args.day_dir, args.output)
