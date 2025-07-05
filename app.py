from flask import Flask, render_template, request, flash, redirect, url_for
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from flask import Flask, render_template, request, redirect, url_for, flash
from crud import *  # importa tutte le funzioni CRUD definite nel file precedentflask

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # per usare flash messages

@app.route('/')
def home():
    return render_template('home.html')

# ----------- PRODUCT ROUTES -----------

@app.route('/create_product', methods=['GET', 'POST'])
def create_product_route():
    from crud import categories_col  # se non già importato
    categories = categories_col.distinct("category_name")  # tutte le categorie

    if request.method == 'POST':
        # Recupero dei campi
        product_id = request.form.get('product_id', '').strip()
        product_name = request.form.get('product_name', '').strip()
        actual_price = request.form.get('actual_price', '').strip()

        # Validazione e normalizzazione actual_price
        price_actual_for_validation = actual_price.replace("₹", "").replace(",", "").strip()
        try:
            actual_price_num = float(price_actual_for_validation)
        except ValueError:
            flash("Il prezzo deve essere un numero valido (es. '₹1,000').", "danger")
            return render_template('create_product.html', categories=categories)

        # Aggiungi simbolo rupia se manca
        if not actual_price.strip().startswith("₹"):
            actual_price = f"₹{price_actual_for_validation}"

        discount_percentage = request.form.get('discount_percentage', '').strip()

        # Validazione discount_percentage
        discount_for_validation = discount_percentage.replace("%", "").strip()
        try:
            discount_num = float(discount_for_validation)
        except ValueError:
            flash("La percentuale di sconto deve essere un numero valido (es. '10').", "danger")
            return render_template('create_product.html', categories=categories)

        # Concateno il simbolo % se manca
        if not discount_percentage.strip().endswith("%"):
            discount_percentage = f"{discount_for_validation}%"

        # Calcolo discounted price come stringa
        discounted_num = actual_price_num * (1 - discount_num / 100)
        discounted_price = f"₹{int(discounted_num)}"

        rating = request.form.get('rating', '').strip()
        try:
            rating = float(rating)  # rating come numero
        except ValueError:
            flash("Il campo rating deve essere un numero valido.", "danger")
            return render_template('create_product.html', categories=categories)

        rating_count = 0
        about_product = request.form.get('about_product', '').strip()
        img_link = request.form.get('img_link', '').strip()
        product_link = request.form.get('product_link', '').strip()
        category_names = request.form.getlist('category_names')

        # Controllo che tutti i campi obbligatori siano compilati
        if not all([product_id, product_name, actual_price,
                    discount_percentage, rating,
                    about_product, img_link, product_link]) or not category_names:
            flash("Tutti i campi devono essere compilati e almeno una categoria deve essere selezionata.", "danger")
            return render_template('create_product.html', categories=categories)

        # Se tutto è ok, crea il prodotto
        try:
            create_product(
                product_id,
                product_name,
                discounted_price,
                actual_price,
                discount_percentage,
                rating,
                rating_count,
                about_product,
                img_link,
                product_link,
                category_names
            )
            flash("Prodotto creato con successo!", "success")
            return redirect(url_for('create_product_route'))
        except Exception as e:
            flash(f"Errore durante la creazione: {str(e)}", "danger")

    return render_template('create_product.html', categories=categories)




@app.route('/read_product', methods=['GET', 'POST'])
def read_product_route():
    product = None
    num_reviews = 0  # inizializza numero recensioni a 0

    if request.method == 'POST':
        product_id = request.form['product_id']
    else:
        product_id = request.args.get('product_id')

    if product_id:
        product = read_product(product_id)
        if not product:
            flash("Prodotto non trovato.", "warning")
        else:
            # Conta le recensioni collegate al prodotto
            num_reviews = db.reviews.count_documents({"product_id": product_id})

    # Lista prodotti per la select
    products = list(db.products.find({}, {"_id": 0, "product_id": 1, "product_name": 1}).sort("product_name", 1))

    return render_template(
        'read_product.html',
        product=product,
        products=products,
        num_reviews=num_reviews
    )


@app.route('/update_product', methods=['GET', 'POST'])
def update_product_route():
    from crud import categories_col
    categories = categories_col.distinct("category_name")

    products = list(db.products.find({}, {"_id": 0, "product_id": 1, "product_name": 1}).sort("product_name", 1))

    if request.method == 'POST':
        product_id = request.form['product_id']
    else:
        product_id = request.args.get('product_id')

    if product_id:
        product = read_product(product_id)
    else:
        product = None

    # Qui lasci invariato il resto della logica già presente nel tuo codice
    # (validazioni, update_fields, update_product, flash, etc.)
    # Basta solo che passi anche `product` e `products` al template.

    return render_template('update_product.html', categories=categories, products=products, product=product)



@app.route('/delete_product', methods=['GET', 'POST'])
def delete_product_route():
    products = list(db.products.find({}, {"_id": 0, "product_id": 1, "product_name": 1}).sort("product_name", 1))

    if request.method == 'POST':
        product_id = request.form['product_id']
    else:
        product_id = request.args.get('product_id')

    if product_id:
        deleted = delete_product(product_id)
        if deleted:
            flash("Prodotto eliminato.", "success")
        else:
            flash("Prodotto non trovato.", "warning")

    return render_template('delete_product.html', products=products)

# ----------- REVIEW ROUTES -----------

@app.route('/add_review', methods=['GET', 'POST'])
def add_review_route():
    # Ordina gli utenti alfabeticamente per nome
    users = list(db.users.find({}, {"_id": 0, "user_id": 1, "user_name": 1}).sort("user_name", 1))

    # Ordina i prodotti alfabeticamente per nome
    products = list(db.products.find({}, {"_id": 0, "product_id": 1, "product_name": 1}).sort("product_name", 1))

    if request.method == 'POST':
        try:
            add_review(
                request.form['product_id'],
                request.form['review_id'],
                request.form['user_id'],
                request.form['review_title'],
                request.form['review_content']
            )
            flash("Recensione aggiunta con successo!", "success")
        except Exception as e:
            flash(str(e), "danger")

    return render_template('create_review.html', users=users, products=products)


@app.route('/update_review', methods=['GET', 'POST'])
def update_review_route():
    products = list(db.products.find())
    selected_product_id = None
    reviews = []

    if request.method == 'POST':
        # Se arriva solo product_id (selezione prodotto)
        if 'product_id' in request.form and 'review_id' not in request.form:
            selected_product_id = request.form.get('product_id')
            if selected_product_id:
                reviews = list(db.reviews.find({"product_id": selected_product_id}))

        # Se arriva anche review_id, allora aggiorna la recensione
        elif 'review_id' in request.form:
            review_id = request.form.get('review_id')
            review_title = request.form.get('review_title')
            review_content = request.form.get('review_content')
            selected_product_id = request.form.get('product_id')
            if not all([review_id, review_title, review_content]):
                flash("Tutti i campi devono essere compilati.", "danger")
            else:
                modified = update_review(review_id, review_title, review_content)
                if modified:
                    flash("Recensione aggiornata!", "success")
                else:
                    flash("Recensione non trovata o nessuna modifica.", "warning")
                # Ricarica le recensioni per il prodotto selezionato
                if selected_product_id:
                    reviews = list(db.reviews.find({"product_id": selected_product_id}))

    return render_template('update_review.html', products=products, selected_product_id=selected_product_id,
                           reviews=reviews)


@app.route('/remove_review', methods=['GET', 'POST'])
def remove_review_route():
    products = list(db.products.find({}, {"product_id": 1, "product_name": 1}))
    reviews = []
    selected_product_id = None

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        review_id = request.form.get('review_id')

        if product_id and not review_id:
            # Selezionato solo prodotto, carico recensioni
            reviews = list(db.reviews.find({"product_id": product_id}))
            selected_product_id = product_id
        elif product_id and review_id:
            # Selezionato prodotto e recensione → procedo a rimuovere
            review = db.reviews.find_one({"review_id": review_id, "product_id": product_id})
            if not review:
                flash("Recensione non trovata per questo prodotto.", "warning")
            else:
                removed = remove_review(product_id, review_id)
                if removed:
                    flash("Recensione rimossa con successo!", "success")
                else:
                    flash("Errore durante la rimozione.", "danger")
        else:
            flash("Seleziona un prodotto.", "warning")

    return render_template('remove_review.html', products=products, reviews=reviews, selected_product_id=selected_product_id)


@app.route('/read_review', methods=['GET', 'POST'])
def read_review_route():
    products = list(db.products.find())
    reviews = []
    selected_review = None
    selected_product_id = request.form.get('product_id')
    selected_product = None
    selected_user = None

    if selected_product_id:
        reviews = list(db.reviews.find({"product_id": selected_product_id}))
        if request.form.get('review_id'):
            review_id = request.form.get('review_id')
            selected_review = db.reviews.find_one({"review_id": review_id})
            if selected_review:
                selected_product = db.products.find_one({"product_id": selected_review.get("product_id")})
                selected_user = db.users.find_one({"user_id": selected_review.get("user_id")})
    return render_template("read_review.html",
                           products=products,
                           reviews=reviews,
                           selected_review=selected_review,
                           selected_product_id=selected_product_id,
                           selected_product=selected_product,
                           selected_user=selected_user)


#-------SEARCH ROUTES--------
@app.route('/search_products', methods=['GET', 'POST'])
def search_products():
    results = []
    from crud import categories_col
    categories = categories_col.distinct("category_name")

    if request.method == 'POST':
        category_filter = request.form.get('category_name')
        min_rating = request.form.get('min_rating')
        price_min = request.form.get('min_price')
        price_max = request.form.get('max_price')

        pipeline = []

        # Filtra solo prodotti che hanno prezzo come stringa
        pipeline.append({"$match": {"discounted_price": {"$type": "string"}}})

        # Rimuovi simboli e converti il prezzo in numero
        pipeline += [
            {"$addFields": {
                "price_no_rupia": {"$replaceAll": {
                    "input": "$discounted_price",
                    "find": "₹",
                    "replacement": ""
                }}
            }},
            {"$addFields": {
                "price_clean": {"$replaceAll": {
                    "input": "$price_no_rupia",
                    "find": ",",
                    "replacement": ""
                }}
            }},
            {"$addFields": {
                "price_num": {"$toDouble": "$price_clean"}
            }}
        ]

        # Costruisci filtro per prezzo
        price_filter = {}
        if price_min:
            price_filter["$gte"] = float(price_min)
        if price_max:
            price_filter["$lte"] = float(price_max)

        match_filter = {}

        if price_filter:
            match_filter["price_num"] = price_filter

        # Filtro per categoria (se selezionata)
        if category_filter:
            match_filter["categories"] = category_filter

        #Filtro per rating (convertito in float)
        if min_rating:
            try:
                rating_value = float(min_rating)
                match_filter["rating"] = {"$gte": rating_value}
            except:
                pass  # Ignora se non valido

        # Applica i filtri finali
        pipeline.append({"$match": match_filter})

        #Ottieni i risultati
        results = list(db.products.aggregate(pipeline))

    return render_template("search_products.html", results=results, categories=categories)


@app.route('/search_reviews', methods=['GET', 'POST'])
def search_reviews():
    results = []
    #recupero i prodotti e gli utenti per effettuare la ricerca mirata
    products = list(db.products.find({}, {"_id": 0, "product_id": 1, "product_name": 1}).sort("product_name", 1))
    users = list(db.users.find({}, {"_id": 0, "user_id": 1, "user_name": 1}).sort("user_name",1))

    #quando facciamo la ricerca, creiamo la query
    if request.method == 'POST':
        query = {}
        #se il campo prodotto è stato selezionato, aggiungiamo il filtro product_id alla query
        #quindi avremo la ricerca in base all'id del nome prodotto selezionato
        if request.form.get('product_id'):
            query['product_id'] = request.form['product_id']
        #stesso per user_id
        if request.form.get('user_id'):
            query['user_id'] = request.form['user_id']

        #recuperiamo le recensioni che rispettano la query
        reviews = list(db.reviews.find(query))

        # Creiamo dizionari di lookup per simulare la join per prodotti e utenti
        product_dict = {p['product_id']: p['product_name'] for p in products}
        user_dict = {u['user_id']: u['user_name'] for u in users}

        # Arricchiamo le recensioni con i nomi
        for r in reviews:
            r['product_name'] = product_dict.get(r['product_id'], 'Prodotto sconosciuto')
            r['user_name'] = user_dict.get(r['user_id'], 'Utente sconosciuto')

        results = reviews

    return render_template("search_reviews.html", results=results, products=products, users=users)





if __name__ == '__main__':
    app.run(debug=True)
