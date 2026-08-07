from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.data_contracts import ClimateDailyContract, MunicipalityContract, ZarcWindowContract, validate_contract


def test_municipality_contract_accepts_valid_ibge_record() -> None:
    item = MunicipalityContract(
        ibge_code="3302403",
        name="Macaé",
        uf="RJ",
        latitude=-22.37,
        longitude=-41.78,
    )
    assert item.uf == "RJ"


def test_municipality_contract_rejects_bad_ibge_code() -> None:
    with pytest.raises(ValidationError):
        MunicipalityContract(
            ibge_code="33024",
            name="Macaé",
            uf="RJ",
            latitude=-22.37,
            longitude=-41.78,
        )


def test_climate_contract_rejects_negative_precipitation() -> None:
    with pytest.raises(ValidationError):
        ClimateDailyContract(
            municipality_ibge="3302403",
            observed_on=date(2026, 8, 7),
            temperature_min_c=18,
            temperature_max_c=27,
            precipitation_mm=-1,
            source="open-meteo",
            collected_at=datetime.now(UTC),
        )


def test_climate_contract_rejects_inverted_temperature_range() -> None:
    item = ClimateDailyContract(
        municipality_ibge="3302403",
        observed_on=date(2026, 8, 7),
        temperature_min_c=30,
        temperature_max_c=20,
        precipitation_mm=0,
        source="open-meteo",
        collected_at=datetime.now(UTC),
    )
    with pytest.raises(ValueError, match="temperature_min_c"):
        validate_contract(item)


def test_zarc_contract_rejects_inverted_window() -> None:
    item = ZarcWindowContract(
        municipality_ibge="3302403",
        crop="milho",
        soil_class="2",
        cycle_group="I",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 9, 1),
        source_document="MAPA/ZARC",
        source_version="2026-08",
    )
    with pytest.raises(ValueError, match="start_date"):
        validate_contract(item)
