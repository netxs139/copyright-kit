#!/usr/bin/env python3
"""scripts/export_document_docx.py — 软件著作权使用说明书与详细设计说明书 Word (.docx) 导出引擎。

功能职责:
1. 纯 Python 标准库 (zipfile, xml.sax.saxutils) 实现原生 OpenXML .docx 导出，零第三方依赖；
2. 支持《用户操作说明书》(software_user_manual) 与《详细设计说明书》(software_design_specification) 渲染；
3. 将 Markdown 语法深度映射为原生 Word 样式：封面信息卡、多级标题、引用高亮框、表格、Mermaid/代码块、列表；
4. 专为 CPCC 规范定制「界面全景与操作截图占位框」，方便在 Word/WPS 中直接粘贴真实系统截图；
5. 自动配置两端对齐页眉与动态页码页脚 (第 X 页 共 Y 页)。
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
from xml.sax.saxutils import escape
import zipfile


# ==============================================================================
# 1. 样式与 OpenXML 部件定义
# ==============================================================================

CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Default Extension="jpeg" ContentType="image/jpeg"/>
  <Default Extension="jpg" ContentType="image/jpeg"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
  <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
</Types>"""

PKG_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  <Relationship Id="rIdHeader1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
  <Relationship Id="rIdFooter1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
</Relationships>"""

STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Microsoft YaHei" w:cs="Calibri"/>
        <w:sz w:val="21"/>
        <w:szCs w:val="21"/>
        <w:color w:val="1E293B"/>
      </w:rPr>
    </w:rPrDefault>
    <w:pPrDefault>
      <w:pPr>
        <w:spacing w:before="0" w:after="120" w:line="320" w:lineRule="auto"/>
      </w:pPr>
    </w:pPrDefault>
  </w:docDefaults>
</w:styles>"""


def build_header_xml(doc_title: str) -> str:
    """构建标准页眉 XML (左侧文档标题，右侧 CPCC 鉴别材料，下方横线分隔)。"""
    escaped_title = escape(doc_title)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:p>
    <w:pPr>
      <w:tabs><w:tab w:val="right" w:pos="9026"/></w:tabs>
      <w:pBdr><w:bottom w:val="single" w:sz="6" w:space="4" w:color="CBD5E1"/></w:pBdr>
      <w:spacing w:before="0" w:after="100"/>
    </w:pPr>
    <w:r><w:rPr><w:sz w:val="18"/><w:color w:val="64748B"/></w:rPr><w:t>{escaped_title}</w:t></w:r>
    <w:r><w:tab/><w:rPr><w:sz w:val="18"/><w:color w:val="64748B"/></w:rPr><w:t>中国版权保护中心 (CPCC) 申报鉴别材料</w:t></w:r>
  </w:p>
</w:hdr>"""


def build_footer_xml(left_label: str) -> str:
    """构建标准页脚 XML (左侧版权归属/全称，右侧动态页码: 第 X 页 共 Y 页)。"""
    escaped_label = escape(left_label)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:p>
    <w:pPr>
      <w:tabs><w:tab w:val="right" w:pos="9026"/></w:tabs>
      <w:spacing w:before="120" w:after="0"/>
    </w:pPr>
    <w:r><w:rPr><w:sz w:val="18"/><w:color w:val="94A3B8"/></w:rPr><w:t>{escaped_label}</w:t></w:r>
    <w:r><w:tab/><w:rPr><w:sz w:val="18"/><w:color w:val="64748B"/></w:rPr><w:t>第 </w:t></w:r>
    <w:fldSimple w:instr="PAGE"><w:r><w:rPr><w:sz w:val="18"/><w:color w:val="64748B"/></w:rPr><w:t>1</w:t></w:r></w:fldSimple>
    <w:r><w:rPr><w:sz w:val="18"/><w:color w:val="64748B"/></w:rPr><w:t> 页 / 共 </w:t></w:r>
    <w:fldSimple w:instr="NUMPAGES"><w:r><w:rPr><w:sz w:val="18"/><w:color w:val="64748B"/></w:rPr><w:t>1</w:t></w:r></w:fldSimple>
    <w:r><w:rPr><w:sz w:val="18"/><w:color w:val="64748B"/></w:rPr><w:t> 页</w:t></w:r>
  </w:p>
</w:ftr>"""


# ==============================================================================
# 2. Markdown 内联与块级 OpenXML 渲染器
# ==============================================================================

def render_inline_runs(text: str, default_sz: int = 21, default_color: str = "1E293B") -> str:
    """解析 Markdown 行内样式 (**粗体**, *斜体*, `代码`, 链接) 为 OpenXML <w:r> 集合。"""
    pattern = re.compile(r"(\*\*.*?\*\*|\*.*?\*|`.*?`|\[.*?\]\(.*?\))")
    tokens = pattern.split(text)
    runs: list[str] = []

    for token in tokens:
        if not token:
            continue
        is_bold = False
        is_italic = False
        is_code = False
        color = default_color
        sz = default_sz

        if token.startswith("**") and token.endswith("**") and len(token) >= 4:
            is_bold = True
            body_text = token[2:-2]
        elif token.startswith("*") and token.endswith("*") and len(token) >= 2:
            is_italic = True
            body_text = token[1:-1]
        elif token.startswith("`") and token.endswith("`") and len(token) >= 2:
            is_code = True
            body_text = token[1:-1]
            color = "C7254E"
        elif token.startswith("[") and "](" in token and token.endswith(")"):
            m = re.match(r"\[(.*?)\]\((.*?)\)", token)
            body_text = m.group(1) if m else token
            color = "2563EB"
        else:
            body_text = token

        rpr_parts: list[str] = []
        if is_code:
            rpr_parts.append('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="SimSun"/>')
            rpr_parts.append('<w:shd w:val="clear" w:color="auto" w:fill="F1F5F9"/>')
            sz = max(18, sz - 2)
        if is_bold:
            rpr_parts.append("<w:b/>")
        if is_italic:
            rpr_parts.append("<w:i/>")
        if color != default_color:
            rpr_parts.append(f'<w:color w:val="{color}"/>')
        if sz != 21:
            rpr_parts.append(f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>')

        rpr_xml = f"<w:rPr>{''.join(rpr_parts)}</w:rPr>" if rpr_parts else ""
        escaped_text = escape(body_text)
        runs.append(f'<w:r>{rpr_xml}<w:t xml:space="preserve">{escaped_text}</w:t></w:r>')

    return "".join(runs)


def render_heading(text: str, level: int) -> str:
    """渲染多级标题为美观的 OpenXML 段落。"""
    clean_text = text.lstrip("#").strip()
    if level == 1:
        # 文档大标题
        runs = render_inline_runs(clean_text, default_sz=40, default_color="0F172A")
        return f"""<w:p>
  <w:pPr>
    <w:jc w:val="center"/>
    <w:spacing w:before="400" w:after="240"/>
  </w:pPr>
  {runs}
</w:p>"""
    elif level == 2:
        # 第一级核心章节
        runs = render_inline_runs(clean_text, default_sz=30, default_color="0F172A")
        return f"""<w:p>
  <w:pPr>
    <w:pBdr><w:bottom w:val="single" w:sz="12" w:space="8" w:color="E2E8F0"/></w:pBdr>
    <w:spacing w:before="360" w:after="160"/>
  </w:pPr>
  <w:r><w:rPr><w:b/></w:rPr></w:r>
  {runs}
</w:p>"""
    elif level == 3:
        # 二级子小节
        runs = render_inline_runs(clean_text, default_sz=24, default_color="1E293B")
        return f"""<w:p>
  <w:pPr>
    <w:spacing w:before="240" w:after="100"/>
  </w:pPr>
  {runs}
</w:p>"""
    else:
        # 四级标题
        runs = render_inline_runs(clean_text, default_sz=22, default_color="334155")
        return f"""<w:p>
  <w:pPr>
    <w:spacing w:before="160" w:after="80"/>
  </w:pPr>
  {runs}
</w:p>"""


def render_table(rows: list[list[str]]) -> str:
    """将 Markdown 表格渲染为符合 Word 排版的专业表格 XML。"""
    if not rows:
        return ""

    tbl_xml_parts: list[str] = [
        """<w:tbl>
  <w:tblPr>
    <w:jc w:val="center"/>
    <w:tblW w:w="9026" w:type="dxa"/>
    <w:tblBorders>
      <w:top w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
      <w:left w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
      <w:bottom w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
      <w:right w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
      <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
      <w:insideV w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
    </w:tblBorders>
  </w:tblPr>"""
    ]

    for row_idx, row in enumerate(rows):
        is_header = row_idx == 0
        tr_parts: list[str] = ["<w:tr>"]
        if is_header:
            tr_parts.append("<w:trPr><w:tblHeader/></w:trPr>")

        for cell in row:
            bg_color = "F1F5F9" if is_header else "FFFFFF"
            cell_runs = render_inline_runs(cell.strip(), default_sz=19, default_color="0F172A" if is_header else "334155")
            bold_flag = "<w:b/>" if is_header else ""
            tr_parts.append(f"""<w:tc>
  <w:tcPr>
    <w:shd w:val="clear" w:color="auto" w:fill="{bg_color}"/>
    <w:tcMar>
      <w:top w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/>
      <w:left w:w="140" w:type="dxa"/><w:right w:w="140" w:type="dxa"/>
    </w:tcMar>
    <w:vAlign w:val="center"/>
  </w:tcPr>
  <w:p>
    <w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr>
    <w:r><w:rPr>{bold_flag}</w:rPr></w:r>
    {cell_runs}
  </w:p>
</w:tc>""")
        tr_parts.append("</w:tr>")
        tbl_xml_parts.append("".join(tr_parts))

    tbl_xml_parts.append("</w:tbl>")
    # 表格后增加空段落缓冲
    tbl_xml_parts.append('<w:p><w:pPr><w:spacing w:before="60" w:after="100"/></w:pPr></w:p>')
    return "".join(tbl_xml_parts)


def render_screenshot_placeholder(desc: str) -> str:
    """生成醒目的 CPCC 截图占位框，指导并在 Word/WPS 中留出真实的图片粘贴位。"""
    escaped_desc = escape(desc)
    return f"""<w:p>
  <w:pPr>
    <w:pBdr>
      <w:top w:val="dashed" w:sz="12" w:space="8" w:color="3B82F6"/>
      <w:left w:val="dashed" w:sz="12" w:space="8" w:color="3B82F6"/>
      <w:bottom w:val="dashed" w:sz="12" w:space="8" w:color="3B82F6"/>
      <w:right w:val="dashed" w:sz="12" w:space="8" w:color="3B82F6"/>
    </w:pBdr>
    <w:shd w:val="clear" w:color="auto" w:fill="EFF6FF"/>
    <w:spacing w:before="180" w:after="80"/>
    <w:jc w:val="center"/>
  </w:pPr>
  <w:r>
    <w:rPr><w:b/><w:sz w:val="22"/><w:color w:val="1D4ED8"/></w:rPr>
    <w:t>📸【系统界面全景 / 功能操作真实截图粘贴区】</w:t>
  </w:r>
</w:p>
<w:p>
  <w:pPr>
    <w:pBdr>
      <w:left w:val="dashed" w:sz="12" w:space="8" w:color="3B82F6"/>
      <w:bottom w:val="dashed" w:sz="12" w:space="8" w:color="3B82F6"/>
      <w:right w:val="dashed" w:sz="12" w:space="8" w:color="3B82F6"/>
    </w:pBdr>
    <w:shd w:val="clear" w:color="auto" w:fill="EFF6FF"/>
    <w:spacing w:before="0" w:after="180"/>
    <w:jc w:val="center"/>
  </w:pPr>
  <w:r>
    <w:rPr><w:sz w:val="18"/><w:color w:val="475569"/></w:rPr>
    <w:t>{escaped_desc}</w:t>
  </w:r>
</w:p>"""


def render_code_or_mermaid(lines: list[str], lang: str) -> str:
    """渲染代码块或 Mermaid 流程图定义为 Word 等宽代码容器。"""
    xml_parts: list[str] = []
    is_mermaid = "mermaid" in lang.lower()
    title = "📐 架构流程图 / 业务时序定义 (Mermaid)" if is_mermaid else f"💻 核心逻辑代码块 ({lang or 'Text'})"

    xml_parts.append(f"""<w:p>
  <w:pPr>
    <w:pBdr><w:top w:val="single" w:sz="6" w:color="CBD5E1"/><w:left w:val="single" w:sz="6" w:color="CBD5E1"/><w:right w:val="single" w:sz="6" w:color="CBD5E1"/></w:pBdr>
    <w:shd w:val="clear" w:color="auto" w:fill="F1F5F9"/>
    <w:spacing w:before="160" w:after="40"/>
  </w:pPr>
  <w:r><w:rPr><w:b/><w:sz w:val="18"/><w:color w:val="475569"/></w:rPr><w:t xml:space="preserve">  {escape(title)}</w:t></w:r>
</w:p>""")

    for idx, line in enumerate(lines):
        escaped_line = escape(line)
        is_last = idx == len(lines) - 1
        bottom_bdr = '<w:bottom w:val="single" w:sz="6" w:color="CBD5E1"/>' if is_last else ""
        after_space = "120" if is_last else "0"
        xml_parts.append(f"""<w:p>
  <w:pPr>
    <w:pBdr><w:left w:val="single" w:sz="6" w:color="CBD5E1"/><w:right w:val="single" w:sz="6" w:color="CBD5E1"/>{bottom_bdr}</w:pBdr>
    <w:shd w:val="clear" w:color="auto" w:fill="F8FAFC"/>
    <w:spacing w:before="0" w:after="{after_space}" w:line="240" w:lineRule="auto"/>
    <w:ind w:left="180"/>
  </w:pPr>
  <w:r>
    <w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="SimSun"/><w:sz w:val="17"/><w:color w:val="334155"/></w:rPr>
    <w:t xml:space="preserve">{escaped_line}</w:t>
  </w:r>
</w:p>""")
    return "".join(xml_parts)


def render_blockquote(lines: list[str]) -> str:
    """渲染引用/提示块，识别 ⚠️ 警示并赋予暖橙色/深蓝色侧边框。"""
    full_text = " ".join(lines)
    is_warning = any(w in full_text for w in ["⚠️", "审查", "硬指标", "必须", "驳回", "注意"])
    border_color = "D97706" if is_warning else "2563EB"
    bg_color = "FFFBEB" if is_warning else "F8FAFC"

    xml_parts: list[str] = []
    for idx, line in enumerate(lines):
        clean_line = line.lstrip(">").strip()
        if not clean_line:
            continue
        runs = render_inline_runs(clean_line, default_sz=20, default_color="92400E" if is_warning else "334155")
        before_sp = "100" if idx == 0 else "0"
        after_sp = "120" if idx == len(lines) - 1 else "40"
        xml_parts.append(f"""<w:p>
  <w:pPr>
    <w:pBdr><w:left w:val="single" w:sz="24" w:space="12" w:color="{border_color}"/></w:pBdr>
    <w:shd w:val="clear" w:color="auto" w:fill="{bg_color}"/>
    <w:ind w:left="240" w:right="120"/>
    <w:spacing w:before="{before_sp}" w:after="{after_sp}"/>
  </w:pPr>
  {runs}
</w:p>""")
    return "".join(xml_parts)


# ==============================================================================
# 3. 核心转换引擎: Markdown -> OpenXML DOCX
# ==============================================================================

def markdown_to_docx(
    md_content: str,
    output_docx_path: Path,
    doc_title: str = "",
    footer_label: str = "",
) -> Path:
    """将 Markdown 内容完整解析为符合 CPCC 官方排版规范的原生 Word (.docx) 文件。"""
    output_docx_path = Path(output_docx_path).resolve()
    output_docx_path.parent.mkdir(parents=True, exist_ok=True)

    lines = md_content.splitlines()
    body_parts: list[str] = []

    # 1. 自动推断文档大标题与页眉页脚元数据
    if not doc_title:
        for line in lines:
            if line.startswith("# "):
                doc_title = line[2:].strip()
                break
    if not doc_title:
        doc_title = output_docx_path.stem.replace("_", " ").title()

    if not footer_label:
        m_app = re.search(r">\s*\*\*软件全称\*\*\s*：\s*([^\n\r]+)", md_content)
        m_ver = re.search(r">\s*\*\*版本号\*\*\s*：\s*([^\n\r]+)", md_content)
        if m_app and m_ver:
            footer_label = f"{m_app.group(1).strip()} {m_ver.group(1).strip()}"
        elif m_app:
            footer_label = m_app.group(1).strip()
        else:
            footer_label = doc_title

    i = 0
    total_lines = len(lines)

    while i < total_lines:
        line = lines[i]
        stripped = line.strip()

        # 空行跳过
        if not stripped:
            i += 1
            continue

        # 1. 代码块 / Mermaid
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < total_lines and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # 跳过结尾 ```
            body_parts.append(render_code_or_mermaid(code_lines, lang))
            continue

        # 2. 标题 (H1 - H4)
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            body_parts.append(render_heading(stripped, level))
            i += 1
            continue

        # 3. 水平分割线
        if stripped in ("---", "***", "___"):
            body_parts.append("""<w:p>
  <w:pPr><w:spacing w:before="120" w:after="160"/></w:pPr>
  <w:r><w:rPr><w:color w:val="CBD5E1"/><w:sz w:val="14"/></w:rPr><w:t>________________________________________________________________________________</w:t></w:r>
</w:p>""")
            i += 1
            continue

        # 4. 引用块 (> ...)
        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while i < total_lines and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip())
                i += 1
            body_parts.append(render_blockquote(quote_lines))
            continue

        # 5. 表格 (| ... |)
        if stripped.startswith("|") and stripped.endswith("|"):
            table_rows: list[list[str]] = []
            while i < total_lines and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                raw_row = lines[i].strip()
                # 过滤分隔行 | :--- | :--- |
                if not re.match(r"^\|[\s\-:|]+\|$", raw_row):
                    cols = [c.strip() for c in raw_row.strip("|").split("|")]
                    table_rows.append(cols)
                i += 1
            body_parts.append(render_table(table_rows))
            continue

        # 6. 截图占位指示 (CPCC 截图硬指标)
        if ("【必须插入】" in stripped or "截图" in stripped) and (stripped.startswith("*") or stripped.startswith("（")):
            desc = stripped.strip("*()（）")
            body_parts.append(render_screenshot_placeholder(desc))
            i += 1
            continue

        # 7. 列表项 (- 或 * 或 1.)
        m_list = re.match(r"^(\s*)([-*]|\d+\.)\s+(.+)$", line)
        if m_list:
            prefix = m_list.group(2)
            content = m_list.group(3)
            bullet = "• " if prefix in ("-", "*") else f"{prefix} "
            bold_prefix = "<w:b/>" if prefix not in ("-", "*") else ""
            runs = render_inline_runs(content)
            body_parts.append(f"""<w:p>
  <w:pPr>
    <w:ind w:left="420" w:hanging="260"/>
    <w:spacing w:before="40" w:after="60"/>
  </w:pPr>
  <w:r><w:rPr>{bold_prefix}<w:color w:val="2563EB"/></w:rPr><w:t xml:space="preserve">{bullet}</w:t></w:r>
  {runs}
</w:p>""")
            i += 1
            continue

        # 8. 常规段落
        p_runs = render_inline_runs(stripped)
        body_parts.append(f"""<w:p>
  <w:pPr>
    <w:spacing w:before="40" w:after="120" w:line="320" w:lineRule="auto"/>
  </w:pPr>
  {p_runs}
</w:p>""")
        i += 1

    # 组装节属性 (A4 / 2cm 标准边距 / 绑定 Header 与 Footer)
    body_parts.append("""<w:sectPr>
  <w:headerReference w:type="default" r:id="rIdHeader1"/>
  <w:footerReference w:type="default" r:id="rIdFooter1"/>
  <w:pgSz w:w="11906" w:h="16838"/>
  <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="720" w:footer="720" w:gutter="0"/>
</w:sectPr>""")

    full_document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    {"".join(body_parts)}
  </w:body>
</w:document>"""

    header_xml = build_header_xml(doc_title)
    footer_xml = build_footer_xml(footer_label)

    with zipfile.ZipFile(output_docx_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        z.writestr("_rels/.rels", PKG_RELS_XML)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS_XML)
        z.writestr("word/styles.xml", STYLES_XML)
        z.writestr("word/header1.xml", header_xml)
        z.writestr("word/footer1.xml", footer_xml)
        z.writestr("word/document.xml", full_document_xml)

    return output_docx_path


# ==============================================================================
# 4. 高级封装: 模板变量渲染与说明书/设计说明书直出
# ==============================================================================

def normalize_app_and_version(app_name: str, version: str = "V1.0") -> tuple[str, str, str]:
    """标准化软件全称与版本号，避免二次重复拼接。

    返回三元组: (base_name, final_version, full_name)
    """
    clean_app = app_name.strip() if app_name else "自研数字化协同管理软件"
    clean_ver = version.strip() if version else "V1.0"

    match = re.search(r"\s+([Vv]\d+(?:\.\d+)*)$", clean_app)
    if match:
        embedded_ver = match.group(1)
        if embedded_ver.startswith("v"):
            embedded_ver = "V" + embedded_ver[1:]
        base_name = clean_app[: match.start()].strip()
        final_ver = clean_ver if (clean_ver and clean_ver != "V1.0") else embedded_ver
        if final_ver.startswith("v"):
            final_ver = "V" + final_ver[1:]
        full_name = f"{base_name} {final_ver}"
        return base_name, final_ver, full_name

    base_name = clean_app
    final_ver = clean_ver if clean_ver else "V1.0"
    if final_ver.startswith("v"):
        final_ver = "V" + final_ver[1:]
    full_name = f"{base_name} {final_ver}"
    return base_name, final_ver, full_name


def fill_template_variables(
    content: str,
    app_name: str = "",
    version: str = "V1.0",
    company_name: str = "",
    short_name: str = "",
    date_str: str = "",
) -> str:
    """替换说明书模板中的占位符变量。"""
    import datetime
    today = date_str or datetime.date.today().strftime("%Y年%m月%d日")

    base_name, final_version, full_name = normalize_app_and_version(app_name, version)

    replacements = {
        "{{FULL_NAME}}": full_name,
        "{{SHORT_NAME}}": short_name or base_name[:8],
        "{{VERSION}}": final_version,
        "{{COMPANY_NAME}}": company_name or "自主研发著作权人",
        "{{DATE}}": today,
    }
    for k, v in replacements.items():
        content = content.replace(k, v)
    return content


def export_manual_doc(
    input_path: Path,
    output_path: Path,
    app_name: str = "",
    version: str = "V1.0",
    company_name: str = "",
    short_name: str = "",
    date_str: str = "",
) -> Path:
    """导出《用户操作说明书》Word (.docx) 版。"""
    raw = Path(input_path).read_text(encoding="utf-8")
    base_name, final_version, full_name = normalize_app_and_version(app_name, version)
    filled = fill_template_variables(
        raw,
        app_name=base_name,
        version=final_version,
        company_name=company_name,
        short_name=short_name,
        date_str=date_str,
    )
    title = f"{full_name} 用户操作说明书"
    return markdown_to_docx(filled, output_path, doc_title=title, footer_label=full_name)


def export_design_doc(
    input_path: Path,
    output_path: Path,
    app_name: str = "",
    version: str = "V1.0",
    company_name: str = "",
    short_name: str = "",
    date_str: str = "",
) -> Path:
    """导出《详细设计说明书》Word (.docx) 版。"""
    raw = Path(input_path).read_text(encoding="utf-8")
    base_name, final_version, full_name = normalize_app_and_version(app_name, version)
    filled = fill_template_variables(
        raw,
        app_name=base_name,
        version=final_version,
        company_name=company_name,
        short_name=short_name,
        date_str=date_str,
    )
    title = f"{full_name} 详细设计说明书"
    return markdown_to_docx(filled, output_path, doc_title=title, footer_label=full_name)


def get_default_template_path(template_name: str) -> Path:
    """自适应探测模板文件路径。"""
    candidates = [
        Path(__file__).resolve().parent.parent / "templates" / template_name,
        Path.cwd() / "templates" / template_name,
        Path.cwd() / ".agents" / "skills" / "copyright-kit" / "templates" / template_name,
    ]
    for c in candidates:
        if c.is_file():
            return c
    return candidates[0]


def export_all_docs(
    target_dir: Path,
    app_name: str = "",
    version: str = "V1.0",
    company_name: str = "",
    short_name: str = "",
    date_str: str = "",
) -> list[Path]:
    """一键为目标目录导出或转出用户操作说明书与详细设计说明书的 Word (.docx) 版本。"""
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    results: list[Path] = []

    # 1. 用户操作说明书
    manual_md = target_dir / "software_user_manual.md"
    manual_src = manual_md if manual_md.exists() else get_default_template_path("user_manual_template.md")
    manual_docx = target_dir / "software_user_manual.docx"
    if manual_src.exists():
        p1 = export_manual_doc(
            manual_src,
            manual_docx,
            app_name=app_name,
            version=version,
            company_name=company_name,
            short_name=short_name,
            date_str=date_str,
        )
        results.append(p1)

    # 2. 详细设计说明书
    design_md = target_dir / "software_design_specification.md"
    design_src = design_md if design_md.exists() else get_default_template_path("design_specification_template.md")
    design_docx = target_dir / "software_design_specification.docx"
    if design_src.exists():
        p2 = export_design_doc(
            design_src,
            design_docx,
            app_name=app_name,
            version=version,
            company_name=company_name,
            short_name=short_name,
            date_str=date_str,
        )
        results.append(p2)

    return results


# ==============================================================================
# 5. CLI 命令行入口
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="导出软件著作权《用户操作说明书》与《详细设计说明书》原生 Word (.docx) 鉴别材料"
    )
    parser.add_argument("--input", "-i", help="输入的 Markdown 说明书文件或模板路径")
    parser.add_argument("--output", "-o", help="输出的 Word (.docx) 目标路径")
    parser.add_argument(
        "--type",
        choices=["manual", "design", "auto"],
        default="auto",
        help="文档类型: manual (用户手册), design (详细设计), auto (自动识别)",
    )
    parser.add_argument("--all", action="store_true", help="一键为目标目录导出用户手册与设计说明书双 docx 版本")
    parser.add_argument("--dir", default="docs/copyright", help="目标输出目录 (与 --all 联用，默认: docs/copyright)")
    parser.add_argument("--app-name", help="软件全称 (如: SeedFlow家庭资产数字化记账软件 V1.0)")
    parser.add_argument("--version", default="V1.0", help="软件版本号 (默认: V1.0)")
    parser.add_argument("--company", default="", help="著作权人名称 (企业或个人)")
    parser.add_argument("--short-name", default="", help="软件简称")
    parser.add_argument("--date", default="", help="编写日期")

    args = parser.parse_args()

    app_name = args.app_name or "自研数字化协同管理软件"
    version = args.version or "V1.0"
    company = args.company or "自主研发申报主体"

    print("=" * 68)
    print("📄 正在生成软件著作权鉴别材料 Word (.docx) 版...")
    print(f"   软件全称: {app_name} | 版本号: {version}")

    if args.all:
        target_dir = Path(args.dir).resolve()
        exported = export_all_docs(
            target_dir=target_dir,
            app_name=app_name,
            version=version,
            company_name=company,
            short_name=args.short_name,
            date_str=args.date,
        )
        print(f"✅ 成功一键导出 {len(exported)} 个 Word 排版说明书文档:")
        for p in exported:
            print(f"   - {p}")
        print("=" * 68)
        return

    # 单文件转换模式
    if not args.input:
        print("❌ 错误: 未指定输入文件，请使用 --input <file.md> 或指定 --all", file=sys.stderr)
        sys.exit(1)

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"❌ 错误: 输入文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        out_path = Path(args.output).resolve()
    else:
        out_path = input_path.with_suffix(".docx")

    doc_type = args.type
    if doc_type == "auto":
        if "design" in input_path.name.lower() or "设计" in input_path.name:
            doc_type = "design"
        else:
            doc_type = "manual"

    if doc_type == "design":
        res = export_design_doc(
            input_path=input_path,
            output_path=out_path,
            app_name=app_name,
            version=version,
            company_name=company,
            short_name=args.short_name,
            date_str=args.date,
        )
    else:
        res = export_manual_doc(
            input_path=input_path,
            output_path=out_path,
            app_name=app_name,
            version=version,
            company_name=company,
            short_name=args.short_name,
            date_str=args.date,
        )

    print(f"✅ 成功导出 Word 排版文档: {res}")
    print("=" * 68)


if __name__ == "__main__":
    main()
