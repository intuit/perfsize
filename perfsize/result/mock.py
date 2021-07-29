from decimal import Decimal
from perfsize.perfsize import Config, Result, ResultManager, Run


class MockResultManager(ResultManager):
    def query(self, config: Config, run: Run) -> None:
        print(f"MockResultManager is querying metrics based on {config} and {run}")
        response_time_metric = "latency_success_p99"
        if response_time_metric in config.requirements:
            run.results.append(
                Result(
                    response_time_metric,
                    Decimal("199"),
                    config.requirements[response_time_metric],
                )
            )
        error_rate_metric = "percent_fail"
        if error_rate_metric in config.requirements:
            run.results.append(
                Result(
                    error_rate_metric,
                    Decimal("0"),
                    config.requirements[error_rate_metric],
                )
            )
