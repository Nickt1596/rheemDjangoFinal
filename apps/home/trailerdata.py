import time
import os
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor
from geopy.geocoders import Nominatim
import time
import json
import pandas as pd

timeData = []


class GeoLocator:
    def __init__(self, lat, long):
        self.geoLocator = Nominatim(user_agent="geoapiExercises")
        self.lat = lat
        self.long = long
        self.location = self.location()
        self.address = self.location.raw['address']
        self.city = ""
        self.state = ""
        self.country = ""

    def location(self):
        self.location = self.geoLocator.reverse(str(self.lat) + "," + str(self.long))
        return self.location

    def get_city(self):
        if self.address.get('city') is not None:
            return self.address.get('city')
        elif self.address.get('town') is not None:
            return self.address.get('town')
        else:
            return self.address.get('county')

    def get_state(self):
        return us_state_to_abbrev[self.address.get('state')]

    def get_country(self):
        return self.address.get('country_code')


class Trailer:
    def __init__(self, trailernum, lat, long):
        self.trailernum = trailernum
        self.lat = lat
        self.long = long
        self.geoLocator = GeoLocator(self.lat, self.long)
        self.city = self.geoLocator.get_city()
        self.state = self.geoLocator.get_state()
        self.country = self.geoLocator.get_country()

    def printTrailer(self):
        print(self.trailernum, self.lat, self.long, self.city, self.state, self.country)

    def get_trailernum(self):
        return str(self.trailernum)

    def get_lat(self):
        return str(self.lat)

    def get_long(self):
        return str(self.long)

    def get_city(self):
        return str(self.city)

    def get_state(self):
        return str(self.state)

    def get_country(self):
        return str(self.country)


class TrailerDict:
    def __init__(self):
        self.dict = {}

    def add_trailer(self, trailer):
        trailerNum = trailer.get_trailernum()
        trailerList = [trailer.get_lat(), trailer.get_long(), trailer.get_city(),
                       trailer.get_state(), trailer.get_country()]
        self.dict[trailerNum] = trailerList

    def get_dict(self):
        return self.dict


def get_options():
    options = webdriver.ChromeOptions()
    prefs = {"download.default_directory": r"C:\Users\Nick\PycharmProjects\GoogleSheets\LocationCSVs"}
    options.add_experimental_option("prefs", prefs)
    return options


def get_driver():
    options = webdriver.ChromeOptions()
    # options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    options.add_argument("--headless")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument('--disable-gpu')
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    # driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=options)
    driver = webdriver.Chrome(options=options)
    return driver

    # return webdriver.Chrome(options=get_options())


def spireon(trailerDict, driver):
    driver.get('https://transportation.us.spireon.com/home/signin#0')
    driver.find_element_by_css_selector("input[name='username']").send_keys("FreightPros")
    driver.find_element_by_css_selector("input[name='password']").send_keys("password")
    driver.find_element_by_css_selector("#login-button > input[type=submit]").click()
    driver.get(
        'https://transportation.us.spireon.com/operation/json/deviceLocationRestService/get?_dc=1634494068936&id'
        '=12849167')
    structure1 = json.loads(driver.find_element_by_tag_name('body').text)
    driver.get('https://transportation.us.spireon.com/#0')
    driver.find_element_by_css_selector("#accountsCombo-inputEl").click()
    WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, "/html/body/div[5]/div/ul/li[2]")))
    driver.find_element_by_xpath("/html/body/div[5]/div/ul/li[1]").click()
    time.sleep(1)
    driver.get('https://transportation.us.spireon.com/operation/json/deviceLocationRestService/get?_dc'
               '=1634499607619&id=27541113')
    structure2 = json.loads(driver.find_element_by_tag_name('body').text)
    driver.close()
    spireonParse(structure1, trailerDict)
    spireonParse(structure2, trailerDict)


def spireonParse(structure, trailerDict):
    dataDict = dict(structure['data'][0])
    trailerNumber = dataDict['assetName']
    splitTrailer = trailerNumber.split()
    trailerNumber = splitTrailer[0]
    latitude = dataDict['lat']
    longitude = dataDict['lng']
    t = Trailer(trailerNumber, latitude, longitude)
    trailerDict.add_trailer(t)


def skybitztesting(trailerDict, driver):
    trailers = "546500,528687,545823,536313"
    driver.get('https://insight.skybitz.com/')
    driver.find_element_by_css_selector("input[name='strUserName']").send_keys("Freightpros")
    driver.find_element_by_css_selector("input[name='strPassword']").send_keys("Michael1")
    driver.find_element_by_css_selector("input[name='go']").click()
    driver.get('https://insight.skybitz.com/LAABSearch?event=menustartsearch&dispatchTo=/LocateAssets'
               '/AssetBasedSearchAssetsMultiple.jsp')
    driver.find_element_by_css_selector("textarea[name='assetIds']").send_keys(trailers)
    driver.find_element_by_css_selector("input[name='assetSearch']").click()
    html = driver.find_element_by_css_selector('#locateAssetsTbl')
    htmltest = html.get_attribute("outerHTML")
    driver.close()
    skybitzParse(htmltest, trailerDict)


def skybitzParse(htmltest, trailerDict):
    tables = pd.read_html(htmltest)
    table = tables[0]
    for i in range(len(table)):
        trailerNum = table.loc[i, 'Asset ID']
        Latitude = table.loc[i, 'Latitude']
        Longitude = table.loc[i, 'Longitude']
        t = Trailer(trailerNum, Latitude, Longitude)
        trailerDict.add_trailer(t)


def skybitztesting2(trailerDict, driver):
    driver.get('https://insight.skybitz.com/')
    driver.find_element_by_css_selector("input[name='strUserName']").send_keys("freightpros1@gmail.com")
    driver.find_element_by_css_selector("input[name='strPassword']").send_keys("Welcome123")
    driver.find_element_by_css_selector("input[name='go']").click()
    driver.get('https://insight.skybitz.com/LAABSearch?event=menustartsearch&dispatchTo=/LocateAssets'
               '/AssetBasedSearchAssetsSingle.jsp')
    driver.find_element_by_css_selector("input[name='assetIdTypeAhead']").send_keys("U969542")
    driver.find_element_by_css_selector("input[name='assetSearch']").click()
    html = driver.find_element_by_css_selector('#locateAssetsTbl')
    htmltest = html.get_attribute("outerHTML")
    driver.close()
    skybitzParse(htmltest, trailerDict)


def xtralease(trailerDict, driver):
    driver.get("https://secure.xtra.com/Secure/TrailerTracking/SelectTrackingProvider.aspx?ver=tt")
    driver.find_element_by_css_selector("input[name='lgnSite$UserName']").send_keys("GREATWIDE5422")
    driver.find_element_by_css_selector("input[name='lgnSite$Password']").send_keys("XTRA5423")
    driver.find_element_by_css_selector("input[name='lgnSite$LoginButton']").click()
    driver.get('https://trailertracking.xtra.com/trailers')
    text = driver.execute_script('return trailerVOListJson')
    driver.close()
    xtraleaseParse(text, trailerDict)


def xtraleaseParse(text, trailerDict):
    for i in range(len(text)):
        if text[i]['trailerId'] == 'W00231':
            trailerNumber = text[i]['trailerId']
            latitude = text[i]['landmarkVO']['latitude']
            longitude = text[i]['landmarkVO']['longitude']
    t = Trailer(trailerNumber, latitude, longitude)
    trailerDict.add_trailer(t)


def run():
    trailerDict = TrailerDict()
    # with ThreadPoolExecutor(max_workers=1) as executor:
    #     executor.submit(skybitztesting, trailerDict, driver=get_driver())
    #     executor.submit(skybitztesting2, trailerDict, driver=get_driver())
    #     executor.submit(xtralease, trailerDict, driver=get_driver())
    #     executor.submit(spireon, trailerDict, driver=get_driver())
    xtralease(trailerDict, get_driver())
    spireon(trailerDict, get_driver())
    skybitztesting(trailerDict, get_driver())
    skybitztesting2(trailerDict, get_driver())
    time.sleep(1)
    dict = trailerDict.get_dict()
    return dict


us_state_to_abbrev = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "District of Columbia": "DC",
    "American Samoa": "AS",
    "Guam": "GU",
    "Northern Mariana Islands": "MP",
    "Puerto Rico": "PR",
    "United States Minor Outlying Islands": "UM",
    "U.S. Virgin Islands": "VI",
    "Tamaulipas": "TM"
}
