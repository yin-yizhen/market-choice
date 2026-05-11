/// <reference types="vite/client" />

type AMapLngLat = [number, number];

type AMapCircleOptions = {
  center: AMapLngLat;
  radius: number;
  map: unknown;
  strokeColor: string;
  strokeOpacity: number;
  strokeWeight: number;
  fillOpacity: number;
  fillColor: string;
};

type AMapMapClickEvent = {
  lnglat: {
    getLng: () => number;
    getLat: () => number;
  };
};

type AMapMapInstance = {
  destroy: () => void;
  setZoomAndCenter: (zoom: number, center: AMapLngLat) => void;
  clearMap: () => void;
  on: (event: 'click', handler: (event: AMapMapClickEvent) => void) => void;
};

declare global {
  interface Window {
    _AMapSecurityConfig?: {
      securityJsCode: string;
    };
    AMap?: {
      Map: new (
        element: HTMLElement,
        options: { zoom: number; center: AMapLngLat; resizeEnable: boolean },
      ) => AMapMapInstance;
      Marker: new (options: { position: AMapLngLat; map: unknown }) => unknown;
      Circle: new (options: AMapCircleOptions) => unknown;
    };
  }
}

export {};
