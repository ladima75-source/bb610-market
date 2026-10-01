const LANDINGS = Object.freeze({
  nutrition: {
    title: 'Професійні добрива для рослин — BB610 Market',
    description: 'Професійні добрива для рослин у BB610 Market. Ціни, фасування, характеристики та дані виробника. Доставка по Україні та самовивіз у Дніпрі.',
    h1: 'Професійні добрива для рослин',
    breadcrumb: 'BB610 MARKET / ПРОФЕСІЙНІ ДОБРИВА',
    canonical: 'https://market.bb610.com.ua/catalog.html?category=nutrition',
  },
  biostimulation: {
    title: 'Біостимулятори для рослин — BB610 Market',
    description: 'Біостимулятори для рослин у BB610 Market. Ціни, фасування, характеристики та дані виробника. Доставка по Україні та самовивіз у Дніпрі.',
    h1: 'Біостимулятори для рослин',
    breadcrumb: 'BB610 MARKET / БІОСТИМУЛЯТОРИ',
    canonical: 'https://market.bb610.com.ua/catalog.html?category=biostimulation',
  },
});

class TitleHandler {
  constructor(value){ this.value=value; }
  element(element){ element.setInnerContent(this.value); }
}
class DescriptionHandler {
  constructor(value){ this.value=value; }
  element(element){ element.setAttribute('content', this.value); }
}
class CanonicalHandler {
  constructor(value){ this.value=value; }
  element(element){ element.setAttribute('href', this.value); }
}
class TextHandler {
  constructor(value){ this.value=value; }
  element(element){ element.setInnerContent(this.value); }
}

export default {
  async fetch(request) {
    const url = new URL(request.url);

    // The Worker is deliberately narrow: only the existing catalog URL is intercepted.
    if (url.pathname !== '/catalog.html') {
      return fetch(request);
    }

    const category = url.searchParams.get('category') || '';
    const landing = LANDINGS[category];

    // General catalog and every other category pass through unchanged.
    if (!landing) {
      return fetch(request);
    }

    const originResponse = await fetch(request);
    if (!originResponse.ok) {
      return originResponse;
    }

    const contentType = originResponse.headers.get('content-type') || '';
    if (!contentType.toLowerCase().includes('text/html')) {
      return originResponse;
    }

    const transformed = new HTMLRewriter()
      .on('title', new TitleHandler(landing.title))
      .on('meta[name="description"]', new DescriptionHandler(landing.description))
      .on('link[rel="canonical"]', new CanonicalHandler(landing.canonical))
      .on('[data-default-catalog-hero] .breadcrumbs', new TextHandler(landing.breadcrumb))
      .on('[data-default-catalog-hero] h1', new TextHandler(landing.h1))
      .transform(originResponse);

    // Useful for automated production verification; no SEO semantics depend on it.
    transformed.headers.set('X-BB610-Category-SEO', category);
    transformed.headers.set('Vary', 'Accept-Encoding');
    return transformed;
  },
};
