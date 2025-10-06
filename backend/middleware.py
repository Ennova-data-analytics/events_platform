from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://www.ennova-events.com",
    "https://ennova-events.com"
]

def setup_middleware(app: FastAPI):
    """Configures and adds all middleware to the FastAPI application"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app 