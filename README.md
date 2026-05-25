# WeChat Export Reader

Privacy-first local Codex workflow for WeChat material.

This plugin reads only files the user has deliberately exported or copied into a local folder. It does not decrypt WeChat databases, log in to WeChat, read passwords, or bypass app permissions.

## Default Folders

- Input: `/Volumes/T7/AI/微信导出`
- Output: `/Volumes/T7/AI/微信导出/.codex-wechat-index`

## Typical Use

1. Create `/Volumes/T7/AI/微信导出`.
2. Put exported WeChat chats, copied public-account articles, PDFs, DOCX files, images, and attachments there.
3. Ask Codex: `用 wechat-export-reader 索引我的微信导出目录`.
4. Codex runs `scripts/index_wechat_exports.py` and then reads the generated Markdown/JSONL index.

## Safety Boundary

- Allowed: user-exported `.txt`, `.md`, `.csv`, `.docx`, `.pdf`, images, and other local attachment files.
- Not allowed: reading encrypted WeChat database internals, credential stores, private app containers, or live chats without user action.
