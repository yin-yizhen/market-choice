export type LocationCandidate = {
  name: string;
  address: string;
  city: string;
  district: string;
  latitude: number;
  longitude: number;
};

export type BusinessInput = {
  business_type: string;
  average_ticket: number;
  store_area: number;
  employee_count: number;
  target_customer: string;
  opening_hours: string;
  differentiation: string;
};

export type FinancialInput = {
  monthly_rent: number;
  property_fee: number;
  transfer_fee: number;
  deposit: number;
  renovation_cost: number;
  equipment_cost: number;
  labor_cost: number;
  utilities_cost: number;
  raw_material_cost: number;
  platform_commission: number;
  marketing_cost: number;
  license_cost: number;
  working_capital: number;
  expected_monthly_revenue: number;
  gross_margin: number;
};

export type AnalysisResponse = {
  data_notes: string[];
  poi_rings: Array<{
    radius: number;
    total: number;
    categories: Record<string, number>;
    competitor_count: number;
    complementary_count: number;
  }>;
  financials: Record<string, number | string | null>;
  scoring: {
    overall_score: number;
    scores: Record<string, number>;
    risk_factors: string[];
    method_note?: string;
  };
  report: {
    source: 'llm' | 'fallback';
    markdown: string;
    ai_error: string | null;
  };
};
