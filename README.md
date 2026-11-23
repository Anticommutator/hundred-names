# The Hundred Names

If you learned a country's 100 most common first names, what share of its people could you call by name?

**Live page:** https://anticommutator.github.io/hundred-names/

An interactive table and world map for 140 countries plus the world:

- coverage of the top 100 first names: everyone, men and women separately
- coverage of the top 100 surnames
- the top 10 / 25 / 50 / 100 men's and women's names per country (click a country)
- hover a name for its spellings and their shares; click it for a name page with a map of where it is most common
- a quiz: guess a name from its map, four options, with easy / medium / hard levels
- for each name, the 5 names with the most similar geography
- an option to merge spelling variants (Mohammed/Muhammad/Mohamed, Sergey/Sergei, José/Jose)
- people per name, number of distinct names, share of women in the records
- an unweighted country average next to the population-weighted world figure

## Method

Counts come from the per-country forename and surname rankings on [Forebears](https://forebears.io), retrieved November 2026.
Top-100 coverage = summed incidence of the 100 most frequent names ÷ Forebears' total for that country
(distinct names × people per name). Titles and non-names (e.g. *Nushi* "Ms.", *Masmaat* "Mrs.", *Sri/Smt*) are removed before ranking.

Forebears gives each name a gender percentage but not which gender it refers to; the majority gender was assigned
from name knowledge in each country's context, so unisex names carry some uncertainty.
Countries whose source data does not describe the population (very short lists, expat-dominated records,
names split into syllables) are left out and listed on the page with the reason.

People with several given names (José María, Anna Maria) count once per name, which inflates
Spain, Italy, Portugal and Latin America somewhat.

## Files

- `index.html` — the whole page; data is embedded
- `names.json` — per-country top-100 name lists, as listed and with spellings merged (loaded when a country is opened)
- `ni/*.json` — cross-country name index (sharded by first letter), loaded when a name is clicked
- `quiz.json` — 400 widespread name families with their per-country shares, for the quiz
- `countries-110m.json` — country shapes from [world-atlas](https://github.com/topojson/world-atlas) (Natural Earth, public domain)

## Name distance

Each name family (all spellings, both sexes) is a vector over countries: the square root of the share of people carrying it in each country.
The square root keeps a name's single stronghold from dominating (with plain shares, Mohammed's neighbours were Bangladeshi names because 39% of Bangladeshi men carry it; with square roots they are Ahmed, Ali and Noor). Dividing each country by its total or by its top name was also tested and worked less well.
After L2 normalisation, the distance between two names is the Euclidean distance between their vectors
(0 = identical map, √2 ≈ 1.41 = no overlap); the "similarity" shown is the cosine, 1 − d²/2.
Quiz difficulty sets a minimum distance x between the answer and every wrong option
(easy 1.3, medium 0.9, hard 0.35); wrong options are drawn from the names closest to the answer that still clear x
(medium: the 25 closest, hard: the 10 closest; easy: any).
