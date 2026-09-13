# backtest_engine.py
"""Backtest vectorizado con walk-forward, bootstrap y Monte Carlo."""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class BacktestEngine:
    def __init__(self, initial_capital=10000.0, fee=0.001, slippage=0.0005):
        self.initial_capital = initial_capital
        self.fee = fee
        self.slippage = slippage

    def simulate(self, signals_df, data_dict, max_hold=60):
        trades = []
        for _, sig in signals_df.iterrows():
            sym = sig['symbol']
            if sym not in data_dict or data_dict[sym] is None:
                continue
            df = data_dict[sym]
            if df.empty:
                continue
            entry_idx = df.index.get_indexer([sig['timestamp']], method='nearest')[0]
            if entry_idx < 0 or entry_idx >= len(df) - 1:
                continue

            direction = sig['direction']
            entry = sig['entry_price']
            sl = sig['sl_price']
            tp = sig['tp_price']
            be_trigger = sig.get('break_even_trigger', 0.002)

            end_idx = min(entry_idx + max_hold, len(df) - 1)
            future = df.iloc[entry_idx + 1: end_idx + 1]

            exit_price = None
            exit_reason = 'TIME'
            be_active = False

            for ts, row in future.iterrows():
                high, low, close = row['high'], row['low'], row['close']

                if direction == 'LONG':
                    if low <= sl:
                        exit_price = sl * (1 - self.slippage)
                        exit_reason = 'SL'
                        break
                    if high >= tp:
                        exit_price = tp * (1 - self.slippage)
                        exit_reason = 'TP'
                        break
                    if not be_active and (high / entry - 1) >= be_trigger:
                        be_active = True
                        sl = entry
                    if be_active:
                        new_sl = close * (1 - be_trigger)
                        sl = max(sl, new_sl)
                else:
                    if high >= sl:
                        exit_price = sl * (1 + self.slippage)
                        exit_reason = 'SL'
                        break
                    if low <= tp:
                        exit_price = tp * (1 + self.slippage)
                        exit_reason = 'TP'
                        break
                    if not be_active and (1 - low / entry) >= be_trigger:
                        be_active = True
                        sl = entry
                    if be_active:
                        new_sl = close * (1 + be_trigger)
                        sl = min(sl, new_sl)

            if exit_price is None:
                exit_price = future['close'].iloc[-1] if not future.empty else entry

            if direction == 'LONG':
                gross = (exit_price - entry) / entry
            else:
                gross = (entry - exit_price) / entry
            net = gross - 2 * self.fee

            trades.append({
                'symbol': sym, 'direction': direction,
                'entry_time': sig['timestamp'], 'entry_price': entry,
                'exit_price': exit_price, 'exit_reason': exit_reason,
                'pnl_pct': net * 100, 'pnl_abs': net * self.initial_capital,
                'score': sig.get('score', 0), 'level': sig.get('level', 'NO-TIER'),
                'adx': sig.get('adx', 0), 'ker': sig.get('ker', 0),
                'regime': sig.get('regime', 'Chop'),
            })
        return pd.DataFrame(trades)

    def compute_metrics(self, trades_df):
        if trades_df.empty:
            return {'error': 'No trades'}
        wins = trades_df[trades_df['pnl_pct'] > 0]
        losses = trades_df[trades_df['pnl_pct'] <= 0]
        n = len(trades_df)
        n_wins, n_losses = len(wins), len(losses)
        wr = n_wins / n if n > 0 else 0
        avg_win = wins['pnl_pct'].mean() if n_wins > 0 else 0
        avg_loss = losses['pnl_pct'].mean() if n_losses > 0 else 0
        gross_profit = wins['pnl_pct'].sum() if n_wins > 0 else 0
        gross_loss = abs(losses['pnl_pct'].sum()) if n_losses > 0 else 1e-9
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        expectancy = wr * avg_win + (1 - wr) * avg_loss
        total_return = trades_df['pnl_pct'].sum()
        equity = self.initial_capital * (1 + trades_df['pnl_pct'] / 100).cumprod()
        peak = equity.cummax()
        dd = (equity - peak) / peak
        max_dd = dd.min() * 100
        rets = trades_df['pnl_pct'] / 100
        sharpe = (rets.mean() / rets.std() * np.sqrt(252)) if rets.std() > 0 else 0
        downside = rets[rets < 0].std()
        sortino = (rets.mean() / downside * np.sqrt(252)) if downside > 0 else 0
        calmar = total_return / abs(max_dd) if max_dd != 0 else 0
        return {
            'total_trades': n, 'wins': n_wins, 'losses': n_losses,
            'win_rate': wr * 100, 'profit_factor': pf,
            'expectancy_pct': expectancy, 'total_return_pct': total_return,
            'max_drawdown_pct': max_dd, 'sharpe': sharpe,
            'sortino': sortino, 'calmar': calmar,
            'avg_win_pct': avg_win, 'avg_loss_pct': avg_loss,
        }


def walk_forward_backtest(signals_all, data_dict, train_days=30, test_days=7,
                          max_hold=60, capital=10000.0):
    if signals_all.empty:
        return []
    signals_all = signals_all.sort_values('timestamp')
    start = signals_all['timestamp'].min()
    end = signals_all['timestamp'].max()
    windows = []
    cursor = start
    while cursor + timedelta(days=train_days + test_days) <= end:
        train_end = cursor + timedelta(days=train_days)
        test_end = train_end + timedelta(days=test_days)
        train_sigs = signals_all[(signals_all['timestamp'] >= cursor) &
                                 (signals_all['timestamp'] < train_end)]
        test_sigs = signals_all[(signals_all['timestamp'] >= train_end) &
                                (signals_all['timestamp'] < test_end)]
        engine = BacktestEngine(capital)
        train_trades = engine.simulate(train_sigs, data_dict, max_hold)
        test_trades = engine.simulate(test_sigs, data_dict, max_hold)
        windows.append({
            'train_start': cursor, 'train_end': train_end,
            'test_start': train_end, 'test_end': test_end,
            'train_metrics': engine.compute_metrics(train_trades),
            'test_metrics': engine.compute_metrics(test_trades),
            'test_trades': len(test_trades),
        })
        cursor += timedelta(days=test_days)
    return windows


def monte_carlo_bootstrap(trades_df, n_iter=10000, capital=10000.0):
    if trades_df.empty or len(trades_df) < 5:
        return {}
    pnls = trades_df['pnl_pct'].values / 100
    n = len(pnls)
    results = np.zeros((n_iter, 4))
    rng = np.random.default_rng(42)
    for i in range(n_iter):
        sample = rng.choice(pnls, size=n, replace=True)
        equity = capital * np.cumprod(1 + sample)
        final_ret = equity[-1] / capital - 1
        peak = np.maximum.accumulate(equity)
        dd = ((equity - peak) / peak).min()
        sharpe = sample.mean() / sample.std() * np.sqrt(252) if sample.std() > 0 else 0
        wr = (sample > 0).mean()
        results[i] = [final_ret, dd, sharpe, wr]
    return {
        'final_return_ci95': (np.percentile(results[:, 0], 2.5), np.percentile(results[:, 0], 97.5)),
        'max_dd_ci95': (np.percentile(results[:, 1], 2.5), np.percentile(results[:, 1], 97.5)),
        'sharpe_ci95': (np.percentile(results[:, 2], 2.5), np.percentile(results[:, 2], 97.5)),
        'win_rate_ci95': (np.percentile(results[:, 3], 2.5), np.percentile(results[:, 3], 97.5)),
        'median_final_return': np.median(results[:, 0]),
        'prob_positive': (results[:, 0] > 0).mean(),
    }
