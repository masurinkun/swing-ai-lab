"""Generate review deadlines from the stored official JPX calendar, without fetching prices."""
import argparse
import csv
from datetime import date, timedelta
from pathlib import Path
from research_checks import ROOT, read_rows, session_after


def schedule(root, as_of):
    recs=read_rows(root/'history/recommendations.csv')
    holidays={r['date'] for r in read_rows(root/'data/jpx_holidays_2026.csv')}
    days=[]
    d=date(2026,1,1)
    while d.year==2026:
        if d.weekday()<5 and str(d) not in holidays: days.append(str(d))
        d+=timedelta(days=1)
    marks={(r['recommendation_date'],r['stock_code'],r['horizon_sessions']) for r in read_rows(root/'history/mark_returns.csv') if r['audit_status']=='verified'}
    legacy={(r['recommendation_date'],r['stock_code']) for r in read_rows(root/'history/audit.csv')}
    output=[]
    for r in recs:
        for n in [5,10,20]:
            due=session_after(r['recommendation_date'],n,days)
            key=(r['recommendation_date'],r['stock_code'])
            status=('calendar_missing' if due is None else 'not_due' if due>as_of else
                    'verified' if (*key,str(n)) in marks else
                    'legacy_revalidation_required' if key in legacy else 'due')
            output.append(dict(recommendation_date=key[0],stock_code=key[1],horizon_sessions=n,due_date=due or '',as_of=as_of,status=status,
                reason='旧基準再検証' if status=='legacy_revalidation_required' else ''))
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of',required=True,help='Last confirmed closed JPX session, YYYY-MM-DD')
    parser.add_argument('--write',action='store_true',help='Update the canonical deadline CSV')
    args=parser.parse_args();date.fromisoformat(args.as_of)
    rows=schedule(ROOT,args.as_of)
    if args.write:
        with (ROOT/'history/evaluation_schedule.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
    from collections import Counter
    print(dict(Counter(r['status'] for r in rows)))
