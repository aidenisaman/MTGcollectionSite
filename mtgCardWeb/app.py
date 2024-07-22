import random
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy.orm import relationship
from sqlalchemy import JSON

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to your own secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    cards = relationship('Card', backref='user', lazy=True)

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    set_name = db.Column(db.String(150))
    price = db.Column(db.Float)
    is_foil = db.Column(db.Boolean, default=False)
    image_url = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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
    flash('You have been logged out.', 'success')
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

def get_random_commander():
    url = "https://api.scryfall.com/cards/random"
    params = {
        'q': 'is:commander'
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        card = response.json()
        return {
            'name': card['name'],
            'image_url': card['image_uris']['normal'] if 'image_uris' in card else card['card_faces'][0]['image_uris']['normal'],
            'edhrec_url': f"https://edhrec.com/commanders/{card['name'].lower().replace(' ', '-').replace(',', '')}"
        }
    return None

@app.route('/')
def index():
    random_commander = get_random_commander()
    return render_template('index.html', random_commander=random_commander)

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
    card_data = request.json
    new_card = Card(
        card_id=card_data['id'],
        name=card_data['name'],
        set_name=card_data['set_name'],
        price=float(card_data['price']) if card_data['price'] not in ['N/A', None, ''] else None,
        is_foil=card_data['is_foil'],
        image_url=card_data['image_url'],
        user_id=current_user.id
    )
    db.session.add(new_card)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/remove_from_collection', methods=['POST'])
@login_required
def remove_from_collection():
    card_id = request.json['id']
    card = Card.query.filter_by(card_id=card_id, user_id=current_user.id).first()
    if card:
        db.session.delete(card)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Card not found in collection'})

@app.route('/collection')
@login_required
def view_collection():
    cards = Card.query.filter_by(user_id=current_user.id).all()
    total_value = sum(card.price for card in cards if card.price is not None)
    return render_template('collection.html', collection=cards, total_value=total_value)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
