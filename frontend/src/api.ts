import type { AnalysisResponse, BusinessInput, FinancialInput, LocationCandidate } from './types';

export async function geocode(keyword: string, city: string): Promise<LocationCandidate[]> {
  const params = new URLSearchParams({ keyword, city });
  const response = await fetch(`/api/geocode?${params.toString()}`);
  if (!response.ok) {
    const message = await readError(response);
    throw new Error(message || '位置搜索失败');
  }
  return response.json();
}

export async function analyzeLocation(input: {
  location: LocationCandidate & { district_note?: string };
  business: BusinessInput;
  financial: FinancialInput;
}): Promise<AnalysisResponse> {
  const response = await fetch('/api/analyze-location', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      location: {
        address: input.location.address,
        city: input.location.city,
        latitude: input.location.latitude,
        longitude: input.location.longitude,
        district_note: input.location.district_note ?? '',
      },
      business: input.business,
      financial: input.financial,
    }),
  });
  if (!response.ok) {
    const message = await readError(response);
    throw new Error(message || '分析失败');
  }
  return response.json();
}

async function readError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    return payload.detail ?? payload.message ?? '';
  } catch {
    return '';
  }
}
