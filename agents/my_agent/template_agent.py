import json
import logging
from random import randint
from time import time
from typing import cast

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
            self.save_data()
            # terminate the agent MUST BE CALLED
            self.logger.log(logging.INFO, "party is terminating:")
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
        if self.other:
            self.history[self.other] = {
                "bids": [
                    {
                        issue: str(value) 
                        for issue, value in bid.items()  # Access as dictionary
                    }
                    for bid in self.opponent_model.get_bid_history()
                ],
                "preferences": {
                    issue: {
                        str(value): utility
                        for value, utility in preferences.items()
                    }
                    for issue, preferences in self.opponent_model.get_preferences().items()
                },
            }
        with open(f"{self.storage_dir}/history.json", "w") as f:
            json.dump(self.history, f)
    def load_history(self):
        try:
            with open(f"{self.storage_dir}/history.json", "r") as f:
                self.history = json.load(f)
        except FileNotFoundError:
            self.history = {}
            self.logger.log(logging.INFO, "No previous history found.")

    ###########################################################################################
    ################################## Example methods below ##################################
    ###########################################################################################

    def accept_condition(self, bid: Bid) -> bool:
        """
        Determines whether to accept the opponent's bid based on advanced strategies.

        Args:
            bid (Bid): The last received bid from the opponent.

        Returns:
            bool: True if the bid should be accepted; False otherwise.
        """
        if bid is None:
            return False

        progress = self.progress.get(time() * 1000)
        our_utility = float(self.profile.getUtility(bid))
        opponent_utility = (
            self.opponent_model.get_predicted_utility(bid) if self.opponent_model else 0.0
        )

        # Dynamic Acceptance Threshold
        # Threshold starts high and reduces gradually, but adjusts based on opponent behavior
        dynamic_threshold = max(0.9 - progress * 0.2, 0.7)
        

        # Nash Equilibrium Check
        nash_product = our_utility * opponent_utility
        nash_threshold = 0.8 * max(nash_product, 0.5)  # Moderate Nash-based threshold

        # Pareto Optimality Check
        is_pareto = True
        if self.opponent_model and self.last_received_bid:
            prev_opponent_utility = self.opponent_model.get_predicted_utility(self.last_received_bid)
            prev_our_utility = float(self.profile.getUtility(self.last_received_bid))
            is_pareto = (
                opponent_utility >= prev_opponent_utility
                and our_utility >= prev_our_utility
            )

        # Time-Sensitive Risk Adjustment
        risk_tolerance = max(0.85, progress + 0.1)

        # Enhanced Acceptance Logic
        accept = all(
            [
                our_utility >= dynamic_threshold,
                nash_product >= nash_threshold,
                is_pareto,
                our_utility >= risk_tolerance,
                progress > 0.85,  # Avoid early acceptance
            ]
        )

        # Logging for debugging
        self.logger.log(
            logging.INFO,
            f"Accept Condition: {accept}, Our Utility: {our_utility}, Opponent Utility: {opponent_utility}, "
            f"Progress: {progress}, Dynamic Threshold: {dynamic_threshold}, Nash Product: {nash_product}, "
            f"Pareto Optimal: {is_pareto}, Risk Tolerance: {risk_tolerance}",
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
            threshold = base_threshold * 0.8  # More cooperative in the final stage

        pareto_bids = self.filter_pareto_bids(all_bids)
        if not pareto_bids:
            self.logger.log(logging.ERROR, "No Pareto-efficient bids found!")
            return None

        best_bid = None
        best_score = float("-inf")

        for bid in pareto_bids:
            refined_bid = self.refine_bid(bid)
            if refined_bid is None:
                continue

            # Consider both utility and fairness
            our_utility = self.profile.getUtility(refined_bid)
            opponent_utility = (
                self.opponent_model.get_predicted_utility(refined_bid)
                if self.opponent_model
                else 0
            )
            fairness_score = self.calculate_fairness_score(our_utility, opponent_utility)

            # Dynamic scoring combining utility and fairness
            score = self.score_bid_advanced(refined_bid) + fairness_score
            if score > best_score and our_utility >= threshold:
                best_score = score
                best_bid = refined_bid

        if best_bid is None:
            self.logger.log(logging.ERROR, "No valid bid found after refinement!")
        return best_bid


    def calculate_fairness_score(self, our_utility, opponent_utility, fairness_weight=0.5):
    
        # Ensure both utilities are converted to float for compatibility
        our_utility = float(our_utility)
        opponent_utility = float(opponent_utility)

        # Nash product as a measure of fairness
        nash_product = our_utility * opponent_utility
        return fairness_weight * nash_product


    
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

    def score_bid(self, bid: Bid, alpha: float = 0.95, eps: float = 0.1) -> float:
        """Calculate heuristic score for a bid

        Args:
            bid (Bid): Bid to score
            alpha (float, optional): Trade-off factor between self interested and
                altruistic behaviour. Defaults to 0.95.
            eps (float, optional): Time pressure factor, balances between conceding
                and Boulware behaviour over time. Defaults to 0.1.

        Returns:
            float: score
        """
        progress = self.progress.get(time() * 1000)

        our_utility = float(self.profile.getUtility(bid))

        time_pressure = 1.0 - progress ** (1 / eps)
        score = alpha * time_pressure * our_utility

        if self.opponent_model is not None:
            opponent_utility = self.opponent_model.get_predicted_utility(bid)
            opponent_score = (1.0 - alpha * time_pressure) * opponent_utility
            score += opponent_score

        return score
    
    def score_bid_advanced(self, bid: Bid, alpha: float = 0.7, beta: float = 0.3) -> float:
        """Advanced heuristic score for a bid considering fairness and time pressure."""
        progress = self.progress.get(time() * 1000)

        # Convert utilities to float
        our_utility = float(self.profile.getUtility(bid))
        opponent_utility = (
            float(self.opponent_model.get_predicted_utility(bid)) if self.opponent_model else 0.0
        )

        # Time pressure: Encourage concessions near the deadline
        time_pressure = 1.0 - progress ** 2

        # Multi-objective scoring
        score = (
            alpha * our_utility  # Weight for self-utility
            + beta * opponent_utility  # Weight for opponent utility
            + time_pressure * our_utility  # Adjust for time pressure
        )
        return score

    
    def refine_bid(self, initial_bid: Bid, iterations: int = 10, step_size: float = 0.1) -> Bid:
        """Refine the bid using a gradient-based approach."""
        if initial_bid is None:
            self.logger.log(logging.ERROR, "Initial bid for refinement is None!")
            return None

        refined_bid = initial_bid
        best_score = self.score_bid_advanced(refined_bid)

        for _ in range(iterations):
            neighbors = self.generate_neighbors(refined_bid)
            if not neighbors:
                self.logger.log(logging.WARNING, f"No neighbors generated for bid: {refined_bid}")
                continue

            for neighbor in neighbors:
                score = self.score_bid_advanced(neighbor)
                if score > best_score:
                    best_score = score
                    refined_bid = neighbor

        return refined_bid if refined_bid else initial_bid


    def generate_neighbors(self, bid: Bid) -> list:
        """Generate neighboring bids by tweaking issue values."""
        domain = self.profile.getDomain()
        neighbors = []

        for issue in domain.getIssues():
            values = domain.getValues(issue)

            for value in values:
                # Avoid generating the same bid by skipping the current value
                if bid.getValue(issue) != value:
                    # Create a new bid by modifying the issue's value
                    new_bid_values = bid.getIssueValues().copy()
                    new_bid_values[issue] = value
                    new_bid = Bid(new_bid_values)
                    neighbors.append(new_bid)

        return neighbors




