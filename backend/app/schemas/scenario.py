import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

DisruptionType = Literal["cancellation", "delay", "denied_boarding", "downgrading"]


class Scenario(BaseModel):
    """Explicit, validated facts used by the deterministic recovery engine."""
    model_config = ConfigDict(extra="forbid")

    type: DisruptionType | None = None
    origin: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    destination: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    flight_number: str | None = Field(default=None, min_length=2, max_length=15)
    reason: str | None = Field(default=None, min_length=2, max_length=64)

    notice_hours: float | None = Field(default=None, ge=0, le=8760)
    has_contact_info: bool | None = None
    extraordinary_circumstances_established: bool | None = None

    block_time_minutes: int | None = Field(default=None, ge=1, le=2000)
    basic_fare: float | None = Field(default=None, ge=0)
    fuel_charge: float | None = Field(default=None, ge=0)

    delay_minutes: int | None = Field(default=None, ge=0, le=100000)
    total_delay_from_published_minutes: int | None = Field(default=None, ge=0, le=100000)
    checked_in_on_time: bool | None = None
    scheduled_departure: str | None = None
    domestic: bool | None = None
    revised_departure_communicated_more_than_24h: bool | None = None

    confirmed_booking: bool | None = None
    overbooking: bool | None = None
    voluntary_surrender: bool | None = None
    connecting_same_ticket: bool | None = None
    final_arrival_delay_minutes: int | None = Field(default=None, ge=0, le=100000)

    alternate_flight_offered: bool | None = None
    acceptable_alternative_or_refund_provided: bool | None = None
    alternate_flight_accepted: bool | None = None
    alternate_departure_delay_minutes: int | None = Field(default=None, ge=0, le=100000)

    sector: Literal["domestic", "international"] | None = None
    ticket_amount_including_taxes: float | None = Field(default=None, ge=0)
    involuntary: bool | None = None
    distance_km: float | None = Field(default=None, ge=0)

    @field_validator("origin", "destination", "flight_number", mode="before")
    @classmethod
    def normalize_codes(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        if isinstance(value, str):
            return re.sub(r"[^a-z0-9_]+", "_", value.strip().lower().replace("-", "_"))
        return value

    @field_validator("scheduled_departure")
    @classmethod
    def validate_departure_time(cls, value):
        if value is not None and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("Time must be in HH:MM 24-hour format")
        return value

    def facts(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


def sanitize_facts(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    clean: dict[str, Any] = {}
    rejected: list[str] = []
    for key, value in raw.items():
        if key not in Scenario.model_fields:
            rejected.append(key)
            continue
        if value is None:
            continue
        try:
            clean.update(Scenario.model_validate({key: value}).facts())
        except ValidationError:
            rejected.append(key)
    return clean, rejected


class AskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=3, max_length=2000)
    session_id: str | None = Field(default=None, min_length=36, max_length=36, pattern=r"^[0-9a-fA-F-]{36}$")
    known_facts: dict[str, Any] = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value):
        if not value.strip():
            raise ValueError("message cannot be blank")
        return value.strip()

    @field_validator("known_facts", mode="before")
    @classmethod
    def validate_known_facts(cls, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("known_facts must be a JSON object")
        return Scenario.model_validate(value).facts()
