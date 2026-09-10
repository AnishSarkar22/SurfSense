from worker.artifacts.builder import Builder
from worker.artifacts.builders.flashcards import flashcards
from worker.artifacts.builders.html_doc import html_doc
from worker.artifacts.builders.infographic import infographic
from worker.artifacts.builders.mindmap import mindmap
from worker.artifacts.builders.quiz import quiz
from worker.artifacts.builders.summary import summary

# format key -> builder for the structured formats: the model emits markdown or
# JSON and a small deterministic builder renders it. The other families route
# elsewhere — documents to worker/artifacts/office/ (model-written code) and audio/
# visual to worker/artifacts/media/. The API's dependency-free catalog
# (modules/artifacts/formats.py) lists every key; tests/unit/worker/
# test_artifact_builders.py asserts the three families partition it.
BUILDERS: dict[str, Builder] = {
    builder.key: builder
    for builder in (
        summary,
        html_doc,
        infographic,
        mindmap,
        flashcards,
        quiz,
    )
}

__all__ = ["BUILDERS"]
