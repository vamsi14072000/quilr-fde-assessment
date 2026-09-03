from pydantic import BaseModel, ConfigDict, Field


class CustomerRecordInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(
        ...,
        pattern=r"^CUST-\d{5}$",
        description="Customer ID formatted as CUST-XXXXX",
    )


class RefundInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(
        ...,
        pattern=r"^CUST-\d{5}$",
        description="Customer ID formatted as CUST-XXXXX",
    )

    amount: float = Field(
        ...,
        gt=0,
        description="Refund amount must be greater than zero.",
    )

    reason: str = Field(
        ...,
        min_length=10,
        description="Refund reason must contain at least 10 characters.",
    )