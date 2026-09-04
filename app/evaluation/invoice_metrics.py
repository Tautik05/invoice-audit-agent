from dataclasses import dataclass
from decimal import Decimal

from app.schemas.extraction import ExtractedInvoice
from app.schemas.synthetic import SyntheticInvoiceRecord


@dataclass
class InvoiceEvaluation:
    invoice_number_correct: bool
    vendor_correct: bool
    po_number_correct: bool
    currency_correct: bool
    line_items_correct: bool
    subtotal_correct: bool
    tax_rate_correct: bool
    tax_correct: bool
    total_correct: bool

    @property
    def correct_fields(self) -> int:
        return sum(
            [
                self.invoice_number_correct,
                self.vendor_correct,
                self.po_number_correct,
                self.currency_correct,
                self.line_items_correct,
                self.subtotal_correct,
                self.tax_rate_correct,
                self.tax_correct,
                self.total_correct,
            ]
        )

    @property
    def total_fields(self) -> int:
        return 9

    @property
    def accuracy(self) -> float:
        return self.correct_fields / self.total_fields


def decimal_equal(
    expected: Decimal,
    actual: Decimal,
) -> bool:
    return expected == actual


def line_items_equal(
    expected,
    actual,
) -> bool:
    if len(expected) != len(actual):
        return False

    for expected_item, actual_item in zip(expected, actual):
        if expected_item.description != actual_item.description:
            return False

        if expected_item.quantity != actual_item.quantity:
            return False

        if expected_item.unit_price != actual_item.unit_price:
            return False

    return True


def evaluate_invoice(
    ground_truth: SyntheticInvoiceRecord,
    prediction: ExtractedInvoice,
) -> InvoiceEvaluation:
    return InvoiceEvaluation(
        invoice_number_correct=(
            ground_truth.invoice_number
            == prediction.invoice_number
        ),
        vendor_correct=(
            ground_truth.vendor.strip().lower()
            == prediction.vendor.strip().lower()
        ),
        po_number_correct=(
            ground_truth.po_number
            == prediction.po_number
        ),
        currency_correct=(
            ground_truth.currency.upper()
            == prediction.currency.upper()
        ),
        line_items_correct=line_items_equal(
            ground_truth.line_items,
            prediction.line_items,
        ),
        subtotal_correct=decimal_equal(
            ground_truth.subtotal,
            prediction.subtotal,
        ),
        tax_rate_correct=decimal_equal(
            ground_truth.tax_rate,
            prediction.tax_rate,
        ),
        tax_correct=decimal_equal(
            ground_truth.tax,
            prediction.tax,
        ),
        total_correct=decimal_equal(
            ground_truth.total,
            prediction.total,
        ),
    )