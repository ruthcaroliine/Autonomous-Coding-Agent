from app.agent.controller import AgentController
from app.agent.state import AgentState, Attempt, AttemptOutcome, ExecutionObservation


def make_attempt(attempt_number: int, outcome: AttemptOutcome) -> Attempt:
    return Attempt(
        attempt_number=attempt_number,
        code="print('hello')",
        observation=ExecutionObservation(exit_code=0),
        outcome=outcome,
        diagnosis="test diagnosis",
    )


def test_runtime_error_and_invalid_result_share_retry_budget() -> None:
    state = AgentState(task="test task", max_retry_attempts=3)

    state.add_attempt(make_attempt(1, AttemptOutcome.RUNTIME_ERROR))
    state.add_attempt(make_attempt(2, AttemptOutcome.INVALID_RESULT))

    assert state.attempts_used == 2
    assert state.attempts_remaining == 1
    assert not state.succeeded


def test_success_attempt_marks_state_succeeded() -> None:
    state = AgentState(task="test task", max_retry_attempts=3)

    state.add_attempt(make_attempt(1, AttemptOutcome.SUCCESS))

    assert state.attempts_used == 1
    assert state.attempts_remaining == 2
    assert state.succeeded


def test_controller_success_path() -> None:
    class SuccessfulController(AgentController):
        def _generate_code(self, state: AgentState) -> str:
            return "print('done')"

        def _execute_code(self, code: str) -> ExecutionObservation:
            return ExecutionObservation(
                stdout="done\n",
                exit_code=0,
                generated_files=["result.txt"],
            )

        def _validate_result(
            self,
            state: AgentState,
            observation: ExecutionObservation,
        ) -> bool:
            return True

    state = SuccessfulController().run("create a result")

    assert state.succeeded
    assert state.final_answer == "Task completed successfully."
    assert state.attempts_used == 1
    assert state.attempts[0].outcome == AttemptOutcome.SUCCESS
