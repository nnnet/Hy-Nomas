"""HTTP acceptance steps for an already running aggregate compose stack."""

import json
import hashlib
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pytest_bdd import parsers, then, when


BUILT_IN_GALLERY = {
    "curated-20261022-snow-palace-walk": "curated-20261022-snow-palace-walk.mp4",
    "curated-20261022-snow-palace-ascent": "curated-20261022-snow-palace-ascent.mp4",
    "curated-20261022-coastal-waterfall": "curated-20261022-coastal-waterfall.mp4",
    "curated-20261022-voxel-adventure": "curated-20261022-voxel-adventure.mp4",
    "curated-20261022-kitchen-stories": "curated-20261022-kitchen-stories.mp4",
    "curated-20261022-street-coffee": "curated-20261022-street-coffee.mp4",
}

UPSTREAM_CASES = {
    "snow-palace-walk",
    "snow-palace-ascent",
    "coastal-waterfall",
    "voxel-adventure",
    "kitchen-stories",
    "street-coffee",
}
EXACT_UPSTREAM_CASES = {
    "snow-palace-ascent",
    "voxel-adventure",
    "kitchen-stories",
}
PARTIAL_UPSTREAM_CASES = UPSTREAM_CASES - EXACT_UPSTREAM_CASES
UPSTREAM_BUNDLE_URL = (
    "https://hy-nomas.hy.tencent.com/assets/index-DdHuI7-l.js"
)
UPSTREAM_BUNDLE_SHA256 = (
    "e135e2bb3948740d32c6f9de8a6efc095491dae508a14d0b9c9ec8343f42bd2a"
)


@when(parsers.parse('я запрашиваю HTTP путь "{path}"'))
def _request_http_path(context, path):
    request = Request(f"http://127.0.0.1:7878{path}", headers={"Accept": "*/*"})
    with urlopen(request, timeout=30) as response:
        context["http_status"] = response.status
        context["http_content_type"] = response.headers.get("Content-Type", "")
        context["http_body"] = response.read()


@when(parsers.parse('я запрашиваю backend HTTP путь "{path}"'))
def _request_backend_http_path(context, path):
    request = Request(f"http://127.0.0.1:7879{path}", headers={"Accept": "*/*"})
    with urlopen(request, timeout=30) as response:
        context["http_status"] = response.status
        context["http_content_type"] = response.headers.get("Content-Type", "")
        context["http_body"] = response.read()


@then(parsers.parse("HTTP статус равен {status:d}"))
def _status_equals(context, status):
    assert context["http_status"] == status


@then(parsers.parse('HTTP Content-Type содержит "{value}"'))
def _content_type_contains(context, value):
    assert value in context["http_content_type"]


@then(parsers.parse('JSON поле "{field}" равно "{value}"'))
def _json_field_equals(context, field, value):
    payload = json.loads(context["http_body"])
    assert payload[field] == value


@then(parsers.parse('JSON поле "{field}" истинно'))
def _json_field_true(context, field):
    payload = json.loads(context["http_body"])
    assert payload[field] is True


@then(parsers.parse('JSON массив "{field}" не пуст'))
def _json_array_not_empty(context, field):
    payload = json.loads(context["http_body"])
    assert isinstance(payload[field], list)
    assert payload[field]


@then("Gallery не содержит видео с одинаковым содержимым")
def _gallery_content_is_unique(context):
    payload = json.loads(context["http_body"])
    digests = []
    for item in payload["items"]:
        if not str(item.get("id") or "").startswith("saved-"):
            continue
        request = Request(
            f"http://127.0.0.1:7878/{item['video']}",
            headers={"Accept": "video/mp4"},
        )
        with urlopen(request, timeout=30) as response:
            assert "video/mp4" in response.headers.get("Content-Type", "")
            digests.append(hashlib.sha256(response.read()).hexdigest())
    assert len(digests) == len(set(digests)), digests


@then("встроенные карточки Gallery не подменены сохранёнными генерациями")
def _built_in_gallery_is_not_substituted(context):
    payload = json.loads(context["http_body"])
    items_by_id = {str(item.get("id") or ""): item for item in payload["items"]}
    saved_digests = set()
    for item in payload["items"]:
        if not str(item.get("id") or "").startswith("saved-"):
            continue
        request = Request(
            f"http://127.0.0.1:7878/{item['video']}",
            headers={"Accept": "video/mp4"},
        )
        with urlopen(request, timeout=30) as response:
            saved_digests.add(hashlib.sha256(response.read()).hexdigest())

    for item_id in BUILT_IN_GALLERY:
        assert item_id in items_by_id, item_id
        video = str(items_by_id[item_id].get("video") or "")
        request = Request(
            f"http://127.0.0.1:7878/{video}",
            headers={"Accept": "video/mp4"},
        )
        if video.startswith("gallery/unavailable-upstream/"):
            try:
                urlopen(request, timeout=30)
            except HTTPError as error:
                assert error.code == 404
            else:
                raise AssertionError(f"unavailable Gallery video was served: {video}")
            continue
        with urlopen(request, timeout=30) as response:
            digest = hashlib.sha256(response.read()).hexdigest()
        assert digest not in saved_digests, video


@then(parsers.parse('контейнеры Compose имеют префикс "{prefix}"'))
def _compose_container_prefix(repo, prefix):
    import subprocess

    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "{{.Name}}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    names = [name for name in result.stdout.splitlines() if name]
    assert len(names) == 3
    assert all(name.startswith(prefix) for name in names), names


def _source_pack_root(repo: Path) -> Path:
    return repo / "reproductions" / "upstream-curated"


@then("source pack содержит шесть отдельных upstream-примеров")
def _source_pack_has_six_cases(repo):
    root = _source_pack_root(repo)
    case_dirs = {path.name for path in root.iterdir() if path.is_dir()}
    assert case_dirs == UPSTREAM_CASES
    for case in UPSTREAM_CASES:
        entry = json.loads((root / case / "upstream-gallery-entry.json").read_text())
        assert entry["id"] == f"curated-20261022-{case}"


@then("provenance source pack закрепляет официальный bundle и видео")
def _source_pack_provenance_is_pinned(repo):
    root = _source_pack_root(repo)
    for case in UPSTREAM_CASES:
        provenance = json.loads((root / case / "provenance.json").read_text())
        assert provenance["gallery_bundle"]["url"] == UPSTREAM_BUNDLE_URL
        assert provenance["gallery_bundle"]["sha256"] == UPSTREAM_BUNDLE_SHA256
        assert provenance["video"]["url"].startswith(
            "https://hy-nomas.hy.tencent.com/gallery/curated-20261022-"
        )
        assert len(provenance["video"]["sha256"]) == 64


@then("полные upstream-примеры готовы для одинакового CLI и Web replay")
def _exact_source_pack_cases_are_replayable(repo):
    import subprocess

    subprocess.run(
        ["bash", "-n", "sh/run_hynomas_16.sh"],
        cwd=repo,
        check=True,
        timeout=30,
    )
    subprocess.run(
        ["python3", "-m", "py_compile", "sh/run_hynomas_inference.py"],
        cwd=repo,
        check=True,
        timeout=30,
    )
    root = _source_pack_root(repo)
    for case in EXACT_UPSTREAM_CASES:
        case_dir = root / case
        availability = json.loads((case_dir / "availability.json").read_text())
        scenario = json.loads((case_dir / "scenario.json").read_text())
        web_replay = json.loads((case_dir / "web-replay.json").read_text())
        assert availability["exact_replay"] is True
        assert web_replay["scenario"] == scenario
        assert scenario[0]["test_id"] == f"upstream-{case}"
        assert scenario[0]["segments"]
        published = json.loads(
            (case_dir / "upstream-gallery-entry.json").read_text()
        )["prompt_timeline"]
        adapted = scenario[0]["segments"]
        assert adapted[0]["visual_description_long"] == published[0]["prompt"]
        assert [segment["description_change"] for segment in adapted[1:]] == [
            turn["prompt"] for turn in published[1:]
        ]


@then("неполные upstream-примеры не подменяют скрытые prompts и camera trajectory")
def _partial_source_pack_cases_are_not_fabricated(repo):
    root = _source_pack_root(repo)
    for case in PARTIAL_UPSTREAM_CASES:
        case_dir = root / case
        availability = json.loads((case_dir / "availability.json").read_text())
        assert availability["exact_replay"] is False
        assert not (case_dir / "scenario.json").exists()
        assert availability["missing"]
        camera = json.loads((case_dir / "camera-control.json").read_text())
        if "camera_trajectory" in availability["missing"]:
            assert camera["trajectory"] is None
            assert camera["status"] == "not-published"
