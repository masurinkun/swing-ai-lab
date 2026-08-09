#!/usr/bin/env python3
"""Build the read-only Swing AI Lab report site from canonical Markdown and CSV files."""

from __future__ import annotations

import argparse
import csv
import html
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
SITE_SOURCE = ROOT / "site"
REPORT_GROUPS = (
    ("screening", "銘柄選定", "週次の候補選定と売買計画"),
    ("reviews", "事後評価", "推薦後の値動きと振り返り"),
    ("monthly", "月次レビュー", "成績集計と改善テーマ"),
    ("experiments", "検証記録", "検証実験と分析メモ"),
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip().replace(",", "").replace("%", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def yes(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "はい", "到達", "約定"}


def format_number(value: str | float | None, decimals: int = 0) -> str:
    number = safe_float(str(value)) if value is not None else None
    if number is None:
        return "—"
    if decimals:
        return f"{number:,.{decimals}f}"
    return f"{number:,.0f}"


def format_price(value: str | float | None) -> str:
    number = safe_float(str(value)) if value is not None else None
    if number is None:
        return "—"
    return f"{number:,.1f}" if not number.is_integer() else f"{number:,.0f}"


def format_percent(value: str | float | None) -> str:
    number = safe_float(str(value)) if value is not None else None
    if number is None:
        return "—"
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.2f}%"


def format_date(value: str) -> str:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        year, month, day = value.split("-")
        return f"{year}.{month}.{day}"
    return value or "—"


def format_report_stamp(value: str) -> str:
    return format_date(value) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or "") else "記録"


def slugify(value: str) -> str:
    ascii_slug = re.sub(r"[^a-zA-Z0-9\-\s]", "", value).strip().lower()
    if ascii_slug:
        return re.sub(r"[\s\-]+", "-", ascii_slug)
    return "section"


def inline_markdown(value: str) -> str:
    escaped = html.escape(value, quote=False)
    code_tokens: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        code_tokens.append(f"<code>{match.group(1)}</code>")
        return f"@@CODE{len(code_tokens) - 1}@@"

    escaped = re.sub(r"`([^`]+)`", stash_code, escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        lambda match: (
            f'<a href="{html.escape(html.unescape(match.group(2)), quote=True)}" '
            f'target="_blank" rel="noopener noreferrer">{match.group(1)}</a>'
        ),
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    for index, token in enumerate(code_tokens):
        escaped = escaped.replace(f"@@CODE{index}@@", token)
    return escaped


def is_table_separator(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    paragraph: list[str] = []
    in_code = False
    code_lines: list[str] = []
    list_type: str | None = None
    heading_counts: defaultdict[str, int] = defaultdict(int)
    index = 0

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{inline_markdown(' '.join(part.strip() for part in paragraph))}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            output.append(f"</{list_type}>")
            list_type = None

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            close_list()
            if in_code:
                output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            index += 1
            continue

        if in_code:
            code_lines.append(line)
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1]):
            flush_paragraph()
            close_list()
            headers = table_cells(line)
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(table_cells(lines[index]))
                index += 1
            output.append('<div class="table-scroll"><table><thead><tr>')
            output.extend(f"<th>{inline_markdown(cell)}</th>" for cell in headers)
            output.append("</tr></thead><tbody>")
            for row in rows:
                output.append("<tr>")
                output.extend(f"<td>{inline_markdown(cell)}</td>" for cell in row)
                output.append("</tr>")
            output.append("</tbody></table></div>")
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            base_slug = slugify(text)
            heading_counts[base_slug] += 1
            suffix = f"-{heading_counts[base_slug]}" if heading_counts[base_slug] > 1 else ""
            output.append(
                f'<h{level} id="{base_slug}{suffix}">{inline_markdown(text)}</h{level}>'
            )
            index += 1
            continue

        unordered = re.match(r"^[-*]\s+(.+)$", stripped)
        ordered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if unordered or ordered:
            flush_paragraph()
            requested = "ul" if unordered else "ol"
            if list_type != requested:
                close_list()
                list_type = requested
                output.append(f"<{list_type}>")
            content = (unordered or ordered).group(1)
            output.append(f"<li>{inline_markdown(content)}</li>")
            index += 1
            continue

        if stripped.startswith("> "):
            flush_paragraph()
            close_list()
            output.append(f"<blockquote>{inline_markdown(stripped[2:])}</blockquote>")
            index += 1
            continue

        if stripped in {"---", "***"}:
            flush_paragraph()
            close_list()
            output.append("<hr>")
            index += 1
            continue

        if not stripped:
            flush_paragraph()
            close_list()
        else:
            close_list()
            paragraph.append(stripped)
        index += 1

    flush_paragraph()
    close_list()
    if in_code:
        output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    return "\n".join(output)


def markdown_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        match = re.match(r"^#\s+(.+)$", line.strip())
        if match:
            return match.group(1).strip()
    return fallback


def badge(label: str, tone: str = "neutral") -> str:
    return f'<span class="badge badge--{tone}">{html.escape(label)}</span>'


def result_tone(result: str) -> str:
    normalized = result.strip().lower()
    if normalized in {"win", "勝ち", "利益"}:
        return "positive"
    if normalized in {"loss", "負け", "損失"}:
        return "negative"
    if normalized in {"no_entry", "未約定", "見送り"}:
        return "muted"
    return "pending"


class SiteBuilder:
    def __init__(self, output: Path) -> None:
        self.output = output
        self.recommendations = read_csv(ROOT / "history/recommendations.csv")
        self.evaluations = read_csv(ROOT / "history/evaluations.csv")
        self.weekly = read_csv(ROOT / "history/weekly_performance.csv")
        self.markets = read_csv(ROOT / "history/market_environment.csv")
        self.rule_markdown = read_text(ROOT / "rules/current_rules.md")
        self.improvement_markdown = read_text(ROOT / "rules/improvement_history.md")
        self.candidates_markdown = read_text(ROOT / "rules/rule_candidates.md")
        self.rejected_markdown = read_text(ROOT / "rules/rejected_rules.md")
        self.rule_version = self.extract_rule_version()
        self.generated_at = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y.%m.%d %H:%M JST")
        self.report_index: dict[str, str] = {}

    def extract_rule_version(self) -> str:
        match = re.search(r"^v\d+\.\d+\.\d+", self.rule_markdown, re.MULTILINE)
        return match.group(0) if match else "不明"

    def prepare(self) -> None:
        if self.output.exists():
            shutil.rmtree(self.output)
        self.output.mkdir(parents=True)
        shutil.copytree(SITE_SOURCE / "assets", self.output / "assets")
        (self.output / ".nojekyll").write_text("", encoding="utf-8")

    def prefix(self, depth: int) -> str:
        return "../" * depth if depth else "./"

    def page(
        self,
        path: str,
        *,
        title: str,
        description: str,
        body: str,
        active: str,
        depth: int,
        page_class: str = "",
    ) -> None:
        target = self.output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        prefix = self.prefix(depth)
        nav_items = (
            ("overview", "概要", ""),
            ("recommendations", "推薦銘柄", "recommendations/"),
            ("results", "推薦結果", "results/"),
            ("reports", "レポート", "reports/"),
            ("rules", "ルール・改善", "rules/"),
        )
        nav = "".join(
            f'<a href="{prefix}{href}" class="nav-link{" is-active" if key == active else ""}">{label}</a>'
            for key, label, href in nav_items
        )
        document = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#102c2b">
  <meta name="description" content="{html.escape(description, quote=True)}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{html.escape(title, quote=True)} | Swing AI Lab">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <title>{html.escape(title)} | Swing AI Lab</title>
  <link rel="stylesheet" href="{prefix}assets/styles.css">
  <script src="{prefix}assets/site.js" defer></script>
</head>
<body class="{html.escape(page_class, quote=True)}">
  <a class="skip-link" href="#main">本文へ移動</a>
  <header class="site-header">
    <div class="header-inner">
      <a class="brand" href="{prefix}" aria-label="Swing AI Lab トップ">
        <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span>
        <span><strong>Swing AI Lab</strong><small>日本株スイング分析記録</small></span>
      </a>
      <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">メニュー</button>
      <nav class="site-nav" id="site-nav" aria-label="メインナビゲーション">{nav}</nav>
    </div>
  </header>
  <main id="main">{body}</main>
  <footer class="site-footer">
    <div class="footer-inner">
      <div><strong>Swing AI Lab</strong><p>選定・検証・改善の全記録を、同じ基準で積み上げるための公開台帳。</p></div>
      <div class="footer-note"><p>本サイトは投資助言ではなく分析補助です。売買判断は利用者自身が行ってください。</p><p>サイト生成: {self.generated_at}</p></div>
    </div>
  </footer>
</body>
</html>
"""
        target.write_text(document, encoding="utf-8")

    def evaluation_for(self, recommendation: dict[str, str]) -> dict[str, str] | None:
        for evaluation in self.evaluations:
            if (
                evaluation.get("recommendation_date") == recommendation.get("recommendation_date")
                and evaluation.get("stock_code") == recommendation.get("stock_code")
            ):
                return evaluation
        return None

    def report_url(self, report_file: str, prefix: str) -> str:
        normalized = report_file.strip()
        return f"{prefix}{self.report_index[normalized]}" if normalized in self.report_index else f"{prefix}reports/"

    def recommendation_card(self, row: dict[str, str], prefix: str) -> str:
        evaluation = self.evaluation_for(row)
        result = evaluation.get("result", "") if evaluation else ""
        status_label = result or ("評価中" if evaluation else "評価待ち")
        tone = result_tone(status_label)
        report_href = self.report_url(row.get("report_file", ""), prefix)
        score = safe_float(row.get("score")) or 0
        stock_name = html.escape(row.get("stock_name", "不明"))
        reason = html.escape(row.get("selection_reason", "不明"))
        risks = html.escape(row.get("key_risks", "不明"))
        return f"""
<article class="stock-card filter-item" data-search="{html.escape((row.get('stock_name', '') + ' ' + row.get('stock_code', '') + ' ' + row.get('sector', '')).lower(), quote=True)}" data-status="{tone}">
  <div class="stock-card__top">
    <div><span class="rank">#{html.escape(row.get('rank', '—'))}</span><span class="stock-code">{html.escape(row.get('stock_code', '—'))}</span><h3>{stock_name}</h3><p class="sector">{html.escape(row.get('sector', '不明'))}</p></div>
    <div class="score" aria-label="スコア {score:.0f}点"><strong>{score:.0f}</strong><span>/ 100</span><i style="--score:{score:.0f}%"></i></div>
  </div>
  <div class="trade-grid">
    <div><span>参考価格</span><strong>¥{format_price(row.get('reference_price'))}</strong></div>
    <div><span>エントリー</span><strong>¥{format_number(row.get('entry_low'))}–{format_number(row.get('entry_high'))}</strong></div>
    <div><span>損切り</span><strong class="negative">¥{format_number(row.get('stop_price'))}</strong></div>
    <div><span>目標 1</span><strong class="positive">¥{format_number(row.get('target1'))}</strong></div>
  </div>
  <div class="card-copy"><span>選定理由</span><p>{reason}</p></div>
  <details><summary>主なリスク</summary><p>{risks}</p></details>
  <div class="stock-card__footer">{badge(status_label, tone)}<a class="text-link" href="{report_href}">詳細レポート <span aria-hidden="true">→</span></a></div>
</article>"""

    def build_reports(self) -> None:
        for folder, _, _ in REPORT_GROUPS:
            source_dir = ROOT / "reports" / folder
            for source in sorted(source_dir.glob("*.md"), reverse=True):
                relative_source = source.relative_to(ROOT).as_posix()
                output_path = f"reports/{folder}/{source.stem}/index.html"
                self.report_index[relative_source] = f"reports/{folder}/{source.stem}/"
                markdown = read_text(source)
                title = markdown_title(markdown, source.stem)
                article = f"""
<section class="page-hero page-hero--compact">
  <div class="shell"><p class="eyebrow">REPORT / {folder.upper()}</p><h1>{html.escape(title)}</h1><p>正本ファイル: {html.escape(relative_source)}</p></div>
</section>
<div class="shell article-layout">
  <article class="prose report-prose">{markdown_to_html(markdown)}</article>
  <aside class="article-aside"><div class="aside-card"><span>記録の扱い</span><p>このページは正本のMarkdownから自動生成されています。</p><a class="text-link" href="../../../reports/">レポート一覧へ →</a></div></aside>
</div>"""
                self.page(
                    output_path,
                    title=title,
                    description=f"Swing AI Labの{title}",
                    body=article,
                    active="reports",
                    depth=3,
                    page_class="article-page",
                )

    def latest_recommendations(self) -> list[dict[str, str]]:
        if not self.recommendations:
            return []
        latest_date = max(row.get("recommendation_date", "") for row in self.recommendations)
        return sorted(
            [row for row in self.recommendations if row.get("recommendation_date") == latest_date],
            key=lambda row: safe_float(row.get("rank")) or 999,
        )

    def latest_market(self) -> dict[str, str] | None:
        return max(self.markets, key=lambda row: row.get("date", "")) if self.markets else None

    def build_home(self) -> None:
        latest = self.latest_recommendations()
        latest_date = latest[0].get("recommendation_date", "") if latest else ""
        market = self.latest_market()
        evaluation_count = len([row for row in self.evaluations if row.get("result", "").strip()])
        cards = "".join(self.recommendation_card(row, "") for row in latest)
        if not cards:
            cards = self.empty_state("現在、公開中の推薦はありません", "条件が弱い週は無理に候補を追加しません。")
        market_body = (
            f"""<div class="market-state"><span class="pulse" aria-hidden="true"></span><div><small>MARKET REGIME</small><strong>{html.escape(market.get('market_regime', '不明'))}</strong></div></div>
            <p>{html.escape(market.get('volatility_notes', '市場環境データは未登録です。'))}</p>
            <div class="market-ticker">
              <div><span>日経平均</span><strong>{format_number(market.get('nikkei225'), 2)}</strong></div>
              <div><span>TOPIX</span><strong>{format_number(market.get('topix'), 2)}</strong></div>
              <div><span>USD/JPY</span><strong>{format_number(market.get('usd_jpy'), 2)}</strong></div>
              <div><span>米10年債</span><strong>{format_number(market.get('us_10y_yield'), 2)}%</strong></div>
            </div>"""
            if market
            else self.empty_state("市場環境は未登録です", "次回のスクリーニング後に反映されます。")
        )
        latest_reports = self.report_links(limit=4, prefix="")
        body = f"""
<section class="home-hero">
  <div class="shell home-hero__grid">
    <div class="hero-copy"><p class="eyebrow">RESEARCH LEDGER · JP EQUITIES</p><h1>判断の根拠を残し、<br><em>結果から改善する。</em></h1><p class="lead">日本株の1〜3週間スイング候補を、選定・検証・改善まで一貫して記録する公開リサーチ台帳です。</p><div class="hero-actions"><a class="button" href="recommendations/">最新の推薦を見る</a><a class="button button--ghost" href="reports/">レポートを読む</a></div></div>
    <div class="hero-panel">{market_body}<div class="as-of">基準日 <strong>{format_date(market.get('date', '')) if market else '—'}</strong></div></div>
  </div>
</section>
<section class="metric-band"><div class="shell metric-grid">
  <div><span>最新候補</span><strong>{len(latest)}</strong><small>銘柄</small></div>
  <div><span>評価完了</span><strong>{evaluation_count}</strong><small>件</small></div>
  <div><span>現行ルール</span><strong class="metric-text">{html.escape(self.rule_version)}</strong><small>version</small></div>
  <div><span>推薦基準日</span><strong class="metric-text">{format_date(latest_date)}</strong><small>as of</small></div>
</div></section>
<section class="section shell">
  <div class="section-heading"><div><p class="eyebrow">LATEST SELECTION</p><h2>最新の推薦銘柄</h2><p>{format_date(latest_date)} 選定。指定価格帯への到達と反発確認を前提とします。</p></div><a class="text-link" href="recommendations/">すべての推薦を見る →</a></div>
  <div class="stock-grid">{cards}</div>
</section>
<section class="section section--tint"><div class="shell process-grid">
  <div><p class="eyebrow">SELF-IMPROVEMENT</p><h2>結果を隠さず、<br>ルールを急いで変えない。</h2><p>推薦後の値動きを5・10・20営業日で評価し、期待値とProfit Factorを重視します。改善案は最低20件・4週間以上を原則に検証します。</p><a class="button button--dark" href="rules/">ルールと改善履歴</a></div>
  <ol class="process-list"><li><span>01</span><div><strong>選定</strong><p>テクニカル、業績、需給、材料、地合いを同じ基準で確認。</p></div></li><li><span>02</span><div><strong>事後評価</strong><p>約定、リターン、MFE・MAE、Target・Stopを記録。</p></div></li><li><span>03</span><div><strong>改善</strong><p>十分な標本と検証期間を満たした案だけを現行ルールへ反映。</p></div></li></ol>
</div></section>
<section class="section shell"><div class="section-heading"><div><p class="eyebrow">RECENT REPORTS</p><h2>新着レポート</h2></div><a class="text-link" href="reports/">アーカイブを見る →</a></div><div class="report-list">{latest_reports}</div></section>
<section class="disclaimer"><div class="shell"><strong>ご利用にあたって</strong><p>本サイトは投資助言、売買推奨、将来の収益保証を目的としません。掲載価格には基準時点があり、現在値とは異なる場合があります。最終的な投資判断は利用者自身で行ってください。</p></div></section>"""
        self.page(
            "index.html",
            title="日本株スイング分析の公開記録",
            description="日本株のスイング候補、選定理由、事後評価、ルール改善を公開する分析記録です。",
            body=body,
            active="overview",
            depth=0,
            page_class="home-page",
        )

    def empty_state(self, title: str, copy: str) -> str:
        return f'<div class="empty-state"><span aria-hidden="true">—</span><strong>{html.escape(title)}</strong><p>{html.escape(copy)}</p></div>'

    def build_recommendations(self) -> None:
        grouped: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
        for row in self.recommendations:
            grouped[row.get("recommendation_date", "不明")].append(row)
        sections: list[str] = []
        for date in sorted(grouped, reverse=True):
            rows = sorted(grouped[date], key=lambda row: safe_float(row.get("rank")) or 999)
            sections.append(
                f'<section class="recommendation-group"><div class="date-heading"><h2>{format_date(date)}</h2><span>{len(rows)}銘柄</span></div><div class="stock-grid">'
                + "".join(self.recommendation_card(row, "../") for row in rows)
                + "</div></section>"
            )
        content = "".join(sections) or self.empty_state("推薦履歴はまだありません", "条件を満たした候補が記録されると、ここに表示されます。")
        body = f"""
<section class="page-hero"><div class="shell"><p class="eyebrow">RECOMMENDATIONS</p><h1>推薦銘柄</h1><p>その時点で利用可能だった情報だけで選定した候補と、具体的な売買計画を記録しています。</p></div></section>
<div class="shell page-content">
  <div class="toolbar"><label class="search"><span>銘柄を検索</span><input type="search" data-filter-search placeholder="銘柄名・コード・セクター" autocomplete="off"></label><div class="filter-buttons" aria-label="評価状態"><button class="is-active" data-filter="all">すべて</button><button data-filter="pending">評価待ち</button><button data-filter="positive">勝ち</button><button data-filter="negative">負け</button></div></div>
  <p class="filter-empty" hidden>条件に一致する銘柄はありません。</p>{content}
</div>"""
        self.page(
            "recommendations/index.html",
            title="推薦銘柄",
            description="Swing AI Labが選定した日本株スイング候補と選定理由の一覧です。",
            body=body,
            active="recommendations",
            depth=1,
        )

    def build_results(self) -> None:
        completed = [row for row in self.evaluations if row.get("result", "").strip()]
        wins = [row for row in completed if result_tone(row.get("result", "")) == "positive"]
        losses = [row for row in completed if result_tone(row.get("result", "")) == "negative"]
        returns = [value for row in completed for value in [safe_float(row.get("return_20d"))] if value is not None]
        settled_count = len(wins) + len(losses)
        win_rate = f"{len(wins) / settled_count * 100:.1f}%" if settled_count else "—"
        latest_weekly = max(self.weekly, key=lambda row: row.get("review_date", "")) if self.weekly else None
        profit_factor = format_number(latest_weekly.get("profit_factor"), 2) if latest_weekly else "—"
        metrics = f"""
<div class="results-metrics">
  <div><span>評価完了</span><strong>{len(completed)}</strong><small>件</small></div>
  <div><span>勝率</span><strong>{win_rate}</strong><small>勝敗確定分</small></div>
  <div><span>20日平均</span><strong>{format_percent(mean(returns)) if returns else '—'}</strong><small>記録済みのみ</small></div>
  <div><span>Profit Factor</span><strong>{profit_factor}</strong><small>{'最新週次集計' if latest_weekly else '週次集計待ち'}</small></div>
</div>""" if completed else f"""
<div class="results-metrics">
  <div><span>評価完了</span><strong>0</strong><small>件</small></div>
  <div><span>勝率</span><strong>—</strong><small>評価待ち</small></div>
  <div><span>期待値</span><strong>—</strong><small>評価待ち</small></div>
  <div><span>Profit Factor</span><strong>—</strong><small>評価待ち</small></div>
</div>"""
        if completed:
            rows = []
            for row in sorted(completed, key=lambda item: item.get("evaluation_date", ""), reverse=True):
                result = row.get("result", "評価中")
                rows.append(f"""<tr><td>{format_date(row.get('recommendation_date', ''))}</td><td><strong>{html.escape(row.get('stock_code', '—'))}</strong><br>{html.escape(row.get('stock_name', '—'))}</td><td>{badge(result, result_tone(result))}</td><td>{format_percent(row.get('return_5d'))}</td><td>{format_percent(row.get('return_10d'))}</td><td>{format_percent(row.get('return_20d'))}</td><td>{format_percent(row.get('mfe_pct'))}</td><td>{format_percent(row.get('mae_pct'))}</td></tr>""")
            results_content = '<div class="table-scroll"><table><thead><tr><th>推薦日</th><th>銘柄</th><th>結果</th><th>5日</th><th>10日</th><th>20日</th><th>MFE</th><th>MAE</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"
        else:
            results_content = self.empty_state("最初の事後評価を待っています", "推薦翌営業日以降の5・10・20営業日を確認後、結果がここに反映されます。")
        body = f"""
<section class="page-hero"><div class="shell"><p class="eyebrow">PERFORMANCE</p><h1>推薦結果</h1><p>勝率だけでなく、期待値、Profit Factor、MFE・MAEを継続して確認します。</p></div></section>
<div class="shell page-content">{metrics}<section class="content-card"><div class="content-card__heading"><div><h2>評価履歴</h2><p>未取得データは推測せず空欄で残します。</p></div>{badge('未来情報を理由へ混入しない', 'neutral')}</div>{results_content}</section>
<section class="method-note"><div><p class="eyebrow">EVALUATION POLICY</p><h2>評価の考え方</h2></div><div><p>日足だけでTargetとStopの同日到達順を特定できない場合は「順序不明」とします。推薦時点の理由と、推薦後に判明した結果を分離して記録します。</p></div></section></div>"""
        self.page(
            "results/index.html",
            title="推薦結果",
            description="推薦銘柄の5・10・20営業日リターン、MFE、MAE、勝敗を記録します。",
            body=body,
            active="results",
            depth=1,
        )

    def all_report_records(self) -> list[tuple[str, str, str, str]]:
        records: list[tuple[str, str, str, str]] = []
        labels = {folder: label for folder, label, _ in REPORT_GROUPS}
        for source_path, url in self.report_index.items():
            source = ROOT / source_path
            markdown = read_text(source)
            folder = source.parent.name
            records.append((source.stem, markdown_title(markdown, source.stem), labels.get(folder, folder), url))
        return sorted(
            records,
            key=lambda item: (bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", item[0])), item[0]),
            reverse=True,
        )

    def report_links(self, limit: int | None, prefix: str) -> str:
        records = self.all_report_records()
        if limit is not None:
            records = records[:limit]
        if not records:
            return self.empty_state("レポートはまだありません", "新しいレポートが作成されると、ここに表示されます。")
        return "".join(
            f'<a class="report-row" href="{prefix}{url}"><div><span>{html.escape(label)}</span><h3>{html.escape(title)}</h3></div><time>{format_report_stamp(date)}</time><i aria-hidden="true">→</i></a>'
            for date, title, label, url in records
        )

    def build_report_index(self) -> None:
        groups: list[str] = []
        for folder, label, description in REPORT_GROUPS:
            records = [record for record in self.all_report_records() if record[2] == label]
            rows = "".join(
                f'<a class="report-row" href="../{url}"><div><span>{html.escape(label)}</span><h3>{html.escape(title)}</h3></div><time>{format_report_stamp(date)}</time><i aria-hidden="true">→</i></a>'
                for date, title, _, url in records
            ) or self.empty_state(f"{label}はまだありません", description)
            groups.append(f'<section class="report-group"><div class="date-heading"><div><h2>{html.escape(label)}</h2><p>{html.escape(description)}</p></div><span>{len(records)}件</span></div><div class="report-list">{rows}</div></section>')
        body = f"""
<section class="page-hero"><div class="shell"><p class="eyebrow">REPORT ARCHIVE</p><h1>レポート</h1><p>選定時の判断と、後日の検証を時系列で追跡できます。</p></div></section>
<div class="shell page-content report-archive">{''.join(groups)}</div>"""
        self.page(
            "reports/index.html",
            title="レポート",
            description="銘柄選定、事後評価、月次レビュー、検証記録のアーカイブです。",
            body=body,
            active="reports",
            depth=1,
        )

    def build_rules(self) -> None:
        body = f"""
<section class="page-hero"><div class="shell"><p class="eyebrow">RULES &amp; GOVERNANCE</p><h1>ルール・改善</h1><p>ルールは結果に合わせて都合よく書き換えず、十分な検証を経てバージョン管理します。</p></div></section>
<div class="shell rules-summary"><div><span>現行バージョン</span><strong>{html.escape(self.rule_version)}</strong></div><div><span>採用に必要な標本</span><strong>20<small>件以上</small></strong></div><div><span>最低検証期間</span><strong>4<small>週間</small></strong></div></div>
<div class="shell article-layout rules-layout"><article class="prose">{markdown_to_html(self.rule_markdown)}</article><aside class="article-aside"><div class="aside-card aside-card--sticky"><span>改善記録</span><p>採用済みの変更、検証中の候補、棄却済み案を確認できます。</p><a class="button button--dark" href="../improvements/">改善履歴を見る</a></div></aside></div>"""
        self.page(
            "rules/index.html",
            title="現行ルール",
            description="Swing AI Labの現行選定ルールとリスク管理基準です。",
            body=body,
            active="rules",
            depth=1,
            page_class="article-page",
        )

    def build_improvements(self) -> None:
        body = f"""
<section class="page-hero"><div class="shell"><p class="eyebrow">IMPROVEMENT LOG</p><h1>運用改善レポート</h1><p>何を、なぜ変えたか。採用しなかった案も含めて記録します。</p></div></section>
<div class="shell improvement-layout">
  <section class="prose improvement-block"><div class="block-label">ADOPTED</div>{markdown_to_html(self.improvement_markdown)}</section>
  <section class="prose improvement-block"><div class="block-label">UNDER REVIEW</div>{markdown_to_html(self.candidates_markdown)}</section>
  <section class="prose improvement-block"><div class="block-label">REJECTED</div>{markdown_to_html(self.rejected_markdown)}</section>
</div>"""
        self.page(
            "improvements/index.html",
            title="運用改善レポート",
            description="採用済みルール変更、検証中の改善候補、棄却済みルールの記録です。",
            body=body,
            active="rules",
            depth=1,
            page_class="article-page",
        )

    def build_not_found(self) -> None:
        body = """
<section class="page-hero"><div class="shell"><p class="eyebrow">404 / NOT FOUND</p><h1>ページが見つかりません</h1><p>URLが変更されたか、まだ公開されていない可能性があります。</p><div class="hero-actions"><a class="button" href="./">トップへ戻る</a><a class="button button--ghost" href="./reports/">レポートを見る</a></div></div></section>
"""
        self.page(
            "404.html",
            title="ページが見つかりません",
            description="指定されたページは見つかりませんでした。",
            body=body,
            active="overview",
            depth=0,
        )

    def build(self) -> None:
        self.prepare()
        self.build_reports()
        self.build_home()
        self.build_recommendations()
        self.build_results()
        self.build_report_index()
        self.build_rules()
        self.build_improvements()
        self.build_not_found()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT not in output.parents:
        raise SystemExit("Output directory must be inside the repository and cannot be the repository root.")
    builder = SiteBuilder(output)
    builder.build()
    html_count = len(list(output.rglob("*.html")))
    print(f"Built {html_count} HTML pages in {output}")


if __name__ == "__main__":
    main()
