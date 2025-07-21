from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://nafe:0597785625nafe@coffeeshop.s8duwhp.mongodb.net/?retryWrites=true&w=majority&appName=coffeeshop"

# # Create a new client and connect to the server
# client = MongoClient(uri, server_api=ServerApi('1'))
# db = client.coffeeshop
# collection = db["receipt"]

# uri = "mongodb+srv://abubakernafe1:0597785625nafe@trafficmanagement.r28vab3.mongodb.net/"

client = MongoClient(uri, server_api=ServerApi('1'))
db = client.trafficmanagement
collection = db["records"]
violations_coll = db["violations"]

