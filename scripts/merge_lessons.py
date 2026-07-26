"""
merge_lessons.py -- 极简教案合并

原则：除了 \\usepackage{tocloft}、\\tableofcontents 和 \\newpage 之外，
不生成任何新的排版内容。所有正文、标题均原样取自各天 _lesson.tex。

合并逻辑：
1. 取 day-01 的「共享 preamble」：去掉 title/author/date/fancyfoot，
   加上 tocloft（仅目录格式控制，不加 hyperref）
2. 每个天的标题块从该天 preamble 中提取，原样注入到该天正文之前
3. 按天序拼接：\\tableofcontents -> Day 1 -> ... -> Day N

用法：python scripts/merge_lessons.py samples/castle
"""

import argparse, os, re, subprocess, sys


def split_tex(content: str):
    """返回 (preamble, title_block, body)。"""
    doc_begin = content.find(r'\begin{document}')
    doc_end = content.find(r'\end{document}')
    if doc_begin == -1:
        return None

    preamble = content[:doc_begin]

    # 提取 title/author/date 块
    title_match = re.search(
        r'(\\title\{.+?\})\s*\n(?:\s*\\author\{.*?\}\s*\n)?(?:\s*\\date\{.*?\}\s*\n)?',
        preamble, re.DOTALL,
    )
    title_block = title_match.group(0) if title_match else ''

    clean = (
        preamble[:title_match.start()] + preamble[title_match.end():]
        if title_match
        else preamble
    )

    body_start = doc_begin + len(r'\begin{document}')
    body = content[body_start:] if doc_end == -1 else content[body_start:doc_end]

    return clean, title_block.strip(), body.strip()


def find_day_dirs(base_dir: str):
    days = []
    for entry in os.listdir(base_dir):
        full = os.path.join(base_dir, entry)
        if os.path.isdir(full):
            m = re.match(r'^day-(\d+)$', entry)
            if m:
                days.append((int(m.group(1)), full))
    days.sort(key=lambda x: x[0])
    return days


def clean_preamble(preamble: str) -> str:
    """去掉共享 preamble 中不该有的命令。

    各天原始的 \\fancyfoot 没有对应的 \\usepackage{fancyhdr}，
    LaTeX 静默忽略它（页码仍由 article 默认机制显示）。合并版
    删除此命令，保持 clean。
    """
    # 删除空的 \\fancyfoot 行和周围的空行
    p = re.sub(r'\n\s*\\fancyfoot\[C\]\{\s*\\small\s*\\thepage\s*\}\s*\n', '\n', preamble)
    # 删除紧随其后的空 \\AtBeginDocument{}（如果有的话它也无意义）
    p = re.sub(r'\\AtBeginDocument\{\}\s*\n', '', p)
    return p.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('base_dir', help='包含 day-XX 子目录的根目录')
    args = parser.parse_args()

    base_dir = os.path.abspath(args.base_dir)
    merged_dir = os.path.join(base_dir, 'merged')
    os.makedirs(merged_dir, exist_ok=True)

    days = find_day_dirs(base_dir)
    if not days:
        print('Error: 未找到 day-XX 目录', file=sys.stderr)
        sys.exit(1)

    shared_preamble = None
    segments = []

    for day_num, day_dir in days:
        tex_path = os.path.join(day_dir, '_lesson.tex')
        if not os.path.exists(tex_path):
            print(f'  [skip] day-{day_num:02d}: _lesson.tex 不存在')
            continue
        with open(tex_path, 'r', encoding='utf-8') as f:
            content = f.read()

        result = split_tex(content)
        if result is None:
            print(f'  [skip] day-{day_num:02d}: 格式异常')
            continue

        cp, title_block, body = result
        if shared_preamble is None:
            shared_preamble = clean_preamble(cp)
        segments.append((day_num, title_block, body))
        print(f'  day-{day_num:02d}: {len(body)} chars')

    if shared_preamble is None:
        print('Error: 无可用 preamble', file=sys.stderr)
        sys.exit(1)

    # 组装 preamble：只加 tocloft（不加 fancyhdr，因为 \\fancyfoot 已删除）
    merged_preamble = shared_preamble
    if r'\usepackage{tocloft}' not in merged_preamble:
        merged_preamble += '\n\\usepackage{tocloft}\n'

    # 组装正文
    lines = [merged_preamble, r'\begin{document}']

    # 封面（可选）
    cover_path = os.path.join(merged_dir, 'cover.tex')
    if os.path.exists(cover_path):
        with open(cover_path, 'r', encoding='utf-8') as f:
            cover_content = f.read()
        cb = cover_content.find(r'\begin{document}')
        ce = cover_content.find(r'\end{document}')
        if cb != -1 and ce != -1:
            cover_body = cover_content[cb + len(r'\begin{document}'):ce].strip()
            lines.append(cover_body)
            lines.append(r'\newpage')

    lines.append(r'\renewcommand{\contentsname}{目录}')
    lines.append(r'\tableofcontents')

    for day_num, title_block, body in segments:
        lines.append(r'\newpage')
        # 手动渲染标题：居中 \LARGE \bfseries
        # 从 title_block 中提取纯标题文本（去掉外围的 \title{} 包装）
        import re as _re
        # 从 \title{...} 中提取内容（用括号配对而非 regex）
        ti_start = title_block.find(r'\title{')
        if ti_start >= 0:
            ti_content_start = ti_start + len(r'\title{')
            depth = 1
            ti_end = ti_content_start
            while ti_end < len(title_block) and depth > 0:
                if title_block[ti_end] == '{': depth += 1
                elif title_block[ti_end] == '}': depth -= 1
                ti_end += 1
            title_text = title_block[ti_content_start:ti_end-1].strip()
            lines.append(r'\begin{center}')
            lines.append(r'{\LARGE ' + title_text + '}')
            lines.append(r'\end{center}')
            lines.append(r'\vspace{1em}')
        else:
            lines.append(title_block)
        # 清理 body: 移除 \maketitle + 后续间距调整
        body_clean = _re.sub(
            r'\s*\\maketitle\s*\n(?:\s*\\vspace\{-?\d+[a-z]+\}\s*\n)*',
            '', body, count=1, flags=_re.DOTALL)
        # 去掉 body 开头的 \author{} 和 \date{}
        body_clean = _re.sub(r'^\s*\\author\{\}\s*\n', '', body_clean, count=1)
        body_clean = _re.sub(r'^\s*\\date\{\}\s*\n', '', body_clean, count=1)
        lines.append(body_clean)

    lines.append(r'\end{document}')
    tex_content = '\n'.join(lines) + '\n'

    tex_path = os.path.join(merged_dir, 'merged_lessons.tex')
    with open(tex_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(tex_content)
    print(f'\n写入: {tex_path}')

    # 编译两遍
    xelatex = r'C:\Program Files\MiKTeX\miktex\bin\x64\xelatex.exe'
    for i in range(2):
        subprocess.run(
            [xelatex, '-interaction=nonstopmode',
             '-output-directory', merged_dir, tex_path],
            capture_output=True, timeout=120,
        )
        log_path = os.path.join(merged_dir, 'merged_lessons.log')
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                errors = [l.strip() for l in f if l.startswith('!')]
            if errors:
                for e in errors[:5]:
                    print(f'  [{i+1}] {e}')
            else:
                print(f'  第 {i + 1} 遍编译完成')

    pdf_path = os.path.join(merged_dir, 'merged_lessons.pdf')
    if os.path.exists(pdf_path):
        size_kb = os.path.getsize(pdf_path) / 1024
        print(f'\nPDF: {pdf_path} ({size_kb:.1f} KB)')
    else:
        print('Error: PDF 未生成', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
