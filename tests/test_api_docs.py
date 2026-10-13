import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("generate_api_docs", ROOT / "scripts" / "generate_api_docs.py")
docs_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs_script)


def test_api_reference_mentions_every_endpoint():
    """If this fails, run:  python scripts/generate_api_docs.py"""
    text = (ROOT / "docs" / "API.md").read_text(encoding="utf-8")
    missing = [
        f"{e['method']} {e['path']}"
        for e in docs_script.collect_endpoints()
        if f"| {e['method']} | `{e['path']}` |" not in text
    ]
    assert not missing, f"docs/API.md is out of date, missing: {missing[:5]}. Run: python scripts/generate_api_docs.py"


def test_readme_has_the_endpoint_list_and_all_fifteen_sections():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert docs_script.README_START in text and docs_script.README_END in text
    for number in range(1, 16):
        assert f"\n## {number}. " in text, f"README section {number} is missing"
    assert "run `python scripts/generate_api_docs.py` to fill this in" not in text, "the endpoint list was never generated"


def test_generator_output_is_complete_and_deterministic():
    first = docs_script.build_tables()
    assert first == docs_script.build_tables()
    assert "/api/v1/admin/dashboard" in first and "/api/v1/worker/complaints" in first
    assert "Public" in first and "ADMIN" in first
