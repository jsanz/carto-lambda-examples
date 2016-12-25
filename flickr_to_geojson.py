import logging
from flask import Flask
from flask import make_response
from flask import request
import os

app = Flask(__name__)
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def getPhotos(arguments):
    """Generic request that by default will look for 5 photos from the
    "Project weather" group but will allow to be overriden with any
    other Flickr method that retrieves photos.

    arguments -- list of parameters received from the GET petition
    """
    import requests
    import json
    import pprint

    api_key = os.environ.get('FLICKR_API_KEY')

    # Defaults
    url = "https://api.flickr.com/services/rest/"
    querystring = {
        "api_key": api_key,
        "format": "json",
        "nojsoncallback": "1",
        "per_page": 5,
        "method": "flickr.groups.pools.getPhotos",
        "group_id": "1463451@N25"
    }

    # Create a complete querystring for Flickr
    querystring.update(arguments)

    # Convert all parameters to strings
    for key in querystring:
        if type(querystring[key]) is list:
            querystring[key] = querystring[key][0]

    # Assure "geo" is in the extras parameter or set a default
    if 'extras' in querystring and querystring['extras'].find("geo") == -1:
        querystring['extras'] = "{},geo".format(querystring['extras'])
    elif 'extras' not in querystring:
        querystring['extras'] = ",".join([
            "geo",
            "description",
            "date_upload",
            "date_taken",
            "owner_name",
            "tags",
            "machine_tags",
            "path_alias",
            "views",
            "url_t",
            "url_m",
            "url_o"])

    logger.debug(pprint.pprint(querystring))
    response = requests.request("GET", url, params=querystring)
    logger.debug(response.url)

    if response.status_code == requests.codes.ok:
        return response.text
    else:
        msg = 'Error making the request to Flickr\r\n{}'
        raise Exception(msg.format(str(querystring)))


@app.route('/', methods=['GET'])
def lambda_handler(event=None, context=None):
    """
    Lambda handler that behaves like a normal Flask function
    """
    logger.info('Lambda function invoked index()')

    file_name_default = os.environ.get('FLICKR_FILE_NAME') or "flickr_map"

    # Parameters, take a file name if exists and remove it from the dict
    file_name = request.args.get('file_name') or file_name_default
    params = request.args.copy()
    if 'file_name' in params:
        params.pop('file_name')

    try:
        import json
        from geojson import FeatureCollection, Feature, Point

        # Request Flickr JSON
        result = json.loads(getPhotos(params))

        # Check the Flickr photos list is in the result
        if 'photos' in result and 'photo' in result['photos']:
            photos = result['photos']['photo']

            # Generate the GeoJSON from Flickr response
            geophotos = []
            for photo in photos:
                # Fix Flickr description object
                if 'description' in photo:
                    photo['description'] = photo['description']['_content']

                # Take the coordinates (if exist)
                has_coordinates = photo['longitude'] and photo['latitude']
                if 'geo_is_public' in photo and has_coordinates:
                    point = Point((float(photo['longitude']),
                                   float(photo['latitude'])))
                else:
                    point = Point(None, None)

                geophotos.append(Feature(geometry=point, properties=photo))

            # Produce a GeoJSON Feature collection
            body = json.dumps(FeatureCollection(geophotos))
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
