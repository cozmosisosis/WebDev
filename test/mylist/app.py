import os, logging, sqlite3
from datetime import datetime
from helpers import login_required, get_db, close_db
from flask import Flask, flash, render_template, redirect, session, request, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'





@app.route('/')
@login_required
def index():

    db = get_db()

    if 'user_id' in session:
        error = None
        user = db.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()

        if not user:
            error = "Failure retreving user account info please try logging on again"
            flash(error)
            close_db()
            return redirect(url_for('login'))

        db.execute('UPDATE users SET date_last_active = ? WHERE user_id = ?', (datetime.utcnow(), session['user_id']))
        db.commit()
        close_db()
        return render_template("index.html")

    error = 'login failure, user_id not found in session'
    flash(error)
    close_db()
    return redirect(url_for('login'))
    
        


@app.route('/login', methods=['GET', 'POST'])
def login():


    db = get_db()
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        error = None

        if username == "" or password == "":
            error = 'Username and or Password was left empty'

        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()


        if user is None or not check_password_hash(user['hashed_password'], password):
            error = 'Username and or Password is Incorrect'

        if error is None:

            session.clear()
            session['user_id'] = user['user_id']
            try:
                db.execute('UPDATE users SET date_last_active = ? WHERE user_id = ?', (datetime.utcnow(), user['user_id']))
                db.commit()
                close_db()
                return redirect(url_for('index'))
            except:
                error = 'Failed to update date last active in account info'

        flash(error)
        close_db()
        return redirect(url_for('login'))
    else:
        try:
            if session['user_id'] is not None:
                flash('Logged in!')
                db.execute('UPDATE users SET date_last_active = ? WHERE user_id = ?', (datetime.utcnow(), session['user_id']))
                db.commit()
                close_db()
                return redirect(url_for('index'))
        except:
            close_db()
            return render_template('login.html')

        
    
    


@app.route("/logout", methods=['POST', 'GET'])
def logout():
    session.clear()
    flash("Logged out")
    return redirect(url_for('login'))



@app.route("/register", methods=['POST', 'GET'])
def register():

    db = get_db()
    if request.method == 'GET':
        try:
            if session['user_id'] is not None:
                flash('Must not be logged in to register')
                close_db()
                return redirect(url_for('index'))
        except: pass
        close_db()
        return render_template('register.html')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_verification = request.form['password_verification']
        user_email = request.form['email']
        user_email_verification = request.form['email_verification']
        error = None

        if not username or not password or not password_verification:
            error = 'Please fill out all required fields'
        elif not password == password_verification:
            error = 'Passwords do not match'
        elif not user_email:
            flash('Email was not filled out. Please update your email for recovery purposes!')
            user_email = 'N/A'
        elif not user_email == user_email_verification:
            error = 'Email and email verification do not match!'


        if error is None: 
            try:
                db.execute(
                    'INSERT INTO users (username, hashed_password, user_email, date_created, date_last_active) VALUES (?, ?, ?, ?, ?)',
                    (username, generate_password_hash(password), user_email, datetime.utcnow(), datetime.utcnow())
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            
            else:
                flash('Account created, Please Login!')
                close_db()
                return redirect(url_for('login'))


        flash(error)

        close_db()
        return redirect(url_for('register'))



@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():

    db = get_db()
    if 'user_id' in session:
        error = None
        user = db.execute('SELECT user_id, username, user_email, date_created, date_last_active FROM users WHERE user_id = ?', (session['user_id'],))

        if user is None:
            error = "Failure retreving user account info please try logging on again"
            flash(error)
            close_db()
            return redirect(url_for('login'))

        db.execute('UPDATE users SET date_last_active = ? WHERE user_id = ?', (datetime.utcnow(), session['user_id']))
        db.commit()
        close_db()
        return render_template("account.html", user=user)

    

@app.route("/my_items", methods=['GET', 'POST'])
@login_required
def my_items():

    db = get_db()
    if request.method == 'GET':
        # render db info
        item = db.execute("SELECT * FROM item WHERE user_id = ?", (session['user_id'],))
        close_db()
        return render_template('my_items.html', item=item)
        
    if not request.form['item_name']:
        flash('Name must be filled out to submit')
        close_db()
        return redirect(url_for('my_items'))

    new_item_name = request.form['item_name']
    item_exists = db.execute("SELECT * FROM item WHERE item_name = ? AND user_id = ?", (new_item_name, session['user_id'],)).fetchone()
    if item_exists:
        flash('Item already exists')
        close_db()
        return redirect(url_for('my_items'))
    db.execute("INSERT INTO item (user_id, item_name) VALUES (?, ?)", (session['user_id'], new_item_name, ))
    db.commit()
    close_db()
    return redirect(url_for('my_items'))
    
    

@app.route("/remove_item", methods=['GET', 'POST'])
@login_required
def remove_item():

    db = get_db()
    if request.method == 'GET':
        close_db()
        return redirect(url_for('my_items'))
    
    item_deleting = request.form['item_id']

    valid_item = db.execute("SELECT * FROM item WHERE item_id = ? AND user_id = ?", (item_deleting, session['user_id'],)).fetchone()
    if not valid_item:
        flash('not valid item')
        close_db()
        return redirect(url_for('my_items'))

    db.execute("DELETE FROM item WHERE item_id = ? AND user_id = ?", (item_deleting, session['user_id']))
    db.execute("DELETE FROM groups_items WHERE item_id = ?", (item_deleting,))
    db.commit()

    close_db()
    return redirect(url_for('my_items'))



@app.route("/my_groups", methods=['GET', 'POST'])
@login_required
def my_groups():

    db = get_db()
    if request.method == 'GET':
        groups = db.execute("SELECT * FROM groups WHERE user_id = ?", (session['user_id'],))
        close_db()
        return render_template('my_groups.html', groups=groups)
    new_group = request.form['group_name']
    
    if not new_group:
        flash('Group Name Not Filled out!')
        close_db()
        return redirect(url_for('my_groups'))
    
    group = db.execute("SELECT * FROM groups WHERE groups_name = ? AND user_id = ?", (new_group, session['user_id'],)).fetchone()

    if group is not None:
        flash('Group already exists')
        close_db()
        return redirect(url_for('my_groups'))

    db.execute("INSERT INTO groups (user_id, groups_name) VALUES (?,?)", (session['user_id'], new_group))  
    db.commit()

    flash('Group Added')
    close_db()
    return redirect(url_for('my_groups'))



@app.route("/remove_group", methods=['GET', 'POST'])
@login_required
def remove_group():

    db = get_db()
    if request.method == 'GET':
        close_db()
        return redirect(url_for('my_groups'))
    group_deleting = request.form['groups_id']
    valid_group = db.execute("SELECT * FROM groups WHERE groups_id = ? AND user_id = ?", (group_deleting, session['user_id'],)).fetchone()
    if not valid_group:
        flash('Error with trying to delete group')
        close_db()
        return redirect(url_for('my_groups'))
    
    db.execute("DELETE FROM groups_items WHERE groups_id = ?", (group_deleting,))
    db.execute("DELETE FROM groups WHERE groups_id = ? AND user_id = ?", (group_deleting, session['user_id']))
    db.commit()
    close_db()
    return redirect(url_for('my_groups'))



@app.route("/edit_groups", methods=['GET', 'POST'])
@login_required
def edit_groups():

    db = get_db()
    if request.method == 'GET':

        groups = db.execute("SELECT * FROM groups WHERE user_id = ?", (session['user_id'],))
        groups = list(groups)
        group_items = db.execute("SELECT groups_items.groups_id, item.item_id, item.item_name, groups_items.quantity, item.user_id FROM item JOIN groups_items ON groups_items.item_id = item.item_id WHERE item.user_id = ?", (session['user_id'],))
        group_items = list(group_items)
        users_items = db.execute("SELECT * FROM item WHERE user_id = ?", (session['user_id'],))
        users_items = list(users_items)

        close_db()
        return render_template('edit_groups.html', groups=groups, group_items=group_items, users_items=users_items)
    close_db()
    return redirect(url_for('edit_groups'))



@app.route("/add_to_group", methods=['POST', 'GET'])
@login_required
def add_to_group():

    db = get_db()
    if request.method == 'GET':
        close_db()
        return redirect(url_for('edit_groups'))
    
    selected_group = request.form.get('groups')
    selected_item = request.form.get('items')
    inputed_quantity = request.form.get('quantity')


    if not selected_group or not selected_item or not inputed_quantity:
        flash('Must select group, item to add and a valid quantity (greater than 0)')
        close_db()
        return redirect(url_for('edit_groups'))
    
    inputed_quantity = int(inputed_quantity)
    if inputed_quantity <= 0:
        flash('Must input a valid quantity (greater than 0)')
        close_db()
        return redirect(url_for('edit_groups'))


    users_item = db.execute("SELECT * FROM item WHERE item_id = ? and user_id = ?", (selected_item, session['user_id'],)).fetchone()
    users_group = db.execute("SELECT * FROM groups WHERE groups_id = ? and user_id = ?", (selected_group, session['user_id'],)).fetchone()
    
    if users_item is None or users_group is None:
        flash('Error occured with either item submitted or group submitted to. No link to user')
        close_db()
        return redirect(url_for('edit_groups'))
    
    ingredient_is_in_groups_items = db.execute("SELECT * FROM groups_items WHERE groups_id = ? AND item_id = ?", (selected_group, selected_item,)).fetchone()

    if not ingredient_is_in_groups_items:
        db.execute("INSERT INTO groups_items (groups_id, item_id, quantity) VALUES (?, ?, ?)", (selected_group, selected_item, inputed_quantity))
        db.commit()
        close_db()
        return redirect(url_for('edit_groups'))

    old_quantity = ingredient_is_in_groups_items['quantity']
    new_quantity = inputed_quantity + old_quantity
    db.execute("UPDATE groups_items SET quantity = ? WHERE groups_id = ? AND item_id = ?", (new_quantity, selected_group, selected_item,))
    db.commit()
    close_db()
    return redirect(url_for('edit_groups'))



@app.route("/delete_account", methods=['GET', 'POST'])
@login_required
def delete_account():

    db = get_db()
    if request.method == 'GET':
        close_db()
        return render_template('delete_account.html')
    
    username = request.form['username']
    password = request.form['password']

    if not username or not password:
        flash('Must fill out both username and password to DELETE account')
        close_db()
        return redirect(url_for('delete_account'))
    
    user = db.execute('SELECT * FROM users WHERE user_id = ?', (session['user_id'],)).fetchone()


    if user is None or username != user['username'] or not check_password_hash(user['hashed_password'], password):
        flash('Error with submitted User Info for deletion. Please log out, log back in, and then try deleting account again.')
        close_db()
        return redirect(url_for('delete_account'))


    # NEED TO DELETE ALL USER DATA BEFORE USER ACCOUNT

    db.execute("DELETE FROM groups_items WHERE item_id IN (SELECT item_id FROM item WHERE user_id = ?)", (session['user_id'],))
    db.execute("DELETE FROM item WHERE user_id = ?", (session['user_id'],))

    db.execute("DELETE FROM groups_items WHERE groups_id IN (SELECT groups_id FROM groups WHERE user_id = ?)", (session['user_id'],))
    db.execute("DELETE FROM groups WHERE user_id = ?", (session['user_id'],))

    db.execute("DELETE FROM users WHERE user_id = ?", (session['user_id'],))

    db.commit()
    close_db()

    session.clear()
    flash("Account Deleted")
    return redirect(url_for('login'))




@app.errorhandler(404)
def page_not_found(error):
    flash('Invalid route')
    return redirect(url_for('index'))