import json
import os
from pathlib import Path
import time


from utils.runners import run_tournament


RESULTS_DIR = Path("results", time.strftime('%Y%m%d-%H%M%S'))


# create results directory if it does not exist
if not RESULTS_DIR.exists():
    RESULTS_DIR.mkdir(parents=True)


# Settings to run a negotiation session:
#   You need to specify the classpath of 2 agents to start a negotiation. Parameters for the agent can be added as a dict (see example)
#   You need to specify the preference profiles for both agents. The first profile will be assigned to the first agent.
#   You need to specify a time deadline (is milliseconds (ms)) we are allowed to negotiate before we end without agreement.
tournament_settings = {
    "agents": [
        {
            "class": "agents.my_agent.template_agent.TemplateAgent",
            "parameters": {"storage_dir": "agent_storage/MyAgent"}
        },
         {
            "class": "agents.conceder_agent.conceder_agent.ConcederAgent",
        },
        {
            "class": "agents.CSE3210.agent2.agent2.Agent2",
        },
        {
            "class": "agents.CSE3210.agent3.agent3.Agent3",
        },
        {
            "class": "agents.CSE3210.agent7.agent7.Agent7",
        },
        {
            "class": "agents.CSE3210.agent43.agent43.Agent43",
        },
        {
            "class": "agents.CSE3210.agent50.agent50.Agent50",
        },
        {
            "class": "agents.CSE3210.agent52.agent52.Agent52",
        },
        {
            "class": "agents.CSE3210.agent55.agent55.Agent55",
        },
        {
            "class": "agents.CSE3210.agent58.agent58.Agent58",
        },
       
    ],
    "profile_sets": [
        ["domains/domain00/profileA.json", "domains/domain00/profileB.json"],
        ["domains/domain01/profileA.json", "domains/domain01/profileB.json"],
    ],
    "deadline_time_ms": 10000,
}


# run a session and obtain results in dictionaries
tournament_steps, tournament_results, tournament_results_summary = run_tournament(tournament_settings)


# save the tournament settings for reference
with open(RESULTS_DIR.joinpath("tournament_steps.json"), "w", encoding="utf-8") as f:
    f.write(json.dumps(tournament_steps, indent=2))
# save the tournament results
with open(RESULTS_DIR.joinpath("tournament_results.json"), "w", encoding="utf-8") as f:
    f.write(json.dumps(tournament_results, indent=2))
# save the tournament results summary
tournament_results_summary.to_csv(RESULTS_DIR.joinpath("tournament_results_summary.csv"))
