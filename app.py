import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import requests

# SISTEMA DI SICUREZZA: Se la libreria manca, il sito NON si rompe
try:
    from docx import Document
    DOCX_AVAILABLE = True
except Exception:
    DOCX_AVAILABLE = False

st.set_page_config(page_title="SFM Terminal", layout="wide")

def get_ticker_from_name(name):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={name}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        data = res.json()
        return data['quotes'][0]['symbol']
    except: return name

st.title("🏦 SFM Intelligence Terminal")

# --- INPUT E DATI ---
search_query = st.text_input("Cerca Azienda (es: Tenaris, Apple, Tesla)", "Tenaris")
ticker = get_ticker_from_name(search_query)

if ticker:
    stock = yf.Ticker(ticker)
    info = stock.info
    hist = stock.history(period="1y")
    
    if not hist.empty:
        # --- VALUTAZIONE DCF ---
        st.header(f"💎 Valutazione: {info.get('longName', ticker)}")
        
        prezzo_att = info.get('currentPrice', 0)
        div_yield = info.get('dividendYield', 0) * 100
        st.write(f"**Prezzo Attuale:** ${prezzo_att} | **Rendimento Dividendi:** {div_yield:.2f}%")

        # --- SEZIONE DOWNLOAD ---
        st.divider()
        col_w, col_e = st.columns(2)
        
        with col_w:
            if DOCX_AVAILABLE:
                if st.button("Genera Report Word (ITA)"):
                    doc = Document()
                    doc.add_heading(f'Analisi SFM: {info.get("longName")}', 0)
                    doc.add_paragraph(f"Prezzo di mercato: ${prezzo_att}")
                    buffer = io.BytesIO()
                    doc.save(buffer)
                    st.download_button("Scarica Word", buffer.getvalue(), f"Report_{ticker}.docx")
            else:
                st.warning("⚠️ Funzione Word in attivazione. Il grafico sotto è comunque disponibile.")

        with col_e:
            output_ex = io.BytesIO()
            with pd.ExcelWriter(output_ex, engine='openpyxl') as writer:
                hist.tail(60).to_excel(writer, sheet_name='Dati')
            st.download_button("Scarica Excel", output_ex.getvalue(), f"Dati_{ticker}.xlsx")

        # --- GRAFICO A FINE PAGINA (SEMPRE VISIBILE) ---
        st.divider()
        st.subheader("📈 Analisi Tecnica e RSI")
        
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        hist['RSI'] = 100 - (100 / (1 + (gain/loss)))

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='Prezzo'), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], line=dict(color='orange')), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        fig.update_layout(template='plotly_dark', height=600, xaxis_rangeslider_visible=False, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)