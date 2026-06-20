"""Generate the public EPP-NSV workflow figure used by paper/V1.tex.

The diagram is conceptual. It contains no patient data and is designed to make
the evidence boundary of the prototype explicit.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

OUTPUT = "paper/workflow.pdf"
PAGE_W, PAGE_H = landscape(letter)


def wrapped_lines(text, font, size, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = word if not current else current + " " + word
        if stringWidth(candidate, font, size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def box(c, x, y, w, h, title, body, fill):
    c.setStrokeColor(colors.HexColor("#374151"))
    c.setLineWidth(1.1)
    c.setFillColor(fill)
    c.roundRect(x, y, w, h, 8, stroke=1, fill=1)
    c.setFillColor(colors.HexColor("#111827"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(x + w / 2, y + h - 16, title)
    c.setFont("Helvetica", 7.1)
    lines = wrapped_lines(body, "Helvetica", 7.1, w - 14)
    base_y = y + h - 31
    for i, line in enumerate(lines[:4]):
        c.drawCentredString(x + w / 2, base_y - i * 9, line)


def arrow(c, x1, y1, x2, y2):
    c.setStrokeColor(colors.HexColor("#374151"))
    c.setLineWidth(1.2)
    c.line(x1, y1, x2, y2)
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 6
    for offset in (2.65, -2.65):
        c.line(
            x2,
            y2,
            x2 - size * math.cos(angle + offset),
            y2 - size * math.sin(angle + offset),
        )


def main():
    c = canvas.Canvas(OUTPUT, pagesize=landscape(letter))
    c.setTitle("EPP-NSV high-level workflow")
    c.setAuthor("Mohammad Tanhaei")
    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawCentredString(PAGE_W / 2, PAGE_H - 33, "EPP-NSV: Evidence-Bounded Verification Workflow")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#374151"))
    c.drawCentredString(
        PAGE_W / 2,
        PAGE_H - 48,
        "Conceptual public-prototype workflow; not a clinical deployment or real-data result.",
    )

    y = 325
    w, h = 123, 72
    xs = [35, 172, 309, 446, 583]
    entries = [
        ("1. Evidence-bearing input", "Structured EHR fields, notes, specialty-form features, timestamps, provenance, missingness.", colors.HexColor("#DCEEFF")),
        ("2. Per-eye state + scope", "Patient-eye-episode abstraction. Disease and same-eye gate; invalid comparisons are out of scope.", colors.HexColor("#EEE4FF")),
        ("3. Semantic lifting", "Candidate facts may be proposed; evidence, assertion, laterality, time, and validation remain attached.", colors.HexColor("#FFE7C2")),
        ("4. Versioned policy", "Named decision vector and safety-critical predicates. Public release uses a synthetic demonstration policy.", colors.HexColor("#DDF5E5")),
        ("5. SMT distinguishing query", "Compile policy branches, bind admissible observations, and ask whether any output component differs.", colors.HexColor("#FFE0E0")),
    ]
    for x, entry in zip(xs, entries):
        box(c, x, y, w, h, *entry)
    for i in range(len(xs) - 1):
        arrow(c, xs[i] + w, y + h / 2, xs[i + 1] - 5, y + h / 2)

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawCentredString(PAGE_W / 2, 255, "Conservative audit-oriented outcomes")
    outcomes = [
        ("Equivalent under Guideline", "No counterexample under the named policy and complete required evidence.", colors.HexColor("#E5F5E8")),
        ("Non-equivalent", "A compiled policy branch produces a decision-vector difference.", colors.HexColor("#FDE2E2")),
        ("Indeterminate", "Required evidence is missing, stale, conflicting, or unresolved.", colors.HexColor("#FFF3CD")),
        ("Out of scope", "Disease or laterality eligibility gate fails; no cross-domain comparison.", colors.HexColor("#EAECEF")),
    ]
    y2, w2, h2 = 132, 166, 66
    xs2 = [51, 230, 409, 588]
    for x, (title, body, fill) in zip(xs2, outcomes):
        box(c, x, y2, w2, h2, title, body, fill)
        arrow(c, PAGE_W / 2, y - 8, x + w2 / 2, y2 + h2 + 3)

    c.setFont("Helvetica-Oblique", 7.3)
    c.setFillColor(colors.HexColor("#374151"))
    c.drawCentredString(
        PAGE_W / 2,
        75,
        "An SMT result validates only the encoded policy, observation model, eligibility gate, and admitted evidence; it does not prove real-world clinical interchangeability.",
    )
    c.save()


if __name__ == "__main__":
    main()
