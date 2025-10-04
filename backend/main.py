from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

app = FastAPI(title="My Monorepo API", version="0.1.0")

allow_origins = os.getenv("ALLOW_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"DFSB4-NASA-Hackathon": True}

class EchoIn(BaseModel):
    message: str

@app.post("/api/echo")
def echo(body: EchoIn):
    return {"echo": body.message}

# local test: vicorn main:app --host 0.0.0.0 --port 8000
