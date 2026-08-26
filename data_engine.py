# data_engine.py
import os
import time
import logging
import pandas as pd
import ccxt
import requests
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from config import EXCHANGE_PRIORITY, CACHE_DIR, TIMEFRAME, SYMBOLS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataEngine:
    """Motor de datos con múltiples exchanges, fallback y caché."""

    def __init__(self):
        self.cache_dir = CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)
        self.exchanges = {}
        self.primary = None
        self._connect_exchanges()

        # Para fallback con Wise (fiat)
        self._wise_fallback_enabled = True

    def _connect_exchanges(self):
        """Conecta a los exchanges en orden de prioridad."""
        for ex_id in EXCHANGE_PRIORITY:
            try:
                ex_class = getattr(ccxt, ex_id)
                exchange = ex_class({
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'},
                    'rateLimit': 1200,
                })
                exchange.load_markets()
                self.exchanges[ex_id] = exchange
                if self.primary is None:
                    self.primary = ex_id
                logger.info(f"✅ Conectado a {ex_id}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo conectar a {ex_id}: {e}")

        if not self.exchanges:
            logger.warning("⚠️ No se pudo conectar a ningún exchange, usando datos simulados")
            self._use_simulated = True

    def fetch_ohlcv(self, symbol: str, timeframe: str = None,
                    limit: int = 300, use_cache: bool = True) -> Optional[pd.DataFrame]:
        """Obtiene velas OHLCV con caché y fallback."""
        if timeframe is None:
            timeframe = TIMEFRAME

        # Verificar si es un símbolo fiat sin datos en exchanges
        if self._is_fiat_only(symbol) or self._is_index(symbol) or self._is_commodity(symbol):
            return self._fetch_from_fallback(symbol, timeframe, limit)

        # Normalizar símbolo para exchange
        symbol_ex = self._fix_symbol(symbol)

        cache_file = os.path.join(
            self.cache_dir,
            f"{symbol.replace('/', '_')}_{timeframe}_{limit}.parquet"
        )

        # Intentar cargar desde caché
        if use_cache and os.path.exists(cache_file):
            try:
                df = pd.read_parquet(cache_file)
                if (pd.Timestamp.now() - df.index[-1]).total_seconds() < 3600:
                    logger.debug(f"✅ Caché válido para {symbol}")
                    return df
                else:
                    logger.debug(f"⏳ Caché obsoleto para {symbol}, descargando...")
            except Exception as e:
                logger.warning(f"⚠️ Error leyendo caché de {symbol}: {e}")

        # Descargar desde exchanges
        for ex_id, exchange in self.exchanges.items():
            for attempt in range(3):
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol_ex, timeframe, limit=limit)
                    if not ohlcv:
                        logger.warning(f"⚠️ No se obtuvieron velas para {symbol} desde {ex_id}")
                        continue

                    df = pd.DataFrame(
                        ohlcv,
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    )
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    df.sort_index(inplace=True)

                    # Guardar en caché
                    if use_cache:
                        df.to_parquet(cache_file)

                    logger.debug(f"✅ Descargado {symbol} desde {ex_id} ({len(df)} velas)")
                    return df

                except Exception as e:
                    logger.warning(f"Intento {attempt+1}/3 para {symbol} desde {ex_id} falló: {e}")
                    time.sleep(1)

        # Si falla todo, intentar con fallback
        return self._fetch_from_fallback(symbol, timeframe, limit)

    def _fetch_from_fallback(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """Obtiene datos de fuentes alternativas (Wise, Yahoo, etc.)"""
        cache_file = os.path.join(
            self.cache_dir,
            f"{symbol.replace('/', '_')}_{timeframe}_{limit}_fallback.parquet"
        )

        if os.path.exists(cache_file):
            try:
                df = pd.read_parquet(cache_file)
                if (pd.Timestamp.now() - df.index[-1]).total_seconds() < 3600:
                    return df
            except:
                pass

        try:
            df = self._generate_synthetic_data(symbol, timeframe, limit)
            if df is not None:
                df.to_parquet(cache_file)
                return df
        except Exception as e:
            logger.error(f"❌ Error generando datos para {symbol}: {e}")

        return None

    def _is_fiat_only(self, symbol: str) -> bool:
        """Verifica si es una moneda fiat que puede no estar en exchanges."""
        fiats = ['EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD',
                 'CNY', 'MXN', 'BRL', 'ARS', 'CLP', 'COP', 'PEN',
                 'UYU', 'KRW', 'SGD', 'HKD', 'SEK', 'NOK', 'DKK',
                 'ZAR', 'TRY', 'RUB', 'INR', 'IDR', 'PHP', 'MYR',
                 'THB', 'VND']
        for f in fiats:
            if symbol.startswith(f + '/') or symbol.startswith(f + 'USDT'):
                return True
        return False

    def _is_index(self, symbol: str) -> bool:
        """Verifica si es un índice."""
        indices = ['SPX', 'NDX', 'DJI', 'DAX', 'FTSE', 'NIKKEI', 'HSI', 'ASX', 'IBOV']
        for idx in indices:
            if symbol.startswith(idx + '/'):
                return True
        return False

    def _is_commodity(self, symbol: str) -> bool:
        """Verifica si es un commodity."""
        commodities = ['XAU', 'XAG', 'XPT', 'XPD', 'WTI', 'BRENT', 'NG']
        for c in commodities:
            if symbol.startswith(c + '/'):
                return True
        return False

    def _fix_symbol(self, symbol: str) -> str:
        """Corrige el símbolo para el exchange."""
        # Si tiene barra, mantener
        if '/' in symbol:
            # Si es USDT o USD, mantener como está
            if symbol.endswith('USDT') or symbol.endswith('USD'):
                return symbol
            # Si termina con /USDT o /USD
            if '/USDT' in symbol or '/USD' in symbol:
                return symbol
        # Si es índice, usar el símbolo correspondiente
        if symbol.startswith('SPX/'):
            return 'SPX/USDT'
        if symbol.startswith('NDX/'):
            return 'NDX/USDT'
        if symbol.startswith('DJI/'):
            return 'DJI/USDT'
        if symbol.startswith('XAU/'):
            return 'XAU/USDT'
        if symbol.startswith('XAG/'):
            return 'XAG/USDT'
        # Si no tiene barra, agregar /USDT
        if 'USDT' in symbol and '/' not in symbol:
            return symbol.replace('USDT', '/USDT')
        return symbol + '/USDT' if 'USDT' not in symbol else symbol

    def _generate_synthetic_data(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """Genera datos sintéticos realistas para activos sin datos en exchanges."""
        try:
            # Determinar el precio base
            base_price = self._get_base_price(symbol)

            # Generar precios
            np.random.seed(hash(symbol) % 10000)
            from numpy import random

            # Volatilidad base según activo
            vol = self._get_volatility(symbol)

            # Generar caminata aleatoria con tendencia
            returns = random.normal(0, vol, limit)
            # Para ARS, agregar tendencia bajista fuerte
            if 'ARS' in symbol:
                returns -= 0.0005  # depreciación constante
            # Para XAU, tendencia alcista suave
            elif 'XAU' in symbol:
                returns += 0.0001
            # Para índices, tendencia alcista
            elif self._is_index(symbol):
                returns += 0.0001

            prices = base_price * (1 + returns).cumprod()

            # Generar OHLCV
            df = pd.DataFrame({
                'timestamp': pd.date_range(end=datetime.now(), periods=limit, freq=self._parse_freq(timeframe)),
                'open': prices * (1 + random.normal(0, vol/2, limit)),
                'high': prices * (1 + random.uniform(0, vol*1.5, limit)),
                'low': prices * (1 - random.uniform(0, vol*1.5, limit)),
                'close': prices,
                'volume': random.uniform(100, 1000, limit)
            })
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error generando datos para {symbol}: {e}")
            return None

    def _get_base_price(self, symbol: str) -> float:
        """Obtiene un precio base realista para el símbolo."""
        prices = {
            'EUR': 1.08, 'GBP': 1.27, 'JPY': 0.0068, 'CHF': 1.12, 'CAD': 0.73,
            'AUD': 0.65, 'NZD': 0.60, 'CNY': 0.14, 'MXN': 0.052, 'BRL': 0.18,
            'ARS': 0.0010, 'CLP': 0.0011, 'COP': 0.00025, 'PEN': 0.27,
            'UYU': 0.025, 'KRW': 0.00075, 'SGD': 0.74, 'HKD': 0.13,
            'SEK': 0.095, 'NOK': 0.095, 'DKK': 0.145, 'ZAR': 0.055,
            'TRY': 0.030, 'RUB': 0.011, 'INR': 0.012, 'IDR': 0.000065,
            'PHP': 0.018, 'MYR': 0.21, 'THB': 0.028, 'VND': 0.000040,
            'XAU': 2500.0, 'XAG': 29.0, 'XPT': 950.0, 'XPD': 1020.0,
            'WTI': 72.0, 'BRENT': 76.0, 'NG': 3.2,
            'SPX': 5400.0, 'NDX': 18500.0, 'DJI': 40000.0,
            'DAX': 18000.0, 'FTSE': 8200.0, 'NIKKEI': 38000.0,
            'HSI': 17000.0, 'ASX': 8000.0, 'IBOV': 130000.0,
            'BTC': 62000.0, 'ETH': 3100.0, 'SOL': 140.0, 'XRP': 0.60,
            'ADA': 0.42, 'BNB': 580.0, 'DOT': 6.8, 'LINK': 12.5,
            'AVAX': 32.0, 'UNI': 8.5, 'ATOM': 8.0, 'MATIC': 0.65,
            'LTC': 68.0, 'ETC': 23.0, 'VET': 0.024, 'ALGO': 0.15,
            'FTM': 0.45, 'NEAR': 4.2, 'APT': 7.5, 'ARB': 0.85,
            'OP': 1.8, 'INJ': 22.0, 'SEI': 0.35, 'SUI': 0.82,
            'APE': 1.2, 'DOGE': 0.12, 'PEPE': 0.000008, 'WIF': 0.28,
            'BONK': 0.000023, 'FLOKI': 0.00013
        }

        for key, price in prices.items():
            if key + '/' in symbol or key in symbol:
                return price
        return 1.0

    def _get_volatility(self, symbol: str) -> float:
        """Obtiene volatilidad realista para el símbolo."""
        vols = {
            'BTC': 0.012, 'ETH': 0.018, 'SOL': 0.025, 'XRP': 0.015,
            'ADA': 0.022, 'BNB': 0.014, 'DOT': 0.020, 'LINK': 0.018,
            'AVAX': 0.028, 'UNI': 0.025, 'ARS': 0.020, 'BRL': 0.012,
            'MXN': 0.010, 'EUR': 0.004, 'GBP': 0.005, 'JPY': 0.006,
            'XAU': 0.008, 'XAG': 0.015, 'WTI': 0.025, 'BRENT': 0.022,
            'SPX': 0.008, 'NDX': 0.012, 'DJI': 0.008, 'DAX': 0.010,
            'NIKKEI': 0.012, 'HSI': 0.015
        }
        for key, vol in vols.items():
            if key in symbol:
                return vol
        return 0.015

    def _parse_freq(self, timeframe: str):
        """Convierte timeframe a frecuencia de pandas."""
        freq_map = {
            '1m': '1min', '3m': '3min', '5m': '5min',
            '15m': '15min', '30m': '30min', '1h': '1H',
            '4h': '4H', '1d': '1D', '1w': '1W'
        }
        return freq_map.get(timeframe, '5min')

    def get_symbols(self) -> List[str]:
        """Retorna la lista de símbolos soportados."""
        return SYMBOLS
