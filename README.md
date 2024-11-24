## Adaptive Negotiation Agent with Learning-Based Strategies for Bilateral Negotiations

This is a repository containing all the code written for the group project taken under the CSC 555 : Social Computing and Decentralized Artificial Intelligence course at NC State University.  This repository has been forked from the template repository given for [ANL 2023](https://github.com/brenting/ANL-2023-example-agent/tree/main)

In this project, we address the challenge of improving autonomous negotiation outcomes by developing an intelligent agent capable of learning from previous interactions. Unlike traditional negotiation systems that rely on static strategies, our agent integrates dynamic learning capabilities, allowing it to adapt and refine its behavior over time. A central feature of this agent is its ability to store and analyze detailed session data after each negotiation. 

## Overview
- directories:
    - `agents`: Contains directories with the agents. The `template_agent` directory contains the template agent for the ANL competition. Our agent is present under the `my_agent` directory.
    - `domains`: Contains the domains which are problems over which the agents are supposed to negotiate.
    - `utils`: Arbitrary utilities to run sessions and process results.
- files:
    - `run.py`: Main interface to test agents in single session runs.
    - `run_tournament.py`: Main interface to test a set of agents in a tournament. Here, every agent will negotiate against every other agent in the set on every set of preferences profiles that is provided (see code).
    - `requirements.txt`: Python dependencies for this repository.
    - `requirements_allowed.txt`: Additional dependencies that were allowed for ANL-2023.

## Installation
Download or clone this repository.

We recommend using Python 3.9 as this version is the best supported version for all required dependencies. The required dependencies are listed in the `requirements.txt` file and can be installed through `pip install -r requirements.txt`. We advise you to create a Python virtual environment to install the dependencies in isolation (e.g. `python3.9 -m venv .venv`, see also [here](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#creating-a-virtual-environment))

For VSCode devcontainer users: We included a devcontainer specification in the `.devcontainer` directory.

## Quickstart for developing your own agent 
- Copy and rename the template agent's directory, files and classname.
- Read through the code to familiarise yourself with its workings. The agent already works but is not very good.
- Develop your agent in the copied directory. Make sure that all the files that you use are in the directory.
- Test your agent through `run.py`, results will be returned as dictionaries and saved as json-file. A plot of the negotiation trace will also be saved.
- You can also test your agent more extensively by running a tournament with a set of agents. Use the `run_tournament.py` script for this. Summaries of the results will be saved to the results directory.

## Documentation
The code of GeniusWebPython is properly documented. Exploring the class definitions of the classes used in the template agent is usually sufficient to understand how to work with them.

[More documentation can be found here](https://tracinsy.ewi.tudelft.nl/pubtrac/GeniusWebPython/wiki/WikiStart). This documentation was written for the Java version of GeniusWeb, but classes and functionality are identical as much as possible.

## Team Members 
- Krithika Ragothaman (kragoth)
- Raj Kalantri (rkalant)
- Sreehith Yachamaneni (syacham)
