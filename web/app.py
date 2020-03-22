from flask import Flask,jsonify,request
from flask_restful import Api,Resource
from pymongo import MongoClient
import bcrypt
import json
import requests
import subprocess


app = Flask(__name__)
api = Api(app)
client = MongoClient("mongodb://db:27017")
db = client.ImageClassify
user = db['Users'] #collection


def UserExist(username):
    if user.find({'username':username}).count()==0:
        return False
    else: return True

def verifyCred(username,password):
    if not UserExist(username):
        return jsonify(genRetDict(301,"Invalid Username")),True
    correct_psw = verify_pw(username,password)
    if not correct_psw:
        return jsonify(genRetDict(302,"Invalid Password")),True
    else:
        return None,False

def verify_pw(username,password):
    if not UserExist(username):
        return False
    hashed_psw = user.find({'username':username})[0]['password']
    if (bcrypt.hashpw(password.encode('utf8'),hashed_psw)==hashed_psw):
        return True
    else: return False

def genRetDict(status,msg):
    retJSON={
        'status':status,
        'message':msg
    }
    return retJSON



class Register(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData['username']
        password = postedData['password']

        if UserExist(username):
            return jsonify(genRetDict(301,"Invalid Username"))

        hashed = bcrypt.hashpw(password.encode('utf8'),bcrypt.gensalt())

        user.insert({
            'username' : username,
            'password': hashed,
            'tokens' :10
        })

        return jsonify(genRetDict(200,"User is registered"))

class Classify(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData['username']
        password = postedData['password']
        url = postedData['url']

        hashed = bcrypt.hashpw(password.encode('utf8'),bcrypt.gensalt())

        retJSON,error = verifyCred(username,password)

        if error:
            return jsonify(genRetDict(302,"Invalid Password"))

        tokens = user.find({'username':username})[0]['tokens']

        if tokens<=0:
            return jsonify(genRetDict(303,"Out of tokens"))


        image = requests.get(url)
        retJSON={}
        with open("temp.jpg","wb") as f:
            f.write(image.content)
            proc = subprocess.Popen('python classify_image.py --model_dir=. --image_file=./temp.jpg',shell=True)
            proc.communicate()[0]
            proc.wait()
        with open('text.txt') as g:
            retJSON = json.load(g)

        user.update({
            'username' : username,
        },
        {'$set':{
            'tokens': tokens-1 }
        })

        return jsonify(retJSON)

class Refill(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData['username']
        password = postedData['password']
        amount = postedData['amount']

        if not UserExist(username):
            return jsonify(genRetDict(301,"Invalid Username"))


        admin_psw ='abc'

        if not password == admin_psw:
            return jsonify(genRetDict(304,"Invalid Admin Password"))

        user.update({
            'username':username
        },{
            '$set':{
            'tokens':amount
            }
        })

        return jsonify(genRetDict(200,"Refilled Successfully"))



api.add_resource(Register,"/register")
api.add_resource(Classify,"/classify")
api.add_resource(Refill,"/refill")

@app.route('/')
def hello_world():
    return "Hello World"

if __name__ == "__main__":
    app.run(host='0.0.0.0')
