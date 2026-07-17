# Weekly Review Prompt

このリポジトリを正本として、過去の推薦結果を評価してください。

必ず以下を実施してください。

1. `AGENTS.md` の作業開始順に従い、過去情報を読む。
2. 評価対象の推薦を `history/recommendations.csv` から確認する。
3. 推薦翌営業日以降、5営業日、10営業日、20営業日の値動きを最新データで確認する。
4. エントリー到達、仮定約定価格、リターン、MFE、MAE、Target 到達、Stop 到達、先行イベント、結果分類、失敗理由を評価する。
5. 日足データだけで Target と Stop の順序を特定できない場合は、順序不明と記録する。
6. `history/evaluations.csv` に追記する。
7. `reports/reviews/YYYY-MM-DD.md` を作成する。
8. 推薦数、約定数、未約定数、勝率、平均リターン、中央値、平均利益、平均損失、Payoff Ratio、Profit Factor、期待値、最大利益、最大損失、平均MFE、平均MAE、Target到達率、Stop到達率を集計する。
9. ランク別、セクター別、相場環境別、ルールバージョン別の成績を整理する。
10. 改善案が必要な場合は `rules/rule_candidates.md` に追記する。

推薦時点で利用できなかった未来情報を、推薦理由の評価に混入させないでください。
