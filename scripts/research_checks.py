"""Offline ledger validation and deterministic research calculations; never places orders."""
from __future__ import annotations

import csv
import hashlib
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite number")
    return result


def trade_pnl(row):
    return ((number(row['exit_price']) - number(row['entry_price'])) * number(row['shares'])
            + number(row['dividend_jpy']) - number(row['fees_jpy']) - number(row['slippage_jpy']))


def aggregate_trades(rows):
    """Return separate populations; never select a convenient latest weekly row."""
    groups = {}
    seen = set()
    for r in rows:
        if r['trade_id'] in seen:
            raise ValueError('Duplicate trade_id')
        seen.add(r['trade_id'])
        if r['audit_status'] != 'verified' or r['status'] != 'closed':
            continue
        key = (r['strategy_id'], r['protocol_id'], r['cost_model_id'])
        groups.setdefault(key, []).append(r)
    output = []
    for key, group in sorted(groups.items()):
        pnls = [trade_pnl(r) for r in group]
        losses = -sum(x for x in pnls if x < 0)
        output.append(dict(strategy=key[0], protocol=key[1], cost_model=key[2], count=len(group),
            start=min(r['entry_date'] for r in group), end=max(r['exit_date'] for r in group),
            win_rate=100 * sum(x > 0 for x in pnls) / len(pnls),
            average_return=mean(100*p/(number(r['entry_price'])*number(r['shares'])) for p,r in zip(pnls,group)),
            pnl=sum(pnls), pf=sum(x for x in pnls if x > 0)/losses if losses else None))
    return output


def session_after(start, count, sessions):
    later = [d for d in sessions if d > start]
    if len(later) < count:
        return None
    return later[count-1]


def entry_at_open(signal_date, order_date, entry_limit, bar):
    """EP-1, prices before explicit costs. A filled limit cannot be cancelled retrospectively."""
    if not signal_date < order_date or bar['date'] != order_date:
        raise ValueError('Signal must precede the order session')
    opening = number(bar['open'])
    return opening if opening <= entry_limit else None


def exit_from_bar(stop, target, bar, *, entered_today=False, deadline=False):
    """Daily bars cannot resolve both exits or child-order activation at an opening gap."""
    o,h,l,c = (number(bar[k]) for k in ['open','high','low','close'])
    if entered_today and o <= stop:
        return ('ambiguous', None)
    if not entered_today and o <= stop:
        return ('stop_gap', o)
    if not entered_today and o >= target:
        return ('target_gap', o)
    if l <= stop and h >= target:
        return ('ambiguous', None)
    if l <= stop:
        return ('stop', stop)
    if h == target:
        return ('ambiguous', None)  # Queue/volume are unavailable.
    if h > target:
        return ('target', target)
    return ('deadline', c) if deadline else ('open', None)


def size_position(capital_available, entry_limit, stop, risk_available, per_trade_risk, lot_size=100, cost_reserve=0):
    if entry_limit <= stop or stop <= 0 or lot_size <= 0 or cost_reserve < 0:
        raise ValueError('Invalid price, lot or cost')
    money = max(0, capital_available-cost_reserve)
    risk = max(0, min(risk_available, per_trade_risk)-cost_reserve)
    lots = math.floor(min(money/entry_limit, risk/(entry_limit-stop))/lot_size)
    return max(0,lots)*lot_size


def max_drawdown(nav):
    if not nav or any(number(x) <= 0 for x in nav):
        raise ValueError('A complete positive NAV series including initial capital is required')
    peak=number(nav[0]); dd=0.0
    for x in nav:
        x=number(x); peak=max(peak,x); dd=min(dd,x/peak-1)
    return 100*dd


def validate(root=ROOT):
    errors=[]
    def check(condition, message):
        if not condition: errors.append(message)
    recs=read_rows(root/'history/recommendations.csv')
    keys=[(r['recommendation_date'],r['stock_code']) for r in recs]
    check(len(keys)==len(set(keys)), 'Duplicate recommendation key')
    rec_by_key=dict(zip(keys,recs))
    for a in read_rows(root/'history/audit.csv'):
        key=(a['recommendation_date'],a['stock_code'])
        check(key in rec_by_key, f'Audit without recommendation: {key}')
        if key in rec_by_key:
            for col in ['entry_low','entry_high','stop_price']:
                check(a[col]==rec_by_key[key][col],f'Audit changes original {key} {col}')
    archive=root/'archive/pre_audit_2026-10-09'
    for r in read_rows(archive/'manifest.csv'):
        p=archive/r['path']
        check(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'], f'Archive changed: {p}')
    for file in ['evaluations.csv','weekly_performance.csv']:
        old=read_rows(archive/'history'/file); new=read_rows(root/'history'/file)
        check(len(old)==len(new),f'Legacy row count changed: {file}')
        for before,after in zip(old,new):
            check(all(after.get(k)==v for k,v in before.items()),f'Legacy claim overwritten: {file}')
            check(after.get('audit_status')=='legacy_unverified',f'Unverified legacy row exposed: {file}')
    for r in read_rows(root/'data/manifest.csv'):
        p=root/r['path']
        check(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],f'Source checksum mismatch: {p}')
    plans=read_rows(root/'history/plans.csv')
    check(len(plans)==len({r['plan_id'] for r in plans}), 'Duplicate plan_id')
    by_plan={p['plan_id']:p for p in plans}
    for p in plans:
        try:
            signal=datetime.fromisoformat(p['signal_confirmed_at'])
            created=datetime.fromisoformat(p['created_at'])
            check(signal.utcoffset() is not None and created.utcoffset() is not None,'Plan timestamps require timezone')
            if signal.utcoffset() is None or created.utcoffset() is None:
                raise ValueError('Missing timezone')
            signal=signal.astimezone(ZoneInfo('Asia/Tokyo'))
            created=created.astimezone(ZoneInfo('Asia/Tokyo'))
            check(signal<=created, 'Plan created before its signal')
            check(signal.date().isoformat()==p['signal_date'], 'Signal timestamp/date mismatch')
            check((signal.hour,signal.minute)>=(15,30),'Signal before market close')
            check(p['signal_date'] < p['order_date'] <= p['exit_deadline'],'Invalid plan session order')
            check(created.date().isoformat() <= p['order_date'],'Plan registered retrospectively')
            if created.date().isoformat()==p['order_date']:
                check(created.hour<9,'Order plan registered after opening')
            check(number(p['stop_price'])<number(p['entry_limit'])<number(p['target_price']),'Invalid plan prices')
            check(number(p['shares'])>0 and number(p['shares'])%number(p['lot_size'])==0,'Invalid lot sizing')
            check((root/p['source_file']).is_file(), 'Plan source missing')
        except (ValueError,ZeroDivisionError,KeyError): errors.append('Invalid plan: '+p.get('plan_id',''))
    trades=read_rows(root/'history/trade_results.csv')
    for r in trades:
        check(r['status'] in {'pending','open','closed','no_entry','ambiguous'},'Unknown trade status')
        check(r['audit_status'] in {'verified','unverified'},'Unknown audit status')
        check(r['plan_id'] in by_plan,'Trade without plan')
        if r['audit_status']=='verified':
            check(bool(r['source_file']) and (root/r['source_file']).is_file(),'Verified trade without evidence')
        if r['audit_status']=='verified' and r['status']=='closed':
            try:
                check(r['entry_date']<=r['exit_date'],'Exit before entry')
                check(number(r['entry_price'])>0 and number(r['exit_price'])>0 and number(r['shares'])>0,'Invalid trade values')
                for k in ['fees_jpy','slippage_jpy','dividend_jpy']: check(number(r[k])>=0, 'Missing/negative cost or dividend')
                p=by_plan.get(r['plan_id'],{})
                for k in ['strategy_id','protocol_id','cost_model_id','recommendation_date','stock_code']:
                    check(r[k]==p.get(k),'Trade changes plan: '+k)
                check(r['entry_date']==p.get('order_date'),'Trade on wrong order day')
                check(r['exit_date']<=p.get('exit_deadline',''),'Exit past deadline')
                check(r['shares']==p.get('shares'),'Trade sizing differs from plan; split/partial fills need separate audit')
            except (ValueError,KeyError): errors.append('Invalid closed trade: '+r.get('trade_id',''))
    marks=read_rows(root/'history/mark_returns.csv')
    markkeys=[(r['recommendation_date'],r['stock_code'],r['horizon_sessions']) for r in marks]
    check(len(markkeys)==len(set(markkeys)), 'Duplicate mark return')
    for r in marks:
        if r['audit_status']!='verified': continue
        try:
            check(r['recommendation_date']<r['base_date']<=r['end_date'],'Invalid fixed-return base date')
            check(r['adjustment_basis']=='split_adjusted_price_only','Inconsistent fixed-return adjustment basis')
            check(abs(number(r['return_pct'])-100*(number(r['end_close'])/number(r['base_open'])-1))<0.011,'Incorrect fixed return')
            check((root/r['source_file']).is_file(),'Missing fixed-return evidence')
        except (ValueError,ZeroDivisionError): errors.append('Invalid fixed return')
    navs=read_rows(root/'history/portfolio_daily.csv')
    navkeys=[(r['experiment_id'],r['strategy_id'],r['cost_model_id'],r['date']) for r in navs]
    check(len(navkeys)==len(set(navkeys)), 'Duplicate NAV observation')
    for r in navs:
        if r['audit_status']!='verified': continue
        try:
            total=sum(number(r[k]) for k in ['cash_jpy','market_value_jpy','dividend_receivable_jpy'])
            check(abs(total-number(r['nav_jpy']))<0.01,'NAV does not reconcile')
            check(number(r['cash_jpy'])>=0,'Negative cash in cash-only model')
            check((root/r['source_file']).is_file(),'NAV evidence missing')
        except ValueError: errors.append('Invalid NAV')
    try: aggregate_trades(trades)
    except (ValueError,KeyError,ZeroDivisionError) as e: errors.append(str(e))
    return errors


if __name__=='__main__':
    errors=validate()
    if errors: raise SystemExit('\n'.join(errors))
    print('Ledger identities, immutable history, provenance and verified populations checked.')
