from perfsize.perfsize import Config, Plan
from perfsize.step.all import AllStepManager
from typing import Optional


class MockStepManager(AllStepManager):
    def __init__(self, plan: Plan) -> None:
        super().__init__(plan)

    def next(self) -> Optional[Config]:
        config = super().next()
        print(f"MockStepManager is choosing next step {config}")
        return config
