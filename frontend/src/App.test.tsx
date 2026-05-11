import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';

type MapClickHandler = (event: { lnglat: { getLng: () => number; getLat: () => number } }) => void;

function installFakeAmap() {
  let clickHandler: MapClickHandler | undefined;
  const setZoomAndCenter = vi.fn();
  const clearMap = vi.fn();
  const marker = vi.fn();
  const circle = vi.fn();

  class FakeMap {
    setZoomAndCenter = setZoomAndCenter;
    clearMap = clearMap;
    destroy = vi.fn();
    on(event: 'click', handler: MapClickHandler) {
      if (event === 'click') clickHandler = handler;
    }
  }

  class FakeMarker {
    constructor(options: unknown) {
      marker(options);
    }
  }

  class FakeCircle {
    constructor(options: unknown) {
      circle(options);
    }
  }

  window.AMap = {
    Map: FakeMap as never,
    Marker: FakeMarker as never,
    Circle: FakeCircle as never,
  };

  return {
    get clickHandler() {
      return clickHandler;
    },
    setZoomAndCenter,
    clearMap,
    marker,
    circle,
  };
}

function mockSuccessFetch() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
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
    if (url.startsWith('/api/reverse-geocode')) {
      return Response.json({
        name: '上海市静安区南京西路100号',
        address: '上海市静安区南京西路100号',
        city: '上海',
        district: '静安区',
        latitude: 31.2,
        longitude: 121.5,
      });
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
      research_bundle: {
        provider: 'dashscope',
        queries: ['上海 南京西路 城市更新 商业 改造'],
        sources: [
          {
            id: 'S1',
            title: '南京西路街区城市更新规划',
            url: 'https://example.gov.cn/plan',
            search_query: '上海 南京西路 城市更新 商业 改造',
            confidence: 0.66,
            category: '街区发展计划',
            snippet: '道路提升和商业更新',
          },
        ],
        categories: {
          街区发展计划: {
            status: 'supported',
            summary: '公开资料显示周边有道路提升和商业更新。',
            confidence: 0.82,
            sources: [
              {
                id: 'S1',
                title: '南京西路街区城市更新规划',
                url: 'https://example.gov.cn/plan',
                search_query: '上海 南京西路 城市更新 商业 改造',
                confidence: 0.66,
                category: '街区发展计划',
                snippet: '道路提升和商业更新',
              },
            ],
          },
        },
      },
      scoring: {
        overall_score: 72,
        scores: { 目标人流: 76, 租金合理性: 70 },
        risk_factors: ['竞品密度偏高'],
      },
      report: {
        source: 'fallback',
        markdown: '## 关键结论\n这个点位有机会，但需要控制租金。\n## 联网调研证据\n- 南京西路街区城市更新规划',
        ai_error: 'LLM_API_KEY is not configured',
      },
    });
  });
}

describe('App', () => {
  afterEach(() => {
    document.querySelectorAll('script[data-amap-loader="true"]').forEach((script) => script.remove());
    delete window.AMap;
    delete window._AMapSecurityConfig;
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('validates required location before analysis', async () => {
    render(<App />);

    await userEvent.click(screen.getByRole('button', { name: '生成选址报告' }));

    expect(await screen.findByText('请先搜索位置，并在地图上点击确认一个铺位点')).toBeInTheDocument();
  });

  it('moves to search result, lets map click select point, and submits analysis', async () => {
    const amap = installFakeAmap();
    const fetchMock = mockSuccessFetch();

    render(<App />);
    await waitFor(() => expect(amap.clickHandler).toBeDefined());

    await userEvent.type(screen.getByLabelText('搜索位置'), '南京西路');
    await userEvent.click(screen.getByRole('button', { name: '搜索' }));

    expect(await screen.findByRole('button', { name: /定位到 上海市静安区南京西路/ })).toBeInTheDocument();
    await waitFor(() => expect(amap.setZoomAndCenter).toHaveBeenCalledWith(15, [121.4737, 31.2304]));
    expect(screen.getByLabelText('搜索位置')).toHaveValue('上海市静安区南京西路');

    await act(async () => {
      amap.clickHandler?.({ lnglat: { getLat: () => 31.2, getLng: () => 121.5 } });
    });

    await waitFor(() => expect(screen.getByLabelText('搜索位置')).toHaveValue('上海市静安区南京西路100号'));
    expect(amap.marker).toHaveBeenCalled();
    expect(amap.circle.mock.calls.length).toBeGreaterThanOrEqual(3);

    await userEvent.clear(screen.getByLabelText('月租金'));
    await userEvent.type(screen.getByLabelText('月租金'), '30000');
    await userEvent.click(screen.getByRole('button', { name: '生成选址报告' }));

    expect(await screen.findByText('综合得分 72')).toBeInTheDocument();
    expect(screen.getAllByText('联网调研证据').length).toBeGreaterThan(0);
    expect(screen.getByText('南京西路街区城市更新规划')).toHaveAttribute('href', 'https://example.gov.cn/plan');
    expect(fetchMock).toHaveBeenCalledWith('/api/analyze-location', expect.objectContaining({ method: 'POST' }));
  });

  it('shows the research loading state immediately after submit', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise<Response>(() => {}));

    render(<App />);
    await userEvent.click(screen.getByRole('button', { name: '使用示例点位' }));
    await userEvent.click(screen.getByRole('button', { name: '生成选址报告' }));

    expect(screen.getByRole('button', { name: /正在联网检索公开资料/ })).toBeDisabled();
  });

  it('shows a clear research failure error', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      Response.json({ detail: '联网调研失败：DASHSCOPE_API_KEY is not configured' }, { status: 503 }),
    );

    render(<App />);
    await userEvent.click(screen.getByRole('button', { name: '使用示例点位' }));
    await userEvent.click(screen.getByRole('button', { name: '生成选址报告' }));

    expect(await screen.findByText('联网调研失败：DASHSCOPE_API_KEY is not configured')).toBeInTheDocument();
  });

  it('configures AMap security code before loading the map script', async () => {
    vi.stubEnv('VITE_AMAP_JS_API_KEY', 'test-map-key');
    vi.stubEnv('VITE_AMAP_SECURITY_JS_CODE', 'test-security-code');

    render(<App />);
    await userEvent.click(screen.getByRole('button', { name: '使用示例点位' }));

    const script = document.querySelector<HTMLScriptElement>('script[data-amap-loader="true"]');
    expect(window._AMapSecurityConfig).toEqual({ securityJsCode: 'test-security-code' });
    expect(script?.src).toContain('key=test-map-key');
  });

  it('uses a map host class that does not collide with AMap internals', async () => {
    vi.stubEnv('VITE_AMAP_JS_API_KEY', 'test-map-key');

    render(<App />);
    await userEvent.click(screen.getByRole('button', { name: '使用示例点位' }));

    expect(document.querySelector('.amap-host')).toBeInTheDocument();
    expect(document.querySelector('.map-canvas > .amap-layer')).not.toBeInTheDocument();
  });
});
