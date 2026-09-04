from pydantic import BaseModel, Field


class BenchmarkDocument(BaseModel):
    invoice_number: str = Field(min_length=1)
    category: str = Field(min_length=1)
    template: int | None = Field(
        default=None,
        gt=0,
    )


class BenchmarkEvaluationSet(BaseModel):
    version: int = Field(gt=0)
    description: str = Field(min_length=1)
    documents: list[BenchmarkDocument] = Field(
        min_length=1,
    )