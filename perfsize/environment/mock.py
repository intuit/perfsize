from perfsize.perfsize import Config, EnvironmentManager


class MockEnvironmentManager(EnvironmentManager):
    def setup(self, config: Config) -> None:
        print(f"MockEnvironmentManager is setting up environment based on {config}")

    def teardown(self, config: Config) -> None:
        print(f"MockEnvironmentManager is tearing down environment based on {config}")
