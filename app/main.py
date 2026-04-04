import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from utils import PixlPal, compose_system_prompt, write_to_file

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


class GeminiTextGenerator:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """Initializes the GeminiTextGenerator with API key and model."""
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_text(
        self,
        system_instruction: str,
        user_input: str,
        temperature: float = 1.0,
        top_p: float = 0.95,
        top_k: int = 20,
        max_output_tokens: int = 100,
        stop_sequences: list = None,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        seed: int = None,
    ) -> str:
        """Generates text using the Gemini API."""
        if stop_sequences is None:
            stop_sequences = []

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            candidate_count=1,
            seed=seed,
            max_output_tokens=max_output_tokens,
            stop_sequences=stop_sequences,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
        )

        parts = [types.Part.from_text(text=f"<user_input>{user_input}</user_input>")]

        contents = types.Content(
            parts=parts,
            role="user",
        )

        response = self.client.models.generate_content(
            model=self.model,
            config=config,
            contents=contents,
        )

        return response.candidates[0].content.parts[0].text


def pixlpal_response(
    pxl: PixlPal, text: str = "Tell me about your favorite food."
) -> str:
    """Generates a response from a PixlPal."""
    system_instruction = compose_system_prompt(pxl)
    generator = GeminiTextGenerator(api_key=GEMINI_API_KEY)
    response = generator.generate_text(
        system_instruction=system_instruction,
        user_input=text,
        temperature=1,
        top_p=0.95,
        top_k=20,
        max_output_tokens=2000,
        stop_sequences=["STOP!"],
        presence_penalty=0.0,
        frequency_penalty=0.0,
        seed=5,
    )
    write_to_file(system_instruction, "system_prompt_created.txt")
    return response


def main():
    golden_retriever_pal = PixlPal(
        "Abbie", ["playful", "curious", "honest", "sincere", "genuine"]
    )
    bratty_pal = PixlPal(
        "Mal", ["witty", "sassy", "funny", "ironic", "maliciously compliant"]
    )
    # TODO: This "text" will eventually be a user input
    bratty_answer = pixlpal_response(bratty_pal, "Tell me about your favorite food.")
    golden_retriever_answer = pixlpal_response(
        golden_retriever_pal, "Tell me about your favorite food."
    )
    write_to_file(bratty_answer, "bratty_answer.txt")
    write_to_file(golden_retriever_answer, "golden_retriever_answer.txt")


if __name__ == "__main__":
    main()
