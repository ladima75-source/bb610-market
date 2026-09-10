(()=>{
  'use strict';
  const nativeFetch = window.fetch.bind(window);
  window.fetch = (input, init={}) => {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    if (url.startsWith('https://api.market.bb610.com.ua/api/v1/admin/')) {
      init = {...init, cache:'no-store'};
    }
    return nativeFetch(input, init);
  };
})();
