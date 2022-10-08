from flask import Flask, jsonify, request, make_response
from flask_restful import Api, Resource
from flask_pymongo import PyMongo
from flask_cors import CORS
import bcrypt

app = Flask(__name__)
docker_version = "mongodb://db:27017/bank"
local_version = "mongodb://localhost:27017/bank"
app.config["MONGO_URI"] = local_version
mongo = PyMongo(app)
api = Api(app)
CORS(app)


####################################
def user_exist(username):
    if mongo.db.users.find({
        "username": username
    }).count() == 0:
        return False
    return True


####################################
def verify_pw(username, password):
    hashed_pw = mongo.db.users.find({
        "username": username
    })[0]["password"]
    # a = [user for user in hashed_pw]
    # print(a)
    if bcrypt.checkpw(password.encode(), hashed_pw):
        return True
    return False


####################################
def generate_dico(status, message):
    retJson = {
        "status": status,
        "message": message
    }
    return retJson


####################################
def verify_credentials(username, password):
    if not user_exist(username):
        return generate_dico(301, "Invalid username"), True
    correct_pw = verify_pw(username, password)
    if not correct_pw:
        return generate_dico(302, "Invalid password"), True
    return None, False


####################################
def cash_with_users(username):
    cash = mongo.db.users.find({
        "username": username
    })[0]["Own"]
    return cash


####################################
def debt_with_users(username):
    debt = mongo.db.users.find({
        "username": username
    })[0]["Debt"]
    return debt


####################################
def update_account(username, balance):
    mongo.db.users.update({
        "username": username,
    }, {
        "$set": {
            "Own": balance
        }
    })


####################################
def update_debt(username, balance):
    mongo.db.users.update({
        "username": username,
    }, {
        "$set": {
            "Debt": balance
        }
    })


class Register(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]
        if user_exist(username):
            retJson = {
                "status": 301,
                "message": "Invalid username"
            }
            return jsonify(retJson)
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        mongo.db.users.insert({
            "username": username,
            "password": hashed_pw,
            "Own": 0,
            "Debt": 0
        })
        retJson = {
            "status": 200,
            "msg": "You Successefully registred for the API"
        }
        return jsonify(retJson)


class Add(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]
        money = posted_data["amount"]
        retJson, error = verify_credentials(username, password)
        if error:
            return jsonify(retJson)
        if money <= 0:
            return jsonify(generate_dico(304, "money amount must be greater than Zero"))
        cash = cash_with_users(username)
        money -= 1
        bank_cash = cash_with_users("BANK")
        update_account("BANK", bank_cash + 1)
        update_account(username, cash + money)
        return jsonify(generate_dico(200, "Amount added successfully to the Accounts !"))


class Transfer(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]
        to = posted_data["To"]
        money = posted_data["amount"]
        retJson, error = verify_credentials(username, password)
        if error:
            return make_response(jsonify(retJson), 400)
        cash = cash_with_users(username)
        if cash <= 0:
            return make_response(
                jsonify(generate_dico(304, "You're out of money please add or take a loan"))
                , 400)

        if not user_exist(to):
            return make_response(jsonify(generate_dico(301, "Receiver username is Invalid !")), 400)
        cash_from = cash_with_users(username)
        cash_to = cash_with_users(to)
        bank_cash = cash_with_users("BANK")
        update_account("BANK", bank_cash + 1)
        update_account(to, cash_to + money - 1)
        update_account(username, cash_from - money)
        return jsonify(generate_dico(200, "Amount transfered successfully !"))


class Balance(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]
        retJson, error = verify_credentials(username, password)
        if error:
            return jsonify(retJson)
        retJson = mongo.db.users.find({
            "username": username
        }, {
            'password': 0,
            '_id': 0
        })[0]
        return jsonify(retJson)


class Takeloan(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]
        money = posted_data["amount"]
        retJson, error = verify_credentials(username, password)
        if error:
            return jsonify(retJson)
        cash = cash_with_users(username)
        debt = debt_with_users(username)
        update_account(username, cash + money)
        update_debt(username, debt + money)
        return jsonify(generate_dico(200, "Loan added to your Account successfully !"))


class Payloan(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]
        money = posted_data["amount"]
        retJson, error = verify_credentials(username, password)
        if error:
            return jsonify(retJson)
        cash = cash_with_users(username)
        if cash < money:
            return jsonify(generate_dico(303, "Not enough cash in your account"))
        debt = debt_with_users(username)
        update_account(username, cash - money)
        update_debt(username, debt - money)
        return jsonify(generate_dico(200, "You've successfully payed your loan"))


api.add_resource(Register, '/register')
api.add_resource(Add, '/add')
api.add_resource(Transfer, '/transfer')
api.add_resource(Balance, '/balance')
api.add_resource(Takeloan, '/takeloan')
api.add_resource(Payloan, '/payloan')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

# bank pw : bankpassword
