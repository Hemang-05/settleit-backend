import random

FORMAT_CONFIG = {
    "odi": {"total_overs": 50, "pp_overs": 10, "label": "ODI", "par_score": "250-320"},
    "t20": {"total_overs": 20, "pp_overs": 6, "label": "T20", "par_score": "160-190"},
    "t10": {"total_overs": 10, "pp_overs": 3, "label": "T10", "par_score": "90-120"},
}

def format_team(team, tactics):
    players_text = ""
    for i, p in enumerate(team):
        role = p.get("role", "Unknown")
        known_for = ", ".join(p.get("known_for", []))
        era = f"{p.get('era_start', '?')}–{p.get('era_end', 2099) if p.get('era_end') != 2099 else 'Present'}"
        players_text += f"  {i+1}. {p['name']} ({role}, {p['nationality']}, {era}) — {known_for}\n"

    captain_id = tactics.get('captain')
    captain_name = team[0]['name'] if team else "Unknown"
    if captain_id:
        for p in team:
            if p.get('id') == captain_id:
                captain_name = p['name']
                break

    return f"""Players:
{players_text}Captain: {captain_name}
Tactics:
  - Batting: {tactics.get('batting', 'balanced')}
  - Bowling: {tactics.get('bowling', 'balanced')}
  - Field: {tactics.get('field', 'standard')}
  - Aggression: {tactics.get('aggression', 5)}/10
  - Captain's Note: "{tactics.get('captainNote', 'None')}"
"""


def build_match_context(team_a, team_b, tactics_a, tactics_b):
    return f"""=== TEAM A ===
{format_team(team_a, tactics_a)}
=== TEAM B ===
{format_team(team_b, tactics_b)}"""


def get_batting_order(toss_info):
    """Returns which team bats first: 'A' or 'B'"""
    winner = toss_info.get("tossWinnerTeam", "A")
    decision = toss_info.get("decision", "bat")
    if decision == "bat":
        return winner
    return "B" if winner == "A" else "A"


def build_phase_prompt(team_a, team_b, tactics_a, tactics_b, format_id, phase, match_state, toss_info):
    config = FORMAT_CONFIG.get(format_id, FORMAT_CONFIG["odi"])
    pp = config["pp_overs"]
    total = config["total_overs"]
    label = config["label"]
    par = config["par_score"]

    first_bat = get_batting_order(toss_info)
    pitch = toss_info.get("pitchLabel", "Balanced")
    weather = toss_info.get("weatherLabel", "Sunny")

    context = build_match_context(team_a, team_b, tactics_a, tactics_b)

    # Phase-specific instructions
    if phase == "inn1_pp":
        batting = "Team A" if first_bat == "A" else "Team B"
        bowling = "Team B" if first_bat == "A" else "Team A"
        phase_instruction = f"""Simulate the 1ST INNINGS POWERPLAY (overs 1 to {pp}) of a {label} match.
{batting} is batting. {bowling} is bowling.
Pitch: {pitch}. Weather: {weather}.
Par score for full innings in {label}: {par}.
Generate a realistic powerplay with 8-15 commentary events including boundaries, wickets (if any), and the powerplay summary."""

    elif phase == "inn1_mid":
        batting = "Team A" if first_bat == "A" else "Team B"
        bowling = "Team B" if first_bat == "A" else "Team A"
        prev = match_state.get("innings1_pp", {})
        prev_score = prev.get("score", {})
        prev_scorecard = prev.get("scorecard", [])
        not_out = [p for p in prev_scorecard if "not out" in p.get("out", "").lower()]

        phase_instruction = f"""Continue the 1ST INNINGS from over {pp+1} to {total} of a {label} match.
{batting} is batting. {bowling} is bowling.
CURRENT STATE after powerplay: {prev_score.get('runs',0)}/{prev_score.get('wickets',0)} in {prev_score.get('overs',pp)} overs.
Batsmen at crease: {', '.join([p['name']+' '+str(p['runs'])+'('+str(p['balls'])+')' for p in not_out]) if not_out else 'New pair'}.
Continue from this state. Generate the FULL innings scorecard (all 11 batters) and bowling figures.
Include 10-15 commentary events for key moments (wickets, 50s, 100s, death overs drama, final score)."""

    elif phase == "inn2_pp":
        chasing = "Team B" if first_bat == "A" else "Team A"
        bowling = "Team A" if first_bat == "A" else "Team B"
        target = match_state.get("innings1_total", 250)
        phase_instruction = f"""Simulate the 2ND INNINGS POWERPLAY (overs 1 to {pp}) of a {label} match.
{chasing} is CHASING a target of {target+1} runs.
{chasing} is batting. {bowling} is bowling.
Pitch: {pitch}. Weather: {weather}.
Generate a realistic chase powerplay with 8-15 commentary events."""

    elif phase == "inn2_mid":
        chasing = "Team B" if first_bat == "A" else "Team A"
        bowling = "Team A" if first_bat == "A" else "Team B"
        target = match_state.get("innings1_total", 250)
        prev = match_state.get("innings2_pp", {})
        prev_score = prev.get("score", {})
        prev_scorecard = prev.get("scorecard", [])
        not_out = [p for p in prev_scorecard if "not out" in p.get("out", "").lower()]

        phase_instruction = f"""Continue the 2ND INNINGS from over {pp+1} to {total} of a {label} match.
{chasing} is CHASING {target+1}. {bowling} is bowling.
CURRENT STATE after powerplay: {prev_score.get('runs',0)}/{prev_score.get('wickets',0)} in {prev_score.get('overs',pp)} overs.
Batsmen at crease: {', '.join([p['name']+' '+str(p['runs'])+'('+str(p['balls'])+')' for p in not_out]) if not_out else 'New pair'}.
Runs needed: {target+1 - prev_score.get('runs',0)} from {total - pp} overs.
Generate the FULL innings scorecard and bowling figures. Determine the match result.
Include 10-15 commentary events. If tied, set "match_tied": true."""

    elif phase == "super_over":
        phase_instruction = f"""Simulate a SUPER OVER (1 over per side). Both teams bat and bowl 1 over each.
Team A selected batters: {', '.join([p['name'] for p in match_state.get('so_batters_a', [])])}
Team A bowler: {match_state.get('so_bowler_a', {}).get('name', 'Unknown')}
Team B selected batters: {', '.join([p['name'] for p in match_state.get('so_batters_b', [])])}
Team B bowler: {match_state.get('so_bowler_b', {}).get('name', 'Unknown')}
Generate commentary for both super over innings and determine the winner."""
    else:
        phase_instruction = "Simulate the match."

    prompt = f"""You are a world-class cricket analyst simulating a {label} match phase.

{context}

{phase_instruction}

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "batting_team": "Team A or Team B",
  "score": {{"runs": 0, "wickets": 0, "overs": 0}},
  "scorecard": [
    {{"name": "player name", "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "out": "how out or not out"}}
  ],
  "bowling": [
    {{"name": "bowler name", "overs": 0, "runs": 0, "wickets": 0}}
  ],
  "commentary_events": [
    {{"over": "1.3", "type": "boundary", "text": "FOUR! Description..."}},
    {{"over": "3.5", "type": "wicket", "text": "WICKET! Description...", "score": "25/1"}},
    {{"over": "8.0", "type": "milestone", "text": "FIFTY for Player!", "player": "name"}},
    {{"over": "{pp}.0", "type": "phase_end", "text": "End of phase: Score summary"}}
  ],
  "phase_summary": "Brief summary of what happened this phase"
}}

EVENT TYPES: boundary, six, wicket, milestone, phase_end, normal, dramatic
Include 8-15 events. Make wickets dramatic. Include milestones (50s, 100s).
{"Add match_result: {winner, margin, player_of_match, player_of_match_reason, summary} if this is the final phase." if phase in ("inn2_mid", "super_over") else ""}
Respond with ONLY the JSON, no extra text."""

    return prompt


# Keep legacy single-call prompt for test/superover formats
def build_simulation_prompt(team_a, team_b, tactics_a, tactics_b):
    context = build_match_context(team_a, team_b, tactics_a, tactics_b)
    prompt = f"""You are a world-class cricket analyst and commentator simulating a One Day International (ODI) match between two all-time XIs featuring legends from different eras.

MATCH CONTEXT:
{context}

YOUR TASK:
Simulate a full ODI cricket match (50 overs per side) between these two teams. Consider:
- Each player's actual playing style, strengths, weaknesses
- The tactics and captain's instructions provided
- Era differences (e.g. modern players may have T20 skills, legends had different conditions)
- Realistic cricket logic (wickets, partnerships, collapses, powerplays, death overs)
- How bowling matchups would realistically play out

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "toss": {{
    "winner": "Team A or Team B",
    "decision": "bat or bowl"
  }},
  "innings1": {{
    "batting_team": "Team A or Team B",
    "total": 0,
    "wickets": 0,
    "overs": 50,
    "scorecard": [
      {{"name": "player name", "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "out": "how they got out or not out"}}
    ],
    "bowling": [
      {{"name": "bowler name", "overs": 0, "runs": 0, "wickets": 0}}
    ],
    "key_moments": ["moment 1", "moment 2", "moment 3", "moment 4", "moment 5"]
  }},
  "innings2": {{
    "batting_team": "Team A or Team B",
    "total": 0,
    "wickets": 0,
    "overs": 50,
    "scorecard": [
      {{"name": "player name", "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "out": "how they got out or not out"}}
    ],
    "bowling": [
      {{"name": "bowler name", "overs": 0, "runs": 0, "wickets": 0}}
    ],
    "key_moments": ["moment 1", "moment 2", "moment 3", "moment 4", "moment 5"]
  }},
  "result": {{
    "winner": "Team A or Team B",
    "margin": "e.g. 47 runs or 3 wickets",
    "player_of_match": "player name",
    "player_of_match_reason": "why they won it",
    "summary": "2-3 sentence dramatic match summary"
  }},
  "commentary": [
    "Over 1: dramatic commentary line...",
    "Over 5: key moment commentary...",
    "Over 10: commentary...",
    "Over 15: commentary...",
    "Over 20: commentary...",
    "Over 25: commentary...",
    "Over 30: commentary...",
    "Over 35: commentary...",
    "Over 40: commentary...",
    "Over 45: commentary...",
    "Over 50: innings end commentary...",
    "2nd innings Over 1: commentary...",
    "2nd innings Over 10: commentary...",
    "2nd innings Over 20: commentary...",
    "2nd innings Over 30: commentary...",
    "2nd innings Over 40: commentary...",
    "2nd innings Over 50: final over commentary..."
  ]
}}

IMPORTANT:
- Make scores realistic for ODI cricket (230-320 is par, 350+ is exceptional)
- Give players scores that reflect their actual ability and the match context
- Use the captain's instructions to influence decisions
- Make key moments dramatic and specific to the actual players involved
- Respond with ONLY the JSON, no extra text
"""
    return prompt