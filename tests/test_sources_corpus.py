"""
Local corpus adapter tests.

The corpus is the source that must stay honest when everything else fails: no
network, no credential, deterministic ordering across repeated calls.
"""

from __future__ import annotations

import json

from rta.sources.base import CODE_NOT_FOUND, DiskCache, SourcePolicy
from rta.sources.corpus import CorpusAdapter


def build_corpus(tmp_path, files: dict, roots=None):
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    adapter = CorpusAdapter(
        roots=roots if roots is not None else [tmp_path / "docs"],
        policy=SourcePolicy(max_items=10),
        cache=DiskCache(tmp_path / "cache"),
        base_dir=tmp_path,
    )
    adapter.rebuild()
    return adapter


DOCS = {
    "docs/README-01-checker.md": "# Checker\n\nRule SDC-005 fires when input "
                                 "delays are missing.\nOther text here.\n",
    "docs/README-02-generator.md": "# Generator\n\nGenerates clocks and IO "
                                   "delays.\n",
    "docs/migration/notes.md": "Migration note: SDC-006 output delay.\n",
}


class TestSearch:
    def test_finds_matching_rule_document(self, tmp_path):
        adapter = build_corpus(tmp_path, DOCS)
        result = adapter.search("SDC-005")
        assert result["ok"] is True
        assert result["data"]["matches"]
        assert result["data"]["matches"][0]["path"] == "docs/README-01-checker.md"

    def test_ranking_is_deterministic_across_calls(self, tmp_path):
        adapter = build_corpus(tmp_path, DOCS)
        first = json.dumps(adapter.search("delay")["data"]["matches"])
        second = json.dumps(adapter.search("delay")["data"]["matches"])
        assert first == second

    def test_limit_is_respected(self, tmp_path):
        adapter = build_corpus(tmp_path, DOCS)
        assert len(adapter.search("delay", limit=1)["data"]["matches"]) == 1

    def test_path_filter_narrows_results(self, tmp_path):
        adapter = build_corpus(tmp_path, DOCS)
        result = adapter.search("delay", path_filter="migration")
        paths = {m["path"] for m in result["data"]["matches"]}
        assert paths == {"docs/migration/notes.md"}

    def test_empty_query_is_ok_with_note_not_error(self, tmp_path):
        adapter = build_corpus(tmp_path, DOCS)
        result = adapter.search("")
        assert result["ok"] is True
        assert result["data"]["matches"] == []
        assert "no searchable terms" in result["note"]

    def test_no_match_is_ok_with_hint(self, tmp_path):
        adapter = build_corpus(tmp_path, DOCS)
        result = adapter.search("zzzznothing")
        assert result["ok"] is True
        assert result["data"]["matches"] == []
        assert "SDC-" in (result["note"] or "")

    def test_snippet_is_truncated_and_hashed(self, tmp_path):
        long_line = "clocks " + ("x" * 400)
        adapter = build_corpus(tmp_path, {"docs/long.md": long_line})
        match = adapter.search("clocks")["data"]["matches"][0]
        assert len(match["snippet"]) <= 240
        assert len(match["content_hash"]) == 16

    def test_returns_line_numbers(self, tmp_path):
        adapter = build_corpus(tmp_path, DOCS)
        match = adapter.search("SDC-005")["data"]["matches"][0]
        assert match["line"] >= 1


class TestIndexing:
    def test_binary_files_are_skipped(self, tmp_path):
        (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
        (tmp_path / "docs" / "blob.md").write_bytes(b"\x00\x01\x02binary")
        adapter = build_corpus(tmp_path, {"docs/real.md": "real knowledge\n"})
        assert adapter.health()["files_indexed"] == 1

    def test_non_text_extensions_are_skipped(self, tmp_path):
        adapter = build_corpus(tmp_path, {"docs/data.bin": "not indexed\n",
                                          "docs/notes.md": "indexed\n"})
        assert [e.rel for e in adapter.entries()] == ["docs/notes.md"]

    def test_index_signature_is_stable_and_changes_with_content(self, tmp_path):
        adapter = build_corpus(tmp_path, DOCS)
        first = adapter.health()["index_signature"]
        adapter.rebuild()
        assert adapter.health()["index_signature"] == first
        (tmp_path / "docs" / "new.md").write_text("new", encoding="utf-8")
        adapter.rebuild()
        assert adapter.health()["index_signature"] != first

    def test_missing_roots_are_reported(self, tmp_path):
        adapter = CorpusAdapter(roots=[tmp_path / "nope"],
                                cache=DiskCache(tmp_path / "cache"),
                                base_dir=tmp_path)
        health = adapter.health()
        assert health["files_indexed"] == 0
        assert health["missing_roots"]

    def test_no_roots_returns_not_found_envelope(self, tmp_path):
        adapter = CorpusAdapter(roots=[tmp_path / "nope"],
                                cache=DiskCache(tmp_path / "cache"),
                                base_dir=tmp_path)
        adapter.rebuild()
        result = adapter.search("anything")
        assert result["ok"] is False
        assert result["error"]["code"] == CODE_NOT_FOUND

    def test_health_declares_no_network_or_credential(self, tmp_path):
        health = build_corpus(tmp_path, DOCS).health()
        assert health["requires_network"] is False
        assert health["requires_credential"] is False
        assert health["kind"] == "local-corpus"
