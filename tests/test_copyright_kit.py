"""tests/test_copyright_kit.py — 软件著作权抽取与审计工具链自动化单元测试。"""

import json
from pathlib import Path
import pytest
from scripts.audit_copyright_package import audit_naming, audit_source_file
from scripts.export_copyright_source import (
    clean_source_line,
    detect_app_name,
    detect_src_dirs,
    export_as_docx,
    is_excluded,
    paginate_source_code,
    update_application_card_sloc,
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


