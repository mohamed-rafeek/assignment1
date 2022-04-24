from flask import Flask, request
from flask_restful import Resource
from pymongo import MongoClient
import bcrypt
import jwt
from datetime import datetime, timedelta
from .utils import *
import os
from dotenv import load_dotenv, find_dotenv

# Load .env files in this virtual env
load_dotenv(find_dotenv())
app = Flask(__name__)
# This Secret key was generated from  import secrets for JWT token secure
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# Mongo DB connection and colection has been defined
try:
    connect = MongoClient(os.environ.get('DB_HOST'))
    db = connect.testshopdb
    users = db["users"]
    products = db["products"]
    reviews = db["reviews"]
except:
    print("ERROR - Cannot connect to DB")

# When they Call the Register class from
class Register(Resource):
    def post(self):
        # Get posted data by the user
        postedData = request.get_json()

        # Get the data
        username = postedData["username"]
        email = postedData["email"]
        password = postedData["password"]
        # Store M for Male and F for Female
        gender = "M" if postedData["gender"] == "Male" else "F"
        phonenumber = postedData["phonenumber"]
        role = postedData["role"]

        # To encode given user password using bcrypt module
        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        # Store username and pw into the database
        users.insert_one({
            "name": username,
            "email": email,
            "password": hashed_pw,
            "gender": gender,
            "phonenumber": phonenumber,
            "role": role,
            "created_on": str(datetime.utcnow()),
            "token": '',
            "logged_on": '',
            "delete_flag": 0
        })
        # Below function was there in utils.py file
        return json_return('200', "Registered successfully")


# When the user Login
class Login(Resource):
    # Login Authentication and generating JWT token
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]

        # verify the username password match
        correct_passwd = verify_password(username, password)

        if not correct_passwd:
            return json_return(302, "Incorrect Username or Password")

        # Generating JWT Token for the user this token will be saved in user collection
        # All at the API response
        token = jwt.encode({"user_id": username,
                            "exp": datetime.utcnow() + timedelta(minutes=5000)},
                           app.config['SECRET_KEY'], algorithm="HS256")

        # Updating Token in the user collection
        users.update_one({
            "name": username
        }, {
            "$set": {
                "token": str(token),
                "logged_on": str(datetime.utcnow())
            }
        })

        # return with JWT Token
        retJson = {
            "status": 200,
            "token": str(token),
            "message": "Logged in successfully"
        }
        return jsonify(retJson)

# When the User review with user role can able to access URL
class ProductReview(Resource):
    def post(self):
        # JWT token validation get the user name from jwt token
        current_user = token_required()
        if current_user == 404:
            return json_return(404, "a valid token is missing")
        if current_user == 401:
            return json_return(401, "token is invalid")

        # the user colection _id to update review given by this user
        userid = users.find({"name": current_user})[0]["_id"]
        role = users.find({"name": current_user})[0]["role"]

        posted_data = request.get_json()
        # Admin dont have permission to review the product
        if role == "Admin":
            return json_return(500, "You are not authorized to review")

        # Get the barcode and review comment from user input
        barcode = posted_data["barcode"]
        review = posted_data["review"]

        # User must enter the Barcode and review unless through the error
        if barcode == '' or review == '':
            return json_return(500, "Barcode or Review cannot be empty")

        # Store review info in the review collection
        reviews.insert_one({
            "userid": userid,
            "barcode": barcode,
            "review": review,
            "created_at": str(datetime.utcnow())
        })
        # Send Successfull response in the API response
        return json_return(200, "Review added successfully")

# When user want to view Product also have user role can access this API
class ProductSearch(Resource):
    def post(self):
        # Get posted data by the user
        posted_data = request.get_json()
        pageno = int(request.args.get('page'))
        searchstr = posted_data["search"]

        # Verify the Token info and get the user from JWT Token
        current_user = token_required()
        if current_user == 404:
            return json_return(404, "a valid token is missing")
        if current_user == 401:
            return json_return(401, "token is invalid")
        role = users.find({"name": current_user
                           })[0]["role"]
        # Check only User Role can access the API
        if role == "Admin":
            return json_return(500, "User only can search product")

        all_products = {}
        offset = 0
        # Get how many Product need to display per page access from .env file
        # Also number of review per product
        prod_per_page = int(os.environ.get('PRODUCT_LIST_PER_PAGE'))
        review_limit = int(os.environ.get('REVIEW_PRODUCT'))

        if pageno > 0:
            offset = int((pageno * prod_per_page) - prod_per_page)
        prod_list = []
        # Get total product count
        all_products['totalCount'] = products.count_documents({})
        product_data = products.find({"name": {"$regex": searchstr}}). \
            skip(offset).limit(prod_per_page)

        for each_product in product_data:
            # once get each product finding reviews
            review_list = reviews.find({"barcode": each_product["barcode"]}).\
                sort("created_at", -1).limit(review_limit)
            review_data = []

            for each_review in review_list:
                # Only reviewer name and review need to show
                reviewer_name = users.find({"_id": each_review['userid']
                                            })[0]["name"]
                review_data.append(dict(name=reviewer_name, \
                                        review=each_review['review']))
            each_product["reviews"] = review_data
            del each_product['_id']
            prod_list.append(each_product)
        all_products["products"] = prod_list
        # API response in each page
        return json_return(201, all_products)


# Password encrypt user to verify the user with correct credential
def verify_password(username, password):
    hashed_pw = users.find({
        "name": username
    })[0]["password"]
    if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
        return True
    else:
        return False

# JWT Token verification Function for the this will retun the user name
def token_required():
    token = None
    if 'x-access-tokens' in request.headers:
        token = request.headers['x-access-tokens']
    # Set the Authorization update Jwt token while send each time
    if 'Authorization' in request.headers:
        token = request.headers['Authorization']
        token = token.split(" ", 1)
        token = token[1]
    if not token:
        return 404
    try:
        # Decoding the data from Token
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        current_user = data['user_id']
    except:
        return 401
    return current_user
