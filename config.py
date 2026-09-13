# config.py
# ============================================================
# DAPS Ω — Trading Engine · Configuración central
# Auditoría forense aplicada — v2.1.0
# ============================================================
import os

# ============================================================
# PROYECTO
# ============================================================
PROJECT_NAME = "DAPS Ω — Trading Engine"
VERSION = "2.1.0"

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
# ACTIVOS — LIMPIADOS Y VERIFICADOS
# Símbolos fantasma eliminados: 1000X, 1000000MOG, 1000WHY,
# COOKIE, ALCH, SWARMS, PONKE, SLERF, GRIFFAIN, KMNO, AERO,
# ETHW, MORPHO, SWELL, MATIC (renombrado POL), FTM (→S),
# RNDR (→RENDER), ILV (baja liquidez)
# ============================================================
SYMBOLS = [
    # Top 10 por capitalización
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOT/USDT', 'LINK/USDT', 'AVAX/USDT', 'UNI/USDT', 'ATOM/USDT',

    # Capa 1 y Capa 2 consolidadas
    'BNB/USDT', 'LTC/USDT', 'ETC/USDT', 'NEAR/USDT', 'APT/USDT',
    'ARB/USDT', 'OP/USDT', 'INJ/USDT', 'SUI/USDT', 'APE/USDT',
    'SEI/USDT', 'VET/USDT', 'ALGO/USDT',

    # Meme coins con liquidez verificada
    'DOGE/USDT', 'PEPE/USDT', 'WIF/USDT', 'BONK/USDT', 'FLOKI/USDT',

    # DeFi y ecosistemas
    'AAVE/USDT', 'MKR/USDT', 'CRV/USDT', 'LDO/USDT',

    # Gaming y metaverso
    'SAND/USDT', 'MANA/USDT', 'GALA/USDT', 'AXS/USDT',

    # Almacenamiento y computación
    'FIL/USDT', 'AR/USDT', 'ICP/USDT',
]

# ============================================================
# EXCHANGES (fallback en cascada)
# ============================================================
EXCHANGE_PRIORITY = [
    'binance',
    'okx',
    'kucoin',
    'mexc',
    'kraken',
    'bybit',
    'gateio',
    'bitget',
]

# ============================================================
# PARÁMETROS DE ESTRATEGIA (OPTIMIZADOS)
# ============================================================
MIN_SCORE = 0.35
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
# Solo para activos presentes en SYMBOLS.
# ============================================================
ASSET_PARAMS = {
    'BTC/USDT':  {'adx_opt': 21, 'ker_opt': 14, 'ema_opt': 34, 'atr_opt': 16},
    'ETH/USDT':  {'adx_opt': 16, 'ker_opt': 12, 'ema_opt': 21, 'atr_opt': 14},
    'SOL/USDT':  {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'XRP/USDT':  {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'ADA/USDT':  {'adx_opt': 12, 'ker_opt':  9, 'ema_opt': 17, 'atr_opt': 14},
    'BNB/USDT':  {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'DOT/USDT':  {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'LINK/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'AVAX/USDT': {'adx_opt': 12, 'ker_opt':  9, 'ema_opt': 17, 'atr_opt': 12},
    'UNI/USDT':  {'adx_opt': 12, 'ker_opt':  9, 'ema_opt': 17, 'atr_opt': 12},
    'ATOM/USDT': {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'LTC/USDT':  {'adx_opt': 14, 'ker_opt': 10, 'ema_opt': 21, 'atr_opt': 14},
    'ETC/USDT':  {'adx_opt': 12, 'ker_opt':  9, 'ema_opt': 17, 'atr_opt': 12},
    'NEAR/USDT': {'adx_opt': 12, 'ker_opt':  9, 'ema_opt': 17, 'atr_opt': 12},
    'APT/USDT':  {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'ARB/USDT':  {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'OP/USDT':   {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'INJ/USDT':  {'adx_opt': 12, 'ker_opt':  9, 'ema_opt': 17, 'atr_opt': 12},
    'SUI/USDT':  {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'APE/USDT':  {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'SEI/USDT':  {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'VET/USDT':  {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'ALGO/USDT': {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'DOGE/USDT': {'adx_opt':  8, 'ker_opt':  6, 'ema_opt': 10, 'atr_opt':  8},
    'PEPE/USDT': {'adx_opt':  8, 'ker_opt':  6, 'ema_opt': 10, 'atr_opt':  8},
    'WIF/USDT':  {'adx_opt':  8, 'ker_opt':  6, 'ema_opt': 10, 'atr_opt':  8},
    'BONK/USDT': {'adx_opt':  8, 'ker_opt':  6, 'ema_opt': 10, 'atr_opt':  8},
    'FLOKI/USDT':{'adx_opt':  8, 'ker_opt':  6, 'ema_opt': 10, 'atr_opt':  8},
    'AAVE/USDT': {'adx_opt': 12, 'ker_opt':  9, 'ema_opt': 17, 'atr_opt': 12},
    'MKR/USDT':  {'adx_opt': 12, 'ker_opt':  9, 'ema_opt': 17, 'atr_opt': 12},
    'CRV/USDT':  {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'LDO/USDT':  {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'SAND/USDT': {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'MANA/USDT': {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'GALA/USDT': {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'AXS/USDT':  {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'FIL/USDT':  {'adx_opt': 12, 'ker_opt':  9, 'ema_opt': 17, 'atr_opt': 12},
    'AR/USDT':   {'adx_opt': 10, 'ker_opt':  8, 'ema_opt': 13, 'atr_opt': 10},
    'ICP/USDT':  {'adx_opt': 12, 'ker_opt':  9, 'ema_opt': 17, 'atr_opt': 12},
}

# ============================================================
# PARÁMETROS POR DEFECTO
# ============================================================
DEFAULT_PARAMS = {
    'min_score':   MIN_SCORE,
    'min_score_a': MIN_SCORE_A,
    'min_score_s': MIN_SCORE_S,
    'adx_threshold':   ADX_THRESHOLD,
    'adx_threshold_a': ADX_THRESHOLD_A,
    'adx_threshold_s': ADX_THRESHOLD_S,
    'ker_threshold':   KER_THRESHOLD,
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

# ============================================================
# PARÁMETROS DE BACKTEST
# ============================================================
BACKTEST_CONFIG = {
    'default_symbols': SYMBOLS[:10],
    'default_timeframe': '1h',
    'default_limit': 4320,          # ~180 días de 1h
    'default_capital': INITIAL_CAPITAL,
    'default_fee': 0.001,           # 0.10% por lado
    'default_slippage': 0.0005,     # 0.05%
    'default_max_hold': MAX_HOLD,
    'walk_forward_train_days': 30,
    'walk_forward_test_days': 7,
    'monte_carlo_iterations': 10000,
    'random_seed': 42,
}

# ============================================================
# APIs PÚBLICAS (fallback para activos no-cripto)
# ============================================================
API_ENDPOINTS = {
    'fiat_frankfurter': 'https://api.frankfurter.dev/v1',
    'index_stooq': 'https://stooq.com/q/d/l/',
    'commodity_goldprice': 'https://api.goldprice.dev/v1',
}
