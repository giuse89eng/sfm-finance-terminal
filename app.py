import streamlit as st
import yfinance as yf
import pandas as pd
import io

st.set_page_config(page_title="SFM Value Analyzer", layout="wide")
st.title("🏦 SFM Corporate Value Analyzer")

ticker = st.text_input("Inserisci Ticker (es: TS per Tenaris su NYSE o TEN.MI per Milano)", "TS")

if ticker:
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Recupero dati finanziari
    cf = stock.cashflow
    bs = stock.balance_sheet
    
    if not cf.empty and 'Free Cash Flow' in cf.index:
        st.header(f"Analisi di Bilancio: {info.get('longName')}")
        
        # Dati per il modello DCF
        fcf_ultimo = cf.loc['Free Cash Flow'].iloc[0]
        posizione_fin_netta = info.get('totalCash', 0) - info.get('totalDebt', 0)
        azioni_circolazione = info.get('sharesOutstanding', 1)
        
        # Interfaccia di input per l'utente
        col1, col2 = st.columns(2)
        with col1:
            growth = st.slider("Tasso di Crescita FCF (%)", 0.0, 20.0, 5.0) / 100
            wacc = st.slider("WACC (%)", 5.0, 15.0, 9.0) / 100
        
        # Calcolo Fair Value
        terminal_value = (fcf_ultimo * (1 + 0.02)) / (wacc - 0.02)
        enterprise_value = (fcf_ultimo * (1 + growth)) + terminal_value
        equity_value = enterprise_value + posizione_fin_netta
        fair_value = equity_value / azioni_circolazione
        prezzo_attuale = info.get('currentPrice')
        margine_sicurezza = (1 - (prezzo_attuale / fair_value)) * 100
        
        # Visualizzazione Risultati
        st.metric("Fair Value Stimato", f"${fair_value:.2f}")
        if margine_sicurezza > 0:
            st.success(f"Margine di Sicurezza: {margine_sicurezza:.1f}%")
        else:
            st.error(f"Sopravvalutata del: {abs(margine_sicurezza):.1f}%")

        # Sezione Tesi d'investimento
        st.divider()
        st.subheader("📝 Anteprima Tesi di Investimento")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.write("**Business & Financials:**")
            st.write(f"- Margine Operativo: {info.get('operatingMargins', 0)*100:.1f}%")
            st.write(f"- ROE: {info.get('returnOnEquity', 0)*100:.1f}%")
        with col_t2:
            st.write("**Rischi & Catalizzatori:**")
            st.write("- Esposizione ai prezzi delle materie prime.")
            st.write("- Ciclicità del settore energy.")

        # --- FUNZIONE EXPORT EXCEL ---
        report_data = {
            'Metrica': ['Ticker', 'Prezzo Attuale', 'Fair Value', 'Margine Sicurezza %', 'FCF Ultimo', 'WACC %', 'PFN'],
            'Valore': [ticker, prezzo_attuale, fair_value, margine_sicurezza, fcf_ultimo, wacc*100, posizione_fin_netta]
        }
        df_report = pd.DataFrame(report_data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_report.to_excel(writer, index=False, sheet_name='Analisi DCF')
        
        st.download_button(
            label="📥 Scarica Report Excel (Modello SFM)",
            data=output.getvalue(),
            file_name=f"Analisi_SFM_{ticker}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Dati Free Cash Flow non trovati per questo ticker.")
        # --- MODULO AI TRADING SIGNALS ---
st.divider()
st.subheader("🎯 IA Trading Signals (Analisi Tecnica + Fondamentale)")

# Analisi Tecnica veloce
hist = stock.history(period="60d")
sma_50 = hist['Close'].mean()
prezzo_ora = info.get('currentPrice')

# Logica decisionale IA
st.write(f"Confronto Prezzo (${prezzo_ora:.2f}) vs Media 50gg (${sma_50:.2f})")

decisione = ""
if prezzo_ora < fair_value and prezzo_ora > sma_50:
    decisione = "🟢 SEGNALE: LONG (Sottovalutata + Trend Rialzista)"
    colore = "green"
elif prezzo_ora > fair_value and prezzo_ora < sma_50:
    decisione = "🔴 SEGNALE: SHORT (Sopravvalutata + Trend Ribassista)"
    colore = "red"
else:
    decisione = "🟡 SEGNALE: NEUTRALE (In attesa di conferma)"
    colore = "gray"

st.markdown(f"### :{colore}[{decisione}]")
import plotly.graph_objects as go

# ... (sotto la parte dove scarichi i dati 'hist')

from plotly.subplots import make_subplots
import plotly.graph_objects as go

st.subheader(f"📊 Terminale Avanzato: {ticker}")

# --- CALCOLO INDICATORI ---
# 1. RSI (14 periodi)
delta = hist['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
hist['RSI'] = 100 - (100 / (1 + rs))

# --- CREAZIONE LAYOUT A 3 LIVELLI (Prezzo, Volume, RSI) ---
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.05, 
                    row_heights=[0.5, 0.2, 0.3],
                    subplot_titles=(f'Candlestick {ticker}', 'Volume', 'RSI (14)'))

# 1. Grafico a Candele
fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'],
                low=hist['Low'], close=hist['Close'], name='Prezzo'), row=1, col=1)

# 2. Volume (Barre)
fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name='Volume', 
                marker_color='royalblue', opacity=0.5), row=2, col=1)

# 3. RSI (Linea con soglie 30/70)
fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], name='RSI', 
                line=dict(color='orange', width=2)), row=3, col=1)
# Aggiunta linee di soglia RSI
fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

# Layout Finale Estetico
fig.update_layout(template='plotly_dark', height=800, showlegend=False,
                  xaxis_rangeslider_visible=False)

st.plotly_chart(fig, use_container_width=True)