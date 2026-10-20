# 入行 Career Toolkit

[English](README.md) · [统一使用入口](SKILL.md) · [来源与许可](NOTICE.md)

通过 Codex 对话完成“找岗位 → 分析岗位 → 准备简历 → 准备面试 → 比较 Offer → 谈薪”，并用本地文件连接投递、材料归档和复盘。可以从任意阶段开始，已有资料直接复用。本轮采用 Skill + Python 标准库工具 + HTML；没有独立网站、自动投递、邮箱或 Notion 集成。

**当前状态：本地可用版，2026-10-20 收口。** 可用于个人真实求职，采用“Codex 辅助、关键事实由用户确认”的方式。六阶段与投递闭环已完成本地模拟演练和独立复核；不再扩展本轮功能。本版按用户授权同步到 GitHub 项目分支；未创建 PR、部署网站或发布 Release。此结论不代表全自动运行或真实求职结果已验证。

## 开始使用

在当前项目的 Codex 对话中说：**“请读取 SKILL.md，使用求职工具包。”** 然后说明当前需求，例如：

第一次用于真实求职，可以直接说：**“请读取 SKILL.md，使用求职工具包。真实资料使用项目内 `.career-data/personal/`，不要读取模拟演练资料。先根据我提供的简历和一个目标 JD 开始；投递和结果由我明确确认。”** Codex 后续工具操作沿用同一数据目录，以申请 ID 关联资料。这里只约定使用方式，不自动创建个人资料或申请记录。

| 你要做什么 | 可直接说的话 | 执行模块 |
|---|---|---|
| 找岗位 | 根据我的简历找 AI 产品设计岗位，只保留有来源的结果 | job-hunt-skill |
| 分析岗位 | 这份 JD 适合我吗？有哪些证据和缺口？ | job-description-skill |
| 准备简历 | 用已确认的经历，针对这个岗位做打印版和可编辑版简历 | resume-skill |
| 准备面试 | 按这次申请实际提交的简历准备面试 | bq-skill |
| 比较 Offer | 按现金、风险和成长比较这两份 Offer | offer-compare-skill |
| 谈薪 | 根据已确认条件给我谈薪话术和停止条件 | salary-negotiation-skill |
| 管理进度 | 建草稿；我确认已经投递后再登记并归档 | application-tracker-skill |

整包使用，保持目录结构。六个子模块需要共享的 `references/local-workspace.md`；不要只复制一个目录后期待入行适配继续生效。其他宿主可以读取这些 Markdown，但自动发现、工具调用与完整流程需要在对应宿主另行验证。本次不改全局 Skill 安装。

## 资料与真实性

默认存到项目内 `.career-data/`，该目录整体被 Git 忽略；也可指定项目外本地目录。个人资料、JD、故事、Offer、谈薪记录都按[统一规则](references/local-workspace.md)保存。工具目录只含规则、模板和上游示例。示例不属于用户经历；匹配判断不是招聘方结论。外部网页打不开时接受粘贴 JD，注明用户提供和未独立核验，不编造岗位、经历或薪酬。

入行365不接收材料。对话中的材料仍会由当前 Agent、模型及服务商处理，请按其隐私政策决定提供范围。

简历保留 12 个当前模板与旧版 Tech Compact，共 13 个。生成打印 HTML 和浏览器编辑 HTML；编辑版刷新会丢失改动，修改后使用打印存 PDF，并同步重要事实回结构化资料。旧 HTML/PDF 不会被批量重写。

## 投递闭环

材料生成只创建草稿。用户明确报告投递后才标记“已投递”，同时复制实际 JD、简历和可选求职信为不可变快照；缺失材料会如实显示。补投形成新快照。面试优先读已提交版本，当前简历改稿不影响历史。

状态包含草稿、已投递、面试、收到 Offer、已接受、被拒绝、无回复、拒绝 Offer、主动撤回。无回复与拒绝分开；统计依据真实阶段历史，不把草稿计入投递，也不由 Offer 倒推之前一定有面试。同岗位再次申请需明确新建，旧记录保留。

工具需 Python 3.10+，无第三方运行依赖。以下命令从项目根目录运行；写入参数详见[投递模块](application-tracker-skill/SKILL.md)。每次写入先读取 revision，传入 `--expected-revision` 和稳定 `--request-id`，相同操作重试去重，旧 revision 拒绝写入。状态写入必须包含用户确认依据和发生日期。

```sh
python3 application-tracker-skill/scripts/tracker.py read
python3 application-tracker-skill/scripts/tracker.py report
python3 application-tracker-skill/scripts/tracker.py verify
python3 tools/migrate_legacy.py --dry-run
```

报告生成在 `.career-data/reports/applications.html`，直接用浏览器打开可搜索、筛选、查看历史和材料链接。新进展需重新生成报告。迁移去掉 `--dry-run` 才会复制校验旧资料，不删除源文件，不覆盖冲突文件，不导入原样上游示例；原目录仍可只读检索。写入失败保留旧记录；锁冲突需要核对其他进程和现场，不自动清锁。

## 上游升级

`upstreams.lock.json` 记录固定提交、引入路径、上游原始 SHA-256/Git blob、本地安装校验值和适配范围。Offer Toolkit 保留 Git upstream 关系，基线 `f66c4b75dd68da409197ffc06c9807209037ce41`；ai-job-search 仅引用 v1.7.3 `84808eebc13fa7b781b2ede034120c092776668d` 的少量命令与材料文档，不覆盖根 Agent 配置。

```sh
python3 tools/check_upstreams.py --verify-local
python3 tools/check_upstreams.py
```

在线检查使用已配置的 `gh`，对比上游候选提交与固定版本及本地文件，只报告新增、修改、删除、冲突和适配检查范围，不 fetch/merge 或改文件。改名按删除+新增呈现。可用 `--offer-ref`、`--job-ref` 指定候选版本。网络失败返回 `complete:false` 和非零退出码，不能当作“没有更新”。

后续按模块人工适配，验证旧资料和实际流程后再更新锁定版本。来源追踪有助于兼容升级，不能保证未来上游改动自动兼容。没有定时更新任务。

## 本地验收

```sh
python3 -m unittest discover -s tests -v
```

截至 2026-10-20，实际通过的验收如下；证据来自当前 Codex 执行与独立文件、页面核对，不只依据子代理声明。

| 验收 | 结果 |
|---|---|
| 数据与升级工具 | 30 项测试通过，覆盖去重、再次申请、确认边界、未知/损坏数据、并发冲突、保存失败、快照、HTML 转义、迁移及上游只读检查 |
| 第一轮六阶段体验 | 33 项浏览器检查及后续补验通过，操作了搜索筛选、双语切换、归档链接、简历编辑、Markdown 下载、PDF 生成及复制失败回退 |
| 子代理独立演练 | 使用全新合成中国产品经理、两个模拟 JD 与两份模拟 Offer，实际执行 44 次 tracker CLI（含读取与校验），六阶段及复盘全部落盘 |
| 资料与记录衔接 | 当前简历改稿后，已提交快照内容和哈希不变；面试读取该提交版本。同 request 重试返回原记录，旧 revision 被拒，同岗位再次申请保留新 ID |
| 状态与漏斗 | 子代理演练最终为 2 个 Offer、1 个再次申请草稿；历史到达投递 2、面试 1、Offer 2、接受 0。未补造另一家的面试，也未因生成谈薪方案自动接受 |
| 来源与隔离 | 145 个引入文件的原始校验值、2 个旧模板相关文件已核对；只读在线检查未改写源码。验收资料被 Git 忽略，收口前本地来源和提交快照复核正常 |

现有本地成果入口（均被 Git 忽略，新克隆不包含这些文件）：

- [第一轮六阶段验收](.career-data/acceptance/index.html)，对应 [验收结果与限制](.career-data/acceptance/verification.json)。该轮使用合成候选资料、公开 JD 样本和模拟结果。
- [子代理独立求职演练](.career-data/subagent-flow-20261020/index.html)，对应 [逐步过程与发现](.career-data/subagent-flow-20261020/walkthrough.md)、[实际命令与返回](.career-data/subagent-flow-20261020/commands/execution-log.json)及[主代理独立复核](.career-data/subagent-flow-20261020/review/independent-check.json)。该轮人物、岗位、Offer 与反馈全部合成，没有公开搜索。

复用链为：固定画像与岗位清单 → 选定 JD 分析 → 定向简历 → 用户确认投递后保存快照 → 面试读取提交版本并记录反馈 → Offer 条款与个人偏好比较 → 谈薪草稿与复盘。最终文件清单的哈希只代表最终版本；历史时点以各次读回、提交快照和 CLI 日志为准。模拟演练不能证明真实投递、谈薪或求职成功。

## 本地使用边界与剩余限制

- **资料隔离与确认：**真实资料使用独立数据根，不能把上游示例或两轮演练内容当作用户经历。投递、面试、Offer、接受等状态必须有用户明确报告；报告生成不是状态依据。
- **Offer 关联仍需明确处理：**工具允许先记录用户报告的 Offer 状态，不强制检查条款文件是否存在或是否关联正确申请。本轮曾先记状态、后补条款，已追加来源说明并保留原历史。实际使用应先保存完整条款，核对申请 ID，再比较和谈薪；若来源未齐，明确标缺失，不倒填成早已存在。
- **报告仍需内容核对：**子代理初版评分偏离既有 rubric，模板页脚还出现未使用的来源声明及说明文字；本次成果已纠正并复核，但未增加保证每次生成正确的自动门禁。对外使用前核对个人事实、数字、评分依据、来源与薪资条件；没有校准数据不估计拿面概率。
- **衔接由 Agent 执行：**画像、JD、故事、Offer、谈薪材料之间的关联需要 Codex 读取文件组织；tracker 只负责记录、快照与看板。浏览器编辑简历不自动同步回结构化资料，记录变更后看板也需要重新生成。
- **尚未验证的范围：**其他宿主自动发现和完整运行、真实招聘与薪酬结果、所有 PDF 阅读器或 ATS 兼容性。本轮子代理未测试公开搜索；第一轮仅覆盖一个雇主公开源的两个岗位，受限访问回退为模拟验证。未来上游更新仍需按模块适配和验收。

当前按上述边界投入个人使用即可，不因这些限制继续扩建本轮功能；对外投递、发送、提交或发布仍按实际动作另行获得授权。

## 致谢

六阶段方法与模板来自 Dreameryanyan / yanliudesign 的 [Offer Toolkit](https://github.com/yanliudesign/offer-toolkit-skill)；投递管理方法参考 Mads Lorentzen 的 [ai-job-search](https://github.com/MadsLorentzen/ai-job-search)。两方 MIT 许可证与完整署名见 [NOTICE.md](NOTICE.md)。
