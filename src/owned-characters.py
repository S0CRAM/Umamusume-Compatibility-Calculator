from flask import Flask, request, render_template_string
import json
import os

app = Flask(__name__)

# Load available characters
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
with open(os.path.join(DATA_DIR, 'availChars.json'), 'r', encoding='utf-8') as f:
    avail_chars = json.load(f)

@app.route('/', methods=['GET'])
def index():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Umamusume Character Selection</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .character { margin: 10px 0; }
            .character label { font-weight: bold; }
            button { margin-top: 20px; padding: 10px; }
        </style>
    </head>
    <body>
        <h1>Select Owned Characters</h1>
        <form method="POST">
            {% for char in avail_chars %}
            <div class="character">
                <input type="checkbox" id="char_{{ char.char_id }}" name="owned_chars" value="{{ char.char_id }}">
                <label for="char_{{ char.char_id }}">{{ char.en_name }} ({{ char.char_id }})</label>
            </div>
            {% endfor %}
            <button type="submit">Save Selection</button>
        </form>
    </body>
    </html>
    '''
    return render_template_string(html, avail_chars=avail_chars)

@app.route('/', methods=['POST'])
def save_selection():
    selected_chars = request.form.getlist('owned_chars')
    owned_chars = [{'char_id': int(char_id), 'en_name': next((c['en_name'] for c in avail_chars if c['char_id'] == int(char_id)), '')} for char_id in selected_chars]
    
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Save to ownedCharacters.json
    with open(os.path.join(DATA_DIR, 'ownedCharacters.json'), 'w', encoding='utf-8') as f:
        json.dump(owned_chars, f, indent=4)
    
    # Return success message with JavaScript to close window
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Selection Saved</title>
        <script>
            alert("Selection saved successfully!");
            // Make request to shutdown endpoint
            fetch('/shutdown', { method: 'POST' })
                .then(() => window.close())
                .catch(() => window.close());
        </script>
    </head>
    <body>
        <h1>Selection Saved!</h1>
        <p>Your character selection has been saved to ownedCharacters.json</p>
        <p>You can now close this window and run the brute-force calculator.</p>
    </body>
    </html>
    '''

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Shutdown the Flask server"""
    os._exit(0)

if __name__ == '__main__':
    app.run(debug=False)