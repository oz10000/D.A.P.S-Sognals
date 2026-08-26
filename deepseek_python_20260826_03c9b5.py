# config.py
import os

# ============================================================
# PROYECTO
# ============================================================
PROJECT_NAME = "DAPS Ω — Trading Engine"
VERSION = "1.0.0"

# ============================================================
# ZONA HORARIA
# ============================================================
TIMEZONE = 'America/Argentina/Buenos_Aires'

# ============================================================
# CONSTANTES PRINCIPALES
# ============================================================
TIMEFRAME = '5m'
INITIAL_CAPITAL = 10000.0
MAX_HOLD = 60                     # minutos
RISK_PER_TRADE = 0.01
LEVERAGE = 1

# ============================================================
# DIRECTORIOS
# ============================================================
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(ROOT_DIR, 'cache')
DATA_DIR = os.path.join(ROOT_DIR, 'data')
LOGS_DIR = os.path.join(ROOT_DIR, 'logs')

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# ============================================================
# TODOS LOS ACTIVOS — FIAT + CRYPTO + INDICES + COMMODITIES
# ============================================================

# ---------- CRYPTO (Top 30) ----------
CRYPTO_SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'BNB/USDT', 'DOT/USDT', 'LINK/USDT', 'AVAX/USDT', 'UNI/USDT',
    'ATOM/USDT', 'MATIC/USDT', 'LTC/USDT', 'ETC/USDT', 'VET/USDT',
    'ALGO/USDT', 'FTM/USDT', 'NEAR/USDT', 'APT/USDT', 'ARB/USDT',
    'OP/USDT', 'INJ/USDT', 'SEI/USDT', 'SUI/USDT', 'APE/USDT',
    'DOGE/USDT', 'PEPE/USDT', 'WIF/USDT', 'BONK/USDT', 'FLOKI/USDT'
]

# ---------- FIAT CURRENCIES (vs USDT) ----------
FIAT_SYMBOLS = [
    'EUR/USDT', 'GBP/USDT', 'JPY/USDT', 'CHF/USDT', 'CAD/USDT',
    'AUD/USDT', 'NZD/USDT', 'CNY/USDT', 'MXN/USDT', 'BRL/USDT',
    'ARS/USDT', 'CLP/USDT', 'COP/USDT', 'PEN/USDT', 'UYU/USDT',
    'KRW/USDT', 'SGD/USDT', 'HKD/USDT', 'SEK/USDT', 'NOK/USDT',
    'DKK/USDT', 'ZAR/USDT', 'TRY/USDT', 'RUB/USDT', 'INR/USDT',
    'IDR/USDT', 'PHP/USDT', 'MYR/USDT', 'THB/USDT', 'VND/USDT'
]

# ---------- INDICES ----------
INDEX_SYMBOLS = [
    'SPX/USDT',      # S&P 500
    'NDX/USDT',      # NASDAQ
    'DJI/USDT',      # Dow Jones
    'DAX/USDT',      # DAX
    'FTSE/USDT',     # FTSE 100
    'NIKKEI/USDT',   # Nikkei 225
    'HSI/USDT',      # Hang Seng
    'ASX/USDT',      # ASX 200
    'IBOV/USDT',     # Bovespa
]

# ---------- COMMODITIES ----------
COMMODITY_SYMBOLS = [
    'XAU/USDT',      # Gold
    'XAG/USDT',      # Silver
    'XPT/USDT',      # Platinum
    'XPD/USDT',      # Palladium
    'WTI/USDT',      # Crude Oil
    'BRENT/USDT',    # Brent Oil
    'NG/USDT',       # Natural Gas
]

# ---------- TODOS LOS ACTIVOS JUNTOS ----------
SYMBOLS = CRYPTO_SYMBOLS + FIAT_SYMBOLS + INDEX_SYMBOLS + COMMODITY_SYMBOLS

# ============================================================
# EXCHANGES (fallback prioritario)
# ============================================================
EXCHANGE_PRIORITY = [
    'binance',
    'okx',
    'kucoin',
    'mexc',
    'kraken',
    'bybit',
    'gateio',
    'bitget'
]

# ============================================================
# PARÁMETROS DE ESTRATEGIA OPTIMIZADOS
# ============================================================
MIN_SCORE = 0.35                  # Score mínimo (B-TIER)
MIN_SCORE_A = 0.45                # Score mínimo (A-TIER)
MIN_SCORE_S = 0.60                # Score mínimo (S-TIER)

ADX_THRESHOLD = 22                # ADX mínimo (B-TIER)
ADX_THRESHOLD_A = 30              # ADX mínimo (A-TIER)
ADX_THRESHOLD_S = 38              # ADX mínimo (S-TIER)

KER_THRESHOLD = 0.42              # KER mínimo (B-TIER)
KER_THRESHOLD_A = 0.55            # KER mínimo (A-TIER)
KER_THRESHOLD_S = 0.65            # KER mínimo (S-TIER)

SL_MULT_B = 0.4                   # SL = 0.4 * ATR (B-TIER)
SL_MULT_A = 0.5                   # SL = 0.5 * ATR (A-TIER)
SL_MULT_S = 0.6                   # SL = 0.6 * ATR (S-TIER)

TP_MULT_B = 1.2                   # TP = 1.2 * ATR (B-TIER)
TP_MULT_A = 1.8                   # TP = 1.8 * ATR (A-TIER)
TP_MULT_S = 2.5                   # TP = 2.5 * ATR (S-TIER)

TRAILING_DISTANCE_B = 0.0012      # 0.12% (B-TIER)
TRAILING_DISTANCE_A = 0.0010      # 0.10% (A-TIER)
TRAILING_DISTANCE_S = 0.0008      # 0.08% (S-TIER)

BE_TRIGGER_B = 0.0025             # 0.25% (B-TIER)
BE_TRIGGER_A = 0.0020             # 0.20% (A-TIER)
BE_TRIGGER_S = 0.0015             # 0.15% (S-TIER)

BE_BUFFER = 0.0005                # 0.05%

# ============================================================
# PARÁMETROS POR ACTIVO (optimizados)
# ============================================================
ASSET_PARAMS = {
    # Crypto
    'BTC/USDT': {'adx_opt': 21, 'ker_opt': 14, 'ema_opt': 34, 'atr_opt': 16},
    'ETH/USDT': {'adx_opt': 16, 'ker_opt': 12, 'ema_opt': 21, 'atr_opt': 14},
    'SOL/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'XRP/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'ADA/USDT': {'adx_opt': 12, 'ker_opt': 9, 'ema_opt': 17, 'atr_opt': 14},
    # Fiat
    'EUR/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 12},
    'GBP/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 12},
    'JPY/USDT': {'adx_opt': 12, 'ker_opt': 8, 'ema_opt': 17, 'atr_opt': 10},
    'CHF/USDT': {'adx_opt': 16, 'ker_opt': 10, 'ema_opt': 25, 'atr_opt': 14},
    'CAD/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 12},
    'AUD/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 12},
    'ARS/USDT': {'adx_opt': 28, 'ker_opt': 18, 'ema_opt': 55, 'atr_opt': 20},
    'BRL/USDT': {'adx_opt': 18, 'ker_opt': 12, 'ema_opt': 25, 'atr_opt': 16},
    'MXN/USDT': {'adx_opt': 16, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    # Indices
    'SPX/USDT': {'adx_opt': 20, 'ker_opt': 14, 'ema_opt': 30, 'atr_opt': 14},
    'NDX/USDT': {'adx_opt': 18, 'ker_opt': 12, 'ema_opt': 25, 'atr_opt': 14},
    'DJI/USDT': {'adx_opt': 20, 'ker_opt': 14, 'ema_opt': 30, 'atr_opt': 14},
    'DAX/USDT': {'adx_opt': 16, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'NIKKEI/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    # Commodities
    'XAU/USDT': {'adx_opt': 18, 'ker_opt': 12, 'ema_opt': 25, 'atr_opt': 14},
    'XAG/USDT': {'adx_opt': 16, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 12},
    'WTI/USDT': {'adx_opt': 16, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'BRENT/USDT': {'adx_opt': 16, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
}

# ============================================================
# PARÁMETROS POR DEFECTO
# ============================================================
DEFAULT_PARAMS = {
    'min_score': MIN_SCORE,
    'min_score_a': MIN_SCORE_A,
    'min_score_s': MIN_SCORE_S,
    'adx_threshold': ADX_THRESHOLD,
    'adx_threshold_a': ADX_THRESHOLD_A,
    'adx_threshold_s': ADX_THRESHOLD_S,
    'ker_threshold': KER_THRESHOLD,
    'ker_threshold_a': KER_THRESHOLD_A,
    'ker_threshold_s': KER_THRESHOLD_S,
    'sl_mult_b': SL_MULT_B,
    'sl_mult_a': SL_MULT_A,
    'sl_mult_s': SL_MULT_S,
    'tp_mult_b': TP_MULT_B,
    'tp_mult_a': TP_MULT_A,
    'tp_mult_s': TP_MULT_S,
    'trailing_distance_b': TRAILING_DISTANCE_B,
    'trailing_distance_a': TRAILING_DISTANCE_A,
    'trailing_distance_s': TRAILING_DISTANCE_S,
    'be_trigger_b': BE_TRIGGER_B,
    'be_trigger_a': BE_TRIGGER_A,
    'be_trigger_s': BE_TRIGGER_S,
    'be_buffer': BE_BUFFER,
    'max_hold': MAX_HOLD,
    'risk_per_trade': RISK_PER_TRADE,
    'leverage': LEVERAGE,
}