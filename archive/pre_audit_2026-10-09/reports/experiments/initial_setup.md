# Initial Setup

## Date

2026-07-17

## Purpose

日本株の自己改善型スイングトレード分析プロジェクトとして、このリポジトリを運用できる状態に初期化した。

## Created Structure

- `AGENTS.md`
- `README.md`
- `rules/current_rules.md`
- `rules/rule_candidates.md`
- `rules/improvement_history.md`
- `rules/rejected_rules.md`
- `history/recommendations.csv`
- `history/evaluations.csv`
- `history/weekly_performance.csv`
- `history/market_environment.csv`
- `reports/screening/`
- `reports/reviews/`
- `reports/monthly/`
- `reports/experiments/`
- `prompts/weekly_screening.md`
- `prompts/weekly_review.md`
- `prompts/rule_improvement.md`
- `archive/`

## Initial Rules

`rules/current_rules.md` を v0.1.0 として作成した。対象、テクニカル、ファンダメンタル、需給、イベント、リスク管理、スコアリングの初期基準を定義した。

このルールは統計的な裏付けがまだ十分ではない暫定ルールであり、今後の推薦結果と評価結果に基づいて改善する。

## Initial Data

CSV はヘッダーのみを作成した。現時点では推薦、評価、週次成績、市場環境の実データは未登録。

## Operational Notes

- アプリケーションコード、Web サービス、API サーバー、データベースは作成していない。
- 自動売買、証券口座接続、注文執行は行わない。
- 今後の毎週の選定では、最新株価と信頼できる情報源を確認する。
- 推薦時点で利用できない未来情報は使用しない。
