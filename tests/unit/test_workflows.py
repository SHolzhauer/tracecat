"""Unit tests for workflows.

Objectives
----------
1. Test that the workflows can be executed in an isolated environment
2. Test that the workflows can be executed with the correct inputs and outputs
3. Test that the workflows can be executed with the correct ordering

"""

import asyncio
import os
from pathlib import Path
from typing import Any

import pytest
import yaml
from loguru import logger
from slugify import slugify
from temporalio.common import RetryPolicy
from temporalio.worker import Worker

from tracecat.contexts import ctx_role
from tracecat.dsl.common import DSLInput, get_temporal_client
from tracecat.dsl.worker import new_sandbox_runner
from tracecat.dsl.workflow import DSLActivities, DSLContext, DSLRunArgs, DSLWorkflow
from tracecat.expressions import ExprContext
from tracecat.identifiers.resource import ResourcePrefix
from tracecat.types.exceptions import TracecatExpressionError

DATA_PATH = Path(__file__).parent.parent.joinpath("data/workflows")
SHARED_TEST_DEFNS = list(DATA_PATH.glob("shared_*.yml"))
ORDERING_TEST_DEFNS = list(DATA_PATH.glob("unit_ordering_*.yml"))


TEST_WF_ID = "wf-00000000000000000000000000000000"


def generate_test_exec_id(name: str) -> str:
    return (
        TEST_WF_ID
        + f":{ResourcePrefix.WORKFLOW_EXECUTION}-"
        + slugify(name, separator="_")
    )


@pytest.fixture
def mock_registry():
    """Mock registry for testing UDFs.

    Note
    ----
    - This fixture is used to test the integration of UDFs with the workflow.
    - It's unreachable by an external worker, as the worker will not have access
    to these functions when it starts up.
    """
    from tracecat.registry import registry

    # NOTE!!!!!!!: Didn't want to spend too much time figuring out how
    # to grab the actual execution order using the client, so I'm using a
    # hacky way to get the order of execution. TO FIX LATER
    # The counter doesn't get reset properly so you should never use this outside
    # of the 'ordering' tests
    def counter():
        i = 0
        while True:
            yield i
            i += 1

    counter_gen = counter()
    if "integration_test.count" not in registry:

        @registry.register(
            description="Counts up from 0",
            namespace="integration_test",
        )
        def count(arg: str | None = None) -> int:
            order = next(counter_gen)
            return order

    if "integration_test.passthrough" not in registry:

        @registry.register(
            description="passes through",
            namespace="integration_test",
        )
        async def passthrough(num: int) -> int:
            await asyncio.sleep(0.1)
            return num

    registry.init()
    yield registry
    counter_gen = counter()  # Reset the counter generator


# Fixture to load workflow DSLs from YAML files
@pytest.fixture
def dsl(request: pytest.FixtureRequest) -> DSLInput:
    path: list[Path] = request.param
    dsl = DSLInput.from_yaml(path)
    return dsl


# Fixture to load yaml files from name
@pytest.fixture
def expected(request: pytest.FixtureRequest) -> dict[str, Any]:
    path: Path = request.param
    with path.open() as f:
        yaml_data = f.read()
    data = yaml.safe_load(yaml_data)
    return {key: (value or {}) for key, value in data.items()}


@pytest.mark.parametrize("dsl", SHARED_TEST_DEFNS, indirect=True)
@pytest.mark.asyncio
async def test_workflow_can_run_from_yaml(
    dsl, temporal_cluster, mock_registry, auth_sandbox
):
    test_name = f"test_workflow_can_run_from_yaml-{dsl.title}"
    wf_exec_id = generate_test_exec_id(test_name)
    client = await get_temporal_client()
    # Run workflow
    async with Worker(
        client,
        task_queue=os.environ["TEMPORAL__CLUSTER_QUEUE"],
        activities=DSLActivities.load(),
        workflows=[DSLWorkflow],
        workflow_runner=new_sandbox_runner(),
    ):
        result = await client.execute_workflow(
            DSLWorkflow.run,
            DSLRunArgs(dsl=dsl, role=ctx_role.get(), wf_id=TEST_WF_ID),
            id=wf_exec_id,
            task_queue=os.environ["TEMPORAL__CLUSTER_QUEUE"],
            retry_policy=RetryPolicy(maximum_attempts=1),
        )

    logger.info(result)
    assert len(result[ExprContext.ACTIONS]) == len(dsl.actions)


@pytest.mark.asyncio
async def test_workflow_udf_registry_function_can_be_called(mock_registry):
    """We need to test that the ordering of the workflow tasks is correct."""
    udf = mock_registry.get("integration_test.count")
    for i in range(10):
        assert i == udf.fn()


@pytest.mark.asyncio
async def test_workflow_udf_registry_async_function_can_be_called(mock_registry):
    """We need to test that the ordering of the workflow tasks is correct."""
    udf = mock_registry.get("integration_test.passthrough")

    async def coro(i: int):
        v = await udf.fn(num=i)
        assert i == v

    async with asyncio.TaskGroup() as tg:
        tasks = []
        for i in range(10):
            tasks.append(tg.create_task(coro(i)))


def assert_respectful_exec_order(dsl: DSLInput, final_context: DSLContext):
    act_outputs = final_context[ExprContext.ACTIONS]
    for action in dsl.actions:
        target = action.ref
        for source in action.depends_on:
            source_order = act_outputs[source]["result"]
            target_order = act_outputs[target]["result"]
            assert source_order < target_order


@pytest.mark.parametrize("dsl", ORDERING_TEST_DEFNS, indirect=True)
@pytest.mark.asyncio
async def test_workflow_ordering_is_correct(
    dsl, temporal_cluster, mock_registry, auth_sandbox
):
    """We need to test that the ordering of the workflow tasks is correct."""

    # Connect client

    test_name = f"test_workflow_ordering_is_correct-{dsl.title}"
    wf_exec_id = generate_test_exec_id(test_name)
    client = await get_temporal_client()
    # Run a worker for the activities and workflow
    async with Worker(
        client,
        task_queue=os.environ["TEMPORAL__CLUSTER_QUEUE"],
        activities=DSLActivities.load(),
        workflows=[DSLWorkflow],
        workflow_runner=new_sandbox_runner(),
    ):
        result = await client.execute_workflow(
            DSLWorkflow.run,
            DSLRunArgs(dsl=dsl, role=ctx_role.get(), wf_id=TEST_WF_ID),
            id=wf_exec_id,
            task_queue=os.environ["TEMPORAL__CLUSTER_QUEUE"],
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
    # Iterate over the actual ordering of the tasks
    # and compare that in the topological ordering every LHS task in a pair executed before the RHS task

    # Check that the execution order respects the graph edges
    assert_respectful_exec_order(dsl, result)


def _get_expected(path: Path) -> dict[str, Any]:
    with path.open() as f:
        yaml_data = f.read()
    data = yaml.safe_load(yaml_data)
    return {key: (value or {}) for key, value in data.items()}


# Get the paths from the test name
@pytest.fixture
def dsl_with_expected(request: pytest.FixtureRequest) -> DSLInput:
    test_name = request.param
    data_path = DATA_PATH / f"{test_name}.yml"
    expected_path = DATA_PATH / f"{test_name}_expected.yml"
    dsl = DSLInput.from_yaml(data_path)
    expected = _get_expected(expected_path)
    return dsl, expected


correctness_test_cases = [
    "unit_conditional_adder_tree_skips",
    "unit_conditional_adder_tree_continues",
    "unit_conditional_adder_tree_skip_propagates",
    "unit_conditional_adder_diamond_skip_with_join_weak_dep",
    "unit_transform_forwarder_loop",
    "unit_transform_forwarder_loop_chained",
    "unit_transform_forwarder_arrange",
    "unit_transform_forwarder_arrange_loop",
    "unit_transform_forwarder_zip",
    "unit_transform_forwarder_map_loop",
]


@pytest.mark.parametrize(
    "dsl_with_expected",
    correctness_test_cases,
    indirect=True,
    ids=correctness_test_cases,
)
@pytest.mark.asyncio
async def test_workflow_completes_and_correct(
    dsl_with_expected, temporal_cluster, mock_registry, auth_sandbox
):
    dsl, expected = dsl_with_expected
    test_name = f"test_correctness_execution-{dsl.title}"
    wf_exec_id = generate_test_exec_id(test_name)

    client = await get_temporal_client()
    # Run a worker for the activities and workflow
    async with Worker(
        client,
        task_queue=os.environ["TEMPORAL__CLUSTER_QUEUE"],
        activities=DSLActivities.load(),
        workflows=[DSLWorkflow],
        workflow_runner=new_sandbox_runner(),
    ):
        result = await client.execute_workflow(
            DSLWorkflow.run,
            DSLRunArgs(dsl=dsl, role=ctx_role.get(), wf_id=TEST_WF_ID),
            id=wf_exec_id,
            task_queue=os.environ["TEMPORAL__CLUSTER_QUEUE"],
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
    assert result == expected


@pytest.mark.parametrize(
    "dsl",
    [DATA_PATH / "stress_adder_tree.yml"],
    indirect=True,
)
@pytest.mark.slow
@pytest.mark.asyncio
async def test_stress_workflow(dsl, temporal_cluster, mock_registry, auth_sandbox):
    """Test that we can have multiple executions of the same workflow running at the same time."""
    test_name = f"test_stress_workflow-{dsl.title}"
    client = await get_temporal_client()

    tasks: list[asyncio.Task] = []
    async with (
        Worker(
            client,
            task_queue=os.environ["TEMPORAL__CLUSTER_QUEUE"],
            activities=DSLActivities.load(),
            workflows=[DSLWorkflow],
            workflow_runner=new_sandbox_runner(),
        ),
    ):
        async with asyncio.TaskGroup() as tg:
            # We can have multiple executions of the same workflow running at the same time
            for i in range(100):
                wf_exec_id = generate_test_exec_id(test_name + f"-{i}")
                task = tg.create_task(
                    client.execute_workflow(
                        DSLWorkflow.run,
                        DSLRunArgs(dsl=dsl, role=ctx_role.get(), wf_id=TEST_WF_ID),
                        id=wf_exec_id,
                        task_queue=os.environ["TEMPORAL__CLUSTER_QUEUE"],
                        retry_policy=RetryPolicy(maximum_attempts=1),
                    )
                )
                tasks.append(task)

    assert all(task.done() for task in tasks)


@pytest.mark.parametrize(
    "dsl",
    [DATA_PATH / "unit_conditional_adder_diamond_skip_with_join_strong_dep_fails.yml"],
    indirect=True,
)
@pytest.mark.asyncio
@pytest.mark.skip
async def test_conditional_execution_fails(
    dsl, temporal_cluster, mock_registry, auth_sandbox
):
    test_name = f"test_conditional_execution-{dsl.title}"
    wf_exec_id = generate_test_exec_id(test_name)
    client = await get_temporal_client()
    async with Worker(
        client,
        task_queue=os.environ["TEMPORAL__CLUSTER_QUEUE"],
        activities=DSLActivities.load(),
        workflows=[DSLWorkflow],
        workflow_runner=new_sandbox_runner(),
    ):
        # NOTE: I can't seem to figure out how to catch the exception thrown by the workflow
        # We need to figure out how to bubble up certain exceptions to the client
        # Or allow certain exceptions to control workflow execution
        with pytest.raises(TracecatExpressionError) as e:
            await client.execute_workflow(
                DSLWorkflow.run,
                DSLRunArgs(dsl=dsl, role=ctx_role.get(), wf_id=TEST_WF_ID),
                id=wf_exec_id,
                task_queue=os.environ["TEMPORAL__CLUSTER_QUEUE"],
                retry_policy=RetryPolicy(
                    maximum_attempts=0,
                    non_retryable_error_types=[
                        "tracecat.types.exceptions.TracecatExpressionError"
                        "TracecatValidationError"
                    ],
                ),
            )
        assert "Operand has no path" in str(e)
