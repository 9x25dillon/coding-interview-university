import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kgirl_learn.curriculum import find_subtopic, find_topic, parse_readme, slugify

FIXTURE = """# Study plan

## Table of Contents

- [Data Structures](#data-structures)

## Data Structures

- ### Arrays
    - [ ] Implement a vector (mutable array with automatic resizing):
        - [ ] size() - number of items
    - [ ] [Arrays CS50 (video)](https://example.com/arrays)
    - [ ] About arrays:
        - [Dynamic arrays](https://example.com/dynamic)

- ### Linked Lists
    - [ ] [Linked Lists CS50](https://example.com/ll)

## Sorting

- [ ] Notes:
    - [ ] Stability in sorting algorithms
- [ ] [Mergesort (video)](https://example.com/merge)

## Update Your Resume

- [ ] Not a study topic
"""

CIU_README = Path(__file__).resolve().parents[2] / "README.md"


class CurriculumTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "README.md"
        self.path.write_text(FIXTURE, encoding="utf-8")
        self.cur = parse_readme(self.path)

    def test_only_study_topics(self):
        names = [t["name"] for t in self.cur["topics"]]
        self.assertEqual(names, ["Data Structures", "Sorting"])
        self.assertTrue(all(t["kind"] == "core" for t in self.cur["topics"]))

    def test_subtopics(self):
        ds = find_topic(self.cur, "Data Structures")
        self.assertEqual([s["name"] for s in ds["subtopics"]], ["Arrays", "Linked Lists"])

    def test_implicit_subtopic_for_flat_topic(self):
        sorting = find_topic(self.cur, "Sorting")
        self.assertEqual(len(sorting["subtopics"]), 1)
        self.assertEqual(sorting["subtopics"][0]["name"], "Sorting")

    def test_resources_and_tasks(self):
        arrays = find_subtopic(self.cur, "Data Structures", "Arrays")
        urls = [r["url"] for r in arrays["resources"]]
        self.assertEqual(urls, ["https://example.com/arrays", "https://example.com/dynamic"])
        self.assertIn("size() - number of items", arrays["tasks"])
        self.assertNotIn("Implement a vector (mutable array with automatic resizing):", arrays["tasks"])

    def test_lookup_by_slug_and_name(self):
        self.assertIsNotNone(find_topic(self.cur, "data-structures"))
        self.assertIsNotNone(find_subtopic(self.cur, "Data Structures", "linked-lists"))
        self.assertIsNone(find_topic(self.cur, "nope"))

    def test_slugify(self):
        self.assertEqual(slugify("Heap / Priority Queue / Binary Heap"), "heap-priority-queue-binary-heap")

    @unittest.skipUnless(CIU_README.exists(), "real CIU README not present")
    def test_real_readme(self):
        cur = parse_readme(CIU_README)
        self.assertEqual(len(cur["topics"]), 9)
        ds = find_topic(cur, "Data Structures")
        self.assertEqual(len(ds["subtopics"]), 5)
        self.assertIsNotNone(find_subtopic(cur, "More Knowledge", "Binary search"))
        self.assertIsNotNone(find_subtopic(cur, "Even More Knowledge", "Dynamic Programming"))
        self.assertTrue(all(s["resources"] for t in cur["topics"] for s in t["subtopics"]))


if __name__ == "__main__":
    unittest.main()