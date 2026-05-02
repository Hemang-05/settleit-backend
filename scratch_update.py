import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Update David Warner
print("Updating David Warner...")
supabase.table("players").update({"preset_teams": ["2015_odi_australia", "2023_odi_australia"]}).eq("name", "David Warner").execute()

# Update Michael Hussey
print("Updating Michael Hussey...")
supabase.table("players").update({"preset_teams": ["2007_odi_australia", "2011_odi_australia"]}).eq("name", "Michael Hussey").execute()

print("Done!")
