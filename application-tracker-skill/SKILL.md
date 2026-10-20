---
name: application-tracker-skill
description: "记录求职申请、已提交材料、面试阶段和结果，生成本地进展看板与复盘。用于用户明确要求记录/查看进展；不代投、不发跟进消息。"
---

# 投递管理与复盘

先读 [本地资料规则](../references/local-workspace.md)。使用本目录 `scripts/tracker.py` 操作记录，不直接重写 JSON。输入内容保存到数据根目录内的临时 JSON 文件，不在命令行拼接个人材料。

## 最短操作流程

1. `python3 <脚本绝对路径> read --data-dir <数据根>`，取得 `revision` 和已有申请 ID。没有文件返回 revision 0，纯读取不创建目录。
2. 明确用户要创建申请、更新状态、追加反馈还是查看报告。按下表构造输入，保留事实依据。
3. 写操作使用：`python3 <脚本> <操作> --data-dir <数据根> --input <输入文件> --expected-revision <刚读到的版本> --request-id <本次操作UUID>`。
4. 读回核对。未知结果重用相同 request-id 和内容，不换号盲重试。冲突重新读回并判断，不能覆盖较新版本。
5. 需要查看进展时运行 `report` 并在浏览器打开返回的 HTML。报告是生成时的快照，修改记录后重新生成。

| 操作 | 输入字段 |
|---|---|
| `create` | 必填 `company`、`role`；可选 `source_url`、`note`、`materials`。同公司岗位的新一轮申请必须明确 `new_attempt: true` |
| `draft` | `id`、`materials`，更新当前草稿路径，不改状态或历史快照 |
| `status` | `id`、`status`、`confirmed: true`、`evidence`（用户原话或回执依据）、`occurred_on`（YYYY-MM-DD）；可选 `note`、`materials` |
| `archive` | `id`、`confirmed: true`、`evidence`、`occurred_on`、`materials`，补交或补充准确历史版本，新增快照 |
| `note` | `id`，至少一个 `stage`、`note`、`feedback`（原始反馈）、`suggestion`（分析建议）；不改变状态 |
| `read` / `verify` / `report` | 不需要输入 JSON、request-id 或 revision |

`materials` 是可选键 `jd`、`resume`、`cover_letter` 对应的**绝对文件路径**。只支持用户已确认的本地材料；不下载来源 URL 的附件。`status=applied` 会复制这些文件并记录哈希；未提供或不存在的文件明确记为 missing。

状态词：`drafted`、`applied`、`interview`、`offer`、`hired`、`rejected`、`no_response`、`offer_declined`、`withdrawn`。草稿创建后，用户确认实际投递才进入 applied。接受或拒绝 Offer 前先记录 offer；不同状态需要分别报告其发生日期。已经关闭的申请收到迟到反馈，可在用户明确说明后设置 `reopen: true`，历史仍保留。再次申请则新建 ID。

输入示例（仅结构示意，不可当作用户已确认）：
```json
{"id":"申请UUID","status":"applied","confirmed":true,"evidence":"用户明确报告的已投递事实","occurred_on":"2026-10-20","materials":{"jd":"/绝对路径/jd.md","resume":"/绝对路径/resume.html"}}
```

## 面试和复盘

- 面试先运行 verify；读取选定申请的提交快照和历史反馈，交给 BQ 模块。存在多次提交时让用户的轮次/日期决定用哪个快照，默认使用最近一次已确认提交，并说明版本。
- 继续同一轮面试时用 note 记录轮次和原话；首次进入面试先更新 interview。建议不作为已发生的事件。
- 复盘按“实际反馈 → 与先前判断的差异 → 可验证的下一步”组织，写入 suggestion。单次拒信不证明某项技能不足，无回复不等于拒绝。
- report 分别统计草稿、当前状态和真实到达阶段；不从拿到 Offer 推断一定经过某种面试。没有数据时显示空态，分母为零不计算比率。
- 原工具参考保存在 `../references/upstream/ai-job-search/`，仅供维护溯源；不执行其 Claude 配置、自动同步或清理命令。
