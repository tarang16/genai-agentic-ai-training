import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class FakeStructuredLLM:
    """Stands in for ChatOpenAI in tests: returns a fixed structured result, records the prompt."""

    def __init__(self, result: dict):
        self.result = result
        self.calls = []

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        return self.schema(**self.result)
