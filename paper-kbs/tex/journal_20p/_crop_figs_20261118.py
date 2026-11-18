#!/usr/bin/env python3
"""Whitespace audit + tight-bbox crop for the journal_20p figure PDFs.

Every PDF referenced by main_20p.tex / supplementary.tex is rasterised, its
non-white content bounding box is measured, and (in --crop mode) the page
CropBox is rewritten to that box plus a uniform breathing margin.  The output
hashes in experiment_data/figure-redraw-manifest-20261116.json are refreshed
afterwards so provenance keeps matching the packaged files.

Usage:  python _crop_figs_20261118.py [--crop]
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
FIGS = HERE / "figs"
MANIFEST = HERE / "experiment_data" / "figure-redraw-manifest-20261116.json"

MAIN_FIGS = [
    "fig_library_analogy_vector",
    "fig_service_architecture_vector",
    "fig_workflow_vector",
    "fig_tiered_drawio_20261116",
    "fig_opt_route",
    "fig_opt_case",
    "fig_opt_content",
    "fig_opt_answer",
    "fig_opt_verifier",
]
SUPP_FIGS = [
    "fig1_architecture_native",
    "fig_opt_s_answer",
    "fig_exp_s3",
    "fig_opt_s_margin",
    "fig_exp_s5",
]

MARGIN_PT = 5.0   # breathing margin kept around the content box
THRESHOLD = 245   # pixel is content if min(R,G,B) < THRESHOLD (pale fills count)
DPI = 200


def content_bbox(path: Path) -> tuple[pymupdf.Page, pymupdf.Rect]:
    doc = pymupdf.open(path)
    page = doc[0]
    if page.rotation != 0:
        raise ValueError(f"{path.name}: rotation {page.rotation} not handled")
    # Reset any pre-existing CropBox before measuring.  Both get_pixmap and
    # set_cropbox operate in MediaBox coordinates, so measuring an
    # already-cropped page and then writing the box shifted the frame:
    # content near the old crop-box origin fell outside the new one (bottom
    # clipped) while previously cropped-away padding re-entered at the top.
    page.set_cropbox(page.mediabox)
    pix = page.get_pixmap(dpi=DPI, annots=False)
    if pix.colorspace is None or pix.n < 3:
        raise ValueError(f"{path.name}: unexpected pixmap colorspace")
    samples = pix.samples
    stride = pix.stride
    width, height = pix.width, pix.height
    min_x, min_y, max_x, max_y = width, height, -1, -1
    for y in range(height):
        row = samples[y * stride : y * stride + width * pix.n]
        # min over the first three channels per pixel
        found = False
        for i in range(0, width * pix.n, pix.n):
            if row[i] < THRESHOLD or row[i + 1] < THRESHOLD or row[i + 2] < THRESHOLD:
                found = True
                break
        if not found:
            continue
        # column-precise second pass only on rows that contain content
        for i in range(0, width * pix.n, pix.n):
            if row[i] < THRESHOLD or row[i + 1] < THRESHOLD or row[i + 2] < THRESHOLD:
                x = i // pix.n
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
        if y < min_y:
            min_y = y
        if y > max_y:
            max_y = y
    if max_x < 0:
        raise ValueError(f"{path.name}: no content pixels found")
    sx = page.rect.width / width
    sy = page.rect.height / height
    rect = pymupdf.Rect(min_x * sx, min_y * sy, (max_x + 1) * sx, (max_y + 1) * sy)
    return page, rect


def audit() -> None:
    print(f"{'figure':38s} {'page (pt)':>16s} {'content (pt)':>18s} "
          f"{'margins L/T/R/B':>20s}")
    for name in MAIN_FIGS + SUPP_FIGS:
        path = FIGS / f"{name}.pdf"
        if not path.is_file():
            print(f"{name:38s}  MISSING")
            continue
        page, rect = content_bbox(path)
        page_rect = page.rect
        margins = (
            rect.x0, rect.y0,
            page_rect.x1 - rect.x1, page_rect.y1 - rect.y1,
        )
        print(f"{name:38s} {page_rect.width:7.1f}x{page_rect.height:6.1f} "
              f"{rect.width:8.1f}x{rect.height:7.1f} "
              f"{margins[0]:5.1f}/{margins[1]:5.1f}/{margins[2]:5.1f}/{margins[3]:5.1f}")


def replace_with_retry(tmp: Path, path: Path, attempts: int = 5) -> None:
    for k in range(attempts):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if k == attempts - 1:
                raise
            import time
            time.sleep(1.0 + k)


def crop() -> None:
    changed = 0
    for name in MAIN_FIGS + SUPP_FIGS:
        path = FIGS / f"{name}.pdf"
        if not path.is_file():
            print(f"skip missing {name}")
            continue
        page, rect = content_bbox(path)
        page_rect = page.rect
        box = pymupdf.Rect(
            max(page_rect.x0, rect.x0 - MARGIN_PT),
            max(page_rect.y0, rect.y0 - MARGIN_PT),
            min(page_rect.x1, rect.x1 + MARGIN_PT),
            min(page_rect.y1, rect.y1 + MARGIN_PT),
        )
        old = (page_rect.width, page_rect.height)
        page.set_cropbox(box)
        tmp = path.with_suffix(".pdf.tmp")
        page.parent.save(tmp, garbage=3, deflate=True)
        page.parent.close()
        replace_with_retry(tmp, path)
        new_doc = pymupdf.open(path)
        new_rect = new_doc[0].rect
        new_doc.close()
        dw = new_rect.width - old[0]
        dh = new_rect.height - old[1]
        if abs(dw) > 0.05 or abs(dh) > 0.05:
            changed += 1
            print(f"crop {name:36s} {old[0]:6.1f}x{old[1]:6.1f} -> "
                  f"{new_rect.width:6.1f}x{new_rect.height:6.1f}  (dW {dw:+6.1f}, dH {dh:+6.1f})")
        else:
            print(f"kept {name:37s} already tight")
    print(f"cropped {changed} figure(s)")

    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        outputs = manifest.get("output_sha256", {})
        touched = 0
        for rel in list(outputs):
            path = HERE / rel
            if path.is_file() and path.suffix == ".pdf" and (
                path.stem in MAIN_FIGS or path.stem in SUPP_FIGS
            ):
                outputs[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
                touched += 1
        MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
        print(f"refreshed {touched} output hash(es) in {MANIFEST.name}")


if __name__ == "__main__":
    if "--crop" in sys.argv[1:]:
        crop()
    else:
        audit()
