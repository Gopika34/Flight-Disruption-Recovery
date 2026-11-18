
from app.schemas.capabilities import (
    EmergencyDutyOfCareResponse,
    EmergencyStayRequest,
    HotelOffer,
    TransportOption,
)
from app.services.airports import get_airport
from app.services.hotels import cab_estimate_inr


CURATED_AIRPORT_HOTELS: dict[str, list[HotelOffer]] = {
    "DEL": [
        HotelOffer(
            id="del-niranta",
            name="Holiday Inn New Delhi International Airport",
            tier="Comfort Suites",
            distance_km=2.8,
            estimated_transit_minutes=10,
            price_per_night_inr=4200,
            free_airport_shuttle=True,
            address="Asset Area 12, Hospitality District, Aerocity, New Delhi 110037",
            phone="+91-11-4222-2000",
            booking_url="https://www.ihg.com/holidayinn/hotels/us/en/new-delhi/delap/hoteldetail",
            verified_available=False,
            availability_status="unverified_directory_listing",
            listing_source="curated_directory",
            price_status="estimated_not_live",
        ),
        HotelOffer(
            id="del-radisson",
            name="Radisson Blu Plaza Delhi Airport",
            tier="Grand Residency",
            distance_km=3.5,
            estimated_transit_minutes=12,
            price_per_night_inr=6800,
            free_airport_shuttle=True,
            address="National Highway 8, Mahipalpur, New Delhi 110037",
            phone="+91-11-2677-9191",
            booking_url="https://www.radissonhotels.com",
            verified_available=False,
            availability_status="unverified_directory_listing",
            listing_source="curated_directory",
            price_status="estimated_not_live",
        ),
        HotelOffer(
            id="del-ibis",
            name="ibis New Delhi Aerocity",
            tier="Budget Stay",
            distance_km=2.4,
            estimated_transit_minutes=8,
            price_per_night_inr=3100,
            free_airport_shuttle=False,
            address="Asset No 9, Hospitality District, Aerocity, New Delhi 110037",
            phone="+91-11-4302-0202",
            booking_url="https://all.accor.com/hotel/7448/index.en.shtml",
            verified_available=False,
            availability_status="unverified_directory_listing",
            listing_source="curated_directory",
            price_status="estimated_not_live",
        ),
    ],
    "BOM": [
        HotelOffer(
            id="bom-niranta",
            name="Niranta Airport Transit Hotel & Lounge",
            tier="Comfort Suites",
            distance_km=0.4,
            estimated_transit_minutes=4,
            price_per_night_inr=4800,
            free_airport_shuttle=True,
            address="Terminal 2, Chhatrapati Shivaji Maharaj International Airport, Mumbai 400099",
            phone="+91-22-6725-0000",
            booking_url="https://www.nirantahotels.com",
            verified_available=False,
            availability_status="unverified_directory_listing",
            listing_source="curated_directory",
            price_status="estimated_not_live",
        ),
        HotelOffer(
            id="bom-orchid",
            name="The Orchid Hotel Mumbai Airport",
            tier="Grand Residency",
            distance_km=1.8,
            estimated_transit_minutes=8,
            price_per_night_inr=6400,
            free_airport_shuttle=True,
            address="70-C, Nehru Road, Near Domestic Airport, Vile Parle East, Mumbai 400099",
            phone="+91-22-2616-4040",
            booking_url="https://www.orchidhotel.com",
            verified_available=False,
            availability_status="unverified_directory_listing",
            listing_source="curated_directory",
            price_status="estimated_not_live",
        ),
        HotelOffer(
            id="bom-astoria",
            name="Bawa International Hotel Mumbai Airport",
            tier="Budget Stay",
            distance_km=1.5,
            estimated_transit_minutes=6,
            price_per_night_inr=2900,
            free_airport_shuttle=False,
            address="Nehru Road, Near Domestic Airport, Vile Parle East, Mumbai 400099",
            phone="+91-22-2611-3636",
            booking_url="https://www.hotelbawainternational.com",
            verified_available=False,
            availability_status="unverified_directory_listing",
            listing_source="curated_directory",
            price_status="estimated_not_live",
        ),
    ],
    "BLR": [
        HotelOffer(
            id="blr-taj",
            name="Taj Bangalore Kempegowda Airport",
            tier="Grand Residency",
            distance_km=0.3,
            estimated_transit_minutes=4,
            price_per_night_inr=7800,
            free_airport_shuttle=True,
            address="Kempegowda International Airport, Devanahalli, Bengaluru 560300",
            phone="+91-80-6600-3300",
            booking_url="https://www.tajhotels.com",
            verified_available=False,
            availability_status="unverified_directory_listing",
            listing_source="curated_directory",
            price_status="estimated_not_live",
        ),
        HotelOffer(
            id="blr-bloom",
            name="Bloomrooms @ Kempegowda Airport",
            tier="Budget Stay",
            distance_km=5.2,
            estimated_transit_minutes=12,
            price_per_night_inr=2700,
            free_airport_shuttle=False,
            address="Near Airport Toll Plaza, Devanahalli, Bengaluru 560300",
            phone="+91-80-4667-0000",
            booking_url="https://bloomrooms.com",
            verified_available=False,
            availability_status="unverified_directory_listing",
            listing_source="curated_directory",
            price_status="estimated_not_live",
        ),
    ],
}


def search_emergency_stay_and_transport(req: EmergencyStayRequest) -> EmergencyDutyOfCareResponse:
    iata = req.airport_code.upper()
    airport = get_airport(iata)
    airport_name = airport.get("name", iata) if airport else iata

    # DGCA CAR Section 3, Series M, Part IV, Para 3.4.3 & 3.8.1 (b):
    # Mandatory duty-of-care hotel accommodation and transfers applies when:
    # 1. Overnight delay occurs, OR
    # 2. Delay exceeds 6 hours between 20:00 and 09:00, OR
    # 3. Flight delay exceeds 24 hours.
    start_minutes = None
    if req.delay_start_local_time:
        hh, mm = (int(part) for part in req.delay_start_local_time.split(":"))
        start_minutes = hh * 60 + mm
    delay_starts_in_night_window = (
        start_minutes is not None and (start_minutes >= 20 * 60 or start_minutes < 9 * 60)
    )
    duty_mandated = bool(
        req.is_overnight
        or (req.delay_hours > 6.0 and delay_starts_in_night_window)
        or req.delay_hours > 24.0
    )
    clause = "DGCA CAR Section 3, Series M, Part IV, Para 3.4.3 & Para 3.8.1 (b)"

    # Curated listings are discovery references only. We have no live hotel
    # inventory provider, so do not fabricate addresses, phone numbers,
    # availability confirmations or listings for unknown airports.
    hotels: list[HotelOffer] = list(CURATED_AIRPORT_HOTELS.get(iata, []))

    avg_km = hotels[0].distance_km if hotels else 6.0
    cab_fare = cab_estimate_inr(avg_km)

    transport_options = [
        TransportOption(
            mode="Complimentary Airline / Hotel Transit Shuttle",
            estimated_fare_inr=0,
            estimated_duration_minutes=int(avg_km * 2.5),
            pickup_point="Ask the operating airline or hotel to confirm the current shuttle pickup point.",
            booking_link_or_instructions="Show hotel reservation or airline duty manager voucher at shuttle desk.",
        ),
        TransportOption(
            mode="Authorized Airport Prepaid Taxi",
            estimated_fare_inr=cab_fare,
            estimated_duration_minutes=int(avg_km * 2.2),
            pickup_point="Use the airport-authorized prepaid taxi counter; confirm its current location on arrival.",
            booking_link_or_instructions="Collect fixed-rate physical receipt before boarding taxi.",
        ),
        TransportOption(
            mode="Ride-Hailing Cab (Uber / Ola / Rapido)",
            estimated_fare_inr=int(cab_fare * 1.15),
            estimated_duration_minutes=int(avg_km * 2.0),
            pickup_point="Use the pickup point currently shown in the official ride-hailing app.",
            booking_link_or_instructions="Book via Uber or Ola app entering terminal gate pickup.",
        ),
    ]

    airline = req.airline_name or "Operating Airline"

    if duty_mandated:
        counter_script = (
            f"Good evening. My flight disruption has resulted in an overnight/qualifying long delay. "
            f"{airline}, based on the supplied facts, please assess my entitlement under {clause} and arrange any "
            f"required accommodation and airport transfers. Please provide the decision and any voucher in writing."
        )
    else:
        counter_script = (
            f"My flight has been delayed by {req.delay_hours:.1f} hours. Please confirm the applicable "
            "DGCA duty-of-care provision for my flight and provide written details of meals, accommodation "
            "or transfers available in my circumstances."
        )

    if duty_mandated:
        self_booking_claim = (
            f"DRAFT REIMBURSEMENT REQUEST — DUTY OF CARE\n"
            f"To: Nodal Officer, {airline}\nAirport: {iata} ({airport_name})\n\n"
            "I request review of reasonable documented accommodation and transport expenses incurred "
            "during the disruption. Please assess the applicable DGCA duty-of-care provisions and the "
            "receipts attached, and provide a written decision. This draft does not guarantee reimbursement.\n"
        )
    else:
        self_booking_claim = (
            "A statutory hotel/transport reimbursement demand has not been prepared because the supplied "
            "facts do not establish the relevant duty-of-care trigger. Confirm the timing and circumstances "
            "with the airline before making a statutory reimbursement claim."
        )

    statement = (
        "DUTY-OF-CARE INDICATOR: Based on the supplied overnight/timing facts, the duty-of-care provisions "
        "may apply. Ask the operating airline to assess the circumstances and provide its decision in writing. "
        "Hotel listings below are directory references only; availability and prices are not live-verified."
        if duty_mandated
        else ("The supplied facts do not establish the overnight/qualifying night-window/over-24-hour "
              "hotel duty-of-care trigger. If the delay exceeds six hours, provide the local delay start time "
              "to assess the night-window condition. Other care obligations may still apply.")
    )

    return EmergencyDutyOfCareResponse(
        airport_code=iata,
        duty_of_care_mandated=duty_mandated,
        statutory_clause=clause,
        airline_liability_statement=statement,
        hotels=hotels,
        transport=transport_options,
        counter_demand_script=counter_script,
        self_booking_claim_template=self_booking_claim,
    )
