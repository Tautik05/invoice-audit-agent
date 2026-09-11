import json
import shutil
import sys
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Paragraph,
)

# ---------------------------------------------------------------------------
# Project import setup
# ---------------------------------------------------------------------------

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1]),
)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path("data/audit_scenarios")
DOCUMENTS_DIR = OUTPUT_DIR / "documents"

GROUND_TRUTH_PATH = OUTPUT_DIR / "ground_truth.jsonl"
ERP_FIXTURES_PATH = OUTPUT_DIR / "erp_fixtures.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def money(value: str | Decimal) -> Decimal:
    """Convert a value to Decimal with two decimal places."""
    return Decimal(str(value)).quantize(Decimal("0.01"))


def calculate_totals(
    line_items: list[dict],
    tax_rate: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calculate subtotal, tax, and total from line items."""

    subtotal = sum(
        (
            money(item["quantity"]) * money(item["unit_price"])
            for item in line_items
        ),
        Decimal("0.00"),
    )

    subtotal = subtotal.quantize(Decimal("0.01"))

    tax = (subtotal * tax_rate).quantize(
        Decimal("0.01")
    )

    total = (subtotal + tax).quantize(
        Decimal("0.01")
    )

    return subtotal, tax, total


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

def generate_invoice_pdf(
    scenario: dict,
    output_path: Path,
) -> None:
    """Generate a realistic invoice PDF for one audit scenario."""

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    normal_style = styles["Normal"]

    story = []

    vendor = scenario["vendor"]
    invoice = scenario["invoice"]

    story.append(
        Paragraph(
            "INVOICE",
            title_style,
        )
    )

    story.append(Spacer(1, 8 * mm))

    header_data = [
        [
            Paragraph(
                f"<b>Vendor:</b><br/>{vendor['name']}",
                normal_style,
            ),
            Paragraph(
                f"<b>Invoice Number:</b><br/>"
                f"{invoice['invoice_number']}",
                normal_style,
            ),
        ],
        [
            Paragraph(
                f"<b>Vendor Code:</b><br/>{vendor['vendor_code']}",
                normal_style,
            ),
            Paragraph(
                f"<b>Invoice Date:</b><br/>{invoice['invoice_date']}",
                normal_style,
            ),
        ],
        [
            Paragraph(
                f"<b>Currency:</b><br/>{invoice['currency']}",
                normal_style,
            ),
            Paragraph(
                f"<b>Purchase Order:</b><br/>"
                f"{invoice.get('po_number') or 'N/A'}",
                normal_style,
            ),
        ],
    ]

    header_table = Table(
        header_data,
        colWidths=[85 * mm, 85 * mm],
    )

    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(header_table)
    story.append(Spacer(1, 10 * mm))

    story.append(
        Paragraph(
            "Line Items",
            heading_style,
        )
    )

    line_item_rows = [
        [
            "Description",
            "Quantity",
            "Unit Price",
            "Amount",
        ]
    ]

    for item in invoice["line_items"]:
        quantity = Decimal(str(item["quantity"]))
        unit_price = money(item["unit_price"])
        amount = (quantity * unit_price).quantize(
            Decimal("0.01")
        )

        line_item_rows.append(
            [
                item["description"],
                str(item["quantity"]),
                f"{invoice['currency']} {unit_price:,.2f}",
                f"{invoice['currency']} {amount:,.2f}",
            ]
        )

    line_item_table = Table(
        line_item_rows,
        colWidths=[
            75 * mm,
            25 * mm,
            35 * mm,
            35 * mm,
        ],
        repeatRows=1,
    )

    line_item_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.lightgrey,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.black,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "RIGHT",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(line_item_table)
    story.append(Spacer(1, 8 * mm))

    totals = [
        [
            "Subtotal",
            f"{invoice['currency']} "
            f"{invoice['subtotal']:,.2f}",
        ],
        [
            f"Tax ({invoice['tax_rate'] * 100:.0f}%)",
            f"{invoice['currency']} "
            f"{invoice['tax']:,.2f}",
        ],
        [
            "Total",
            f"{invoice['currency']} "
            f"{invoice['total']:,.2f}",
        ],
    ]

    totals_table = Table(
        totals,
        colWidths=[
            135 * mm,
            35 * mm,
        ],
        hAlign="RIGHT",
    )

    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(totals_table)

    story.append(Spacer(1, 12 * mm))

    story.append(
        Paragraph(
            "Thank you for your business.",
            normal_style,
        )
    )

    document.build(story)


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS = [
    {
        "scenario_id": "AUDIT-001",
        "name": "Exact PO Match",
        "description": (
            "Invoice exactly matches the ERP purchase order."
        ),
        "vendor": {
            "vendor_code": "V-1001",
            "name": "Acme Office Supplies",
            "currency": "USD",
        },
        "invoice": {
            "invoice_number": "AUDIT-001",
            "invoice_date": "2026-09-01",
            "po_number": "PO-10001",
            "currency": "USD",
            "tax_rate": Decimal("0.18"),
            "line_items": [
                {
                    "description": "Laptop",
                    "quantity": 10,
                    "unit_price": "1000.00",
                },
                {
                    "description": "Monitor",
                    "quantity": 5,
                    "unit_price": "300.00",
                },
            ],
        },
        "expected": {
            "validation": "passed",
            "reconciliation": "matched",
            "decision": "auto_approve",
            "settlement": True,
        },
        "erp": {
            "purchase_order": {
                "po_number": "PO-10001",
                "vendor_code": "V-1001",
                "currency": "USD",
                "tax_rate": "0.18",
                "status": "approved",
                "line_items": [
                    {
                        "description": "Laptop",
                        "quantity": 10,
                        "unit_price": "1000.00",
                    },
                    {
                        "description": "Monitor",
                        "quantity": 5,
                        "unit_price": "300.00",
                    },
                ],
            }
        },
    },
    {
        "scenario_id": "AUDIT-002",
        "name": "Missing PO",
        "description": (
            "Valid invoice with a known ERP vendor but no PO."
        ),
        "vendor": {
            "vendor_code": "V-1002",
            "name": "Hoffman Ltd",
            "currency": "INR",
        },
        "invoice": {
            "invoice_number": "AUDIT-002",
            "invoice_date": "2026-09-02",
            "po_number": None,
            "currency": "INR",
            "tax_rate": Decimal("0.18"),
            "line_items": [
                {
                    "description": "Office Printer",
                    "quantity": 4,
                    "unit_price": "15000.00",
                },
                {
                    "description": "Printer Paper",
                    "quantity": 10,
                    "unit_price": "500.00",
                },
            ],
        },
        "expected": {
            "validation": "passed",
            "reconciliation": "not_found",
            "decision": "human_review",
            "settlement": True,
            "human_approval_required": True,
        },
        "erp": {
            "purchase_order": None,
        },
    },
    {
        "scenario_id": "AUDIT-003",
        "name": "Small Price Variance",
        "description": (
            "Invoice contains a small unit-price variance "
            "against the PO."
        ),
        "vendor": {
            "vendor_code": "V-1003",
            "name": "Global Office Systems",
            "currency": "USD",
        },
        "invoice": {
            "invoice_number": "AUDIT-003",
            "invoice_date": "2026-09-03",
            "po_number": "PO-10003",
            "currency": "USD",
            "tax_rate": Decimal("0.18"),
            "line_items": [
                {
                    "description": "Keyboard",
                    "quantity": 20,
                    "unit_price": "105.00",
                },
                {
                    "description": "Mouse",
                    "quantity": 20,
                    "unit_price": "50.00",
                },
            ],
        },
        "expected": {
            "validation": "passed",
            "reconciliation": "variance",
            "decision": "human_review",
            "settlement": True,
            "human_approval_required": True,
        },
        "erp": {
            "purchase_order": {
                "po_number": "PO-10003",
                "vendor_code": "V-1003",
                "currency": "USD",
                "tax_rate": "0.18",
                "status": "approved",
                "line_items": [
                    {
                        "description": "Keyboard",
                        "quantity": 20,
                        "unit_price": "100.00",
                    },
                    {
                        "description": "Mouse",
                        "quantity": 20,
                        "unit_price": "50.00",
                    },
                ],
            }
        },
    },
    {
        "scenario_id": "AUDIT-004",
        "name": "Vendor Mismatch",
        "description": (
            "Invoice references a PO belonging to another vendor."
        ),
        "vendor": {
            "vendor_code": "V-1004",
            "name": "Northstar Technologies",
            "currency": "USD",
        },
        "invoice": {
            "invoice_number": "AUDIT-004",
            "invoice_date": "2026-09-04",
            "po_number": "PO-10004",
            "currency": "USD",
            "tax_rate": Decimal("0.18"),
            "line_items": [
                {
                    "description": "Laptop Dock",
                    "quantity": 10,
                    "unit_price": "250.00",
                }
            ],
        },
        "expected": {
            "validation": "passed",
            "reconciliation": "variance",
            "decision": "human_review",
            "settlement": True,
            "human_approval_required": True,
        },
        "erp": {
            "purchase_order": {
                "po_number": "PO-10004",
                "vendor_code": "V-9999",
                "currency": "USD",
                "tax_rate": "0.18",
                "status": "approved",
                "line_items": [
                    {
                        "description": "Laptop Dock",
                        "quantity": 10,
                        "unit_price": "250.00",
                    }
                ],
            }
        },
    },
    {
        "scenario_id": "AUDIT-005",
        "name": "Currency Mismatch",
        "description": (
            "Invoice currency differs from the ERP purchase order."
        ),
        "vendor": {
            "vendor_code": "V-1005",
            "name": "European Office Goods",
            "currency": "EUR",
        },
        "invoice": {
            "invoice_number": "AUDIT-005",
            "invoice_date": "2026-09-05",
            "po_number": "PO-10005",
            "currency": "USD",
            "tax_rate": Decimal("0.18"),
            "line_items": [
                {
                    "description": "Office Chair",
                    "quantity": 10,
                    "unit_price": "400.00",
                }
            ],
        },
        "expected": {
            "validation": "passed",
            "reconciliation": "variance",
            "decision": "human_review",
            "settlement": True,
            "human_approval_required": True,
        },
        "erp": {
            "purchase_order": {
                "po_number": "PO-10005",
                "vendor_code": "V-1005",
                "currency": "EUR",
                "tax_rate": "0.20",
                "status": "approved",
                "line_items": [
                    {
                        "description": "Office Chair",
                        "quantity": 10,
                        "unit_price": "400.00",
                    }
                ],
            }
        },
    },
    {
        "scenario_id": "AUDIT-006",
        "name": "Wrong PO",
        "description": (
            "Invoice references a real PO, but the PO is unrelated "
            "to the invoice contents."
        ),
        "vendor": {
            "vendor_code": "V-1006",
            "name": "Metro Computing",
            "currency": "GBP",
        },
        "invoice": {
            "invoice_number": "AUDIT-006",
            "invoice_date": "2026-09-06",
            "po_number": "PO-10006",
            "currency": "GBP",
            "tax_rate": Decimal("0.20"),
            "line_items": [
                {
                    "description": "Webcam",
                    "quantity": 15,
                    "unit_price": "120.00",
                }
            ],
        },
        "expected": {
            "validation": "passed",
            "reconciliation": "variance",
            "decision": "human_review",
            "settlement": True,
            "human_approval_required": True,
        },
        "erp": {
            "purchase_order": {
                "po_number": "PO-10006",
                "vendor_code": "V-1006",
                "currency": "GBP",
                "tax_rate": "0.20",
                "status": "approved",
                "line_items": [
                    {
                        "description": "Headset",
                        "quantity": 15,
                        "unit_price": "80.00",
                    }
                ],
            }
        },
    },
    {
        "scenario_id": "AUDIT-007",
        "name": "Duplicate Invoice",
        "description": (
            "Invoice number already exists as a settled invoice."
        ),
        "vendor": {
            "vendor_code": "V-1007",
            "name": "Reliable Business Equipment",
            "currency": "USD",
        },
        "invoice": {
            "invoice_number": "AUDIT-007",
            "invoice_date": "2026-09-07",
            "po_number": "PO-10007",
            "currency": "USD",
            "tax_rate": Decimal("0.18"),
            "line_items": [
                {
                    "description": "Desktop Computer",
                    "quantity": 5,
                    "unit_price": "1200.00",
                }
            ],
        },
        "expected": {
            "validation": "passed",
            "reconciliation": "matched",
            "decision": "reject",
            "settlement": False,
            "duplicate": True,
        },
        "erp": {
            "purchase_order": {
                "po_number": "PO-10007",
                "vendor_code": "V-1007",
                "currency": "USD",
                "tax_rate": "0.18",
                "status": "approved",
                "line_items": [
                    {
                        "description": "Desktop Computer",
                        "quantity": 5,
                        "unit_price": "1200.00",
                    }
                ],
            },
            "settled_invoice": {
                "invoice_number": "AUDIT-007",
                "vendor_code": "V-1007",
                "po_number": "PO-10007",
                "currency": "USD",
                "status": "settled",
            },
        },
    },
    {
        "scenario_id": "AUDIT-008",
        "name": "Invalid Financial Calculation",
        "description": (
            "Invoice total is mathematically inconsistent with "
            "subtotal and tax."
        ),
        "vendor": {
            "vendor_code": "V-1008",
            "name": "Precision Office Ltd",
            "currency": "USD",
        },
        "invoice": {
            "invoice_number": "AUDIT-008",
            "invoice_date": "2026-09-08",
            "po_number": "PO-10008",
            "currency": "USD",
            "tax_rate": Decimal("0.18"),
            "line_items": [
                {
                    "description": "Printer",
                    "quantity": 5,
                    "unit_price": "1000.00",
                }
            ],
            "forced_total": "6000.00",
        },
        "expected": {
            "validation": "failed",
            "reconciliation": None,
            "decision": "reject",
            "settlement": False,
        },
        "erp": {
            "purchase_order": {
                "po_number": "PO-10008",
                "vendor_code": "V-1008",
                "currency": "USD",
                "tax_rate": "0.18",
                "status": "approved",
                "line_items": [
                    {
                        "description": "Printer",
                        "quantity": 5,
                        "unit_price": "1000.00",
                    }
                ],
            }
        },
    },
    {
        "scenario_id": "AUDIT-009",
        "name": "Large Price Variance",
        "description": (
            "Invoice contains a substantial price difference "
            "from the approved PO."
        ),
        "vendor": {
            "vendor_code": "V-1009",
            "name": "Enterprise Hardware Corp",
            "currency": "USD",
        },
        "invoice": {
            "invoice_number": "AUDIT-009",
            "invoice_date": "2026-09-09",
            "po_number": "PO-10009",
            "currency": "USD",
            "tax_rate": Decimal("0.18"),
            "line_items": [
                {
                    "description": "Server",
                    "quantity": 2,
                    "unit_price": "5000.00",
                }
            ],
        },
        "expected": {
            "validation": "passed",
            "reconciliation": "variance",
            "decision": "human_review",
            "settlement": True,
            "human_approval_required": True,
        },
        "erp": {
            "purchase_order": {
                "po_number": "PO-10009",
                "vendor_code": "V-1009",
                "currency": "USD",
                "tax_rate": "0.18",
                "status": "approved",
                "line_items": [
                    {
                        "description": "Server",
                        "quantity": 2,
                        "unit_price": "3000.00",
                    }
                ],
            }
        },
    },
    {
        "scenario_id": "AUDIT-010",
        "name": "Ambiguous Vendor Match",
        "description": (
            "Invoice has no PO and multiple ERP purchase orders "
            "belong to vendors with the same normalized name."
        ),
        "vendor": {
            "vendor_code": "V-1010",
            "name": "ABC Technologies",
            "currency": "USD",
        },
        "invoice": {
            "invoice_number": "AUDIT-010",
            "invoice_date": "2026-09-10",
            "po_number": None,
            "currency": "USD",
            "tax_rate": Decimal("0.18"),
            "line_items": [
                {
                    "description": "Network Switch",
                    "quantity": 5,
                    "unit_price": "600.00",
                }
            ],
        },
        "expected": {
            "validation": "passed",
            "reconciliation": "ambiguous",
            "decision": "human_review",
            "settlement": True,
            "human_approval_required": True,
        },
        "erp": {
            "purchase_orders": [
                {
                    "po_number": "PO-10010-A",
                    "vendor_code": "V-1011",
                    "vendor_name": "ABC Technologies",
                    "currency": "USD",
                    "tax_rate": "0.18",
                    "status": "approved",
                    "line_items": [
                        {
                            "description": "Network Switch",
                            "quantity": 5,
                            "unit_price": "600.00",
                        }
                    ],
                },
                {
                    "po_number": "PO-10010-B",
                    "vendor_code": "V-1012",
                    "vendor_name": "ABC Technologies",
                    "currency": "USD",
                    "tax_rate": "0.18",
                    "status": "approved",
                    "line_items": [
                        {
                            "description": "Network Switch",
                            "quantity": 5,
                            "unit_price": "600.00",
                        }
                    ],
                },
            ]
        },
    },
]


# ---------------------------------------------------------------------------
# Finalize invoice financial fields
# ---------------------------------------------------------------------------

def finalize_scenario(scenario: dict) -> dict:
    """Calculate invoice totals while preserving intentional anomalies."""

    invoice = scenario["invoice"]

    subtotal, tax, total = calculate_totals(
        invoice["line_items"],
        invoice["tax_rate"],
    )

    invoice["subtotal"] = subtotal
    invoice["tax"] = tax

    if "forced_total" in invoice:
        invoice["total"] = money(
            invoice["forced_total"]
        )
    else:
        invoice["total"] = total

    return scenario


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------

def json_default(value):
    """Serialize Decimal values for JSON."""
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(
        f"Object of type {type(value).__name__} "
        "is not JSON serializable"
    )


# ---------------------------------------------------------------------------
# Dataset generation
# ---------------------------------------------------------------------------

def generate_dataset() -> None:
    """Generate audit scenario PDFs and metadata."""

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    DOCUMENTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    scenarios = [
        finalize_scenario(scenario)
        for scenario in SCENARIOS
    ]

    # ---------------------------------------------------------------
    # Generate PDFs
    # ---------------------------------------------------------------

    for scenario in scenarios:
        filename = (
            f"{scenario['scenario_id']}.pdf"
        )

        output_path = DOCUMENTS_DIR / filename

        generate_invoice_pdf(
            scenario,
            output_path,
        )

    # ---------------------------------------------------------------
    # Ground truth
    # ---------------------------------------------------------------

    with GROUND_TRUTH_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        for scenario in scenarios:
            record = {
                "scenario_id": scenario["scenario_id"],
                "name": scenario["name"],
                "description": scenario["description"],
                "invoice_file": (
                    f"{scenario['scenario_id']}.pdf"
                ),
                "vendor": scenario["vendor"],
                "invoice": scenario["invoice"],
                "expected": scenario["expected"],
            }

            file.write(
                json.dumps(
                    record,
                    default=json_default,
                )
                + "\n"
            )

    # ---------------------------------------------------------------
    # ERP fixtures
    # ---------------------------------------------------------------

    vendors = {}
    purchase_orders = []
    settled_invoices = []

    for scenario in scenarios:
        vendor = scenario["vendor"]

        vendors[vendor["vendor_code"]] = vendor

        erp = scenario["erp"]

        if erp.get("purchase_order") is not None:
            purchase_orders.append(
                erp["purchase_order"]
            )

        for purchase_order in erp.get(
            "purchase_orders",
            [],
        ):
            purchase_orders.append(
                purchase_order
            )

        if erp.get("settled_invoice") is not None:
            settled_invoices.append(
                erp["settled_invoice"]
            )

    # Add the vendor used by the vendor-mismatch PO.
    vendors["V-9999"] = {
        "vendor_code": "V-9999",
        "name": "Different Vendor Ltd",
        "currency": "USD",
    }

    # Add vendors used by ambiguous scenario.
    vendors["V-1011"] = {
        "vendor_code": "V-1011",
        "name": "ABC Technologies",
        "currency": "USD",
    }

    vendors["V-1012"] = {
        "vendor_code": "V-1012",
        "name": "ABC Technologies",
        "currency": "USD",
    }

    erp_fixtures = {
        "vendors": list(vendors.values()),
        "purchase_orders": purchase_orders,
        "settled_invoices": settled_invoices,
    }

    with ERP_FIXTURES_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            erp_fixtures,
            file,
            indent=2,
            default=json_default,
        )

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------

    print(
        f"Generated audit dataset: "
        f"{OUTPUT_DIR}"
    )

    print(
        f"Generated {len(scenarios)} invoice PDFs."
    )

    print(
        f"Ground truth: {GROUND_TRUTH_PATH}"
    )

    print(
        f"ERP fixtures: {ERP_FIXTURES_PATH}"
    )

    print("\nScenarios:")

    for scenario in scenarios:
        expected = scenario["expected"]

        print(
            f"  {scenario['scenario_id']} | "
            f"{scenario['name']} | "
            f"decision={expected['decision']} | "
            f"settlement={expected['settlement']}"
        )


if __name__ == "__main__":
    generate_dataset()