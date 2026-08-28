window.BB610_ANALYTICS_CONFIG = Object.freeze({
  enabled: true,
  debug: false,
  site: 'market.bb610.com.ua',
  currency: 'UAH',
  tagManager: {
    enabled: false,
    containerId: null,
    dataLayerName: 'dataLayer'
  },
  consent: {
    required: true,
    defaultState: {
      analytics_storage: 'denied',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied'
    },
    waitForUpdateMs: 500
  },
  providers: {
    ga4: { enabled: false, measurementId: null },
    googleAds: { enabled: false, conversionId: null },
    metaPixel: { enabled: false, pixelId: null },
    metaCapi: { enabled: false, endpoint: null }
  }
});
