# data_engine.py
# ============================================================
# Motor de datos con múltiples exchanges, APIs públicas y caché.
# Auditoría forense aplicada:
#   P0-1: import numpy al top
#   P0-4: eliminación completa de datos sintéticos
#   P1-3: timezone aware (UTC)
#   P1-5: _fix_symbol blindado
# ============================================================
import os
import time
import logging
from io import StringIO
from typing import Optional, List, Dict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import ccxt
import requests

from config import EXCHANGE_PRIORITY, CACHE_DIR, TIMEFRAME, SYMBOLS, API_ENDPOINTS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 3600


class DataEngine:
    """Motor de datos con multi-exchange, APIs públicas y caché."""

    def __init__(self):
        self.cache_dir = CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self.primary: Optional[str] = None
        self._connect_exchanges()

    # --------------------------------------------------------
    # CONEXIÓN A EXCHANGES
    # --------------------------------------------------------
    def _connect_exchanges(self):
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
            logger.error("❌ Ningún exchange disponible. Solo se podrán usar APIs públicas.")

    # --------------------------------------------------------
    # HELPERS DE CACHÉ
    # --------------------------------------------------------
    def _cache_is_fresh(self, path: str, ttl: int = CACHE_TTL_SECONDS) -> Optional[pd.DataFrame]:
        """Devuelve el DataFrame si la caché existe y es fresca. Si no, None."""
        if not os.path.exists(path):
            return None
        try:
            df = pd.read_parquet(path)
            if df is None or df.empty:
                return None
            last_ts = df.index[-1]
            if last_ts.tzinfo is None:
                last_ts = last_ts.tz_localize('UTC')
            age = (pd.Timestamp.now(tz='UTC') - last_ts).total_seconds()
            if age < ttl:
                return df
        except Exception as e:
            logger.debug(f"Caché inválida en {path}: {e}")
        return None

    # --------------------------------------------------------
    # ROUTER PRINCIPAL
    # --------------------------------------------------------
    def fetch_ohlcv(self, symbol: str, timeframe: str = None,
                    limit: int = 300, use_cache: bool = True) -> Optional[pd.DataFrame]:
        if timeframe is None:
            timeframe = TIMEFRAME

        if self._is_fiat_only(symbol):
            return self._fetch_fiat_frankfurter(symbol, timeframe, limit, use_cache)

        if self._is_index(symbol):
            return self._fetch_index_stooq(symbol, timeframe, limit, use_cache)

        if self._is_commodity(symbol):
            return self._fetch_commodity_goldprice(symbol, timeframe, limit, use_cache)

        return self._fetch_crypto(symbol, timeframe, limit, use_cache)

    # --------------------------------------------------------
    # CRIPTO — vía CCXT con fallback entre exchanges
    # --------------------------------------------------------
    def _fetch_crypto(self, symbol: str, timeframe: str,
                      limit: int, use_cache: bool) -> Optional[pd.DataFrame]:
        symbol_ex = self._fix_symbol(symbol)
        cache_file = os.path.join(
            self.cache_dir,
            f"{symbol.replace('/', '_')}_{timeframe}_{limit}.parquet"
        )

        if use_cache:
            df = self._cache_is_fresh(cache_file)
            if df is not None:
                logger.debug(f"✅ Caché válida para {symbol}")
                return df

        for ex_id, exchange in self.exchanges.items():
            for attempt in range(3):
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol_ex, timeframe, limit=limit)
                    if not ohlcv:
                        logger.warning(f"⚠️ {symbol} sin velas desde {ex_id}")
                        continue

                    df = pd.DataFrame(
                        ohlcv,
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    )
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                    df = df.set_index('timestamp').sort_index()
                    df = df[~df.index.duplicated(keep='last')]

                    if use_cache:
                        try:
                            df.to_parquet(cache_file)
                        except Exception as e:
                            logger.debug(f"No se pudo guardar caché: {e}")

                    logger.debug(f"✅ {symbol} desde {ex_id} ({len(df)} velas)")
                    return df

                except Exception as e:
                    logger.warning(f"Intento {attempt+1}/3 {symbol} @ {ex_id}: {e}")
                    time.sleep(1)

        logger.error(f"❌ No se pudo obtener {symbol} desde ningún exchange")
        return None

    # --------------------------------------------------------
    # FIAT — Frankfurter (ECB, sin API key)
    # --------------------------------------------------------
    def _fetch_fiat_frankfurter(self, symbol: str, timeframe: str,
                                limit: int, use_cache: bool) -> Optional[pd.DataFrame]:
        cache_file = os.path.join(
            self.cache_dir,
            f"fiat_{symbol.replace('/', '_')}_{timeframe}.parquet"
        )

        if use_cache:
            df = self._cache_is_fresh(cache_file)
            if df is not None:
                return df

        try:
            base = symbol.split('/')[0]
            quote = symbol.split('/')[1] if '/' in symbol else 'USD'

            # Frankfurter solo tiene datos diarios
            end = datetime.utcnow().date()
            start = end - timedelta(days=730)
            url = f"{API_ENDPOINTS['fiat_frankfurter']}/{start}..{end}?base={base}"
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            rates = data.get('rates', {})
            if not rates:
                logger.warning(f"Frankfurter sin datos para {symbol}")
                return None

            rows = []
            for date_str, rd in sorted(rates.items()):
                if quote in rd:
                    p = float(rd[quote])
                    rows.append({
                        'timestamp': pd.Timestamp(date_str, tz='UTC'),
                        'open': p, 'high': p, 'low': p, 'close': p,
                        'volume': 0.0,
                    })

            if not rows:
                return None

            df = pd.DataFrame(rows).set_index('timestamp').sort_index()
            df = df[~df.index.duplicated(keep='last')]

            if use_cache:
                try:
                    df.to_parquet(cache_file)
                except Exception:
                    pass
            return df

        except Exception as e:
            logger.warning(f"Frankfurter falló para {symbol}: {e}")
            return None

    # --------------------------------------------------------
    # ÍNDICES — Stooq CSV (gratuito)
    # --------------------------------------------------------
    def _fetch_index_stooq(self, symbol: str, timeframe: str,
                           limit: int, use_cache: bool) -> Optional[pd.DataFrame]:
        cache_file = os.path.join(
            self.cache_dir,
            f"idx_{symbol.replace('/', '_')}.parquet"
        )

        if use_cache:
            df = self._cache_is_fresh(cache_file)
            if df is not None:
                return df

        try:
            idx_map = {
                'SPX': '^spx', 'NDX': '^ndx', 'DJI': '^dji',
                'DAX': '^dax', 'FTSE': '^ftm', 'NIKKEI': '^nkx',
                'HSI': '^hsi', 'ASX': '^asx', 'IBOV': '^ibov',
            }
            base = symbol.split('/')[0]
            ticker = idx_map.get(base)
            if not ticker:
                logger.warning(f"Índice {symbol} no mapeado en Stooq")
                return None

            url = f"{API_ENDPOINTS['index_stooq']}?s={ticker}&i=d"
            r = requests.get(url, timeout=15)
            r.raise_for_status()

            df = pd.read_csv(StringIO(r.text))
            if df.empty or 'Date' not in df.columns:
                return None

            df['Date'] = pd.to_datetime(df['Date'], utc=True)
            df = df.set_index('Date').rename(columns={
                'Open': 'open', 'High': 'high',
                'Low': 'low', 'Close': 'close', 'Volume': 'volume',
            })
            df = df[~df.index.duplicated(keep='last')].sort_index()

            if use_cache:
                try:
                    df.to_parquet(cache_file)
                except Exception:
                    pass
            return df

        except Exception as e:
            logger.warning(f"Stooq falló para {symbol}: {e}")
            return None

    # --------------------------------------------------------
    # COMMODITIES — goldprice.dev
    # --------------------------------------------------------
    def _fetch_commodity_goldprice(self, symbol: str, timeframe: str,
                                   limit: int, use_cache: bool) -> Optional[pd.DataFrame]:
        cache_file = os.path.join(
            self.cache_dir,
            f"comm_{symbol.replace('/', '_')}.parquet"
        )

        if use_cache:
            df = self._cache_is_fresh(cache_file)
            if df is not None:
                return df

        try:
            sym_map = {'XAU': 'XAU-USD-SPOT', 'XAG': 'XAG-USD-SPOT'}
            base = symbol.split('/')[0]
            api_sym = sym_map.get(base)
            if not api_sym:
                logger.warning(f"Commodity {symbol} no soportado por goldprice.dev")
                return None

            url = f"{API_ENDPOINTS['commodity_goldprice']}/prices/history?symbol={api_sym}&interval=1d"
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            series = r.json().get('series', [])
            if not series:
                return None

            rows = []
            for bar in series:
                rows.append({
                    'timestamp': pd.Timestamp(bar['date'], tz='UTC'),
                    'open': float(bar['open']),
                    'high': float(bar['high']),
                    'low': float(bar['low']),
                    'close': float(bar['close']),
                    'volume': float(bar.get('volume') or 0),
                })

            df = pd.DataFrame(rows).set_index('timestamp').sort_index()
            df = df[~df.index.duplicated(keep='last')]

            if use_cache:
                try:
                    df.to_parquet(cache_file)
                except Exception:
                    pass
            return df

        except Exception as e:
            logger.warning(f"goldprice.dev falló para {symbol}: {e}")
            return None

    # --------------------------------------------------------
    # CLASIFICADORES
    # --------------------------------------------------------
    def _is_fiat_only(self, symbol: str) -> bool:
        fiats = [
            'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD',
            'CNY', 'MXN', 'BRL', 'ARS', 'CLP', 'COP', 'PEN',
            'UYU', 'KRW', 'SGD', 'HKD', 'SEK', 'NOK', 'DKK',
            'ZAR', 'TRY', 'RUB', 'INR', 'IDR', 'PHP', 'MYR',
            'THB', 'VND',
        ]
        if '/' not in symbol:
            return False
        base = symbol.split('/')[0]
        return base in fiats

    def _is_index(self, symbol: str) -> bool:
        indices = ['SPX', 'NDX', 'DJI', 'DAX', 'FTSE', 'NIKKEI', 'HSI', 'ASX', 'IBOV']
        if '/' not in symbol:
            return False
        return symbol.split('/')[0] in indices

    def _is_commodity(self, symbol: str) -> bool:
        commodities = ['XAU', 'XAG', 'XPT', 'XPD', 'WTI', 'BRENT', 'NG']
        if '/' not in symbol:
            return False
        return symbol.split('/')[0] in commodities

    # --------------------------------------------------------
    # NORMALIZACIÓN DE SÍMBOLO
    # --------------------------------------------------------
    def _fix_symbol(self, symbol: str) -> str:
        """Normaliza el símbolo para CCXT. Blindado contra edge cases."""
        if not symbol:
            return symbol

        # Ya tiene formato con slash
        if '/' in symbol:
            return symbol

        # Sin slash: agregar /USDT
        if 'USDT' in symbol:
            # Evitar "USDT" → "/USDT"
            base = symbol.replace('USDT', '')
            if not base:
                return 'USDT/USDT'  # caso degenerado
            return f"{base}/USDT"

        return f"{symbol}/USDT"

    # --------------------------------------------------------
    # SÍMBOLOS DISPONIBLES
    # --------------------------------------------------------
    def get_symbols(self) -> List[str]:
        return SYMBOLS
