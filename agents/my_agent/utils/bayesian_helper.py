import numpy as np

from geniusweb.issuevalue.Bid import Bid
from geniusweb.issuevalue.Value import Value

def get_opponent_utility(bid, issue_estimators, issue_weights):
      
        # initiate
        total_issue_weight = 0.0
        value_utilities = []
        total_issue_weight = sum(issue_weights)

        for issue_id, issue_estimator in issue_estimators.items():
            # get the value that is set for this issue in the bid
            value: Value = bid.getValue(issue_id)

            # collect both the predicted weight for the issue and
            # predicted utility of the value within this issue
            value_utilities.append(issue_estimator.get_value_utility(value))


        # normalise the issue weights such that the sum is 1.0
        if total_issue_weight == 0.0:
            issue_weights = [1 / len(issue_weights) for _ in issue_weights]
        else:
            issue_weights = [iw / total_issue_weight for iw in issue_weights]

        # calculate predicted utility by multiplying all value utilities with their issue weight
        predicted_utility = sum(
            [iw * vu for iw, vu in zip(issue_weights, value_utilities)]
        )

        return predicted_utility

def generate_candidate_hypotheses(num_candidates, num_issues):
    return np.random.dirichlet(np.ones(num_issues), size=num_candidates)

def initialize_priors(num_candidates):
    return np.ones(num_candidates) / num_candidates

def update_beliefs(priors, candidates, observed_offer : Bid, issue_estimators):
    #issues = [int(observed_offer.getValue(issue_id).getValue()) for issue_id, issue_estimator in issue_estimators.items()]
    likelihoods = np.array([get_opponent_utility(observed_offer, issue_estimators, candidate) for candidate in candidates])
    posterior = priors * likelihoods
    total = np.sum(posterior)
    if total == 0:
        return priors
    else:
        return posterior / total

def estimate_preference(beliefs, candidates, reservation_value):
    if np.all(beliefs == 0):
        # least possible utility below which opponent wouldn't accept offer
        return reservation_value
    #print("opponent util" , np.average(candidates, axis=0, weights=beliefs))
    result = np.average(candidates, axis=0, weights=beliefs)
    norm_result = (result - np.min(result)) / (np.max(result) - np.min(result))
    return np.sum(norm_result)



