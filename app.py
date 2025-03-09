import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime as dt
import plotly.graph_objects as go

# Set page configuration
st.set_page_config(
    page_title="Stock Watchlist Dashboard",
    page_icon="📈",
    layout="wide"
)

# Initialize session state for watchlist if it doesn't exist
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']


# Sidebar for adding and removing tickers
st.sidebar.header("Manage Watchlist")

# Add new ticker
new_ticker = st.sidebar.text_input("Add a new ticker:", placeholder="e.g., TSLA")
add_button = st.sidebar.button("Add Ticker")

if add_button and new_ticker:
    # Convert to uppercase
    new_ticker = new_ticker.upper().strip()
    
    # Validate ticker exists
    try:
        ticker_info = yf.Ticker(new_ticker).info
        if 'regularMarketPrice' in ticker_info and ticker_info['regularMarketPrice'] is not None:
            if new_ticker not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_ticker)
                st.sidebar.success(f"Added {new_ticker} to watchlist!")
            else:
                st.sidebar.warning(f"{new_ticker} is already in your watchlist.")
        else:
            st.sidebar.error(f"Could not validate ticker {new_ticker}.")
    except:
        st.sidebar.error(f"Could not validate ticker {new_ticker}.")

# Remove ticker
st.sidebar.subheader("Remove Tickers")
if st.session_state.watchlist:
    ticker_to_remove = st.sidebar.selectbox("Select ticker to remove:", st.session_state.watchlist)
    remove_button = st.sidebar.button("Remove Ticker")
    
    if remove_button:
        st.session_state.watchlist.remove(ticker_to_remove)
        st.sidebar.success(f"Removed {ticker_to_remove} from watchlist!")

# Show current watchlist
st.sidebar.subheader("Current Watchlist")
st.sidebar.write(", ".join(st.session_state.watchlist))

# Function to fetch stock data
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def fetch_stock_data(tickers, period="5d"):
    """Fetch stock data for the given tickers and period."""
    data = {}
    
    for ticker in tickers:
        try:
            # Get historical price data
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            
            if not hist.empty:
                # Basic info
                info = stock.info
                
                # Extract relevant data
                data[ticker] = {
                    'name': info.get('shortName', ticker),
                    'sector': info.get('sector', 'N/A'),
                    'industry': info.get('industry', 'N/A'),
                    'price': info.get('regularMarketPrice', 0),
                    'change_1d': ((hist['Close'].iloc[-1] / hist['Close'].iloc[-2]) - 1) * 100 if len(hist) >= 2 else 0,
                    'change_3d': ((hist['Close'].iloc[-1] / hist['Close'].iloc[-4]) - 1) * 100 if len(hist) >= 4 else 0,
                    'volume': info.get('volume', 0),
                    'market_cap': info.get('marketCap', 0)
                }
            else:
                st.warning(f"Could not fetch data for {ticker}")
        except Exception as e:
            st.warning(f"Error fetching data for {ticker}: {e}")
    
    return data

# Main dashboard area
if st.session_state.watchlist:
    # Fetch data for all tickers in watchlist
    with st.spinner("Fetching stock data..."):
        stock_data = fetch_stock_data(st.session_state.watchlist)
    
    if stock_data:
        # Create dataframe for the heatmap
        heatmap_data = []
        for ticker, data in stock_data.items():
            heatmap_data.append({
                'Ticker': ticker,
                'Name': data['name'],
                'Price': f"${data['price']:.2f}",
                'Return 1D (%)': data['change_1d'],
                'Return 3D (%)': data['change_3d'],
                'Sector': data['sector'],
                'Volume': f"{data['volume']:,}",
                'Market Cap': f"${data['market_cap']/1e9:.2f}B" if data['market_cap'] > 0 else 'N/A'
            })
        
        df = pd.DataFrame(heatmap_data)
        
        # Display basic info table
        st.subheader("Watchlist Overview")
        st.dataframe(
            df[['Ticker', 'Name', 'Price', 'Sector', 'Volume', 'Market Cap']], 
            hide_index=True,
            use_container_width=True
        )
        
        # Create heat map for returns
        st.subheader("Returns Heatmap")
        
        # Define columns for heatmap
        heatmap_cols = ['Return 1D (%)', 'Return 3D (%)']
        
        # Create heatmap dataframe with numeric values
        heatmap_df = df[['Ticker', 'Name'] + heatmap_cols].copy()
        
        # Create the heatmap
        fig = go.Figure()
        
        # Color scale for heatmap (red for negative, green for positive)
        for i, col in enumerate(heatmap_cols):
            # Get values for current column
            values = heatmap_df[col].values
            
            # Create text to display in heatmap cells
            text = [f"{val:.2f}%" for val in values]
            
            # Create hovertext
            hovertext = [f"{ticker} - {name}<br>{col}: {val:.2f}%" 
                         for ticker, name, val in zip(heatmap_df['Ticker'], heatmap_df['Name'], values)]
            
            # Add heatmap trace
            fig.add_trace(go.Heatmap(
                z=[values],
                x=heatmap_df['Ticker'],
                y=[col],
                text=[text],
                texttemplate="%{text}",
                textfont={"size":12},
                colorscale=[[0, 'rgb(255,0,0)'], [0.5, 'rgb(255,255,255)'], [1, 'rgb(0,128,0)']],
                zmid=0,
                zmin=-5,  # Adjust these limits as needed
                zmax=5,   # Adjust these limits as needed
                showscale=False,
                hoverinfo='text',
                hovertext=[hovertext],
            ))
        
        # Update layout
        fig.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(
                tickmode='array',
                tickvals=heatmap_cols,
                ticktext=heatmap_cols
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Stock charts using Finviz
        st.subheader("Stock Charts (Finviz)")
        
        # Create two columns for charts
        cols = st.columns(2)
        
        # Distribute charts across columns
        for i, ticker in enumerate(st.session_state.watchlist):
            col = cols[i % 2]
            with col:
                if ticker in stock_data:
                    st.markdown(f"{stock_data[ticker]['name']} ({ticker})")
                    
                    # Display Finviz chart
                    st.image(f"https://charts2.finviz.com/chart.ashx?t={ticker}", width=600)
                    
                    
    else:
        st.error("Could not fetch data for any tickers in your watchlist. Please try again later.")
else:
    st.info("Your watchlist is empty. Please add some tickers using the sidebar.")

# Footer
st.markdown("---")
