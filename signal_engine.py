# signal_engine.py
# ============================================================
# Generador de señales.
# Auditoría forense aplicada:
#   P0-5: eliminación de look-ahead (uso de df.iloc[:-1])
#   P0-3: score simétrico (uso de score firmado)
#   P1-6: eliminación de trailing_activation huérfano
#   P1-9: penalización explícita de régimen Chop en confidence
# ============================================================
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from core_engine import (
    compute_adx, compute_ker, compute_atr, compute_ema,
    compute_regime, compute_pidelta_score, get_level_params,
    estimate_mfe, estimate_persistence,
)
from config import DEFAULT_PARAMS, ASSET_PARAMS


class Signal:
    """Genera señal para un activo con todos los indicadores y ranking."""

    def __init__(self, symbol: str, df: pd.DataFrame, params: dict = None):
        self.symbol = symbol
        self.params = params or DEFAULT_PARAMS

        # ---- P0-5 FIX: eliminar vela en formación (look-ahead bias) ----
        if df is not None and len(df) > 1:
            self.df = df.iloc[:-1]
        else:
            self.df = df

        # Inicialización de variables (evita AttributeError en to_dict)
        self.score = 0.0
        self.adx = 0.0
        self.ker = 0.0
        self.atr_pct = 0.0
        self.atr_abs = 0.0
        self.regime = 'Chop'
        self.is_valid = False
        self.reason = "No evaluado"
        self.direction = None
        self.confidence = 0.0
        self.entry_price = 0.0
        self.sl_price = 0.0
        self.tp_price = 0.0
        self.tp_percent = 0.0
        self.sl_percent = 0.0
        self.trailing_distance = 0.0
        self.break_even_trigger = 0.0
        self.break_even_buffer = 0.0
        self.max_hold_minutes = 0
        self.ema15 = 0.0
        self.ema50 = 0.0
        self.volume_ratio = 0.0
        self.mfe_expected = 0.0
        self.max_price_estimate = 0.0
        self.min_price_estimate = 0.0
        self.estimated_time_to_trade = 0
        self.level = 'NO-TIER'
        self.persistence = 0.0

        if self.df is not None and not self.df.empty and len(self.df) > 30:
            self._compute()

    # --------------------------------------------------------
    # CÁLCULO PRINCIPAL
    # --------------------------------------------------------
    def _compute(self):
        p = self.params
        close = self.df['close'].iloc[-1]
        volume = self.df['volume'].iloc[-1]

        # Parámetros por activo
        if self.symbol in ASSET_PARAMS:
            asset_p = ASSET_PARAMS[self.symbol]
            adx_period = asset_p.get('adx_opt', 14)
            ker_period = asset_p.get('ker_opt', 10)
            atr_period = asset_p.get('atr_opt', 14)
        else:
            adx_period = 14
            ker_period = 10
            atr_period = 14

        # Indicadores
        self.score = compute_pidelta_score(self.df, self.symbol)

        adx_series = compute_adx(self.df, adx_period)
        self.adx = float(adx_series.iloc[-1]) if not adx_series.empty else 0.0

        ker_series = compute_ker(self.df, ker_period)
        self.ker = float(ker_series.iloc[-1]) if not ker_series.empty else 0.0

        atr_series = compute_atr(self.df, atr_period)
        atr_val = float(atr_series.iloc[-1]) if not atr_series.empty else 0.0
        self.atr_abs = atr_val
        self.atr_pct = atr_val / close if close > 0 else 0.0

        self.regime = compute_regime(self.df, self.adx, self.ker, self.atr_pct)

        self.ema15 = float(compute_ema(self.df, 15).iloc[-1])
        self.ema50 = float(compute_ema(self.df, 50).iloc[-1])

        avg_volume = self.df['volume'].rolling(20).mean().iloc[-1]
        self.volume_ratio = volume / avg_volume if avg_volume > 0 else 0.0

        # Dirección
        self.direction = 'LONG' if self.score > 0 else 'SHORT'

        # Nivel — pasamos score firmado; get_level_params usa abs() internamente
        level_params = get_level_params(self.score, self.adx, self.ker, p)
        self.level = level_params['level']

        # --------------------------------------------------
        # VALIDACIÓN
        # --------------------------------------------------
        self.is_valid = True
        self.reason = "OK"

        if self.level == 'NO-TIER':
            self.is_valid = False
            self.reason = f"NO-TIER: score {self.score:.2f}"
        elif self.regime == 'Chop':
            self.is_valid = False
            self.reason = "Régimen Chop"
        else:
            # Filtro EMA15 — alineación con tendencia
            if self.direction == 'LONG' and close < self.ema15:
                self.is_valid = False
                self.reason = "Precio < EMA15"
            elif self.direction == 'SHORT' and close > self.ema15:
                self.is_valid = False
                self.reason = "Precio > EMA15"

        # --------------------------------------------------
        # PRECIOS
        # --------------------------------------------------
        self.entry_price = close
        sl_mult = level_params['sl_mult']
        tp_mult = level_params['tp_mult']

        if self.direction == 'LONG':
            self.sl_price = close * (1 - sl_mult * self.atr_pct)
            self.tp_price = close * (1 + tp_mult * self.atr_pct)
        else:
            self.sl_price = close * (1 + sl_mult * self.atr_pct)
            self.tp_price = close * (1 - tp_mult * self.atr_pct)

        self.tp_percent = (self.tp_price / self.entry_price - 1) * 100
        self.sl_percent = (self.sl_price / self.entry_price - 1) * 100

        self.trailing_distance = level_params['trailing_distance']
        self.break_even_trigger = level_params['be_trigger']
        self.break_even_buffer = level_params['be_buffer']
        self.max_hold_minutes = p.get('max_hold', 60)

        # --------------------------------------------------
        # CONFIANZA
        # --------------------------------------------------
        self.confidence = (
            30
            + 20 * (self.adx / 40)
            + 20 * (self.ker / 0.6)
            + 15 * (abs(self.score) / 0.6)
            + 15 * min(self.volume_ratio / 1.5, 1)
        )
        self.confidence = min(max(self.confidence, 0), 100)

        # P1-9 FIX: penalización explícita en Chop
        if self.regime == 'Chop':
            self.confidence *= 0.70

        # --------------------------------------------------
        # MFE / PERSISTENCIA
        # --------------------------------------------------
        self.mfe_expected = estimate_mfe(
            self.df, self.regime, self.atr_pct, self.volume_ratio
        )
        self.persistence = estimate_persistence(
            abs(self.score), self.adx, self.ker, self.regime
        )

        mfe = self.mfe_expected
        if self.direction == 'LONG':
            self.max_price_estimate = close * (1 + mfe * 1.5)
            self.min_price_estimate = close * (1 - mfe * 0.5)
        else:
            self.max_price_estimate = close * (1 + mfe * 0.5)
            self.min_price_estimate = close * (1 - mfe * 1.5)

        self.estimated_time_to_trade = self._estimate_time_to_trade()

    # --------------------------------------------------------
    # ESTIMACIÓN DE TIEMPO
    # --------------------------------------------------------
    def _estimate_time_to_trade(self) -> int:
        if self.is_valid:
            if self.confidence > 80:
                return 5 + int((100 - self.confidence) / 10)
            return 10 + int((80 - self.confidence) / 5)
        if abs(self.score) > 0.5:
            return 15 + int((1 - abs(self.score)) * 30)
        return 45 + int((1 - abs(self.score)) * 60)

    # --------------------------------------------------------
    # EXPORTACIÓN
    # --------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'score': self.score,
            'adx': self.adx,
            'ker': self.ker,
            'atr_pct': self.atr_pct,
            'atr_abs': self.atr_abs,
            'regime': self.regime,
            'direction': self.direction,
            'is_valid': self.is_valid,
            'reason': self.reason,
            'confidence': self.confidence,
            'entry_price': self.entry_price,
            'sl_price': self.sl_price,
            'tp_price': self.tp_price,
            'tp_percent': self.tp_percent,
            'sl_percent': self.sl_percent,
            'trailing_distance': self.trailing_distance,
            'break_even_trigger': self.break_even_trigger,
            'break_even_buffer': self.break_even_buffer,
            'max_hold_minutes': self.max_hold_minutes,
            'ema15': self.ema15,
            'ema50': self.ema50,
            'volume_ratio': self.volume_ratio,
            'mfe_expected': self.mfe_expected,
            'max_price_estimate': self.max_price_estimate,
            'min_price_estimate': self.min_price_estimate,
            'estimated_time_to_trade': self.estimated_time_to_trade,
            'level': self.level,
            'persistence': self.persistence,
            'tp_percent_formatted': f"{self.tp_percent:.2f}%",
            'sl_percent_formatted': f"{self.sl_percent:.2f}%",
            'mfe_expected_formatted': f"{self.mfe_expected * 100:.2f}%",
        }


# ============================================================
# RANKING
# ============================================================
def rank_signals(signals: list) -> list:
    """Ranking simétrico por |score|. Aprobadas primero, luego no aprobadas."""
    approved = [s for s in signals if s.get('is_valid', False)]
    not_approved = [s for s in signals if not s.get('is_valid', False)]

    approved_sorted = sorted(approved, key=lambda x: abs(x['score']), reverse=True)
    not_approved_sorted = sorted(not_approved, key=lambda x: abs(x['score']), reverse=True)

    ranked = []
    rank = 1
    for s in approved_sorted:
        s['rank'] = rank
        s['rank_label'] = f"#{rank} APROBADA"
        ranked.append(s)
        rank += 1
    for s in not_approved_sorted:
        s['rank'] = rank
        s['rank_label'] = f"#{rank} (no aprobada)"
        ranked.append(s)
        rank += 1

    return ranked


# ============================================================
# CLASIFICACIÓN POR DIRECCIÓN
# ============================================================
def classify_by_direction(signals: list) -> dict:
    result = {
        'long_valid': [],
        'long_invalid': [],
        'short_valid': [],
        'short_invalid': [],
        'all': signals,
    }

    for s in signals:
        d = s.get('direction')
        valid = s.get('is_valid', False)
        if d == 'LONG':
            (result['long_valid'] if valid else result['long_invalid']).append(s)
        elif d == 'SHORT':
            (result['short_valid'] if valid else result['short_invalid']).append(s)

    for key in ['long_valid', 'long_invalid', 'short_valid', 'short_invalid']:
        result[key] = sorted(result[key], key=lambda x: abs(x['score']), reverse=True)

    return result
