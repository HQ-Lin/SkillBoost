from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ArtifactTests(unittest.TestCase):
    def test_paper_figures_are_embeddable_svg_assets(self) -> None:
        asset_dir = ROOT / "docs" / "assets"
        stems = {"skill-overfitting", "skillboost-framework", "best-of-n"}
        for stem in stems:
            svg = asset_dir / f"{stem}.svg"
            self.assertTrue(svg.is_file(), svg)
            self.assertIn(b"<svg", svg.read_bytes()[:1024], svg)
            self.assertFalse((asset_dir / f"{stem}.png").exists(), stem)
            self.assertFalse((asset_dir / f"{stem}.pdf").exists(), stem)

    def test_schemas_are_valid_json_and_have_version(self) -> None:
        for path in sorted((ROOT / "schemas").glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(schema["type"], "object", path)
            self.assertIn("schema_version", schema["properties"], path)

    def test_core_skill_names_match_directories(self) -> None:
        for folder in sorted((ROOT / "skills" / "evolving_skill").iterdir()):
            if not folder.is_dir():
                continue
            text = (folder / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(f"name: {folder.name}", text)

    def test_markdown_links_use_existing_local_targets(self) -> None:
        import re

        for markdown in ROOT.rglob("*.md"):
            text = markdown.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if target.startswith(("http://", "https://", "#")) or "<" in target:
                    continue
                target_path = target.split("#", 1)[0]
                if not target_path:
                    continue
                self.assertTrue((markdown.parent / target_path).exists(), f"{markdown}: {target}")

    def test_every_core_skill_reference_is_mounted(self) -> None:
        for folder in sorted((ROOT / "skills" / "evolving_skill").iterdir()):
            references = folder / "references"
            if not references.is_dir():
                continue
            skill = (folder / "SKILL.md").read_text(encoding="utf-8")
            for reference in sorted(references.glob("*.md")):
                target = f"references/{reference.name}"
                self.assertIn(f"]({target})", skill, f"unreachable reference: {reference}")

    def test_repair_brief_schema_exposes_all_paper_modules(self) -> None:
        schema = json.loads((ROOT / "schemas/repair-brief.schema.json").read_text(encoding="utf-8"))
        required = set(schema["required"])
        self.assertTrue(
            {
                "metadata",
                "baseline_performance",
                "failure_clusters",
                "repair_strategy",
                "action_mapping",
                "anti_regression_guardrails",
                "back_testing",
                "execution_plan",
            }.issubset(required)
        )

    def test_local_schema_references_resolve(self) -> None:
        def visit(value: object, source: Path) -> None:
            if isinstance(value, dict):
                reference = value.get("$ref")
                if isinstance(reference, str) and not reference.startswith(("#", "http://", "https://")):
                    target = reference.split("#", 1)[0]
                    self.assertTrue((source.parent / target).is_file(), f"{source}: {reference}")
                for child in value.values():
                    visit(child, source)
            elif isinstance(value, list):
                for child in value:
                    visit(child, source)

        for path in sorted((ROOT / "schemas").glob("*.schema.json")):
            visit(json.loads(path.read_text(encoding="utf-8")), path)

    def test_core_evolution_package_contains_no_benchmark_or_business_coupling(self) -> None:
        forbidden = {
            "livemath",
            "alfworld",
            "bfcl",
            "docvqa",
            "spreadsheetbench",
            "officeqa",
            "swe-bench",
            "content moderation",
            "audit point",
        }
        roots = [ROOT / "skills/evolving_skill", ROOT / "schemas", ROOT / "src/skillboost"]
        offenders: list[str] = []
        for base in roots:
            for path in base.rglob("*"):
                if not path.is_file() or path.suffix not in {".md", ".py", ".json"}:
                    continue
                lowered = path.read_text(encoding="utf-8", errors="ignore").casefold()
                if any(term in lowered for term in forbidden):
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
