# ai-coding-harness-isucon2026-inspired

> **WIP** — 「要件どおりに作る」と「ISUCON のように速くする」の 2 つのハーネスを 1 リポジトリで回す実験。

## フォルダー

| パス | 役割 |
|---|---|
| `harness/implement/` | 要件どおりに作るハーネス |
| `harness/tune/` | 速くするハーネス（試行ログ `log.md`） |
| `harness/shared/` | 両方で使うゲート |
| `app/` | 対象アプリ（implement が作り、tune が速くする） |
| `specs/` | 要件と受け入れ条件 |
| `tests/acceptance/` | 受け入れテスト（tune では変更禁止） |
| `.claude/` | Claude Code 設定 |

## ブランチ

| 接頭辞 | 用途 |
|---|---|
| `impl/` | 実装作業 |
| `tune/` | 最適化作業（効果がなければブランチごと捨てる） |

## 状態

| 項目 | 状態 |
|---|---|
| フォルダー構成 | ✅ |
| 共通ゲート | 未着手 |
| implement ハーネス | 未着手 |
| tune ハーネス | 未着手 |
| 対象アプリ | 未定 |
