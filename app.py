import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import requests

st.set_page_config(page_title="SFM Financial Terminal", layout="wide")

# --- FUNZIONE RICERCA NOME -> TICKER ---
def cerca_ticker(nome):
    try:
        # Usa l'API di Yahoo per trovare il ticker dal nome
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={nome}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data['quotes']:
            return data['quotes'][0]['symbol']
        return nome
    except:
        return nome

st.title("🏦 SFM Intelligence Terminal")

# --- INPUT INTELLIGENTE ---
nome_input = st.text_input("Inserisci Nome Azienda o Ticker (es: Tenaris, Nvidia, TS, AAPL)", "Tenaris")
ticker = cerca_ticker(nome_input)
st.caption(f"Analisi basata sul Ticker: **{ticker}**")

if ticker:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        
        if not hist.empty:
            # --- SEZIONE 1: DATI AZIENDALI ---
            st.header(f"Analisi Fondamentale: {info.get('longName', ticker)}")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Prezzo", f"${info.get('currentPrice', 0)}")
            c2.metric("Dividendo", f"{info.get('dividendYield', 0)*100:.2f}%")
            c3.metric("Capitalizzazione", f"${info.get('marketCap', 0)/1e9:.2f}B")

            # --- SEZIONE 2: VALUTAZIONE DCF (LOGICA EXCEL SFM) ---
            st.divider()
            st.subheader("💎 Calcolo Valore Intrinseco (DCF)")
            
            cf = stock.cashflow
            fair_value = 0
            if 'Free Cash Flow' in cf.index:
                fcf = cf.loc['Free Cash Flow'].iloc[0]
                pfn = info.get('totalCash', 0) - info.get('totalDebt', 0)
                
                col_a, col_b = st.columns(2)
                wacc = col_a.slider("WACC %", 5.0, 15.0, 9.0) / 100
                crescita = col_b.slider("Crescita %", 0.0, 20.0, 5.0) / 100
                
                # Formula DCF semplificata (simile al tuo excel)
                tv = (fcf * (1 + 0.02)) / (wacc - 0.02)
                fair_value = (((fcf * (1 + crescita)) + tv) + pfn) / info.get('sharesOutstanding', 1)
                margine = (1 - (info.get('currentPrice') / fair_value)) * 100
                
                st.metric("Fair Value Stimato", f"${fair_value:.2f}", f"Margine: {margine:.1f}%")
            else:
                st.warning("Dati Free Cash Flow non disponibili per questo titolo.")

            # --- SEZIONE 3: EXPORT EXCEL ---
            st.divider()
            st.subheader("📥 Esporta Analisi")
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                hist.to_excel(writer, sheet_name='Prezzi_Storici')
                if 'fair_value' in locals():
                    df_val = pd.DataFrame({'Parametro': ['Ticker', 'Fair Value', 'Margine'], 'Valore': [ticker, fair_value, margine]})
                    df_val.to_excel(writer, sheet_name='Valutazione', index=False)
            
            st.download_button(
                label="📥 Scarica Report Excel",
                data=output.getvalue(),
                file_name=f"Analisi_{ticker}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # --- SEZIONE 4: GRAFICO IN FONDO ---
            st.divider()
            st.subheader("📈 Analisi Tecnica (Candele e RSI)")
            
            # Calcolo RSI
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            hist['RSI'] = 100 - (100 / (1 + (gain/loss)))

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], name='RSI', line=dict(color='orange')), row=2, col=1)
            
            fig.update_layout(template='plotly_dark', height=600, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Errore durante il caricamento: {e}")