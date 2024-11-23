import numpy as np

from geniusweb.issuevalue.Bid import Bid
from opponent_model import IssueEstimator

def opponent_utility(issues, weights):
    # predict utility value of offer
    # implemented from Opponent Modelling in Automated Multi-Issue Negotiation Using Bayesian Learning
    # we assume that the first 
    return sum(value * weight for value, weight in zip(issues, weights))

def generate_candidate_hypotheses(num_candidates, num_issues):
    return np.random.dirichlet(np.ones(num_issues), size=num_candidates)

def initialize_priors(num_candidates):
    return np.ones(num_candidates) / num_candidates

def update_beliefs(priors, candidates, observed_offer : Bid, issue_estimators):
    issues = [observed_offer.getValue(issue_id) for issue_id, issue_estimator in issue_estimators.items()]
    likelihoods = np.array([opponent_utility(issues, candidate) for candidate in candidates])
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
    return np.average(candidates, axis=0, weights=beliefs)


