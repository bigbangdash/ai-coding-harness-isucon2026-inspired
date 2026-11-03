# implement — 要件どおりに作るハーネス

```
specs/<機能>/requirements.md, acceptance.md   ← 人間が合意（AI は下書きまで）
        ↓
tests/acceptance/                             ← AI が下書き → 人間が承認
        ↓
app/ を実装 → harness/shared/evaluate.sh
        ├─ FAIL    → 修正して再評価（3 回続いたら critic）
        ├─ BLOCKED → 人間に確認
        └─ PASS    → risk high なら evaluator（design）→ evaluator（final）→ 人間の承認
```

- 作業ブランチ: `impl/<番号>-<名前>`
- 評価基準: `evals/`（設計・実装・業務受入・AI 行動）
