"""Tests for the hook entry point: stdin payload in, JSON out, record appended.

Design §8's overriding rule is the one guarantee that must hold absolutely:
the tool is never the reason a session fails. Every failure path here must
still exit 0.
"""

import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from plimslop.hook import main


def transcript(*usages):
    fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for total in usages:
        fh.write(json.dumps({"message": {"usage": {"input_tokens": total}}}) + "\n")
    fh.close()
    return fh.name


def run(payload, corpus_path=None):
    """Run the hook over a payload; return (exit_code, parsed_stdout)."""
    out = io.StringIO()
    code = main(io.StringIO(json.dumps(payload)), out, corpus_path=corpus_path)
    text = out.getvalue()
    return code, (json.loads(text) if text.strip() else None)


class NormalOperation(unittest.TestCase):

    def test_reports_the_figure_and_exits_zero(self):
        path = transcript(60_000, 190_000)
        self.addCleanup(os.unlink, path)

        code, out = run({"transcript_path": path, "session_id": "s1", "cwd": "/tmp/p"})

        self.assertEqual(code, 0)
        self.assertIn("190,000", out["systemMessage"])


class NeverBreaksTheTurn(unittest.TestCase):

    def test_malformed_stdin_exits_zero(self):
        out = io.StringIO()
        self.assertEqual(main(io.StringIO("{not json"), out), 0)

    def test_empty_stdin_exits_zero(self):
        out = io.StringIO()
        self.assertEqual(main(io.StringIO(""), out), 0)

    def test_payload_without_a_transcript_path_exits_zero(self):
        code, _ = run({"session_id": "s1"})
        self.assertEqual(code, 0)

    def test_a_transcript_that_does_not_exist_exits_zero(self):
        code, _ = run({"transcript_path": "/nope/missing.jsonl", "session_id": "s1"})
        self.assertEqual(code, 0)

    def test_an_unwritable_corpus_still_reports_and_exits_zero(self):
        """A corpus we cannot write is a lost record, not a lost turn."""
        path = transcript(190_000)
        self.addCleanup(os.unlink, path)

        code, out = run({"transcript_path": path, "session_id": "s1"},
                        corpus_path="/nonexistent/dir/corpus.jsonl")

        self.assertEqual(code, 0)
        self.assertIn("190,000", out["systemMessage"])


class CorpusRecord(unittest.TestCase):

    def setUp(self):
        self.corpus = os.path.join(tempfile.mkdtemp(), "corpus.jsonl")

    def records(self):
        with open(self.corpus) as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_one_turn_record_is_appended_per_run(self):
        path = transcript(190_000)
        self.addCleanup(os.unlink, path)

        run({"transcript_path": path, "session_id": "s1", "cwd": "/tmp/p"},
            corpus_path=self.corpus)
        run({"transcript_path": path, "session_id": "s1", "cwd": "/tmp/p"},
            corpus_path=self.corpus)

        self.assertEqual(len(self.records()), 2)

    def test_the_record_carries_tokens_baseline_session_and_project(self):
        path = transcript(40_000, 190_000)
        self.addCleanup(os.unlink, path)

        run({"transcript_path": path, "session_id": "s1", "cwd": "/tmp/proj"},
            corpus_path=self.corpus)

        record = self.records()[0]
        self.assertEqual(record["type"], "turn")
        self.assertEqual(record["tokens"], 190_000)
        self.assertEqual(record["baseline"], 40_000)
        self.assertEqual(record["session"], "s1")
        self.assertEqual(record["project"], "/tmp/proj")

    def test_the_record_is_written_even_when_the_model_is_told_nothing(self):
        """Below every floor the model hears nothing, but the corpus is how the
        floors eventually get argued with, so the turn is still recorded."""
        path = transcript(12_000)
        self.addCleanup(os.unlink, path)

        run({"transcript_path": path, "session_id": "s1", "cwd": "/tmp/p"},
            corpus_path=self.corpus)

        self.assertEqual(self.records()[0]["tokens"], 12_000)


if __name__ == "__main__":
    unittest.main()
