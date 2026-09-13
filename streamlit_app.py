# streamlit_app.py
# ============================================================
# DAPS Ω — Dashboard + Backtest Lab
# Auditoría forense aplicada:
#   P1-7 FIX: global_time calculado antes de renderizar métricas
#   + Sección BACKTEST LAB completa
#   + Exportación CSV / Reporte
#   + Manejo robusto de estados vacíos
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import logging
from io import BytesIO

from data_engine import DataEngine
from signal_engine import Signal, rank_signals, classify_by_direction
from backtest_engine import (
    BacktestEngine, walk_forward_backtest, monte_carlo_bootstrap,
)
from config import (
    INITIAL_CAPITAL, DEFAULT_PARAMS, VERSION,
    PROJECT_NAME, TIMEFRAME, SYMBOLS, BACKTEST_CONFIG,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title=f"{PROJECT_NAME}",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS — legibilidad en modo claro
st.markdown("""
<style>
    .stApp { background-color: white; color: black; }
    .stDataFrame { background-color: white; }
    .stDataFrame table { color: black; }
    .stExpander { background-color: #f8f8f8; border: 1px solid #ddd; }
    .stMetric { background-color: #f9f9f9; border-radius: 8px; padding: 8px; border: 1px solid #eee; }
    h1, h2, h3, h4, h5, h6 { color: #000; }
    .stButton button { background-color: #f0f0f0; color: black; border: 1px solid #ccc; }
    .stButton button:hover { background-color: #e0e0e0; }
    .css-1d391kg { background-color: #f5f5f5; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# TÍTULO
# ============================================================
st.title(f"📊 {PROJECT_NAME}")
st.subheader(f"v{VERSION} — Scanner de {len(SYMBOLS)} activos · Timeframe {TIMEFRAME}")
st.markdown("---")


# ============================================================
# INICIALIZACIÓN DE ESTADO
# ============================================================
def _init_state():
    defaults = {
        'data_engine': None,
        'symbols': SYMBOLS,
        'signals': [],
        'valid_signals': [],
        'ranked_signals': [],
        'classified': {},
        'last_refresh': None,
        'data_dict': {},
        'global_time': "N/A",
        'bt_trades': None,
        'bt_metrics': None,
        'bt_wf': None,
        'bt_mc': None,
        'bt_signals_df': None,
        'bt_data': None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()

if st.session_state.data_engine is None:
    with st.spinner("🔌 Inicializando motor de datos..."):
        try:
            st.session_state.data_engine = DataEngine()
        except Exception as e:
            st.error(f"❌ No se pudo inicializar DataEngine: {e}")
            st.session_state.data_engine = None


# ============================================================
# SIDEBAR — CONFIGURACIÓN + BACKTEST LAB
# ============================================================
with st.sidebar:
    st.header("⚙️ Configuración")
    st.caption(f"Capital: ${INITIAL_CAPITAL:,.2f}")
    st.caption(f"Timeframe: {TIMEFRAME}")
    st.caption(f"Activos: {len(SYMBOLS)}")

    st.markdown("---")
    st.header("🎯 Parámetros")
    st.caption(f"Score mínimo: {DEFAULT_PARAMS['min_score']}")
    st.caption(f"ADX umbral: {DEFAULT_PARAMS['adx_threshold']}")
    st.caption(f"KER umbral: {DEFAULT_PARAMS['ker_threshold']}")
    st.caption(f"TP S-TIER: {DEFAULT_PARAMS['tp_mult_s']}× ATR")
    st.caption(f"SL S-TIER: {DEFAULT_PARAMS['sl_mult_s']}× ATR")

    st.markdown("---")
    st.header("🔄 Acciones")
    refresh_btn = st.button("🔄 Actualizar Ranking", type="primary", use_container_width=True)

    st.markdown("---")
    st.header("🧪 Backtest Lab")

    bt_symbols = st.multiselect(
        "Activos para backtest",
        options=SYMBOLS,
        default=BACKTEST_CONFIG['default_symbols'],
    )
    bt_timeframe = st.selectbox(
        "Timeframe",
        options=['5m', '15m', '1h', '4h', '1d'],
        index=2,
    )
    bt_limit = st.number_input(
        "Velas a descargar",
        min_value=200, max_value=20000,
        value=BACKTEST_CONFIG['default_limit'], step=100,
    )
    bt_capital = st.number_input(
        "Capital inicial ($)",
        min_value=100.0, value=float(BACKTEST_CONFIG['default_capital']), step=500.0,
    )
    bt_fee_pct = st.number_input(
        "Comisión por lado (%)",
        min_value=0.0, max_value=1.0, value=0.10, step=0.01,
    )
    bt_slippage_pct = st.number_input(
        "Slippage (%)",
        min_value=0.0, max_value=1.0, value=0.05, step=0.01,
    )
    bt_max_hold = st.number_input(
        "Max hold (velas)",
        min_value=5, max_value=500, value=int(BACKTEST_CONFIG['default_max_hold']), step=5,
    )

    st.markdown("**Walk-Forward**")
    bt_train_days = st.number_input("Train days", min_value=5, max_value=180, value=30)
    bt_test_days = st.number_input("Test days", min_value=1, max_value=60, value=7)

    st.markdown("**Monte Carlo**")
    bt_mc_iters = st.number_input(
        "Iteraciones",
        min_value=100, max_value=50000,
        value=int(BACKTEST_CONFIG['monte_carlo_iterations']), step=1000,
    )

    col_bt1, col_bt2 = st.columns(2)
    with col_bt1:
        run_bt_btn = st.button("▶ Backtest", type="primary", use_container_width=True)
    with col_bt2:
        run_wf_btn = st.button("▶ Walk-Fwd", use_container_width=True)

    col_bt3, col_bt4 = st.columns(2)
    with col_bt3:
        run_mc_btn = st.button("▶ MonteCarlo", use_container_width=True)
    with col_bt4:
        clear_bt_btn = st.button("🗑️ Limpiar", use_container_width=True)

    st.markdown("---")
    st.header("📊 Estado")
    st.caption(f"Última actualización: {st.session_state.last_refresh or 'Nunca'}")
    st.caption(f"Señales aprobadas: {len(st.session_state.valid_signals)}")
    st.caption(f"Señales totales: {len(st.session_state.ranked_signals)}")
    if st.session_state.bt_metrics:
        st.caption(f"Backtest trades: {st.session_state.bt_metrics.get('total_trades', 0)}")


# ============================================================
# FUNCIONES — SCANNER
# ============================================================
def refresh_ranking():
    de = st.session_state.data_engine
    if de is None:
        st.error("❌ DataEngine no inicializado")
        return

    symbols = st.session_state.symbols
    signals = []
    data_dict = {}
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, sym in enumerate(symbols):
        status_text.text(f"Escaneando {sym}... ({i+1}/{len(symbols)})")
        try:
            df = de.fetch_ohlcv(sym, limit=300)
        except Exception as e:
            logger.warning(f"Error fetching {sym}: {e}")
            df = None

        if df is not None and not df.empty:
            data_dict[sym] = df
            try:
                s = Signal(sym, df, DEFAULT_PARAMS)
                signals.append(s.to_dict())
            except Exception as e:
                logger.warning(f"Error señal {sym}: {e}")

        progress_bar.progress((i + 1) / len(symbols))

    progress_bar.empty()
    status_text.empty()

    st.session_state.data_dict = data_dict
    st.session_state.signals = signals
    st.session_state.valid_signals = [s for s in signals if s.get('is_valid', False)]
    st.session_state.ranked_signals = rank_signals(signals)
    st.session_state.classified = classify_by_direction(signals)
    st.session_state.last_refresh = datetime.now().strftime("%H:%M:%S")


# ============================================================
# FUNCIONES — BACKTEST
# ============================================================
def _fetch_backtest_data(symbols, timeframe, limit):
    """Descarga datos históricos vía DataEngine (usa ccxt + caché)."""
    de = st.session_state.data_engine
    if de is None:
        st.error("❌ DataEngine no inicializado")
        return {}

    data = {}
    progress = st.progress(0)
    status = st.empty()
    for i, sym in enumerate(symbols):
        status.text(f"📥 Descargando {sym}... ({i+1}/{len(symbols)})")
        try:
            df = de.fetch_ohlcv(sym, timeframe=timeframe, limit=limit, use_cache=True)
            if df is not None and not df.empty and len(df) > 60:
                data[sym] = df
        except Exception as e:
            logger.warning(f"Error descarga {sym}: {e}")
        progress.progress((i + 1) / len(symbols))
    progress.empty()
    status.empty()
    return data


def _generate_signals_for_backtest(data_dict, use_look_ahead_fix=True):
    """
    Genera señales bar-by-bar para backtest.
    use_look_ahead_fix=True  → V2 corregido (df.iloc[:i])
    use_look_ahead_fix=False → V1 legacy (df.iloc[:i+1])
    """
    signals = []
    for sym, df in data_dict.items():
        n = len(df)
        if n < 60:
            continue
        for i in range(60, n):
            window = df.iloc[:i] if use_look_ahead_fix else df.iloc[:i + 1]
            if len(window) < 30:
                continue
            try:
                s = Signal(sym, window, DEFAULT_PARAMS)
                d = s.to_dict()
                d['timestamp'] = df.index[i]
                signals.append(d)
            except Exception:
                continue
    return pd.DataFrame(signals)


def run_backtest():
    if not bt_symbols:
        st.error("❌ Seleccioná al menos un activo")
        return

    with st.spinner(f"📥 Descargando {len(bt_symbols)} activos..."):
        data = _fetch_backtest_data(bt_symbols, bt_timeframe, int(bt_limit))

    if not data:
        st.error("❌ No se pudieron descargar datos. Verificá conexión.")
        return

    st.info(f"✅ Datos descargados: {len(data)} activos · "
            f"{sum(len(v) for v in data.values())} velas totales")

    with st.spinner("🧠 Generando señales históricas (V2 corregido)..."):
        sigs = _generate_signals_for_backtest(data, use_look_ahead_fix=True)

    if sigs.empty:
        st.warning("⚠️ No se generaron señales")
        return

    approved = sigs[sigs['is_valid']]
    st.info(f"📊 Señales: {len(sigs)} totales · {len(approved)} aprobadas")

    with st.spinner("💰 Simulando trades..."):
        engine = BacktestEngine(
            initial_capital=bt_capital,
            fee=bt_fee_pct / 100.0,
            slippage=bt_slippage_pct / 100.0,
        )
        trades = engine.simulate(approved, data, max_hold=int(bt_max_hold))
        metrics = engine.compute_metrics(trades)

    st.session_state.bt_trades = trades
    st.session_state.bt_metrics = metrics
    st.session_state.bt_signals_df = sigs
    st.session_state.bt_data = data


def run_walk_forward():
    if st.session_state.bt_signals_df is None or st.session_state.bt_data is None:
        st.warning("⚠️ Ejecutá primero un Backtest")
        return

    approved = st.session_state.bt_signals_df
    approved = approved[approved['is_valid']]

    with st.spinner("🔄 Ejecutando Walk-Forward..."):
        wf = walk_forward_backtest(
            approved,
            st.session_state.bt_data,
            train_days=int(bt_train_days),
            test_days=int(bt_test_days),
            max_hold=int(bt_max_hold),
            capital=bt_capital,
        )
    st.session_state.bt_wf = wf


def run_monte_carlo():
    if st.session_state.bt_trades is None or st.session_state.bt_trades.empty:
        st.warning("⚠️ Ejecutá primero un Backtest")
        return

    with st.spinner(f"🎲 Monte Carlo ({bt_mc_iters} iteraciones)..."):
        mc = monte_carlo_bootstrap(
            st.session_state.bt_trades,
            n_iter=int(bt_mc_iters),
            capital=bt_capital,
        )
    st.session_state.bt_mc = mc


# ============================================================
# TRIGGERS
# ============================================================
if refresh_btn or st.session_state.last_refresh is None:
    if st.session_state.data_engine is not None:
        with st.spinner("🔍 Escaneando activos..."):
            refresh_ranking()
        st.rerun()

if run_bt_btn:
    run_backtest()
if run_wf_btn:
    run_walk_forward()
if run_mc_btn:
    run_monte_carlo()
if clear_bt_btn:
    st.session_state.bt_trades = None
    st.session_state.bt_metrics = None
    st.session_state.bt_wf = None
    st.session_state.bt_mc = None
    st.session_state.bt_signals_df = None
    st.session_state.bt_data = None
    st.rerun()


# ============================================================
# TABS PRINCIPALES
# ============================================================
tab_scanner, tab_backtest, tab_compare, tab_tiers = st.tabs([
    "📡 Scanner", "🧪 Backtest Lab", "⚖️ Comparativa V1 vs V2", "🏷️ Por Tier"
])


# ============================================================
# TAB 1 — SCANNER
# ============================================================
with tab_scanner:
    ranked = st.session_state.ranked_signals
    valid = st.session_state.valid_signals
    classified = st.session_state.classified

    # P1-7 FIX: calcular global_time ANTES de renderizar métricas
    if ranked:
        times = [s.get('estimated_time_to_trade', 999) for s in ranked]
        global_time = min(times) if times else "N/A"
    else:
        global_time = "N/A"
    st.session_state.global_time = global_time

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📈 Señales aprobadas", len(valid))
    with col2:
        st.metric("📊 Señales totales", len(ranked))
    with col3:
        st.metric("🟢 LONG aprobadas", len(classified.get('long_valid', [])))
    with col4:
        st.metric("🔴 SHORT aprobados", len(classified.get('short_valid', [])))
    with col5:
        st.metric("⏱️ Próximo trade", f"{global_time} min")

    st.markdown("---")
    st.subheader("🏆 Ranking de Señales (Todas)")

    if ranked:
        df_rank = pd.DataFrame(ranked)
        display_cols = [
            'rank_label', 'symbol', 'direction', 'score', 'adx', 'ker',
            'regime', 'level', 'confidence', 'is_valid', 'reason',
            'tp_percent', 'sl_percent', 'entry_price', 'tp_price', 'sl_price',
            'max_price_estimate', 'min_price_estimate',
            'mfe_expected_formatted', 'estimated_time_to_trade', 'persistence',
        ]
        display_cols = [c for c in display_cols if c in df_rank.columns]

        rename_map = {
            'rank_label': 'Rank', 'symbol': 'Activo', 'direction': 'Dir.',
            'score': 'Score', 'adx': 'ADX', 'ker': 'KER',
            'regime': 'Régimen', 'level': 'Nivel', 'confidence': 'Confianza',
            'is_valid': 'Aprobada', 'reason': 'Razón',
            'tp_percent': 'TP %', 'sl_percent': 'SL %',
            'entry_price': 'Entrada $', 'tp_price': 'TP $', 'sl_price': 'SL $',
            'max_price_estimate': 'Máx estimado $',
            'min_price_estimate': 'Mín estimado $',
            'mfe_expected_formatted': 'Amplitud %',
            'estimated_time_to_trade': '⏱️ Próximo (min)',
            'persistence': 'Persistencia',
        }
        df_display = df_rank[display_cols].rename(columns=rename_map)

        def _safe_str(s, k):
            return s.get(k, '')

        st.dataframe(df_display, use_container_width=True, height=600)
    else:
        st.info("No hay señales disponibles. Presioná 'Actualizar Ranking'.")

    st.markdown("---")
    st.subheader("📊 Clasificación por Dirección")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🟢 LONG")
        long_valid = classified.get('long_valid', [])
        long_invalid = classified.get('long_invalid', [])
        if long_valid:
            df_long = pd.DataFrame(long_valid[:10])
            cols = [c for c in ['symbol', 'score', 'adx', 'ker', 'level', 'confidence'] if c in df_long.columns]
            st.dataframe(df_long[cols])
            st.caption(f"✅ Aprobadas: {len(long_valid)}")
        else:
            st.info("No hay LONG aprobadas")
        st.caption(f"⏳ Pendientes: {len(long_invalid)}")

    with col2:
        st.markdown("### 🔴 SHORT")
        short_valid = classified.get('short_valid', [])
        short_invalid = classified.get('short_invalid', [])
        if short_valid:
            df_short = pd.DataFrame(short_valid[:10])
            cols = [c for c in ['symbol', 'score', 'adx', 'ker', 'level', 'confidence'] if c in df_short.columns]
            st.dataframe(df_short[cols])
            st.caption(f"✅ Aprobados: {len(short_valid)}")
        else:
            st.info("No hay SHORT aprobados")
        st.caption(f"⏳ Pendientes: {len(short_invalid)}")

    st.markdown("---")
    st.subheader("✅ Señales Aprobadas (Detalle)")

    if valid:
        for s in valid[:10]:
            with st.expander(f"{s['symbol']} — {s['direction']} (Score: {s['score']:.2f})"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📊 Score", f"{s['score']:.3f}")
                    st.metric("📈 ADX", f"{s['adx']:.1f}")
                    st.metric("📉 KER", f"{s['ker']:.3f}")
                    st.metric("🎯 Régimen", s['regime'])
                    st.metric("🏷️ Nivel", s['level'])
                    st.metric("📊 Volumen ratio", f"{s['volume_ratio']:.2f}x")
                with col2:
                    st.metric("💹 Confianza", f"{s['confidence']:.1f}%")
                    st.metric("📌 Entrada", f"${s['entry_price']:.4f}")
                    st.metric("🛑 SL", f"${s['sl_price']:.4f} ({s['sl_percent']:.2f}%)")
                    st.metric("🎯 TP", f"${s['tp_price']:.4f} ({s['tp_percent']:.2f}%)")
                    st.metric("🔒 Trailing", f"{s['trailing_distance'] * 100:.2f}%")
                    st.metric("📈 MFE esperado", f"{s['mfe_expected'] * 100:.2f}%")
                with col3:
                    st.metric("📈 Máx estimado", f"${s['max_price_estimate']:.4f}")
                    st.metric("📉 Mín estimado", f"${s['min_price_estimate']:.4f}")
                    est_time = s.get('estimated_time_to_trade', 0)
                    st.metric("⏱️ Próximo trade", f"{est_time:.0f} min")
                    st.metric("📊 Persistencia", f"{s.get('persistence', 0):.1f}%")
                    st.metric("🛑 Break-even", f"{s['break_even_trigger'] * 100:.2f}%")

                if s['symbol'] in st.session_state.data_dict:
                    df = st.session_state.data_dict[s['symbol']]
                    if df is not None and not df.empty:
                        tail = df.tail(50)
                        fig = go.Figure(data=[
                            go.Candlestick(
                                x=tail.index,
                                open=tail['open'], high=tail['high'],
                                low=tail['low'], close=tail['close'],
                            )
                        ])
                        fig.add_hline(y=s['entry_price'], line_dash="dash",
                                      line_color="black", annotation_text="Entry")
                        fig.add_hline(y=s['sl_price'], line_dash="dash",
                                      line_color="red", annotation_text="SL")
                        fig.add_hline(y=s['tp_price'], line_dash="dash",
                                      line_color="green", annotation_text="TP")
                        fig.update_layout(
                            height=250,
                            margin=dict(l=0, r=0, t=0, b=0),
                            xaxis_rangeslider_visible=False,
                            paper_bgcolor='white',
                            plot_bgcolor='white',
                            font_color='black',
                        )
                        fig.update_xaxes(gridcolor='#e0e0e0', color='black')
                        fig.update_yaxes(gridcolor='#e0e0e0', color='black')
                        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay señales aprobadas en este momento.")

    st.markdown("---")
    if ranked:
        st.success(f"⏱️ **TIEMPO HASTA LA PRÓXIMA SEÑAL GLOBAL:** {global_time} minutos")
    else:
        st.info("⏱️ **TIEMPO HASTA LA PRÓXIMA SEÑAL GLOBAL:** Sin señales")


# ============================================================
# TAB 2 — BACKTEST LAB
# ============================================================
with tab_backtest:
    st.subheader("🧪 Backtest Lab")

    metrics = st.session_state.bt_metrics
    trades = st.session_state.bt_trades

    if metrics is None or not metrics or 'error' in metrics:
        st.info("👈 Configurá parámetros en la sidebar y presioná **▶ Backtest** para comenzar.")
    else:
        # ---- Métricas principales ----
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Trades", metrics.get('total_trades', 0))
        col2.metric("Win Rate", f"{metrics.get('win_rate', 0):.1f}%")
        col3.metric("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
        col4.metric("Expectancy", f"{metrics.get('expectancy_pct', 0):.2f}%")
        col5.metric("Max DD", f"{metrics.get('max_drawdown_pct', 0):.2f}%")

        col6, col7, col8, col9, col10 = st.columns(5)
        col6.metric("Return total", f"{metrics.get('total_return_pct', 0):.2f}%")
        col7.metric("Sharpe", f"{metrics.get('sharpe', 0):.2f}")
        col8.metric("Sortino", f"{metrics.get('sortino', 0):.2f}")
        col9.metric("Calmar", f"{metrics.get('calmar', 0):.2f}")
        col10.metric("Avg Win/Loss",
                     f"{metrics.get('avg_win_pct', 0):.2f}/{metrics.get('avg_loss_pct', 0):.2f}")

        st.markdown("---")

        # ---- Equity Curve + Drawdown ----
        if trades is not None and not trades.empty:
            trades = trades.sort_values('entry_time').reset_index(drop=True)
            equity = bt_capital * (1 + trades['pnl_pct'] / 100).cumprod()
            peak = equity.cummax()
            dd = (equity - peak) / peak * 100

            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                row_heights=[0.7, 0.3],
                subplot_titles=("Equity Curve", "Drawdown %"),
                vertical_spacing=0.08,
            )
            fig.add_trace(
                go.Scatter(x=trades['entry_time'], y=equity,
                           mode='lines', name='Equity',
                           line=dict(color='green', width=2)),
                row=1, col=1,
            )
            fig.add_trace(
                go.Scatter(x=trades['entry_time'], y=dd,
                           mode='lines', name='Drawdown',
                           line=dict(color='red', width=1),
                           fill='tozeroy', fillcolor='rgba(255,0,0,0.15)'),
                row=2, col=1,
            )
            fig.update_layout(
                height=500, showlegend=True,
                paper_bgcolor='white', plot_bgcolor='white', font_color='black',
                margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

        # ---- Distribución de PnL ----
        if trades is not None and not trades.empty:
            colA, colB = st.columns(2)
            with colA:
                fig_hist = px.histogram(
                    trades, x='pnl_pct', nbins=50,
                    title='Distribución de PnL por trade (%)',
                    color_discrete_sequence=['#4a90e2'],
                )
                fig_hist.add_vline(x=0, line_dash="dash", line_color="black")
                fig_hist.update_layout(
                    height=300,
                    paper_bgcolor='white', plot_bgcolor='white', font_color='black',
                )
                st.plotly_chart(fig_hist, use_container_width=True)

            with colB:
                exit_counts = trades['exit_reason'].value_counts().reset_index()
                exit_counts.columns = ['exit_reason', 'count']
                fig_pie = px.pie(exit_counts, names='exit_reason', values='count',
                                 title='Distribución por motivo de salida')
                fig_pie.update_layout(
                    height=300,
                    paper_bgcolor='white', plot_bgcolor='white', font_color='black',
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        # ---- Heatmap mensual ----
        if trades is not None and not trades.empty:
            trades['month'] = pd.to_datetime(trades['entry_time']).dt.to_period('M').astype(str)
            monthly = trades.groupby('month')['pnl_pct'].agg(['sum', 'count', 'mean']).reset_index()
            fig_m = px.bar(monthly, x='month', y='sum',
                           title='Retorno mensual (%)',
                           color='sum', color_continuous_scale='RdYlGn')
            fig_m.update_layout(
                height=300,
                paper_bgcolor='white', plot_bgcolor='white', font_color='black',
            )
            st.plotly_chart(fig_m, use_container_width=True)

        # ---- Trade Ledger ----
        st.markdown("---")
        st.subheader("📒 Trade Ledger")
        if trades is not None and not trades.empty:
            st.dataframe(trades, use_container_width=True, height=400)

            csv = trades.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Descargar trade ledger (CSV)",
                data=csv,
                file_name=f"daps_trades_{datetime.now():%Y%m%d_%H%M}.csv",
                mime='text/csv',
            )

        # ---- Walk Forward ----
        if st.session_state.bt_wf:
            st.markdown("---")
            st.subheader("🔄 Walk-Forward Results")
            wf = st.session_state.bt_wf
            rows = []
            for w in wf:
                tm = w.get('test_metrics', {})
                if 'total_return_pct' in tm:
                    rows.append({
                        'test_start': w['test_start'].date() if hasattr(w['test_start'], 'date') else w['test_start'],
                        'test_end': w['test_end'].date() if hasattr(w['test_end'], 'date') else w['test_end'],
                        'trades': tm.get('total_trades', 0),
                        'return_pct': tm.get('total_return_pct', 0),
                        'win_rate': tm.get('win_rate', 0),
                        'profit_factor': tm.get('profit_factor', 0),
                    })
            if rows:
                df_wf = pd.DataFrame(rows)
                st.dataframe(df_wf, use_container_width=True)
                colA, colB, colC = st.columns(3)
                colA.metric("OOS mean return", f"{df_wf['return_pct'].mean():.2f}%")
                colB.metric("OOS std return", f"{df_wf['return_pct'].std():.2f}%")
                colC.metric("Ventanas positivas", f"{(df_wf['return_pct'] > 0).mean() * 100:.1f}%")

        # ---- Monte Carlo ----
        if st.session_state.bt_mc:
            st.markdown("---")
            st.subheader(f"🎲 Monte Carlo ({bt_mc_iters} iteraciones)")
            mc = st.session_state.bt_mc
            colA, colB = st.columns(2)
            with colA:
                st.markdown(f"**Return final CI95%:** {mc.get('final_return_ci95')}")
                st.markdown(f"**Max DD CI95%:** {mc.get('max_dd_ci95')}")
                st.markdown(f"**Sharpe CI95%:** {mc.get('sharpe_ci95')}")
            with colB:
                st.markdown(f"**Win Rate CI95%:** {mc.get('win_rate_ci95')}")
                st.markdown(f"**Median return:** {mc.get('median_final_return', 0):.4f}")
                prob_pos = mc.get('prob_positive', 0)
                st.metric("Probabilidad positiva", f"{prob_pos * 100:.1f}%")


# ============================================================
# TAB 3 — COMPARATIVA V1 vs V2
# ============================================================
with tab_compare:
    st.subheader("⚖️ Comparativa V1 (actual) vs V2 (corregido)")

    if st.session_state.bt_data is None:
        st.info("👈 Ejecutá primero un **Backtest** en la pestaña Backtest Lab.")
    else:
        if st.button("🔬 Ejecutar comparativa V1 vs V2", type="primary"):
            data = st.session_state.bt_data
            with st.spinner("📊 Generando señales V1 (legacy)..."):
                sigs_v1 = _generate_signals_for_backtest(data, use_look_ahead_fix=False)
            with st.spinner("📊 Generando señales V2 (corregido)..."):
                sigs_v2 = _generate_signals_for_backtest(data, use_look_ahead_fix=True)

            engine = BacktestEngine(
                initial_capital=bt_capital,
                fee=bt_fee_pct / 100.0,
                slippage=bt_slippage_pct / 100.0,
            )

            with st.spinner("💰 Simulando V1..."):
                t1 = engine.simulate(sigs_v1[sigs_v1['is_valid']], data, max_hold=int(bt_max_hold))
                m1 = engine.compute_metrics(t1)
            with st.spinner("💰 Simulando V2..."):
                t2 = engine.simulate(sigs_v2[sigs_v2['is_valid']], data, max_hold=int(bt_max_hold))
                m2 = engine.compute_metrics(t2)

            # Tabla comparativa
            rows = []
            for key, label in [
                ('total_trades', 'Trades'),
                ('win_rate', 'Win Rate %'),
                ('profit_factor', 'Profit Factor'),
                ('expectancy_pct', 'Expectancy %'),
                ('total_return_pct', 'Return total %'),
                ('max_drawdown_pct', 'Max DD %'),
                ('sharpe', 'Sharpe'),
                ('sortino', 'Sortino'),
                ('calmar', 'Calmar'),
                ('avg_win_pct', 'Avg Win %'),
                ('avg_loss_pct', 'Avg Loss %'),
            ]:
                v1 = m1.get(key, 'N/A')
                v2 = m2.get(key, 'N/A')
                if isinstance(v1, float):
                    v1 = f"{v1:.3f}"
                if isinstance(v2, float):
                    v2 = f"{v2:.3f}"
                rows.append({'Métrica': label, 'V1 (actual)': v1, 'V2 (corregido)': v2})

            # LONG / SHORT distribution
            for label, sigs in [('V1', sigs_v1), ('V2', sigs_v2)]:
                app = sigs[sigs['is_valid']]
                longs = (app['direction'] == 'LONG').sum()
                shorts = (app['direction'] == 'SHORT').sum()
                rows.append({
                    'Métrica': f'LONG aprobadas ({label})',
                    'V1 (actual)': longs if label == 'V1' else '-',
                    'V2 (corregido)': longs if label == 'V2' else '-',
                })
                rows.append({
                    'Métrica': f'SHORT aprobadas ({label})',
                    'V1 (actual)': shorts if label == 'V1' else '-',
                    'V2 (corregido)': shorts if label == 'V2' else '-',
                })

            df_cmp = pd.DataFrame(rows)
            st.dataframe(df_cmp, use_container_width=True)

            # Distribución de direcciones
            colA, colB = st.columns(2)
            with colA:
                st.markdown("### V1 (actual)")
                app1 = sigs_v1[sigs_v1['is_valid']]
                if not app1.empty:
                    counts1 = app1['direction'].value_counts().reset_index()
                    counts1.columns = ['direction', 'count']
                    fig = px.pie(counts1, names='direction', values='count',
                                 color='direction',
                                 color_discrete_map={'LONG': '#2ecc71', 'SHORT': '#e74c3c'})
                    fig.update_layout(height=300, paper_bgcolor='white', font_color='black')
                    st.plotly_chart(fig, use_container_width=True)
            with colB:
                st.markdown("### V2 (corregido)")
                app2 = sigs_v2[sigs_v2['is_valid']]
                if not app2.empty:
                    counts2 = app2['direction'].value_counts().reset_index()
                    counts2.columns = ['direction', 'count']
                    fig = px.pie(counts2, names='direction', values='count',
                                 color='direction',
                                 color_discrete_map={'LONG': '#2ecc71', 'SHORT': '#e74c3c'})
                    fig.update_layout(height=300, paper_bgcolor='white', font_color='black')
                    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# TAB 4 — POR TIER (S/A/B/NO-TIER)
# ============================================================
with tab_tiers:
    st.subheader("🏷️ Análisis por Tier (S / A / B / NO-TIER)")

    trades = st.session_state.bt_trades
    if trades is None or trades.empty:
        st.info("👈 Ejecutá primero un **Backtest** en la pestaña Backtest Lab.")
    else:
        tiers = ['S-TIER', 'A-TIER', 'B-TIER', 'NO-TIER']
        summary = []
        for tier in tiers:
            subset = trades[trades['level'] == tier]
            if subset.empty:
                summary.append({
                    'Tier': tier, 'Trades': 0, 'Pct': 0.0,
                    'WinRate %': 0.0, 'PF': 0.0, 'Expectancy %': 0.0,
                    'Avg Return %': 0.0, 'Max Win %': 0.0, 'Max Loss %': 0.0,
                    'LONG': 0, 'SHORT': 0,
                })
                continue

            wins = subset[subset['pnl_pct'] > 0]
            losses = subset[subset['pnl_pct'] <= 0]
            wr = len(wins) / len(subset) * 100
            gp = wins['pnl_pct'].sum() if not wins.empty else 0
            gl = abs(losses['pnl_pct'].sum()) if not losses.empty else 1e-9
            pf = gp / gl if gl > 0 else 0
            exp = (wr / 100) * (wins['pnl_pct'].mean() if not wins.empty else 0) \
                  + (1 - wr / 100) * (losses['pnl_pct'].mean() if not losses.empty else 0)

            summary.append({
                'Tier': tier,
                'Trades': len(subset),
                'Pct': len(subset) / len(trades) * 100,
                'WinRate %': wr,
                'PF': pf,
                'Expectancy %': exp,
                'Avg Return %': subset['pnl_pct'].mean(),
                'Max Win %': wins['pnl_pct'].max() if not wins.empty else 0,
                'Max Loss %': losses['pnl_pct'].min() if not losses.empty else 0,
                'LONG': (subset['direction'] == 'LONG').sum(),
                'SHORT': (subset['direction'] == 'SHORT').sum(),
            })

        df_tiers = pd.DataFrame(summary)
        st.dataframe(df_tiers, use_container_width=True)

        st.markdown("---")
        st.subheader("📊 Distribución por Tier")
        fig_tier = px.bar(
            df_tiers, x='Tier', y='Trades',
            color='Tier',
            color_discrete_map={
                'S-TIER': '#8e44ad', 'A-TIER': '#3498db',
                'B-TIER': '#95a5a6', 'NO-TIER': '#e74c3c',
            },
            title='Cantidad de trades por tier',
        )
        fig_tier.update_layout(
            height=350, paper_bgcolor='white',
            plot_bgcolor='white', font_color='black',
        )
        st.plotly_chart(fig_tier, use_container_width=True)


# ============================================================
# PIE DE PÁGINA
# ============================================================
st.markdown("---")
st.caption(
    f"DAPS Ω Trading Engine v{VERSION} — "
    f"Última actualización: {st.session_state.last_refresh or 'Nunca'} — "
    f"{len(SYMBOLS)} activos configurados"
)
