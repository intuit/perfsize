from perfsize.perfsize import Config, Plan, StepManager
from typing import Optional


class AllStepManager(StepManager):
    def __init__(self, plan: Plan) -> None:
        super().__init__(plan)
        self.stepindex = -1

    def next(self) -> Optional[Config]:
        # Check results of most recent step
        # TODO: Replace this logic as needed.
        # For demo purposes, will choose lowest successful Tuple.
        if not self.plan.recommendation:
            if self.plan.history:
                previous_config = self.plan.history[-1]
                if previous_config.runs:
                    previous_run = previous_config.runs[-1]
                    if previous_run.status:
                        self.plan.recommendation = previous_config.parameters

        # Determine next step
        self.stepindex = self.stepindex + 1
        if self.stepindex >= len(self.plan.combinations):
            return None
        combination = self.plan.combinations[self.stepindex]
        config = self.plan.configs[combination]
        self.plan.history.append(config)
        return config
