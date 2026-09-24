window.BB610_ANALYTICS_CONFIG = Object.freeze({
  enabled: true,
  debug: false,
  site: 'market.bb610.com.ua',
  currency: 'UAH',
  tagManager: {
    enabled: true,
    containerId: 'GTM-MF8PZJCJ',
    dataLayerName: 'dataLayer'
  },
  consent: {
    required: true,
    defaultState: {
      analytics_storage: 'granted',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied'
    },
    waitForUpdateMs: 500
  },
  providers: {
    ga4: { enabled: true, measurementId: 'G-QWG1K17HC3' },
    googleAds: { enabled: true, conversionId: 'AW-73873342320', conversionLabel: null },
    metaPixel: { enabled: true, pixelId: '1103668908981910' },
    metaCapi: { enabled: true, endpoint: 'https://api.market.bb610.com.ua/api/v1/analytics/meta-capi' }
  }
});
