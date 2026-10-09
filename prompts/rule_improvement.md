# Rule Improvement Prompt

## 2026-10-09改訂・優先手順

EP-1と比較検証プロトコルを必ず読み、以下を旧記述より優先する。

- 新しい結果は `plans.csv` / `trade_results.csv` / `mark_returns.csv` / `portfolio_daily.csv` へ記録する。旧evaluations/weekly_performanceへ新方式の行を追記しない。
- 寄り付き前・引け後の実行制約、資金・単元・同時注文リスク、注文機能、費用を確認する。私的条件は公開しない。
- 全一次確認を `universe.csv` へ記録し、元価格・調整係数・取得時刻とハッシュを保存する。
- 全推薦の評価期限と欠損理由を照合する。CSVと推薦文書の価格不一致は公開前に直す。
- 成績は同一戦略・プロトコル・コスト・期間の検証済み確定分のみ。仮想と実約定を混ぜない。
- EXP-2026-10-09の比較群と作業時間を同時に記録する。設定・市場データ未確定なら開始済みと書かない。
- 重要な数値訂正は直ちに監査履歴へ追記。戦略優位性の採用は最低標本に加え比較検証が必要。
- `scripts/research_checks.py`、単体テスト、サイト生成・検証を通してから差分確認・コミット・通常pushを行う。

このリポジトリを正本として、選定ルールの改善可否を検討してください。

必ず以下を実施してください。

1. `AGENTS.md` の作業開始順に従い、過去情報を読む。
2. `history/evaluations.csv`、`history/weekly_performance.csv`、`reports/reviews/`、`rules/rule_candidates.md` を確認する。
3. 改善候補ごとに、対象データ、サンプル数、検証期間、Profit Factor、期待値、最大ドローダウン、セクター偏り、相場環境偏りを確認する。
4. 原則として、最低20件の約定データと4週間以上の検証がない案は採用しない。
5. 採用条件を満たす場合のみ `rules/current_rules.md` のバージョンを上げて更新する。
6. 採用理由を `rules/improvement_history.md` に追記する。
7. 棄却する案は `rules/rejected_rules.md` に記録する。
8. Git の状態を確認し、必要に応じてコミットする。通常pushはAGENTS.mdの継続許可に従う。

1週間だけの結果、特定1銘柄だけの結果、特定1セクターだけの結果で恒久ルールを変更しないでください。
