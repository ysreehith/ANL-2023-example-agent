from collections import defaultdict

from geniusweb.issuevalue.Bid import Bid
from geniusweb.issuevalue.DiscreteValueSet import DiscreteValueSet
from geniusweb.issuevalue.Domain import Domain
from geniusweb.issuevalue.Value import Value
from bayesian_helper import generate_candidate_hypotheses, initialize_priors, update_beliefs, estimate_preference


class OpponentModel:
    def __init__(self, domain: Domain):
        self.offers = []
        self.domain = domain
        self.num_candidate_hypotheses = 10
        self.issue_estimators = {
            i: IssueEstimator(v) for i, v in domain.getIssuesValues().items()
        }
        self.hypotheses_candidates = generate_candidate_hypotheses(self.num_candidate_hypotheses, len(self.issue_estimators))
        self.beliefs = initialize_priors(self.num_candidate_hypotheses)
        self.reservation_value = 0.5 # can be changed 

    def update(self, bid: Bid):
        # keep track of all bids received
        self.offers.append(bid)

        # update all issue estimators with the value that is offered for that issue
        for issue_id, issue_estimator in self.issue_estimators.items():
            issue_estimator.update(bid.getValue(issue_id))

        self.beliefs = update_beliefs(self.beliefs, self.hypotheses_candidates, bid, self.issue_estimators)

    def get_predicted_utility(self, bid: Bid):
        if len(self.offers) == 0 or bid is None:
            return 0
        predicted_utility = estimate_preference(self.beliefs, self.hypotheses_candidates, self.reservation_value)

        return predicted_utility


class IssueEstimator:
    def __init__(self, value_set: DiscreteValueSet):
        if not isinstance(value_set, DiscreteValueSet):
            raise TypeError(
                "This issue estimator only supports issues with discrete values"
            )

        self.bids_received = 0
        self.max_value_count = 0
        self.num_values = value_set.size()
        self.value_trackers = defaultdict(ValueEstimator)
        self.weight = 0

    def update(self, value: Value):
        self.bids_received += 1

        # get the value tracker of the value that is offered
        value_tracker = self.value_trackers[value]

        # register that this value was offered
        value_tracker.update()

        # update the count of the most common offered value
        self.max_value_count = max([value_tracker.count, self.max_value_count])

        # update predicted issue weight
        # the intuition here is that if the values of the receiverd offers spread out over all
        # possible values, then this issue is likely not important to the opponent (weight == 0.0).
        # If all received offers proposed the same value for this issue,
        # then the predicted issue weight == 1.0
        equal_shares = self.bids_received / self.num_values
        self.weight = (self.max_value_count - equal_shares) / (
            self.bids_received - equal_shares
        )

        # recalculate all value utilities
        for value_tracker in self.value_trackers.values():
            value_tracker.recalculate_utility(self.max_value_count, self.weight)

    def get_value_utility(self, value: Value):
        if value in self.value_trackers:
            return self.value_trackers[value].utility

        return 0


class ValueEstimator:
    def __init__(self):
        self.count = 0
        self.utility = 0

    def update(self):
        self.count += 1

    def recalculate_utility(self, max_value_count: int, weight: float):
        if weight < 1:
            mod_value_count = ((self.count + 1) ** (1 - weight)) - 1
            mod_max_value_count = ((max_value_count + 1) ** (1 - weight)) - 1

            self.utility = mod_value_count / mod_max_value_count
        else:
            self.utility = 1
