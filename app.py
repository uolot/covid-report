from collections import namedtuple
from itertools import chain
import json
from typing import Any, Dict, Set

import requests

FROM_WEB = False

CORONA_URL = "https://coronavirus-tracker-api.herokuapp.com/all"
COUNTRY_CODE_URL = "https://restcountries.eu/rest/v2/alpha/"
COUNTRY_NAME_URL = "https://restcountries.eu/rest/v2/name/"

COVID_FILE = "data/covid.json"
COUNTRIES_FILE = "data/countries.json"


def save_data(data: Any, filename: str):
    with open(filename, "wt") as f:
        json.dump(data, f)


def load_data(filename: str) -> Any:
    with open(filename, "rt") as f:
        return json.load(f)


def get_covid_data() -> dict:
    if FROM_WEB:
        r = requests.get(CORONA_URL)
        data = r.json()
        save_data(data, COVID_FILE)
        return data
    else:
        return load_data(COVID_FILE)


def save_countries_data(known_countries: Any):
    save_data({"countries": list(known_countries.items())}, COUNTRIES_FILE)


def load_countries_data() -> Any:
    data = load_data(COUNTRIES_FILE)["countries"]
    known_countries: Dict[Location, Country] = {}
    for location, country in data:
        known_countries[Location(*location)] = Country(*country)
    return known_countries


Location = namedtuple("Location", ["name", "code"])
Country = namedtuple("Country", ["name", "code", "population"])

IGNORE_LOCATIONS: Set[Location] = {
    Location("Others", "XX"),
    Location("occupied Palestinian territory", "XX"),
    Location("Channel Islands", "XX"),
}

FIX_LOCATIONS: Dict[Location, Location] = {
    Location("Republic of Korea", "XX"): Location("South Korea", "KR"),
    Location("Hong Kong SAR", "XX"): Location("Honk Kong", "HK"),
    Location("Taipei and environs", "XX"): Location("Taiwan", "TW"),
    Location(name="Macao SAR", code="XX"): Location("Macau", "MO"),
}


def get_country_details(location: Location) -> Country:
    population = 0
    country_code = location.code

    if location.code == "XX":
        r = requests.get(COUNTRY_NAME_URL + location.name)
        if r.ok:
            country_data = r.json()
            if isinstance(country_data, list):
                if len(country_data) > 1:
                    names = [country["name"] for country in country_data]
                    print(
                        f"ERROR: Multiple countries returned for location {location}: {names}"
                    )
                else:
                    population = country_data[0]["population"]
                    country_code = country_data[0]["alpha2Code"]
            else:
                population = country_data["population"]
                country_code = country_data["alpha2Code"]
    else:
        r = requests.get(COUNTRY_CODE_URL + location.code)
        if r.ok:
            country_data = r.json()
            population = country_data["population"]
            country_code = country_data["alpha2Code"]

    if population == 0:
        print(f"ERROR: Data for location {location} not found")

    return Country(location.name, country_code, population)


def build_countries(data_locations) -> Dict[Location, Country]:
    if not FROM_WEB:
        return load_countries_data()

    known_countries: Dict[Location, Country] = {}

    for data_location in data_locations:
        location = Location(data_location["country"], data_location["country_code"])

        if location in known_countries:
            continue

        if location in IGNORE_LOCATIONS:
            continue

        if location in FIX_LOCATIONS:
            location = FIX_LOCATIONS[location]

        known_countries[location] = get_country_details(location)

    if FROM_WEB:
        save_countries_data(known_countries)

    return known_countries


covid_data = get_covid_data()
confirmed = covid_data["confirmed"]["locations"]
deaths = covid_data["deaths"]["locations"]
recovered = covid_data["recovered"]["locations"]

known_countries = build_countries(chain.from_iterable([confirmed, deaths, recovered]))

for location in sorted(known_countries):
    country = known_countries[location]
    print(country.name, country.population)


"""
Numbers = namedtuple("Numbers", ["population", "confirmed", "deaths", "recovered"])

data = requests.get(CORONA_URL).json()
confirmed = data["confirmed"]

countries = set()

confirmed_counts: Counter = Counter()

for loc in confirmed["locations"]:
    country_name = loc["country"]
    country_code = loc["country_code"]
    population = 0

    if country_code == "XX":
        r = requests.get(COUNTRY_NAME_URL + country_name)
        if r.ok:
            country_data = r.json()
            if isinstance(country_data, list):
                if len(country_data) > 1:
                    names = [country["name"] for country in country_data]
                    print(
                        f"Multiple countries returned for name {country_name}: {names}"
                    )
                else:
                    population = country_data[0]["population"]
            else:
                population = country_data["population"]
    else:
        r = requests.get(COUNTRY_CODE_URL + country_code)
        if r.ok:
            country_data = r.json()
            population = country_data["population"]

    country = Country(country_name, country_code, population)
    countries.add(country)

    # confirmed_counts[loc["country"]] += loc["latest"]

# for country, cases in confirmed_counts.most_common(10):
#     print(f"{country}: {cases}")

for country in countries:
    print(country)
"""
