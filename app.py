import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import requests

# Configurazione pagina
st.set_page_config(page_title="SFM Terminal", layout="wide")

# Funzione per trovare il Ticker dal nome (es. Tenaris -> TS)
def trova_ticker(nome):
    try:
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

# Ricerca azienda
nome_input = st.text_input("Inserisci Nome Azienda o Ticker", "Tenaris")
ticker = trova_ticker(nome_input)
st.info(f"Analizzando il Ticker: {ticker}")

if ticker:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")

        if not hist.empty:
            # --- PARTE 1: DATI E DCF ---
            st.header(f"Valutazione: {info.get('longName', ticker)}")
            
            c1, c2 = st.columns(2)
            c1.metric("Prezzo Attuale", f"${info.get('currentPrice', 0)}")
            c2.metric("Rendimento Dividendi", f"{info.get('dividendYield', 0)*100:.2f}%")

            st.divider()
            st.subheader("💎 Valutazione Intrinseca (DCF)")
            
            cf = stock.cashflow
            if 'Free Cash Flow' in cf.index:
                fcf = cf.loc['Free Cash Flow'].iloc[0]
                pfn = info.get('totalCash', 0) - info.get('totalDebt', 0)
                
                # Input per il calcolo
                wacc = st.slider("Tasso Sconto (WACC) %", 5.0, 15.0, 9.0) / 100
                crescita = st.slider("Crescita Attesa %", 0.0, 20.0, 5.0) / 100
                
                # Calcolo DCF rapido
                valore_terminale = (fcf * 1.02) / (wacc - 0.02)
                fair_value = ((fcf * (1 + crescita) + valore_terminale) + pfn) / info.get('sharesOutstanding', 1)
                margine = (1 - (info.get('currentPrice') / fair_value)) * 100
                
                st.metric("Fair Value", f"${fair_value:.2f}", f"Margine: {margine:.1f}%")
            
            # --- PARTE 2: EXCEL ---
            st.divider()
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                hist.to_excel(writer, sheet_name='Dati_Storici')
            
            st.download_button(
                label="📥 Scarica Report Excel",
                data=buffer.getvalue(),
                file_name=f"Analisi_{ticker}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # --- PARTE 3: GRAFICO (IN FONDO) ---
            st.divider()
            st.subheader("📈 Analisi Tecnica")
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='Price'), row=1, col=1)
            
            # RSI
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            hist['RSI'] = 100 - (100 / (1 + (gain/loss)))
            
            fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], name='RSI', line=dict(color='orange')), row=2, col=1)
            fig.update_layout(template='plotly_dark', height=600, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Errore: {e}")