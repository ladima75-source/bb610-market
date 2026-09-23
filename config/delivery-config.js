window.BB610_DELIVERY_CONFIG = Object.freeze({
  orderRules: Object.freeze({
    minOrderUah: 500,
    freeShippingThresholdUah: 2500,
    freeShippingMaxChargeableWeightKg: 10,
    freeShippingProvider: 'nova_poshta'
  }),
  providers: {
    pickup_dnipro: {label:'Самовивіз у Дніпрі',service:'pickup'},
    delivery_dnipro: {label:'Доставка по Дніпру',service:'courier'},
    nova_poshta: {label:'Нова пошта',services:['branch','locker']},
    ukrposhta: {label:'Укрпошта',services:['branch']}
  },
  lookupMinChars: 2,
  requestTimeoutMs: 10000
});
