window.BB610_COMMERCE_CONFIG = Object.freeze({
  apiBaseUrl: null,
  apiVersion: 'v1',
  endpoints: {
    createOrder: '/api/v1/orders',
    getOrder: '/api/v1/orders/{orderId}',
    paymentMethods: '/api/v1/payments/methods'
  },
  checkoutMode: 'backend-required',
  paymentMode: 'backend-directed',
  successPath: '/order/success/',
  requestTimeoutMs: 12000
});
