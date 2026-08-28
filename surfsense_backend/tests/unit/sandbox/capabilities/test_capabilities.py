from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.sandbox.capabilities.disclosure import build_public_capability_catalog
from app.sandbox.capabilities.loader import (
    CAPABILITY_INDEX_PATH,
    _parse_index,
    clear_capability_index_cache,
    load_capability_index,
)
from app.sandbox.capabilities.retrieval import retrieve_capability_ids
from app.sandbox.capabilities.schema import (
    CapabilityEnvelope,
    CapabilityIndex,
    CapabilityKind,
    CapabilityPostings,
    CapabilityTier,
)

pytestmark = pytest.mark.unit
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
VIDEO_RUNTIME_ROOT = REPOSITORY_ROOT / "docker" / "sandbox" / "video-runtime"


class _Sandbox:
    session_id = "capability-test"

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.reads = 0

    async def read_file(self, path: str) -> bytes:
        assert path == CAPABILITY_INDEX_PATH
        self.reads += 1
        return self.data


def _capability(
    capability_id: str,
    *,
    category: str,
    summary: str,
    tags: tuple[str, ...],
    use_for: tuple[str, ...] = (),
    avoid_for: tuple[str, ...] = (),
    dependencies: tuple[str, ...] = (),
    tier: CapabilityTier = CapabilityTier.VETTED,
) -> CapabilityEnvelope[dict[str, object]]:
    return CapabilityEnvelope[dict[str, object]](
        id=capability_id,
        kind=CapabilityKind.COMPONENT,
        domain="video",
        category=category,
        summary=summary,
        tags=tags,
        use_for=use_for,
        avoid_for=avoid_for,
        dependencies=dependencies,
        natural_frame_length=30,
        tier=tier,
        props_schema={"type": "object", "additionalProperties": False},
        declaration={
            "public_export": "".join(
                part.title() for part in capability_id.rsplit(".", maxsplit=1)[-1].split("-")
            )
        },
        search_text=" ".join((summary, *tags, *use_for, *avoid_for)).casefold(),
    )


def _index_for(
    capabilities: tuple[CapabilityEnvelope[dict[str, object]], ...],
) -> CapabilityIndex:
    fields = {
        "all": lambda capability: " ".join(
            (
                capability.id,
                capability.summary,
                capability.category,
                *capability.tags,
                *capability.use_for,
                *capability.avoid_for,
            )
        ),
        "tags": lambda capability: " ".join(capability.tags),
        "use_for": lambda capability: " ".join(capability.use_for),
        "summary": lambda capability: capability.summary,
        "vibe": lambda capability: " ".join(capability.vibe),
        "category": lambda capability: capability.category,
        "avoid_for": lambda capability: " ".join(capability.avoid_for),
    }
    postings: dict[str, dict[str, list[str]]] = {
        field_name: {} for field_name in fields
    }
    for capability in capabilities:
        for field_name, text in fields.items():
            for term in set(re.findall(r"[a-z0-9]+", text(capability).casefold())):
                postings[field_name].setdefault(term, []).append(capability.id)

    return CapabilityIndex(
        schema_version=1,
        build_id="build-1",
        capabilities=capabilities,
        postings=CapabilityPostings.model_validate_json(json.dumps(postings)),
    )


def _index() -> CapabilityIndex:
    return _index_for(
        (
            _capability(
                "video.component.metric-grid",
                category="data",
                summary="Animated metric grid for KPI comparisons",
                tags=("metrics", "grid", "data"),
                use_for=("quarterly KPI comparison",),
            ),
            _capability(
                "video.component.metric-cards",
                category="data",
                summary="Metric cards for dashboards",
                tags=("metrics", "cards", "data"),
                use_for=("dashboard metrics",),
            ),
            _capability(
                "video.component.confetti",
                category="celebration",
                summary="Celebratory confetti burst",
                tags=("celebration",),
                avoid_for=("serious financial reporting",),
            ),
            _capability(
                "video.component.core.text",
                category="core",
                summary="General text composition fallback",
                tags=("text", "fallback"),
                tier=CapabilityTier.CORE,
            ),
        )
    )


def test_generic_envelope_is_strict_and_forbids_unknown_fields() -> None:
    document = _capability(
        "video.component.core.text",
        category="core",
        summary="Text",
        tags=("text",),
    ).model_dump()
    document["natural_frame_length"] = "30"
    document["implementation_path"] = "/private/source.tsx"

    with pytest.raises(ValidationError):
        CapabilityEnvelope[dict[str, object]].model_validate(document)


def test_node_generated_index_satisfies_python_contract(tmp_path: Path) -> None:
    if (
        shutil.which("node") is None
        or not (VIDEO_RUNTIME_ROOT / "node_modules").is_dir()
    ):
        pytest.skip("Node and installed video-runtime dependencies are required")

    output = tmp_path / "capabilities"
    subprocess.run(
        ["node", "scripts/build-capabilities.mjs"],
        cwd=VIDEO_RUNTIME_ROOT,
        env={**os.environ, "SURFSENSE_CAPABILITY_OUTPUT": str(output)},
        check=True,
        capture_output=True,
        text=True,
    )
    index = _parse_index((output / "index.json").read_bytes())

    assert index.schema_version == 1
    assert index.build_id
    assert index.runtime_build_id
    assert tuple(capability.id for capability in index.capabilities) == tuple(
        sorted(capability.id for capability in index.capabilities)
    )
    known_ids = set(index.by_id())
    assert known_ids
    assert all(
        set(posting_ids) <= known_ids
        for field_name in type(index.postings).model_fields
        for posting_ids in getattr(index.postings, field_name).values()
    )
    assert all(
        capability.domain == "video" and capability.declaration["deterministic"] is True
        for capability in index.capabilities
    )
    animated_bar_chart = index.by_id()["video.component.animated-bar-chart"]
    assert animated_bar_chart.declaration["public_export"] == "AnimatedBarChart"
    catalog = build_public_capability_catalog(
        index, selected_ids=tuple(index.by_id())
    )
    disclosed = next(
        capability
        for capability in catalog["capabilities"]
        if capability["id"] == animated_bar_chart.id
    )
    assert disclosed["export_name"] == "AnimatedBarChart"
    assert disclosed["props_schema"]["required"] == ["data"]


async def test_loader_reads_live_and_caches_only_immutable_digest_identity() -> None:
    clear_capability_index_cache()
    sandbox = _Sandbox(_index().model_dump_json().encode())
    digest = f"sha256:{'a' * 64}"

    first = await load_capability_index(sandbox, image_digest=digest)
    second = await load_capability_index(sandbox, image_digest=digest)
    mutable_first = await load_capability_index(sandbox, image_digest="dev:latest")
    mutable_second = await load_capability_index(sandbox, image_digest="dev:latest")

    assert sandbox.reads == 4
    assert first is second
    assert mutable_first is not mutable_second
    with pytest.raises(TypeError, match="immutable"):
        first.capabilities[0].props_schema["type"] = "string"


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 2},
        {"build_id": "other"},
    ],
)
async def test_loader_rejects_version_or_expected_build_mismatch(change) -> None:
    document = _index().model_dump(mode="json")
    document.update(change)
    sandbox = _Sandbox(json.dumps(document).encode())

    with pytest.raises((ValueError, ValidationError), match=r"schema|build"):
        await load_capability_index(
            sandbox,
            image_digest=None,
            expected_build_id="build-1",
        )


def test_public_catalog_is_bounded_to_selected_ids_and_rejects_missing_exports() -> None:
    index = _index()
    selected = (
        "video.component.metric-grid",
        "video.component.core.text",
    )
    catalog = build_public_capability_catalog(index, selected_ids=selected)

    assert catalog["build_id"] == index.build_id
    assert [item["id"] for item in catalog["capabilities"]] == [
        *selected,
    ]
    broken = _capability(
        "video.component.broken",
        category="core",
        summary="Broken",
        tags=("broken",),
    ).model_copy(update={"declaration": {}})
    with pytest.raises(ValueError, match="lacks a public export"):
        build_public_capability_catalog(
            _index_for((broken,)), selected_ids=(broken.id,)
        )


def test_retrieval_is_deterministic_diverse_and_closes_dependencies() -> None:
    helper = _capability(
        "video.component.chart-label",
        category="typography",
        summary="Labels for data charts",
        tags=("labels", "data"),
    )
    metric = _capability(
        "video.component.metric-grid",
        category="data",
        summary="Animated metric grid for quarterly KPI comparison",
        tags=("metrics", "grid", "data"),
        use_for=("quarterly KPI comparison",),
        dependencies=(helper.id,),
    )
    confetti = _capability(
        "video.component.confetti",
        category="celebration",
        summary="Celebratory confetti burst",
        tags=("celebration",),
        avoid_for=("serious financial reporting",),
    )
    generated = tuple(
        _capability(
            f"video.component.option-{index:03d}",
            category=("data", "typography", "interface", "background")[index % 4],
            summary=f"Vetted visual option {index}",
            tags=("business", f"option-{index}"),
            use_for=("financial reporting",),
        )
        for index in range(147)
    )
    index = _index_for((helper, metric, confetti, *generated))

    first = retrieve_capability_ids(
        index, "Quarterly KPI comparison for serious financial reporting"
    )
    second = retrieve_capability_ids(
        index, "Quarterly KPI comparison for serious financial reporting"
    )

    assert first == second
    assert 8 <= len(first) <= 16
    assert metric.id in first
    assert helper.id in first
    assert confetti.id not in first
    categories = [index.by_id()[capability_id].category for capability_id in first]
    assert all(categories.count(category) <= 3 for category in set(categories))
