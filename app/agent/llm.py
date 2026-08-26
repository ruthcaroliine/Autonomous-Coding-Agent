import google.generativeai as genai

from app.config import settings

genai.configure(api_key=settings.google_api_key)
_model = genai.GenerativeModel(settings.llm_model)


def generate_code(task: str, prior_diagnosis: str | None = None) -> str:
    prompt = f"Write Python code to accomplish this task:\n{task}\n"
    if prior_diagnosis:
        prompt += f"\nA previous attempt failed. Fix this issue:\n{prior_diagnosis}\n"
    prompt += "\nRespond with ONLY the Python code, no explanations, no markdown fences."

    response = _model.generate_content(prompt)
    return response.text.strip()

def validate_output(task: str, stdout: str, generated_files: list[str]) -> tuple[bool, str]:
    files_note = f"\nGenerated files: {', '.join(generated_files)}" if generated_files else ""
    prompt = (
        f"Task: {task}\n"
        f"Program output (stdout):\n{stdout}\n"
        f"{files_note}\n\n"
        "Does this output correctly and completely satisfy the task? "
        "Respond with exactly one line in this format:\n"
        "VALID: yes\n"
        "or\n"
        "VALID: no - <short reason>"
    )
    response = _model.generate_content(prompt)
    text = response.text.strip()

    if text.lower().startswith("valid: yes"):
        return True, ""
    reason = text.split("-", 1)[1].strip() if "-" in text else text
    return False, reason