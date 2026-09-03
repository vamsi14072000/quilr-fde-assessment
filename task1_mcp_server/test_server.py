import pytest
from pydantic import ValidationError

from models import CustomerRecordInput, RefundInput


@pytest.mark.parametrize(
    "customer_id",
    ["CUST-12345", "CUST-00001", "CUST-99999"],
)
def test_valid_customer_id(customer_id):
    model = CustomerRecordInput(customer_id=customer_id)
    assert model.customer_id == customer_id


@pytest.mark.parametrize(
    "customer_id",
    [
        "ABC-12345",
        "CUST-123",
        "CUST-ABCDE",
        "12345",
        "",
    ],
)
def test_invalid_customer_id(customer_id):
    with pytest.raises(ValidationError):
        CustomerRecordInput(customer_id=customer_id)


@pytest.mark.parametrize("amount", [1, 10.50, 100.00])
def test_valid_refund_amount(amount):
    model = RefundInput(
        customer_id="CUST-12345",
        amount=amount,
        reason="Product arrived damaged",
    )

    assert model.amount == amount


@pytest.mark.parametrize("amount", [0, -1, -100])
def test_invalid_refund_amount(amount):
    with pytest.raises(ValidationError):
        RefundInput(
            customer_id="CUST-12345",
            amount=amount,
            reason="Product arrived damaged",
        )


def test_short_reason_rejected():
    with pytest.raises(ValidationError):
        RefundInput(
            customer_id="CUST-12345",
            amount=50,
            reason="damaged",
        )


def test_valid_reason():
    model = RefundInput(
        customer_id="CUST-12345",
        amount=50,
        reason="Product arrived damaged",
    )

    assert model.reason == "Product arrived damaged"


def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        CustomerRecordInput(
            customer_id="CUST-12345",
            unexpected_field="invalid",
        )