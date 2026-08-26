# core_engine.py
import pandas as pd
import numpy as np
import logging
from config import ASSET_PARAMS, DEFAULT_PARAMS

logger = logging.getLogger(__name__)


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ADX (Average Directional Index)"""
    if df.empty or len(df) < period:
        return pd.Series(0.0, index=df.index)

    high, low, close = df['high'], df['low'], df['close']

    tr = pd.DataFrame({
        'hl': high - low,
        'hc': (high - close.shift()).abs(),
        'lc': (low - close.shift()).abs()
    }).max(axis=1)

    plus_dm = high.diff()
    minus_dm = low.diff().abs() * -1
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = minus_dm.abs()

    atr = tr.rolling(period).mean()
    atr = atr.replace(0, np.nan)

    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(period).mean()
    adx = adx.fillna(0).replace([np.inf, -np.inf], 0)

    return adx


def compute_ker(df: pd.DataFrame, period: int = 10) -> pd.Series:
    """KER (Kaufman Efficiency Ratio)"""
    if df.empty or len(df) < period:
        return pd.Series(0.0, index=df.index)

    close = df['close']
    change = abs(close.diff(period))
    volatility = close.diff().abs().rolling(period).sum()
    ker = change / (volatility + 1e-9)
    ker = ker.fillna(0).replace([np.inf, -np.inf], 0)

    return ker


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR (Average True Range)"""
    if df.empty or len(df) < period:
        return pd.Series(0.0, index=df.index)

    high, low, close = df['high'], df['low'], df['close']

    tr = pd.DataFrame({
        'hl': high - low,
        'hc': (high - close.shift()).abs(),
        'lc': (low - close.shift()).abs()
    }).max(axis=1)

    atr = tr.rolling(period).mean()
    atr = atr.fillna(0).replace([np.inf, -np.inf], 0)

    return atr


def compute_ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """EMA (Exponential Moving Average)"""
    if df.empty:
        return pd.Series(0.0, index=df.index)
    return df['close'].ewm(span=period, adjust=False).mean()


def compute_regime(df: pd.DataFrame, adx_val: float, ker_val: float, atr_pct: float) -> str:
    """Clasifica régimen de mercado"""
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
    """Score compuesto [-1, 1] con parámetros optimizados por activo"""
    if df.empty or len(df) < 30:
        return 0.0

    close = df['close']
    last_close = close.iloc[-1]

    # Obtener parámetros del activo o usar defaults
    if symbol and symbol in ASSET_PARAMS:
        params = ASSET_PARAMS[symbol]
        ema_period = params.get('ema_opt', 22)
        atr_period = params.get('atr_opt', 14)
        adx_period = params.get('adx_opt', 14)
        ker_period = params.get('ker_opt', 10)
    else:
        ema_period = 22
        atr_period = 14
        adx_period = 14
        ker_period = 10

    # 1. Trend (25%)
    ema = close.ewm(span=ema_period).mean()
    ema_slope = (ema.iloc[-1] - ema.iloc[-5]) / ema.iloc[-5] if len(ema) >= 5 else 0
    trend_score = np.clip(ema_slope * 10, -1, 1) * 0.25

    # 2. Strength (20%)
    adx_series = compute_adx(df, adx_period)
    adx_val = adx_series.iloc[-1] if not adx_series.empty else 0
    strength_score = np.clip(adx_val / 40, 0, 1) * 0.20

    # 3. KER (15%)
    ker_series = compute_ker(df, ker_period)
    ker_val = ker_series.iloc[-1] if not ker_series.empty else 0
    ker_score = np.clip(ker_val, 0, 1) * 0.15

    # 4. ATR relativo (10%)
    atr_series = compute_atr(df, atr_period)
    atr_val = atr_series.iloc[-1] if not atr_series.empty else 0
    atr_ma = atr_series.rolling(20).mean().iloc[-1] if len(atr_series) >= 20 else atr_val
    atr_rel = atr_val / atr_ma if atr_ma > 0 else 1
    atr_score = np.clip(atr_rel, 0.5, 2) * 0.10

    # 5. Momentum (10%)
    momentum = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] if len(close) >= 5 else 0
    momentum_score = np.clip(momentum * 20, -1, 1) * 0.10

    # 6. Otros (20%)
    ema_50 = close.ewm(span=50).mean()
    ema_direction = 1 if last_close > ema_50.iloc[-1] else -1
    ema_direction_score = ema_direction * 0.20

    # Score total
    score = (trend_score + strength_score + ker_score +
             atr_score + momentum_score + ema_direction_score)

    return np.clip(score, -1, 1)


def get_level_params(score: float, adx: float, ker: float, config: dict = None) -> dict:
    """Determina el nivel de la señal y sus parámetros"""
    if config is None:
        from config import DEFAULT_PARAMS as DEFAULT
        config = DEFAULT

    if score >= config.get('min_score_s', 0.60) and adx >= config.get('adx_threshold_s', 38) and ker >= config.get('ker_threshold_s', 0.65):
        level = 'S-TIER'
        sl_mult = config.get('sl_mult_s', 0.6)
        tp_mult = config.get('tp_mult_s', 2.5)
        trailing_dist = config.get('trailing_distance_s', 0.0008)
        be_trigger = config.get('be_trigger_s', 0.0015)
    elif score >= config.get('min_score_a', 0.45) and adx >= config.get('adx_threshold_a', 30) and ker >= config.get('ker_threshold_a', 0.55):
        level = 'A-TIER'
        sl_mult = config.get('sl_mult_a', 0.5)
        tp_mult = config.get('tp_mult_a', 1.8)
        trailing_dist = config.get('trailing_distance_a', 0.0010)
        be_trigger = config.get('be_trigger_a', 0.0020)
    elif score >= config.get('min_score', 0.35) and adx >= config.get('adx_threshold', 22) and ker >= config.get('ker_threshold', 0.42):
        level = 'B-TIER'
        sl_mult = config.get('sl_mult_b', 0.4)
        tp_mult = config.get('tp_mult_b', 1.2)
        trailing_dist = config.get('trailing_distance_b', 0.0012)
        be_trigger = config.get('be_trigger_b', 0.0025)
    else:
        level = 'NO-TIER'
        sl_mult = 0.4
        tp_mult = 1.2
        trailing_dist = 0.0012
        be_trigger = 0.0025

    return {
        'level': level,
        'sl_mult': sl_mult,
        'tp_mult': tp_mult,
        'trailing_distance': trailing_dist,
        'be_trigger': be_trigger,
        'be_buffer': config.get('be_buffer', 0.0005)
    }


def estimate_mfe(df: pd.DataFrame, regime: str, atr_pct: float, volume_ratio: float) -> float:
    """Estima el MFE (Maximum Favorable Excursion) esperado"""
    base = atr_pct * 1.5
    regime_factors = {
        'Expansión': 1.5,
        'Tendencia Fuerte': 1.3,
        'Tendencia Débil': 1.1,
        'Chop': 0.5
    }
    factor = regime_factors.get(regime, 1.0)
    volume_factor = min(volume_ratio / 1.2, 1.5)
    return base * factor * volume_factor


def estimate_persistence(score: float, adx: float, ker: float, regime: str) -> float:
    """Estima la persistencia de la señal (0-100)"""
    base = 50
    base += 20 * (score / 0.6)
    base += 10 * (adx / 40)
    base += 10 * (ker / 0.6)
    if regime in ['Tendencia Fuerte', 'Expansión']:
        base += 10
    elif regime == 'Chop':
        base -= 20
    return max(0, min(100, base))
