from fastapi import FastAPI

from web_interface.server import app as server_app

app = FastAPI()
app.mount("/api", server_app)
