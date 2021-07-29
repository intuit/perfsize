from datetime import datetime
from decimal import Decimal
import logging.config
from numpy import array, min, max, percentile
import os
from pandas import DataFrame
from perfsize.perfsize import Condition, Config, gte, lt, Result, ResultManager, Run
from pprint import pprint
from typing import Dict, List, Optional, Union
import yaml

log = logging.getLogger(__name__)


# Reserved word for summarizing stats by request name, represents all requests.
ALL_REQUESTS = "__all_requests__"


class Metric:
    count_success = "count_success"
    count_fail = "count_fail"
    count_total = "count_total"
    percent_success = "percent_success"
    percent_fail = "percent_fail"
    latency_success_min = "latency_success_min"
    latency_success_p25 = "latency_success_p25"
    latency_success_p50 = "latency_success_p50"
    latency_success_p75 = "latency_success_p75"
    latency_success_p90 = "latency_success_p90"
    latency_success_p95 = "latency_success_p95"
    latency_success_p98 = "latency_success_p98"
    latency_success_p99 = "latency_success_p99"
    latency_success_max = "latency_success_max"
    simulation_start = "simulation_start"
    simulation_end = "simulation_end"


class GatlingResultManager(ResultManager):
    def __init__(self, results_path: str):
        self.results_path = results_path

    def get_stats(self, df: DataFrame) -> Dict[str, Decimal]:
        df_success = df[(df["status"] == "OK")]
        df_fail = df[(df["status"] == "KO")]
        latency_list_success = list(df_success["latency"])
        latency_list_fail = list(df_fail["latency"])
        count_success = Decimal(len(latency_list_success))
        count_fail = Decimal(len(latency_list_fail))
        count_total = count_success + count_fail
        latency_success = array(latency_list_success)
        if not latency_list_success:
            # Handle case of empty success list by forcing 0.
            latency_success = array([0])
        stats: Dict[str, Decimal] = {}
        stats[Metric.count_success] = count_success
        stats[Metric.count_fail] = count_fail
        stats[Metric.count_total] = count_total
        stats[Metric.percent_success] = (count_success / count_total) * 100
        stats[Metric.percent_fail] = (count_fail / count_total) * 100
        stats[Metric.latency_success_min] = Decimal(int(min(latency_success)))
        stats[Metric.latency_success_p25] = Decimal(
            int(percentile(latency_success, 25))
        )
        stats[Metric.latency_success_p50] = Decimal(
            int(percentile(latency_success, 50))
        )
        stats[Metric.latency_success_p75] = Decimal(
            int(percentile(latency_success, 75))
        )
        stats[Metric.latency_success_p90] = Decimal(
            int(percentile(latency_success, 90))
        )
        stats[Metric.latency_success_p95] = Decimal(
            int(percentile(latency_success, 95))
        )
        stats[Metric.latency_success_p98] = Decimal(
            int(percentile(latency_success, 98))
        )
        stats[Metric.latency_success_p99] = Decimal(
            int(percentile(latency_success, 99))
        )
        stats[Metric.latency_success_max] = Decimal(int(max(latency_success)))
        stats[Metric.simulation_start] = Decimal(int(min(array(list(df["start"])))))
        stats[Metric.simulation_end] = Decimal(int(max(array(list(df["end"])))))
        return stats

    def parse(self, simulation_log_path: str) -> Dict[str, Dict[str, Decimal]]:
        request_names: List[str] = []
        requests: List[Dict[str, Union[datetime, str, int]]] = []

        with open(simulation_log_path) as f:
            lines = f.readlines()
        if not lines:
            raise RuntimeError(f"ERROR: Simulation log is empty: {simulation_log_path}")

        # Check Gatling version is supported. First line expected to have:
        # RUN	GenericSageMakerScenario	test_run_tag	1620982654518	 	3.2.0
        line = lines[0]
        if not line.startswith("RUN"):
            raise ValueError(f"Unexpected first line: {line}")
        tokens = line.split("\t")
        if len(tokens) != 6:
            raise ValueError(f"Unexpected run format: {line}")
        gatling_version = tokens[5].strip("\n")  # 3.2.0
        if gatling_version not in ("3.2.0"):
            log.warning(
                f"Unrecognized Gatling version may not be supported: {gatling_version}"
            )

        # Sample lines from simulation.log (there are other line formats too):
        # REQUEST	1		Predict-intelligent-case-routing-1-happy_path	1573776120651	1573776125919	KO	status.find.is(200), but actually found 503
        # REQUEST	6		Predict-intelligent-case-routing-1-happy_path	1573776125622	1573776129161	OK	 .
        #
        # These lines are tab delimited. The OK example has no error message but
        # ends with a space character (but added a period here as a formatting
        # placeholder so the IDE does not delete trailing whitespace).
        for line in lines:
            if line.startswith("REQUEST"):
                tokens = line.split("\t")
                if len(tokens) != 8:
                    # simulation.log format can change between Gatling versions
                    raise ValueError(f"Unexpected request format: {line}")
                name = tokens[3]  # Predict-intelligent-case-routing-1-happy_path
                start = int(tokens[4])  # 1573776120651
                end = int(tokens[5])  # 1573776125919
                status = tokens[6]  # KO or OK
                request: Dict[str, Union[datetime, str, int]] = {}
                request["name"] = name
                if name == ALL_REQUESTS:
                    raise RuntimeError(
                        f"ERROR: Request name cannot be reserved word '{ALL_REQUESTS}'."
                    )
                if name not in request_names:
                    request_names.append(name)
                request["start"] = start
                request["end"] = end
                request["latency"] = end - start
                request["status"] = status
                request["time"] = datetime.fromtimestamp(int(start / 1000))
                requests.append(request)
        if not requests:
            raise RuntimeError(
                f"ERROR: Simulation log has no requests: {simulation_log_path}"
            )

        df = DataFrame(requests)
        df.set_index("time", inplace=True)
        combined_stats: Dict[str, Dict[str, Decimal]] = {}
        combined_stats[ALL_REQUESTS] = self.get_stats(df)
        for name in request_names:
            df_subset = df[(df["name"] == name)]
            combined_stats[name] = self.get_stats(df_subset)
        return combined_stats

    # Gatling saves results in folders named with given run_tag appended by timestamp.
    # Search results_path for this run_tag, which must be unique, and return
    # directory name.
    def find_run_dir(self, run_tag: str) -> str:
        run_dir: Optional[str] = None
        for dirpath, dirnames, filenames in os.walk(self.results_path):
            for dir in dirnames:
                if dir.startswith(run_tag):
                    if not run_dir:
                        run_dir = dir
                    else:
                        raise RuntimeError(
                            f"ERROR: Found multiple matches with run_tag {run_tag}: {run_dir} and {dir}"
                        )
        if not run_dir:
            raise RuntimeError(
                f"ERROR: Unable to find directory starting with run_tag {run_tag}"
            )
        return run_dir

    def query(self, config: Config, run: Run) -> None:
        log.debug(f"About to process {self.results_path}/{run.id}*/simulation.log")
        run_dir = self.find_run_dir(run.id)
        simulation_log_path = (
            self.results_path + os.sep + run_dir + os.sep + "simulation.log"
        )
        combined_stats = self.parse(simulation_log_path)
        # pprint(combined_stats)

        # Add stat results to run. Include any matching requirement conditions.
        stats = combined_stats[ALL_REQUESTS]
        for metric in stats:
            conditions = []
            if metric in config.requirements:
                conditions = config.requirements[metric]
            run.results.append(
                Result(metric=metric, value=stats[metric], conditions=conditions)
            )

        # TODO: Add results by request name split as well. Maybe use naming convention f"{request_name}_{metric}")
        # TODO: Assert that time range is valid within run definition.
