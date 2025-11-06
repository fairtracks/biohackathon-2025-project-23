#!/usr/bin/env python3
import sys
import os
import re
import csv
from collections import Counter, OrderedDict
from typing import Dict, List, Tuple
import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# ----------------------- Utilities -----------------------

def check_file_exists(file_path: str) -> None:
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if not os.access(file_path, os.R_OK):
        raise PermissionError(f"File not readable: {file_path}")

def ensure_output_dir(output_pdf: str) -> None:
    out_dir = os.path.dirname(os.path.abspath(output_pdf)) or "."
    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    if not os.access(out_dir, os.W_OK):
        raise PermissionError(f"Output directory not writable: {out_dir}")

def safe_readlines(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as f:
            return f.readlines()
    except UnicodeDecodeError:
        # Fall back to latin-1 with replacement to be forgiving
        with open(path, "r", encoding="latin-1", errors="replace") as f:
            return f.readlines()

# ----------------------- GFF -----------------------

def count_unique_column3(gff_path: str) -> Counter:
    """
    Count unique values in column 3 of a GFF/GTF-like file.
    """
    check_file_exists(gff_path)
    counts: Counter = Counter()
    with open(gff_path, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 9:
                raise ValueError(
                    f"Invalid GFF format at line {line_num}: "
                    f"expected 9 columns, got {len(parts)}"
                )
            counts[parts[2]] += 1
    return counts

def plot_bar_to_pdf(
    pdf: PdfPages,
    title: str,
    labels: List[str],
    values: List[float],
    xlabel: str,
    ylabel: str,
    rotation: int = 45,
) -> None:
    plt.figure(figsize=(10, 6))
    plt.bar(labels, values)
    plt.xticks(rotation=rotation, ha="right")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    pdf.savefig()
    plt.close()

def add_kv_table_page(
    pdf: PdfPages,
    title: str,
    rows: List[Tuple[str, str]],
    note: str = "",
) -> None:
    """
    Make a simple text table page for key/value results.
    """
    plt.figure(figsize=(10, 6))
    plt.axis("off")
    y = 0.95
    plt.text(0.5, y, title, ha="center", va="top", fontsize=16, fontweight="bold", transform=plt.gca().transAxes)
    y -= 0.08
    for k, v in rows:
        plt.text(0.1, y, f"{k}", ha="left", va="top", fontsize=12, transform=plt.gca().transAxes)
        plt.text(0.6, y, f"{v}", ha="left", va="top", fontsize=12, transform=plt.gca().transAxes)
        y -= 0.06
        if y < 0.1:
            break
    if note:
        plt.text(0.5, 0.08, note, ha="center", va="bottom", fontsize=10, style="italic", transform=plt.gca().transAxes)
    pdf.savefig()
    plt.close()

# ----------------------- BUSCO parsing -----------------------

BUSCO_KEYS_ORDER = ["Complete", "Single-copy", "Duplicated", "Fragmented", "Missing", "Total BUSCO groups (n)"]

def parse_busco_stats(busco_path: str) -> Dict[str, float]:
    """
    Parse common BUSCO short_summary*.txt formats, e.g.:
    C:95.3%[S:93.1%,D:2.2%],F:2.6%,M:2.1%,n:255
    Returns percentages for C/S/D/F/M and 'n'.
    """
    check_file_exists(busco_path)
    lines = [l.strip() for l in safe_readlines(busco_path) if l.strip() and not l.startswith("#")]

    # Try canonical compact line
    pattern = re.compile(
        r"C:(?P<C>[\d.]+)%\s*\[\s*S:(?P<S>[\d.]+)%\s*,\s*D:(?P<D>[\d.]+)%\s*\]\s*,\s*"
        r"F:(?P<F>[\d.]+)%\s*,\s*M:(?P<M>[\d.]+)%\s*,\s*n:(?P<n>\d+)"
    )
    for line in lines:
        m = pattern.search(line)
        if m:
            C = float(m.group("C"))
            S = float(m.group("S"))
            D = float(m.group("D"))
            F = float(m.group("F"))
            M = float(m.group("M"))
            n = int(m.group("n"))
            return {
                "Complete": C,
                "Single-copy": S,
                "Duplicated": D,
                "Fragmented": F,
                "Missing": M,
                "Total BUSCO groups (n)": float(n),
            }

    # Try verbose key:value formats (some summaries list one per line)
    # e.g. "Complete BUSCOs (C):	95.3%", "Complete and single-copy BUSCOs (S): 93.1%", etc.
    kv = {}
    for line in lines:
        # normalize
        line_clean = re.sub(r"\s+", " ", line)
        # capture percentage
        pct = re.search(r"([\d.]+)\s*%", line_clean)
        num = re.search(r"\b(n|Number of BUSCOs|Total BUSCO groups)\D+(\d+)", line_clean, flags=re.I)
        if "Complete and single-copy" in line_clean or "(S)" in line_clean:
            if pct: kv["Single-copy"] = float(pct.group(1))
        elif "Duplicated" in line_clean or "(D)" in line_clean:
            if pct: kv["Duplicated"] = float(pct.group(1))
        elif line_clean.lower().startswith("c:") or "Complete BUSCOs" in line_clean or "(C)" in line_clean:
            if pct: kv["Complete"] = float(pct.group(1))
        elif "Fragmented" in line_clean or "(F)" in line_clean:
            if pct: kv["Fragmented"] = float(pct.group(1))
        elif "Missing" in line_clean or "(M)" in line_clean:
            if pct: kv["Missing"] = float(pct.group(1))
        if num:
            kv["Total BUSCO groups (n)"] = float(num.group(2))

    if kv:
        # sanity: fill missing keys with 0.0
        for k in BUSCO_KEYS_ORDER:
            kv.setdefault(k, 0.0)
        return kv

    raise ValueError(
        "Could not parse BUSCO stats. Expected a 'short_summary*.txt' style line like "
        "'C:..%[S:..%,D:..%],F:..%,M:..%,n:..' or a verbose key:value summary."
    )

def plot_busco_summary(pdf: PdfPages, busco: Dict[str, float]) -> None:
    labels = ["Complete", "Single-copy", "Duplicated", "Fragmented", "Missing"]
    values = [busco.get(k, 0.0) for k in labels]
    plot_bar_to_pdf(
        pdf=pdf,
        title="BUSCO Summary",
        labels=labels,
        values=values,
        xlabel="Category",
        ylabel="Percent (%)",
        rotation=0,
    )
    # Add a small table page with n
    add_kv_table_page(
        pdf,
        "BUSCO Details",
        [(k, f"{int(busco[k])}" if k.endswith("(n)") else f"{busco[k]:.2f}%")
         for k in BUSCO_KEYS_ORDER if k in busco],
        note="Values shown are percentages except for (n).",
    )

# ----------------------- OMArk parsing -----------------------

OMARK_COMMON_HEADERS = {
    "complete", "duplicated", "fragmented", "missing",
    "single-copy", "single_copy", "total", "n", "busco_like_complete"
}

def _to_number(s: str) -> float:
    s = s.strip()
    s = s.rstrip("%")
    try:
        return float(s)
    except ValueError:
        return float("nan")

def parse_omark_stats(omark_path: str) -> Dict[str, float]:
    """
    OMArk formats vary; we try in order:
    1) key: value or key\tvalue (percentages or counts)
    2) CSV/TSV with headers containing common category names
    3) fallback: word frequency for a few known tokens
    """
    check_file_exists(omark_path)
    lines = [l.strip() for l in safe_readlines(omark_path) if l.strip() and not l.startswith("#")]

    # 1) key:value pairs per line
    kv: Dict[str, float] = {}
    for line in lines:
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip().lower()
            v = v.strip()
            if any(h in k for h in OMARK_COMMON_HEADERS):
                kv[k] = _to_number(v)
        elif "\t" in line:
            k, v = line.split("\t", 1)
            k = k.strip().lower()
            v = v.strip()
            if any(h in k for h in OMARK_COMMON_HEADERS):
                kv[k] = _to_number(v)

    if kv:
        return kv

    # 2) CSV/TSV
    # Try to detect delimiter
    sniff_delim = "," if any("," in l for l in lines[:5]) else "\t"
    try:
        reader = csv.DictReader(lines, delimiter=sniff_delim)
        headers = [h.lower() for h in (reader.fieldnames or [])]
        hits = [h for h in headers if any(k in h for k in OMARK_COMMON_HEADERS)]
        if hits:
            accum: Dict[str, float] = {}
            for row in reader:
                for h in headers:
                    if any(k in h for k in OMARK_COMMON_HEADERS):
                        accum[h] = _to_number(row.get(h, "nan"))
            if accum:
                return accum
    except Exception:
        pass

    # 3) Fallback: simple counts of words (very forgiving)
    tokens = " ".join(lines).lower()
    crude = OrderedDict()
    for k in ["complete", "single-copy", "duplicated", "fragmented", "missing"]:
        crude[k] = float(tokens.count(k))
    if any(v > 0 for v in crude.values()):
        return crude

    raise ValueError(
        "Could not parse OMArk stats. Expected key:value lines or a CSV/TSV with category columns."
    )

def plot_omark_summary(pdf: PdfPages, omark: Dict[str, float]) -> None:
    # Decide whether these look like percents (0..100) or counts
    vals = [v for v in omark.values() if v == v]  # drop NaN
    looks_like_pct = vals and all(0.0 <= v <= 100.0 for v in vals)
    ylabel = "Percent (%)" if looks_like_pct else "Count"
    # Choose a display order if keys resemble BUSCO
    preferred = ["complete", "single-copy", "duplicated", "fragmented", "missing"]
    keys = [k for k in preferred if k in omark] + [k for k in omark.keys() if k not in preferred]
    labels = [k for k in keys]
    values = [omark[k] for k in keys]
    plot_bar_to_pdf(
        pdf=pdf,
        title="OMArk Summary",
        labels=[lbl.title() for lbl in labels],
        values=values,
        xlabel="Category",
        ylabel=ylabel,
        rotation=0,
    )
    add_kv_table_page(
        pdf,
        "OMArk Details",
        [(k, f"{v:.2f}%" if looks_like_pct else f"{int(v) if v == v and float(v).is_integer() else v}")
         for k, v in zip(labels, values)],
        note="Values interpreted as percentages if they all fit in 0–100.",
    )

# ----------------------- Main -----------------------

def main() -> None:
    if len(sys.argv) != 5:
        print("Usage: python pipeline.py <gff_file> <busco_stats_file> <omark_stats_file> <output_pdf>")
        sys.exit(1)

    gff_file = sys.argv[1]
    busco_stats_file = sys.argv[2]
    omark_stats_file = sys.argv[3]
    output_pdf = sys.argv[4]

    try:
        print("Validating input files...")
        print(f"GFF file path: {gff_file}")
        print(f"BUSCO stats path: {busco_stats_file}")
        print(f"OMArk stats path: {omark_stats_file}")
        print(f"Output PDF path: {output_pdf}")

        check_file_exists(gff_file)
        check_file_exists(busco_stats_file)
        check_file_exists(omark_stats_file)
        ensure_output_dir(output_pdf)

        # 1) GFF feature distribution
        print("Reading GFF and counting feature types...")
        feature_counts = count_unique_column3(gff_file)

        # 2) Parse BUSCO
        print("Parsing BUSCO stats...")
        busco = parse_busco_stats(busco_stats_file)

        # 3) Parse OMArk
        print("Parsing OMArk stats...")
        omark = parse_omark_stats(omark_stats_file)

        # 4) Build PDF
        print("Building PDF...")
        with PdfPages(output_pdf) as pdf:
            # Page 1: GFF
            if feature_counts:
                names = list(feature_counts.keys())
                values = [feature_counts[k] for k in names]
                plot_bar_to_pdf(
                    pdf=pdf,
                    title="Feature Distribution in GFF File",
                    labels=names,
                    values=values,
                    xlabel="Feature Type",
                    ylabel="Count",
                    rotation=45,
                )
            else:
                add_kv_table_page(pdf, "Feature Distribution in GFF File", [("Info", "No features found")])

            # Page 2–3: BUSCO & OMArk
            plot_busco_summary(pdf, busco)
            plot_omark_summary(pdf, omark)

        print(f"PDF successfully saved to {output_pdf}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
