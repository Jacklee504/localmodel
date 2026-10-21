/** Normalise a raw deal record into the shape the matcher expects. */
export interface RawDeal {
  title?: unknown;
  company?: unknown;
  amount?: unknown;
  url?: unknown;
}

export interface NormalDeal {
  title: string;
  company: string;
  amount: number;
  url: string;
}

export function normaliseDeal(raw: RawDeal): NormalDeal {
  return {
    title: String(raw.title ?? ''),
    company: String(raw.company ?? ''),
    amount: Number(raw.amount ?? 0),
    url: String(raw.url ?? ''),
  };
}
