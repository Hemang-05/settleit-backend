from fastapi import APIRouter
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

@router.get("/search")
def search_players(q: str, sport: str = "cricket"):
    result = supabase.table("players")\
        .select("*")\
        .eq("sport", sport)\
        .ilike("name", f"%{q}%")\
        .limit(10)\
        .execute()
    return result.data