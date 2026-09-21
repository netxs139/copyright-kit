# 📜 Copyright-Kit (全自动软件著作权申报材料生成套件)

> **面向中国版权保护中心 (CPCC) 官方审查规范的自包含、零依赖、专业的软著材料自动化提取与合规门禁工具。**  
> 无论是作为 **AI Agent Skill**（智能体技能）融入日常研发对话，还是作为 **独立 CLI 命令行** 运行于本地终端与 CI/CD 流水线，均可实现 **60 秒一键交付** 100% 合规的软著申报材料包！

[![CI](https://github.com/netxs139/copyright-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/netxs139/copyright-kit/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dependencies](https://img.shields.io/badge/dependencies-0%20(Standard%20Library)-brightgreen.svg)]()
[![CPCC Standard](https://img.shields.io/badge/CPCC-100%25%20Compliant-success.svg)]()

> 📖 **快速导航**: [贡献指南 (CONTRIBUTING.md)](./CONTRIBUTING.md) | [Skill 智能体集成指南](SKILL.md)

---

## 💡 为什么需要它？

申报《计算机软件著作权登记证书》是中国境内软件发布、高企认定、企业合规以及主流应用商店（华为、小米、OPPO、vivo、App Store 等）上架提审的法定前置要件。

而传统的申报材料准备过程繁琐且极易踩坑被打回：

| 维度 | 传统手工准备痛点 | Copyright-Kit 自动化解决方案 |
| :--- | :--- | :--- |
| **源码排版** | 手动拷贝分散源码、手动调 Word 页边距与分页符，耗时数小时 | **纯标准库零依赖直出官方标准 UTF-8 PDF 原生文档**，同时伴生交付 `.docx` 与 `.txt` |
| **行数指标** | 人工删减空行，易因每页不足 50 行被审查员直接驳回（延误 30 天） | **严格法定硬指标防护**：每页实打实 50~55 行有效代码，前 30 + 后 30 共 60 页 |
| **敏感词审查** | 代码中残留 `TODO` / `FIXME` 会被判定为“未开发完成”而拒绝登记 | **全语种智能截断脱敏**：保留代码主体，自动截断行尾 TODO 与剥离第三方商业版权头 |
| **申请表填写** | 官方三页结构字段易遗漏，主要功能字数不足或结构不全被驳回 | **官方三页标准结构填报卡**：自动回填真实 SLOC，内置 500—1300 字五大核心板块模板 |
| **鉴别材料** | 缺少详细设计或操作手册截图无文字说明，图文软件名与版本号漂移 | **双轨鉴别材料模板**：内置用户手册截图规范与详细设计说明书全套架构/模块 Mermaid 流程图 |
| **合规把关** | 材料递交后漫长等待，因命名大小写不一致（V1.0 vs v1.0）收到补正 | **内置 CPCC Pre-flight Doctor**：一键预审，跨材料 100% 逐字符动态强一致性核验 |

---

## 🏗️ 处理流水线架构 (Pipeline)

```mermaid
flowchart LR
    A[项目多端源码<br/>src / apps / lib] --> B[智能感知推断<br/>名称/版本/目录]
    B --> C[全语种脱敏截断<br/>TODO/FIXME/版权头]
    C --> D[有效源码量 SLOC 统计<br/>千分位双向回填]
    D --> E1[纯标准库 PDF 渲染引擎<br/>A4/2cm边距/STSong-Light]
    D --> E2[原生 OpenXML 动态组装<br/>Consolas/Word 排版]
    E1 --> F1[📕 source_code_60pages.pdf<br/>官方标准 UTF-8 PDF]
    E2 --> F2[📄 source_code_60pages.docx<br/>原生 Word 排版]
    D --> F3[📝 source_code_60pages.txt<br/>标准 \\f 硬分页]
    D --> F4[📋 cpcc_form_fields.md<br/>三页全字段卡 + 500-1300字]
    D --> F5[📖 software_user_manual.md / .docx<br/>用户操作手册 (md+Word版)]
    D --> F6[📐 software_design_specification.md / .docx<br/>详细设计说明书 (md+Word版)]
    F1 & F2 & F3 & F4 & F5 & F6 --> G[🩺 CPCC Pre-flight Doctor<br/>合规门禁 100% 预审]
```

---

## 🌟 核心特性 (Key Features)

- 🚀 **100% 零第三方依赖 (Zero-Dependency)**：
  - 核心引擎完全基于 Python 3.8+ 标准库实现；
  - **无需安装任何第三方库**（如 `reportlab`, `python-docx` 等），全平台（Linux / macOS / Windows / 无外网沙箱环境）离线开箱即用。
- 📕 **纯标准库原生官方标准 PDF 直出**：
  - 采用轻量级原生 PDF 矢量构建引擎，零依赖一键生成符合官方规格的标准 PDF 文档；
  - 内置标准 A4 页面、上下左右严格 2.0cm 页边距、UTF-8 / CJK 矢量字体支持，彻底告别乱码与格式错位；
  - 自动生成两端对齐页眉（左侧为 `软件全称 + 版本号`，右侧为 `第 X 页`，下方矢量细横线）；
  - 每页实打实 55 行有效代码，完全满足官方“必须是 PDF、不能是 Word、不能有乱码/图片/截图”的严苛要求。
- 📄 **原生 Word (.docx) 与纯文本 (.txt) 同步伴生交付**：
  - 满足多端审阅与归档需求，支持灵活二次排版。
- 📘 **说明书与详细设计说明书原生 Word (.docx / doc版) 双轨直出**：
  - 内置纯标准库 Markdown 到原生 OpenXML 转换引擎，一键直出 A4 专业排版 Word 文档；
  - 自动渲染封面信息卡、多级标题、引用警示框、Mermaid/代码块、专业数据表格；
  - 专为 CPCC 审查指标定制「界面全景与操作截图占位框」，用户可在 Word/WPS 中直接粘贴真实界面截图后「另存为 PDF」；
  - 自动生成两端对齐页眉与动态页码页脚（第 PAGE 页 共 NUMPAGES 页）。
- 📋 **官方三页标准申请表填报卡与 500—1300 字核心功能模板**：
  - 严格按照官方申请表第一页（申请信息）、第二页（开发信息）、第三页（功能与特点）分层组织；
  - 补全原创、独立开发、开发目的、面向领域、技术特点等全要素；
  - 提供规范的 **500—1300 字** 主要功能描述模板，完整覆盖 **「研发背景」、「核心架构」、「功能模块」、「技术实现」、「应用场景」** 五大板块。
- 📐 **《用户操作说明书》与《详细设计说明书》双轨模板体系**：
  - 用户手册：包含主界面全景截图规范、每个主要操作截图步骤说明及软件名称版本号一致性约束；
  - 详细设计说明书：包含系统概述、分层技术架构、业务流转总流程图与各模块详细流程图（标准 Mermaid 格式）。
- 📊 **全项目真实 SLOC 精确统计与自动双向回填**：
  - 自动递归扫描过滤后的全部生产代码，排除注释、空行、测试代码与构建产物，精准计算项目实际有效源码行数（SLOC）；
  - 自动检测并同步更新申请表中的 `| **源程序量（行）** |` 字段（如 `56,783`），告别手工估算。
- 🧹 **全语种待办注释与敏感词深度截断脱敏 (Deep Sanitization)**：
  - **截断而非整行抹除**：智能识别行尾注释，保留核心有效逻辑（如 `return result # TODO: opt` 清洗为 `return result`）；
  - 全面支持 Python, TypeScript, Vue, JavaScript, Go, Rust, Java, C/C++, SQL, HTML, CSS 等主流语言；
  - 深度剥离外源商业版权声明（如 `Copyright (c) ... Facebook/Google/MIT`），保障申报主体 100% 独立知识产权。
- 🩺 **CPCC Pre-flight Doctor 门禁扫描器 (5 大维度全覆盖)**：
  - 1. 软件全称法定命名后缀与大写 V 版本号合规性；
  - 2. 60 页源程序 PDF / TXT 密度硬指标（$\ge 50$ 行）与敏感词零容忍；
  - 3. 申请表三页结构与主要功能 500—1300 字深度审计；
  - 4. 鉴别材料大纲与截图/流程图规范把关；
  - 5. **跨材料 100% 逐字符动态强一致性核验**：申请表、源码页眉、说明书、详细设计说明书中的软件全称与版本号严格一致（哪怕大小写 `V1.0` vs `v1.0` 亦立即拦截）。

---

## ⚖️ 申报主体选择决策指南 (个人 vs 企业)

在正式申报前，请根据商业化规划决策申报主体性质：

| 决策维度 | 选项 A：【个人（自然人）】申报 | 选项 B：【公司（企业法人）】申报 (推荐用于商用App) |
| :--- | :--- | :--- |
| **所需资质** | 仅需**个人身份证正反面彩色扫描件** | 需**营业执照副本彩色扫描件**、**企业公章**、法人身份证 |
| **签章流程** | **免公章**，申请表签章页仅需个人手写签字 | 申请表签章页必须**加盖公章并由法人签字** |
| **应用市场上架** | **严重受限 ❌**（华为/小米/OPPO等各大应用商店均已限制个人开发者提交收支/记账/工具类App） | **一路绿灯 ✔**（企业开发者账号上架无阻碍，软著权属与上架主体一致） |
| **资产与高企** | 属于个人私产；如需注入公司需走繁琐的软著转让变更（耗时1~2个月） | 计入公司无形资产，可直接用于高新技术企业认定与税收优惠 |
| **保护期限** | 作者终生及死后 50 年 | 软件开发完成之日起 50 年 |

---

## 📦 目录结构 (Self-Contained Architecture)

```text
copyright-kit/
├── .github/workflows/ci.yml          # GitHub Actions 跨平台持续集成
├── SKILL.md                          # AI Agent 自动化申报技能规约 (供智能体读取)
├── README.md                         # 开发者手册与命令行指南 (本文档)
├── LICENSE                           # MIT 开源许可证
├── pyproject.toml                    # 标准 PEP 621 打包配置与 CLI 入口声明
├── scripts/                          # 核心脚本引擎 (纯标准库，零依赖)
│   ├── export_copyright_source.py   # 60 页源程序提取、PDF/docx/txt 渲染与行数同步引擎
│   ├── export_document_docx.py      # 说明书与设计说明书原生 Word (.docx) 排版渲染引擎
│   ├── audit_copyright_package.py   # CPCC 合规门禁 Pre-flight Doctor 扫描器 (5大维度)
│   └── verify_compliance.py         # 商业与内部敏感信息开源合规审计工具
├── templates/                        # 官方申报标准化模板
│   ├── cpcc_form_fields.md          # CPCC 申请表官方三页标准填报卡 (含 500-1300 字模板)
│   ├── user_manual_template.md      # 7 大标准章节《用户操作说明书》图文骨架 (含截图合规指标)
│   └── design_specification_template.md # 《详细设计说明书》模板 (含总体架构与模块流程图)
└── tests/
    ├── test_compliance.py           # 6 项合规测试
    └── test_copyright_kit.py        # 17 项全要素自动化测试 (PDF/申请表/Word说明书/跨文件一致性)
```

---

## 🛠️ 安装与使用方式 (Installation & Setup)

### 方式一：使用 uvx / pipx 免安装一键运行 (极速推荐)

```bash
# 一键抽取 60 页 PDF/docx/txt 源码
uvx --from git+https://github.com/netxs139/copyright-kit.git copyright-kit --app-name "某某管理软件 V1.0"

# 一键导出用户手册与详细设计说明书 Word (.docx) 版
uvx --from git+https://github.com/netxs139/copyright-kit.git export-doc --all --app-name "某某管理软件 V1.0"

# 门禁合规审计
uvx --from git+https://github.com/netxs139/copyright-kit.git audit-copyright --dir docs/copyright
```

### 方式二：作为 AI Agent 技能接入

支持将本套件作为 Skill 挂载至任何具备智能体能力的 IDE（如 Antigravity IDE, Claude Code, Cursor, Windsurf 等）：
- 直接在对话框中输入：`帮我准备这个项目的软件著作权材料` 或 `/copyright-kit`。

### 方式三：作为独立 CLI 命令行使用 (克隆即用)

```bash
git clone https://github.com/netxs139/copyright-kit.git
```

---

## 🚀 命令行快速上手 (CLI Quick Start)

### 步骤 1：一键抽取 60 页合规源程序 (直出 PDF/DOCX/TXT)

```bash
python3 scripts/export_copyright_source.py \
  --src-dir src/ apps/ \
  --app-name "SeedFlow家庭资产数字化记账软件 V1.0" \
  --version "V1.0" \
  --lines-per-page 55 \
  --pages 60
```

**控制台实际输出示例**：
```text
====================================================================
📄 正在抽取软件著作权源程序文档: SeedFlow家庭资产数字化记账软件 V1.0
   基础名称: SeedFlow家庭资产数字化记账软件 | 规范版本号: V1.0
   扫描目录: /workspace/my-project/src
   目标规格: 每页 55 行，共 60 页 (前 30 + 后 30)
====================================================================
🔍 扫描到清洗后有效代码行数: 48,260 行
✅ 成功导出标准软著源程序纯文本: docs/copyright/source_code_60pages.txt
   总格式化行数: 3539 行 (包含页眉与分隔线)
📕 成功导出官方标准 UTF-8 PDF 文档: docs/copyright/source_code_60pages.pdf (A4 / 2cm 边距 / 矢量等宽代码)
📄 成功导出原生 Word 排版文档: docs/copyright/source_code_60pages.docx (内置 A4 / 2cm 边距 / Consolas 等宽字体)
📊 已将真实源程序量 (48,260 行) 自动同步至申报填报卡: docs/copyright/cpcc_application_info.md
====================================================================
```

---

### 步骤 2：一键导出鉴别材料 Word (.docx / doc版)

```bash
python3 scripts/export_document_docx.py \
  --all \
  --dir docs/copyright \
  --app-name "SeedFlow家庭资产数字化记账软件 V1.0" \
  --version "V1.0"
```

**控制台实际输出示例**：
```text
====================================================================
📄 正在生成软件著作权鉴别材料 Word (.docx) 版...
   软件全称: SeedFlow家庭资产数字化记账软件 V1.0 | 版本号: V1.0
✅ 成功一键导出 2 个 Word 排版说明书文档:
   - docs/copyright/software_user_manual.docx
   - docs/copyright/software_design_specification.docx
====================================================================
```

> **提示**：生成的 Word 文档内置标准封面信息卡、章节编号样式、截图指示虚线框与两端对齐页眉。用户可在 Word/WPS 中直接粘贴截图，完成后直接「另存为 PDF」即可向 CPCC 提报。

---

### 步骤 3：运行 CPCC 合规门禁审查 (Pre-flight Doctor)

在正式向中国版权保护中心提交前，运行静态门禁扫描器（支持 .md 与 .docx 双模智能审查）：

```bash
python3 scripts/audit_copyright_package.py \
  --dir docs/copyright \
  --app-name "SeedFlow家庭资产数字化记账软件 V1.0" \
  --version "V1.0"
```

**审计结果**：
```text
====================================================================
🛡️ 正在执行软件著作权申报材料合规门禁深度审计 (CPCC Pre-flight Doctor)
   目标目录: .../docs/copyright
====================================================================
✅ [1/5] 软件全称与版本法定命名合规: 'SeedFlow家庭资产数字化记账软件 V1.0'
✅ [2/5] 60 页源程序文档 (PDF/TXT) 密度、页码与敏感词零容忍 100% 达标！
✅ [3/5] CPCC 申请表三页全字段规范与主要功能 500—1300 字五大模块 100% 就绪！
✅ [4/5] 鉴别材料大纲、截图规范与架构流程图完整就绪 (用户操作手册 (md+docx) + 详细设计说明书 (md+docx))！
✅ [5/5] 申请表、源程序页眉与说明书命名及版本号 100% 逐字符强一致！
====================================================================
🎉 恭喜！软著全套申报材料 100% 通过合规门禁，完全符合中国版权保护中心官方审查规范！
====================================================================
```

---

## 🧪 自动化测试与验证

套件内置自包含轻量级自动化测试套件，克隆本仓库后即可直接验证：

```bash
pytest tests/test_copyright_kit.py -v
```

---

## 📄 开源许可证 (License)

本项目遵循 [MIT License](LICENSE) 开源协议。欢迎提交 PR 与 Issue！
