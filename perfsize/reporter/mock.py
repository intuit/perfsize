from perfsize.perfsize import Plan, Reporter
from pprint import pformat


class MockReporter(Reporter):
    def render(self, plan: Plan) -> str:
        print(f"MockReporter is rendering {plan}")
        return f"""\
Requirements:
{pformat(plan.requirements)}

Configs:
{pformat(plan.configs, sort_dicts=False)}

History:
{pformat(plan.history)}

Recommendation:
{pformat(plan.recommendation)}
"""
