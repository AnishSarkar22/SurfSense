from dataclasses import dataclass


@dataclass(frozen=True)
class Format:
    """One artifact the app can produce."""

    key: str
    label: str
    description: str
    requires_role: str | None = "generation"


# The catalog. Kept dependency-free so the API validates and lists without
# importing builder libraries; the worker's BUILDERS registry must carry a
# builder for every non-visual key (asserted in the worker unit test).
FORMATS: tuple[Format, ...] = (
    Format("summary", "Summary", "Generate a summary based on your sources"),
    Format("docx", "Document", "Generate reports based on your sources"),
    Format("pptx", "Slides", "Generate a slide deck based on your sources"),
    Format("xlsx", "Spreadsheet", "Generate a spreadsheet based on your sources"),
    Format("html", "Web page", "Generate a web page based on your sources"),
    Format("pdf", "PDF", "Generate a PDF based on your sources"),
    Format("mindmap", "Mind map", "Generate a mind map based on your sources"),
    Format("flashcards", "Flashcards", "Generate flashcards based on your sources"),
    Format("quiz", "Quiz", "Generate a quiz based on your sources"),
    Format("podcast", "Podcast", "Generate a podcast based on your sources"),
    Format(
        "image",
        "Image",
        "Generate an image based on your sources",
        requires_role="image_generation",
    ),
    Format(
        "infographic", "Infographic", "Generate an infographic based on your sources"
    ),
)

FORMATS_BY_KEY: dict[str, Format] = {fmt.key: fmt for fmt in FORMATS}
