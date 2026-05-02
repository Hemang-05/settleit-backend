from fastapi import APIRouter
from supabase import create_client
import os
import random
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

@router.get("/search")
def search_players(q: str, sport: str = "cricket"):
    query = q.strip().lower()

    # Role keyword mapping — keys are search terms, values are matching DB roles
    role_keywords = {
        "fast bowler": ["Fast Bowler"],
        "pace bowler": ["Fast Bowler"],
        "pacer": ["Fast Bowler"],
        "fast": ["Fast Bowler"],
        "pace": ["Fast Bowler"],
        "leg spin": ["Leg Spin Bowler"],
        "leg spinner": ["Leg Spin Bowler"],
        "off spin": ["Off Spin Bowler"],
        "off spinner": ["Off Spin Bowler"],
        "wrist spin": ["Leg Spin Bowler", "Left Arm Wrist Spinner"],
        "spinner": ["Leg Spin Bowler", "Off Spin Bowler", "Spin Bowler", "Left Arm Wrist Spinner"],
        "spin bowler": ["Leg Spin Bowler", "Off Spin Bowler", "Spin Bowler", "Left Arm Wrist Spinner"],
        "spin": ["Leg Spin Bowler", "Off Spin Bowler", "Spin Bowler", "Left Arm Wrist Spinner"],
        "bowler": ["Fast Bowler", "Leg Spin Bowler", "Off Spin Bowler", "Spin Bowler", "Left Arm Wrist Spinner"],
        "batsman": ["Top Order Bat", "Middle Order Bat"],
        "batter": ["Top Order Bat", "Middle Order Bat"],
        "batsmen": ["Top Order Bat", "Middle Order Bat"],
        "opener": ["Top Order Bat"],
        "top order": ["Top Order Bat"],
        "middle order": ["Middle Order Bat"],
        "allrounder": ["All Rounder"],
        "all rounder": ["All Rounder"],
        "all-rounder": ["All Rounder"],
        "wicket keeper": ["Wicket Keeper Bat"],
        "wicketkeeper": ["Wicket Keeper Bat"],
        "wicket": ["Wicket Keeper Bat"],
        "keeper": ["Wicket Keeper Bat"],
        "wk": ["Wicket Keeper Bat"],
    }

    # Try longest keyword match first (more specific matches win)
    matched_roles = None
    for keyword in sorted(role_keywords.keys(), key=len, reverse=True):
        if keyword in query:
            matched_roles = role_keywords[keyword]
            break

    if matched_roles:
        result = supabase.table("players")\
            .select("*")\
            .eq("sport", sport)\
            .in_("role", matched_roles)\
            .order("peak_rating", desc=True)\
            .limit(50)\
            .execute()
        return result.data or []

    # Search by name, nationality, and role — merge all results
    name_results = supabase.table("players")\
        .select("*")\
        .eq("sport", sport)\
        .ilike("name", f"%{query}%")\
        .limit(50)\
        .execute()

    nationality_results = supabase.table("players")\
        .select("*")\
        .eq("sport", sport)\
        .ilike("nationality", f"%{query}%")\
        .limit(50)\
        .execute()

    role_results = supabase.table("players")\
        .select("*")\
        .eq("sport", sport)\
        .ilike("role", f"%{query}%")\
        .limit(50)\
        .execute()

    seen = set()
    merged = []
    for p in (name_results.data or []) + (nationality_results.data or []) + (role_results.data or []):
        if p["id"] not in seen:
            seen.add(p["id"])
            merged.append(p)

    # Sort by peak_rating descending for better results
    merged.sort(key=lambda p: p.get("peak_rating", 0), reverse=True)

    return merged


@router.get("/presets")
def get_preset_teams(sport: str = "cricket"):
    result = supabase.table("preset_teams")\
        .select("*")\
        .eq("sport", sport)\
        .order("year", desc=False)\
        .execute()
    return result.data or []

@router.get("/preset/{team_key}")
def get_preset_squad(team_key: str):
    result = supabase.table("players")\
        .select("*")\
        .contains("preset_teams", [team_key])\
        .order("peak_rating", desc=True)\
        .execute()
    # Cap at 11 players per squad
    data = result.data or []
    return data[:11]


@router.get("/autofill")
def autofill_team(sport: str = "cricket", count: int = 11, exclude: str = ""):
    """
    AI autofill — builds a balanced team with proper role distribution.
    Tries to pick: 1 keeper, 4 batsmen, 2 allrounders, 4 bowlers
    """
    exclude_ids = [e for e in exclude.split(",") if e.strip()]

    def fetch_by_role(roles, limit=10):
        result = supabase.table("players")\
            .select("*")\
            .eq("sport", sport)\
            .in_("role", roles)\
            .order("peak_rating", desc=True)\
            .limit(limit)\
            .execute()
        players = result.data or []
        return [p for p in players if p["id"] not in exclude_ids]

    keepers = fetch_by_role(["Wicket Keeper Bat"], 5)
    batsmen = fetch_by_role(["Top Order Bat", "Middle Order Bat"], 15)
    allrounders = fetch_by_role(["All Rounder"], 8)
    bowlers = fetch_by_role(["Fast Bowler", "Leg Spin Bowler", "Off Spin Bowler"], 15)

    team = []
    used_ids = set(exclude_ids)

    def pick(pool, n):
        available = [p for p in pool if p["id"] not in used_ids]
        # shuffle top players for variety
        top = available[:max(n * 2, 6)]
        random.shuffle(top)
        chosen = top[:n]
        for p in chosen:
            used_ids.add(p["id"])
        return chosen

    # Build balanced XI
    team += pick(keepers, min(1, count))
    team += pick(batsmen, min(4, count - len(team)))
    team += pick(allrounders, min(2, count - len(team)))
    team += pick(bowlers, min(4, count - len(team)))

    # Fill remaining slots if needed
    if len(team) < count:
        all_players = supabase.table("players")\
            .select("*").eq("sport", sport)\
            .order("peak_rating", desc=True).limit(50).execute()
        remaining = [p for p in (all_players.data or []) if p["id"] not in used_ids]
        random.shuffle(remaining)
        team += remaining[:count - len(team)]

    return team[:count]
    
    # from fastapi import APIRouter
# from supabase import create_client
# import os
# from dotenv import load_dotenv

# load_dotenv()

# router = APIRouter()
# supabase = create_client(
#     os.getenv("SUPABASE_URL"),
#     os.getenv("SUPABASE_SERVICE_KEY")
# )

# @router.get("/search")
# def search_players(q: str, sport: str = "cricket"):
#     result = supabase.table("players")\
#         .select("*")\
#         .eq("sport", sport)\
#         .ilike("name", f"%{q}%")\
#         .limit(10)\
#         .execute()
#     return result.data