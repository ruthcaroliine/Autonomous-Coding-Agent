from app.agent.state import AgentState, Attempt, AttemptOutcome, ExecutionObservation
from app.config import Settings, settings
from app.sandbox.executor import DockerSandboxExecutor


class AgentController:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings
        self.executor = DockerSandboxExecutor(app_settings)

    def run(self, task: str) -> AgentState:
        state = AgentState(
            task=task,
            max_retry_attempts=self.settings.max_retry_attempts,
        )

        while state.attempts_remaining > 0:
            attempt_number = state.attempts_used + 1
            code = self._generate_code(state)
            observation = self._execute_code(code)

            if observation.timed_out or observation.exit_code != 0:
                diagnosis = self._diagnose_runtime_error(observation)
                state.add_attempt(
                    Attempt(
                        attempt_number=attempt_number,
                        code=code,
                        observation=observation,
                        outcome=AttemptOutcome.RUNTIME_ERROR,
                        diagnosis=diagnosis,
                    )
                )
                continue

            is_valid = self._validate_result(state, observation)
            if is_valid:
                state.add_attempt(
                    Attempt(
                        attempt_number=attempt_number,
                        code=code,
                        observation=observation,
                        outcome=AttemptOutcome.SUCCESS,
                        diagnosis="Execution completed and result validation passed.",
                    )
                )
                state.final_answer = "Task completed successfully."
                state.succeeded = True
                break

            diagnosis = self._diagnose_invalid_result(observation)
            state.add_attempt(
                Attempt(
                    attempt_number=attempt_number,
                    code=code,
                    observation=observation,
                    outcome=AttemptOutcome.INVALID_RESULT,
                    diagnosis=diagnosis,
                )
            )

        if not state.succeeded:
            last_diagnosis = (
                state.attempts[-1].diagnosis
                if state.attempts
                else "No executable attempt was completed."
            )
            state.final_answer = (
                f"Failed after {state.attempts_used} attempt(s). "
                f"Last diagnosis: {last_diagnosis}"
            )

        return state

    def _generate_code(self, state: AgentState) -> str:
        raise NotImplementedError(
            "Phase 3 implements LLM code generation. "
            "The controller loop is wired, but code generation is not available yet."
        )

    def _execute_code(self, code: str) -> ExecutionObservation:
        return self.executor.execute(code)

    def _validate_result(
        self,
        state: AgentState,
        observation: ExecutionObservation,
    ) -> bool:
        raise NotImplementedError(
            "Phase 4 implements result validation. "
            "The controller loop is wired, but validation is not available yet."
        )

    def _diagnose_runtime_error(self, observation: ExecutionObservation) -> str:
        if observation.timed_out:
            return "Execution timed out."
        if observation.stderr:
            return f"Runtime error: {observation.stderr}"
        return f"Runtime error with exit code {observation.exit_code}."

    def _diagnose_invalid_result(self, observation: ExecutionObservation) -> str:
        if not observation.generated_files:
            return "Execution completed, but no generated files were found."
        return "Execution completed, but generated outputs did not pass validation."
