from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
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
    search_prefix = request.form.get('product_name', "").strip() if request.method == 'POST' else ""

    if search_prefix:
        # Trova il primo prodotto esatto con quel prefisso
        product = db.products.find_one({
            "product_name": {"$regex": f"^{search_prefix}", "$options": "i"}
        })

        if not product:
            flash("Prodotto non trovato.", "warning")

        # Lista dei prodotti che iniziano per il prefisso
        products = list(db.products.find(
            {"product_name": {"$regex": f"^{search_prefix}", "$options": "i"}},
            {"_id": 0, "product_name": 1}
        ).sort("product_name", 1))
    else:
        # Nessun prefisso: mostra tutti i prodotti
        products = list(db.products.find({}, {"_id": 0, "product_name": 1}).sort("product_name", 1))

    return render_template("read_product.html", product=product, products=products, search_prefix=search_prefix)



from flask import render_template, request, redirect, url_for, flash
from app import app, db
from crud import update_product, categories_col

@app.route('/update_product', methods=['GET', 'POST'])
def update_product_route():
    categories = categories_col.distinct("category_name")
    search_prefix = ""
    product = None

    if request.method == 'POST':
        product_id = request.form.get('product_id')

        # Controlla se è una richiesta di aggiornamento (ci sono almeno uno dei campi extra)
        if product_id and any(request.form.get(field) for field in [
            'product_name', 'product_description', 'product_category',
            'product_price', 'product_discount', 'product_rating', 'product_link'
        ]):
            update_data = {}

            if request.form.get('product_name'):
                update_data['product_name'] = request.form['product_name'].strip()

            if request.form.get('product_description'):
                update_data['product_description'] = request.form['product_description'].strip()

            if request.form.get('product_category'):
                update_data['product_category'] = request.form['product_category'].strip()

            if request.form.get('product_price'):
                try:
                    update_data['product_price'] = float(request.form['product_price'])
                except ValueError:
                    flash("Prezzo non valido.", "danger")

            if request.form.get('product_discount'):
                try:
                    update_data['product_discount'] = float(request.form['product_discount'])
                except ValueError:
                    flash("Sconto non valido.", "danger")

            if request.form.get('product_rating'):
                try:
                    update_data['product_rating'] = float(request.form['product_rating'])
                except ValueError:
                    flash("Valutazione non valida.", "danger")

            if request.form.get('product_link'):
                update_data['product_link'] = request.form['product_link'].strip()

            if update_data:
                result = db.products.update_one(
                    {'product_id': product_id},
                    {'$set': update_data}
                )
                if result.modified_count > 0:
                    flash("Prodotto aggiornato con successo!", "success")
                else:
                    flash("Nessuna modifica effettuata o prodotto non trovato.", "warning")
            else:
                flash("Nessun campo compilato per l'aggiornamento.", "danger")

            # Dopo aggiornamento ricarica il prodotto aggiornato
            product = db.products.find_one({'product_id': product_id})

        # Se l'utente ha solo selezionato un prodotto
        elif product_id:
            product = db.products.find_one({'product_id': product_id})

    # Recupera il prefisso usato per la ricerca (dalla barra input se presente)
    search_prefix = request.form.get('search_prefix', "") if request.method == 'POST' else ""

    if search_prefix:
        products = list(db.products.find(
            {"product_name": {"$regex": f"^{search_prefix}", "$options": "i"}},
            {"_id": 0, "product_id": 1, "product_name": 1}
        ).sort("product_name", 1))
    else:
        products = list(db.products.find(
            {}, {"_id": 0, "product_id": 1, "product_name": 1}
        ).sort("product_name", 1))

    return render_template('update_product.html',
                           categories=categories,
                           products=products,
                           product=product,
                           search_prefix=search_prefix)



from flask import render_template, request, redirect, url_for, flash
from app import app, db
from crud import delete_product

@app.route('/delete_product', methods=['GET', 'POST'])
def delete_product_route():
    product_id = None
    search_prefix = ""

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        search_prefix = request.form.get('search_prefix', "").strip()

        if product_id:
            deleted = delete_product(product_id)
            if deleted:
                flash("Prodotto eliminato.", "success")
            else:
                flash("Prodotto non trovato.", "warning")
    else:
        search_prefix = request.args.get('search_prefix', "").strip()

    # Filtraggio dei prodotti in base al prefisso
    if search_prefix:
        products = list(db.products.find(
            {"product_name": {"$regex": f"^{search_prefix}", "$options": "i"}},
            {"_id": 0, "product_id": 1, "product_name": 1}
        ).sort("product_name", 1))
    else:
        products = list(db.products.find(
            {}, {"_id": 0, "product_id": 1, "product_name": 1}
        ).sort("product_name", 1))

    return render_template('delete_product.html',
                           products=products,
                           search_prefix=search_prefix)


# ----------- REVIEW ROUTES -----------

@app.route('/add_review', methods=['GET', 'POST'])
def add_review_route():
    # Ottieni utenti e prodotti ordinati alfabeticamente
    users = list(db.users.find({}, {"_id": 0, "user_id": 1, "user_name": 1}).sort("user_name", 1))
    products = list(db.products.find({}, {"_id": 0, "product_id": 1, "product_name": 1}).sort("product_name", 1))

    if request.method == 'POST':
        # Pulizia input
        review_id = request.form.get('review_id', '').strip()
        product_id = request.form.get('product_id', '').strip()
        user_id = request.form.get('user_id', '').strip()
        review_title = request.form.get('review_title', '').strip()
        review_content = request.form.get('review_content', '').strip()

        # Verifica campi obbligatori
        if not all([review_id, product_id, user_id, review_title, review_content]):
            flash("Tutti i campi sono obbligatori.", "danger")
            return render_template('create_review.html', users=users, products=products)

        # (Opzionale) Controllo duplicato ID recensione
        if db.reviews.find_one({"review_id": review_id}):
            flash("Esiste già una recensione con questo ID.", "danger")
            return render_template('create_review.html', users=users, products=products)

        # Creazione recensione
        try:
            add_review(
                product_id,
                review_id,
                user_id,
                review_title,
                review_content
            )
            flash("Recensione aggiunta con successo!", "success")
            return redirect(url_for('add_review_route'))
        except Exception as e:
            flash(f"Errore durante l'inserimento: {str(e)}", "danger")
            return render_template('create_review.html', users=users, products=products)

    return render_template('create_review.html', users=users, products=products)



@app.route('/update_review', methods=['GET', 'POST'])
def update_review_route():
    products = list(db.products.find())
    selected_product_id = None
    reviews = []
    selected_review = None

    if request.method == 'POST':
        selected_product_id = request.form.get('product_id')

        if 'product_id' in request.form and 'review_id' not in request.form:
            if selected_product_id:
                reviews = list(db.reviews.find({"product_id": selected_product_id}))

        elif 'review_id' in request.form and 'review_title' not in request.form:
            selected_review_id = request.form.get('review_id')
            if selected_product_id:
                reviews = list(db.reviews.find({"product_id": selected_product_id}))
            if selected_review_id:
                selected_review = db.reviews.find_one({"review_id": selected_review_id})

        elif 'review_id' in request.form and 'review_title' in request.form:
            review_id = request.form.get('review_id')
            review_title = request.form.get('review_title')
            review_content = request.form.get('review_content')

            if not all([review_id, review_title, review_content]):
                flash("Tutti i campi devono essere compilati.", "danger")
            else:
                modified = update_review(review_id, review_title, review_content)
                if modified:
                    flash("Recensione aggiornata!", "success")
                else:
                    flash("Recensione non trovata o nessuna modifica.", "warning")
            if selected_product_id:
                reviews = list(db.reviews.find({"product_id": selected_product_id}))

    return render_template(
        'update_review.html',
        products=products,
        selected_product_id=selected_product_id,
        reviews=reviews,
        selected_review=selected_review
    )


from flask import session

@app.route('/remove_review', methods=['GET', 'POST'])
def remove_review_route():
    prefix = request.form.get('search_prefix', '').strip()
    selected_product_id = request.form.get('product_id')
    review_id = request.form.get('review_id')
    action = request.form.get('action')  # 'search' o 'remove' o None
    reviews = []

    if prefix:
        products = list(db.products.find(
            {"product_name": {"$regex": f"^{prefix}", "$options": "i"}},
            {"_id": 0, "product_id": 1, "product_name": 1}
        ).sort("product_name", 1))
    else:
        products = list(db.products.find(
            {}, {"_id": 0, "product_id": 1, "product_name": 1}
        ).sort("product_name", 1))

    if action == 'remove':
        if selected_product_id and review_id:
            review = db.reviews.find_one({"review_id": review_id, "product_id": selected_product_id})
            if not review:
                flash("Recensione non trovata per questo prodotto.", "warning")
            else:
                removed = remove_review(selected_product_id, review_id)
                if removed:
                    flash("Recensione rimossa con successo!", "success")
                    session['just_removed'] = True  # ✅ Solo se rimozione avvenuta
                else:
                    flash("Errore durante la rimozione.", "danger")
        else:
            flash("Seleziona un prodotto e una recensione da rimuovere.", "warning")

        # aggiorna le recensioni se il prodotto è ancora selezionato
        if selected_product_id:
            reviews = list(db.reviews.find({"product_id": selected_product_id}))

    elif action == 'search' and selected_product_id:
        reviews = list(db.reviews.find({"product_id": selected_product_id}))

    return render_template(
        'remove_review.html',
        products=products,
        reviews=reviews,
        selected_product_id=selected_product_id,
        search_prefix=prefix
    )





@app.route('/read_review', methods=['GET', 'POST'])
def read_review_route():
    products = list(db.products.find())
    reviews = []
    selected_review = None
    selected_product_id = request.form.get('product_id')
    selected_product = None
    selected_user = None

    prefix = request.form.get('name_prefix', '').strip()

    # Filtro prodotti per prefisso nome
    if prefix:
        products = [p for p in products if p['product_name'].lower().startswith(prefix.lower())]

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
    selected_product = None

    from crud import categories_col
    categories = categories_col.distinct("category_name")

    if request.method == 'POST':
        category_filter = request.form.get('category_name')
        min_rating = request.form.get('min_rating')
        price_min = request.form.get('min_price')
        price_max = request.form.get('max_price')
        product_id = request.form.get('product_id')

        pipeline = []

        pipeline.append({"$match": {"discounted_price": {"$type": "string"}}})

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

        price_filter = {}
        if price_min:
            price_filter["$gte"] = float(price_min)
        if price_max:
            price_filter["$lte"] = float(price_max)

        match_filter = {}

        if price_filter:
            match_filter["price_num"] = price_filter

        if category_filter:
            match_filter["categories"] = category_filter

        if min_rating:
            try:
                rating_value = float(min_rating)
                match_filter["rating"] = {"$gte": rating_value}
            except:
                pass

        pipeline.append({"$match": match_filter})
        results = list(db.products.aggregate(pipeline))

        if product_id:
            selected_product = db.products.find_one({"product_id": product_id})

    # products_list contiene solo i prodotti risultati dalla ricerca
    products_list = results if results else []

    return render_template("search_products.html", results=results, categories=categories, products=products_list, selected_product=selected_product)


from flask import redirect, url_for

@app.route('/search_reviews', methods=['GET', 'POST'])
def search_reviews():
    products = list(db.products.find({}, {"_id": 0, "product_id": 1, "product_name": 1}).sort("product_name", 1))
    users = []
    query = {}
    page = int(request.args.get('page', 1))
    per_page = 5
    selected_product = None
    selected_user = None

    if request.method == 'POST':
        if 'reset' in request.form:
            return redirect(url_for('search_reviews'))

        selected_product = request.form.get('product_id') or None
        selected_user = request.form.get('user_id') or None

        return redirect(url_for('search_reviews', product_id=selected_product, user_id=selected_user, page=1))

    # Metodo GET
    selected_product = request.args.get('product_id') or None
    selected_user = request.args.get('user_id') or None

    if selected_product:
        query['product_id'] = selected_product
    if selected_user:
        query['user_id'] = selected_user

    if selected_product and not selected_user:
        user_ids = db.reviews.distinct('user_id', {'product_id': selected_product})
        users = list(db.users.find({'user_id': {'$in': user_ids}}, {"_id": 0, "user_id": 1, "user_name": 1}).sort("user_name", 1))
    else:
        users = list(db.users.find({}, {"_id": 0, "user_id": 1, "user_name": 1}).sort("user_name", 1))

    all_reviews = list(db.reviews.find(query))
    total = len(all_reviews)
    start = (page - 1) * per_page
    end = start + per_page
    reviews_page = all_reviews[start:end]

    product_dict = {p['product_id']: p['product_name'] for p in products}
    user_dict = {u['user_id']: u['user_name'] for u in users}

    for r in reviews_page:
        r['product_name'] = product_dict.get(r['product_id'], 'Prodotto sconosciuto')
        r['user_name'] = user_dict.get(r['user_id'], 'Utente sconosciuto')

    return render_template("search_reviews.html",
                           results=reviews_page if reviews_page else None,
                           products=products,
                           users=users,
                           selected_product=selected_product,
                           selected_user=selected_user,
                           page=page,
                           total=total,
                           per_page=per_page)


if __name__ == '__main__':
    app.run(debug=True)
