import os
from flask import jsonify
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


# This function will send JSON response in case Success or fail
def json_return(status, message):
    retJson = {
        "status": status,
        "message": message
    }
    return jsonify(retJson)

# Validate Upload file format should be csv or txt
# need to update in the .env file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() \
       in eval(os.environ.get('ALLOWED_FILE_EXTENSIONS'))