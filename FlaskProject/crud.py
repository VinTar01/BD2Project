from pymongo import MongoClient
from pymongo.server_api import ServerApi


uri = "mongodb+srv://vtarantino96:MProject010@cluster0.c5pfztz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connessione
client = MongoClient(uri, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print(" Connessione a MongoDB Atlas riuscita!")
except Exception as e:
    print(" Errore durante la connessione:", e)


db = client["AmazonDB"]

# Collezioni
products_col = db.products
categories_col = db.categories
users_col = db.users
reviews_col = db.reviews


# --- CRUD PRODOTTI ---

def create_product(product_id, product_name, discounted_price, actual_price,
                   discount_percentage, rating, rating_count, about_product,
                   img_link, product_link, category_names):
    # Verifica che tutte le categorie esistano
    existing_categories = categories_col.distinct("category_name")
    missing = set(category_names) - set(existing_categories)
    if missing:
        raise ValueError(f"Le seguenti categorie non esistono: {missing}")

    # Verifica se il prodotto esiste già
    if products_col.find_one({"product_id": product_id}):
        raise ValueError(f"Prodotto con ID '{product_id}' già esistente.")

    new_product = {
        "product_id": product_id,
        "product_name": product_name,
        "discounted_price": discounted_price,
        "actual_price": actual_price,
        "discount_percentage": discount_percentage,
        "rating": rating,
        "rating_count": rating_count,
        "about_product": about_product,
        "img_link": img_link,
        "product_link": product_link,
        "categories": category_names,
        "reviews": []  # Inizialmente vuoto
    }

    result = products_col.insert_one(new_product)
    return result.inserted_id


def read_product(product_id):
    return products_col.find_one({"product_id": product_id})


def update_product(product_id, product_name, product_description, product_category,
                   price, discount=0, rating=0, ref_link=''):
    result = db.products.update_one(
        {"product_id": product_id},
        {"$set": {
            "product_name": product_name,
            "product_description": product_description,
            "product_category": product_category,
            "price": price,
            "discount": discount,
            "rating": rating,
            "ref_link": ref_link
        }}
    )
    return result.modified_count > 0



def delete_product(product_id):
    # Rimuove anche tutte le recensioni dalla collection reviews
    reviews_col.delete_many({"product_id": product_id})
    result = products_col.delete_one({"product_id": product_id})
    return result.deleted_count


# --- CRUD RECENSIONI ---

def add_review(product_id, review_id, user_id, review_title, review_content):
    # Verifica esistenza prodotto
    product = products_col.find_one({"product_id": product_id})
    if not product:
        raise ValueError(f"Prodotto con ID '{product_id}' non esiste.")

    # Verifica esistenza utente
    user = users_col.find_one({"user_id": user_id})
    if not user:
        raise ValueError(f"Utente con ID '{user_id}' non esiste.")

    # Verifica che la recensione non esista già
    if reviews_col.find_one({"review_id": review_id}):
        raise ValueError(f"Recensione con ID '{review_id}' già esistente.")

    review = {
        "review_id": review_id,
        "product_id": product_id,
        "user_id": user_id,
        "review_title": review_title,
        "review_content": review_content
    }

    # Inserisce nella collezione reviews
    reviews_col.insert_one(review)

    # Aggiunge la recensione al prodotto (embedded)
    products_col.update_one(
        {"product_id": product_id},
        {"$push": {"reviews": review}}
    )

    # Ricalcola rating_count
    new_rating_count = reviews_col.count_documents({"product_id": product_id})
    products_col.update_one(
        {"product_id": product_id},
        {"$set": {"rating_count": new_rating_count}}
    )

    return True


def update_review(review_id, new_title, new_content):
    # Aggiorna nella collezione reviews
    result1 = reviews_col.update_one(
        {"review_id": review_id},
        {"$set": {
            "review_title": new_title,
            "review_content": new_content
        }}
    )

    # Aggiorna anche nel documento embedded dentro products
    result2 = products_col.update_one(
        {"reviews.review_id": review_id},
        {"$set": {
            "reviews.$.review_title": new_title,
            "reviews.$.review_content": new_content
        }}
    )

    return result1.modified_count + result2.modified_count


def remove_review(product_id, review_id):
    # Verifica che il prodotto esista
    if not products_col.find_one({"product_id": product_id}):
        raise ValueError(f"Prodotto con ID '{product_id}' non esiste.")

    # Rimuove dalla collezione reviews
    result1 = reviews_col.delete_one({"review_id": review_id})

    # Rimuove dal prodotto
    result2 = products_col.update_one(
        {"product_id": product_id},
        {"$pull": {"reviews": {"review_id": review_id}}}
    )

    #  Ricalcola rating_count
    new_rating_count = reviews_col.count_documents({"product_id": product_id})
    products_col.update_one(
        {"product_id": product_id},
        {"$set": {"rating_count": new_rating_count}}
    )

    return result1.deleted_count + result2.modified_count


