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