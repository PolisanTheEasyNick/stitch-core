from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
import requests
import json
import datetime
import pytz
from time import sleep
import asyncio
import websockets

from .base import APIModule
from core.config import ACCUWEATHER_API_KEY, ACCUWEATHER_LOCATION_CODE, WEATHER_API_KEY, WEATHER_COORDS

url = f'http://dataservice.accuweather.com/currentconditions/v1/{ACCUWEATHER_LOCATION_CODE}?apikey={ACCUWEATHER_API_KEY}&details=true'

connected_clients = set()
last_weather = {}

async def send_update(data):
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
        while True:
          # Send a GET request to the API endpoint and parse the JSON response
        #   response = requests.get(url)
        #   try:
        #     weather_data = json.loads(response.content)[0]
        #   except:
        #     print(f"Cant get [0], response.content: {response.content}")
        #     sleep(1800)
        #     continue

          weather_data = json.loads('[{"LocalObservationDateTime":"2024-07-24T17:22:00+03:00","EpochTime":1721830920,"WeatherText":"Mostly cloudy","WeatherIcon":6,"HasPrecipitation":false,"PrecipitationType":null,"IsDayTime":true,"Temperature":{"Metric":{"Value":19.9,"Unit":"C","UnitType":17},"Imperial":{"Value":68.0,"Unit":"F","UnitType":18}},"RealFeelTemperature":{"Metric":{"Value":17.9,"Unit":"C","UnitType":17,"Phrase":"Pleasant"},"Imperial":{"Value":64.0,"Unit":"F","UnitType":18,"Phrase":"Pleasant"}},"RealFeelTemperatureShade":{"Metric":{"Value":16.7,"Unit":"C","UnitType":17,"Phrase":"Pleasant"},"Imperial":{"Value":62.0,"Unit":"F","UnitType":18,"Phrase":"Cool"}},"RelativeHumidity":78,"IndoorRelativeHumidity":77,"DewPoint":{"Metric":{"Value":15.9,"Unit":"C","UnitType":17},"Imperial":{"Value":61.0,"Unit":"F","UnitType":18}},"Wind":{"Direction":{"Degrees":338,"Localized":"NNW","English":"NNW"},"Speed":{"Metric":{"Value":24.8,"Unit":"km/h","UnitType":7},"Imperial":{"Value":15.4,"Unit":"mi/h","UnitType":9}}},"WindGust":{"Speed":{"Metric":{"Value":30.5,"Unit":"km/h","UnitType":7},"Imperial":{"Value":19.0,"Unit":"mi/h","UnitType":9}}},"UVIndex":2,"UVIndexText":"Low","Visibility":{"Metric":{"Value":24.1,"Unit":"km","UnitType":6},"Imperial":{"Value":15.0,"Unit":"mi","UnitType":2}},"ObstructionsToVisibility":"","CloudCover":76,"Ceiling":{"Metric":{"Value":12192.0,"Unit":"m","UnitType":5},"Imperial":{"Value":40000.0,"Unit":"ft","UnitType":0}},"Pressure":{"Metric":{"Value":1009.8,"Unit":"mb","UnitType":14},"Imperial":{"Value":29.82,"Unit":"inHg","UnitType":12}},"PressureTendency":{"LocalizedText":"Falling","Code":"F"},"Past24HourTemperatureDeparture":{"Metric":{"Value":-7.1,"Unit":"C","UnitType":17},"Imperial":{"Value":-13.0,"Unit":"F","UnitType":18}},"ApparentTemperature":{"Metric":{"Value":20.0,"Unit":"C","UnitType":17},"Imperial":{"Value":68.0,"Unit":"F","UnitType":18}},"WindChillTemperature":{"Metric":{"Value":20.0,"Unit":"C","UnitType":17},"Imperial":{"Value":68.0,"Unit":"F","UnitType":18}},"WetBulbTemperature":{"Metric":{"Value":17.5,"Unit":"C","UnitType":17},"Imperial":{"Value":63.0,"Unit":"F","UnitType":18}},"WetBulbGlobeTemperature":{"Metric":{"Value":19.6,"Unit":"C","UnitType":17},"Imperial":{"Value":67.0,"Unit":"F","UnitType":18}},"Precip1hr":{"Metric":{"Value":0.2,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.01,"Unit":"in","UnitType":1}},"PrecipitationSummary":{"Precipitation":{"Metric":{"Value":0.2,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.01,"Unit":"in","UnitType":1}},"PastHour":{"Metric":{"Value":0.2,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.01,"Unit":"in","UnitType":1}},"Past3Hours":{"Metric":{"Value":1.0,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.04,"Unit":"in","UnitType":1}},"Past6Hours":{"Metric":{"Value":8.8,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.35,"Unit":"in","UnitType":1}},"Past9Hours":{"Metric":{"Value":8.8,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.35,"Unit":"in","UnitType":1}},"Past12Hours":{"Metric":{"Value":8.8,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.35,"Unit":"in","UnitType":1}},"Past18Hours":{"Metric":{"Value":8.8,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.35,"Unit":"in","UnitType":1}},"Past24Hours":{"Metric":{"Value":9.0,"Unit":"mm","UnitType":3},"Imperial":{"Value":0.36,"Unit":"in","UnitType":1}}},"TemperatureSummary":{"Past6HourRange":{"Minimum":{"Metric":{"Value":19.2,"Unit":"C","UnitType":17},"Imperial":{"Value":66.0,"Unit":"F","UnitType":18}},"Maximum":{"Metric":{"Value":27.0,"Unit":"C","UnitType":17},"Imperial":{"Value":81.0,"Unit":"F","UnitType":18}}},"Past12HourRange":{"Minimum":{"Metric":{"Value":16.1,"Unit":"C","UnitType":17},"Imperial":{"Value":61.0,"Unit":"F","UnitType":18}},"Maximum":{"Metric":{"Value":27.0,"Unit":"C","UnitType":17},"Imperial":{"Value":81.0,"Unit":"F","UnitType":18}}},"Past24HourRange":{"Minimum":{"Metric":{"Value":14.8,"Unit":"C","UnitType":17},"Imperial":{"Value":59.0,"Unit":"F","UnitType":18}},"Maximum":{"Metric":{"Value":28.2,"Unit":"C","UnitType":17},"Imperial":{"Value":83.0,"Unit":"F","UnitType":18}}}},"MobileLink":"http://www.accuweather.com/en/ua/chernivtsi/322253/current-weather/322253?lang=en-us","Link":"http://www.accuweather.com/en/ua/chernivtsi/322253/current-weather/322253?lang=en-us"}]')[0]

          # Extract the temperature in Celsius and the weather icon ID from the response
          temp = weather_data['Temperature']['Metric']['Value']
          weather_icon = weather_data['WeatherIcon']
          weather_text = weather_data['WeatherText']
          uv_index = weather_data['UVIndex']
          real_temp = weather_data['RealFeelTemperature']['Metric']['Value']

          response = requests.get(f"http://api.weatherapi.com/v1/astronomy.json?key={WEATHER_API_KEY}7&q={WEATHER_COORDS}")
          sunrise_data = json.loads(response.content)
          sunrise = sunrise_data['astronomy']['astro']['sunrise']
          sunset = sunrise_data['astronomy']['astro']['sunset']
          # Parse the target time string into a datetime.time object
          sunrise_time = datetime.datetime.strptime(sunrise, '%I:%M %p').time()
          sunset_time = datetime.datetime.strptime(sunset, '%I:%M %p').time()

          kiev_tz = pytz.timezone('Europe/Kiev')
          current_time = datetime.datetime.now(kiev_tz).time()
          isDay = False
          if current_time >= sunrise_time and current_time <= sunset_time:
            isDay = True
          else:
            isDay = False

          print(f"Current temp: {temp}")
          print(f"Real temp: {real_temp}")
          print(f"Weather text: {weather_text}")
          print(f"Weather icon id: {weather_icon}")
          print(f"Sunrise time: {sunrise}")
          print(f"UV Index: {uv_index}")
          print(f"Is day in Ukraine: {isDay}")
          print(f"Update time: {datetime.datetime.now(kiev_tz).strftime('%Y-%m-%d %H:%M:%S')}")

          # Create a dictionary with the weather data
          weather_dict = {
            'temperature_celsius': temp,
            'real_temp_celsius': real_temp,
            'weather_icon_id':  weather_icon,
            'is_day': isDay,
            'weather_text': weather_text,
            'uv_index': uv_index,
            'last_update_time': datetime.datetime.now(kiev_tz).strftime('%Y-%m-%d %H:%M:%S'),
          }

          # Write the weather data as JSON to a file named "weather_data.json"
          with open('weather_data.json', 'w') as f:
                  json.dump(weather_dict, f)
          await send_update(weather_dict)
          last_weather = weather_dict
          await asyncio.sleep(1800) #sleep 30 mins #1800 was


class WeatherModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:

        @router.get("/weather")
        def get_weather():
            return last_weather

    def register_websockets(self, app: FastAPI):
        @app.websocket("/weather")
        async def websocket_endpoint(websocket: WebSocket):
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
