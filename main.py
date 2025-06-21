from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from pymongo import MongoClient, errors
import yaml
import logging
from logging_loki import LokiHandler

# 🔧 OpenTelemetry + Prometheus
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# 📄 Load config from env.yaml
with open("env.yaml", "r") as f:
    config = yaml.safe_load(f)

mongodb_config = config['mongodb']
server_config = config['server']
loki_config = config['loki']

# 🔗 Connect to MongoDB
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

# ⚙️ Setup logging to Loki AND console
logger = logging.getLogger("flask-app")
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Loki handler
loki_handler = LokiHandler(
    url=loki_config['url'],
    tags={"app": "sm"},
    version="1",
)
loki_handler.setFormatter(formatter)
logger.addHandler(loki_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logger.propagate = False  # avoid duplicate logs if root logger exists

# Also send werkzeug logs to Loki and console
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.setLevel(logging.INFO)
werkzeug_logger.addHandler(loki_handler)
werkzeug_logger.addHandler(console_handler)

# 🚀 Init Flask
app = Flask(__name__)
CORS(app)

# 📊 OpenTelemetry Metrics Setup
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
            logger.warning("Missing 'key' or 'value' in request")
            return jsonify({"error": "Both 'key' and 'value' are required"}), 400

        collection.update_one(
            {'key': key},
            {'$set': {'value': value}},
            upsert=True
        )
        logger.info(f"Stored value for key: {key}")
        print(f"TEST_LOG: Stored value for key: {key}", flush=True)
        return jsonify({"key": key, "message": "Value stored successfully"}), 201
    except Exception as e:
        logger.error(f"Exception in store_key_value: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@app.route('/store', methods=['GET'])
def get_all_key_values():
    try:
        docs = list(collection.find({}, {'_id': 0}))
        logger.info("Fetched all key-value pairs")
        return jsonify(docs), 200
    except Exception as e:
        logger.error(f"Exception in get_all_key_values: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@app.route('/store/<key>', methods=['GET'])
def get_value(key):
    try:
        doc = collection.find_one({'key': key})
        if not doc:
            logger.warning(f"Key not found: {key}")
            return jsonify({"error": f"Key '{key}' not found"}), 404
        logger.info(f"Fetched value for key: {key}")
        return jsonify({"key": doc['key'], "value": doc['value']}), 200
    except Exception as e:
        logger.error(f"Exception in get_value: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@app.route("/metrics", methods=['GET'])
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=server_config["port"], debug=True)
