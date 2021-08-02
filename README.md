![perfsize logo](.github/assets/images/perfsize-logo.png)

# perfsize

[![Python Publish](https://github.com/intuit/perfsize/actions/workflows/python-publish.yml/badge.svg)](https://github.com/intuit/perfsize/actions/workflows/python-publish.yml)

`perfsize` is a tool that uses automated performance testing to determine the right size of
infrastructure that can meet a given set of requirements. This repo is for common interfaces and
shared components that can be imported into technology specific implementations.

One example implementation is
[perfsize-sagemaker](https://github.com/intuit/perfsize-sagemaker)
which is the open source implementation that is specific to AWS SageMaker infrastructure.
The environment update uses the `boto3` SDK, and the traffic generator uses
[sagemaker-gatling](https://github.com/intuit/sagemaker-gatling)
to call SageMaker endpoints directly.

The goal is to make `perfsize` general enough so that it can be included in some other
implementation for "x" infrastructure, which could have its own SDK for updating infrastructure, and
its own load generator for sending traffic.


## Data Structures

- `Condition`
  - `function`: any function that takes a Decimal value and returns True for success, False for
    failure. Some examples provided in the tests use comparison operators `lt`, `lte`, `eq`, `ne`,
    `gt`, `gte` to create functions to check a given value against specified thresholds.
  - `description`: string summary for what the function is checking, useful for printing in
    reports.
  - Example: `Condition(lt(Decimal("200")), "value < 200")`

- `Result`
  - `metric`: string id of metric being measured. Examples could be `error_percent`, `p99_total`,
    `p99_pass`, `p99_fail`.
  - `value`: the Decimal value measured.
  - `conditions`: list of `Condition` to check.
  - `successes()`: subset list of `Condition` that succeeded based on given value.
  - `failures()`: subset list of `Condition` that failed based on given value.
  - Example: `Result("p99 response time", Decimal("201"), conditions)`

- `Run`
  - `start`: starting timestamp of test run.
  - `end`: ending timestamp of test run.
  - `results`: list of `Result`.
  - `status()`: False if any result has failures, else True if any result has successes, else None.
  - Example:
    ```
    result1 = Result("p99 response time", Decimal("199.01"), p99conditions)
    result2 = Result("error rate", Decimal("0"), errorconditions)
    run = Run(
        datetime.fromisoformat("2021-04-01T00:00:00"),
        datetime.fromisoformat("2021-04-01T01:00:00"),
        [result1, result2],
    )
    ```

- `Config`
  - `parameters`: dictionary mapping parameter name to parameter value, to describe all settings for
    a particular configuration to be tested. Example:
    ```
    parameters = {
        "instance type": "ml.m5.large",
        "instance count": "1",
        "tps": "100",
    }
    ```
  - `requirements`: dictionary mapping a metric name to a list of `Condition`, to describe how each
    measured `Result` will be checked for success.
    ```
    p99conditions = [
        Condition(lt(Decimal("200")), "value < 200"),
        Condition(gte(Decimal("0")), "value >= 0"),
    ]
    errorconditions = [
        Condition(lt(Decimal("0.01")), "value < 0.01"),
        Condition(gte(Decimal("0")), "value >= 0"),
    ]
    requirements = {
        "p99 response time": p99conditions,
        "error rate": errorconditions,
    }
    ```
  - `runs`: list of test `Run` for the given config.
  - Example:
    ```
    config = Config(parameters, requirements)
    ```

- `Plan`
  - `parameter_lists`: dictionary mapping parameter name to list of possible values to test.
    Example:
    ```
    parameter_lists = {
        "instance type": [
            "ml.m5.large",
            "ml.m5.xlarge",
            "ml.m5.2xlarge",
            "ml.m5.4xlarge",
        ],
        "instance count": ["1"],
        "tps": [
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
    ```
  - `requirements`: dictionary mapping a metric name to a list of `Condition`, to describe how each
    measured `Result` will be checked for success.
  - `combinations`: list of tuples covering the cross product of possible combinations using the
    values from given parameter lists. Example:
    ```
    [
        ("ml.m5.large", "1", "1"),
        ("ml.m5.large", "1", "2"),
        ("ml.m5.large", "1", "3"),
        ...
        ("ml.m5.xlarge", "1", "1"),
        ...
        ("ml.m5.2xlarge", "1", "1"),
        ...
        ("ml.m5.4xlarge", "1", "1"),
        ...
        ("ml.m5.4xlarge", "1", "300"),
        ("ml.m5.4xlarge", "1", "400"),
    ]
    ```
  - `configs`: dictionary mapping each tuple above to a `Config` object. Example:
    ```
    {
        ("ml.m5.large", "1", "1"): Config(
                                             {
                                                 "instance type": "ml.m5.large",
                                                 "instance count": "1",
                                                 "tps": "1",
                                             },
                                             requirements
                                         ),
        ("ml.m5.large", "1", "2"): Config(...),
        ("ml.m5.large", "1", "3"): Config(...),
        ...
        ("ml.m5.xlarge", "1", "1"): Config(...),
        ...
        ("ml.m5.2xlarge", "1", "1"): Config(...),
        ...
        ("ml.m5.4xlarge", "1", "1"): Config(...),
        ...
        ("ml.m5.4xlarge", "1", "300"): Config(...),
        ("ml.m5.4xlarge", "1", "400"): Config(...),
    }
    ```
  - `history`: list of `Config` tested so far.
  - `recommendation`: mapping of parameter name to parameter value, to describe all settings for a
    recommended configuration found to be the best so far. Example:
    ```
    recommendation = {
        "instance type": "ml.m5.large",
        "instance count": "2",
    }
    ```

## Interfaces

- `StepManager`
  - `next()`: based on current state of configs tested and their results, return next Config to
    test, or None if process is completed.
  - Example implementations:
    - `AllStepManager`: test every config in order.
    - `FirstFailureStepManager`: current ml-pathfinder algorithm.
    - `BinarySearchStepManager`: try binary search over TPS range given.

- `EnvironmentManager`
  - `setup()`: update target environment based on settings from given `Config`.
  - `teardown()`: clean up target environment based on settings from given `Config`.
  - Example implementations:
    - `SageMakerEnvironmentManager`: update AWS SageMaker environment using boto3
    - `XEnvironmentManager`: update "X" environment using "X" SDK

- `LoadManager`
  - `send()`: create `Run` to track timing and results, send target test traffic of given `Config`.
  - Example implementations:
    - `SageMakerLoadManager`: send traffic using `sagemaker-gatling` library
    - `XLoadManager`: send traffic using "X" SDK

- `ResultManager`
  - `query()`: for the time period of a given `Run`, gather metrics and append as `Result` items on
    the `Run`.
  - Example implementations:
    - `GatlingResultManager`: get results from parsing Gatling output files
    - `SplunkResultManager`: get results from Splunk server with given query
    - `WavefrontResultManager`: get results from Wavefront
    - `CloudWatchResultManager`: get results from CloudWatch

- `Reporter`
  - `render()`: generate a report given the tested configs and their results.
  - Example implementations:
    - `DefaultReporter`: string representation formatted by white space
    - `HTMLReporter`: HTML string

- `Workflow`
  - `run()`: set up the test plan and call various managers to do work and determine next steps.
    When all test runs are completed, update results and return the recommended settings.
  - `DefaultWorkflow` - call each manager below and print placeholder text to simulate test activity
  - `SageMakerWorkflow` - call SageMaker specific managers
  - `XWorkflow` - call "X" specific managers


# Installation

[perfsize]((https://pypi.org/project/perfsize/)) is available at The Python Package Index (PyPI).

Install using `pip` (or your preferred dependency manager and virtual environment):

```bash
pip install perfsize
```

# Usage

See tests folder for examples.

# Development

Clone repository:

```
git clone https://github.com/intuit/perfsize.git
cd perfsize
```

Install `poetry` for dependency management and packaging:
```
https://python-poetry.org/docs/
```

Set up your virtual environment (with package versions from `poetry.lock` file):
```
poetry install
```

Start a shell for your virtual environment for running additional commands that need access to the
installed packages:
```
poetry shell
python anything.py
```

Other commands from the Makefile:
- `make format`: format code with [black](https://github.com/psf/black)
- `make test`: run all tests
- `make build`: create artifacts
- `make publish`: push artifacts to PyPI

See packages installed:
```
poetry show --tree
```

See info about environments:
```
poetry env info
poetry env list
```

## Integration with your IDE

Optional. For integration with your IDE, you can run `poetry env info` to get the Virtualenv path,
like `/Users/your-name-here/Library/Caches/pypoetry/virtualenvs/perfsize-VvRdEPIE-py3.9`, and point your IDE
to the `bin/python` there.

In IntelliJ:
- Create a new Python SDK option under
  `File > Project Structure > Platform Settings > SDKs > Add new Python SDK > Virtualenv Environment > Existing environment > Interpreter`
  and specify the path above including `bin/python`.
- Update `Project Settings > Project SDK` and `Project Settings > Modules > Module SDK` to point to
  the SDK you just created.


# Publishing a Release️

Make sure you are doing this from a clean working directory.

Possible release types are:
- `patch`
- `minor`
- `major`
- `prepatch`
- `preminor`
- `premajor`
- `prerelease`

```bash
VERSION_BUMP_MSG=$(poetry version --no-ansi <release>)
NEW_VERSION=$(poetry version --no-ansi | cut -d ' ' -f2)
git commit -am "${VERSION_BUMP_MSG}"
git tag "v${NEW_VERSION}"
git push && git push --tags
```

Once tag is published as a release, GitHub Action
[python-publish.yml](.github/workflows/python-publish.yml)
will publish the artifacts to
[perfsize](https://pypi.org/project/perfsize/)
on PyPI.


# Contributing

Feel free to open an
[issue](https://github.com/intuit/perfsize/issues)
or
[pull request](https://github.com/intuit/perfsize/pulls)!

For major changes, please open an issue first to discuss what you would like to change.

Make sure to read our [code of conduct](CODE_OF_CONDUCT.md).


# License

This project is licensed under the terms of the [Apache License 2.0](LICENSE).
