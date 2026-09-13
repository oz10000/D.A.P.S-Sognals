# core_engine.py
import pandas as pd
import numpy as np
import logging
from config import ASSET_PARAMS, DEFAULT_PARAMS

logger = logging.getLogger(__name__)


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df['high'], df['low'], df['close'].shift(1)
    return pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR con suavizado Wilder (RMA)."""
    if df.empty or len(df) < period:
        return pd.Series(0.0, index=df.index)
    tr = _true_range(df)
    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    return atr.fillna(0).replace([np.inf, -np.inf], 0)


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ADX con fórmula original de Wilder."""
    if df.empty or len(df) < period:
        return pd.Series(0.0, index=df.index)

    high, low = df['high'], df['low']
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    alpha = 1.0 / period
    tr = _true_range(df)
    atr_s = tr.ewm(alpha=alpha, adjust=False).mean().replace(0, np.nan)

    plus_di = 100 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_s
    minus_di = 100 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_s

    di_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = (plus_di - minus_di).abs() / di_sum * 100
    dx = dx.fillna(0).replace([np.inf, -np.inf], 0)
    adx = dx.ewm(alpha=alpha, adjust=False).mean()
    return adx.fillna(0).replace([np.inf, -np.inf], 0)


def compute_ker(df: pd.DataFrame, period: int = 10) -> pd.Series:
    if df.empty or len(df) < period:
        return pd.Series(0.0, index=df.index)
    close = df['close']
    change = abs(close.diff(period))
    volatility = close.diff().abs().rolling(period).sum()
    ker = change / (volatility + 1e-9)
    return ker.fillna(0).replace([np.inf, -np.inf], 0)


def compute_ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    if df.empty:
        return pd.Series(0.0, index=df.index)
    return df['close'].ewm(span=period, adjust=False).mean()


def compute_regime(df: pd.DataFrame, adx_val: float, ker_val: float, atr_pct: float) -> str:
    if df.empty or len(df) < 30:
        return 'Chop'
    if adx_val > 40 and atr_pct > 0.02:
        return 'Expansión'
    elif adx_val > 30:
        return 'Tendencia Fuerte'
    elif adx_val > 20:
        return 'Tendencia Débil'
    else:
        return 'Chop'


def compute_pidelta_score(df: pd.DataFrame, symbol: str = None) -> float:
    """Score compuesto SIMÉTRICO [-1, +1]."""
    if df.empty or len(df) < 30:
        return 0.0
    close = df['close']

    if symbol and symbol in ASSET_PARAMS:
        p = ASSET_PARAMS[symbol]
        ema_period, atr_period = p.get('ema_opt', 22), p.get('atr_opt', 14)
        adx_period, ker_period = p.get('adx_opt', 14), p.get('ker_opt', 10)
    else:
        ema_period, atr_period, adx_period, ker_period = 22, 14, 14, 10

    ema = close.ewm(span=ema_period, adjust=False).mean()
    trend_raw = (ema.iloc[-1] - ema.iloc[-5]) / (ema.iloc[-5] + 1e-12) if len(ema) >= 5 else 0
    momentum_raw = (close.iloc[-1] - close.iloc[-5]) / (close.iloc[-5] + 1e-12) if len(close) >= 5 else 0
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema_dir = np.sign(close.iloc[-1] - ema50.iloc[-1])

    adx_s = compute_adx(df, adx_period); adx_v = adx_s.iloc[-1] if not adx_s.empty else 0
    ker_s = compute_ker(df, ker_period); ker_v = ker_s.iloc[-1] if not ker_s.empty else 0
    atr_s = compute_atr(df, atr_period); atr_v = atr_s.iloc[-1] if not atr_s.empty else 0
    atr_ma = atr_s.rolling(20).mean().iloc[-1] if len(atr_s) >= 20 else atr_v
    atr_rel = atr_v / atr_ma if atr_ma > 0 else 1.0

    quality = (
        0.25 * min(abs(trend_raw) * 10, 1.0) +
        0.20 * min(adx_v / 40.0, 1.0) +
        0.15 * min(max(ker_v, 0), 1.0) +
        0.10 * min(max(atr_rel, 0.5), 2.0) / 2.0 +
        0.10 * min(abs(momentum_raw) * 20, 1.0) +
        0.20 * 1.0
    )
    dir_raw = trend_raw * 0.25 + momentum_raw * 0.10 + ema_dir * 0.20
    direction = np.sign(dir_raw) if abs(dir_raw) > 1e-9 else 0
    return float(np.clip(direction * quality, -1.0, 1.0))


def get_level_params(score: float, adx: float, ker: float, config: dict = None) -> dict:
    if config is None:
        from config import DEFAULT_PARAMS as DEFAULT
        config = DEFAULT
    abs_score = abs(score)

    if abs_score >= config.get('min_score_s', 0.60) and adx >= config.get('adx_threshold_s', 38) and ker >= config.get('ker_threshold_s', 0.65):
        level, sl_mult, tp_mult = 'S-TIER', config.get('sl_mult_s', 0.6), config.get('tp_mult_s', 2.5)
        trailing_dist, be_trigger = config.get('trailing_distance_s', 0.0008), config.get('be_trigger_s', 0.0015)
    elif abs_score >= config.get('min_score_a', 0.45) and adx >= config.get('adx_threshold_a', 30) and ker >= config.get('ker_threshold_a', 0.55):
        level, sl_mult, tp_mult = 'A-TIER', config.get('sl_mult_a', 0.5), config.get('tp_mult_a', 1.8)
        trailing_dist, be_trigger = config.get('trailing_distance_a', 0.0010), config.get('be_trigger_a', 0.0020)
    elif abs_score >= config.get('min_score', 0.35) and adx >= config.get('adx_threshold', 22) and ker >= config.get('ker_threshold', 0.42):
        level, sl_mult, tp_mult = 'B-TIER', config.get('sl_mult_b', 0.4), config.get('tp_mult_b', 1.2)
        trailing_dist, be_trigger = config.get('trailing_distance_b', 0.0012), config.get('be_trigger_b', 0.0025)
    else:
        level, sl_mult, tp_mult, trailing_dist, be_trigger = 'NO-TIER', 0.4, 1.2, 0.0012, 0.0025

    return {'level': level, 'sl_mult': sl_mult, 'tp_mult': tp_mult,
            'trailing_distance': trailing_dist, 'be_trigger': be_trigger,
            'be_buffer': config.get('be_buffer', 0.0005)}


def estimate_mfe(df, regime, atr_pct, volume_ratio) -> float:
    base = atr_pct * 1.5
    factors = {'Expansión': 1.5, 'Tendencia Fuerte': 1.3, 'Tendencia Débil': 1.1, 'Chop': 0.5}
    return base * factors.get(regime, 1.0) * min(volume_ratio / 1.2, 1.5)


def estimate_persistence(score, adx, ker, regime) -> float:
    base = 50 + 20 * (abs(score) / 0.6) + 10 * (adx / 40) + 10 * (ker / 0.6)
    if regime in ['Tendencia Fuerte', 'Expansión']: base += 10
    elif regime == 'Chop': base -= 20
    return max(0, min(100, base))
