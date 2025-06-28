import threading
from flask import Flask
from waitress import serve
from loguru import logger

app = Flask('')

@app.route('/')
def home():
    return "Link Guard Robot is running!"

def run():
    logger.info("Starting web server for keep-alive")
    serve(app, host='0.0.0.0', port=8080)

def keep_alive():
    """Start a simple web server to keep the bot running on Replit"""
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()
    logger.info("Keep-alive web server started")
    return t