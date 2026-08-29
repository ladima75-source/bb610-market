window.BB610_DELIVERY_CONFIG = Object.freeze({
  providers: {
    pickup_dnipro: {label:'Самовивіз у Дніпрі',service:'pickup'},
    delivery_dnipro: {label:'Доставка по Дніпру',service:'courier'},
    nova_poshta: {label:'Нова пошта',services:['branch','locker']},
    ukrposhta: {label:'Укрпошта',services:['branch']}
  },
  lookupMinChars: 2,
  requestTimeoutMs: 10000
});
