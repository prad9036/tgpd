from flask import Flask, jsonify
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)

# MongoDB connection
mongo_client = MongoClient('your_mongo_uri_here')
db = mongo_client.get_database()
collection = db.get_collection('files')  # Assuming a collection named 'files'

@app.route('/watch/<file_id>', methods=['GET'])
def watch_file(file_id):
    file_object_id = ObjectId(file_id)
    file = collection.find_one({"_id": file_object_id})

    if file:
        return jsonify(file)
    else:
        return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    app.run(port=8080)
