from datetime import datetime
import decimal
from decimal import Decimal, FloatOperation
import itertools
from typing import (
    Callable,
    Dict,
    KeysView,
    List,
    Optional,
    Tuple,
    ValuesView,
)


# Avoid accidental mixing of decimals and floats in constructors or comparisons
c = decimal.getcontext()
c.traps[FloatOperation] = True


def lt(target: Decimal) -> Callable[[Decimal], bool]:
    return lambda x: x < target


def lte(target: Decimal) -> Callable[[Decimal], bool]:
    return lambda x: x <= target


def gt(target: Decimal) -> Callable[[Decimal], bool]:
    return lambda x: x > target


def gte(target: Decimal) -> Callable[[Decimal], bool]:
    return lambda x: x >= target


def eq(target: Decimal) -> Callable[[Decimal], bool]:
    return lambda x: x == target


def neq(target: Decimal) -> Callable[[Decimal], bool]:
    return lambda x: x != target


class Condition:
    def __init__(self, function: Callable[[Decimal], bool], description: str):
        self.function = function
        self.description = description

    def __repr__(self) -> str:
        return f"Condition('{self.description}')"


class Result:
    def __init__(self, metric: str, value: Decimal, conditions: List[Condition]):
        self.metric = metric
        self.value = value
        self.conditions = conditions

    # TODO: Enable value to be DataFrame and apply condition to check it.

    @property
    def successes(self) -> List[Condition]:
        if not self.conditions:
            return []
        return list(filter(lambda c: c.function(self.value), self.conditions))

    @property
    def failures(self) -> List[Condition]:
        if not self.conditions:
            return []
        return list(filter(lambda c: not c.function(self.value), self.conditions))

    def __repr__(self) -> str:
        return f"Result(metric={self.metric},value={self.value},conditions={self.conditions})"


class Run:
    def __init__(self, id: str, start: datetime, end: datetime, results: List[Result]):
        self.id = id
        self.start = start
        self.end = end
        self.results = results

    def __repr__(self) -> str:
        return (
            f"Run(id={self.id},start={self.start},end={self.end},results={self.results}"
        )

    @property
    def status(self) -> Optional[bool]:
        # False if any failure, else True if any success, else None
        found_success: Optional[bool] = None
        for result in self.results:
            if result.successes:
                found_success = True
            if result.failures:
                return False
        return found_success

    # TODO: Add context (screenshots, graphs, captions, DataFrames) per Run/Plan


class Config:
    def __init__(
        self, parameters: Dict[str, str], requirements: Dict[str, List[Condition]]
    ):
        self.parameters = parameters
        self.requirements = requirements
        self.runs: List[Run] = []

    def __repr__(self) -> str:
        return f"Config(parameters={self.parameters},requirements={self.requirements},runs={self.runs})"


class Plan:
    def __init__(
        self,
        parameter_lists: Dict[str, List[str]],
        requirements: Dict[str, List[Condition]],
    ):
        self.parameter_lists = parameter_lists
        self.requirements = requirements

        self.configs: Dict[Tuple[str, ...], Config] = {}
        parameter_names: KeysView[str] = parameter_lists.keys()
        parameter_values: ValuesView[List[str]] = parameter_lists.values()
        self.combinations: List[Tuple[str, ...]] = list(
            itertools.product(*parameter_values)
        )
        for combo in self.combinations:
            parameters: Dict[str, str] = {}
            index = 0
            for key in parameter_names:
                parameters[key] = combo[index]
                index = index + 1
            self.configs[combo] = Config(parameters, requirements)

        self.history: List[Config] = []
        self.recommendation: Dict[str, str] = {}

    def __repr__(self) -> str:
        return f"Plan(parameter_lists={self.parameter_lists},requirements={self.requirements})"

    # TODO: Add properties for earliest start and latest end times across runs


class StepManager:
    def __init__(self, plan: Plan):
        self.plan = plan

    def next(self) -> Optional[Config]:
        # TODO: read/update plan state like `combinations` and `history`
        # TODO: each implementation can add other state tracking like step index
        raise NotImplementedError


class EnvironmentManager:
    def setup(self, config: Config) -> None:
        raise NotImplementedError

    def teardown(self, config: Config) -> None:
        raise NotImplementedError


class LoadManager:
    def send(self, config: Config) -> Run:
        # TODO: create Run object to track timing and results
        raise NotImplementedError


class ResultManager:
    def query(self, config: Config, run: Run) -> None:
        raise NotImplementedError


class Reporter:
    def render(self, plan: Plan) -> str:
        raise NotImplementedError


class Workflow:
    def __init__(
        self,
        plan: Plan,
        step_manager: StepManager,
        environment_manager: EnvironmentManager,
        load_manager: LoadManager,
        result_managers: List[ResultManager],
        reporters: List[Reporter],
        teardown_between_steps: bool = True,
        teardown_at_end: bool = True,
    ):
        self.plan = plan
        self.step_manager = step_manager
        self.environment_manager = environment_manager
        self.load_manager = load_manager
        self.result_managers = result_managers
        self.reporters = reporters
        self.teardown_between_steps = teardown_between_steps
        self.teardown_at_end = teardown_at_end

    def run(self) -> Dict[str, str]:
        config = self.step_manager.next()
        while config:
            self.environment_manager.setup(config)
            run = self.load_manager.send(config)
            config.runs.append(run)
            for result_manager in self.result_managers:
                result_manager.query(config, run)
            print(f"Step: {config}")
            if self.teardown_between_steps:
                self.environment_manager.teardown(config)
            next_config = self.step_manager.next()
            # If no more configs to test, and teardown not already happening
            # between steps, do teardown on final config.
            if (
                not next_config
                and not self.teardown_between_steps
                and self.teardown_at_end
            ):
                self.environment_manager.teardown(config)
            config = next_config
        for reporter in self.reporters:
            print(reporter.render(self.plan))
        return self.plan.recommendation
