from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import json
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)
COUCHDB_URL = 'http://admin:password@localhost:5984'  # If you have authentication enabled
# Configuration
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change this in production!
jwt = JWTManager(app)

# CouchDB Configuration
COUCHDB_URL = 'http://localhost:5984'
TASKS_DB = 'tasks'
USERS_DB = 'users'

from flask import render_template

@app.route('/')
def index():
    return render_template('index.html')

# Helper Functions
def create_database(db_name):
    """Creates a database if it doesn't exist."""
    url = f'{COUCHDB_URL}/{db_name}'
    try:
        requests.put(url)
    except requests.RequestException:
        pass

# Create necessary databases
create_database(TASKS_DB)
create_database(USERS_DB)

def create_document(db_name, data):
    """Creates a new document in specified database."""
    url = f'{COUCHDB_URL}/{db_name}'
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

def get_document(db_name, doc_id):
    """Retrieves a document by ID."""
    url = f'{COUCHDB_URL}/{db_name}/{doc_id}'
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def update_document(db_name, doc_id, data):
    """Updates an existing document."""
    url = f'{COUCHDB_URL}/{db_name}/{doc_id}'
    # First get the current revision
    current = requests.get(url)
    if current.status_code == 200:
        data['_rev'] = current.json()['_rev']
    response = requests.put(url, json=data)
    response.raise_for_status()
    return response.json()

def delete_document(db_name, doc_id):
    """Deletes a document."""
    # Get the current revision first
    doc = get_document(db_name, doc_id)
    url = f'{COUCHDB_URL}/{db_name}/{doc_id}?rev={doc["_rev"]}'
    response = requests.delete(url)
    response.raise_for_status()
    return response.json()

def query_documents(db_name, selector):
    """Queries documents using CouchDB's find API."""
    url = f'{COUCHDB_URL}/{db_name}/_find'
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json={'selector': selector}, headers=headers)
    response.raise_for_status()
    return response.json()

# Authentication Routes
@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not all(k in data for k in ('username', 'password')):
        return jsonify({'error': 'Missing username or password'}), 400
    
    # Check if username exists
    try:
        existing_user = query_documents(USERS_DB, {'username': data['username']})
        if existing_user.get('docs'):
            return jsonify({'error': 'Username already exists'}), 400
        
        # Create new user
        user_data = {
            'username': data['username'],
            'password': generate_password_hash(data['password']),
            'created_at': datetime.utcnow().isoformat()
        }
        create_document(USERS_DB, user_data)
        return jsonify({'message': 'User registered successfully'}), 201
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not all(k in data for k in ('username', 'password')):
        return jsonify({'error': 'Missing username or password'}), 400
    
    try:
        # Find user
        result = query_documents(USERS_DB, {'username': data['username']})
        users = result.get('docs', [])
        if not users:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        user = users[0]
        if check_password_hash(user['password'], data['password']):
            access_token = create_access_token(identity=data['username'])
            return jsonify({'access_token': access_token}), 200
        return jsonify({'error': 'Invalid credentials'}), 401
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

# Task Routes
@app.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    current_user = get_jwt_identity()
    
    # Get filter parameters
    category = request.args.get('category')
    priority = request.args.get('priority')
    status = request.args.get('status')
    
    # Build selector
    selector = {'user': current_user}
    if category:
        selector['category'] = category
    if priority:
        selector['priority'] = priority
    if status:
        selector['status'] = status
    
    try:
        result = query_documents(TASKS_DB, selector)
        return jsonify(result.get('docs', [])), 200
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tasks', methods=['POST'])
@jwt_required()
def create_task():
    current_user = get_jwt_identity()
    data = request.get_json()
    
    if not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400
    
    task_data = {
        'user': current_user,
        'title': data['title'],
        'description': data.get('description', ''),
        'category': data.get('category', 'other'),
        'priority': data.get('priority', 'medium'),
        'status': 'pending',
        'due_date': data.get('due_date'),
        'created_at': datetime.utcnow().isoformat()
    }
    
    try:
        result = create_document(TASKS_DB, task_data)
        task_data['_id'] = result['id']
        return jsonify(task_data), 201
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tasks/<task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    current_user = get_jwt_identity()
    
    try:
        # Get existing task
        task = get_document(TASKS_DB, task_id)
        if task.get('user') != current_user:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Update task fields
        data = request.get_json()
        task.update({
            'title': data.get('title', task['title']),
            'description': data.get('description', task['description']),
            'category': data.get('category', task['category']),
            'priority': data.get('priority', task['priority']),
            'status': data.get('status', task['status']),
            'due_date': data.get('due_date', task.get('due_date')),
            'updated_at': datetime.utcnow().isoformat()
        })
        
        update_document(TASKS_DB, task_id, task)
        return jsonify(task), 200
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tasks/<task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    current_user = get_jwt_identity()
    
    try:
        # Check if task belongs to user
        task = get_document(TASKS_DB, task_id)
        if task.get('user') != current_user:
            return jsonify({'error': 'Unauthorized'}), 403
        
        delete_document(TASKS_DB, task_id)
        return jsonify({'message': 'Task deleted successfully'}), 200
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)