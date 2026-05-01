from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
import requests
import json
import datetime
import pytz
from time import sleep
import asyncio
import websockets
from os import path

from .base import APIModule
from core.config import ACCUWEATHER_API_KEY, ACCUWEATHER_LOCATION_CODE, WEATHER_API_KEY, WEATHER_COORDS
from core.logger import get_logger

logger = get_logger("Weather")

url = f'http://dataservice.accuweather.com/currentconditions/v1/{ACCUWEATHER_LOCATION_CODE}?apikey={ACCUWEATHER_API_KEY}&details=true'

connected_clients = set()
last_weather = {}

LAST_WEATHER_FILE = '/data/last_weather_fetch.txt'
#FETCH_INTERVAL_SECONDS = 1800  #update once per 30 minutes
FETCH_INTERVAL_SECONDS = 300 #update once per 5 minutes

weather_colors = {
    1:  "#FFD700",  # Sunny - golden yellow
    2:  "#FFE066",  # Mostly sunny - soft yellow
    3:  "#F0E68C",  # Partly sunny - khaki yellow
    4:  "#D3D3D3",  # Intermittent clouds - light gray
    5:  "#E0C080",  # Hazy sunshine - warm beige
    6:  "#A9A9A9",  # Mostly cloudy - dark gray
    7:  "#808080",  # Cloudy - medium gray
    8:  "#696969",  # Dreary (overcast) - dim gray
    11: "#C0C0C0",  # Fog - silvery gray
    12: "#4682B4",  # Showers - steel blue
    13: "#708090",  # Mostly cloudy w/ showers - slate gray
    14: "#87CEEB",  # Partly sunny w/ showers - sky blue
    15: "#483D8B",  # T-storms - dark slate blue
    16: "#4B0082",  # Mostly cloudy w/ T-storms - indigo
    17: "#6A5ACD",  # Partly sunny w/ T-storms - slate blue
    18: "#4169E1",  # Rain - royal blue
    19: "#B0E0E6",  # Flurries - powder blue
    20: "#ADD8E6",  # Mostly cloudy w/ flurries - light blue
    21: "#E6F0FA",  # Partly sunny w/ flurries - pale icy blue
    22: "#FFFFFF",  # Snow - pure white
    23: "#DDEEFF",  # Mostly cloudy w/ snow - cloudy white-blue
    24: "#00CED1",  # Ice - dark turquoise
    25: "#AFEEEE",  # Sleet - pale turquoise
    26: "#40E0D0",  # Freezing rain - turquoise
    29: "#87CEFA",  # Rain and snow - light sky blue
    30: "#FF4500",  # Hot - orange red
    31: "#1E90FF",  # Cold - dodger blue
    32: "#20B2AA",  # Windy - light sea green
    33: "#191970",  # Clear night - midnight blue
    34: "#2F4F4F",  # Mostly clear night - dark slate gray
    35: "#708090",  # Partly cloudy night - slate gray
    36: "#A9A9A9",  # Intermittent clouds night - dark gray
    37: "#B0C4DE",  # Hazy moonlight - light steel blue
    38: "#696969",  # Mostly cloudy night - dim gray
    39: "#4682B4",  # Partly cloudy w/ showers night - steel blue
    40: "#5F9EA0",  # Mostly cloudy w/ showers night - cadet blue
    41: "#483D8B",  # Partly cloudy w/ T-storms night - dark slate blue
    42: "#4B0082",  # Mostly cloudy w/ T-storms night - indigo
    43: "#B0E0E6",  # Mostly cloudy w/ flurries night - powder blue
    44: "#DDEEFF",  # Mostly cloudy w/ snow night - cloudy white-blue
}

async def send_update(data):
    logger.debug("Sending update to WS subscribers")
    global connected_clients
    disconnected = set()
    message = json.dumps(data)
    for ws in connected_clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    connected_clients -= disconnected

async def weather_update():
        global last_weather

        if path.exists(LAST_WEATHER_FILE):
            try:
                with open(LAST_WEATHER_FILE, 'r') as f:
                    cache = json.load(f)
                    last_fetch_str = cache.get("last_fetch_time")
                    last_weather = cache.get("last_weather")
                    if last_fetch_str:
                        last_fetch_time = datetime.datetime.fromisoformat(last_fetch_str)
                        now = datetime.datetime.now(datetime.timezone.utc)
                        elapsed = (now - last_fetch_time).total_seconds()
                        if elapsed < FETCH_INTERVAL_SECONDS:
                            wait_time = FETCH_INTERVAL_SECONDS - elapsed
                            logger.info(f"Last weather fetch was {elapsed:.0f} seconds ago. Waiting {wait_time:.0f} seconds.")
                            await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Failed to load weather cache: {e}")

        while True:
          ### Send a GET request to the API endpoint and parse the JSON response
          response = requests.get(url)
          try:
           weather_data = json.loads(response.content)[0]
          except:
           logger.error(f"Cant get [0], response.content: {response.content}")
           sleep(FETCH_INTERVAL_SECONDS)
           continue

          #weather_data = json.loads('[{"LocalObservationDateTime":"2024-07-24T17:22:00+03:00","EpochTime":1721830920,"WeatherText":"Mostly cloudy","WeatherIcon":6,"HasPrecipitation":false,"PrecipitationType":null,"IsDayTime":true,"Temperature":{"Metric":{"Value":19.9,"Unit":"C","UnitType":17},"Imperial":{"Value":68.0,"Unit":"F","UnitType":18}},"RealFeelTemperature":{"Metric":{"Value":17.9,"Unit":"C","UnitType":17,"Phrase":"Pleasant"},"Imperial":{"Value":64.0,"Unit":"F","UnitType":18,"Phrase":"Pleasant"}},"RealFeelTemperatureShade":{"Metric":{"Value":16.7,"Unit":"C","UnitType":17,"Phrase":"Pleasant"},"Imperial":{"Value":62.0,"Unit":"F","UnitType":18,"Phrase":"Cool"}},"RelativeHumidity":78,"IndoorRelativeHumidity":77,"DewPoint":{"Metric":{"Value":15.9,"Unit":"C","UnitType":17},"Imperial":{"Value":61.0,"Unit":"F","UnitType":18}},"Wind":{"Direction":{"Degrees":338,"Localized":"NNW","English":"NNW"},"Speed":{"Metric":{"Value":24.8,"Unit":"km/h","UnitType":7},"Imperial":{"Value":15.4,"Unit":"mi/h","UnitType":9}}},"WindGust":{"Speed":{"Metric":{"Value":30.5,"Unit":"km/h","UnitType":7},"Imperial":{"Value":19.0,"Unit":"mi/h","UnitType":9}}},"UVIndex":2,"UVIndexText":"Low","Visibility":{"Metric":{"Value":24.1,"Unit":"km","UnitType":6},"Imperial":{"Value":15.0,"Unit":"mi","UnitType":2}},"ObstructionsToVisibility":"","CloudCover":76,"Ceiling":{"Metric":{"Value":12192.0,"Unit":"m","UnitType":5},"Imperial":{"Value":40000.0,"Unit":"ft","UnitType":0}},"Pressure":{"Metric":{"Value":1009.8,"Unit":"mb","UnitType":14},"Imperial":{"Value":29.82,"Unit":"inHg","UnitType":12}},"PressureTendency":{"LocalizedText":"Falling","Code":"F"},"Past24HourTemperatureDeparture":{"Metric":{"Value":-7.1,"Unit":"C","UnitType":17},"Imperial":{"Value":-13.0,"Unit":"F","UnitType":18}},"ApparentTemperature":{"Metric":{"Value":20.0,"Unit":"C","UnitType":17},"Imperial":{"Value":68.0,"Unit":"F","UnitType":18}},"WindChillTemperature":{"Metric":{"Value":20.0,"Unit":"C","UnitType":17},"Imperial":{"Value":68.0,"Unit":"F","UnitType":18}},"WetBulbTemperature":{"Metric":{"Value":17.5,"Unit":"C","UnitType":17},"Imperial":{"Value":63.0,"Unit":"F","UnitType":18}},"WetBulbGlobeTemperature":{"Metric":{"Value":19.6,"Unit":"C","UnitType":17},"Imperial":{"Value":67.0,"Unit":"F","UnitType":18}},"Precip1hr":{"Metric":{"Value":0.2,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.01,"Unit":"in","UnitType":1}},"PrecipitationSummary":{"Precipitation":{"Metric":{"Value":0.2,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.01,"Unit":"in","UnitType":1}},"PastHour":{"Metric":{"Value":0.2,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.01,"Unit":"in","UnitType":1}},"Past3Hours":{"Metric":{"Value":1.0,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.04,"Unit":"in","UnitType":1}},"Past6Hours":{"Metric":{"Value":8.8,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.35,"Unit":"in","UnitType":1}},"Past9Hours":{"Metric":{"Value":8.8,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.35,"Unit":"in","UnitType":1}},"Past12Hours":{"Metric":{"Value":8.8,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.35,"Unit":"in","UnitType":1}},"Past18Hours":{"Metric":{"Value":8.8,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.35,"Unit":"in","UnitType":1}},"Past24Hours":{"Metric":{"Value":9.0,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.36,"Unit":"in","UnitType":1}}},"TemperatureSummary":{"Past6HourRange":{"Minimum":{"Metric":{"Value":19.2,"Unit":"C","UnitType":17},"Imperial":{"Value":66.0,"Unit":"F","UnitType":18}},"Maximum":{"Metric":{"Value":27.0,"Unit":"C","UnitType":17},"Imperial":{"Value":81.0,"Unit":"F","UnitType":18}}},"Past12HourRange":{"Minimum":{"Metric":{"Value":16.1,"Unit":"C","UnitType":17},"Imperial":{"Value":61.0,"Unit":"F","UnitType":18}},"Maximum":{"Metric":{"Value":27.0,"Unit":"C","UnitType":17},"Imperial":{"Value":81.0,"Unit":"F","UnitType":18}}},"Past24HourRange":{"Minimum":{"Metric":{"Value":14.8,"Unit":"C","UnitType":17},"Imperial":{"Value":59.0,"Unit":"F","UnitType":18}},"Maximum":{"Metric":{"Value":28.2,"Unit":"C","UnitType":17},"Imperial":{"Value":83.0,"Unit":"F","UnitType":18}}}},"MobileLink":"http://www.accuweather.com/en/ua/chernivtsi/322253/current-weather/322253?lang=en-us","Link":"http://www.accuweather.com/en/ua/chernivtsi/322253/current-weather/322253?lang=en-us"}]')[0]

          # Extract the temperature in Celsius and the weather icon ID from the response
          temp = weather_data['Temperature']['Metric']['Value']
          weather_icon = weather_data['WeatherIcon']
          weather_text = weather_data['WeatherText']
          uv_index = weather_data['UVIndex']
          real_temp = weather_data['RealFeelTemperature']['Metric']['Value']

          try:
            response = requests.get(f"http://api.weatherapi.com/v1/astronomy.json?key={WEATHER_API_KEY}7&q={WEATHER_COORDS}")
            sunrise_data = json.loads(response.content)
            sunrise = sunrise_data['astronomy']['astro']['sunrise']
            sunset = sunrise_data['astronomy']['astro']['sunset']
            # Parse the target time string into a datetime.time object
            sunrise_time = datetime.datetime.strptime(sunrise, '%I:%M %p').time()
            sunset_time = datetime.datetime.strptime(sunset, '%I:%M %p').time()
          except:
            logger.error(f"Cant get sunrise data, response.content: {response.content}")

          kiev_tz = pytz.timezone('Europe/Kiev')
          current_time = datetime.datetime.now(kiev_tz).time()
          isDay = False
          if current_time >= sunrise_time and current_time <= sunset_time:
            isDay = True
          else:
            isDay = False

          logger.info(f"""Updated weather:
          Current temp: {temp}
          Real temp: {real_temp}
          Weather text: {weather_text}
          Weather icon id: {weather_icon}
          Sunrise time: {sunrise}
          UV Index: {uv_index}
          Is day in Ukraine: {isDay}
          Update time: {datetime.datetime.now(kiev_tz).strftime('%Y-%m-%d %H:%M:%S')}
          Weather color: {weather_colors[weather_icon]}
          """)

          weather_dict = {
            'temperature_celsius': temp,
            'real_temp_celsius': real_temp,
            'weather_icon_id':  weather_icon,
            'is_day': isDay,
            'weather_text': weather_text,
            'uv_index': uv_index,
            'last_update_time': datetime.datetime.now(kiev_tz).strftime('%Y-%m-%d %H:%M:%S'),
            'color': weather_colors[weather_icon]
          }

          await send_update(weather_dict)
          last_weather = weather_dict
          try:
              with open(LAST_WEATHER_FILE, 'w') as f:
                  json.dump({
                      "last_fetch_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      "last_weather": weather_dict
                  }, f)
          except Exception as e:
              logger.error(f"Failed to write weather cache: {e}")
          await asyncio.sleep(FETCH_INTERVAL_SECONDS)


class WeatherModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:

        @router.get("/weather")
        def get_weather():
            logger.debug("GET on /weather")
            return last_weather

    def register_websockets(self, app: FastAPI):
        @app.websocket("/weather")
        async def websocket_endpoint(websocket: WebSocket):
            logger.debug("GET on ws /weather")
            await websocket.accept()
            connected_clients.add(websocket)
            try:
                await websocket.send_json(last_weather)
            except WebSocketDisconnect:
                connected_clients.remove(websocket)

    def register_events(self, app: FastAPI) -> None:
        @app.on_event("startup")
        async def start_weather_update():
            asyncio.create_task(weather_update())
