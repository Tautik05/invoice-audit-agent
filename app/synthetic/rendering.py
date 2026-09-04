from pathlib import Path
from random import Random

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.synthetic import SyntheticInvoiceRecord


OUTPUT_DIRECTORY = Path("data/synthetic/documents")


class InvoiceRenderer:
    """Render synthetic invoices using multiple realistic layouts."""

    def __init__(
        self,
        output_directory: Path = OUTPUT_DIRECTORY,
        seed: int = 42,
    ) -> None:
        self.output_directory = output_directory
        self.rng = Random(seed)

    def render(self, invoice: SyntheticInvoiceRecord) -> Path:
        self.output_directory.mkdir(parents=True, exist_ok=True)

        output_path = self.output_directory / f"{invoice.invoice_number}.pdf"

        # Deterministically assign a template based on invoice number.
        invoice_number = int(invoice.invoice_number.split("-")[-1])
        template_number = ((invoice_number - 1) % 7) + 1

        document = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()

        if template_number == 1:
            story = self._template_classic(invoice, styles)
        elif template_number == 2:
            story = self._template_two_column(invoice, styles)
        elif template_number == 3:
            story = self._template_metadata_first(invoice, styles)
        elif template_number == 4:
            story = self._template_business(invoice, styles)
        elif template_number == 5:
            story = self._template_compact(invoice, styles)
        elif template_number == 6:
            story = self._template_alternative_labels(invoice, styles)
        else:
            story = self._template_multi_section(invoice, styles)

        document.build(story)

        return output_path

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _items_table(
        self,
        invoice: SyntheticInvoiceRecord,
        headers: list[str],
        widths: list[int],
    ) -> Table:
        rows = [headers]

        for item in invoice.line_items:
            amount = item.quantity * item.unit_price

            rows.append(
                [
                    item.description,
                    str(item.quantity),
                    f"{invoice.currency} {item.unit_price:.2f}",
                    f"{invoice.currency} {amount:.2f}",
                ]
            )

        table = Table(rows, colWidths=widths)

        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        return table

    def _summary_table(
        self,
        invoice: SyntheticInvoiceRecord,
        total_label: str = "Total",
    ) -> Table:
        rows = [
            [
                "Subtotal",
                f"{invoice.currency} {invoice.subtotal:.2f}",
            ],
            [
                f"Tax ({invoice.tax_rate * 100:.0f}%)",
                f"{invoice.currency} {invoice.tax:.2f}",
            ],
            [
                total_label,
                f"{invoice.currency} {invoice.total:.2f}",
            ],
        ]

        table = Table(
            rows,
            colWidths=[150, 150],
            hAlign="RIGHT",
        )

        table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        return table

    def _metadata_table(
        self,
        invoice: SyntheticInvoiceRecord,
        labels: tuple[str, str, str, str],
    ) -> Table:
        invoice_label, date_label, po_label, currency_label = labels

        rows = [
            [invoice_label, invoice.invoice_number],
            [date_label, str(invoice.invoice_date)],
            [po_label, invoice.po_number or "N/A"],
            [currency_label, invoice.currency],
        ]

        table = Table(rows, colWidths=[130, 290])

        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        return table

    # ------------------------------------------------------------------
    # Template 1
    # ------------------------------------------------------------------

    def _template_classic(self, invoice, styles):
        story = [
            Paragraph(
                f"<b>{invoice.vendor}</b>",
                styles["Title"],
            ),
            Paragraph("INVOICE", styles["Heading1"]),
            Spacer(1, 12),
            self._metadata_table(
                invoice,
                (
                    "Invoice Number",
                    "Invoice Date",
                    "Purchase Order",
                    "Currency",
                ),
            ),
            Spacer(1, 20),
            self._items_table(
                invoice,
                ["Description", "Quantity", "Unit Price", "Amount"],
                [210, 70, 100, 100],
            ),
            Spacer(1, 20),
            self._summary_table(invoice),
        ]

        return story

    # ------------------------------------------------------------------
    # Template 2 — two-column header
    # ------------------------------------------------------------------

    def _template_two_column(self, invoice, styles):
        header = Table(
            [
                [
                    Paragraph(
                        f"<b>{invoice.vendor}</b>",
                        styles["Heading2"],
                    ),
                    Paragraph("<b>INVOICE</b>", styles["Heading1"]),
                ],
                [
                    "Vendor",
                    f"Invoice #: {invoice.invoice_number}",
                ],
                [
                    "",
                    f"Date: {invoice.invoice_date}",
                ],
                [
                    "",
                    f"PO: {invoice.po_number or 'N/A'}",
                ],
            ],
            colWidths=[260, 200],
        )

        header.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )

        return [
            header,
            Spacer(1, 25),
            self._items_table(
                invoice,
                ["Item", "Qty", "Rate", "Line Amount"],
                [210, 60, 90, 120],
            ),
            Spacer(1, 20),
            self._summary_table(invoice),
        ]

    # ------------------------------------------------------------------
    # Template 3 — metadata first
    # ------------------------------------------------------------------

    def _template_metadata_first(self, invoice, styles):
        story = [
            Paragraph(
                f"INVOICE #{invoice.invoice_number}",
                styles["Heading1"],
            ),
            Spacer(1, 12),
            Paragraph("<b>FROM</b>", styles["Heading3"]),
            Paragraph(invoice.vendor, styles["BodyText"]),
            Spacer(1, 15),
        ]

        details = Table(
            [
                ["DATE", str(invoice.invoice_date)],
                ["PURCHASE ORDER", invoice.po_number or "N/A"],
                ["CURRENCY", invoice.currency],
            ],
            colWidths=[150, 300],
        )

        details.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        story.extend(
            [
                details,
                Spacer(1, 20),
                Paragraph("<b>ITEMS</b>", styles["Heading3"]),
                Spacer(1, 8),
                self._items_table(
                    invoice,
                    ["Description", "Qty", "Price", "Amount"],
                    [210, 60, 90, 120],
                ),
                Spacer(1, 20),
                self._summary_table(invoice, total_label="Amount Due"),
            ]
        )

        return story

    # ------------------------------------------------------------------
    # Template 4 — business style
    # ------------------------------------------------------------------

    def _template_business(self, invoice, styles):
        vendor_block = Table(
            [
                [
                    Paragraph(
                        f"<b>{invoice.vendor}</b>",
                        styles["Heading2"],
                    ),
                    Paragraph(
                        "<b>INVOICE</b>",
                        styles["Heading1"],
                    ),
                ],
                [
                    "Business Address",
                    invoice.invoice_number,
                ],
                [
                    "Accounts Payable",
                    str(invoice.invoice_date),
                ],
            ],
            colWidths=[300, 160],
        )

        vendor_block.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        bill_to = Table(
            [
                ["BILL TO", ""],
                ["Vendor", invoice.vendor],
                ["PO Number", invoice.po_number or "N/A"],
                ["Currency", invoice.currency],
            ],
            colWidths=[130, 330],
        )

        bill_to.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )

        return [
            vendor_block,
            Spacer(1, 15),
            bill_to,
            Spacer(1, 20),
            self._items_table(
                invoice,
                ["Item Description", "Qty", "Rate", "Line Total"],
                [210, 60, 90, 120],
            ),
            Spacer(1, 20),
            self._summary_table(invoice),
        ]

    # ------------------------------------------------------------------
    # Template 5 — compact
    # ------------------------------------------------------------------

    def _template_compact(self, invoice, styles):
        compact_header = Table(
            [
                [
                    Paragraph(
                        f"<b>{invoice.vendor}</b>",
                        styles["Heading2"],
                    ),
                    f"INV: {invoice.invoice_number}",
                    f"DATE: {invoice.invoice_date}",
                ],
                [
                    "",
                    f"PO: {invoice.po_number or 'N/A'}",
                    f"CUR: {invoice.currency}",
                ],
            ],
            colWidths=[220, 120, 120],
        )

        compact_header.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )

        return [
            compact_header,
            Spacer(1, 18),
            self._items_table(
                invoice,
                ["Product", "Units", "Unit Cost", "Amount"],
                [210, 60, 90, 120],
            ),
            Spacer(1, 15),
            self._summary_table(invoice, total_label="Grand Total"),
        ]

    # ------------------------------------------------------------------
    # Template 6 — alternative terminology
    # ------------------------------------------------------------------

    def _template_alternative_labels(self, invoice, styles):
        header = [
            Paragraph(
                f"<b>{invoice.vendor}</b>",
                styles["Title"],
            ),
            Paragraph("BILLING STATEMENT", styles["Heading1"]),
            Spacer(1, 10),
        ]

        information = Table(
            [
                ["Inv. No.", invoice.invoice_number],
                ["Issued", str(invoice.invoice_date)],
                ["Ref. PO", invoice.po_number or "N/A"],
                ["Currency Code", invoice.currency],
            ],
            colWidths=[130, 290],
        )

        information.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        return [
            *header,
            information,
            Spacer(1, 20),
            self._items_table(
                invoice,
                ["Description", "Units", "Unit Cost", "Extended"],
                [210, 60, 90, 120],
            ),
            Spacer(1, 20),
            self._summary_table(invoice, total_label="Balance Due"),
        ]

    # ------------------------------------------------------------------
    # Template 7 — multi-section
    # ------------------------------------------------------------------

    def _template_multi_section(self, invoice, styles):
        sections = [
            [
                Paragraph(
                    f"<b>{invoice.vendor}</b>",
                    styles["Heading2"],
                ),
                Paragraph("INVOICE DOCUMENT", styles["Heading1"]),
            ],
            [
                "Document Number",
                invoice.invoice_number,
            ],
            [
                "Transaction Date",
                str(invoice.invoice_date),
            ],
            [
                "Reference",
                invoice.po_number or "No PO",
            ],
            [
                "Currency",
                invoice.currency,
            ],
        ]

        header = Table(sections, colWidths=[180, 280])

        header.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
                ]
            )
        )

        return [
            header,
            Spacer(1, 25),
            Paragraph("CHARGES", styles["Heading3"]),
            Spacer(1, 8),
            self._items_table(
                invoice,
                ["Charge", "Qty", "Price", "Extended Price"],
                [210, 60, 90, 120],
            ),
            Spacer(1, 20),
            self._summary_table(invoice, total_label="Total Amount"),
        ]