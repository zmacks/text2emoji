import enum
import os
import pprint
from string import Template

PROMPT_DIR = "prompts"


class Fragment(enum.Enum):
    SYSTEM_PROMPT: str = "fragments/system_prompt.txt"
    EXAMPLES: str = "fragments/examples.txt"
    AVANCED_EXAMPLES: str = "fragments/examples-advanced.txt"
    FORMAT: str = "fragments/format.txt"
    RULES: str = "fragments/rules.txt"
    DIRECTIVE: str = "fragments/directive.txt"
    OBJECTIVE: str = "fragments/objective.txt"
    INTRO: str = "fragments/intro.txt"

    def path(self):
        return os.path.join(get_script_directory(), PROMPT_DIR, self.value)

    def read(self):
        with open(self.path(), "r") as f:
            return f.read()


class Placeholder(enum.Enum):
    EXAMPLES: str = "EXAMPLES"
    FORMAT: str = "FORMAT"
    RULES: str = "RULES"
    OBJECTIVE: str = "OBJECTIVE"
    DIRECTIVE: str = "DIRECTIVE"
    ALIAS: str = "PP_ALIAS"
    DESCRIPTION: str = "PP_DESCRIPTION"
    INTRO: str = "INTRO"


class Interaction(enum.Enum):
    GIFT: str = NotImplemented
    TRAIN: str = NotImplemented
    OTHER: str = NotImplemented


def interact():
    pass


def get_script_directory():
    return os.path.dirname(os.path.abspath(__file__))


def write_to_file(
    content: str,
    filename: str,
    dir: str = PROMPT_DIR,
):
    output_path = os.path.join(get_script_directory(), dir, filename)

    with open(output_path, "w") as output:
        output.write(content)


def get_system_prompt_path():
    return os.path.join(
        get_script_directory(), PROMPT_DIR, Fragment.SYSTEM_PROMPT.value
    )


class PixlPal:
    def __init__(self, alias: str, traits: list):
        self._alias: str = alias
        self._traits: list = traits
        self._description = self._compose_description()
        self.objective = self._compose_objective()

    def __str__(self):
        return f"PixlPal(alias={self.alias}, traits={self.traits})"

    @property
    def alias(self):
        return self._alias

    @property
    def description(self):
        return self._description

    @property
    def traits(self):
        return self._traits

    @alias.setter
    def alias(self, alias):
        self._alias = alias
        self._compose_description()  # regenerate description

    @description.setter
    def description(self):
        return self._compose_description()

    @traits.setter
    def traits(self, traits):
        self._traits = traits
        self.description = self._compose_description()  # regenerate description

    def _compose_description(self) -> str:
        return f"{self.alias} is {convert_array_to_string_separated_by_commas(self.traits)}."

    def _compose_objective(self) -> str:
        template = Fragment.OBJECTIVE.read()
        template = templatize(template, self.alias, Placeholder.ALIAS.value)
        template = templatize(template, self.description, Placeholder.DESCRIPTION.value)
        return template


def convert_array_to_string_separated_by_commas(array: list) -> str:
    if len(array) == 0:
        raise ValueError("Cannot convert empty array to string")
    if len(array) == 1:
        return "".join(array)
    if len(array) == 2:
        return f"{array[0]} and {array[1]}"
    else:
        # Join all elements with commas, except the last one
        return ", ".join(array).strip(", ")


def compose_system_prompt(pxl: PixlPal):
    with open(get_system_prompt_path(), "r") as f:
        template = f.read()

    # Insert dynamic placeholder content into system prompt
    # TODO: Map fragments to placeholders and update templatize() to accept dicts for one-shot templating by config
    template = templatize(template, Fragment.INTRO.read(), Placeholder.INTRO.value)
    template = templatize(template, pxl.objective, Placeholder.OBJECTIVE.value)
    template = templatize(
        template, Fragment.DIRECTIVE.read(), Placeholder.DIRECTIVE.value
    )
    template = templatize(template, Fragment.RULES.read(), Placeholder.RULES.value)
    template = templatize(template, Fragment.FORMAT.read(), Placeholder.FORMAT.value)
    template = templatize(
        template, Fragment.EXAMPLES.read(), Placeholder.EXAMPLES.value
    )

    return template


def templatize(
    template_content: str, insert_content: str, placeholder: str, output_filename=None
) -> str:
    """
    Inserts the content of reference into origin, replacing a placeholder.
    If output_filename is provided, writes the result to a file with that name.
    Uses string.Template for substitution.
    """
    try:
        template_obj = Template(template_content)
        # Does not raise a KeyError if a placeholder is missing.
        # Instead, it leaves the placeholder unchanged in the resulting string
        templatized_content = template_obj.safe_substitute(
            {placeholder: insert_content}
        )

        if output_filename:
            write_to_file(templatized_content, output_filename)

        return templatized_content
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
