import pytest

from app.agent.tools.erp_tools import ERPTools
from app.schemas.tools import (
    CheckDuplicateInvoiceArgs,
    QueryPurchaseOrderArgs,
    SearchPurchaseOrdersArgs,
)


def test_query_erp_by_po(erp_service):
    tools = ERPTools(erp_service)

    result = tools.query_erp_by_po(
        QueryPurchaseOrderArgs(po_number="PO-8821")
    )

    assert result is not None
    assert result.po_number == "PO-8821"


def test_query_erp_by_po_missing(erp_service):
    tools = ERPTools(erp_service)

    result = tools.query_erp_by_po(
        QueryPurchaseOrderArgs(po_number="PO-9999")
    )

    assert result is None


def test_search_erp_by_vendor(erp_service):
    tools = ERPTools(erp_service)

    results = tools.search_erp_by_vendor(
        SearchPurchaseOrdersArgs(vendor_name="ABC Supplies")
    )

    assert len(results) == 1
    assert results[0].po_number == "PO-8821"


def test_check_duplicate_invoice(erp_service):
    tools = ERPTools(erp_service)

    result = tools.check_duplicate_invoice(
        CheckDuplicateInvoiceArgs(invoice_number="INV-001")
    )

    assert result is False


def test_invalid_tool_arguments():
    with pytest.raises(ValueError):
        QueryPurchaseOrderArgs(po_number="")