# config.py
import os

# ============================================================
# PROYECTO
# ============================================================
PROJECT_NAME = "DAPS Ω — Trading Engine"
VERSION = "2.0.0"

# ============================================================
# ZONA HORARIA
# ============================================================
TIMEZONE = 'America/Argentina/Buenos_Aires'

# ============================================================
# CONSTANTES PRINCIPALES
# ============================================================
TIMEFRAME = '5m'
INITIAL_CAPITAL = 10000.0
MAX_HOLD = 60
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
# ACTIVOS (52 activos de alta liquidez en Binance/Bybit)
# Basado en FUZZANDTRUSH — probado y validado
# ============================================================
SYMBOLS = [
    # Top 10 por capitalización
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOT/USDT', 'LINK/USDT', 'AVAX/USDT', 'UNI/USDT', 'ATOM/USDT',

    # Capa 1 y Capa 2 consolidados
    'BNB/USDT', 'MATIC/USDT', 'LTC/USDT', 'ETC/USDT', 'VET/USDT',
    'ALGO/USDT', 'FTM/USDT', 'NEAR/USDT', 'APT/USDT', 'ARB/USDT',
    'OP/USDT', 'INJ/USDT', 'SEI/USDT', 'SUI/USDT', 'APE/USDT',

    # Meme coins con alta liquidez
    'DOGE/USDT', 'PEPE/USDT', 'WIF/USDT', 'BONK/USDT', 'FLOKI/USDT',

    # DeFi y ecosistemas
    'AAVE/USDT', 'MKR/USDT', 'CRV/USDT', 'LDO/USDT', 'RNDR/USDT',

    # Gaming y metaverso
    'SAND/USDT', 'MANA/USDT', 'GALA/USDT', 'AXS/USDT', 'ILV/USDT',

    # Almacenamiento y computación
    'FIL/USDT', 'AR/USDT', 'ICP/USDT',

    # Nuevos listados de Binance (confirmados)
    'COOKIE/USDT', 'ALCH/USDT', 'SWARMS/USDT', 'AERO/USDT',
    'ETHW/USDT', 'PONKE/USDT', 'SLERF/USDT', 'KMNO/USDT',
    '1000X/USDT', 'GRIFFAIN/USDT', 'MORPHO/USDT', '1000000MOG/USDT',
    '1000WHY/USDT', 'SWELL/USDT'
]

# ============================================================
# EXCHANGES
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
# PARÁMETROS DE ESTRATEGIA (OPTIMIZADOS)
# ============================================================
MIN_SCORE = 0.50
MIN_SCORE_A = 0.45
MIN_SCORE_S = 0.60

ADX_THRESHOLD = 22
ADX_THRESHOLD_A = 30
ADX_THRESHOLD_S = 38

KER_THRESHOLD = 0.42
KER_THRESHOLD_A = 0.55
KER_THRESHOLD_S = 0.65

SL_MULT_B = 0.4
SL_MULT_A = 0.5
SL_MULT_S = 0.6

TP_MULT_B = 1.2
TP_MULT_A = 1.8
TP_MULT_S = 2.5

TRAILING_DISTANCE_B = 0.0012
TRAILING_DISTANCE_A = 0.0010
TRAILING_DISTANCE_S = 0.0008

BE_TRIGGER_B = 0.0025
BE_TRIGGER_A = 0.0020
BE_TRIGGER_S = 0.0015

BE_BUFFER = 0.0005

# ============================================================
# PARÁMETROS POR ACTIVO (ASSET_PARAMS)
# Si un activo no está en este diccionario, se usan valores por defecto.
# ============================================================
ASSET_PARAMS = {
    'BTC/USDT': {'adx_opt': 21, 'ker_opt': 14, 'ema_opt': 34, 'atr_opt': 16},
    'ETH/USDT': {'adx_opt': 16, 'ker_opt': 12, 'ema_opt': 21, 'atr_opt': 14},
    'SOL/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'XRP/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'ADA/USDT': {'adx_opt': 12, 'ker_opt': 9, 'ema_opt': 17, 'atr_opt': 14},
    'BNB/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'DOT/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'LINK/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'AVAX/USDT': {'adx_opt': 12, 'ker_opt': 9, 'ema_opt': 17, 'atr_opt': 12},
    'UNI/USDT': {'adx_opt': 12, 'ker_opt': 9, 'ema_opt': 17, 'atr_opt': 12},
    'ATOM/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'MATIC/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'LTC/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'ETC/USDT': {'adx_opt': 12, 'ker_opt': 9, 'ema_opt': 17, 'atr_opt': 12},
    'VET/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'ALGO/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'FTM/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'NEAR/USDT': {'adx_opt': 12, 'ker_opt': 9, 'ema_opt': 17, 'atr_opt': 12},
    'APT/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'ARB/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'OP/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'INJ/USDT': {'adx_opt': 12, 'ker_opt': 9, 'ema_opt': 17, 'atr_opt': 12},
    'SEI/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'SUI/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'APE/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'DOGE/USDT': {'adx_opt': 8, 'ker_opt': 6, 'ema_opt': 10, 'atr_opt': 8},
    'PEPE/USDT': {'adx_opt': 8, 'ker_opt': 6, 'ema_opt': 10, 'atr_opt': 8},
    'WIF/USDT': {'adx_opt': 8, 'ker_opt': 6, 'ema_opt': 10, 'atr_opt': 8},
    'BONK/USDT': {'adx_opt': 8, 'ker_opt': 6, 'ema_opt': 10, 'atr_opt': 8},
    'FLOKI/USDT': {'adx_opt': 8, 'ker_opt': 6, 'ema_opt': 10, 'atr_opt': 8},
    'AAVE/USDT': {'adx_opt': 12, 'ker_opt': 9, 'ema_opt': 17, 'atr_opt': 12},
    'MKR/USDT': {'adx_opt': 12, 'ker_opt': 9, 'ema_opt': 17, 'atr_opt': 12},
    'CRV/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'LDO/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'RNDR/USDT': {'adx_opt': 12, 'ker_opt': 9, 'ema_opt': 17, 'atr_opt': 12},
    'SAND/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'MANA/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'GALA/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'AXS/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'ILV/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'FIL/USDT': {'adx_opt': 12, 'ker_opt': 9, 'ema_opt': 17, 'atr_opt': 12},
    'AR/USDT': {'adx_opt': 10, 'ker_opt': 8, 'ema_opt': 13, 'atr_opt': 10},
    'ICP/USDT': {'adx_opt': 12, 'ker_opt': 9, 'ema_opt': 17, 'atr_opt': 12},
    'COOKIE/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'ALCH/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'SWARMS/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'AERO/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'ETHW/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'PONKE/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'SLERF/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'KMNO/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    '1000X/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'GRIFFAIN/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'MORPHO/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    '1000000MOG/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    '1000WHY/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'SWELL/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
}

# ============================================================
# PARÁMETROS POR DEFECTO (DEFAULT_PARAMS)
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
