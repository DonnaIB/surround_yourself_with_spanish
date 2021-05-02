import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


# render main recommendations page
@app.route("/")
@app.route("/get_recommendations")
def get_recommendations():
    recommendations = list(mongo.db.recommendations.find())
    if "user" in session:
        user = mongo.db.users.find_one(
           {"username": session["user"]})
        return render_template(
           "recommendations.html", recommendations=recommendations, user=user)  
    else:
        return render_template(
           "recommendations.html", recommendations=recommendations, user="")  


# search database
@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    recommendations = list(
        mongo.db.recommendations.find({"$text": {"$search": query}}))
    return render_template(
        "recommendations.html", recommendations=recommendations, user="")


# register a new user
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get('username').lower()})

        if existing_user:
            flash("Username already exist. Please chose another username")
            return redirect(url_for("register"))    

            # check if email already exists in db
        existing_email = mongo.db.users.find_one(
            {"email": request.form.get("email").lower()})

        if existing_email:
            flash("Email already registered!")
            return redirect(url_for("register"))

        # add user details to the database
        register = {
            "username": request.form.get("username").lower(),
            "email": request.form.get("email").lower(),
            "password": generate_password_hash(request.form.get("password")),
            "is_admin": False
        }
        mongo.db.users.insert_one(register)

        # session cookie for new user
        session["user"] = request.form.get("username").lower()
        flash("Congratulations! You are now registered.")
        return redirect(url_for("profile", username=session["user"]))
    return render_template("register.html")


# user login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})
    
        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                session["user"] = request.form.get("username").lower()
                return redirect(url_for("profile", username=session["user"]))            
                
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))
    
        else:
            # username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


# display user's recommendations on  profile page
@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    if "user" in session:
        username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
        my_recommendations = list(mongo.db.recommendations.find(
            {"created_by": session["user"]}).sort("time_created"))

        return render_template(
            "profile.html", 
            username=username, 
            my_recommendations=my_recommendations)

    return render_template('404.html'), 404


# Logs user out of their account
@app.route("/logout")
def logout():
    # remove user from session cookie
    flash("You have successfully logged out")
    session.pop("user")
    return redirect(url_for("login"))


# Lets a user add a new recommendation
@app.route("/add_recommendation", methods=["GET", "POST"])
def add_recommendation():
    now = datetime.now()
    if "user" in session:
        if request.method == "POST":
            selected_category = mongo.db.categories.find_one(
                {"category_name": request.form.get("category_name")})
            recommendation = {
                "category_name": request.form.get("category_name"),
                "category_icon": selected_category["category_icon"],
                "rec_name": request.form.get("rec_name"),
                "rec_by": request.form.get("rec_by"),
                "rec_description": request.form.get("rec_description"),
                "level": request.form.get("level"),
                "rec_rating": request.form.get("rec_rating"),
                "created_by": session["user"],
                "time_created": now.strftime("%d/%m/%Y, %H:%M:%S")
                }
            mongo.db.recommendations.insert_one(recommendation)
            flash("Your recommendation has successfully been addded!")
            return redirect(url_for("get_recommendations"))

        categories = mongo.db.categories.find().sort("category_name", 1)
        level = mongo.db.level.find()
        return render_template(
            "add_recommendation.html", categories=categories, level=level)
    else:
        return render_template('404.html'), 404


# Lets a user edit a recommendation
@app.route("/edit_recommendation/<recommendation_id>", methods=["GET", "POST"])
def edit_recommendation(recommendation_id):
    now = datetime.now()
    if "user" in session:
        if request.method == "POST":
            selected_category = mongo.db.categories.find_one(
                {"category_name": request.form.get("category_name")})
            submit = {
                "category_name": request.form.get("category_name"),
                "category_icon": selected_category["category_icon"],
                "rec_name": request.form.get("rec_name"),
                "rec_by": request.form.get("rec_by"),
                "rec_description": request.form.get("rec_description"),
                "level": request.form.get("level"),
                "rec_rating": request.form.get("rec_rating"),
                "created_by": session["user"],
                "time_created": now.strftime("%d/%m/%Y, %H:%M:%S")
            }
            mongo.db.recommendations.update(
                {"_id": ObjectId(recommendation_id)}, submit)
            flash("Your recommendation has been updated!")

        recommendation = mongo.db.recommendations.find_one(
            {"_id": ObjectId(recommendation_id)})
        categories = mongo.db.categories.find().sort("category_name", 1)
        level = mongo.db.level.find()
        return render_template(
            "edit_recommendation.html", recommendation=recommendation, 
            categories=categories, level=level)
    else:
        return render_template('404.html'), 404


# Let a user delete their recommendation
@app.route("/delete_recommendation/<recommendation_id>")
def delete_recommendation(recommendation_id):
    mongo.db.recommendations.remove({"_id": ObjectId(recommendation_id)})
    flash("Your recommendation has been deleted")
    return redirect(url_for("get_recommendations"))


# return 404 error page
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# render categories page
@app.route("/get_categories")
def get_categories():
    categories = list(mongo.db.categories.find())
    if "user" in session:
        user = mongo.db.users.find_one(
           {"username": session["user"]})
        if user["is_admin"]:
            return render_template(
                "categories.html", categories=categories)  
        else:
            return render_template('404.html'), 404
    return render_template('404.html'), 404


# Lets an admin add a category
@app.route("/add_category", methods=["GET", "POST"])
def add_category():
    if "user" in session:
        user = mongo.db.users.find_one(
           {"username": session["user"]})
        if user["is_admin"]:
            existing_cat = mongo.db.categories.find_one(
                {"category_name": request.form.get('category_name')})

            if existing_cat:
                flash("Category already exists")

            elif request.method == "POST":
                category = {
                    "category_name": request.form.get("category_name"),
                    "category_icon": request.form.get("category_icon")
                    }
                mongo.db.categories.insert_one(category)
                flash("Your category has successfully been added!")

                categories = list(mongo.db.categories.find())
                return render_template(
                    "categories.html", categories=categories)
            return render_template("add_category.html")
    else:
        return render_template('404.html'), 404


# Let an admin edit a category
@app.route("/edit_category/<category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    if "user" in session:
        user = mongo.db.users.find_one(
           {"username": session["user"]})
        if user["is_admin"]:
            if request.method == "POST":

                submit = {
                    "category_name": request.form.get("category_name"),
                    "category_icon": request.form.get("category_icon"),
                    }

                mongo.db.categories.update(
                    {"_id": ObjectId(category_id)}, submit)
                flash("Your category has been updated!")
                
            category = mongo.db.categories.find_one(
                {"_id": ObjectId(category_id)})
            return render_template(
                "edit_category.html", category=category)
    else:
        return render_template('404.html'), 404


# Let an admin delete a category
@app.route("/delete_category/<category_id>")
def delete_category(category_id):
    mongo.db.categories.remove({"_id": ObjectId(category_id)})
    flash("Category has been deleted")
    categories = list(mongo.db.categories.find())
    return render_template(
        "categories.html", categories=categories)


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)