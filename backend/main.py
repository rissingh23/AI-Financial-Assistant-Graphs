import uvicorn
import json
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # ✅ Use backend suitable for servers
from fastapi.responses import FileResponse
import matplotlib.pyplot as plt
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ----------------------------
# Setup
# ----------------------------
client = OpenAI(api_key=open('API_KEY', 'r').read())
app = FastAPI()

# For dev, allow all frontend origins (adjust for prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_messages = []

# ----------------------------
# Functions
# ----------------------------
def get_stock_price(ticker):
    return str(yf.Ticker(ticker).history(period='1y').iloc[-1].Close)

def calculate_SMA(ticker, window):
    data = yf.Ticker(ticker).history(period='1y').Close
    return str(data.rolling(window=window).mean().iloc[-1])

def calculate_EMA(ticker, window):
    data = yf.Ticker(ticker).history(period='1y').Close
    return str(data.ewm(span=window, adjust=False).mean().iloc[-1])

def calculate_RSI(ticker):
    data = yf.Ticker(ticker).history(period='1y').Close
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=14 - 1, adjust=False).mean()
    ema_down = down.ewm(com=14 - 1, adjust=False).mean()
    rs = ema_up / ema_down
    return str(100 - (100 / (1 + rs)).iloc[-1])

def calculate_MACD(ticker):
    data = yf.Ticker(ticker).history(period='1y').Close
    short_EMA = data.ewm(span=12, adjust=False).mean()
    long_EMA = data.ewm(span=26, adjust=False).mean()
    MACD = short_EMA - long_EMA
    signal = MACD.ewm(span=9, adjust=False).mean()
    MACD_histogram = MACD - signal
    return f'{MACD[-1]}, {signal[-1]}, {MACD_histogram[-1]}'

def plot_stock_price(ticker):
    data = yf.Ticker(ticker).history(period='1y')
    plt.figure(figsize=(10, 5))
    plt.plot(data.index, data.Close)
    plt.title(f'{ticker} Stock Price Over Last Year')
    plt.xlabel('Date')
    plt.ylabel('Stock Price ($)')
    plt.grid(True)
    plt.savefig('stock.png')
    plt.close()
    return "Chart saved as stock.png"

available_functions = {
    'get_stock_price': get_stock_price,
    'calculate_SMA': calculate_SMA,
    'calculate_EMA': calculate_EMA,
    'calculate_RSI': calculate_RSI,
    'calculate_MACD': calculate_MACD,
    'plot_stock_price': plot_stock_price
}

functions = [  
    {
        'name': 'get_stock_price',
        'description': 'Gets the latest stock price.',
        'parameters': {
            'type': 'object',
            'properties': {'ticker': {'type': 'string'}},
            'required': ['ticker']
        }
    },
    {
        'name': 'calculate_SMA',
        'description': 'Simple Moving Average.',
        'parameters': {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'},
                'window': {'type': 'integer'}
            },
            'required': ['ticker', 'window']
        }
    },
    {
        'name': 'calculate_EMA',
        'description': 'Exponential Moving Average.',
        'parameters': {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'},
                'window': {'type': 'integer'}
            },
            'required': ['ticker', 'window']
        }
    },
    {
        'name': 'calculate_RSI',
        'description': 'Relative Strength Index.',
        'parameters': {
            'type': 'object',
            'properties': {'ticker': {'type': 'string'}},
            'required': ['ticker']
        }
    },
    {
        'name': 'calculate_MACD',
        'description': 'MACD indicator.',
        'parameters': {
            'type': 'object',
            'properties': {'ticker': {'type': 'string'}},
            'required': ['ticker']
        }
    },
    {
        'name': 'plot_stock_price',
        'description': 'Plot stock price and save image.',
        'parameters': {
            'type': 'object',
            'properties': {'ticker': {'type': 'string'}},
            'required': ['ticker']
        }
    }
]

# ----------------------------
# API Request Schema
# ----------------------------
class ChatRequest(BaseModel):
    user_input: str

# ----------------------------
# Endpoint
# ----------------------------
@app.post("/chat")
def chat(chat: ChatRequest):
    user_input = chat.user_input
    messages = [{"role": "user", "content": user_input}]

    try:
        # 1. First call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=[{"type": "function", "function": f} for f in functions],
            tool_choice="auto"
        )

        response_msg = response.choices[0].message

        if response_msg.tool_calls:
            # 2. Add assistant message with tool_calls
            messages.append({
                "role": "assistant",
                "tool_calls": [tc.model_dump() for tc in response_msg.tool_calls],
                "content": None
            })

            for tool_call in response_msg.tool_calls:
                function_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                args_dict = args if isinstance(args, dict) else {}

                function_to_call = available_functions.get(function_name)
                if function_to_call:
                    function_response = function_to_call(**args_dict)

                    # 3. Add tool result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": function_response
                    })

            # 4. Final assistant response
            second_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )

            reply = second_response.choices[0].message.content
            return {"reply": reply}

        else:
            # No tools needed
            reply = response_msg.content
            return {"reply": reply}

    except Exception as e:
        logger.exception("Error in /chat endpoint")
        raise HTTPException(status_code=500, detail=str(e))
    



@app.get("/chart")
def get_chart():
    return FileResponse("stock.png", media_type="image/png")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
