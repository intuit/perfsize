from datetime import datetime
from perfsize.perfsize import Config, LoadManager, Run
from time import sleep


class MockLoadManager(LoadManager):
    def send(self, config: Config) -> Run:
        print(f"MockLoadManager is sending load based on {config}")
        start = datetime.utcnow()
        sleep(0.01)  # force some delay so timestamps between runs are different
        end = datetime.utcnow()
        id = f"{start.timestamp()}-test"
        return Run(id, start, end, results=[])
