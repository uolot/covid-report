"""COVID-19 Graph

Usage:
    __file__ <country>
"""

import csv
from io import StringIO
import subprocess
from typing import List, Tuple

from docopt import docopt
import pygame


# dimensions
SCREEN_SIZE = 1200, 900
BOX_SIZE = 1100, 800
BOX_RECT = (
    (SCREEN_SIZE[0] - BOX_SIZE[0]) // 2 - 1,
    (SCREEN_SIZE[1] - BOX_SIZE[1]) // 2 - 1,
    BOX_SIZE[0] + 1,
    BOX_SIZE[1] + 1,
)
BOX_AREA = BOX_SIZE[0] * BOX_SIZE[1]

# colors
BG_COLOR = pygame.Color("white")
BOX_COLOR = pygame.Color("blue")
CONFIRMED_COLOR = pygame.Color("red")
DEATHS_COLOR = pygame.Color("black")
RECOVERED_COLOR = pygame.Color("green")


def get_country_data(country_name: str) -> List[int]:
    country_name = country_name.lower()
    r = subprocess.run(["python", "report.py", "-c"], text=True, capture_output=True)
    csv_data = r.stdout
    csv_file = StringIO(csv_data)
    reader = csv.reader(csv_file, delimiter=",")
    for line in reader:
        if line[0].lower() == country_name:
            data = list(map(int, line[1:]))
            print(data)
            return data

    raise ValueError(f"Country not found: {country_name}")


def get_data_rect(data_type: str, number: int) -> Tuple[int, ...]:
    x = BOX_RECT[0] + 1

    y = BOX_RECT[1] + 1
    if data_type == "confirmed":
        y += 0
    elif data_type == "deaths":
        y += 1
    elif data_type == "recovered":
        y += 2

    return (x, y, max(number, 1), 1)


def graph(country_name: str):
    population, confirmed, deaths, recovered = get_country_data(country_name)
    population_per_pixel = population // BOX_AREA

    confirmed_pixels = confirmed // population_per_pixel
    deaths_pixels = deaths // population_per_pixel
    recovered_pixels = recovered // population_per_pixel

    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE)
    done = False

    screen.fill(BG_COLOR)
    pygame.draw.rect(screen, BOX_COLOR, BOX_RECT, 1)

    pygame.draw.rect(
        screen, CONFIRMED_COLOR, get_data_rect("confirmed", confirmed_pixels)
    )
    pygame.draw.rect(screen, DEATHS_COLOR, get_data_rect("deaths", deaths_pixels))
    pygame.draw.rect(
        screen, RECOVERED_COLOR, get_data_rect("recovered", recovered_pixels)
    )

    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                done = True

        pygame.display.update()

    pygame.quit()


if __name__ == "__main__":
    args = docopt(__doc__.replace("__file__", __file__))
    country_name = args["<country>"]
    graph(country_name)
