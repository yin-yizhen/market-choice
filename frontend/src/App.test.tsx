import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import App from './App';

describe('App', () => {
  it('validates required location before analysis', async () => {
    render(<App />);

    await userEvent.click(screen.getByRole('button', { name: '生成选址报告' }));

    expect(await screen.findByText('请先搜索并选择一个位置')).toBeInTheDocument();
  });

  it('renders selected location rings and submits an analysis request', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.startsWith('/api/geocode')) {
        return Response.json([
          {
            name: '上海市静安区南京西路',
            address: '上海市静安区南京西路',
            city: '上海',
            district: '静安区',
            latitude: 31.2304,
            longitude: 121.4737,
          },
        ]);
      }
      return Response.json({
        data_notes: ['POI 数据来自高德地图 Web 服务。'],
        poi_rings: [
          { radius: 500, total: 42, categories: { food: 12 }, competitor_count: 5, complementary_count: 18 },
          { radius: 1000, total: 120, categories: { office: 20 }, competitor_count: 16, complementary_count: 52 },
          { radius: 3000, total: 520, categories: { retail: 80 }, competitor_count: 42, complementary_count: 180 },
        ],
        financials: {
          break_even_revenue: 160000,
          survival_months_worst_case: 4.5,
          cash_pressure_level: 'medium',
        },
        scoring: {
          overall_score: 72,
          scores: { 目标人流: 76, 租金合理性: 70 },
          risk_factors: ['竞品密度偏高'],
        },
        report: {
          source: 'fallback',
          markdown: '## 关键结论\n这个点位有机会，但需要控制租金。',
          ai_error: 'LLM_API_KEY is not configured',
        },
      });
    });

    render(<App />);
    await userEvent.type(screen.getByLabelText('搜索位置'), '南京西路');
    await userEvent.click(screen.getByRole('button', { name: '搜索' }));
    await userEvent.click(await screen.findByRole('button', { name: /选择 上海市静安区南京西路/ }));

    expect(screen.getByText('500m')).toBeInTheDocument();
    expect(screen.getByText('1km')).toBeInTheDocument();
    expect(screen.getByText('3km')).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText('月租金'));
    await userEvent.type(screen.getByLabelText('月租金'), '30000');
    await userEvent.click(screen.getByRole('button', { name: '生成选址报告' }));

    expect(await screen.findByText('综合得分 72')).toBeInTheDocument();
    expect(screen.getByText('竞品密度偏高')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/analyze-location', expect.objectContaining({ method: 'POST' }));
  });
});
