from pydantic import BaseModel, Field


class LocationInput(BaseModel):
    address: str
    city: str = ""
    latitude: float
    longitude: float
    district_note: str = ""


class BusinessInput(BaseModel):
    business_type: str
    average_ticket: float = Field(default=30, ge=0)
    store_area: float = Field(default=80, ge=0)
    employee_count: int = Field(default=3, ge=0)
    target_customer: str = ""
    opening_hours: str = "09:00-22:00"
    differentiation: str = ""


class FinancialInput(BaseModel):
    monthly_rent: float = Field(default=0, ge=0)
    other_investment_total: float = Field(default=0, ge=0)
    property_fee: float = Field(default=0, ge=0)
    transfer_fee: float = Field(default=0, ge=0)
    deposit: float = Field(default=0, ge=0)
    renovation_cost: float = Field(default=0, ge=0)
    equipment_cost: float = Field(default=0, ge=0)
    labor_cost: float = Field(default=0, ge=0)
    utilities_cost: float = Field(default=0, ge=0)
    raw_material_cost: float = Field(default=0, ge=0)
    platform_commission: float = Field(default=0, ge=0)
    marketing_cost: float = Field(default=0, ge=0)
    license_cost: float = Field(default=0, ge=0)
    working_capital: float = Field(default=0, ge=0)
    expected_monthly_revenue: float | None = Field(default=None, ge=0)
    gross_margin: float = Field(default=0.55, gt=0, le=1)


class AnalyzeRequest(BaseModel):
    location: LocationInput
    business: BusinessInput
    financial: FinancialInput


class GeocodeCandidate(BaseModel):
    name: str
    address: str
    city: str = ""
    district: str = ""
    latitude: float
    longitude: float


class AnalyzeResponse(BaseModel):
    data_notes: list[str]
    poi_rings: list[dict]
    financials: dict
    scoring: dict
    report: dict
