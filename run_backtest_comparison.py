# run_backtest_comparison.py
"""Backtest comparativo: sistema ACTUAL vs sistema CORREGIDO."""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxt
from config import DEFAULT_PARAMS

SYMBOLS_TEST = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
                'BNB/USDT', 'DOGE/USDT', 'LINK/USDT', 'AVAX/USDT', 'DOT/USDT']
TIMEFRAME = '1h'
LIMIT = 4320
TRAIN_DAYS, TEST_DAYS = 30, 7
CAPITAL, FEE, SLIPPAGE = 10000.0, 0.001, 0.0005


def fetch_historical(symbols, timeframe='1h', limit=4320):
    exchange = ccxt.binance({'enableRateLimit': True})
    exchange.load_markets()
    data = {}
    for sym in symbols:
        try:
            ohlcv = exchange.fetch_ohlcv(sym, timeframe, limit=limit)
            if not ohlcv:
                continue
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df = df.set_index('timestamp').sort_index()
            df = df[~df.index.duplicated(keep='last')]
            data[sym] = df
            print(f"  ✅ {sym}: {len(df)} velas ({df.index[0].date()} → {df.index[-1].date()})")
        except Exception as e:
            print(f"  ⚠️ {sym}: {e}")
    return data


if __name__ == '__main__':
    from signal_engine import Signal
    from backtest_engine import BacktestEngine, walk_forward_backtest, monte_carlo_bootstrap

    print("📥 Descargando datos históricos de Binance (API pública)...")
    data = fetch_historical(SYMBOLS_TEST, TIMEFRAME, LIMIT)

    # V1: sistema actual (look-ahead presente, score asimétrico)
    sigs_v1 = []
    for sym in SYMBOLS_TEST:
        if sym not in data: continue
        df = data[sym]
        for i in range(60, len(df)):
            s = Signal(sym, df.iloc[:i+1], DEFAULT_PARAMS)
            d = s.to_dict(); d['timestamp'] = df.index[i]
            sigs_v1.append(d)
    sigs_v1 = pd.DataFrame(sigs_v1)

    # V2: sistema corregido (sin look-ahead, score simétrico)
    sigs_v2 = []
    for sym in SYMBOLS_TEST:
        if sym not in data: continue
        df = data[sym]
        for i in range(60, len(df)):
            window = df.iloc[:i]
            if len(window) < 30: continue
            s = Signal(sym, window, DEFAULT_PARAMS)
            d = s.to_dict(); d['timestamp'] = df.index[i]
            sigs_v2.append(d)
    sigs_v2 = pd.DataFrame(sigs_v2)

    engine = BacktestEngine(CAPITAL, FEE, SLIPPAGE)
    trades_v1 = engine.simulate(sigs_v1[sigs_v1['is_valid']], data, max_hold=60)
    trades_v2 = engine.simulate(sigs_v2[sigs_v2['is_valid']], data, max_hold=60)

    m1 = engine.compute_metrics(trades_v1)
    m2 = engine.compute_metrics(trades_v2)

    print("\n" + "="*70)
    print(f"{'Métrica':<25} {'V1 (actual)':<20} {'V2 (corregido)':<20}")
    print("-"*65)
    for key, label in [('total_trades','Trades'), ('win_rate','Win Rate %'),
                       ('profit_factor','Profit Factor'), ('expectancy_pct','Expectancy %'),
                       ('total_return_pct','Return total %'), ('max_drawdown_pct','Max DD %'),
                       ('sharpe','Sharpe'), ('sortino','Sortino')]:
        v1 = m1.get(key, 'N/A'); v2 = m2.get(key, 'N/A')
        if isinstance(v1, float): v1 = f"{v1:.3f}"
        if isinstance(v2, float): v2 = f"{v2:.3f}"
        print(f"{label:<25} {str(v1):<20} {str(v2):<20}")

    # Distribución LONG/SHORT
    print("\n" + "="*70)
    print("DISTRIBUCIÓN LONG/SHORT")
    for label, sigs in [('V1', sigs_v1), ('V2', sigs_v2)]:
        app = sigs[sigs['is_valid']]
        l = (app['direction']=='LONG').sum(); s = (app['direction']=='SHORT').sum()
        print(f"  {label}: LONG={l}, SHORT={s}, ratio L/S={l/max(s,1):.2f}")

    # Walk-forward y Monte Carlo sobre V2
    wf = walk_forward_backtest(sigs_v2[sigs_v2['is_valid']], data, TRAIN_DAYS, TEST_DAYS, 60, CAPITAL)
    print("\n" + "="*70)
    print("WALK-FORWARD (V2)")
    for w in wf:
        tm = w['test_metrics']
        if 'total_return_pct' in tm:
            print(f"  {w['test_start'].date()}→{w['test_end'].date()}: "
                  f"{tm['total_trades']} trades, {tm['total_return_pct']:.2f}%, "
                  f"WR={tm['win_rate']:.1f}%")

    mc = monte_carlo_bootstrap(trades_v2, n_iter=10000, capital=CAPITAL)
    print("\n" + "="*70)
    print("MONTE CARLO BOOTSTRAP (V2, 10k iter)")
    for k, v in mc.items(): print(f"  {k}: {v}")
