from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from pymongo import MongoClient, errors
import yaml

# 🔧 OpenTelemetry + Prometheus
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


# Init Flask app
app = Flask(__name__)
CORS(app)

# Load config from env.yaml
with open("env.yaml", "r") as f:
    config = yaml.safe_load(f)

mongodb_config = config['mongodb']
server_config = config['server']

uri = mongodb_config['uri']
db_name = mongodb_config['database']
collection_name = mongodb_config['collection']

try:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
except errors.ServerSelectionTimeoutError:
    print("Error: Could not connect to MongoDB server.")
    raise SystemExit("Failed to connect to MongoDB. Exiting.")

db = client[db_name]
collection = db[collection_name]

# ⚙️ OpenTelemetry Metrics Setup
reader = PrometheusMetricReader()
provider = MeterProvider(
    metric_readers=[reader],
    resource=Resource.create({SERVICE_NAME: "SM-Application"})
)
FlaskInstrumentor().instrument_app(app)

@app.route('/store', methods=['POST'])
def store_key_value():
    try:
        data = request.json
        key = data.get('key')
        value = data.get('value')
        if not key or not value:
            return jsonify({"error": "Both 'key' and 'value' are required"}), 400

        collection.update_one(
            {'key': key},
            {'$set': {'value': value}},
            upsert=True
        )
        return jsonify({"key": key, "message": "Value stored successfully"}), 201
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route('/store', methods=['GET'])
def get_all_key_values():
    try:
        docs = list(collection.find({}, {'_id': 0}))
        return jsonify(docs), 200
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/store/<key>', methods=['GET'])
def get_value(key):
    try:
        doc = collection.find_one({'key': key})
        if not doc:
            return jsonify({"error": f"Key '{key}' not found"}), 404
        return jsonify({"key": doc['key'], "value": doc['value']}), 200
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

if __name__ == '__main__':
    # 👇 Prometheus metrics exposed here
    app.run(host='0.0.0.0', port=server_config["port"])
