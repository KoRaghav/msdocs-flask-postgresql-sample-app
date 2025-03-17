import os
from datetime import datetime
import requests
from flask import Flask, redirect, render_template, request, send_from_directory, url_for
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from identity.flask import Auth
import app_config

app = Flask(__name__, static_folder='static')
csrf = CSRFProtect(app)
app.config.from_object(app_config)
auth = Auth(
    app,
    authority=app.config["AUTHORITY"],
    client_id=app.config["CLIENT_ID"],
    client_credential=app.config["CLIENT_SECRET"],
    redirect_uri=app.config["REDIRECT_URI"]
)

if 'WEBSITE_HOSTNAME' not in os.environ:
    # local development, where we'll use environment variables
    print("Loading config.development and environment variables from .env file.")
    app.config.from_object('azureproject.development')
else:
    # production
    print("Loading config.production.")
    app.config.from_object('azureproject.production')

app.config.update(
    SQLALCHEMY_DATABASE_URI=app.config.get('DATABASE_URI'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
from models import Product, Review

@app.route('/', methods=['GET'])
@auth.login_required
def index(*, context):
    print('Request for index page received')
    products = Product.query.all()
    return render_template('index.html', products=products, user=context['user'])

@app.route('/<int:id>', methods=['GET'])
@auth.login_required
def details(id, context):
    product = Product.query.where(Product.id == id).first()
    reviews = Review.query.where(Review.product == id)
    return render_template('details.html', product=product, reviews=reviews, user=context['user'])

@app.route('/create', methods=['GET'])
@auth.login_required
def create_product(*, context):
    print('Request for add product page received')
    return render_template('create_product.html', user=context['user'])

@app.route('/add', methods=['POST'])
@csrf.exempt
def add_product():
    name = request.values.get('product_name')
    description = request.values.get('description')

    product = Product()
    product.name = name
    product.description = description
    db.session.add(product)
    db.session.commit()

    return redirect(url_for('details', id=product.id))

@app.route('/review/<int:id>', methods=['POST'])
@auth.login_required
@csrf.exempt
def add_review(id, context):
    try:
        user_name = context['user'].get('name')
        rating = request.values.get('rating')
        review_text = request.values.get('review_text')
    except (KeyError):
        #Redisplay the question voting form.
        return render_template('add_review.html', {
            'error_message': "Error adding review",
        })
    else:
        review = Review()
        review.product = id
        review.review_date = datetime.now()
        review.user_name = user_name
        review.rating = int(rating)
        review.review_text = review_text
        db.session.add(review)
        db.session.commit()

    return redirect(url_for('details', id=id))

@app.context_processor
def utility_processor():
    def star_rating(id):
        reviews = Review.query.where(Review.product == id)

        ratings = []
        review_count = 0
        for review in reviews:
            ratings += [review.rating]
            review_count += 1

        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        stars_percent = round((avg_rating / 5.0) * 100) if review_count > 0 else 0
        return {'avg_rating': avg_rating, 'review_count': review_count, 'stars_percent': stars_percent}

    return dict(star_rating=star_rating)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run()
