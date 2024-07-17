from flask import Flask, render_template, request, jsonify, session
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a real secret key in production

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
def add_to_collection():
    card = request.json
    if 'collection' not in session:
        session['collection'] = []
    session['collection'].append(card)
    session.modified = True
    return jsonify({'success': True})

@app.route('/remove_from_collection', methods=['POST'])
def remove_from_collection():
    card_id = request.json['id']
    if 'collection' in session:
        session['collection'] = [card for card in session['collection'] if card['id'] != card_id]
        session.modified = True
    return jsonify({'success': True})

@app.route('/collection')
def view_collection():
    collection = session.get('collection', [])
    print(collection)  # Debugging: Print collection to verify its structure

    # Validate that each card is a dictionary
    valid_collection = []
    for card in collection:
        if isinstance(card, dict):
            valid_collection.append(card)
        else:
            print(f"Invalid card data: {card}")  # Debugging: Log invalid card data

    total_value = sum(float(card.get('price', '0')) for card in valid_collection if card.get('price') not in ['N/A', None])
    return render_template('collection.html', collection=valid_collection, total_value=total_value)

if __name__ == '__main__':
    app.run(debug=True)
