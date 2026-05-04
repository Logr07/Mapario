export const categoryGroups = [
  {
    value: "residential",
    label: "Obytné",
    subcategories: [
      { value: "family_house", label: "Rodinný dům" },
      { value: "villa", label: "Vila" },
      { value: "apartment_building", label: "Bytový dům" },
      { value: "recreational_building", label: "Rekreační stavba" },
      { value: "historical_residence", label: "Historické sídlo" },
      { value: "other_residential", label: "Jiný obytný typ" },
    ],
  },
  {
    value: "industrial",
    label: "Průmysl",
    subcategories: [
      { value: "manufacturing", label: "Výroba" },
      { value: "energy", label: "Energetika" },
      { value: "chemical", label: "Chemický" },
      { value: "mining", label: "Těžba" },
      { value: "storage", label: "Skladování" },
      { value: "agriculture", label: "Zemědělství" },
      { value: "other_industrial", label: "Jiný průmyslový typ" },
    ],
  },
  {
    value: "public",
    label: "Veřejné",
    subcategories: [
      { value: "healthcare", label: "Zdravotnictví" },
      { value: "education", label: "Školství" },
      { value: "sacral", label: "Sakrální" },
      { value: "public_administration", label: "Veřejná správa" },
      { value: "culture_sport", label: "Kultura / sport" },
      { value: "transport", label: "Doprava" },
      { value: "other_public", label: "Jiný veřejný typ" },
    ],
  },
  {
    value: "commercial",
    label: "Komerční",
    subcategories: [
      { value: "accommodation", label: "Ubytování" },
      { value: "gastronomy", label: "Gastronomie" },
      { value: "retail", label: "Obchod" },
      { value: "services", label: "Služby" },
      { value: "administration", label: "Administrativa" },
      { value: "other_commercial", label: "Jiný komerční typ" },
    ],
  },
  {
    value: "military",
    label: "Vojenské",
    subcategories: [
      { value: "barracks_accommodation", label: "Kasárna / ubytování" },
      { value: "military_storage", label: "Skladový areál" },
      { value: "technical_facilities", label: "Technické zázemí" },
      { value: "defensive_structure", label: "Obranná stavba" },
      { value: "other_military", label: "Jiný vojenský typ" },
    ],
  },
  {
    value: "other",
    label: "Ostatní",
    subcategories: [{ value: "other", label: "Ostatní" }],
  },
];

export const categoryOptions = categoryGroups.map(({ value, label }) => ({ value, label }));

export const subcategoryOptions = categoryGroups.flatMap((group) =>
  group.subcategories.map((subcategory) => ({
    ...subcategory,
    category: group.value,
    label: `${group.label}: ${subcategory.label}`,
  })),
);

export const statusOptions = [
  { value: "unsorted", label: "Neroztříděno" },
  { value: "unverified", label: "Neověřeno" },
  { value: "functional", label: "Funkční" },
  { value: "nonfunctional", label: "Nefunkční" },
  { value: "documented", label: "Zdokumentováno" },
  { value: "visited", label: "Navštíveno" },
  { value: "vanished", label: "Zaniklé" },
];

export const ratingOptions = [
  { value: "unrated", label: "Nehodnoceno" },
  { value: "1", label: "1" },
  { value: "2", label: "2" },
  { value: "3", label: "3" },
  { value: "4", label: "4" },
  { value: "5", label: "5" },
];

export const accessibilityOptions = [
  { value: "unknown", label: "Neznámá" },
  { value: "freely_accessible", label: "Volně přístupná" },
  { value: "by_arrangement", label: "Přístupná po domluvě" },
  { value: "inaccessible", label: "Nepřístupná" },
];

/**
 * Vrátí pole podkategorií pro danou kategorii.
 * Pokud kategorie neexistuje, vrátí podkategorie poslední skupiny ("Ostatní").
 *
 * @param {string} category - Hodnota kategorie (např. "industrial").
 * @returns {{ value: string, label: string }[]}
 */
export function subcategoriesForCategory(category) {
  return categoryGroups.find((group) => group.value === category)?.subcategories || categoryGroups.at(-1).subcategories;
}
