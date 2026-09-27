window.BB610_COMMERCE_CONFIG = Object.freeze({
  apiBaseUrl: 'https://api.market.bb610.com.ua',
  apiVersion: 'v1',
  endpoints: {
    createOrder: '/api/v1/orders',
    getOrder: '/api/v1/orders/{orderId}',
    paymentMethods: '/api/v1/payments/methods',
    catalogV5: '/api/v1/catalog/v5'
  },
  checkoutMode: 'backend-required',
  paymentMode: 'backend-directed',
  successPath: '/order/success/',
  requestTimeoutMs: 12000
});
