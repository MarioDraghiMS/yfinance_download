from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import io

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "yfinance API is running"})

@app.route("/api/ohlcv")
def get_ohlcv():
    ticker = request.args.get("ticker", "").upper().strip()
    period = request.args.get("period", "1y")
    interval = request.args.get("interval", "1d")

    if not ticker:
        return jsonify({"error": "Podaj ticker (np. AAPL, TSLA, PKN.WA)"}), 400

    valid_periods = ["1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"]
    valid_intervals = ["1m","2m","5m","15m","30m","60m","90m","1h","1d","5d","1wk","1mo","3mo"]

    if period not in valid_periods:
        return jsonify({"error": f"Nieprawidłowy okres. Dozwolone: {valid_periods}"}), 400
    if interval not in valid_intervals:
        return jsonify({"error": f"Nieprawidłowy interwał. Dozwolone: {valid_intervals}"}), 400

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)

        if df.empty:
            return jsonify({"error": f"Brak danych dla tickera '{ticker}'. Sprawdź czy ticker jest poprawny."}), 404

        df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
        df = df[["Open", "High", "Low", "Close", "Volume"]].round(4)
        df.index.name = "Date"
        df = df.reset_index()
        df["Date"] = df["Date"].astype(str)

        return jsonify({
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "rows": len(df),
            "data": df.to_dict(orient="records")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ohlcv/csv")
def get_ohlcv_csv():
    ticker = request.args.get("ticker", "").upper().strip()
    period = request.args.get("period", "1y")
    interval = request.args.get("interval", "1d")

    if not ticker:
        return jsonify({"error": "Podaj ticker"}), 400

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)

        if df.empty:
            return jsonify({"error": f"Brak danych dla '{ticker}'"}), 404

        df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
        df = df[["Open", "High", "Low", "Close", "Volume"]].round(4)
        df.index.name = "Date"

        output = io.StringIO()
        df.to_csv(output)
        output.seek(0)

        filename = f"{ticker}_{period}_{interval}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/info")
def get_info():
    ticker = request.args.get("ticker", "").upper().strip()
    if not ticker:
        return jsonify({"error": "Podaj ticker"}), 400
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        fields = ["shortName", "longName", "sector", "industry", "country",
                  "currency", "exchange", "marketCap", "regularMarketPrice"]
        result = {k: info.get(k) for k in fields if info.get(k) is not None}
        result["ticker"] = ticker
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
