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
from perfsize.step.mock import MockStepManager
import pytest
from unittest.mock import patch


class TestCondition:
    def test_lt(self) -> None:
        lt200 = lt(Decimal("200"))
        assert lt200(Decimal("199"))
        assert lt200(Decimal("200")) is False
        assert lt200(Decimal("201")) is False

    def test_lte(self) -> None:
        lte200 = lte(Decimal("200"))
        assert lte200(Decimal("199"))
        assert lte200(Decimal("200"))
        assert lte200(Decimal("201")) is False

    def test_gt(self) -> None:
        gt200 = gt(Decimal("200"))
        assert gt200(Decimal("199")) is False
        assert gt200(Decimal("200")) is False
        assert gt200(Decimal("201"))

    def test_gte(self) -> None:
        gte200 = gte(Decimal("200"))
        assert gte200(Decimal("199")) is False
        assert gte200(Decimal("200"))
        assert gte200(Decimal("201"))

    def test_eq(self) -> None:
        eq200 = eq(Decimal("200"))
        assert eq200(Decimal("199")) is False
        assert eq200(Decimal("200"))
        assert eq200(Decimal("201")) is False

    def test_neq(self) -> None:
        neq200 = neq(Decimal("200"))
        assert neq200(Decimal("199"))
        assert neq200(Decimal("200")) is False
        assert neq200(Decimal("201"))

    def test_condition(self) -> None:
        lt200 = lt(Decimal("200"))
        c1 = Condition(lt200, "value < 200")
        assert c1.function(Decimal("199"))
        assert f"{c1}" == "Condition('value < 200')"


class TestResult:
    def test_result(self) -> None:
        result = Result("latency_success_p99", Decimal("199"), [])
        assert result.successes == []
        assert result.failures == []

    def test_result_success(self) -> None:
        lt200 = lt(Decimal("200"))
        c1 = Condition(lt200, "value < 200")
        result = Result("latency_success_p99", Decimal("199"), [c1])
        assert result.successes == [c1]
        assert result.failures == []

    def test_result_failure(self) -> None:
        lt200 = lt(Decimal("200"))
        c1 = Condition(lt200, "value < 200")
        result = Result("latency_success_p99", Decimal("201"), [c1])
        assert result.successes == []
        assert result.failures == [c1]

    def test_result_mixed(self) -> None:
        lt200 = lt(Decimal("200"))
        gte0 = gte(Decimal("0"))
        c1 = Condition(lt200, "value < 200")
        c2 = Condition(gte0, "value >= 0")
        result = Result("latency_success_p99", Decimal("201"), [c1, c2])
        assert result.successes == [c2]
        assert result.failures == [c1]


class TestRun:
    def test_run_failure(self) -> None:
        p99conditions = [
            Condition(lt(Decimal("200")), "value < 200"),
            Condition(gte(Decimal("0")), "value >= 0"),
        ]
        errorconditions = [
            Condition(lt(Decimal("0.01")), "value < 0.01"),
            Condition(gte(Decimal("0")), "value >= 0"),
        ]
        result1 = Result("latency_success_p99", Decimal("199.01"), p99conditions)
        result2 = Result("percent_fail", Decimal("0.01"), errorconditions)
        run = Run(
            "test-run-id",
            datetime.fromisoformat("2021-04-01T00:00:00"),
            datetime.fromisoformat("2021-04-01T01:00:00"),
            [result1, result2],
        )
        assert result1.failures == []
        assert result2.failures == [errorconditions[0]]
        assert run.status is False

    def test_run_success(self) -> None:
        p99conditions = [
            Condition(lt(Decimal("200")), "value < 200"),
            Condition(gte(Decimal("0")), "value >= 0"),
        ]
        errorconditions = [
            Condition(lt(Decimal("0.01")), "value < 0.01"),
            Condition(gte(Decimal("0")), "value >= 0"),
        ]
        result1 = Result("latency_success_p99", Decimal("199.01"), p99conditions)
        result2 = Result("percent_fail", Decimal("0"), errorconditions)
        run = Run(
            "test-run-id",
            datetime.fromisoformat("2021-04-01T00:00:00"),
            datetime.fromisoformat("2021-04-01T01:00:00"),
            [result1, result2],
        )
        assert result1.failures == []
        assert result1.successes == p99conditions
        assert result2.failures == []
        assert result2.successes == errorconditions
        assert run.status is True

    def test_run_neutral(self) -> None:
        result = Result("some random measure", Decimal("123"), [])
        run = Run(
            "test-run-id",
            datetime.fromisoformat("2021-04-01T00:00:00"),
            datetime.fromisoformat("2021-04-01T01:00:00"),
            [result],
        )
        assert result.failures == []
        assert result.successes == []
        assert run.status is None


class TestConfig:
    def test_config(self) -> None:
        parameters = {
            "instance_type": "ml.m5.large",
            "initial_instance_count": "1",
            "steady_state_tps": "100",
        }
        p99conditions = [
            Condition(lt(Decimal("200")), "value < 200"),
            Condition(gte(Decimal("0")), "value >= 0"),
        ]
        errorconditions = [
            Condition(lt(Decimal("0.01")), "value < 0.01"),
            Condition(gte(Decimal("0")), "value >= 0"),
        ]
        requirements = {
            "latency_success_p99": p99conditions,
            "percent_fail": errorconditions,
        }
        config = Config(parameters, requirements)
        assert config.runs == []


@pytest.fixture
def sample_plan() -> Plan:
    parameter_lists = {
        "instance_type": [
            "ml.m5.large",
            "ml.m5.xlarge",
            "ml.m5.2xlarge",
            "ml.m5.4xlarge",
        ],
        "initial_instance_count": ["1"],
        "steady_state_tps": [
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "20",
            "30",
            "40",
            "50",
            "60",
            "70",
            "80",
            "90",
            "100",
            "200",
            "300",
            "400",
        ],
    }
    p99conditions = [
        Condition(lt(Decimal("200")), "value < 200"),
        Condition(gte(Decimal("0")), "value >= 0"),
    ]
    errorconditions = [
        Condition(lt(Decimal("0.01")), "value < 0.01"),
        Condition(gte(Decimal("0")), "value >= 0"),
    ]
    requirements = {
        "latency_success_p99": p99conditions,
        "percent_fail": errorconditions,
    }
    return Plan(parameter_lists, requirements)


class TestPlan:
    def test_plan(self, sample_plan: Plan) -> None:
        assert len(sample_plan.configs) == 88
        assert f"{sample_plan}".startswith("Plan")


class TestStepManager:
    def test_step_manager(self, sample_plan: Plan) -> None:
        step_manager = StepManager(sample_plan)
        with pytest.raises(NotImplementedError):
            next_config = step_manager.next()


class TestEnvironmentManager:
    def test_environment_manager(self, sample_plan: Plan) -> None:
        config = sample_plan.configs[("ml.m5.large", "1", "1")]
        environment_manager = EnvironmentManager()
        with pytest.raises(NotImplementedError):
            environment_manager.setup(config)
        with pytest.raises(NotImplementedError):
            environment_manager.teardown(config)


class TestLoadManager:
    def test_load_manager(self, sample_plan: Plan) -> None:
        config = sample_plan.configs[("ml.m5.large", "1", "1")]
        load_manager = LoadManager()
        with pytest.raises(NotImplementedError):
            run = load_manager.send(config)


class TestResultManager:
    def test_result_manager(self, sample_plan: Plan) -> None:
        config = sample_plan.configs[("ml.m5.large", "1", "1")]
        run = Run(
            "test-run-id",
            datetime.fromisoformat("2021-04-01T00:00:00"),
            datetime.fromisoformat("2021-04-01T01:00:00"),
            [],
        )
        result_manager = ResultManager()
        with pytest.raises(NotImplementedError):
            result_manager.query(config, run)


class TestReporter:
    def test_reporter(self, sample_plan: Plan) -> None:
        reporter = Reporter()
        with pytest.raises(NotImplementedError):
            reporter.render(sample_plan)


class TestWorkflow:
    def test_workflow(self, sample_plan: Plan) -> None:
        workflow = Workflow(
            plan=sample_plan,
            step_manager=MockStepManager(sample_plan),
            environment_manager=MockEnvironmentManager(),
            load_manager=MockLoadManager(),
            result_managers=[MockResultManager()],
            reporters=[MockReporter()],
        )
        recommendation = workflow.run()
        assert len(sample_plan.history) == 88
        assert recommendation["instance_type"] == "ml.m5.large"
        assert recommendation["initial_instance_count"] == "1"

    def test_workflow_with_teardown_true(self, sample_plan: Plan) -> None:
        workflow = Workflow(
            plan=sample_plan,
            step_manager=MockStepManager(sample_plan),
            environment_manager=MockEnvironmentManager(),
            load_manager=MockLoadManager(),
            result_managers=[MockResultManager()],
            reporters=[MockReporter()],
            teardown_between_steps=True,
            teardown_at_end=True,
        )
        with patch(
            "perfsize.environment.mock.MockEnvironmentManager.teardown"
        ) as teardown:
            recommendation = workflow.run()
            assert teardown.call_count == 88
            assert len(sample_plan.history) == 88
            assert recommendation["instance_type"] == "ml.m5.large"
            assert recommendation["initial_instance_count"] == "1"

    def test_workflow_with_teardown_false(self, sample_plan: Plan) -> None:
        workflow = Workflow(
            plan=sample_plan,
            step_manager=MockStepManager(sample_plan),
            environment_manager=MockEnvironmentManager(),
            load_manager=MockLoadManager(),
            result_managers=[MockResultManager()],
            reporters=[MockReporter()],
            teardown_between_steps=False,
            teardown_at_end=False,
        )
        with patch(
            "perfsize.environment.mock.MockEnvironmentManager.teardown"
        ) as teardown:
            recommendation = workflow.run()
            teardown.assert_not_called()
            assert recommendation["instance_type"] == "ml.m5.large"
            assert recommendation["initial_instance_count"] == "1"

    def test_workflow_with_teardown_at_end(self, sample_plan: Plan) -> None:
        workflow = Workflow(
            plan=sample_plan,
            step_manager=MockStepManager(sample_plan),
            environment_manager=MockEnvironmentManager(),
            load_manager=MockLoadManager(),
            result_managers=[MockResultManager()],
            reporters=[MockReporter()],
            teardown_between_steps=False,
            teardown_at_end=True,
        )
        with patch(
            "perfsize.environment.mock.MockEnvironmentManager.teardown"
        ) as teardown:
            recommendation = workflow.run()
            teardown.assert_called_once()
            assert recommendation["instance_type"] == "ml.m5.large"
            assert recommendation["initial_instance_count"] == "1"
