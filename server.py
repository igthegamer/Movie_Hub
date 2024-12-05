# server.py

from flask import Flask, render_template, request, redirect, session, flash
from flask_bcrypt import Bcrypt
from mysqlconnection import connectToMySQL
from nextfix_app import app


bcrypt = Bcrypt(app)

@app.route('/', methods=['GET', 'POST'])
def register_login():
    if request.method == 'POST':
        if 'register_form' in request.form:
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            if len(first_name) < 2 or len(last_name) < 2:
                flash("First name and last name must be at least 2 characters", "registration")

            if len(password) < 8:
                flash("Password must be at least 8 characters", "registration")

            if password != confirm_password:
                flash("Passwords do not match", "registration")

            pw_hash = bcrypt.generate_password_hash(password)

            mysql = connectToMySQL('beltexam_db')

            query = "INSERT INTO users (first_name, last_name, email, password) VALUES (%(fn)s, %(ln)s, %(em)s, %(pw)s);"
            data = {
                'fn': first_name,
                'ln': last_name,
                'em': email,
                'pw': pw_hash
            }
            user_id = mysql.query_db(query, data)

            if user_id:
                session['user_id'] = user_id
                session['username'] = first_name
                return redirect('/dashboard')
            else:
                flash("Registration failed", "registration")

        elif 'login_form' in request.form:
            email = request.form['email']
            password = request.form['password']

            mysql = connectToMySQL('beltexam_db')

            query = "SELECT * FROM users WHERE email = %(email)s;"
            data = {'email': email}
            user = mysql.query_db(query, data)

            if user and bcrypt.check_password_hash(user[0]['password'], password):
                session['user_id'] = user[0]['id']
                session['username'] = user[0]['first_name']
                return redirect('/dashboard')

            else:
                flash("Invalid email/password", "login")

    return render_template('login_registration.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    mysql = connectToMySQL('beltexam_db')
    query = "SELECT * FROM shows;"
    shows = mysql.query_db(query)

    return render_template('dashboard.html', shows=shows)


@app.route('/shows/new', methods=['GET', 'POST'])
def create_show():
    if request.method == 'POST':
        title = request.form['title']
        network = request.form['network']
        release_date = request.form['release_date']
        description = request.form['description']

        if len(title) < 3 or len(network) < 3 or len(description) < 3:
            flash("Title, network, and description must be at least 3 characters", "create_show")
            return redirect('/shows/new')

        mysql = connectToMySQL('beltexam_db')
        query = "INSERT INTO shows (title, network, release_date, description, user_id) VALUES (%(title)s, %(network)s, %(release_date)s, %(description)s, %(user_id)s);"
        data = {
            'title': title,
            'network': network,
            'release_date': release_date,
            'description': description,
            'user_id': session['user_id']
        }
        show_id = mysql.query_db(query, data)

        if show_id:
            return redirect(f'/shows/{show_id}')

    return render_template('create_show.html')
def is_show_creator(show_id):
    mysql = connectToMySQL('beltexam_db')
    query = "SELECT user_id FROM shows WHERE id = %(show_id)s;"
    data = {'show_id': show_id}
    result = mysql.query_db(query, data)
    return session.get('user_id') == result[0]['user_id']

@app.route('/shows/<int:show_id>')
def view_show(show_id):
    mysql = connectToMySQL('beltexam_db')
    query = """
        SELECT shows.*, users.id AS creator_id, users.first_name AS creator_first_name
        FROM shows
        JOIN users ON shows.user_id = users.id
        WHERE shows.id = %(show_id)s;
    """
    data = {'show_id': show_id}
    show = mysql.query_db(query, data)

    query = """
        SELECT comments.id, comments.comment, comments.user_id, users.first_name, users.last_name 
        FROM comments 
        JOIN users ON comments.user_id = users.id 
        WHERE show_id = %(show_id)s;
    """
    comments = mysql.query_db(query, data)

    if not show:
        flash("Show not found", "error")
        return redirect('/dashboard')

    return render_template('show_details.html', show=show[0], comments=comments)

@app.route('/shows/<int:show_id>/comment', methods=['POST'])
def add_comment(show_id):
    if 'user_id' not in session:
        return redirect('/')

    comment = request.form['comment']

    mysql = connectToMySQL('beltexam_db')
    query = "INSERT INTO comments (comment, user_id, show_id) VALUES (%(comment)s, %(user_id)s, %(show_id)s);"
    data = {
        'comment': comment,
        'user_id': session['user_id'],
        'show_id': show_id
    }
    mysql.query_db(query, data)

    return redirect(f'/shows/{show_id}')

def comment_creator(comment_id):
    mysql = connectToMySQL('beltexam_db')
    query = "SELECT user_id FROM comments WHERE id = %(comment_id)s;"
    data = {'comment_id': comment_id}
    result = mysql.query_db(query, data)
    return result[0]['user_id']

@app.route('/shows/<int:show_id>/comments/<int:comment_id>/delete', methods=['POST'])
def delete_comment(show_id, comment_id):
    if 'user_id' not in session:
        return redirect('/')

    mysql = connectToMySQL('beltexam_db')
    query = "SELECT user_id FROM comments WHERE id = %(comment_id)s;"
    data = {'comment_id': comment_id}
    result = mysql.query_db(query, data)
    if result and session['user_id'] == result[0]['user_id']:
        # Delete the comment from the database
        query = "DELETE FROM comments WHERE id = %(comment_id)s;"
        mysql.query_db(query, data)

    return redirect(f'/shows/{show_id}')

@app.route('/shows/<int:show_id>/comments/<int:comment_id>/edit', methods=['POST'])
def edit_comment(show_id, comment_id):
    if 'user_id' not in session:
        return redirect('/')

    mysql = connectToMySQL('beltexam_db')
    query = "SELECT user_id FROM comments WHERE id = %(comment_id)s;"
    data = {'comment_id': comment_id}
    result = mysql.query_db(query, data)
    if result and session['user_id'] == result[0]['user_id']:
        new_comment = request.form['comment']

        query = "UPDATE comments SET comment = %(new_comment)s WHERE id = %(comment_id)s;"
        data = {
            'new_comment': new_comment,
            'comment_id': comment_id
        }
        mysql.query_db(query, data)

    return redirect(f'/shows/{show_id}')

@app.route('/shows/<int:show_id>/delete', methods=['POST'])
def delete_show(show_id):
    if 'user_id' not in session:
        return redirect('/')

    if is_show_creator(show_id):
        mysql = connectToMySQL('beltexam_db')
        query = "DELETE FROM shows WHERE id = %(show_id)s;"
        data = {'show_id': show_id}
        mysql.query_db(query, data)

    return redirect('/dashboard')

@app.route('/shows/<int:show_id>/edit', methods=['GET', 'POST'])
def edit_show(show_id):
    if 'user_id' not in session:
        return redirect('/')

    if is_show_creator(show_id):
        if request.method == 'POST':
            title = request.form['title']
            network = request.form['network']
            release_date = request.form['release_date']
            description = request.form['description']

            mysql = connectToMySQL('beltexam_db')
            query = "UPDATE shows SET title = %(title)s, network = %(network)s, release_date = %(release_date)s, description = %(description)s WHERE id = %(show_id)s;"
            data = {
                'title': title,
                'network': network,
                'release_date': release_date,
                'description': description,
                'show_id': show_id
            }
            mysql.query_db(query, data)

            return redirect('/dashboard')

        else:
            mysql = connectToMySQL('beltexam_db')
            query = "SELECT * FROM shows WHERE id = %(show_id)s;"
            data = {'show_id': show_id}
            show = mysql.query_db(query, data)

            if show:
                return render_template('edit_show.html', show=show[0])

    return redirect('/dashboard')
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)
