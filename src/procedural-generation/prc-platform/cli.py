"""CLI for procedural platform generation."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generator import generate_level, validate_level
from json_export import to_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--length", type=int, default=12800)
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium")
    parser.add_argument("--stage", type=int, default=1)
    parser.add_argument("--id", default="gen_level")
    parser.add_argument("--out", default="generated_level.json")
    args = parser.parse_args()

    level = generate_level(seed=args.seed, length=args.length, difficulty=args.difficulty, stage=args.stage, level_id=args.id)
    validate_level(level)
    to_json(level, args.out)
    print("generated", args.out, "platforms:", len(level["platforms"]), "checkpoints:", len(level["checkpoints"]))


if __name__ == "__main__":
    main()