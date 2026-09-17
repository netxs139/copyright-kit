# 开发者与贡献指南 (Contributing Guide)

感谢您有兴趣为 Copyright-Kit（软著材料生成套件）贡献代码与规则！本文档旨在为人类开发者提供清晰、精炼的快速入场与协作指引。

---

## ⚠️ 架构底线与零依赖铁律 (Core Architectural Invariants)

Copyright-Kit 定位为开箱即用、可在完全离线或无外网沙箱环境下运行的官方合规套件，必须严格遵守以下工程红线：

1. **绝对零第三方依赖 (Zero-Dependency Mandate)**：
   - 核心引擎与 CLI 代码**仅允许使用 Python 标准库**（如 `zipfile`, `xml.sax.saxutils`, `argparse`, `pathlib`, `re`）；
   - **绝对严禁**引入 `python-docx`、`lxml`、`requests` 等任何第三方依赖包；
2. **纯原生 OpenXML 合成机制**：
   - 所有 `.docx` 文档生成逻辑必须基于轻量级 OpenXML XML 动态组装生成；
3. **CPCC 法定指标刚性对齐**：
   - 必须保持每页 50~55 行有效代码、前 30 + 后 30 共 60 页硬分页标准。

---

## 1. 极速上手 (Quick Start)

### 1.1 环境前置要求
- **Python**: 3.8+ (无需安装任何第三方库)
- **Pytest**: (仅在运行开发测试时需要)

### 1.2 快速启动与验证
```bash
# 1. 克隆仓库
git clone <repo-url> && cd copyright-kit

# 2. 运行单测套件
pytest tests/ -v

# 3. 运行本地命令行测试
python3 src/copyright_kit.py --help
```

---

## 2. 贡献工作流 (Workflow & PR Process)

1. **创建分支**：从 `main` 检出特性分支，命名采用 `feat/<name>` 或 `fix/<name>`；
2. **编写与补齐单元测试**：所有新增功能或缺陷修复必须附带完备的单元测试，保持 100% 绿灯；
3. **提交规范 (Conventional Commits)**：
   - 提交信息强制且仅能使用纯英文（English Only），严禁包含中文字符与全角标点；
   - 示例：`feat(engine): add kotlin source file comment stripper` 或 `fix(docx): resolve xml entity escaping in header`；
   - 本地已通过 `setup_git_hooks.py` 挂载 `pre-commit` 与 `commit-msg` 钩子进行毫秒级物理拦截；
4. **提交 Merge Request (MR)**：
   - 标题遵循全英文 Conventional Commits 格式；
   - 关联对应 Issue，等待自动化 CI 测试通过。

---

## 3. 行为准则 (Code of Conduct)

- 保持专业、友善与建设性沟通；
- 坚持第一性原理与极致轻量化设计，共同守护零依赖高可用工具底座。
