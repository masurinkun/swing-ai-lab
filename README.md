# swing-ai-lab

日本株の「自己改善型スイングトレード分析プロジェクト」として運用するリポジトリです。目的は、1〜3週間程度のスイングトレード候補を毎週選定し、その後の結果を検証し、選定ルールを継続的に改善することです。

このリポジトリはチャット履歴ではなく、運用の正本です。Codex は毎回、過去の推薦履歴、評価、反省、現行ルールを読み込んでから作業します。

## このプロジェクトでやること

- 最新の日本株市場を調査する。
- テクニカル、ファンダメンタル、需給、材料、地合いを分析する。
- スイング候補を最大5銘柄まで選定する。
- 各銘柄の売買プランを Markdown と CSV に保存する。
- 後日、推薦結果を検証する。
- 勝率、値幅、MFE、MAE、Profit Factor、期待値を集計する。
- 成功理由、失敗理由、ルール改善案を記録する。
- 十分な検証後に選定ルールを更新する。

## このプロジェクトでやらないこと

- アプリや Web サービスの開発。
- 自動売買。
- 証券口座への接続。
- 注文執行。
- API サーバー、Web 画面、データベースの作成。

## Codex の役割

Codex は分析補助者として、調査、候補選定、記録、評価、改善案作成、ルール更新、Git 記録を行います。投資助言や売買指示ではありません。最終的な投資判断は利用者が行います。

## フォルダ構成

```text
.
├── AGENTS.md
├── README.md
├── rules/
│   ├── current_rules.md
│   ├── rule_candidates.md
│   ├── improvement_history.md
│   └── rejected_rules.md
├── history/
│   ├── recommendations.csv
│   ├── evaluations.csv
│   ├── weekly_performance.csv
│   └── market_environment.csv
├── reports/
│   ├── screening/
│   ├── reviews/
│   ├── monthly/
│   └── experiments/
├── prompts/
│   ├── weekly_screening.md
│   ├── weekly_review.md
│   └── rule_improvement.md
└── archive/
```

## 毎週の運用フロー

1. `AGENTS.md` に従い、過去情報と現行ルールを読む。
2. 最新の株価、市場環境、決算、材料、需給、外部環境を調査する。
3. 現行ルールに基づき、最大5銘柄まで候補を選ぶ。
4. 候補が弱い場合は、無理に5銘柄を出さず、0〜4銘柄にする。
5. `reports/screening/YYYY-MM-DD.md` に選定レポートを保存する。
6. `history/recommendations.csv` に推薦履歴を追記する。
7. 後日、推薦結果を評価し、`history/evaluations.csv` と `reports/reviews/YYYY-MM-DD.md` に保存する。
8. 十分な検証後、改善案をルールへ反映する。

## 推薦結果の評価方法

評価対象は推薦翌営業日以降の 5営業日、10営業日、20営業日です。以下を確認します。

- エントリー価格帯へ到達したか。
- 約定したと仮定できるか。
- 約定価格。
- 5営業日後、10営業日後、20営業日後のリターン。
- 期間中最大上昇率 MFE。
- 期間中最大下落率 MAE。
- Target 1、Target 2、Stop の到達有無。
- Target と Stop のどちらが先だったか。
- 勝ち、負け、未約定の分類。
- 想定シナリオが崩れた原因。

日足データだけでは同日中の順序を特定できない場合、順序不明として記録します。

## 自己改善の仕組み

自己改善とは、モデル自体が学習することではありません。推薦結果を集計し、選定ルール、評価基準、見送り条件、リスク管理条件をファイル上で更新することです。

改善案は `rules/rule_candidates.md` に記録します。原則として、最低20件の約定データ、4週間以上の検証、Profit Factor と期待値の改善または維持、最大ドローダウンの確認を経てから採用します。採用時は `rules/current_rules.md` のバージョンを上げ、`rules/improvement_history.md` に理由を残します。

## Git を使用する理由

Git は、推薦、評価、ルール変更、改善履歴を後から検証できるようにするために使用します。いつ、どのルールで、どのような判断をしたかを追跡できることが、このプロジェクトの品質管理に必要です。

## CSV の役割

- `history/recommendations.csv`: 毎週の推薦銘柄と売買プランを1銘柄1行で記録する。
- `history/evaluations.csv`: 推薦後の値動き、MFE、MAE、Target/Stop 到達、結果分類を記録する。
- `history/weekly_performance.csv`: 週次レビュー単位の集計結果を記録する。
- `history/market_environment.csv`: 推薦週や評価週の市場環境を記録する。

## レポートの役割

- `reports/screening/`: 毎週の選定レポート。
- `reports/reviews/`: 推薦結果の週次レビュー。
- `reports/monthly/`: 月次の成績集計、傾向分析、改善テーマ。
- `reports/experiments/`: 初期構築、検証実験、分析メモ。

## 注意事項と免責

- 本プロジェクトは投資助言ではなく、分析補助と記録管理を目的とします。
- 株価、決算、適時開示、信用需給などは、作業時点で最新情報を確認します。
- データが取得できない場合は推測せず、不明と記録します。
- 推薦時点で利用できない未来情報は使いません。
- 実売買、自動売買、注文執行は行いません。
