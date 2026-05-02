from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Any, Optional
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from engine.cricket_engine import build_simulation_prompt, build_phase_prompt

load_dotenv()

router = APIRouter()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")


def parse_ai_json(raw_text):
    """Parse AI response, stripping markdown fences if present"""
    raw = raw_text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    return json.loads(raw)


class SimulationRequest(BaseModel):
    team_a: List[Any]
    team_b: List[Any]
    tactics_a: Any
    tactics_b: Any
    toss: Optional[Any] = None
    sport: str = "cricket"
    format: str = "odi"


class PhaseRequest(BaseModel):
    team_a: List[Any]
    team_b: List[Any]
    tactics_a: Any
    tactics_b: Any
    toss: Any
    format: str = "odi"
    sport: str = "cricket"
    phase: str  # inn1_pp, inn1_mid, inn2_pp, inn2_mid, super_over
    match_state: Any = {}


@router.post("/run")
async def run_simulation(req: SimulationRequest):
    """Legacy single-call simulation (used for test/superover formats)"""
    try:
        prompt = build_simulation_prompt(
            req.team_a, req.team_b, req.tactics_a, req.tactics_b
        )
        response = model.generate_content(prompt)
        result = parse_ai_json(response.text)
        return {"success": True, "data": result}

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/phase")
async def run_phase(req: PhaseRequest):
    """Phase-based simulation for live match experience"""
    try:
        prompt = build_phase_prompt(
            req.team_a, req.team_b,
            req.tactics_a, req.tactics_b,
            req.format, req.phase,
            req.match_state, req.toss
        )
        response = model.generate_content(prompt)
        result = parse_ai_json(response.text)
        return {"success": True, "data": result}

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))