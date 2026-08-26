# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import logging
from data_engine import DataEngine
from config import (
    INITIAL_CAPITAL, DEFAULT_PARAMS, VERSION,
    PROJECT_NAME, TIMEFRAME, SYMBOLS
)
from signal_engine import Signal, rank_signals, classify_by_direction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=f"{PROJECT_NAME}",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS para modo claro y legibilidad
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
# SIDEBAR
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
    st.caption(f"TP: {DEFAULT_PARAMS['tp_mult_s']}× ATR (S-TIER)")
    st.caption(f"SL: {DEFAULT_PARAMS['sl_mult_s']}× ATR (S-TIER)")

    st.markdown("---")
    st.header("🔄 Acciones")
    refresh_btn = st.button("🔄 Actualizar Ranking", type="primary", use_container_width=True)

    st.markdown("---")
    st.header("📊 Estado")
    st.caption(f"Última actualización: {st.session_state.get('last_refresh', 'Nunca')}")
    st.caption(f"Señales aprobadas: {len(st.session_state.get('valid_signals', []))}")
    st.caption(f"Señales totales: {len(st.session_state.get('ranked_signals', []))}")

# ============================================================
# INICIALIZACIÓN
# ============================================================
if 'data_engine' not in st.session_state:
    with st.spinner("🔌 Inicializando motor de datos..."):
        st.session_state.data_engine = DataEngine()
        st.session_state.symbols = SYMBOLS
        st.session_state.signals = []
        st.session_state.valid_signals = []
        st.session_state.ranked_signals = []
        st.session_state.classified = {}
        st.session_state.last_refresh = None
        st.session_state.data_dict = {}

# ============================================================
# FUNCIONES
# ============================================================
def refresh_ranking():
    de = st.session_state.data_engine
    symbols = st.session_state.symbols
    signals = []
    data_dict = {}
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, sym in enumerate(symbols):
        status_text.text(f"Escaneando {sym}... ({i+1}/{len(symbols)})")
        df = de.fetch_ohlcv(sym, limit=300)
        if df is not None and not df.empty:
            data_dict[sym] = df
            s = Signal(sym, df, DEFAULT_PARAMS)
            signals.append(s.to_dict())
        progress_bar.progress((i + 1) / len(symbols))

    progress_bar.empty()
    status_text.empty()

    st.session_state.data_dict = data_dict
    st.session_state.signals = signals
    st.session_state.valid_signals = [s for s in signals if s.get('is_valid', False)]
    st.session_state.ranked_signals = rank_signals(signals)
    st.session_state.classified = classify_by_direction(signals)
    st.session_state.last_refresh = datetime.now().strftime("%H:%M:%S")

if refresh_btn or st.session_state.last_refresh is None:
    with st.spinner("🔍 Escaneando activos..."):
        refresh_ranking()
    st.rerun()

# ============================================================
# DASHBOARD
# ============================================================
ranked = st.session_state.get('ranked_signals', [])
valid = st.session_state.get('valid_signals', [])
classified = st.session_state.get('classified', {})

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
    st.metric("⏱️ Próximo trade", f"{st.session_state.get('global_time', 'N/A')} min")

st.markdown("---")

# ============================================================
# TABLA DE RANKING COMPLETO
# ============================================================
st.subheader("🏆 Ranking de Señales (Todas)")

if ranked:
    df_rank = pd.DataFrame(ranked)

    display_cols = [
        'rank_label', 'symbol', 'direction', 'score', 'adx', 'ker',
        'regime', 'level', 'confidence', 'is_valid', 'reason',
        'tp_percent', 'sl_percent', 'entry_price', 'tp_price', 'sl_price',
        'max_price_estimate', 'min_price_estimate',
        'mfe_expected_formatted', 'estimated_time_to_trade', 'persistence'
    ]

    rename_map = {
        'rank_label': 'Rank',
        'symbol': 'Activo',
        'direction': 'Dir.',
        'score': 'Score',
        'adx': 'ADX',
        'ker': 'KER',
        'regime': 'Régimen',
        'level': 'Nivel',
        'confidence': 'Confianza',
        'is_valid': 'Aprobada',
        'reason': 'Razón',
        'tp_percent': 'TP %',
        'sl_percent': 'SL %',
        'entry_price': 'Entrada $',
        'tp_price': 'TP $',
        'sl_price': 'SL $',
        'max_price_estimate': 'Máx estimado $',
        'min_price_estimate': 'Mín estimado $',
        'mfe_expected_formatted': 'Amplitud %',
        'estimated_time_to_trade': '⏱️ Próximo (min)',
        'persistence': 'Persistencia'
    }

    df_display = df_rank[display_cols].rename(columns=rename_map)

    def color_rows(row):
        if row['Aprobada']:
            return ['background-color: #1a3a1a; color: #00ff88'] * len(row)
        else:
            return ['background-color: #3a1a1a; color: #ff6666'] * len(row)

    st.dataframe(
        df_display.style.apply(color_rows, axis=1),
        use_container_width=True,
        height=600
    )
else:
    st.info("No hay señales disponibles. Presiona 'Actualizar Ranking'.")

st.markdown("---")

# ============================================================
# CLASIFICACIÓN POR DIRECCIÓN
# ============================================================
st.subheader("📊 Clasificación por Dirección")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🟢 LONG")
    long_valid = classified.get('long_valid', [])
    long_invalid = classified.get('long_invalid', [])
    if long_valid:
        df_long = pd.DataFrame(long_valid[:10])
        st.dataframe(df_long[['symbol', 'score', 'adx', 'ker', 'level', 'confidence']])
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
        st.dataframe(df_short[['symbol', 'score', 'adx', 'ker', 'level', 'confidence']])
        st.caption(f"✅ Aprobados: {len(short_valid)}")
    else:
        st.info("No hay SHORT aprobados")
    st.caption(f"⏳ Pendientes: {len(short_invalid)}")

st.markdown("---")

# ============================================================
# DETALLE DE SEÑALES APROBADAS
# ============================================================
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
                st.metric("📌 Entrada", f"${s['entry_price']:.2f}")
                st.metric("🛑 SL", f"${s['sl_price']:.2f} ({s['sl_percent']:.2f}%)")
                st.metric("🎯 TP", f"${s['tp_price']:.2f} ({s['tp_percent']:.2f}%)")
                st.metric("🔒 Trailing", f"Distancia: {s['trailing_distance']*100:.2f}%")
                st.metric("📈 MFE esperado", f"{s['mfe_expected']*100:.2f}%")

            with col3:
                st.metric("📈 Máx estimado", f"${s['max_price_estimate']:.2f}")
                st.metric("📉 Mín estimado", f"${s['min_price_estimate']:.2f}")
                est_time = s.get('estimated_time_to_trade', 0)
                st.metric("⏱️ Próximo trade (estimado)", f"{est_time:.0f} min")
                st.metric("📊 Persistencia", f"{s.get('persistence', 0):.1f}%")
                st.metric("🛑 Break-even", f"Trigger: {s['break_even_trigger']*100:.2f}%")

            # Gráfico de velas
            if s['symbol'] in st.session_state.data_dict:
                df = st.session_state.data_dict[s['symbol']]
                if df is not None and not df.empty:
                    fig = go.Figure(data=[
                        go.Candlestick(
                            x=df.index[-50:],
                            open=df['open'][-50:],
                            high=df['high'][-50:],
                            low=df['low'][-50:],
                            close=df['close'][-50:]
                        )
                    ])
                    fig.add_hline(y=s['entry_price'], line_dash="dash", line_color="black", annotation_text="Entry")
                    fig.add_hline(y=s['sl_price'], line_dash="dash", line_color="red", annotation_text="SL")
                    fig.add_hline(y=s['tp_price'], line_dash="dash", line_color="green", annotation_text="TP")
                    fig.add_hline(y=s['max_price_estimate'], line_dash="dot", line_color="gray", annotation_text="Máx")
                    fig.add_hline(y=s['min_price_estimate'], line_dash="dot", line_color="gray", annotation_text="Mín")
                    fig.update_layout(
                        height=250,
                        margin=dict(l=0, r=0, t=0, b=0),
                        xaxis_rangeslider_visible=False,
                        paper_bgcolor='white',
                        plot_bgcolor='white',
                        font_color='black'
                    )
                    fig.update_xaxes(gridcolor='#e0e0e0', color='black')
                    fig.update_yaxes(gridcolor='#e0e0e0', color='black')
                    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No hay señales aprobadas en este momento.")

st.markdown("---")

# ============================================================
# TIEMPO GLOBAL HASTA PRÓXIMA SEÑAL
# ============================================================
if ranked:
    times = [s.get('estimated_time_to_trade', 999) for s in ranked]
    min_time = min(times)
    st.session_state.global_time = min_time
    st.success(f"⏱️ **TIEMPO HASTA LA PRÓXIMA SEÑAL GLOBAL:** {min_time} minutos")
else:
    st.session_state.global_time = "N/A"
    st.info("⏱️ **TIEMPO HASTA LA PRÓXIMA SEÑAL GLOBAL:** Sin señales")

st.markdown("---")

# ============================================================
# PIE DE PÁGINA
# ============================================================
st.caption(f"DAPS Ω Trading Engine v{VERSION} — Última actualización: {st.session_state.get('last_refresh', 'Nunca')} — {len(SYMBOLS)} activos analizados")
