from .main import *
from .utils import *
from flask import Flask, request
from flask_restful import Api
import pandas as pd
from werkzeug.utils import secure_filename

# Define the flask application to rub
app = Flask(__name__)
api = Api(app)
# To load the .env file in this virtual env file
load_dotenv(find_dotenv())

# All route related which classes need to call metioned here
# This all classes are there in the main.py file
api.add_resource(Register, '/users/register')
api.add_resource(Login, '/users/login')
api.add_resource(ProductReview, '/products/review')
api.add_resource(ProductSearch, '/products/search')

# Function will be called while the URl http://localhost:5000/products
@app.route('/products', methods=['POST'])
def upload_file():
    # JWT Token Authentication validation part below
    current_user = token_required()
    if current_user == 404:
        return json_return(404, "a valid token is missing")
    if current_user == 401:
        return json_return(401, "token is invalid")

    # To confirm user having User( client Role)
    role = users.find({"name": current_user
                       })[0]["role"]
    if role == "User":
        return json_return(500, "You are not authorized to upload")

    # check if the post request has the file part
    if 'files' not in request.files:
        return json_return(400, "No file part in the request")

    file = request.files.get('files')
    errors = {}
    success = False
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(os.environ.get('FILE_UPLOAD_FOLDER'), filename))
        filepath = os.environ.get('FILE_UPLOAD_FOLDER') + "/" + filename

        # csv file which you want to import used pandas module
        df = pd.read_csv(filepath)
        records_ = df.to_dict(orient='records')
        result = products.insert_many(records_)
        success = True
    else:
        errors[file.filename] = 'File type is not allowed'

    if success:
        return json_return(201, "Files successfully uploaded ")
    else:
        return json_return(500, errors)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False)
