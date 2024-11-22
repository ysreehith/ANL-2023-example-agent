import json
import logging
from random import randint
from time import time
from typing import cast
from math import floor


from geniusweb.actions.Accept import Accept
from geniusweb.actions.Action import Action
from geniusweb.actions.Offer import Offer
from geniusweb.actions.PartyId import PartyId
from geniusweb.bidspace.AllBidsList import AllBidsList
from geniusweb.inform.ActionDone import ActionDone
from geniusweb.inform.Finished import Finished
from geniusweb.inform.Inform import Inform
from geniusweb.inform.Settings import Settings
from geniusweb.inform.YourTurn import YourTurn
from geniusweb.issuevalue.Bid import Bid
from geniusweb.issuevalue.Domain import Domain
from geniusweb.party.Capabilities import Capabilities
from geniusweb.party.DefaultParty import DefaultParty
from geniusweb.profile.utilityspace.LinearAdditiveUtilitySpace import (
    LinearAdditiveUtilitySpace,
)
from geniusweb.profileconnection.ProfileConnectionFactory import (
    ProfileConnectionFactory,
)
from geniusweb.progress.ProgressTime import ProgressTime
from geniusweb.references.Parameters import Parameters
from tudelft_utilities_logging.ReportToLogger import ReportToLogger


from .utils.opponent_model import OpponentModel




class TemplateAgent(DefaultParty):
    """
    Template of a Python geniusweb agent.
    """


    def __init__(self):
        super().__init__()
        self.logger: ReportToLogger = self.getReporter()


        self.domain: Domain = None
        self.parameters: Parameters = None
        self.profile: LinearAdditiveUtilitySpace = None
        self.progress: ProgressTime = None
        self.me: PartyId = None
        self.other: str = None
        self.settings: Settings = None
        self.storage_dir: str = None


        self.last_received_bid: Bid = None
        self.opponent_model: OpponentModel = None
        self.history = {}
        self.data_dict = {"sessions": []}  # To store session data


        # Variables for session tracking
        self.utility_at_finish: float = 0
        self.did_accept: bool = False
        self.top_bids_percentage: float = 1 / 300
        self.force_accept_at_remaining_turns: float = 1
        self.logger.log(logging.INFO, "party is initialized")
        self.logger.log(logging.INFO, "party is initialized")


    def notifyChange(self, data: Inform):
        """MUST BE IMPLEMENTED
        This is the entry point of all interaction with your agent after is has been initialised.
        How to handle the received data is based on its class type.


        Args:
            info (Inform): Contains either a request for action or information.
        """


        # a Settings message is the first message that will be send to your
        # agent containing all the information about the negotiation session.
        if isinstance(data, Settings):
            self.settings = cast(Settings, data)
            self.me = self.settings.getID()


            # progress towards the deadline has to be tracked manually through the use of the Progress object
            self.progress = self.settings.getProgress()


            self.parameters = self.settings.getParameters()
            self.storage_dir = self.parameters.get("storage_dir")
            self.load_history()
            # the profile contains the preferences of the agent over the domain
            profile_connection = ProfileConnectionFactory.create(
                data.getProfile().getURI(), self.getReporter()
            )
            self.profile = profile_connection.getProfile()
            self.domain = self.profile.getDomain()
            profile_connection.close()


        # ActionDone informs you of an action (an offer or an accept)
        # that is performed by one of the agents (including yourself).
        elif isinstance(data, ActionDone):
            action = cast(ActionDone, data).getAction()
            actor = action.getActor()


            # ignore action if it is our action
            if actor != self.me:
                # obtain the name of the opponent, cutting of the position ID.
                self.other = str(actor).rsplit("_", 1)[0]


                # process action done by opponent
                self.opponent_action(action)
        # YourTurn notifies you that it is your turn to act
        elif isinstance(data, YourTurn):
            # execute a turn
            self.my_turn()


        # Finished will be send if the negotiation has ended (through agreement or deadline)
        elif isinstance(data, Finished):
            self.utility_at_finish = (
                float(self.profile.getUtility(self.last_received_bid))
                if self.last_received_bid
                else 0
            )
            self.save_data()
            self.logger.log(logging.INFO, "party is terminating")
            super().terminate()
        else:
            self.logger.log(logging.WARNING, "Ignoring unknown info " + str(data))


    def getCapabilities(self) -> Capabilities:
        """MUST BE IMPLEMENTED
        Method to indicate to the protocol what the capabilities of this agent are.
        Leave it as is for the ANL 2022 competition


        Returns:
            Capabilities: Capabilities representation class
        """
        return Capabilities(
            set(["SAOP"]),
            set(["geniusweb.profile.utilityspace.LinearAdditive"]),
        )


    def send_action(self, action: Action):
        """Sends an action to the opponent(s)


        Args:
            action (Action): action of this agent
        """
        self.getConnection().send(action)


    # give a description of your agent
    def getDescription(self) -> str:
        """MUST BE IMPLEMENTED
        Returns a description of your agent. 1 or 2 sentences.


        Returns:
            str: Agent description
        """
        return "Template agent for the ANL 2022 competition"


    def opponent_action(self, action):
        """Process an action that was received from the opponent.


        Args:
            action (Action): action of opponent
        """
        # if it is an offer, set the last received bid
        if isinstance(action, Offer):
            # create opponent model if it was not yet initialised
            if self.opponent_model is None:
                self.opponent_model = OpponentModel(self.domain)


            bid = cast(Offer, action).getBid()


            # update opponent model with bid
            self.opponent_model.update(bid)
            # set bid as last received
            self.last_received_bid = bid


    def my_turn(self):
        """This method is called when it is our turn. It should decide upon an action
        to perform and send this action to the opponent.
        """
        # Check if the last received offer is good enough
        if self.accept_condition(self.last_received_bid):
            action = Accept(self.me, self.last_received_bid)
            self.did_accept = True
        else:
            # Attempt to find a bid
            bid = self.find_bid()
            if bid is None:
                self.logger.log(logging.WARNING, "No valid bid found. Retrying with fallback strategy.")
                # Fallback strategy: Use a random bid
                bid = AllBidsList(self.profile.getDomain()).get(randint(0, 500))
       
            action = Offer(self.me, bid)


        # Send the action
        self.send_action(action)




    def save_data(self):
        """Save session data, appending to the history of the opponent."""
        progress_at_finish = self.progress.get(time() * 1000)
        session_data = {
            "progressAtFinish": progress_at_finish,
            "utilityAtFinish": self.utility_at_finish,
            "didAccept": self.did_accept,
            "isGood": self.utility_at_finish >= 0.7,
            "topBidsPercentage": self.top_bids_percentage,
            "forceAcceptAtRemainingTurns": self.force_accept_at_remaining_turns,
        }
        self.data_dict["sessions"].append(session_data)


        if self.other:
            filename = f"{self.storage_dir}/{self.other}.json"
            try:
                with open(filename, "r") as f:
                    existing_data = json.load(f)
                existing_data["sessions"].extend(self.data_dict["sessions"])
                self.data_dict = existing_data  # Update the data_dict
            except FileNotFoundError:
                self.logger.log(logging.INFO, "No previous data found; creating new data file.")


            with open(filename, "w") as f:
                json.dump(self.data_dict, f, indent=4)
            self.logger.log(logging.INFO, f"Session data saved to {filename}")


    def load_history(self):
        """Load session history for the opponent."""
        if self.other:
            filename = f"{self.storage_dir}/{self.other}.json"
            try:
                with open(filename, "r") as f:
                    self.data_dict = json.load(f)
                self.logger.log(logging.INFO, f"Loaded data from {filename}")
            except FileNotFoundError:
                self.data_dict = {"sessions": []}
                self.logger.log(logging.INFO, f"No previous data found for {self.other}")




    ###########################################################################################
    ################################## Example methods below ##################################
    ###########################################################################################


    def accept_condition(self, bid: Bid) -> bool:
        """
        Determines whether to accept the opponent's bid based on advanced strategies,
        incorporating historical data from previous sessions.

        Args:
            bid (Bid): The last received bid from the opponent.

        Returns:
            bool: True if the bid should be accepted; False otherwise.
        """
        if bid is None:
            return False

        # Get negotiation progress and utilities
        progress = self.progress.get(time() * 1000)
        our_utility = float(self.profile.getUtility(bid))
        opponent_utility = (
            self.opponent_model.get_predicted_utility(bid) if self.opponent_model else 0.0
        )

        # Load previous session data for this opponent
        historical_utilities = []
        accept_ratios = []
        filename = f"{self.storage_dir}/{self.other}.json"

        try:
            with open(filename, "r") as f:
                history_data = json.load(f)
                for session in history_data.get("sessions", []):
                    historical_utilities.append(session["utilityAtFinish"])
                    if session["didAccept"]:
                        accept_ratios.append(session["progressAtFinish"])
        except FileNotFoundError:
            self.logger.log(logging.INFO, f"No historical data found for {self.other}")
    
        # Adjust dynamic thresholds based on historical data
        avg_utility = (
            sum(historical_utilities) / len(historical_utilities)
            if historical_utilities
            else 0.7  # Default utility threshold
        )
        avg_accept_progress = (
            sum(accept_ratios) / len(accept_ratios)
            if accept_ratios
            else 0.85  # Default progress threshold
        )

        # Dynamic Acceptance Threshold
        dynamic_threshold = max(avg_utility - progress * 0.1, 0.6)

        # Nash Equilibrium Check
        nash_product = our_utility * opponent_utility
        nash_threshold = 0.8 * max(nash_product, 0.5)

        # Pareto Optimality Check
        is_pareto = True
        if self.opponent_model and self.last_received_bid:
            prev_opponent_utility = self.opponent_model.get_predicted_utility(self.last_received_bid)
            prev_our_utility = float(self.profile.getUtility(self.last_received_bid))
            is_pareto = (
                opponent_utility >= prev_opponent_utility
                and our_utility >= prev_our_utility
            )

        # Risk Tolerance based on historical data
        risk_tolerance = max(avg_accept_progress, progress + 0.1)

        # Enhanced Acceptance Logic with Historical Influence
        accept = all(
            [
                our_utility >= dynamic_threshold,
                nash_product >= nash_threshold,
                is_pareto,
                our_utility >= risk_tolerance,
                progress > avg_accept_progress,  # Avoid early acceptance
            ]
        )

        # Logging for debugging
        self.logger.log(
            logging.INFO,
            f"Accept Condition: {accept}, Our Utility: {our_utility}, Opponent Utility: {opponent_utility}, "
            f"Progress: {progress}, Dynamic Threshold: {dynamic_threshold}, Nash Product: {nash_product}, "
            f"Pareto Optimal: {is_pareto}, Risk Tolerance: {risk_tolerance}, "
            f"Historical Avg Utility: {avg_utility}, Historical Avg Accept Progress: {avg_accept_progress}",
        )
        return accept



    def find_bid(self) -> Bid:
        """
        Find a Pareto-efficient bid based on the adaptive concession strategy and fairness metrics.
        """
        if self.profile is None:
            raise ValueError("Profile not initialized")


        domain = self.profile.getDomain()
        all_bids = AllBidsList(domain)


        # Determine Concession Threshold
        progress = self.progress.get(time() * 1000)
        base_threshold = 0.9 - progress * 0.2  # Concession increases with time


        # Multi-Stage Concession
        if progress < 0.5:
            threshold = base_threshold  # Hard-bargaining early
        elif progress < 0.85:
            threshold = base_threshold * 0.9  # Moderate concessions in mid-stage
        else:
            threshold = base_threshold * 0.7  # More cooperative in the final stage


        # Filter Pareto-efficient bids
        pareto_bids = self.filter_pareto_bids(all_bids)
        if not pareto_bids:
            self.logger.log(logging.ERROR, "No Pareto-efficient bids found!")
            return None


    # Select the best Pareto-efficient bid
        best_bid = max(
            pareto_bids,
            key=lambda bid: self.score_pareto_bid(bid, threshold),
            default=None,
    )


        if best_bid is None:
            self.logger.log(logging.ERROR, "No valid bid found after scoring!")
        return best_bid
   
    def score_pareto_bid(self, bid: Bid, threshold: float) -> float:
        """
    Calculate a score for a Pareto-efficient bid by combining utilities and fairness.


    Args:
        bid (Bid): The bid to score.
        threshold (float): The minimum utility threshold.


    Returns:
        float: The calculated score.
    """
        our_utility = float(self.profile.getUtility(bid))
        opponent_utility = (
            self.opponent_model.get_predicted_utility(bid) if self.opponent_model else 0
        )
        joint_utility = our_utility + opponent_utility
        utility_diff = abs(our_utility - opponent_utility)


    # Penalize bids that fall below the utility threshold
        if our_utility < threshold:
            return float("-inf")  # Discard bids below the threshold


    # Weigh joint utility higher and penalize large utility differences
        return joint_utility - 0.5 * utility_diff


    def filter_pareto_bids(self, all_bids: AllBidsList) -> list:
        #"""Filter bids that are Pareto-efficient."""
        pareto_bids = []
        for _ in range(1000):  # Evaluate a subset for efficiency
            bid = all_bids.get(randint(0, all_bids.size() - 1))
            self_utility = self.profile.getUtility(bid)
            opponent_utility = (
               self.opponent_model.get_predicted_utility(bid) if self.opponent_model else 0
            )


            # Check if the bid dominates others in terms of both utilities
            if self.is_pareto_dominant(bid, self_utility, opponent_utility):
                pareto_bids.append(bid)


        self.logger.log(logging.INFO, f"Filtered {len(pareto_bids)} Pareto-efficient bids")
        return pareto_bids


    def is_pareto_dominant(self, bid, self_utility, opponent_utility) -> bool:
        """Determine if a bid is Pareto-efficient."""
        return self_utility > 0.7 and opponent_utility > 0.5



