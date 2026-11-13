# CI/CD 采用 GitHub Actions，校验以无依赖 Python 脚本承载

本仓库为文档 + 技能包形态的 Git 仓库（GitHub 托管），需要一套能强制执行《治理规范》第八章（校验与合规）的自动化流水线。我们决定以 **GitHub Actions** 为流水线平台，合规校验逻辑以**仅依赖标准库的 Python 脚本**（`scripts/validate_skill.py`、`scripts/check_glossary.py`）承载。

**Considered Options:**
- **GitLab CI / Jenkins / 自建**：需额外基础设施与凭据管理，对本仓库规模而言过重；且与 GitHub PR 生态（模板、Release、branch protection）割裂。
- **Node.js 校验器**：需引入 npm 依赖链，运行时环境更重。
- **GitHub Actions + stdlib Python**（选定）：零外部运行时依赖（`setup-python` 即可），校验脚本可在本地与 CI 一致运行；校验逻辑可被 `tests/` 直接导入测试，形成「流水线自测」闭环。

**Consequences:**
- 校验器可在本地 `python scripts/validate_skill.py` 复现，CI 与本地判定一致（「可校验」）。
- 新增检查仅需新增一个脚本 + 在 `ci.yml` 登记一步，扩展成本低。
- 平台锁定于 GitHub；若日后迁仓，需重写 workflow 层，但校验脚本可整体复用。
