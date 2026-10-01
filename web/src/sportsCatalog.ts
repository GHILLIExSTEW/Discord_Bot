export type SportCatalogItem = { slug: string; name: string; feed: 'events' | 'nfl' | 'unavailable' }

export const sportsCatalog: SportCatalogItem[] = [
  { slug: 'football', name: 'Football', feed: 'events' },
  { slug: 'basketball', name: 'Basketball', feed: 'events' },
  { slug: 'baseball', name: 'Baseball', feed: 'events' },
  { slug: 'american-football', name: 'American Football', feed: 'nfl' },
  { slug: 'ncaa', name: 'NCAA', feed: 'events' },
  { slug: 'hockey', name: 'Hockey', feed: 'events' },
  { slug: 'rugby', name: 'Rugby', feed: 'events' },
  { slug: 'handball', name: 'Handball', feed: 'events' },
  { slug: 'volleyball', name: 'Volleyball', feed: 'events' },
  { slug: 'cricket', name: 'Cricket', feed: 'unavailable' },
  { slug: 'formula-1', name: 'Formula 1', feed: 'events' },
  { slug: 'cycling', name: 'Cycling', feed: 'unavailable' },
  { slug: 'mma', name: 'MMA', feed: 'events' },
]