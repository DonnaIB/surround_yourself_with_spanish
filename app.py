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
    user = mongo.db.users.find_one(
        {"username": session["user"]})["is_admin"]
    return render_template(
        "recommendations.html", recommendations=recommendations, user=user)


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
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    if session["user"]:
        my_recommendations = list(mongo.db.recommendations.find(
            {"created_by": session["user"]}).sort("time_created"))

        return render_template(
            "profile.html", 
            username=username, 
            my_recommendations=my_recommendations)

    return redirect(url_for("login"))


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
    if request.method == "POST":
        selected_category = mongo.db.categories.find_one(
            {"category_name": request.form.get("category_name")})
        selected_admin = mongo.db.users.find_one(
            {"username": session["user"]})
        recommendation = {
            "category_name": request.form.get("category_name"),
            "category_icon": selected_category["category_icon"],
            "rec_name": request.form.get("rec_name"),
            "rec_by": request.form.get("rec_by"),
            "rec_description": request.form.get("rec_description"),
            "level": request.form.get("level"),
            "rec_rating": request.form.get("rec_rating"),
            "created_by": session["user"],
            "is_admin": selected_admin["is_admin"],
            "time_created": now.strftime("%d/%m/%Y, %H:%M:%S")
        }
        mongo.db.recommendations.insert_one(recommendation)
        flash("Yay!")
        return redirect(url_for("get_recommendations"))

    categories = mongo.db.categories.find().sort("category_name", 1)
    level = mongo.db.level.find()
    return render_template(
        "add_recommendation.html", categories=categories, level=level)


# Lets a user edit a recommendation
@app.route("/edit_recommendation/<recommendation_id>", methods=["GET", "POST"])
def edit_recommendation(recommendation_id):
    now = datetime.now()
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
            {"_id": ObjectId(recommendation_id)},submit)
        flash("Your recommendation has been updated!")

    recommendation = mongo.db.recommendations.find_one(
        {"_id": ObjectId(recommendation_id)})
    categories = mongo.db.categories.find().sort("category_name", 1)
    level = mongo.db.level.find()
    return render_template(
        "edit_recommendation.html",recommendation=recommendation, 
        categories=categories, level=level)


# Lets a user delete thier recommendation
@app.route("/delete_recommendation/<recommendation_id>")
def delete_recommendation(recommendation_id):
    mongo.db.recommendations.remove({"_id": ObjectId(recommendation_id)})
    flash("Your recommendation has been deleted")
    return redirect(url_for("get_recommendations"))
    

if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)