from enum import StrEnum


class LocationStatus(StrEnum):
    UNSORTED = "unsorted"
    UNVERIFIED = "unverified"
    FUNCTIONAL = "functional"
    NONFUNCTIONAL = "nonfunctional"
    DOCUMENTED = "documented"
    VISITED = "visited"
    VANISHED = "vanished"


class LocationCategory(StrEnum):
    RESIDENTIAL = "residential"
    INDUSTRIAL = "industrial"
    PUBLIC = "public"
    COMMERCIAL = "commercial"
    MILITARY = "military"
    OTHER = "other"


class LocationSubcategory(StrEnum):
    FAMILY_HOUSE = "family_house"
    VILLA = "villa"
    APARTMENT_BUILDING = "apartment_building"
    RECREATIONAL_BUILDING = "recreational_building"
    HISTORICAL_RESIDENCE = "historical_residence"
    OTHER_RESIDENTIAL = "other_residential"
    MANUFACTURING = "manufacturing"
    ENERGY = "energy"
    CHEMICAL = "chemical"
    MINING = "mining"
    STORAGE = "storage"
    AGRICULTURE = "agriculture"
    OTHER_INDUSTRIAL = "other_industrial"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    SACRAL = "sacral"
    PUBLIC_ADMINISTRATION = "public_administration"
    CULTURE_SPORT = "culture_sport"
    TRANSPORT = "transport"
    OTHER_PUBLIC = "other_public"
    ACCOMMODATION = "accommodation"
    GASTRONOMY = "gastronomy"
    RETAIL = "retail"
    SERVICES = "services"
    ADMINISTRATION = "administration"
    OTHER_COMMERCIAL = "other_commercial"
    BARRACKS_ACCOMMODATION = "barracks_accommodation"
    MILITARY_STORAGE = "military_storage"
    TECHNICAL_FACILITIES = "technical_facilities"
    DEFENSIVE_STRUCTURE = "defensive_structure"
    OTHER_MILITARY = "other_military"
    OTHER = "other"


class LocationRating(StrEnum):
    UNRATED = "unrated"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"


class LocationAccessibility(StrEnum):
    UNKNOWN = "unknown"
    FREELY_ACCESSIBLE = "freely_accessible"
    BY_ARRANGEMENT = "by_arrangement"
    INACCESSIBLE = "inaccessible"


CATEGORY_SUBCATEGORIES = {
    LocationCategory.RESIDENTIAL.value: {
        LocationSubcategory.FAMILY_HOUSE.value,
        LocationSubcategory.VILLA.value,
        LocationSubcategory.APARTMENT_BUILDING.value,
        LocationSubcategory.RECREATIONAL_BUILDING.value,
        LocationSubcategory.HISTORICAL_RESIDENCE.value,
        LocationSubcategory.OTHER_RESIDENTIAL.value,
    },
    LocationCategory.INDUSTRIAL.value: {
        LocationSubcategory.MANUFACTURING.value,
        LocationSubcategory.ENERGY.value,
        LocationSubcategory.CHEMICAL.value,
        LocationSubcategory.MINING.value,
        LocationSubcategory.STORAGE.value,
        LocationSubcategory.AGRICULTURE.value,
        LocationSubcategory.OTHER_INDUSTRIAL.value,
    },
    LocationCategory.PUBLIC.value: {
        LocationSubcategory.HEALTHCARE.value,
        LocationSubcategory.EDUCATION.value,
        LocationSubcategory.SACRAL.value,
        LocationSubcategory.PUBLIC_ADMINISTRATION.value,
        LocationSubcategory.CULTURE_SPORT.value,
        LocationSubcategory.TRANSPORT.value,
        LocationSubcategory.OTHER_PUBLIC.value,
    },
    LocationCategory.COMMERCIAL.value: {
        LocationSubcategory.ACCOMMODATION.value,
        LocationSubcategory.GASTRONOMY.value,
        LocationSubcategory.RETAIL.value,
        LocationSubcategory.SERVICES.value,
        LocationSubcategory.ADMINISTRATION.value,
        LocationSubcategory.OTHER_COMMERCIAL.value,
    },
    LocationCategory.MILITARY.value: {
        LocationSubcategory.BARRACKS_ACCOMMODATION.value,
        LocationSubcategory.MILITARY_STORAGE.value,
        LocationSubcategory.TECHNICAL_FACILITIES.value,
        LocationSubcategory.DEFENSIVE_STRUCTURE.value,
        LocationSubcategory.OTHER_MILITARY.value,
    },
    LocationCategory.OTHER.value: {LocationSubcategory.OTHER.value},
}
