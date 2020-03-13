"""COVID-19 Report

Usage:
    __file__ [-w] [-c]

Options:
    -w    pull data from web APIs
    -c    print CSV report
"""

from collections import Counter, namedtuple
from dataclasses import dataclass
from itertools import chain
import json
from typing import Any, Dict, Set

from docopt import docopt
import requests

A_LOT = 999_999_999_999

Location = namedtuple("Location", ["name", "code"])
Country = namedtuple("Country", ["name", "code", "population"])
DataPoint = namedtuple("DataPoint", ["confirmed", "deaths", "recovered"])


@dataclass(order=True)
class Report:
    country_name: str
    population: int
    confirmed: int
    deaths: int
    recovered: int

    @property
    def population_fixed(self):
        return self.population or 1

    @property
    def confirmed_pct(self) -> float:
        return 100 * self.confirmed / self.population_fixed

    @property
    def confirmed_freq(self) -> int:
        ratio = self.confirmed / self.population_fixed
        if ratio:
            return int(1 / ratio)
        else:
            return A_LOT

    @property
    def deaths_pct(self) -> float:
        return 100 * self.deaths / self.population_fixed

    @property
    def deaths_confirmed_pct(self) -> float:
        return 100 * self.deaths / self.confirmed

    @property
    def recovered_pct(self) -> float:
        return 100 * self.recovered / self.population_fixed

    @property
    def recovered_confirmed_pct(self) -> float:
        return 100 * self.recovered / self.confirmed

    @staticmethod
    def csv_header() -> str:
        return '"country_name",population,confirmed,deaths,recovered'

    def csv(self) -> str:
        fields = [
            self.country_name,
            self.population,
            self.confirmed,
            self.deaths,
            self.recovered,
        ]
        return ",".join(map(str, fields))

    def __str__(self) -> str:
        return f"""
{self.country_name}
    population: {self.population}
    confirmed: {self.confirmed}
        {self.confirmed_pct:.6f}% of population = 1 per {self.confirmed_freq}
    deaths: {self.deaths}
        {self.deaths_pct:.6f}% of population
        {self.deaths_confirmed_pct:.6f}% of confirmed cases
    recovered: {self.recovered}
        {self.recovered_pct:.6f}% of population
        {self.recovered_confirmed_pct:.6f}% of confirmed cases
    """.strip()


CORONA_URL = "https://coronavirus-tracker-api.herokuapp.com/all"
COUNTRY_CODE_URL = "https://restcountries.eu/rest/v2/alpha/"
COUNTRY_NAME_URL = "https://restcountries.eu/rest/v2/name/"

COVID_FILE = "data/covid.json"
COUNTRIES_FILE = "data/countries.json"


IGNORE_LOCATIONS: Set[Location] = {
    Location("Others", "XX"),
    Location("occupied Palestinian territory", "XX"),
    Location("Channel Islands", "XX"),
    Location(name="Cruise Ship", code="XX"),
}

FIX_LOCATIONS: Dict[Location, Location] = {
    Location("Republic of Korea", "XX"): Location("South Korea", "KR"),
    Location("Hong Kong SAR", "XX"): Location("Honk Kong", "HK"),
    Location("Taipei and environs", "XX"): Location("Taiwan", "TW"),
    Location(name="Macao SAR", code="XX"): Location("Macau", "MO"),
}


def save_data(data: Any, filename: str):
    with open(filename, "wt") as f:
        json.dump(data, f)


def load_data(filename: str) -> Any:
    with open(filename, "rt") as f:
        return json.load(f)


def get_covid_data(from_web: bool) -> dict:
    if from_web:
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


def build_countries(data_locations, from_web: bool) -> Dict[Location, Country]:
    if not from_web:
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

    if from_web:
        save_countries_data(known_countries)

    return known_countries


def report(from_web: bool, print_csv: bool):
    covid_data = get_covid_data(from_web)
    confirmed = covid_data["confirmed"]["locations"]
    deaths = covid_data["deaths"]["locations"]
    recovered = covid_data["recovered"]["locations"]
    data_locations = list(chain.from_iterable([confirmed, deaths, recovered]))

    known_countries = build_countries(data_locations, from_web)

    confirmed_count: Counter = Counter()
    deaths_count: Counter = Counter()
    recovered_count: Counter = Counter()

    for data_location in confirmed:
        location = Location(data_location["country"], data_location["country_code"])
        confirmed_count[location] += data_location["latest"]

    for data_location in deaths:
        location = Location(data_location["country"], data_location["country_code"])
        deaths_count[location] += data_location["latest"]

    for data_location in recovered:
        location = Location(data_location["country"], data_location["country_code"])
        recovered_count[location] += data_location["latest"]

    from pprint import pprint  # noqa

    reports = []
    for location, country in known_countries.items():
        report = Report(
            country.name,
            country.population,
            confirmed_count[location],
            deaths_count[location],
            recovered_count[location],
        )
        reports.append(report)

    if print_csv:
        print(Report.csv_header())
        for report in sorted(reports, key=lambda r: r.country_name):
            print(report.csv())
    else:
        for report in sorted(reports, key=lambda r: r.confirmed_freq, reverse=True):
            print(report)


def main():
    args = docopt(__doc__.replace("__file__", __file__))
    from_web = args["-w"]
    print_csv = args["-c"]
    report(from_web, print_csv)


if __name__ == "__main__":
    main()
