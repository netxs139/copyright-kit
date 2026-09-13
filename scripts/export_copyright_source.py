#!/usr/bin/env python3
"""export_copyright_source.py — 通用多语言计算机软件著作权 60 页规范源程序抽取与排版引擎。

完全遵循中国版权保护中心 (CPCC) 审查规范：
1. 源码前后各 30 页 (共 60 页)，每页严格 55 行 (满足法定每页 >=50 行标准)；
2. 自动过滤 TODO/FIXME/XXX/DEBUG/第三方商业版权头，彻底剥离行尾未竟注释；
3. 每页自动注入标准两端对齐页眉与连续页码，页间插入标准分页符 (\\f)；
4. 支持自适应零配置嗅探（自动推断当前项目名与生产源码目录）；
5. 零第三方依赖 (Zero-Dependency)，仅使用 Python 标准库，跨平台开箱即用。
"""

import argparse
import json
import re
import sys
from pathlib import Path

# 默认支持的代码扩展名（涵盖主流编程语言、模板与数据库脚本）
DEFAULT_EXTS = {
    ".py",
    ".ts",
    ".vue",
    ".js",
    ".jsx",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".swift",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".sql",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".less",
    ".lua",
    ".sh",
    ".bash",
}

# 默认排除的非生产目录
DEFAULT_EXCLUDES = {
    "node_modules",
    "dist",
    "dist-ssr",
    "build",
    ".venv",
    "venv",
    "env",
    "tests",
    "test",
    "__tests__",
    "__pycache__",
    ".git",
    ".agents",
    "scratch",
    "coverage",
}

# 违规与敏感词正则过滤表 (多语言注释与待办标记全面拦截)
FORBIDDEN_PATTERNS = [
    # 1. HTML / XML 模板待办注释: <!-- TODO: ... -->
    re.compile(r"\s*<!--\s*(TODO|FIXME|XXX).*?(-->|$)", re.IGNORECASE),
    # 2. C / CSS 风格行内块待办注释: /* TODO: ... */
    re.compile(r"\s*/\*\s*(TODO|FIXME|XXX).*?(\*/|$)", re.IGNORECASE),
    # 3. SQL / Lua 单行待办注释: -- TODO: ...
    re.compile(r"\s*--\s*(TODO|FIXME|XXX).*$", re.IGNORECASE),
    # 4. 通用行尾待办截断 (覆盖 Python/Shell '#' 以及 JS/Go/Rust/C++ '//')
    re.compile(r"\s*\b(TODO|FIXME|XXX)\b.*$", re.IGNORECASE),
    # 5. 调试标记清洗
    re.compile(r"\b(const|let|var)?\s*DEBUG\s*=\s*(True|true|1)", re.IGNORECASE),
    # 6. 第三方商业开源版权与声明头
    re.compile(r"Copyright\s+(\(c\)|©)\s*\d{4}.*", re.IGNORECASE),
    re.compile(r"All\s+rights\s+reserved.*", re.IGNORECASE),
    re.compile(r"Licensed\s+under\s+the\s+(Apache|MIT|GPL|BSD).*", re.IGNORECASE),
]

# 清洗后需要直接过滤的纯注释或空符号集合
EMPTY_COMMENT_MARKERS = {
    "#",
    "//",
    "/*",
    "*/",
    "*",
    "--",
    "<!--",
    "-->",
    "<!---->",
    "/**",
    "**/",
}


def clean_source_line(line: str) -> str:
    """清洗单行代码中的违规词与敏感标记。"""
    cleaned = line
    for pat in FORBIDDEN_PATTERNS:
        cleaned = pat.sub("", cleaned)
    return cleaned


def is_excluded(path: Path, exclude_dirs: set[str]) -> bool:
    """判断路径是否包含排除目录。"""
    for part in path.parts:
        if part in exclude_dirs:
            return True
    return False


def collect_source_lines(
    search_paths: list[Path],
    valid_exts: set[str],
    exclude_dirs: set[str],
) -> list[str]:
    """遍历搜索路径收集并清洗有效源代码行。"""
    collected_files: list[Path] = []

    for sp in search_paths:
        if sp.is_file() and sp.suffix in valid_exts:
            if not is_excluded(sp, exclude_dirs):
                collected_files.append(sp)
        elif sp.is_dir():
            for p in sorted(sp.rglob("*")):
                if p.is_file() and p.suffix in valid_exts and not is_excluded(p, exclude_dirs):
                    collected_files.append(p)

    all_lines: list[str] = []
    for fp in collected_files:
        try:
            content = fp.read_text(encoding="utf-8", errors="ignore")
            for raw_line in content.splitlines():
                cl = clean_source_line(raw_line)
                # 过滤掉清洗后变成纯空白或纯单行注释符的无意义行
                stripped = cl.strip()
                if not stripped or stripped in EMPTY_COMMENT_MARKERS:
                    continue
                all_lines.append(cl)
        except Exception:
            continue

    return all_lines


def paginate_source_code(
    lines: list[str],
    app_name: str,
    version: str,
    lines_per_page: int = 55,
    total_pages: int = 60,
) -> str:
    """按照 CPCC 规范切分为指定页数并注入标准两端对齐页眉。"""
    needed_lines = lines_per_page * total_pages
    half_pages = total_pages // 2
    half_lines = lines_per_page * half_pages

    if len(lines) < needed_lines:
        # 代码总量不足 60 页时，取前后两半切分
        mid = len(lines) // 2
        front_lines = lines[:mid]
        back_lines = lines[mid:]
    else:
        # 足够时取连续的前 30 页与后 30 页
        front_lines = lines[:half_lines]
        back_lines = lines[-half_lines:]

    selected = front_lines + back_lines
    pages: list[str] = []

    actual_pages = min(total_pages, (len(selected) + lines_per_page - 1) // lines_per_page)

    for page_idx in range(1, actual_pages + 1):
        start = (page_idx - 1) * lines_per_page
        end = start + lines_per_page
        cur_lines = selected[start:end]

        header_title = f"{app_name} {version}"
        header_page = f"第 {page_idx} 页"
        spaces = max(4, 80 - len(header_title) - len(header_page))
        page_header = f"{header_title}{' ' * spaces}{header_page}\n" + "-" * 80 + "\n"

        pages.append(page_header + "\n".join(cur_lines) + "\n\n")

    return "\f".join(pages)


def export_as_docx(
    lines: list[str],
    app_name: str,
    version: str,
    output_docx_path: Path,
    lines_per_page: int = 55,
    total_pages: int = 60,
) -> None:
    """使用纯 Python 标准库 (zipfile) 生成原生 OpenXML .docx 格式的 60 页标准源程序文档。

    零第三方依赖，内置 A4 纸张、2.0cm 标准边距、Consolas 8.5pt 等宽代码字体与两端对齐页眉。
    """
    import zipfile
    from xml.sax.saxutils import escape

    needed_lines = lines_per_page * total_pages
    half_pages = total_pages // 2
    half_lines = lines_per_page * half_pages

    if len(lines) < needed_lines:
        mid = len(lines) // 2
        front_lines = lines[:mid]
        back_lines = lines[mid:]
    else:
        front_lines = lines[:half_lines]
        back_lines = lines[-half_lines:]

    selected = front_lines + back_lines
    actual_pages = min(total_pages, (len(selected) + lines_per_page - 1) // lines_per_page)

    body_xml_parts: list[str] = []

    for page_idx in range(1, actual_pages + 1):
        start = (page_idx - 1) * lines_per_page
        end = start + lines_per_page
        cur_lines = selected[start:end]

        header_title = escape(f"{app_name} {version}")
        header_page = escape(f"第 {page_idx} 页")

        # 页眉段落 (两端对齐制表位：左边标题，右边页码)
        body_xml_parts.append(f"""<w:p>
  <w:pPr>
    <w:tabs><w:tab w:val="right" w:pos="9638"/></w:tabs>
    <w:spacing w:before="0" w:after="60"/>
  </w:pPr>
  <w:r><w:rPr><w:b/><w:sz w:val="18"/></w:rPr><w:t>{header_title}</w:t></w:r>
  <w:r><w:tab/><w:rPr><w:b/><w:sz w:val="18"/></w:rPr><w:t>{header_page}</w:t></w:r>
</w:p>""")
        # 页眉下方细横线
        body_xml_parts.append("""<w:p>
  <w:pPr><w:spacing w:before="0" w:after="120"/></w:pPr>
  <w:r><w:rPr><w:color w:val="AAAAAA"/><w:sz w:val="14"/></w:rPr><w:t>--------------------------------------------------------------------------------</w:t></w:r>
</w:p>""")

        # 每页 55 行代码段落 (等宽字体，行高紧凑)
        for line in cur_lines:
            escaped_line = escape(line)
            body_xml_parts.append(f"""<w:p>
  <w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>
  <w:r><w:t xml:space="preserve">{escaped_line}</w:t></w:r>
</w:p>""")

        # 如果不是最后一页，插入硬分页符
        if page_idx < actual_pages:
            body_xml_parts.append("<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>")

    # 页面节设置 (A4 尺寸: 11906 x 16838 dxa, 页边距: 2.0 cm = 1134 dxa)
    body_xml_parts.append("""<w:sectPr>
  <w:pgSz w:w="11906" w:h="16838"/>
  <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="720" w:footer="720" w:gutter="0"/>
</w:sectPr>""")

    full_document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {"".join(body_xml_parts)}
  </w:body>
</w:document>"""

    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="SimSun" w:cs="Consolas"/>
        <w:sz w:val="17"/>
        <w:szCs w:val="17"/>
      </w:rPr>
    </w:rPrDefault>
    <w:pPrDefault>
      <w:pPr>
        <w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>
      </w:pPr>
    </w:pPrDefault>
  </w:docDefaults>
</w:styles>"""

    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

    pkg_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    doc_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    output_docx_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_docx_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types_xml)
        z.writestr("_rels/.rels", pkg_rels_xml)
        z.writestr("word/_rels/document.xml.rels", doc_rels_xml)
        z.writestr("word/styles.xml", styles_xml)
        z.writestr("word/document.xml", full_document_xml)


def detect_app_name(project_root: Path) -> str | None:
    """自动从 package.json, pyproject.toml, Cargo.toml 或目录名中推断应用名称建议。"""
    pkg_json = project_root / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            name = data.get("name", "")
            if name:
                clean_name = name.split("/")[-1].replace("-", " ").replace("_", " ").title()
                return f"{clean_name}管理软件"
        except Exception:
            pass

    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        try:
            txt = pyproject.read_text(encoding="utf-8")
            m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', txt)
            if m:
                clean_name = m.group(1).replace("-", " ").replace("_", " ").title()
                return f"{clean_name}系统"
        except Exception:
            pass

    cargo = project_root / "Cargo.toml"
    if cargo.exists():
        try:
            txt = cargo.read_text(encoding="utf-8")
            m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', txt)
            if m:
                clean_name = m.group(1).replace("-", " ").replace("_", " ").title()
                return f"{clean_name}软件"
        except Exception:
            pass

    folder_name = project_root.resolve().name.replace("-", " ").replace("_", " ").title()
    if folder_name and folder_name not in (".", "workspace"):
        return f"{folder_name}协同管理软件"
    return None


def detect_src_dirs(project_root: Path) -> list[Path]:
    """若用户未指定搜索目录，自动探测项目中常见的生产源码目录。"""
    candidates = ["src", "app", "apps", "lib", "packages", "pkg", "core", "server", "web"]
    found = [project_root / c for c in candidates if (project_root / c).is_dir()]
    return found if found else [project_root]


def update_application_card_sloc(card_path: Path, total_lines: int) -> bool:
    """自动将统计出的精确代码总行数回填至 CPCC 在线申请表字段卡中。"""
    if not card_path.exists():
        return False
    try:
        content = card_path.read_text(encoding="utf-8")
        # 匹配形如 | **源程序量** | `28,500` 行 | 或 | **源程序量 (代码行数)** | `...` 行 |
        pattern = re.compile(r"(\|\s*\*\*源程序量[^*]*\*\*\s*\|\s*`)[^`]+(`\s*行\s*\|)")
        formatted_sloc = f"{total_lines:,}"
        if pattern.search(content):
            new_content = pattern.sub(rf"\g<1>{formatted_sloc}\g<2>", content)
            card_path.write_text(new_content, encoding="utf-8")
            return True
    except Exception:
        pass
    return False


def main():
    parser = argparse.ArgumentParser(description="抽取与排版标准 60 页计算机软件著作权源程序文档 (零配置自适应)")
    parser.add_argument("--src-dir", nargs="+", help="源码搜索目录（可指定多个，默认自动探测 src/apps/lib 等）")
    parser.add_argument("--output-file", help="输出目标文件路径 (默认: docs/copyright/source_code_60pages.txt)")
    parser.add_argument("--app-name", help="软件全称 (默认自动从项目元数据推断，必须以软件/系统/平台/工具结尾)")
    parser.add_argument("--version", default="V1.0", help="软件版本号 (默认: V1.0，必须大写 V 开头)")
    parser.add_argument("--lines-per-page", type=int, default=55, help="每页行数 (默认: 55, 法定>=50)")
    parser.add_argument("--pages", type=int, default=60, help="总页数 (默认: 60)")
    parser.add_argument("--exts", help="允许的文件扩展名（逗号分隔，如 .py,.ts,.vue）")
    parser.add_argument("--exclude", help="额外排除的目录名称（逗号分隔）")

    args = parser.parse_args()

    project_root = Path.cwd().resolve()

    # 1. 解析/自适应推断源码目录
    if args.src_dir:
        search_paths = [Path(p).resolve() for p in args.src_dir]
    else:
        search_paths = detect_src_dirs(project_root)

    # 2. 解析/自适应推断应用名称
    app_name = args.app_name or detect_app_name(project_root) or "自研数字化协同管理软件"

    # 3. 解析输出文件路径
    if args.output_file:
        output_path = Path(args.output_file).resolve()
    else:
        output_path = project_root / "docs" / "copyright" / "source_code_60pages.txt"

    exts = set(args.exts.split(",")) if args.exts else DEFAULT_EXTS
    excludes = set(args.exclude.split(",")) if args.exclude else DEFAULT_EXCLUDES

    print("=" * 68)
    print(f"📄 正在抽取软件著作权源程序文档: {app_name} {args.version}")
    print(f"   扫描目录: {', '.join(str(p) for p in search_paths)}")
    print(f"   目标规格: 每页 {args.lines_per_page} 行，共 {args.pages} 页 (前 {args.pages // 2} + 后 {args.pages // 2})")
    print("=" * 68)

    lines = collect_source_lines(search_paths, exts, excludes)
    print(f"🔍 扫描到清洗后有效代码行数: {len(lines)} 行")

    if not lines:
        print("❌ 错误: 未扫描到任何有效源代码行，请检查目录路径或扩展名！", file=sys.stderr)
        sys.exit(1)

    result_text = paginate_source_code(
        lines=lines,
        app_name=app_name,
        version=args.version,
        lines_per_page=args.lines_per_page,
        total_pages=args.pages,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result_text, encoding="utf-8")

    total_output_lines = len(result_text.splitlines())
    print(f"✅ 成功导出标准软著源程序文档: {output_path}")
    print(f"   总格式化行数: {total_output_lines} 行 (包含页眉与分隔线)")

    # 顺便自动导出原生 Word .docx 格式，免去手动排版转 PDF 烦恼
    docx_path = output_path.with_suffix(".docx")
    try:
        export_as_docx(
            lines=lines,
            app_name=app_name,
            version=args.version,
            output_docx_path=docx_path,
            lines_per_page=args.lines_per_page,
            total_pages=args.pages,
        )
        print(f"📄 成功导出原生 Word 排版文档: {docx_path} (内置 A4 / 2cm 边距 / Consolas 等宽字体)")
    except Exception as e:
        print(f"⚠️ 导出 .docx 异常 (已保留 .txt 正常交付): {e}", file=sys.stderr)

    # 尝试自动将真实总代码行数回填至 CPCC 申报表卡
    card_path = output_path.parent / "cpcc_application_info.md"
    if update_application_card_sloc(card_path, len(lines)):
        print(f"📊 已将真实源程序量 ({len(lines):,} 行) 自动同步至申报填报卡: {card_path}")
    print("=" * 68)


if __name__ == "__main__":
    main()
