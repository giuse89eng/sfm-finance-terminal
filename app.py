import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="SFM Slim Terminal", layout="wide")

st.title("🏦 SFM Intelligence Terminal")

# --- RICERCA ---
ticker = st.text_input("Inserisci Ticker (es: TS, AAPL, ENI.MI)", "TS").upper()

if ticker:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        
        if not hist.empty:
            # --- DATI E DCF ---
            st.header(f"Analisi: {info.get('longName', ticker)}")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Prezzo Attuale", f"${info.get('currentPrice', 0)}")
            col2.metric("Dividend Yield", f"{info.get('dividendYield', 0)*100:.2f}%")
            col3.metric("Market Cap", f"${info.get('marketCap', 0)/1e9:.2f}B")

            st.divider()
            st.subheader("💎 Valutazione Intrinseca (Modello SFM)")
            
            cf = stock.cashflow
            if 'Free Cash Flow' in cf.index:
                fcf = cf.loc['Free Cash Flow'].iloc[0]
                pfn = info.get('totalCash', 0) - info.get('totalDebt', 0)
                
                c1, c2 = st.columns(2)
                wacc = c1.slider("Tasso Sconto (WACC) %", 5.0, 15.0, 9.0) / 100
                growth = c2.slider("Crescita Annuale %", 0.0, 20.0, 5.0) / 100
                
                # Calcolo DCF Semplificato
                term_val = (fcf * (1 + 0.02)) / (wacc - 0.02)
                fair_value = (((fcf * (1+growth)) + term_val) + pfn) / info.get('sharesOutstanding', 1)
                margine = (1 - (info.get('currentPrice') / fair_value)) * 100
                
                st.metric("Fair Value Stimato", f"${fair_value:.2f}", f"Margine: {margine:.1f}%")
            else:
                st.warning("Dati Free Cash Flow non disponibili per il calcolo automatico.")

            # --- EXCEL ---
            st.divider()
            buf = io.BytesIO() # Se dà errore 'io', aggiungi 'import io' in alto
            import io
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer: # se non hai xlsxwriter usa openpyxl
                hist.to_excel(writer, sheet_name='Dati')
            st.download_button("📥 Scarica Dati Excel", buf.getvalue(), f"{ticker}_data.xlsx")

            # --- GRAFICO IN FONDO ---
            st.divider()
            st.subheader("📈 Analisi Tecnica")
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='Price'), row=1, col=1)
            
            # RSI veloce
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            hist['RSI'] = 100 - (100 / (1 + (gain/loss)))
            
            fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], name='RSI', line=dict(color='orange')), row=2, col=1)
            fig.update_layout(template='plotly_dark', height=600, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Errore: Ticker non trovato o dati mancanti. ({e})")