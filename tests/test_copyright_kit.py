"""tests/test_copyright_kit.py — 软件著作权抽取与审计工具链自动化单元测试。"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from scripts.audit_copyright_package import (
    audit_application_form,
    audit_cross_materials_alignment,
    audit_design_document,
    audit_manual_document,
    audit_naming,
    audit_source_file,
    audit_source_package,
)
from scripts.export_copyright_source import (
    clean_source_line,
    detect_app_name,
    detect_src_dirs,
    export_as_docx,
    export_as_pdf,
    is_excluded,
    normalize_app_and_version,
    paginate_source_code,
    update_application_card_sloc,
)
from scripts.export_document_docx import (
    export_all_docs,
    export_design_doc,
    export_manual_doc,
    markdown_to_docx,
)



def test_clean_source_line_removes_forbidden_keywords():
    """Given 多语言代码行包含 TODO, FIXME 或第三方版权声明 When 执行清洗 Then 违规词被安全剥离."""
    # 1. Python / Shell 注释
    raw_todo = "def calculate_balance(): # TODO: fix precision issue"
    assert "TODO" not in clean_source_line(raw_todo)
    assert clean_source_line(raw_todo).strip() == "def calculate_balance(): #"

    raw_fixme = "return data # FIXME: optimize loop"
    assert "FIXME" not in clean_source_line(raw_fixme)

    # 2. SQL 注释
    raw_sql = "SELECT id, balance FROM accounts; -- TODO: optimize query index"
    cleaned_sql = clean_source_line(raw_sql)
    assert "TODO" not in cleaned_sql
    assert cleaned_sql.strip() == "SELECT id, balance FROM accounts;"

    # 3. HTML / XML 注释
    raw_html = "<div>{{ user.name }}</div> <!-- FIXME: add fallback avatar -->"
    cleaned_html = clean_source_line(raw_html)
    assert "FIXME" not in cleaned_html
    assert cleaned_html.strip() == "<div>{{ user.name }}</div>"

    # 4. C / CSS 块注释
    raw_css = ".card { border-radius: 8px; } /* XXX: adapt dark theme */"
    cleaned_css = clean_source_line(raw_css)
    assert "XXX" not in cleaned_css
    assert cleaned_css.strip() == ".card { border-radius: 8px; }"

    # 5. 第三方商业版权头与声明
    raw_copyright = "# Copyright (c) 2023 Facebook, Inc. All rights reserved."
    assert "Copyright" not in clean_source_line(raw_copyright)
    assert "All rights reserved" not in clean_source_line(raw_copyright)


def test_is_excluded_directory():
    """Given 目录路径包含 node_modules 或 .venv When 检查排除状态 Then 返回 True."""
    excludes = {"node_modules", "dist", ".venv"}
    assert is_excluded(Path("apps/web/node_modules/vue/index.js"), excludes) is True
    assert is_excluded(Path("apps/api/.venv/lib/python/site.py"), excludes) is True
    assert is_excluded(Path("apps/api/src/main.py"), excludes) is False


def test_paginate_source_code_header_and_density():
    """Given 多行代码数据 When 执行分页排版 Then 注入标准两端对齐页眉且切分为指定页数."""
    lines = [f"const x_{i} = {i};" for i in range(110)]
    paginated = paginate_source_code(
        lines=lines,
        app_name="测试财务管理软件",
        version="V1.0",
        lines_per_page=55,
        total_pages=2,
    )

    pages = paginated.split("\f")
    assert len(pages) == 2
    assert "测试财务管理软件 V1.0" in pages[0]
    assert "第 1 页" in pages[0]
    assert "第 2 页" in pages[1]


def test_audit_naming_rules():
    """Given 软件全称与版本号 When 进行合规审计 Then 正确识别法定后缀与大写 V."""
    # 合规
    assert audit_naming("资产数字化记账软件", "V1.0") == []
    assert audit_naming("供应链数据治理系统", "V2.1.0") == []

    # 违规：缺少法定后缀
    errs_suffix = audit_naming("MyPlatform", "V1.0")
    assert any("必须以法定名词结尾" in e for e in errs_suffix)

    # 违规：版本号缺少大写 V
    errs_ver = audit_naming("财务管理软件", "1.0.0")
    assert any("大写字母 'V' 开头" in e for e in errs_ver)


def test_audit_source_file_validation(tmp_path: Path):
    """Given 格式合规的源程序文档 When 执行审计 Then 0 错误通过."""
    doc_path = tmp_path / "source_code_60pages.txt"

    # 构造 1 页合格的内容
    header = "测试财务管理软件 V1.0                                                  第 1 页\n"
    divider = "-" * 80 + "\n"
    code = "\n".join([f"let line_{i} = {i};" for i in range(55)]) + "\n"
    doc_path.write_text(header + divider + code, encoding="utf-8")

    errs = audit_source_file(doc_path, expected_name="测试财务管理软件", expected_ver="V1.0")
    assert errs == []


def test_detect_app_name_and_src_dirs(tmp_path: Path):
    """Given 一个陌生项目目录结构 When 探测元数据 Then 智能推断合规应用名称与代码路径."""
    # 构造 package.json
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({"name": "@cool-org/cloud-collab"}), encoding="utf-8")

    # 构造常见源码目录
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "index.ts").write_text("console.log('hello');\n", encoding="utf-8")

    # 验证智能嗅探
    name = detect_app_name(tmp_path)
    assert name == "Cloud Collab管理软件"

    dirs = detect_src_dirs(tmp_path)
    assert src_dir in dirs


def test_update_application_card_sloc(tmp_path: Path):
    """Given 包含旧源程序量的申请表卡 When 执行行数同步 Then 精确回填千分位格式的行数."""
    card = tmp_path / "cpcc_application_info.md"
    card.write_text(
        "| **源程序量** | `28,500` 行 |\n| **其他** | `值` |\n",
        encoding="utf-8",
    )

    success = update_application_card_sloc(card, 56624)
    assert success is True

    updated_text = card.read_text(encoding="utf-8")
    assert "| **源程序量** | `56,624` 行 |" in updated_text


def test_export_as_docx_generation(tmp_path: Path):
    """Given 代码行集合 When 导出为 docx 格式 Then 生成合法的 Word OpenXML zip 压缩包且结构完备."""
    import zipfile

    lines = [f"const val_{i} = {i};" for i in range(110)]
    docx_file = tmp_path / "source_code_60pages.docx"

    export_as_docx(
        lines=lines,
        app_name="测试数字化协同软件",
        version="V1.0",
        output_docx_path=docx_file,
        lines_per_page=55,
        total_pages=2,
    )

    assert docx_file.exists()
    assert docx_file.stat().st_size > 500

    # 验证 zip 内部关键 OpenXML 部件
    with zipfile.ZipFile(docx_file, "r") as z:
        file_list = z.namelist()
        assert "[Content_Types].xml" in file_list
        assert "word/document.xml" in file_list
        assert "word/styles.xml" in file_list

        doc_xml = z.read("word/document.xml").decode("utf-8")
        assert "测试数字化协同软件 V1.0" in doc_xml
        assert "第 1 页" in doc_xml
        assert "第 2 页" in doc_xml
        assert "const val_0 = 0;" in doc_xml


def test_normalize_app_and_version():
    """Given 各种格式的应用名称与版本号 When 进行规范化 Then 输出干净的基础名称、大写版本与全称."""
    # 1. 全称尾部自带版本号
    base, ver, full = normalize_app_and_version("SeedFlow家庭资产数字化记账软件 V1.0", "V1.0")
    assert base == "SeedFlow家庭资产数字化记账软件"
    assert ver == "V1.0"
    assert full == "SeedFlow家庭资产数字化记账软件 V1.0"

    # 2. 全称不带版本号
    base2, ver2, full2 = normalize_app_and_version("SeedFlow家庭资产数字化记账软件", "V1.0")
    assert base2 == "SeedFlow家庭资产数字化记账软件"
    assert ver2 == "V1.0"
    assert full2 == "SeedFlow家庭资产数字化记账软件 V1.0"

    # 3. 小写 v 自动转为大写 V
    base3, ver3, full3 = normalize_app_and_version("某某协同系统", "v2.1.0")
    assert ver3 == "V2.1.0"
    assert full3 == "某某协同系统 V2.1.0"


def test_export_as_pdf_generation(tmp_path: Path):
    """Given 源码行集合 When 导出为官方 PDF 格式 Then 纯标准库输出符合规格的 A4 UTF-8 PDF 文件."""
    lines = [f"const record_{i} = {i}; // 业务逻辑代码" for i in range(110)]
    pdf_file = tmp_path / "source_code_60pages.pdf"

    export_as_pdf(
        lines=lines,
        app_name="SeedFlow家庭资产数字化记账软件 V1.0",
        version="V1.0",
        output_pdf_path=pdf_file,
        lines_per_page=55,
        total_pages=2,
    )

    assert pdf_file.exists()
    assert pdf_file.stat().st_size > 1000

    content_bytes = pdf_file.read_bytes()
    assert content_bytes.startswith(b"%PDF-1.4")
    assert b"%%EOF" in content_bytes
    assert b"/STSong-Light" in content_bytes
    assert b"/UniGB-UTF16-H" in content_bytes


def get_template_path() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent / "templates",
        Path(__file__).resolve().parent.parent / ".agents" / "skills" / "copyright-kit" / "templates",
        Path(__file__).resolve().parent.parent.parent / "copyright-kit" / "templates",
    ]
    for c in candidates:
        if (c / "cpcc_form_fields.md").exists():
            return c
    return candidates[0]


def test_audit_application_form_with_template():
    """Given 模板库中的标准三页申请表 When 运行门禁审计 Then 100% 验证通过且字数结构达标."""
    template_path = get_template_path()
    errs, meta = audit_application_form(template_path)
    assert errs == [], f"Template cpcc_form_fields.md should pass audit, but got: {errs}"
    assert meta["form_version"] == "{{VERSION}}"


def test_audit_application_form_word_count_limits(tmp_path: Path):
    """Given 申请表主要功能字数不足或结构缺失 When 审计 Then 拦截并提示."""
    short_card = tmp_path / "cpcc_application_info.md"
    # 字数不足 500 字
    short_card.write_text("""
# 申请表
| **软件全称** | `测试软件 V1.0` |
| **版本号** | `V1.0` |
| **权利获得方式** | `原始取得` |
| **软件分类** | `应用软件` |
| **软件说明** | `原创` |
| **开发方式** | `独立开发` |
| **开发完成日期** | `2026-03-01` |
| **发表状态** | `未发表` |
| **著作权人** | `测试公司` |
| **硬件环境** | `Mac` |
| **操作系统** | `macOS` |
| **开发工具** | `VSCode` |
| **源程序量** | `1000` 行 |
| **开发目的** | `测试目的` |
| **面向领域** | `金融` |
| **技术特点** | `高性能` |

```text
这是一个简短的功能描述，远远不足五百字。
```
""", encoding="utf-8")

    errs, _ = audit_application_form(tmp_path)
    assert any("字数严重不足" in e for e in errs)
    assert any("研发背景" in e for e in errs)


def test_audit_design_document_validation():
    """Given 详细设计说明书模板 When 审计 Then 验证流程图与章节完整性."""
    template_path = get_template_path()
    doc_path = template_path / "design_specification_template.md"
    assert doc_path.exists()
    content = doc_path.read_text(encoding="utf-8")
    assert "```mermaid" in content
    assert "总体技术架构" in content
    assert "业务流程" in content




def test_audit_cross_materials_alignment_strict():
    """Given 申报材料间存在大小写不一致 (V1.0 vs v1.0) 或全称不一致 When 审计 Then 严格阻断拦截."""
    # 1. 大小写不一致
    mismatched_meta = {
        "form_version": "V1.0",
        "source_version": "v1.0",
        "form_app_name": "测试协同软件 V1.0",
        "source_full_title": "测试协同软件 V1.0",
    }
    errs = audit_cross_materials_alignment(mismatched_meta)
    assert len(errs) > 0
    assert any("版本号不一致" in e for e in errs)

    # 2. 完全一致
    aligned_meta = {
        "form_version": "V1.0",
        "source_version": "V1.0",
        "manual_version": "V1.0",
        "design_version": "V1.0",
        "form_app_name": "SeedFlow家庭资产数字化记账软件 V1.0",
        "source_full_title": "SeedFlow家庭资产数字化记账软件 V1.0",
        "manual_app_name": "SeedFlow家庭资产数字化记账软件 V1.0",
        "design_app_name": "SeedFlow家庭资产数字化记账软件 V1.0",
    }
    errs_aligned = audit_cross_materials_alignment(aligned_meta)
    assert errs_aligned == []


def test_markdown_to_docx_rich_elements(tmp_path: Path):
    """Given 包含多级标题、表格、代码块、引用框与截图标记的 Markdown When 转换为 docx Then 生成合规 OpenXML 部件."""
    import zipfile

    md_sample = """# 测试系统 用户操作说明书

> **软件全称**：测试数字化管理系统 V1.0  
> **版本号**：V1.0  

## 第一章 系统概述
这是一个核心概述段落，包含 **粗体字**、*斜体字*、`console.log('hi')` 与 [官方链接](https://example.com)。

> ⚠️ **CPCC 审查硬指标**：必须上传真实界面截图！

| 模块名称 | 状态 | 职责 |
| :--- | :--- | :--- |
| 认证中心 | 正常 | 负责鉴权 |
| 数据网关 | 正常 | 路由分发 |

*（【必须插入】软件主界面全景高清截图：测试数字化管理系统 V1.0）*

```mermaid
graph TD
    A[客户端] --> B[网关]
```

- 列表项 1
- 列表项 2
"""
    output_docx = tmp_path / "rich_sample.docx"
    markdown_to_docx(md_sample, output_docx, doc_title="测试数字化管理系统 V1.0")

    assert output_docx.exists()
    assert output_docx.stat().st_size > 1000

    with zipfile.ZipFile(output_docx, "r") as z:
        names = z.namelist()
        assert "[Content_Types].xml" in names
        assert "word/document.xml" in names
        assert "word/header1.xml" in names
        assert "word/footer1.xml" in names

        doc_xml = z.read("word/document.xml").decode("utf-8")
        assert "测试系统 用户操作说明书" in doc_xml
        assert "<w:tbl>" in doc_xml
        assert "认证中心" in doc_xml
        assert "📸【系统界面全景 / 功能操作真实截图粘贴区】" in doc_xml

        hdr_xml = z.read("word/header1.xml").decode("utf-8")
        assert "测试数字化管理系统 V1.0" in hdr_xml
        assert "CPCC" in hdr_xml

        ftr_xml = z.read("word/footer1.xml").decode("utf-8")
        assert "fldSimple" in ftr_xml


def test_export_manual_and_design_docx_from_templates(tmp_path: Path):
    """Given 用户手册与详细设计说明书模板 When 导出为 docx Then 生成合法的 Word 文档且通过审计门禁."""
    template_dir = get_template_path()
    manual_tpl = template_dir / "user_manual_template.md"
    design_tpl = template_dir / "design_specification_template.md"

    out_manual_docx = tmp_path / "software_user_manual.docx"
    out_design_docx = tmp_path / "software_design_specification.docx"

    export_manual_doc(
        manual_tpl,
        out_manual_docx,
        app_name="智能协同管理软件",
        version="V1.0",
        company_name="开源创新科技",
    )
    export_design_doc(
        design_tpl,
        out_design_docx,
        app_name="智能协同管理软件",
        version="V1.0",
        company_name="开源创新科技",
    )

    assert out_manual_docx.exists()
    assert out_design_docx.exists()

    # 门禁审计纯 docx 目录
    m_errs, m_meta = audit_manual_document(tmp_path)
    assert m_errs == [], f"Manual docx should pass audit: {m_errs}"
    assert m_meta["manual_version"] == "V1.0"
    assert "智能协同管理软件" in m_meta["manual_app_name"]

    d_errs, d_meta = audit_design_document(tmp_path)
    assert d_errs == [], f"Design docx should pass audit: {d_errs}"
    assert d_meta["design_version"] == "V1.0"
    assert "智能协同管理软件" in d_meta["design_app_name"]


def test_export_all_docs_helper(tmp_path: Path):
    """Given 目标目录 When 调用 export_all_docs Then 一键生成双份 Word (.docx) 鉴别材料."""
    docs = export_all_docs(
        tmp_path,
        app_name="资产分析管理系统",
        version="V2.0",
        company_name="云端智联科技",
    )
    assert len(docs) == 2
    assert (tmp_path / "software_user_manual.docx").exists()
    assert (tmp_path / "software_design_specification.docx").exists()

    # 验证双文档跨文件强一致性比对
    _, m_meta = audit_manual_document(tmp_path)
    _, d_meta = audit_design_document(tmp_path)
    combined = {**m_meta, **d_meta, "form_version": "V2.0", "source_version": "V2.0"}
    assert audit_cross_materials_alignment(combined) == []



