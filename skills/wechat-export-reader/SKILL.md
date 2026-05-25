---
name: wechat-export-reader
description: Use when the user wants Codex to read, index, summarize, search, or extract tasks from locally exported WeChat/微信 chats, public-account articles, or attachments. This skill only reads user-provided export folders and must not access encrypted WeChat databases or credentials.
---

# WeChat Export Reader

Use this skill for WeChat/微信 material when the user wants a durable local workflow.

## Safety Rule

Only read files the user deliberately placed in an export folder. Do not inspect WeChat's encrypted databases, keychains, app containers, credentials, or live chat windows unless the user explicitly switches to desktop automation for a specific visible action.

## Default Paths

- Default input folder: `/Volumes/T7/AI/微信导出`
- Default index folder: `/Volumes/T7/AI/微信导出/.codex-wechat-index`
- Script: `../../scripts/index_wechat_exports.py`

## Workflow

1. If this is a new task, check the shared Codex memory files required by the workspace.
2. Confirm or infer the export folder. Prefer `/Volumes/T7/AI/微信导出` unless the user gives another path.
3. Run the indexer:

```bash
python3 /Users/htlh/plugins/wechat-export-reader/scripts/index_wechat_exports.py /Volumes/T7/AI/微信导出
```

4. Read the generated files:

- `.codex-wechat-index/index_summary.md`
- `.codex-wechat-index/index.jsonl`

5. Answer from the index and, when needed, read only the relevant original source files.

## Output Expectations

- For search: cite matching file paths and short snippets.
- For summaries: group by conversation/article/file and preserve dates when visible.
- For task extraction: separate `待办`, `联系人/群`, `时间`, `证据片段`, and `建议下一步`.
- For sensitive content: summarize minimally and avoid unnecessary copying of private text.

## Import Tips For The User

微信桌面端不一定能完整批量导出所有聊天。稳定做法是把需要处理的内容主动复制/另存为文本、Markdown、Word、PDF，或把收发文件拖入默认导出目录。公众号文章可以保存为 PDF 或复制为 Markdown/文本。
