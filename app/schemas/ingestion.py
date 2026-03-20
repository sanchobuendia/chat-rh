from datetime import datetime
from pydantic import BaseModel


class IngestionJobRead(BaseModel):
    id: int
    file_name: str
    title: str
    base_id: int
    classification: str
    status: str
    uploaded_by: str

    model_config = {"from_attributes": True}
