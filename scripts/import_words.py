"""Day 4: clean raw word lists into data/processed/words.json.

Reads every CSV/XLSX in data/raw/, normalizes text, maps POS and dialect
labels, drops duplicates, groups rows into words (one form per dialect),
generates slugs, and writes everything as DRAFT. Nothing here is public.

Outputs (data/processed/):
  words.json           cleaned words, each with its dialect forms
  transform_log.csv    every change, drop, or rejection, one row each
  review_list.csv      rows a human must resolve (unknown labels, conflicts)

Usage:
  python -m scripts.import_words
  python -m scripts.import_words --raw data/raw --out data/processed \
      --permissions docs/permissions/tracker.csv
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

# --------------------------------------------------------------------------
# Controlled vocabularies. The language lead edits these, nothing else.
# --------------------------------------------------------------------------
POS_MAP: dict[str, str] = {
    "n": "noun",
    "noun": "noun",
    "nn": "noun",
    "v": "verb",
    "vb": "verb",
    "verb": "verb",
    "adj": "adjective",
    "a": "adjective",
    "adjective": "adjective",
    "adv": "adverb",
    "adverb": "adverb",
    "pron": "pronoun",
    "pronoun": "pronoun",
    "num": "numeral",
    "numeral": "numeral",
    "postp": "postposition",
    "postposition": "postposition",
    "part": "particle",
    "particle": "particle",
    "interj": "interjection",
    "intj": "interjection",
    "interjection": "interjection",
    "other": "other",
}

# Raw dialect label -> tag slug. Add spellings only when a verifier confirms
# them. Unknown labels are never guessed; they go to review_list.csv.
DIALECT_MAP: dict[str, str] = {
    "dhut": "dhut",
    "kham": "kham",
    "kaike": "kaike",
}

REQUIRED_COLS = ["dialect", "magar_script", "romanized", "gloss_en", "pos", "source_id"]
OPTIONAL_COLS = ["gloss_ne", "withheld", "region_note", "romanization_scheme"]
DEVANAGARI = re.compile(r"[\u0900-\u097F]")
# Invisible characters to strip. ZWJ/ZWNJ (200C/200D) are KEPT: they are
# meaningful in Devanagari conjuncts.
STRIP_CHARS = dict.fromkeys(map(ord, "\ufeff\u200b\u2060\u00ad"), None)
TRUTHY = {"1", "true", "yes", "y", "t"}


@dataclass
class Log:
    rows: list[dict[str, Any]] = field(default_factory=list)
    review: list[dict[str, Any]] = field(default_factory=list)

    def note(self, file: str, row: int, action: str, detail: str) -> None:
        self.rows.append({"file": file, "row": row, "action": action, "detail": detail})

    def flag(self, file: str, row: int, reason: str, values: dict[str, Any]) -> None:
        self.review.append({"file": file, "row": row, "reason": reason, **values})
        self.note(file, row, "review", reason)


def clean_text(value: Any) -> str:
    """NFC-normalize, strip invisible junk, collapse whitespace."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = unicodedata.normalize("NFC", str(value))
    text = text.translate(STRIP_CHARS).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()


def slugify(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")
    return slug or "word"


def romanized_norm(text: str) -> str:
    """Search-only form: lowercase, diacritics stripped."""
    folded = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in folded if not unicodedata.combining(ch)).lower()


def load_raw(raw_dir: Path, log: Log) -> list[tuple[str, int, dict[str, Any]]]:
    out: list[tuple[str, int, dict[str, Any]]] = []
    files = sorted([*raw_dir.glob("*.csv"), *raw_dir.glob("*.xlsx")])
    if not files:
        raise SystemExit(f"No .csv or .xlsx files found in {raw_dir}")
    for path in files:
        df = (
            pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
            if path.suffix == ".csv"
            else pd.read_excel(path, dtype=str).fillna("")
        )
        df.columns = [clean_text(c).lower() for c in df.columns]
        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            log.note(path.name, 0, "file_skipped", f"missing columns: {missing}")
            continue
        for i, rec in enumerate(df.to_dict("records"), start=2):  # row 1 = header
            out.append((path.name, i, rec))
    return out


def load_signed_sources(tracker: Path | None) -> set[str] | None:
    if tracker is None or not tracker.exists():
        return None
    df = pd.read_csv(tracker, dtype=str, keep_default_na=False)
    signed = df[df["status"].str.lower() == "signed"]
    return set(signed["record_id"])


def run(raw_dir: Path, out_dir: Path, tracker: Path | None) -> None:
    log = Log()
    signed = load_signed_sources(tracker)
    rows = load_raw(raw_dir, log)
    kept: dict[tuple[str, str, str], dict[str, Any]] = {}  # (gloss, pos, dialect)

    for fname, rown, rec in rows:
        r = {k: clean_text(rec.get(k, "")) for k in [*REQUIRED_COLS, *OPTIONAL_COLS]}

        # 1. Withheld rows never enter the pipeline (governance section 7).
        if r["withheld"].lower() in TRUTHY:
            log.note(fname, rown, "dropped_withheld", r["gloss_en"])
            continue

        # 2. Source must have a signed permission record (if tracker supplied).
        if signed is not None and r["source_id"] not in signed:
            log.note(
                fname, rown, "dropped_unsigned_source", r["source_id"] or "(blank)"
            )
            continue

        # 3. Dialect label -> slug. Never guess.
        dialect = DIALECT_MAP.get(r["dialect"].lower())
        if dialect is None:
            log.flag(fname, rown, f"unknown dialect label '{r['dialect']}'", r)
            continue

        # 4. POS label -> controlled vocabulary.
        pos = POS_MAP.get(r["pos"].lower())
        if pos is None:
            log.flag(fname, rown, f"unknown part of speech '{r['pos']}'", r)
            continue

        # 5. Required fields after cleaning.
        blank = [c for c in ("magar_script", "romanized", "gloss_en") if not r[c]]
        if blank:
            log.flag(fname, rown, f"empty required field(s): {blank}", r)
            continue
        if not DEVANAGARI.search(r["magar_script"]):
            log.note(fname, rown, "warning_not_devanagari", r["magar_script"])

        gloss_key = r["gloss_en"].lower()
        key = (gloss_key, pos, dialect)
        form = {
            "dialect": dialect,
            "form_script": r["magar_script"],
            "form_romanized": r["romanized"],
            "form_romanized_norm": romanized_norm(r["romanized"]),
            "romanization_scheme": r["romanization_scheme"] or f"{dialect}-v1",
            "region_note": r["region_note"] or None,
            "status": "DRAFT",
            "source_id": r["source_id"],
            "origin": f"{fname}:{rown}",
        }
        if key in kept:
            prev = kept[key]["form"]
            if prev["form_script"] == form["form_script"]:
                log.note(
                    fname, rown, "dropped_duplicate", f"{gloss_key}/{pos}/{dialect}"
                )
            else:
                # Same meaning and dialect, different spelling: a human decides.
                log.flag(
                    fname,
                    rown,
                    f"conflicting form for {gloss_key}/{pos}/{dialect} "
                    f"(kept {prev['form_script']} from {prev['origin']})",
                    r,
                )
            continue
        kept[key] = {"gloss_en": r["gloss_en"], "gloss_ne": r["gloss_ne"], "form": form}

    # 6. Group forms into words by (gloss, pos); build slugs deterministically.
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for (gloss_key, pos, _d), item in sorted(kept.items()):
        w = grouped.setdefault(
            (gloss_key, pos),
            {
                "gloss_en": item["gloss_en"],
                "gloss_ne": item["gloss_ne"],
                "part_of_speech": pos,
                "status": "DRAFT",
                "forms": [],
            },
        )
        if not w["gloss_ne"] and item["gloss_ne"]:
            w["gloss_ne"] = item["gloss_ne"]
        w["forms"].append(item["form"])

    words: list[dict[str, Any]] = []
    used: dict[str, int] = {}
    for w in sorted(
        grouped.values(), key=lambda x: (x["gloss_en"].lower(), x["part_of_speech"])
    ):
        base = slugify(w["forms"][0]["form_romanized"])
        used[base] = used.get(base, 0) + 1
        w["slug"] = base if used[base] == 1 else f"{base}-{used[base]}"
        w["dialect_tags"] = sorted({f["dialect"] for f in w["forms"]})
        w["source_ids"] = sorted({f["source_id"] for f in w["forms"]})
        words.append(w)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "words.json").write_text(
        json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pd.DataFrame(log.rows, columns=["file", "row", "action", "detail"]).to_csv(
        out_dir / "transform_log.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(log.review).to_csv(
        out_dir / "review_list.csv", index=False, encoding="utf-8-sig"
    )

    counts = pd.Series([r["action"] for r in log.rows]).value_counts().to_dict()
    print(
        f"rows read: {len(rows)} | words: {len(words)} | "
        f"forms: {sum(len(w['forms']) for w in words)} | review: {len(log.review)}"
    )
    print(f"log actions: {counts}")


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    p.add_argument("--raw", type=Path, default=Path("data/raw"))
    p.add_argument("--out", type=Path, default=Path("data/processed"))
    p.add_argument(
        "--permissions",
        type=Path,
        default=None,
        help="tracker.csv; rows from unsigned sources are dropped",
    )
    a = p.parse_args()
    run(a.raw, a.out, a.permissions)


if __name__ == "__main__":
    main()
