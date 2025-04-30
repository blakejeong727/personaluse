from dash import Dash, html, dcc, Input, Output, State, dash_table
import plotly.graph_objects as go
import pandas as pd
import requests

CMC_API_KEY = "bb3c32ee-3be4-4fd0-85b4-ad924bd76e26"

def get_iost_price_usdt():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": "IOST", "convert": "USDT"}
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    return float(data["data"]["IOST"]["quote"]["USDT"]["price"])

def fetch_orderbook_binance():
    url = "https://api.binance.com/api/v3/depth?symbol=IOSTUSDT&limit=1000"
    data = requests.get(url).json()["asks"]
    return pd.DataFrame([[float(p), float(q)] for p, q in data], columns=["price", "quantity"])

def fetch_orderbook_okx():
    url = "https://www.okx.com/api/v5/market/books?instId=IOST-USDT"
    data = requests.get(url).json()["data"][0]["asks"]
    return pd.DataFrame([[float(level[0]), float(level[1])] for level in data], columns=["price", "quantity"])

def fetch_orderbook_upbit():
    url = "https://api.upbit.com/v1/orderbook?markets=KRW-IOST"
    data = requests.get(url).json()[0]["orderbook_units"]
    return pd.DataFrame([[round(float(d["ask_price"]), 2), float(d["ask_size"])] for d in data], columns=["price", "quantity"])

def fetch_orderbook_bithumb():
    url = "https://api.bithumb.com/public/orderbook/IOST_KRW"
    data = requests.get(url).json()["data"]["asks"]
    return pd.DataFrame([[round(float(d["price"]), 2), float(d["quantity"])] for d in data], columns=["price", "quantity"])

def calculate_total(df, target_price):
    filtered = df[df["price"] <= target_price]
    total_tokens = filtered["quantity"].sum()
    total_cost = (filtered["price"] * filtered["quantity"]).sum()
    return total_tokens, total_cost

app = Dash(__name__)
app.title = "IOST Orderbook Dashboard"

app.layout = html.Div([
    html.H1("📈 How Much Sell Order to Clear for IOST +X%"),
    html.Div([
        dcc.Slider(id="pct-slider", min=1, max=20, step=1, value=5,
                   marks={i: f"{i}%" for i in range(1, 21)}, tooltip={"always_visible": True}),
        html.Button("Calculate", id="run-button", n_clicks=0)
    ]),
    dash_table.DataTable(id="result-table", style_cell={"textAlign": "center"}, style_header={"fontWeight": "bold"}),
    html.Div(id="total-summary", style={"fontWeight": "bold", "fontSize": "20px", "marginTop": "20px"})
])

@app.callback(
    Output("result-table", "data"),
    Output("total-summary", "children"),
    Input("run-button", "n_clicks"),
    State("pct-slider", "value")
)
def update_output(n_clicks, target_pct):
    if n_clicks == 0:
        return [], ""

    base_usdt_price = get_iost_price_usdt()
    target_usdt_price = round(base_usdt_price * (1 + target_pct / 100), 6)

    sources = {
        "Binance": ("$", fetch_orderbook_binance(), target_usdt_price),
        "OKX": ("$", fetch_orderbook_okx(), target_usdt_price),
        "Upbit": ("₩", fetch_orderbook_upbit(), None),
        "Bithumb": ("₩", fetch_orderbook_bithumb(), None),
    }

    rows = []
    total_tokens = 0
    total_costs = []

    for name, (unit, df, t_price) in sources.items():
        if t_price is None:
            base_price = df["price"].min()
            t_price = round(base_price * (1 + target_pct / 100), 2 if unit == "₩" else 6)

        tokens, cost = calculate_total(df, t_price)
        total_tokens += tokens
        total_costs.append((name, cost, unit))
        rows.append({
            "Exchange": name,
            "Target Price": f"{unit}{t_price:,.6f}" if unit == "$" else f"{unit}{t_price:,.2f}",
            "Total Tokens": f"{int(tokens):,}",
            "Total Cost": f"{unit}{cost:,.2f}" if unit == "$" else f"{unit}{cost:,.0f}"
        })

    summary = f"🔢 Total Tokens: {int(total_tokens):,}"
    return rows, summary

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8051, debug=True)
