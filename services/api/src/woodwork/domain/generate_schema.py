"""Run: python -m woodwork.domain.generate_schema packages/contracts/project.schema.json"""
import argparse
import json
from pathlib import Path

from .models import ProjectSpec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    schema = ProjectSpec.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "urn:woodworking-planner:project-spec:1.0.0"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Generated {args.output.as_posix()}")


if __name__ == "__main__":
    main()
