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


# import time
# from typing import Tuple

# from opentelemetry import trace
# from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
# from opentelemetry.instrumentation.logging import LoggingInstrumentor
# from opentelemetry.sdk.resources import Resource
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import BatchSpanProcessor
# from prometheus_client import REGISTRY, Counter, Gauge, Histogram
# from prometheus_client.openmetrics.exposition import (
#     CONTENT_TYPE_LATEST,
#     generate_latest,
# )
# from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
# from starlette.requests import Request
# from starlette.responses import Response
# from starlette.routing import Match
# from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
# from starlette.types import ASGIApp

# INFO = Gauge("fastapi_app_info", "FastAPI application information.", ["app_name"])
# REQUESTS = Counter(
#     "fastapi_requests_total",
#     "Total count of requests by method and path.",
#     ["method", "path", "app_name"],
# )
# RESPONSES = Counter(
#     "fastapi_responses_total",
#     "Total count of responses by method, path and status codes.",
#     ["method", "path", "status_code", "app_name"],
# )
# REQUESTS_PROCESSING_TIME = Histogram(
#     "fastapi_requests_duration_seconds",
#     "Histogram of requests processing time by path (in seconds)",
#     ["method", "path", "app_name"],
# )
# EXCEPTIONS = Counter(
#     "fastapi_exceptions_total",
#     "Total count of exceptions raised by path and exception type",
#     ["method", "path", "exception_type", "app_name"],
# )
# REQUESTS_IN_PROGRESS = Gauge(
#     "fastapi_requests_in_progress",
#     "Gauge of requests by method and path currently being processed",
#     ["method", "path", "app_name"],
# )


# class PrometheusMiddleware(BaseHTTPMiddleware):
#     def __init__(self, app: ASGIApp, app_name: str = "fastapi-app") -> None:
#         super().__init__(app)
#         self.app_name = app_name
#         INFO.labels(app_name=self.app_name).inc()

#     async def dispatch(
#         self, request: Request, call_next: RequestResponseEndpoint
#     ) -> Response:
#         method = request.method
#         path, is_handled_path = self.get_path(request)

#         if not is_handled_path:
#             return await call_next(request)

#         REQUESTS_IN_PROGRESS.labels(
#             method=method, path=path, app_name=self.app_name
#         ).inc()
#         REQUESTS.labels(method=method, path=path, app_name=self.app_name).inc()
#         before_time = time.perf_counter()
#         try:
#             response = await call_next(request)
#         except BaseException as e:
#             status_code = HTTP_500_INTERNAL_SERVER_ERROR
#             EXCEPTIONS.labels(
#                 method=method,
#                 path=path,
#                 exception_type=type(e).__name__,
#                 app_name=self.app_name,
#             ).inc()
#             raise e from None
#         else:
#             status_code = response.status_code
#             after_time = time.perf_counter()
#             # retrieve trace id for exemplar
#             span = trace.get_current_span()
#             trace_id = trace.format_trace_id(span.get_span_context().trace_id)

#             REQUESTS_PROCESSING_TIME.labels(
#                 method=method, path=path, app_name=self.app_name
#             ).observe(after_time - before_time, exemplar={"TraceID": trace_id})
#         finally:
#             RESPONSES.labels(
#                 method=method,
#                 path=path,
#                 status_code=status_code,
#                 app_name=self.app_name,
#             ).inc()
#             REQUESTS_IN_PROGRESS.labels(
#                 method=method, path=path, app_name=self.app_name
#             ).dec()

#         return response

#     @staticmethod
#     def get_path(request: Request) -> Tuple[str, bool]:
#         for route in request.app.routes:
#             match, child_scope = route.matches(request.scope)
#             if match == Match.FULL:
#                 return route.path, True

#         return request.url.path, False


# def metrics(request: Request) -> Response:
#     return Response(
#         generate_latest(REGISTRY), headers={"Content-Type": CONTENT_TYPE_LATEST}
#     )


# def setting_otlp(
#     app: ASGIApp, app_name: str, endpoint: str, log_correlation: bool = True
# ) -> None:
#     # Setting OpenTelemetry
#     # set the service name to show in traces
#     resource = Resource.create(
#         attributes={"service.name": app_name, "compose_service": app_name}
#     )

#     # set the tracer provider
#     tracer = TracerProvider(resource=resource)
#     trace.set_tracer_provider(tracer)

#     tracer.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))

#     if log_correlation:
#         LoggingInstrumentor().instrument(set_logging_format=True)

#     FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer)
