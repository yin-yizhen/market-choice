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
  opening_hours: string;
  differentiation: string;
};

export type FinancialInput = {
  monthly_rent: number;
  other_investment_total: number;
};

export type AnalysisResponse = {
  data_notes: string[];
  poi_rings: Array<{
    radius: number;
    total: number;
    categories: Record<string, number>;
    competitor_count: number;
    complementary_count: number;
    declared_count?: number;
    pages_fetched?: number;
    truncated?: boolean;
  }>;
  financials: Record<string, number | string | null>;
  scoring: {
    overall_score: number;
    scores: Record<string, number>;
    risk_factors: string[];
    business_metrics?: Record<string, number | string | null>;
    verification_required?: string[];
    method_note?: string;
  };
  report: {
    source: 'llm' | 'fallback';
    markdown: string;
    ai_error: string | null;
  };
};
