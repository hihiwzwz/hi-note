export interface SearchEntry {
  id: string;
  title: string;
  description: string;
  body: string;
}

export function searchPosts(entries: SearchEntry[], query: string) {
  const words = [...new Set(query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean))];
  if (!words.length) return [];
  return entries.map((entry, index) => {
    const title = entry.title.toLocaleLowerCase();
    const description = entry.description.toLocaleLowerCase();
    const body = entry.body.toLocaleLowerCase();
    let score = 0;
    for (const word of words) {
      if (title.includes(word)) score += 10;
      else if (description.includes(word)) score += 5;
      else if (body.includes(word)) score += 1;
      else return null;
    }
    return { entry, index, score };
  }).filter((result): result is NonNullable<typeof result> => result !== null)
    .sort((a, b) => b.score - a.score || a.index - b.index)
    .map(({ entry }) => entry);
}

export function excerpt(entry: SearchEntry, query: string) {
  const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  if (words.some((word) => entry.description.toLocaleLowerCase().includes(word))) return entry.description;
  const positions = words.map((word) => entry.body.toLocaleLowerCase().indexOf(word)).filter((index) => index >= 0);
  if (!positions.length) return entry.description;
  const start = Math.max(0, Math.min(...positions) - 35);
  const end = Math.min(entry.body.length, start + 150);
  return `${start ? '…' : ''}${entry.body.slice(start, end)}${end < entry.body.length ? '…' : ''}`;
}
