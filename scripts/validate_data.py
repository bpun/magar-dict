"""Day 5: validate data/processed/words.json before it may be loaded.

Errors block the pipeline (exit code 1). Warnings never block.
Also draws the native-speaker review sample and, when given the reviewed
sample back, enforces the sign-off.

Usage:
  python -m scripts.validate_data
  python -m scripts.validate_data --permissions docs/permissions/tracker.csv
  python -m scripts.validate_data --signoff data/processed/sample_review_signed.csv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.import_words import DIALECT_MAP, POS_MAP

VALID_POS = set(POS_MAP.values())
VALID_DIALECTS = set(DIALECT_MAP.values())
DEVANAGARI = re.compile(r"[\u0900-\u097F]")
LATIN = re.compile(r"[A-Za-z]")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SAMPLE_ALL_UP_TO = 50  # governance 3.3: review everything up to 50 forms
SAMPLE_RATE_ABOVE = 0.20  # governance 3.3: random 20% above that


class Report:
    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def add(self, level: str, code: str, where: str, msg: str) -> None:
        self.items.append(
            {"level": level, "code": code, "where": where, "message": msg}
        )

    def err(self, code: str, where: str, msg: str) -> None:
        self.add("ERROR", code, where, msg)

    def warn(self, code: str, where: str, msg: str) -> None:
        self.add("WARNING", code, where, msg)

    def count(self, level: str) -> int:
        return sum(1 for i in self.items if i["level"] == level)


def load_sources(tracker: Path | None) -> dict[str, dict[str, str]] | None:
    if tracker is None:
        return None
    df = pd.read_csv(tracker, dtype=str, keep_default_na=False)
    return {r["record_id"]: r for r in df.to_dict("records")}


def check_words(
    words: list[dict[str, Any]], sources: dict[str, dict[str, str]] | None, rep: Report
) -> None:
    slugs: Counter[str] = Counter(w.get("slug", "") for w in words)
    schemes: dict[str, set[str]] = defaultdict(set)
    scripts_seen: dict[tuple[str, str], list[str]] = defaultdict(list)

    for w in words:
        slug = w.get("slug", "") or "(no slug)"
        at = f"word:{slug}"

        # Required fields and controlled vocabularies
        if not SLUG_RE.match(w.get("slug", "")):
            rep.err("E001", at, f"slug missing or malformed: '{w.get('slug', '')}'")
        if not str(w.get("gloss_en", "")).strip():
            rep.err("E001", at, "gloss_en is empty")
        if w.get("part_of_speech") not in VALID_POS:
            rep.err("E002", at, f"invalid part of speech '{w.get('part_of_speech')}'")
        if w.get("status") != "DRAFT":
            rep.err(
                "E008", at, f"imported status must be DRAFT, found '{w.get('status')}'"
            )
        if not str(w.get("gloss_ne", "")).strip():
            rep.warn("W002", at, "no Nepali gloss")
        if slugs[w.get("slug", "")] > 1:
            rep.err("E005", at, "duplicate slug")

        # Dialect rules (requirements FR-02..FR-04)
        tags = set(w.get("dialect_tags", []))
        forms = w.get("forms", [])
        form_dialects = [f.get("dialect") for f in forms]
        if not tags:
            rep.err("E003", at, "word has no dialect tag")
        bad = tags - VALID_DIALECTS
        if bad:
            rep.err("E003", at, f"unknown dialect tag(s): {sorted(bad)}")
        for missing in sorted(tags - set(form_dialects)):
            rep.err("E004", at, f"dialect tag '{missing}' has no form")
        for extra in sorted(set(form_dialects) - tags):
            rep.err("E004", at, f"form for '{extra}' but word is not tagged '{extra}'")
        for d, n in Counter(form_dialects).items():
            if n > 1:
                rep.err("E006", at, f"{n} forms for dialect '{d}' (only one allowed)")
        if len(tags) == 1:
            rep.warn("W006", at, f"only in {next(iter(tags))}; check coverage")

        # Per-form checks
        for f in forms:
            fa = f"{at}/{f.get('dialect')}"
            script, rom = str(f.get("form_script", "")), str(
                f.get("form_romanized", "")
            )
            if not script.strip() or not rom.strip():
                rep.err("E007", fa, "form_script and form_romanized are both required")
                continue
            if (
                unicodedata.normalize("NFC", script) != script
                or unicodedata.normalize("NFC", rom) != rom
            ):
                rep.err("E007", fa, "text is not NFC-normalized")
            if f.get("status") != "DRAFT":
                rep.err(
                    "E008", fa, f"form status must be DRAFT, found '{f.get('status')}'"
                )
            if f.get("withheld"):
                rep.err("E010", fa, "withheld form must never be imported")
            if not DEVANAGARI.search(script):
                rep.warn("W001", fa, f"form_script has no Devanagari: '{script}'")
            elif LATIN.search(script):
                rep.warn("W005", fa, f"Latin letters mixed into Devanagari: '{script}'")
            if f.get("form_romanized_norm") != _norm(rom):
                rep.warn(
                    "W003", fa, "form_romanized_norm does not match romanized form"
                )
            schemes[str(f.get("dialect"))].add(str(f.get("romanization_scheme")))
            scripts_seen[(str(f.get("dialect")), script)].append(slug)

            sid = f.get("source_id", "")
            if sources is not None:
                rec = sources.get(sid)
                if rec is None:
                    rep.err("E009", fa, f"source '{sid}' not in permissions tracker")
                elif rec.get("status", "").lower() != "signed":
                    rep.err(
                        "E009",
                        fa,
                        f"source '{sid}' is '{rec.get('status')}', not signed",
                    )
                elif "license" in rec and not rec["license"].strip():
                    rep.err("E009", fa, f"source '{sid}' has no license recorded")
            elif not sid:
                rep.err("E009", fa, "no source_id")

    for d, s in schemes.items():  # governance: one scheme per variety
        if len(s) > 1:
            rep.err("E011", f"dialect:{d}", f"mixed romanization schemes: {sorted(s)}")
    for (d, script), owners in scripts_seen.items():
        if len(set(owners)) > 1:
            rep.warn(
                "W007",
                f"dialect:{d}",
                f"'{script}' used by several words: {sorted(set(owners))}",
            )


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in folded if not unicodedata.combining(ch)).lower()


def coverage(words: list[dict[str, Any]]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for w in words:
        c.update(f["dialect"] for f in w.get("forms", []))
    return dict(sorted(c.items()))


def draw_sample(
    words: list[dict[str, Any]], seed: int, flagged: set[str]
) -> pd.DataFrame:
    """Per dialect: all forms up to 50, else a random 20% plus every flagged form."""
    rng = random.Random(seed)  # noqa: S311
    by_dialect: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for w in words:
        for f in w.get("forms", []):
            by_dialect[f["dialect"]].append((w["slug"], f))
    rows: list[dict[str, str]] = []
    for d, items in sorted(by_dialect.items()):
        items.sort(key=lambda t: t[0])
        if len(items) <= SAMPLE_ALL_UP_TO:
            chosen = items
        else:
            k = math.ceil(len(items) * SAMPLE_RATE_ABOVE)
            picked = rng.sample(items, k)
            chosen = list(
                {
                    id(i): i for i in picked + [i for i in items if i[0] in flagged]
                }.values()
            )
        for slug, f in chosen:
            rows.append(
                {
                    "dialect": d,
                    "slug": slug,
                    "form_script": f["form_script"],
                    "form_romanized": f["form_romanized"],
                    "decision": "",
                    "reviewer": "",
                    "reason": "",
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "dialect",
            "slug",
            "form_script",
            "form_romanized",
            "decision",
            "reviewer",
            "reason",
        ],
    )


def check_signoff(sample: pd.DataFrame, signed_path: Path, rep: Report) -> None:
    done = pd.read_csv(
        signed_path, dtype=str, keep_default_na=False, encoding="utf-8-sig"
    )
    key = ["dialect", "slug"]
    need = {tuple(r) for r in sample[key].values.tolist()}
    got = {
        tuple(r[:2]): r[2].strip().lower()
        for r in done[[*key, "decision"]].values.tolist()
    }
    for dialect, slug in sorted(need):
        dec = got.get((dialect, slug), "")
        if dec not in {"approved", "rejected"}:
            rep.err(
                "E012",
                f"{dialect}/{slug}",
                "sample entry has no approved/rejected decision",
            )
        elif dec == "rejected":
            rep.err(
                "E013",
                f"{dialect}/{slug}",
                f"rejected in sample: whole {dialect} batch returns for full review",
            )
    if "reviewer" in done.columns and not done["reviewer"].str.strip().all():
        rep.err("E012", "signoff", "every decision needs a reviewer name")


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    p.add_argument("--words", type=Path, default=Path("data/processed/words.json"))
    p.add_argument("--out", type=Path, default=Path("data/processed"))
    p.add_argument("--permissions", type=Path, default=None)
    p.add_argument(
        "--signoff",
        type=Path,
        default=None,
        help="reviewed sample CSV returned by the verifiers",
    )
    a = p.parse_args()

    raw = a.words.read_bytes()
    words: list[dict[str, Any]] = json.loads(raw)
    rep = Report()
    check_words(words, load_sources(a.permissions), rep)

    flagged = {
        i["where"].split("/")[0].removeprefix("word:")
        for i in rep.items
        if i["level"] == "WARNING" and i["where"].startswith("word:")
    }
    seed = int(hashlib.sha256(raw).hexdigest()[:8], 16)  # same file -> same sample
    sample = draw_sample(words, seed, flagged)
    a.out.mkdir(parents=True, exist_ok=True)
    sample.to_csv(a.out / "sample_review.csv", index=False, encoding="utf-8-sig")
    if a.signoff:
        check_signoff(sample, a.signoff, rep)

    pd.DataFrame(rep.items, columns=["level", "code", "where", "message"]).to_csv(
        a.out / "validation_report.csv", index=False, encoding="utf-8-sig"
    )
    print(
        f"Validated {len(words)} words | "
        f"coverage (forms per dialect): {coverage(words)}"
    )
    for it in rep.items:
        print(f"  {it['level']:<7} {it['code']} {it['where']}: {it['message']}")
        print(
            f"\nErrors: {rep.count('ERROR')} | Warnings: {rep.count('WARNING')} | "
            f"Sample to review: {len(sample)} forms -> {a.out / 'sample_review.csv'}"
        )
    if not a.signoff:
        print("Sign-off: PENDING (pass --signoff once verifiers return the sample)")
    ok = rep.count("ERROR") == 0
    print("RESULT:", "PASS" if ok else "FAIL (pipeline blocked)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
