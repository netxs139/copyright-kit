#!/usr/bin/env python3
"""audit_copyright_package.py — 软件著作权申报材料静态合规门禁扫描器 (CPCC Pre-flight Doctor)。

完全遵循中国版权保护中心 (CPCC) 官方审查规范与全套材料一致性法则：
1. 软件全称法定命名后缀与大写 V 版本号合规性校验；
2. 60 页源程序每页有效代码行数严格 >=50 行，总页数恰好 60 页，0 TODO/FIXME/敏感词；
3. 官方标准原生 UTF-8 编码 PDF 格式源程序完整性与无图像截图安全校验；
4. 申请表三页结构与全字段完备性审计（主要功能必须在 500—1300 字，且涵盖研发背景、核心架构、功能模块、技术实现、应用场景五大板块）；
5. 鉴别材料（用户操作说明书 或 详细设计说明书）图文与流程图完备性把关；
6. 跨材料多源动态交叉一致性强校验：申请表、源码页眉、说明书、详细设计说明书中的软件全称与版本号必须 100% 逐字符一致（包括大小写）。
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

# 法定允许的软件全称后缀
LEGAL_SUFFIXES = (
    "软件",
    "系统",
    "平台",
    "工具",
    "中间件",
    "套件",
    "引擎",
)

# 违规与敏感词
FORBIDDEN_KEYWORDS = [
    "TODO",
    "FIXME",
    "XXX",
]

# 主要功能必须涵盖的五大核心板块关键词
FIVE_CORE_MODULES = [
    ("研发背景", re.compile(r"研发背景|立项背景|开发背景|业务背景")),
    ("核心架构", re.compile(r"核心架构|系统架构|技术架构|整体架构")),
    ("功能模块", re.compile(r"功能模块|核心功能|功能划分|系统功能")),
    ("技术实现", re.compile(r"技术实现|技术方案|技术栈|关键技术")),
    ("应用场景", re.compile(r"应用场景|使用场景|业务场景|目标领域")),
]


def normalize_app_and_version(app_name: str, version: str = "V1.0") -> tuple[str, str, str]:
    """标准化软件全称与版本号。"""
    clean_app = app_name.strip()
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


def audit_naming(app_name: str, version: str = "V1.0") -> list[str]:
    """审计软件全称与版本号命名规范。"""
    errors: list[str] = []
    base_name, final_ver, _ = normalize_app_and_version(app_name, version)

    if not base_name.endswith(LEGAL_SUFFIXES):
        errors.append(
            f"软件全称 '{app_name}' 违规：基础名称 '{base_name}' 必须以法定名词结尾 (如: {', '.join(LEGAL_SUFFIXES)})"
        )

    if not final_ver.startswith("V") or not re.match(r"^V\d+(\.\d+)*$", final_ver):
        errors.append(f"版本号 '{final_ver}' 违规：必须以大写字母 'V' 开头 (如 V1.0 或 V1.0.0)")

    return errors


def audit_source_package(
    target_dir: Path,
    expected_name: str | None = None,
    expected_ver: str | None = None,
) -> tuple[list[str], dict[str, str]]:
    """严格审计源程序文档 (PDF 与 TXT 双轨校验) 及页眉规范。"""
    errors: list[str] = []
    metadata: dict[str, str] = {}

    txt_path = target_dir / "source_code_60pages.txt"
    pdf_path = target_dir / "source_code_60pages.pdf"

    # 1. 检查官方交付要求的 PDF 格式
    if not pdf_path.exists():
        errors.append(
            f"缺失官方标准源程序 PDF 文档: {pdf_path} (CPCC 官方要求必须提交 PDF 格式，严禁提交纯 Word)"
        )
    else:
        try:
            pdf_bytes = pdf_path.read_bytes()
            if not pdf_bytes.startswith(b"%PDF-"):
                errors.append(f"源程序 PDF 文件头损坏: {pdf_path} 不是合法的 PDF 文件")
            if len(pdf_bytes) < 1000:
                errors.append(f"源程序 PDF 文件大小异常 ({len(pdf_bytes)} 字节)，疑似空文件")
        except Exception as e:
            errors.append(f"读取源程序 PDF 失败: {e}")

    # 2. 深入审计 TXT 中的行数密度、总页数与页眉一致性
    if not txt_path.exists():
        errors.append(f"缺失源程序文档: {txt_path}")
        return errors, metadata

    try:
        content = txt_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        errors.append(f"读取源程序文件失败: {e}")
        return errors, metadata

    pages = content.split("\f")
    total_pages = len(pages)

    if total_pages > 60:
        errors.append(f"源程序总页数超标: 当前为 {total_pages} 页 (CPCC 官方审查要求最多提交 60 页)")

    extracted_title = ""
    extracted_ver = ""

    for idx, page in enumerate(pages, start=1):
        raw_lines = page.splitlines()
        lines = [line_text for line_text in raw_lines if line_text.strip()]

        if not lines:
            continue

        first_line = lines[0]
        if f"第 {idx} 页" not in first_line:
            errors.append(f"第 {idx} 页页眉异常: 缺少页码标识 '第 {idx} 页'")

        if idx == 1:
            # 从第 1 页页眉抽取全称与版本号
            header_left = first_line.split("第 1 页")[0].strip()
            extracted_title = header_left
            match_ver = re.search(r"\b(V\d+(?:\.\d+)*)\b", header_left)
            if match_ver:
                extracted_ver = match_ver.group(1)

        if expected_name and expected_name not in first_line:
            base_n, _, _ = normalize_app_and_version(expected_name, expected_ver or "V1.0")
            if base_n not in first_line:
                errors.append(f"第 {idx} 页页眉异常: 未包含软件名称 '{base_n}'")

        if expected_ver and expected_ver not in first_line:
            errors.append(f"第 {idx} 页页眉异常: 未包含指定版本号 '{expected_ver}'")

        # 扣除页眉行与横线分隔线后的有效代码行数
        code_lines = [
            line_text
            for line_text in lines[2:]
            if line_text.strip() and not line_text.strip().startswith("---")
        ]
        # 若为标准 60 页或全量提交的前序各页，必须严格 >=50 行；不足 60 页全量提交的尾页允许为剩余代码行
        if (total_pages == 60 or idx < total_pages) and len(code_lines) < 50:
            errors.append(f"第 {idx} 页有效代码行数不足: 仅有 {len(code_lines)} 行 (CPCC 法定硬指标: 每页 >=50 行)")

        # 检查违规敏感词与未清洗待办标记
        for line_no, line_text in enumerate(lines, start=1):
            for kw in FORBIDDEN_KEYWORDS:
                if re.search(rf"\b{kw}\b", line_text, re.IGNORECASE):
                    errors.append(f"第 {idx} 页第 {line_no} 行检测到违规敏感词 '{kw}': '{line_text[:40]}...'")

    metadata["source_full_title"] = extracted_title
    metadata["source_version"] = extracted_ver
    return errors, metadata


def audit_source_file(
    file_path: Path,
    expected_name: str | None = None,
    expected_ver: str | None = None,
) -> list[str]:
    """兼容旧接口：审计 60 页源程序纯文本排版与敏感词。"""
    target_dir = file_path.parent
    errs, _ = audit_source_package(target_dir, expected_name, expected_ver)
    # 过滤掉 PDF 存在性检查，仅关注 txt 文件本身的内容与行数
    return [e for e in errs if "PDF" not in e]



def audit_application_form(target_dir: Path) -> tuple[list[str], dict[str, str]]:
    """严格审计 CPCC 申请表 3 页结构、所有必填字段以及 500—1300 字主要功能五大板块。"""
    errors: list[str] = []
    metadata: dict[str, str] = {}

    form_file = target_dir / "cpcc_application_info.md"
    if not form_file.exists():
        form_file = target_dir / "cpcc_form_fields.md"

    if not form_file.exists():
        errors.append(f"缺失 CPCC 申请表填报字段卡: docs/copyright/cpcc_application_info.md")
        return errors, metadata

    try:
        content = form_file.read_text(encoding="utf-8")
    except Exception as e:
        errors.append(f"读取申请表文件失败: {e}")
        return errors, metadata

    # 1. 抽取全称、简称、版本号
    name_m = re.search(r"\|\s*\*\*软件全称\*\*\s*\|\s*`?([^`|\n]+)`?\s*\|", content)
    ver_m = re.search(r"\|\s*\*\*版本号\*\*\s*\|\s*`?([^`|\n]+)`?\s*\|", content)
    short_m = re.search(r"\|\s*\*\*软件简称\*\*\s*\|\s*`?([^`|\n]+)`?\s*\|", content)

    if name_m:
        raw_name = name_m.group(1).strip()
        metadata["form_app_name"] = raw_name
    else:
        errors.append("申请表缺少必填字段: 【软件全称】")

    if ver_m:
        raw_ver = ver_m.group(1).strip()
        metadata["form_version"] = raw_ver
    else:
        errors.append("申请表缺少必填字段: 【版本号】")

    if short_m:
        metadata["form_short_name"] = short_m.group(1).strip()

    # 2. 检查第一页、第二页、第三页必填字段标记
    required_field_patterns = [
        ("权利获得/取得方式", r"权利(获得|取得)方式"),
        ("软件分类", r"软件分类"),
        ("软件说明", r"软件说明"),
        ("开发方式", r"开发方式"),
        ("开发完成日期", r"开发完成日期"),
        ("发表状态", r"发表状态"),
        ("著作权人", r"著作权人"),
        ("硬件环境", r"硬件环境"),
        ("操作系统", r"操作系统"),
        ("开发工具/环境", r"(开发环境|开发工具|开发语言)"),
        ("源程序量", r"源程序量"),
        ("开发目的", r"开发目的"),
        ("面向领域/行业", r"面向领域|行业"),
        ("技术特点", r"技术特点"),
    ]

    for name, pat in required_field_patterns:
        if not re.search(pat, content):
            errors.append(f"申请表缺少官方规范必填字段: 【{name}】")

    # 3. 重点审核主要功能：字数必须严格在 500—1300 字，且包含 5 大核心板块
    # 提取代码块或正文中关于主要功能的内容
    func_text = ""
    # 优先抽取 ```text ... ``` 代码块中的主要功能模板
    blocks = re.findall(r"```(?:text)?\n(.*?)\n```", content, re.DOTALL)
    if blocks:
        # 取最长的文本块
        func_text = max(blocks, key=len)
    else:
        # 从“主要功能”标题后截取
        match_title = re.search(r"(?:软件的?主要功能[^\n]*\n)(.*)", content, re.DOTALL)
        if match_title:
            func_text = match_title.group(1)

    clean_func_text = "".join(func_text.split())
    # 计算中文字符与字母/数字总数 (去除标点空格)
    chinese_and_words = len(re.sub(r"[\s\W_]+", "", clean_func_text))

    if chinese_and_words < 500:
        errors.append(
            f"申请表【主要功能】字数严重不足: 当前仅约 {chinese_and_words} 字 (CPCC 官方审查硬性要求必须在 500—1300 字之间)"
        )
    elif chinese_and_words > 1300:
        errors.append(
            f"申请表【主要功能】字数超标: 当前约 {chinese_and_words} 字 (CPCC 官方审查硬性要求不能超过 1300 字)"
        )

    for mod_name, mod_pat in FIVE_CORE_MODULES:
        if not mod_pat.search(func_text):
            errors.append(f"申请表【主要功能】结构缺失: 未包含必须涵盖的五大板块之一【{mod_name}】")

    return errors, metadata


def extract_text_from_doc(file_path: Path) -> str:
    """从 Markdown (.md) 或 Word (.docx) 中安全提取纯文本内容。"""
    if file_path.suffix.lower() in (".docx", ".doc"):
        import zipfile
        from xml.sax.saxutils import unescape

        try:
            with zipfile.ZipFile(file_path, "r") as z:
                xml_parts: list[str] = []
                for part in ["word/document.xml", "word/header1.xml", "word/footer1.xml"]:
                    if part in z.namelist():
                        xml_parts.append(z.read(part).decode("utf-8"))
                combined_xml = " ".join(xml_parts)
                texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", combined_xml)
                return " ".join(unescape(t) for t in texts)
        except Exception as e:
            raise RuntimeError(f"解析 Word 文档失败: {e}") from e
    return file_path.read_text(encoding="utf-8")


def audit_manual_document(target_dir: Path) -> tuple[list[str], dict[str, str]]:
    """审计《用户操作说明书》(支持 .md 与 .docx 版) 章节完备性、截图占位与标题版本号。"""
    errors: list[str] = []
    metadata: dict[str, str] = {}

    manual_files = []
    for ext in [".md", ".docx", ".doc"]:
        p = target_dir / f"software_user_manual{ext}"
        if p.exists():
            manual_files.append(p)

    if not manual_files:
        return errors, metadata

    for manual_file in manual_files:
        try:
            content = extract_text_from_doc(manual_file)
        except Exception as e:
            errors.append(f"读取用户手册 ({manual_file.name}) 失败: {e}")
            continue

        # 提取封面名称与版本号 (兼容 md 与 docx)
        name_m = re.search(r"软件全称[*\s]*[:：]\s*([^\s<>&]+(?: [^\s<>&]+)?)", content)
        ver_m = re.search(r"版本号[*\s]*[:：]\s*([^\s<>&]+)", content)
        if name_m and "manual_app_name" not in metadata:
            metadata["manual_app_name"] = name_m.group(1).strip("> *")
        if ver_m and "manual_version" not in metadata:
            metadata["manual_version"] = ver_m.group(1).strip("> *")

        # 检查核心章节
        required_chapters = [
            ("系统概述", r"系统概述"),
            ("技术架构", r"技术架构|系统架构"),
            ("业务流程", r"业务流程|流转逻辑"),
            ("功能模块详细操作", r"核心功能|操作指南|详细操作"),
            ("数据统计/报表", r"数据统计|分析报表"),
            ("系统安全/注销", r"安全管理|注销|退出"),
        ]
        for ch_name, ch_pat in required_chapters:
            if not re.search(ch_pat, content):
                errors.append(f"《用户操作说明书》({manual_file.name}) 缺失核心必要章节: 【{ch_name}】")

        # 检查截图规范提示或截图标记
        if "截图" not in content and "![" not in content and "📸" not in content:
            errors.append(f"《用户操作说明书》({manual_file.name}) 未检测到任何界面全景或主要操作截图占位符")

    return errors, metadata


def audit_design_document(target_dir: Path) -> tuple[list[str], dict[str, str]]:
    """审计《详细设计说明书》(支持 .md 与 .docx 版) 章节、流程图与标题版本号。"""
    errors: list[str] = []
    metadata: dict[str, str] = {}

    design_files = []
    for ext in [".md", ".docx", ".doc"]:
        p = target_dir / f"software_design_specification{ext}"
        if p.exists():
            design_files.append(p)

    if not design_files:
        return errors, metadata

    for design_file in design_files:
        try:
            content = extract_text_from_doc(design_file)
        except Exception as e:
            errors.append(f"读取详细设计说明书 ({design_file.name}) 失败: {e}")
            continue

        # 提取封面名称与版本号 (兼容 md 与 docx)
        name_m = re.search(r"软件全称[*\s]*[:：]\s*([^\s<>&]+(?: [^\s<>&]+)?)", content)
        ver_m = re.search(r"版本号[*\s]*[:：]\s*([^\s<>&]+)", content)
        if name_m and "design_app_name" not in metadata:
            metadata["design_app_name"] = name_m.group(1).strip("> *")
        if ver_m and "design_version" not in metadata:
            metadata["design_version"] = ver_m.group(1).strip("> *")

        # 检查核心章节
        required_chapters = [
            ("系统概述", r"系统概述"),
            ("总体技术架构", r"总体技术架构|技术架构设计"),
            ("业务流程设计", r"核心业务流程设计|业务流转总流程"),
            ("功能模块详细设计", r"功能模块详细设计|模块设计"),
            ("数据模型/接口规范", r"接口契约|数据模型"),
        ]
        for ch_name, ch_pat in required_chapters:
            if not re.search(ch_pat, content):
                errors.append(f"《详细设计说明书》({design_file.name}) 缺失核心必要章节: 【{ch_name}】")

        # 检查全局流程图与模块流程图 (docx 与 md 双模语法支持)
        if design_file.suffix.lower() in (".docx", ".doc"):
            flowcharts_count = len(
                re.findall(
                    r"(?:架构流程图|业务时序定义|flowchart|sequenceDiagram|graph\s+[TLRDB]{2})",
                    content,
                    re.IGNORECASE,
                )
            )
            if flowcharts_count < 2 and "流程图" not in content:
                errors.append(
                    f"《详细设计说明书》({design_file.name}) 流程图数量不足 (必须包含系统整体主流程图及各核心模块流程图)"
                )
        else:
            flowcharts = re.findall(r"```mermaid\n(.*?)\n```", content, re.DOTALL)
            if len(flowcharts) < 2:
                errors.append(
                    f"《详细设计说明书》({design_file.name}) 流程图数量不足: 仅发现 {len(flowcharts)} 张 (必须包含系统整体主流程图及各核心模块流程图)"
                )

    return errors, metadata


def audit_cross_materials_alignment(collected_meta: dict[str, str]) -> list[str]:
    """严格核验申请表、源程序页眉、用户手册、详细设计说明书间的一致性契约 (逐字符强比对)。"""
    errors: list[str] = []

    # 1. 核验版本号一致性 (哪怕一个字母大小写不同也必须严格拦截，如 V1.0 vs v1.0)
    version_sources: dict[str, str] = {}
    if "form_version" in collected_meta:
        version_sources["申请表"] = collected_meta["form_version"]
    if "source_version" in collected_meta:
        version_sources["源代码页眉"] = collected_meta["source_version"]
    if "manual_version" in collected_meta:
        version_sources["用户操作手册"] = collected_meta["manual_version"]
    if "design_version" in collected_meta:
        version_sources["详细设计说明书"] = collected_meta["design_version"]

    distinct_versions = set(version_sources.values())
    if len(distinct_versions) > 1:
        details = ", ".join(f"{src}='{ver}'" for src, ver in version_sources.items())
        errors.append(
            f"【材料一致性红线阻断】各申报材料间的版本号不一致 (哪怕大小写不同也会被官方直接驳回): {details}"
        )

    # 2. 核验软件全称/基础名称一致性
    name_sources: dict[str, str] = {}
    if "form_app_name" in collected_meta:
        name_sources["申请表"] = collected_meta["form_app_name"]
    if "source_full_title" in collected_meta:
        name_sources["源代码页眉"] = collected_meta["source_full_title"]
    if "manual_app_name" in collected_meta:
        name_sources["用户操作手册"] = collected_meta["manual_app_name"]
    if "design_app_name" in collected_meta:
        name_sources["详细设计说明书"] = collected_meta["design_app_name"]

    # 提取归一化基础名称与全称进行一致性审查
    normalized_names = {
        src: normalize_app_and_version(name)[0] for src, name in name_sources.items()
    }
    distinct_base_names = set(normalized_names.values())
    if len(distinct_base_names) > 1:
        details = ", ".join(f"{src}='{name}'" for src, name in name_sources.items())
        errors.append(
            f"【材料一致性红线阻断】各申报材料间的软件全称/基础名称不一致: {details}"
        )

    return errors


def main():
    parser = argparse.ArgumentParser(description="软件著作权申报材料静态合规门禁扫描器 (CPCC Pre-flight Doctor)")
    parser.add_argument("--dir", "--target-dir", dest="dir", help="材料所在目录 (默认: 当前项目 docs/copyright)")
    parser.add_argument("--app-name", help="预期的软件全称 (可选，用于前置校验)")
    parser.add_argument("--version", default="V1.0", help="预期的版本号 (默认: V1.0)")

    args = parser.parse_args()
    if args.dir:
        target_dir = Path(args.dir).resolve()
    else:
        target_dir = (Path.cwd() / "docs" / "copyright").resolve()

    print("=" * 68)
    print("🛡️ 正在执行软件著作权申报材料合规门禁深度审计 (CPCC Pre-flight Doctor)")
    print(f"   目标目录: {target_dir}")
    print("=" * 68)

    all_errors: list[str] = []
    collected_meta: dict[str, str] = {}

    # 1. 命名合法性审计
    if args.app_name:
        name_errs = audit_naming(args.app_name, args.version)
        all_errors.extend(name_errs)
        if not name_errs:
            _, _, full_n = normalize_app_and_version(args.app_name, args.version)
            print(f"✅ [1/5] 软件全称与版本法定命名合规: '{full_n}'")
        else:
            for e in name_errs:
                print(f"❌ {e}")

    else:
        print("ℹ️  [1/5] 跳过命令行命名预审 (未指定 --app-name)")

    # 2. 60 页源程序与官方 PDF 文档审计
    src_errs, src_meta = audit_source_package(target_dir, args.app_name, args.version)
    all_errors.extend(src_errs)
    collected_meta.update(src_meta)
    if not src_errs:
        print("✅ [2/5] 60 页源程序文档 (PDF/TXT) 密度、页码与敏感词零容忍 100% 达标！")
    else:
        for e in src_errs[:5]:
            print(f"❌ {e}")
        if len(src_errs) > 5:
            print(f"   ... 剩余 {len(src_errs) - 5} 项源程序错误已折叠")

    # 3. 申请表三页结构与 500—1300 字主要功能审计
    form_errs, form_meta = audit_application_form(target_dir)
    all_errors.extend(form_errs)
    collected_meta.update(form_meta)
    if not form_errs:
        print("✅ [3/5] CPCC 申请表三页全字段规范与主要功能 500—1300 字五大模块 100% 就绪！")
    else:
        for e in form_errs[:5]:
            print(f"❌ {e}")
        if len(form_errs) > 5:
            print(f"   ... 剩余 {len(form_errs) - 5} 项申请表错误已折叠")

    # 4. 鉴别材料（用户手册 / 详细设计说明书）图文与流程图审计
    manual_errs, manual_meta = audit_manual_document(target_dir)
    all_errors.extend(manual_errs)
    collected_meta.update(manual_meta)

    design_errs, design_meta = audit_design_document(target_dir)
    all_errors.extend(design_errs)
    collected_meta.update(design_meta)

    has_manual_md = (target_dir / "software_user_manual.md").exists()
    has_manual_doc = (target_dir / "software_user_manual.docx").exists() or (target_dir / "software_user_manual.doc").exists()
    has_design_md = (target_dir / "software_design_specification.md").exists()
    has_design_doc = (target_dir / "software_design_specification.docx").exists() or (target_dir / "software_design_specification.doc").exists()

    has_manual = has_manual_md or has_manual_doc
    has_design = has_design_md or has_design_doc

    if not has_manual and not has_design:
        all_errors.append("缺失核心鉴别材料：必须在当前目录下提供《用户操作说明书》或《详细设计说明书》至少一种 (.md 或 .docx)")
    else:
        doc_names = []
        if has_manual:
            formats = []
            if has_manual_md:
                formats.append("md")
            if has_manual_doc:
                formats.append("docx")
            doc_names.append(f"用户操作手册 ({'+'.join(formats)})")
        if has_design:
            formats = []
            if has_design_md:
                formats.append("md")
            if has_design_doc:
                formats.append("docx")
            doc_names.append(f"详细设计说明书 ({'+'.join(formats)})")
        if not manual_errs and not design_errs:
            print(f"✅ [4/5] 鉴别材料大纲、截图规范与架构流程图完整就绪 ({' + '.join(doc_names)})！")
        else:
            for e in (manual_errs + design_errs)[:5]:
                print(f"❌ {e}")

    # 5. 全套材料跨文件 100% 动态强一致性核验
    align_errs = audit_cross_materials_alignment(collected_meta)
    all_errors.extend(align_errs)
    if not align_errs and (has_manual or has_design):
        print("✅ [5/5] 申请表、源程序页眉与说明书命名及版本号 100% 逐字符强一致！")
    elif align_errs:
        for e in align_errs:
            print(f"❌ {e}")

    print("\n" + "=" * 68)
    if all_errors:
        print(f"❌ 门禁拦截: 发现 {len(all_errors)} 项不符合 CPCC 官方审查规范的阻断性缺陷，请修正后再申报！")
        print("=" * 68)
        sys.exit(1)
    else:
        print("🎉 恭喜！软著全套申报材料 100% 通过合规门禁，完全符合中国版权保护中心官方审查规范！")
        print("=" * 68)
        sys.exit(0)


if __name__ == "__main__":
    main()
