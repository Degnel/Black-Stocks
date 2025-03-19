import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import pandas as pd
import datetime
from streamlit_plotly_events import plotly_events  # Nécessite l'installation de streamlit-plotly-events

# Importer vos listes de tickers depuis stocks.py
from stocks import SP500_TICKERS, CAC40_TICKERS

st.title("Visualisation Boursière Dynamique")

# --- Sélection de la période ---
time_range_options = ["1j", "1s", "1m", "6m", "1y", "5y", "25y", "Custom"]
selected_time_range = st.sidebar.selectbox("Sélectionnez la plage de temps du graphique :", options=time_range_options)
today = datetime.date.today()
default_start = today - datetime.timedelta(days=365)  # Valeur par défaut pour Custom

interval = "1d"
if selected_time_range == "Custom":
    start_date, end_date = st.sidebar.date_input("Sélectionnez la période", [default_start, today])
else:
    if selected_time_range == "1j":
        start_date = today
        interval = "1m"
    elif selected_time_range == "1s":
        start_date = today - datetime.timedelta(days=7)
        interval = "30m"
    elif selected_time_range == "1m":
        start_date = today - datetime.timedelta(days=30)
    elif selected_time_range == "6m":
        start_date = today - datetime.timedelta(days=182)
    elif selected_time_range == "1y":
        start_date = today - datetime.timedelta(days=365)
    elif selected_time_range == "5y":
        start_date = today - datetime.timedelta(days=5*365)
    elif selected_time_range == "25y":
        start_date = today - datetime.timedelta(days=25*365)
    end_date = today + datetime.timedelta(days=1)

# --- Sélection de la place boursière et du ticker ---
market = st.selectbox("Sélectionnez la place boursière :", options=["CAC40", "S&P"])
if market == "CAC40":
    tickers_list = CAC40_TICKERS
else:
    tickers_list = SP500_TICKERS
selected_ticker = st.selectbox("Sélectionnez une action :", options=sorted(tickers_list))

# --- Chargement des données pour le ticker sélectionné ---
@st.cache_data
def load_data(ticker, start, end, interval):
    return yf.download(ticker, start=start, end=end, progress=False, interval=interval)

data = load_data(selected_ticker, start_date, end_date, interval)

error = False
if data.empty:
    if selected_time_range == "1j":
        start_date -= datetime.timedelta(days=1)
        data = load_data(selected_ticker, start_date, end_date, interval)
        if data.empty:
            error = True
    else:
        error = True

if error:
    st.error("Données non disponibles pour ce symbole dans la période sélectionnée.")
else:
    # Calcul d'une moyenne mobile sur 50 jours
    data["MA50"] = data["Close"].rolling(window=50).mean()
    st.write("Données récupérées pour :", selected_ticker)
    
    # --- Récupération des informations financières supplémentaires ---
    ticker_obj = yf.Ticker(selected_ticker)
    info = ticker_obj.info

    # Récupération de la capitalisation boursière
    market_cap = info.get("marketCap", None)
    # Récupération du PER (price earnings ratio)
    per = info.get("trailingPE", None)
    # Récupération du chiffre d'affaires (totalRevenue ou revenue)
    revenue = info.get("totalRevenue", None)
    if revenue is None:
        revenue = info.get("revenue", None)
    
    # Calcul du ratio Market Cap / Chiffre d'Affaires (CA)
    ratio = market_cap / revenue if (market_cap and revenue and revenue != 0) else None

    # Calcul de la variation totale du prix
    first_price = data["Close"].iloc[0]
    last_price = data["Close"].iloc[-1]
    percentage_change = float(((last_price - first_price) / first_price))

    # Déterminer la couleur de la courbe en fonction de l'évolution du prix
    color = "green" if last_price.item() >= first_price.item() else "red"
    
    # --- Initialisation et configuration du graphique interactif ---
    if "log_scale" not in st.session_state:
        st.session_state["log_scale"] = False

    if st.button("Mettre en " + ("log-scale" if not st.session_state.get("log_scale", False) else "linear")):
        st.session_state["log_scale"] = not st.session_state.get("log_scale", False)
        st.rerun()

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="color: white; font-size: 24px;">Cours de {selected_ticker}</div>
            <div style="color: {color}; font-size: 24px;">{percentage_change:.2%}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["Close"][selected_ticker].values.tolist(),
        mode='lines',
        name='Prix de Clôture',
        line=dict(color=color)
    ))
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["MA50"].values.tolist(),
        mode='lines',
        name='MA 50 jours',
        line=dict(color="orange", dash='dash')
    ))
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Prix",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis_type="linear" if not st.session_state["log_scale"] else "log",
        xaxis=dict(
            showgrid=False,
            title_font_color="white",
            tickfont=dict(color="white")
        ),
        yaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.25)",
            title_font_color="white",
            tickfont=dict(color="white")
        ),
        margin=dict(l=40, r=0, t=0, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(
                color="white"  # Couleur du texte de la légende
            )
        )
    )


    # Capture des clics sur le graphique
    if 'old_click_data' not in st.session_state:
        st.session_state.old_click_data = None
    click_data = plotly_events(fig, override_height=500)
    print(click_data)
    if st.session_state.old_click_data and click_data:
        first_value = st.session_state.old_click_data[0].get("y")
        second_value = click_data[0].get("y")
        if first_value is not None and second_value is not None:
            evolution_pct = ((second_value - first_value) / first_value) * 100
            color = "green" if evolution_pct >= 0 else "red"
            st.markdown(
                f"<h3 style='color:{color};'>Pourcentage d'évolution: {evolution_pct:.2f}%</h3>",
                unsafe_allow_html=True
            )
            st.session_state.old_click_data = click_data
    else:
        st.session_state.old_click_data = click_data


# Affichage des informations
st.markdown("### Informations Financières")
st.markdown(f"**Capitalisation Boursière :** {market_cap if market_cap else 'N/A'}")
st.markdown(f"**PER :** {per if per else 'N/A'}")
st.markdown(f"**Ratio (Market Cap / CA) :** {ratio if ratio else 'N/A'}")

# Ajout d'une sélection de période pour le calcul de la variation de capitalisation boursière
variation_time_range_options = ["1j", "1s", "1m", "6m", "1y"]
selected_variation_time_range = st.sidebar.selectbox("Sélectionnez la plage de temps pour le calcul de la variation :", options=variation_time_range_options)

# Ajout d'un bouton pour lancer le calcul de la variation
if st.sidebar.button("Calculer les variations de capitalisation boursière"):
    # --- Tableau des variations de capitalisation boursière ---
    st.subheader("Top variations de capitalisation boursière")

    @st.cache_data
    def get_market_cap_variation(ticker, period):
        try:
            # Récupérer les données pour la période sélectionnée
            action = yf.Ticker(ticker)
            info = action.info
            shares_outstanding = info.get("sharesOutstanding", None)
            last_price = info['regularMarketPrice']
            if period == "1j":
                start_date = today - datetime.timedelta(days=1)
            elif period == "1s":
                start_date = today - datetime.timedelta(days=7)
            elif period == "1m":
                start_date = today - datetime.timedelta(days=30)
            elif period == "6m":
                start_date = today - datetime.timedelta(days=182)
            elif period == "1y":
                start_date = today - datetime.timedelta(days=365)
            df = yf.download(ticker, start=start_date, end=today, progress=False)
            former_price = df['Close'][ticker]
            if shares_outstanding is None:
                return None, None
            variation = (last_price - former_price) * shares_outstanding
            percentage = (last_price - former_price) / former_price
            return float(variation), f"{float(percentage):.2%}"
        except Exception:
            return None, None

    # Fusionner les tickers des deux places pour analyser toutes les variations
    all_tickers = list(set(SP500_TICKERS + CAC40_TICKERS))
    variations_list = []
    progress_bar = st.progress(0)
    total = len(all_tickers)
    for i, t in enumerate(all_tickers):
        var, per = get_market_cap_variation(t, selected_variation_time_range)
        if var is not None:
            variations_list.append({"Ticker": t, "Variation": var, "Percentage": per})
        progress_bar.progress((i + 1) / total)

    if variations_list:
        df_variations = pd.DataFrame(variations_list)
        df_variations["AbsVariation"] = df_variations["Variation"].abs()
        df_variations = df_variations.sort_values(by="AbsVariation", ascending=False)

        # Fonction pour colorer toute la ligne en fonction de la variation
        def color_row(row):
            color = 'background-color: lightgreen' if row["Variation"] >= 0 else 'background-color: lightcoral'
            return [color] * len(row)

        df_styled = df_variations.style.apply(color_row, axis=1)
        st.dataframe(df_styled)
    else:
        st.write("Aucune variation calculable.")
