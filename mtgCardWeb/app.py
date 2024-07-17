from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import requests

#The login kinda works but a register/login hyper link needs to be added

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a real secret key in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Use a SQLite database for simplicity
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    collection = db.Column(db.PickleType, default=[])

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

def get_card_printings(card_name, card_type=None, card_color=None):
    url = f"https://api.scryfall.com/cards/search"
    query = f'!"{card_name}"'
    if card_type:
        query += f' type:{card_type}'
    if card_color:
        query += f' color:{card_color}'
    params = {'q': query, 'order': 'released', 'unique': 'prints'}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()['data']
    else:
        return []

def get_image_url(card):
    if 'image_uris' in card:
        return card['image_uris']['normal']
    elif 'card_faces' in card and 'image_uris' in card['card_faces'][0]:
        return card['card_faces'][0]['image_uris']['normal']
    else:
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    card_name = request.form['card_name']
    card_type = request.form.get('card_type')
    card_color = request.form.get('card_color')
    card_data = get_card_printings(card_name, card_type, card_color)
    results = []
    for card in card_data:
        results.append({
            'id': card['id'],
            'name': card['name'],
            'set_name': card['set_name'],
            'usd_price': card['prices'].get('usd', 'N/A'),
            'usd_foil_price': card['prices'].get('usd_foil', 'N/A'),
            'image_url': get_image_url(card),
            'type_line': card.get('type_line', ''),
            'colors': card.get('colors', [])
        })
    return jsonify(results)

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('q', '')
    url = f"https://api.scryfall.com/cards/autocomplete"
    params = {'q': query}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return jsonify(response.json()['data'])
    else:
        return jsonify([])

@app.route('/add_to_collection', methods=['POST'])
@login_required
def add_to_collection():
    card = request.json
    user = User.query.get(current_user.id)
    user.collection.append(card)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/remove_from_collection', methods=['POST'])
@login_required
def remove_from_collection():
    card_id = request.json['id']
    user = User.query.get(current_user.id)
    user.collection = [card for card in user.collection if card['id'] != card_id]
    db.session.commit()
    return jsonify({'success': True})

@app.route('/collection')
@login_required
def view_collection():
    user = User.query.get(current_user.id)
    collection = user.collection
    total_value = sum(float(card.get('price', '0')) for card in collection if card.get('price') not in ['N/A', None])
    return render_template('collection.html', collection=collection, total_value=total_value)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
