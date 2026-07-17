# Rule Improvement Prompt

このリポジトリを正本として、選定ルールの改善可否を検討してください。

必ず以下を実施してください。

1. `AGENTS.md` の作業開始順に従い、過去情報を読む。
2. `history/evaluations.csv`、`history/weekly_performance.csv`、`reports/reviews/`、`rules/rule_candidates.md` を確認する。
3. 改善候補ごとに、対象データ、サンプル数、検証期間、Profit Factor、期待値、最大ドローダウン、セクター偏り、相場環境偏りを確認する。
4. 原則として、最低20件の約定データと4週間以上の検証がない案は採用しない。
5. 採用条件を満たす場合のみ `rules/current_rules.md` のバージョンを上げて更新する。
6. 採用理由を `rules/improvement_history.md` に追記する。
7. 棄却する案は `rules/rejected_rules.md` に記録する。
8. Git の状態を確認し、必要に応じてコミットする。push は明示依頼がある場合のみ行う。

1週間だけの結果、特定1銘柄だけの結果、特定1セクターだけの結果で恒久ルールを変更しないでください。
