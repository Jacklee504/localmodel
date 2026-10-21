# Deal matching normalisation

`matching.ts` normalises raw deal records before they are compared. The normalisation is
incomplete: it does not normalise the text that is actually used for comparison.

## Requirements

1. Add an exported function `normaliseText(value: string): string` that:
   - lowercases the input;
   - replaces every run of whitespace with a single space;
   - trims the result.
2. Add an exported function `dealFingerprint(deal: NormalDeal): string` that returns a
   comparison key built from the deal's normalised title and normalised company,
   separated by a single `|`. A deal with no title and no company must return `|`.
3. `normaliseDeal` must apply `normaliseText` to the title and the company, so the
   resulting `title` and `company` are trimmed, lowercased, and have collapsed
   whitespace.
4. `normaliseDeal` must not change how `amount` and `url` are produced.
5. A missing title, company, amount, or url must keep its current behaviour.
6. Do not change the exported type names `RawDeal` and `NormalDeal`.
7. Do not add a dependency.

## Constraints

- TypeScript only, no runtime dependency.
- The file must still compile with `tsc --noEmit` when a `tsconfig.json` is present.
