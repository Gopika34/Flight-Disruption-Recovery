from typing import Literal, Optional
from pydantic import BaseModel, Field


class Scenario(BaseModel):
    """Everything the rule engine and tools might need. All optional: the engine
    itself reports which facts are still missing."""
    type: Optional[Literal["cancellation", "delay", "denied_boarding", "downgrading"]] = None
    origin: Optional[str] = Field(None, description="IATA code, e.g. MAA")
    destination: Optional[str] = None
    flight_number: Optional[str] = None
    reason: Optional[str] = None
    notice_hours: Optional[float] = None
    has_contact_info: Optional[bool] = None
    block_time_minutes: Optional[int] = None
    basic_fare: Optional[float] = None
    fuel_charge: Optional[float] = None
    delay_minutes: Optional[int] = None
    checked_in_on_time: Optional[bool] = None
    scheduled_departure: Optional[str] = Field(None, pattern=r"^\d{1,2}:\d{2}$")
    domestic: Optional[bool] = None
    confirmed_booking: Optional[bool] = None
    alternate_departure_delay_minutes: Optional[int] = None
    sector: Optional[Literal["domestic", "international"]] = None
    ticket_amount_including_taxes: Optional[float] = None
    involuntary: Optional[bool] = None
    distance_km: Optional[float] = None

    def facts(self):
        return self.model_dump(exclude_none=True)


class AskIn(BaseModel):
    message: str = Field(min_length=3, max_length=2000)
    known_facts: dict = Field(default_factory=dict)