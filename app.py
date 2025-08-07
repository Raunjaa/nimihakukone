from flask import Flask, render_template, request, jsonify, Response
import pandas as pd
import json
from fuzzy_search import fuzzy_search, startswith_search, contains_search
from pyproj import Transformer

#create flask_app

app = Flask(__name__)

# CSV source
csv_file = "hgin_ja_vantaan_nimet_7_8_25.csv"

# Load data
try:
    data = pd.read_csv(csv_file, encoding="utf-8", sep=",", header=0)
except Exception as e:
    print(f"Error loading CSV: {e}")
    exit()

# Coordinate transformer: ETRS-TM35FIN (3067) -> WGS84 (4326)
transformer = Transformer.from_crs("EPSG:3067", "EPSG:4326", always_xy=True)

def transform_coords(x, y):
    try:
        return transformer.transform(x, y)
    except:
        return None, None

@app.route('/')
def index():
    unique_kuntas = sorted(data["kunta"].dropna().unique())
    columns = ["nimi_suomi", "nimi_ruotsi"]
    return render_template('index.html', columns=columns, kuntas=unique_kuntas)

@app.route('/search', methods=['POST'])
def search():
    try:
        search_methods = request.form.getlist('search_method') or []
        search_columns = request.form.getlist('search_column') or []
        search_query = request.form['search_query']
        selected_kuntas = request.form.getlist('kunta')
        threshold = int(request.form.get('threshold', 80))
        show_map = request.form.get('show_map') == 'on'

        if not search_query:
            return jsonify({"error": "Search query cannot be empty"}), 400

        if not search_columns:
            return jsonify({"error": "No search columns selected."}), 400

        invalid_columns = [col for col in search_columns if col not in data.columns]
        if invalid_columns:
            return jsonify({"error": f"Invalid column(s): {', '.join(invalid_columns)}"}), 400

        filtered_data = data[data["kunta"].isin(selected_kuntas)] if selected_kuntas else data

        results = {"Sumea": [], "Alkaa merkkijonolla": [], "Sisältää merkkijonon": []}

        for column in search_columns:
            if 'Sumea' in search_methods:
                fuzzy_results = fuzzy_search(filtered_data, column, search_query, threshold)
                for r in fuzzy_results:
                    lon, lat = transform_coords(r.get("x"), r.get("y"))
                    r["lon"] = lon
                    r["lat"] = lat
                results["Sumea"].extend(fuzzy_results)

            if 'Alkaa merkkijonolla' in search_methods:
                startswith_results = startswith_search(filtered_data, column, search_query)
                for r in startswith_results:
                    lon, lat = transform_coords(r.get("x"), r.get("y"))
                    r["lon"] = lon
                    r["lat"] = lat
                results["Alkaa merkkijonolla"].extend(startswith_results)

            if 'Sisältää merkkijonon' in search_methods:
                contains_results = contains_search(filtered_data, column, search_query)
                for r in contains_results:
                    lon, lat = transform_coords(r.get("x"), r.get("y"))
                    r["lon"] = lon
                    r["lat"] = lat
                results["Sisältää merkkijonon"].extend(contains_results)

        return render_template("results.html", results=results, show_map=show_map)

    except Exception as e:
        return jsonify({"errori lopussa": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)