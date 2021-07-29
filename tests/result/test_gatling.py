from datetime import datetime
from decimal import Decimal
from perfsize.perfsize import (
    lt,
    lte,
    gt,
    gte,
    eq,
    neq,
    Condition,
    Result,
    Run,
    Config,
    Plan,
    StepManager,
    EnvironmentManager,
    LoadManager,
    ResultManager,
    Reporter,
    Workflow,
)
from perfsize.environment.mock import MockEnvironmentManager
from perfsize.load.mock import MockLoadManager
from perfsize.reporter.mock import MockReporter
from perfsize.result.mock import MockResultManager
from perfsize.result.gatling import Metric, GatlingResultManager
from perfsize.step.mock import MockStepManager
from pprint import pprint
import pytest
from unittest.mock import patch


class TestGatlingResultManager:
    def test_gatling_result_manager(self) -> None:
        # A plan would define the various configs possible for testing.
        # A step manager would pick the next config to test.
        # This test is starting with a given Config and an associated Run.
        config = Config(
            parameters={
                "endpoint_name": "LEARNING-model-sim-public-c-1",
                "endpoint_config_name": "LEARNING-model-sim-public-c-1-0",
                "model_name": "model-sim-public",
                "instance_type": "ml.t2.medium",
                "initial_instance_count": "1",
                "ramp_start_tps": "0",
                "ramp_minutes": "0",
                "steady_state_tps": "1",
                "steady_state_minutes": "1",
            },
            requirements={
                Metric.latency_success_p99: [
                    Condition(lt(Decimal("200")), "value < 200"),
                    Condition(gte(Decimal("0")), "value >= 0"),
                ],
                Metric.percent_fail: [
                    Condition(lt(Decimal("0.01")), "value < 0.01"),
                    Condition(gte(Decimal("0")), "value >= 0"),
                ],
            },
        )
        run = Run(
            id="test_run_tag",
            start=datetime.fromisoformat("2021-04-01T00:00:00"),
            end=datetime.fromisoformat("2021-04-01T01:00:00"),
            results=[],
        )
        # GatlingResultManager will parse simulation.log and populate results
        result_manager = GatlingResultManager(
            results_path="examples/perfsize-results-root"
        )
        result_manager.query(config, run)
        pprint(run.results)
