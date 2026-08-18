#!/usr/bin/env python3
"""
Convert LaTeX tables (with \\multirow / \\parbox / \\multicolumn section headers
and \\cite{...} references) into a structured CSV, optionally enriched with
metadata (title, author, year) pulled from a .bib file.

Usage:
    pip install bibtexparser --break-system-packages   # only dep beyond stdlib
    python latex_tables_to_csv.py tables.tex refs.bib output.csv

If you don't want bib enrichment, pass "" (empty string) as the bib path:
    python latex_tables_to_csv.py tables.tex "" output.csv

Output CSV columns:
    table_caption, section, grouping, item, citation_key, title, author, year
(one row per citation — an item cited 5 times produces 5 rows; this "long"
format is easiest to filter/pivot later.)
"""

import csv
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Low-level helpers
# ---------------------------------------------------------------------------

def strip_comments(text: str) -> str:
    """Remove LaTeX % comments (naively — doesn't handle escaped \\%)."""
    return re.sub(r"(?<!\\)%.*", "", text)


def find_matching_brace(text: str, open_idx: int) -> int:
    """Given the index of a '{', return the index of its matching '}'."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("Unbalanced braces in LaTeX source")


def extract_command_arg(text: str, command: str, start: int = 0):
    """
    Find the first occurrence of \\command{...} at or after `start`, using
    proper brace-matching (safe for nested braces like \\begin{tabular}{|p{4cm}|...}).
    Returns (arg_text, arg_start_idx, arg_end_idx, match_end_idx) or None.
    """
    m = re.search(r"\\" + re.escape(command) + r"\{", text[start:])
    if not m:
        return None
    open_idx = start + m.end() - 1
    close_idx = find_matching_brace(text, open_idx)
    return text[open_idx + 1:close_idx], open_idx + 1, close_idx, close_idx + 1


def clean_cell_text(cell: str) -> str:
    """
    Strip \\multirow{n}{*}{...}, \\parbox{Xcm}{...}, \\textbf{...} wrappers
    from a table cell, leaving just the human-readable text.
    """
    cell = cell.strip()

    # Unwrap \multirow{N}{*}{ ... } -> contents
    m = re.search(r"\\multirow\{[^}]*\}\{[^}]*\}\{", cell)
    if m:
        inner_start = m.end() - 1  # index of the opening brace we just matched
        inner_end = find_matching_brace(cell, inner_start)
        cell = cell[m.end():inner_end]

    # Unwrap \parbox{Xcm}{ ... } -> contents
    m = re.search(r"\\parbox\{[^}]*\}\{", cell)
    if m:
        inner_start = m.end() - 1
        inner_end = find_matching_brace(cell, inner_start)
        cell = cell[m.end():inner_end]

    # Unwrap \textbf{...} -> contents
    cell = re.sub(r"\\textbf\{([^}]*)\}", r"\1", cell)

    # Drop any remaining LaTeX commands with no useful text (e.g. \cline etc.)
    cell = re.sub(r"\\[a-zA-Z]+(\{[^}]*\})?", "", cell)

    # Restore escaped special characters to their literal form (must happen
    # after the generic \command stripping above, or "\&" would be eaten).
    cell = cell.replace(r"\&", "&").replace(r"\%", "%").replace(r"\_", "_")

    return cell.strip().strip(",").strip()


def extract_cite_keys(cell: str):
    """Return list of citation keys from all \\cite{...} in a cell."""
    return re.findall(r"\\cite\{([^}]*)\}", cell)


def split_top_level(row: str, sep: str = "&"):
    """
    Split a table row on unescaped '&' column separators.
    LaTeX uses '\\&' for a literal ampersand character (e.g. "Constraint \\&
    Compliance"), which must NOT be treated as a column boundary.
    """
    return re.split(r"(?<!\\)&", row)


# ---------------------------------------------------------------------------
# 2. Table parsing
# ---------------------------------------------------------------------------

def parse_tables(tex_text: str):
    """
    Yields dicts: {table_caption, section, grouping, item, citation_keys}
    """
    tex_text = strip_comments(tex_text)

    table_blocks = re.findall(
        r"\\begin\{table\}.*?\\end\{table\}", tex_text, flags=re.DOTALL
    )

    for block in table_blocks:
        cap_result = extract_command_arg(block, "caption")
        caption = cap_result[0].strip() if cap_result else "UNKNOWN TABLE"

        # Locate \begin{tabular}, then its colspec argument (brace-matched,
        # since colspecs like {|p{4cm}|p{5cm}|} contain nested braces).
        begin_match = re.search(r"\\begin\{tabular\}", block)
        end_match = re.search(r"\\end\{tabular\}", block)
        if not begin_match or not end_match:
            continue

        # Find the '{' immediately after \begin{tabular} and match it properly.
        open_idx = block.index("{", begin_match.end())
        close_idx = find_matching_brace(block, open_idx)
        body = block[close_idx + 1:end_match.start()]

        # Remove \hline and \cline{...} — they don't carry data
        body = re.sub(r"\\hline", "", body)
        body = re.sub(r"\\cline\{[^}]*\}", "", body)

        # Split into rows on LaTeX row-end "\\\\"
        raw_rows = re.split(r"\\\\", body)

        current_section = ""
        current_grouping = ""

        for raw_row in raw_rows:
            raw_row = raw_row.strip()
            if not raw_row:
                continue

            # Section header row, e.g. \multicolumn{3}{|c|}{\textbf{Manipulator Primitives}}
            mc_match = re.search(
                r"\\multicolumn\{[^}]*\}\{[^}]*\}\{(.*)\}", raw_row, flags=re.DOTALL
            )
            if mc_match and "&" not in raw_row.split(mc_match.group(0))[0]:
                # whole row is essentially just the multicolumn header
                current_section = clean_cell_text(mc_match.group(1))
                current_grouping = ""  # reset grouping under a new section
                continue

            cells = split_top_level(raw_row)
            if len(cells) < 3:
                continue  # malformed / stray row, skip

            grouping_raw, item_raw, refs_raw = cells[0], cells[1], "&".join(cells[2:])

            # Skip the column-header row itself, e.g.
            # \textbf{Grouping} & \textbf{Primitive} & \textbf{Reference}
            # (identified by: every cell is just a bare \textbf{...} wrapper).
            if all(re.fullmatch(r"\s*\\textbf\{[^}]*\}\s*", c) for c in (grouping_raw, item_raw, refs_raw)):
                continue

            grouping_clean = clean_cell_text(grouping_raw)
            if grouping_clean:
                current_grouping = grouping_clean

            item_clean = clean_cell_text(item_raw)
            citation_keys = extract_cite_keys(refs_raw)

            if not item_clean and not citation_keys:
                continue

            yield {
                "table_caption": caption,
                "section": current_section,
                "grouping": current_grouping,
                "item": item_clean,
                "citation_keys": citation_keys,
            }


# ---------------------------------------------------------------------------
# 3. Bib enrichment
# ---------------------------------------------------------------------------

def extract_raw_bib_entries(bib_text: str):
    """
    Return dict: citation_key -> the *exact* raw text of its @entry{...}
    block from the .bib file (whitespace collapsed to single spaces so it
    fits cleanly in one CSV cell), used for the full 'citation' column.
    """
    entries = {}
    for m in re.finditer(r"@\w+\s*\{", bib_text):
        open_idx = m.end() - 1
        try:
            close_idx = find_matching_brace(bib_text, open_idx)
        except ValueError:
            continue  # malformed entry; skip rather than crash the whole run
        full_entry = bib_text[m.start():close_idx + 1]

        key_match = re.match(r"@\w+\s*\{\s*([^,\s]+)\s*,", full_entry)
        if not key_match:
            continue
        key = key_match.group(1)

        normalized = re.sub(r"\s+", " ", full_entry).strip()
        entries[key] = normalized

    return entries


def load_bib(bib_path: str):
    """Return dict: citation_key -> {title, author, year, doi_or_url, raw_citation}."""
    if not bib_path:
        return {}

    import bibtexparser  # pip install bibtexparser --break-system-packages

    bib_text = Path(bib_path).read_text(encoding="utf-8")
    with open(bib_path, encoding="utf-8") as f:
        bib_database = bibtexparser.load(f)

    raw_entries = extract_raw_bib_entries(bib_text)

    lookup = {}
    for entry in bib_database.entries:
        key = entry.get("ID", "")
        doi = entry.get("doi", "").strip()
        url = entry.get("url", "").strip()
        lookup[key] = {
            "title": entry.get("title", "").strip("{}"),
            "author": entry.get("author", ""),
            "year": entry.get("year", ""),
            "doi_or_url": doi if doi else url,
            "raw_citation": raw_entries.get(key, ""),
        }
    return lookup


# ---------------------------------------------------------------------------
# 3b. Pivot to one row per paper (citation key)
# ---------------------------------------------------------------------------

ROBOT_PARTS = ["Manipulator", "Mobile Base", "Perception", "Mobile Manipulator"]
ITEM_TYPES = ["Primitive", "Skill", "Task"]
ITEM_TYPE_SUFFIXES = {"Primitives": "Primitive", "Skills": "Skill", "Tasks": "Task"}

# Separator used to pack multiple values into one CSV cell. Deliberately NOT
# a comma or semicolon: many locales (incl. much of Europe) make Excel treat
# ';' as the default CSV field separator when opening a file by double-click,
# which silently re-splits any cell containing ';' into extra columns and
# shifts the whole row. " | " can't be mistaken for a delimiter by anything.
MULTI_VALUE_SEP = " ; "


def parse_section_into_part_and_type(section: str):
    """
    'Mobile Base Skills' -> ('Mobile Base', 'Skill')
    'Manipulator Primitives' -> ('Manipulator', 'Primitive')
    Returns (None, None) if the section doesn't match this pattern
    (e.g. method-table sections like 'Control' or 'Trajectory learning').
    """
    section = section.strip()
    for suffix, item_type in ITEM_TYPE_SUFFIXES.items():
        if section.endswith(suffix):
            part = section[: -len(suffix)].strip()
            if part in ROBOT_PARTS:
                return part, item_type
    return None, None


def build_paper_header():
    header = ["paper_id", "citation_key", "citation", "title", "year", "doi_or_url"]
    for part in ROBOT_PARTS:
        for item_type in ITEM_TYPES:
            col_base = f"{part.lower()} {item_type.lower()}"
            header.append(f"{col_base} category")
            header.append(col_base)
    header += [
        "implementation type",
        "modeled level", "modeled category", "modeled method",
        "learned level", "learned category", "learned method",
    ]
    return header


def build_paper_records(rows):
    """
    rows: output of parse_tables() (one dict per table row, with a list of
    citation_keys). Returns (records, order) where records maps
    citation_key -> nested dict of collected values, and order is the list
    of citation_keys in first-appearance order (used for paper_id).
    """
    records = {}
    order = []

    def get_record(key):
        if key not in records:
            records[key] = {
                "items": {},     # (robot_part, item_type) -> {"categories": [...], "items": [...]}
                "modeled": {"level": [], "category": [], "method": []},
                "learned": {"level": [], "category": [], "method": []},
            }
            order.append(key)
        return records[key]

    for row in rows:
        part, item_type = parse_section_into_part_and_type(row["section"])
        caption_lower = row["table_caption"].lower()

        if part and item_type:
            for key in row["citation_keys"]:
                rec = get_record(key)
                slot = rec["items"].setdefault((part, item_type), {"categories": [], "items": []})
                if row["grouping"] and row["grouping"] not in slot["categories"]:
                    slot["categories"].append(row["grouping"])
                if row["item"] and row["item"] not in slot["items"]:
                    slot["items"].append(row["item"])
            continue

        if "modeled capability" in caption_lower:
            method_type = "modeled"
        elif "learned capability" in caption_lower:
            method_type = "learned"
        else:
            method_type = None  # row from a table we don't recognize; skip

        if method_type:
            for key in row["citation_keys"]:
                rec = get_record(key)
                bucket = rec[method_type]
                if row["section"] and row["section"] not in bucket["level"]:
                    bucket["level"].append(row["section"])
                if row["grouping"] and row["grouping"] not in bucket["category"]:
                    bucket["category"].append(row["grouping"])
                if row["item"] and row["item"] not in bucket["method"]:
                    bucket["method"].append(row["item"])

    return records, order


def build_paper_rows(rows, bib_lookup):
    records, order = build_paper_records(rows)

    for idx, key in enumerate(order, start=1):
        rec = records[key]
        meta = bib_lookup.get(key, {})

        out = {
            "paper_id": idx,
            "citation_key": key,
            "citation": meta.get("raw_citation", ""),
            "title": meta.get("title", ""),
            "year": meta.get("year", ""),
            "doi_or_url": meta.get("doi_or_url", ""),
        }

        for part in ROBOT_PARTS:
            for item_type in ITEM_TYPES:
                slot = rec["items"].get((part, item_type), {"categories": [], "items": []})
                col_base = f"{part.lower()} {item_type.lower()}"
                out[f"{col_base} category"] = MULTI_VALUE_SEP.join(slot["categories"])
                out[col_base] = MULTI_VALUE_SEP.join(slot["items"])

        is_modeled = bool(rec["modeled"]["method"])
        is_learned = bool(rec["learned"]["method"])
        if is_modeled and is_learned:
            impl = "both"
        elif is_modeled:
            impl = "modeled"
        elif is_learned:
            impl = "learned"
        else:
            impl = ""

        out["implementation type"] = impl
        out["modeled level"] = MULTI_VALUE_SEP.join(rec["modeled"]["level"])
        out["modeled category"] = MULTI_VALUE_SEP.join(rec["modeled"]["category"])
        out["modeled method"] = MULTI_VALUE_SEP.join(rec["modeled"]["method"])
        out["learned level"] = MULTI_VALUE_SEP.join(rec["learned"]["level"])
        out["learned category"] = MULTI_VALUE_SEP.join(rec["learned"]["category"])
        out["learned method"] = MULTI_VALUE_SEP.join(rec["learned"]["method"])

        yield out


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 4:
        print("Usage: python latex_tables_to_csv.py <tables.tex> <refs.bib|''> <output.csv>")
        sys.exit(1)

    tex_path, bib_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

    tex_text = Path(tex_path).read_text(encoding="utf-8")
    rows = list(parse_tables(tex_text))
    bib_lookup = load_bib(bib_path)

    # ---- Long format: one row per citation ----
    long_fields = ["table_caption", "section", "grouping", "item",
                    "citation_key", "title", "author", "year"]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=long_fields)
        writer.writeheader()
        for row in rows:
            keys = row["citation_keys"] or [""]
            for key in keys:
                meta = bib_lookup.get(key, {})
                writer.writerow({
                    "table_caption": row["table_caption"],
                    "section": row["section"],
                    "grouping": row["grouping"],
                    "item": row["item"],
                    "citation_key": key,
                    "title": meta.get("title", ""),
                    "author": meta.get("author", ""),
                    "year": meta.get("year", ""),
                })

    # ---- Wide format: one row per item, citations joined ----
    wide_path = str(Path(out_path).with_name(Path(out_path).stem + "_wide.csv"))
    wide_fields = ["table_caption", "section", "grouping", "item", "citation_keys", "n_citations"]

    with open(wide_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=wide_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "table_caption": row["table_caption"],
                "section": row["section"],
                "grouping": row["grouping"],
                "item": row["item"],
                "citation_keys": MULTI_VALUE_SEP.join(row["citation_keys"]),
                "n_citations": len(row["citation_keys"]),
            })

    print(f"Wrote {out_path} ({sum(len(r['citation_keys']) or 1 for r in rows)} rows, long format)")
    print(f"Wrote {wide_path} ({len(rows)} rows, wide format)")

    # ---- Per-paper format: one row per citation key, categories as columns ----
    paper_path = str(Path(out_path).with_name(Path(out_path).stem + "_by_paper.csv"))
    paper_header = build_paper_header()

    with open(paper_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=paper_header)
        writer.writeheader()
        n_papers = 0
        for paper_row in build_paper_rows(rows, bib_lookup):
            writer.writerow(paper_row)
            n_papers += 1

    print(f"Wrote {paper_path} ({n_papers} rows, one per paper)")


if __name__ == "__main__":
    main()
