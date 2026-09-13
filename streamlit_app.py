# En sidebar, después de "Acciones":
st.markdown("---")
st.header("🧪 Backtest Lab")
bt_symbols = st.multiselect("Activos", SYMBOLS, default=SYMBOLS[:10])
bt_timeframe = st.selectbox("Timeframe", ['5m','15m','1h','4h','1d'], index=2)
bt_start = st.date_input("Fecha inicio", datetime(2025,1,1))
bt_end = st.date_input("Fecha fin", datetime.now())
bt_capital = st.number_input("Capital inicial ($)", value=10000.0, step=1000.0)
bt_fee = st.number_input("Comisión (%)", value=0.1, step=0.01) / 100
bt_slippage = st.number_input("Slippage (%)", value=0.05, step=0.01) / 100
bt_max_hold = st.number_input("Max hold (velas)", value=60, step=10)
bt_risk = st.number_input("Riesgo por trade (%)", value=1.0, step=0.1) / 100

col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    if st.button("▶ Ejecutar Backtest", type="primary"):
        st.session_state.run_backtest = True
with col_b:
    if st.button("▶ Walk Forward"):
        st.session_state.run_wf = True
with col_c:
    if st.button("▶ Monte Carlo"):
        st.session_state.run_mc = True
with col_d:
    if st.button("📥 Exportar CSV"):
        st.session_state.export_results = True
