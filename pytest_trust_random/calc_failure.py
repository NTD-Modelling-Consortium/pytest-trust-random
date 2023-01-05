from dataclasses import dataclass
from statistics import NormalDist


@dataclass
class FailureProbabilities:
    per_test_no_reruns: float
    per_test_reruns: float
    one_test_from_all_no_reruns: float
    one_test_from_all_reruns: float


def calc_failure_prob(
    acceptable_st_devs: float,
    re_runs: int,
    independent_variables: int,
    n_tests: int,
    verbose: bool = True,
) -> FailureProbabilities:
    """
    Calculates and prints the probability of failure on any particular run of the
    test suite.

    Args:
        acceptable_st_devs (float): The number of standard devs within which a test will pass
        re_runs (int): The number of times a test is allowed to fail.
        independent_variables (int): The number of fully independent variable in the problem.
        May need to be determined experimentally, by measuring real rate of failure.
        n_tests (int): The total number of tests.
    """
    st_devs = acceptable_st_devs
    re_runs = re_runs
    independent_variables = independent_variables
    st_dev_prob = NormalDist().cdf(-st_devs)
    success_prob = 1 - st_dev_prob * 2
    prob_of_one_test_fail = 1 - success_prob**independent_variables

    prob_of_failing_all_re_runs = prob_of_one_test_fail ** (re_runs + 1)

    prob_of_one_of_all_tests_failing = 1 - (1 - prob_of_one_test_fail) ** n_tests

    prob_of_one_of_all_tests_failing_reruns = (
        1 - (1 - prob_of_failing_all_re_runs) ** n_tests
    )
    if verbose:
        print("Fail probability per test (assuming no reruns): ", prob_of_one_test_fail)
        print(
            "Fail probability per test (assuming reruns): ", prob_of_failing_all_re_runs
        )
        print(
            "Probability of one test failing: (assuming no reruns)",
            prob_of_one_of_all_tests_failing,
        )
        print(
            "Probability of one test failing: (assuming reruns)",
            prob_of_one_of_all_tests_failing_reruns,
        )
    return FailureProbabilities(
        per_test_no_reruns=prob_of_one_test_fail,
        per_test_reruns=prob_of_failing_all_re_runs,
        one_test_from_all_no_reruns=prob_of_one_of_all_tests_failing,
        one_test_from_all_reruns=prob_of_one_of_all_tests_failing_reruns,
    )
