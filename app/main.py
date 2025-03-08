import json
import os
import pprint

from dotenv import load_dotenv
from google import genai
from google.genai import types

from utils import PixlPal, compose_system_prompt, write_to_file

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def pixlpal_response(
    pxl: PixlPal, text: str = "Tell me about your favorite food."
) -> str:
    """Generates a response from a PixlPal.
    Args:
        pxl (PixlPal): The PixlPal to generate a response from.
        text (str): The text to generate a response to.
    Returns:
        str: The generated response.
    """

    def prepare_text(text: str) -> str:
        return f"<user_input>{text}</user_input>"

    system_instruction = compose_system_prompt(pxl)
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=1,
        top_p=0.95,
        top_k=20,
        candidate_count=1,
        seed=5,
        max_output_tokens=100,
        stop_sequences=["STOP!"],
        presence_penalty=0.0,
        frequency_penalty=0.0,
        # response_mime_type="application/json",
    )

    client = genai.Client(api_key=GEMINI_API_KEY)

    parts = [types.Part.from_text(text=prepare_text(text))]

    contents = types.Content(
        parts=parts,
        role="user",
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash-001",
        config=config,
        contents=contents,
    )

    answer = response.candidates[0].content.parts[0].text
    write_to_file(system_instruction, "system_prompt_created.txt")
    return answer


def main():
    golden_retriever_pal = PixlPal(
        "Abbie", ["playful", "curious", "honest", "sincere", "geniune"]
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
