from flask import Flask, request, render_template, flash, session, redirect
from mysqlconnection import MySQLConnector
from flask.ext.bcrypt import Bcrypt
import re
import time
app = Flask(__name__)
app.secret_key = "4821e1b816783408324e587d0ad31ce4"
bcrypt = Bcrypt(app)
mysql = MySQLConnector(app, 'walldb')
email_regex = r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$'

@app.route('/')
def index():
    if "id" in session:
        return redirect('/wall')
    else:
        return render_template('index.html')

@app.route('/login', methods=["POST"])
def login():
    email = request.form["email"]
    query = "SELECT * FROM users WHERE email = :email LIMIT 1"
    data = { "email": email}
    user = mysql.query_db(query, data)
    if user:
        if bcrypt.check_password_hash(user[0]['pw_hash'], request.form["password"]):
            session["id"] = user[0]["id"]
            session["name"] = user[0]["first_name"]
            return redirect("/wall")
        else:
            flash("Invalid username or password")
            return redirect('/')
    else:
        flash("Invalid username or password")
        return redirect('/')


@app.route('/register', methods=["POST"])
def register():
    valid = True
    if (len(request.form["first_name"]) < 3) or not (re.search(r'^[a-zA-Z]+$', request.form["first_name"])):
        flash("First Name field must be letters only and be at least 2 characters")
        valid = False
    if (len(request.form["last_name"]) < 3) or not (re.search(r'^[a-zA-Z]+$', request.form["last_name"])):
        flash("Last Name field must be letters only and be at least 2 characters")
        valid = False
    if not re.match(email_regex, request.form["email"]):
        flash("Invalid email")
        valid = False
    if len(request.form["password"]) < 8:
        flash("Password must be at least 8 characters")
        valid = False
    if not (request.form["password"] == request.form["confirm_password"]):
        flash("Passwords must match")
        valid = False
    query = "SELECT * FROM users WHERE email = :email LIMIT 1"
    data = { "email": request.form["email"]}
    user = mysql.query_db(query, data)
    if user:
        flash("Email address already registered")
        valid = False

    if valid == False:
            return redirect('/')
            print request.form
    else:
        first_name = request.form["first_name"].title()
        last_name = request.form["last_name"].title()
        email = request.form["email"]
        pw_hash = bcrypt.generate_password_hash(request.form["password"])
        query = "INSERT INTO users (first_name, last_name, email, pw_hash, created_at, updated_at) VALUES (:first_name, :last_name, :email, :pw_hash, NOW(), NOW())"
        data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "pw_hash": pw_hash
        }
        mysql.query_db(query, data)
        query = "SELECT * FROM users WHERE email = :email LIMIT 1"
        data = { "email": email}
        user = mysql.query_db(query, data)
        session["id"] = user[0]["id"]
        session["name"] = user[0]["first_name"]
        return redirect('/wall')

@app.route('/wall')
def wall():
    if "id" in session:
        query = "SELECT first_name, last_name, NOW()-messages.created_at AS DIFF, DATE_FORMAT(messages.created_at, '%M %e %Y') AS 'created_at', message, messages.id, users.id as 'users_id' FROM messages JOIN users ON messages.users_id=users.id ORDER BY messages.created_at DESC"
        messages = mysql.query_db(query)
        query = "SELECT first_name, last_name, DATE_FORMAT(comments.created_at, '%M %e %Y') AS 'created_at', comment, messages.id, comments.users_id, comments.id as 'comments_id' FROM comments JOIN users ON comments.users_id=users.id JOIN messages ON comments.messages_id=messages.id ORDER BY created_at ASC"
        comments = mysql.query_db(query)
        return render_template('wall.html', messages=messages, comments=comments)
    else:
        return redirect('/failure')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/failure')
def failure():
    return render_template('failure.html')

@app.route('/message', methods=["POST"])
def message():
    if(len(request.form["message"]) < 1):
        flash("Nothing in message")
        return redirect('/wall')
    else:
        query = "INSERT INTO messages (users_id, message, created_at, updated_at) VALUES (:user_id, :message, NOW(), NOW())"
        data = {
            "user_id": session['id'],
            "message": request.form["message"]
        }
        mysql.query_db(query, data)
        return redirect('/wall')

@app.route('/comment', methods=["POST"])
def comment():
    if(len(request.form["comment"]) < 1):
        flash("Nothing in comment")
        return redirect('/wall')
    else:
        query = "INSERT INTO comments (users_id, messages_id, comment, created_at, updated_at) VALUES (:user_id, :messages_id, :comment, NOW(), NOW())"
        data = {
            "user_id": session['id'],
            "messages_id": request.form["comment_parent"],
            "comment": request.form["comment"]
        }
        mysql.query_db(query, data)
        return redirect('/wall')

@app.route('/delete/comment/<comment_id>')
def delete_comment(comment_id):
    query = "DELETE FROM comments WHERE id=:comment_id"
    data = {
        "comment_id": comment_id
    }
    mysql.query_db(query, data)
    return redirect('/wall')

@app.route('/delete/message/<message_id>')
def delete_message(message_id):
    query = "SELECT NOW()-created_at AS DIFF FROM messages WHERE id=:message_id"
    data = {
        "message_id": message_id
    }
    time = mysql.query_db(query, data)
    if time[0]["DIFF"] > 1800:
        flash("Cannot delete messages from more than 30 minutes ago")
        return redirect('/wall')
    else:
        query = "DELETE FROM messages WHERE id=:message_id"
        mysql.query_db(query, data)
        return redirect('/wall')





app.run(debug=True)
