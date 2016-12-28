import os
import logging
import requests
from flask import Flask
from flask import make_response
from flask import request
import json
from geojson import FeatureCollection, Feature, Point

app = Flask(__name__)
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

@app.route('/', methods=['GET'])
def lambda_handler(event=None, context=None):
    """
    Lambda handler that behaves like a normal Flask function
    """
    logger.info('Lambda function invoked index()')
    ## CONFIG
    MAD_URL = "http://www.mambiente.munimadrid.es/opendata/horario.txt"
    MAD_HEADERS = {'pragma': 'no-cache'}
    MAD_FILENAME = "viva_la_papa"

    try:
        logger.debug('Making the request to the shitty Madrid Open data portal')
        rq = requests.request("GET", url=MAD_URL, headers=MAD_HEADERS)
        logger.debug('Finished')
        if rq.status_code != requests.codes.ok:
            raise Exception('Error making the request\r\n')

        rows = []
        for row in rq.text.splitlines():
            point = Point(None,None)
            properties = {}
            i = 1
            for field in row.split(','):
                try:
                    value=float(field)
                except:
                    value=field

                properties['field_{}'.format(i)] = value
                i = i+1
            rows.append(Feature(geometry=point,properties=properties))

        # Build the response
        body =  json.dumps(FeatureCollection(rows))
        attachment = 'attachment; filename={0}.json'.format(MAD_FILENAME)
        # Create a response with the proper headers
        # CARTO will use the file name property as the table name
        response = make_response(body)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = attachment

        return response

    except Exception as e:
        response = make_response(e.message + "\r\n")
        response.headers['Content-Type'] = 'text/plain'
        response.status_code = 500
        return response

if __name__ == '__main__':
    app.run(debug=True)