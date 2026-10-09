import unittest
import tempfile
import json
from pathlib import Path
from research_checks import aggregate_trades, entry_at_open, exit_from_bar, max_drawdown, size_position, session_after, validate
from evaluation_schedule import schedule
from research_checks import ROOT


class ResearchTests(unittest.TestCase):
    def trade(self, trade_id, pnl, **updates):
        r=dict(trade_id=trade_id,strategy_id='A',protocol_id='EP-1',cost_model_id='base',audit_status='verified',status='closed',entry_date='2026-10-13',exit_date='2026-10-14',entry_price='100',exit_price=str(100+pnl),shares='1',fees_jpy='0',slippage_jpy='0',dividend_jpy='0')
        r.update(updates);return r

    def test_populations_and_missing_are_not_zero(self):
        rows=[self.trade('1',10),self.trade('2',-5),self.trade('3',200,status='open'),self.trade('4',300,audit_status='unverified'),self.trade('5',-50,strategy_id='B')]
        a,b=aggregate_trades(rows)
        self.assertEqual((a['count'],a['win_rate'],a['pf'],a['average_return']),(2,50,2,2.5))
        self.assertEqual(b['pf'],0)
        self.assertIsNone(aggregate_trades([rows[0]])[0]['pf'])

    def test_costs_dividends_breakeven(self):
        a=aggregate_trades([self.trade('1',10,fees_jpy='8',slippage_jpy='3',dividend_jpy='1')])[0]
        self.assertEqual(a['pnl'],0);self.assertEqual(a['win_rate'],0)

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):aggregate_trades([self.trade('1',1),self.trade('1',2)])

    def test_no_lookahead_or_intraday_limit_fill(self):
        bar=dict(date='2026-10-13',open=110,high=115,low=95,close=105)
        self.assertIsNone(entry_at_open('2026-10-09','2026-10-13',100,bar))
        with self.assertRaises(ValueError):entry_at_open('2026-10-13','2026-10-13',100,bar)

    def test_gap_stop_and_ambiguous_sequence(self):
        self.assertEqual(exit_from_bar(95,110,dict(open=90,high=100,low=85,close=96)),('stop_gap',90))
        self.assertEqual(exit_from_bar(95,110,dict(open=100,high=115,low=90,close=105))[0],'ambiguous')
        self.assertEqual(exit_from_bar(95,110,dict(open=90,high=100,low=85,close=96),entered_today=True)[0],'ambiguous')

    def test_lot_and_risk_cap(self):
        self.assertEqual(size_position(10000,100,90,1000,500),0)
        self.assertEqual(size_position(50000,100,90,2000,1000),100)
        self.assertEqual(size_position(10000,100,90,1000,1000,cost_reserve=1),0)

    def test_calendar_and_initial_nav(self):
        self.assertEqual(session_after('2026-10-09',1,['2026-10-09','2026-10-13']), '2026-10-13')
        self.assertIsNone(session_after('2026-10-09',2,['2026-10-13']))
        self.assertAlmostEqual(max_drawdown([100,90,110,88]),-20)

    def test_jpx_deadlines(self):
        rows=schedule(ROOT,'2026-10-08')
        deadlines={(r['recommendation_date'],r['stock_code'],r['horizon_sessions']):r['due_date'] for r in rows}
        self.assertEqual(deadlines[('2026-08-31','6702',20)],'2026-10-01')
        self.assertEqual(deadlines[('2026-10-05','6098',20)],'2026-11-04')

    def test_repository_consistency(self):
        self.assertEqual(validate(),[])

    def test_site_excludes_legacy_metrics_and_private_settings(self):
        from build_site import SiteBuilder
        profile=ROOT/'.local/operating_profile.json'
        private_capital=json.loads(profile.read_text()).get('capital_jpy') if profile.exists() else None
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'site'
            builder=SiteBuilder(output)
            builder.trades=[]  # Explicit empty verified population, independent of future records.
            builder.build()
            page=(output/'results/index.html').read_text()
            self.assertIn('検証済み成績はまだありません',page)
            self.assertIn('監査保留',page)
            self.assertNotIn('83.3%',page)
            self.assertNotIn('20日平均',page)
            for p in output.rglob('*'):
                self.assertNotIn('.local',p.parts)
                if p.suffix=='.html':
                    self.assertNotIn('loss_tolerance_jpy',p.read_text())
                    if private_capital is not None:
                        self.assertNotIn(str(private_capital),p.read_text())


if __name__=='__main__': unittest.main()
