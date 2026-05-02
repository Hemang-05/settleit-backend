from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import players, simulation

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(players.router, prefix="/api/players")
app.include_router(simulation.router, prefix="/api/simulation")

@app.get("/")
def root():
    return {"status": "Settle it API running 🚀"}