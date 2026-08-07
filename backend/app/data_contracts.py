from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MunicipalityContract(StrictContract):
    ibge_code: str = Field(pattern=r"^\d{7}$")
    name: str = Field(min_length=1)
    uf: str = Field(pattern=r"^[A-Z]{2}$")
    latitude: float = Field(ge=-34, le=6)
    longitude: float = Field(ge=-74, le=-28)


class ClimateDailyContract(StrictContract):
    municipality_ibge: str = Field(pattern=r"^\d{7}$")
    observed_on: date
    temperature_min_c: float
    temperature_max_c: float
    precipitation_mm: float = Field(ge=0)
    source: str = Field(min_length=1)
    collected_at: datetime

    @field_validator("temperature_max_c")
    @classmethod
    def max_not_absurd(cls, value: float) -> float:
        if value > 70:
            raise ValueError("temperature_max_c outside supported range")
        return value

    def validate_cross_fields(self) -> "ClimateDailyContract":
        if self.temperature_min_c > self.temperature_max_c:
            raise ValueError("temperature_min_c must be <= temperature_max_c")
        return self


class ZarcWindowContract(StrictContract):
    municipality_ibge: str = Field(pattern=r"^\d{7}$")
    crop: str = Field(min_length=1)
    soil_class: str = Field(min_length=1)
    cycle_group: str = Field(min_length=1)
    start_date: date
    end_date: date
    source_document: str = Field(min_length=1)
    source_version: str = Field(min_length=1)

    def validate_cross_fields(self) -> "ZarcWindowContract":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be <= end_date")
        return self


def validate_contract(record: StrictContract) -> StrictContract:
    validator = getattr(record, "validate_cross_fields", None)
    return validator() if validator else record
