import os
import logging
import json
import requests
from requests.auth import HTTPBasicAuth
from flask import Flask
from flask import make_response
from flask import request
from geojson import FeatureCollection, Feature, Point

app = Flask(__name__)
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@app.route('/', methods=['GET'])
def lambda_handler(event=None, context=None):
    """
    Lambda handler that behaves like a normal Flask function
    """
    logger.info('Lambda function invoked index()')

    # Get configuration from environment
    file_name_default = os.environ.get('FILE_NAME') or "bamboo_employees"
    api_key = os.environ.get('BAMBOO_TOKEN')
    url = os.environ.get('BAMBOO_API')

    # Parameters, take a file name if exists and remove it from the dict
    file_name = request.args.get('file_name') or file_name_default

    try:
        # Request data from Bamboo API
        headers = {'Accept': 'application/json'}
        auth = HTTPBasicAuth(api_key, 'x')
        response = requests.get(url=url, headers=headers, auth=auth)

        if response.status_code != requests.codes.ok:
            raise Exception('Error making the request to Bamboo\r\n')

        # Check the result
        result = json.loads(response.text)
        if 'employees' in result:
            # Generate the GeoJSON from API response
            employees = []
            for employee in result['employees']:
                # Bamboo does not provide explicit locations
                point = Point(None, None)
                employees.append(Feature(geometry=point, properties=employee))

            # Produce a GeoJSON Feature collection
            body = json.dumps(FeatureCollection(employees))
            attachment = 'attachment; filename={0}.json'.format(file_name)

            # Create a response with the proper headers
            # CARTO will use the file name property as the table name
            response = make_response(body)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Disposition'] = attachment
        else:
            raise Exception('No photos on your request')

        return response

    except Exception as e:
        response = make_response(e.message + "\r\n")
        response.headers['Content-Type'] = 'text/plain'
        response.status_code = 500
        return response

if __name__ == '__main__':
    app.run(debug=True)
