from pathlib import Path
import pandas as pd
import rispy

main_folder = "combined"
volume = "mobman"
# volume = "full"
ROOT = Path("../data/"+main_folder+"/new_datasets")
# ROOT = Path("../data/"+main_folder+"/")

###############################################################################
# Reading functions
###############################################################################

def read_ris(filename):
    with open(filename, encoding="utf-8-sig", errors="ignore") as f:
        return rispy.load(f)


def read_csv(filename):
    df = pd.read_csv(filename)
    return df.to_dict("records")


def read_enw(filename):
    """
    Simple EndNote (.enw) parser.
    """
    records = []
    current = {}

    with open(filename, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip()

            if line.startswith("%0"):
                if current:
                    records.append(current)
                current = {}

            elif line.startswith("%"):
                tag = line[1]
                value = line[3:].strip()
                current.setdefault(tag, []).append(value)

        if current:
            records.append(current)

    return records


###############################################################################
# Helpers
###############################################################################

def first_existing(record, names, default=""):
    """
    Returns the first non-empty value among possible keys.
    """
    for name in names:
        if name in record:

            value = record[name]

            if isinstance(value, list):
                value = "; ".join(str(v) for v in value)

            if pd.notna(value) and str(value).strip():
                return str(value).strip()

    return default


###############################################################################
# Normalization
###############################################################################

def normalize_record(record):
    """
    Convert records from any database into a common schema.
    """

    title = first_existing(record, [
        "title",
        "Title",
        "primary_title",
        "Document Title",
        "Article Title",
        "Item Title",
        "TI",
        "T",
    ])

    doi = first_existing(record, [
        "doi",
        "DOI",
        "DI",
        "%R",
    ])

    authors = first_existing(record, [
        "authors",
        "Authors",
        "AU",
        "A1",
        "author",
    ])

    year = first_existing(record, [
        "year",
        "Year",
        "PY",
        "publication_year",
    ])

    journal = first_existing(record, [
        "journal_name",
        "Journal",
        "Source title",
        "Publication Title",
        "secondary_title",
        "T2",
        "JF",
    ])

    abstract = first_existing(record, [
        "abstract",
        "Abstract",
        "AB",
    ])

    keywords = first_existing(record, [
        "keywords",
        "Keywords",
        "DE",
        "ID",
    ])

    return {
        "title": title,
        "authors": authors,
        "year": year,
        "journal": journal,
        "doi": doi.lower().strip(),
        "abstract": abstract,
        "keywords": keywords,
    }


###############################################################################
# Read every file
###############################################################################

normalized = []

for full_folder in ROOT.glob("*/"+volume):

    for file in full_folder.iterdir():

        suffix = file.suffix.lower()

        try:

            if suffix == ".ris":
                records = read_ris(file)

            elif suffix == ".csv":
                records = read_csv(file)

            elif suffix == ".enw":
                records = read_enw(file)

            else:
                continue

            normalized.extend(normalize_record(r) for r in records)

            print(f"Loaded {len(records):4d} records from {file.name}")

        except Exception as e:
            print(f"Could not read {file}: {e}")


###############################################################################
# Build dataframe
###############################################################################

df = pd.DataFrame(normalized)

###############################################################################
# Normalize strings
###############################################################################

df["title_norm"] = (
    df["title"]
    .fillna("")
    .str.lower()
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

df["doi"] = (
    df["doi"]
    .fillna("")
    .str.lower()
    .str.strip()
)

###############################################################################
# Deduplicate
###############################################################################

with_doi = (
    df[df["doi"] != ""]
    .drop_duplicates(subset="doi", keep="first")
)

without_doi = (
    df[df["doi"] == ""]
    .drop_duplicates(subset="title_norm", keep="first")
)

combined = pd.concat([with_doi, without_doi], ignore_index=True)

combined = combined.drop(columns=["title_norm"])

###############################################################################
# Save
###############################################################################

# combined.to_csv("combined_results.csv", index=False)
combined.to_csv(main_folder+"_"+volume+"_combined_results.csv", index=False)

print()
print(f"Total unique records: {len(combined)}")