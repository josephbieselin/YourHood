from flask import Flask, render_template, json, request, redirect, session
from flaskext.mysql import MySQL

app = Flask(__name__)
app.secret_key = 'this is my secret key'

mysql = MySQL()

db_pw = ""
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = db_pw
app.config['MYSQL_DATABASE_DB'] = 'db_project'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

mysql.init_app(app)

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/showSignup')
def signup():
	'''Show the page to sign up'''
	return render_template('signup.html')

@app.route('/showSignin')
def signin():
	'''Show the sign in page if the user is not already signed in via a session'''
	if session.get('user'):
		return render_template('userHome.html', username = session.get('user'))
	else:
		return render_template('signin.html')

@app.route('/userHome')
def home():
	'''Show the user's home page if they are signed in via a session; else return the error page'''
	if session.get('user'):
		return render_template('userHome.html', username = session.get('user'))
	else:
		return render_template('error.html', error = 'Unauthorized Access: please sign in or sign up first.')



'''
<label for="search_type" class="sr-only">Search Type</label>
<select name="search_type" id="search_type">
  <option value="users">Users</option>
  <option value="hood_messages">Users</option>
  <option value="friend_messages">Users</option>
</select>
'''

@app.route('/search', methods=['POST'])
def search():
	_type = request.form['search_type']
	_value = request.form['search_value']
	# url = url_for("search_" + _type, value=_value)
	url = "/search_" + _type + "/" + _value
	return redirect(url)

@app.route('/search_users/<string:value>')
def searchUsers(value):
	'''Show the users that have 'value' in their username'''
	try:
		conn = mysql.connect()
		cursor = conn.cursor()

		# SQL LIKE filters with %filter_str%
		value = '%' + value + '%'

		# get the profile of the current session's user
		cursor.callproc('showUsers', (value, session.get('user')))

		data = cursor.fetchall()
		# data = [[username], [username], ...]

		return render_template('users.html', users = data)
	
	except Exception as e:
		return render_template('error.html', error = str(e))

	finally:
		cursor.close()
		conn.close()

@app.route('/users/<string:username>')
def userPage(username):
	'''Shows the page of the user with username'''
	try:
		conn = mysql.connect()
		cursor = conn.cursor()

		# get the profile of the current session's user
		cursor.callproc('areFriends', (session.get('user'), username))

		data = cursor.fetchall()
		# data = [[username, friend]]

		# 0 = Nothing, 1 = Friends, 2 = Logged In User has Friend request from searched user, 3 = Logged In User has requested to be Friends with the searched user
		friendStatus = 0

		# 0 = Already Friends or  Not FOF, 1 = Friends of Friends
		fofStatus = 0

		# users are not friends
		if len(data) is 0:
			cursor.callproc('friendRequested', (session.get('user'), username))

			data = cursor.fetchall()
			# data = [[requester, requestee]]

			# there is some kind of request
			if len(data) > 0:
				requester = data[0][0]
				requestee = data[0][1]
				if requester == username:
					friendStatus = 2
				else:
					friendStatus = 3

			cursor.callproc('areFOFs', (username, session.get('user')))

			data = cursor.fetchall()
			# data = [[fof]]

			if len(data) > 0:
				fofStatus = 1

		# users are friends
		else:
			friendStatus = 1

		cursor.callproc('showUserMessages', [username, ])

		data = cursor.fetchall()
		# data = [[poster, title, body, msgloc, multimedia, msgtime, visibility, reply], ....]

		return render_template('userPage.html', user = session.get('user'), otherUser = username, friendStatus = friendStatus, fofStatus = fofStatus, messages = data)
	
	except Exception as e:
		return render_template('error.html', error = str(e))

	finally:
		cursor.close()
		conn.close()

@app.route('/postMessageOnUserPage', methods=['POST'])
def postMessageOnUserPage():
	'''Posts a message onto the user's page'''
	#title, body, visibility, otherUser
	_user = request.form['user']
	_title = request.form['title']
	_body = request.form['body']
	_visibility = request.form['visibility']

	try:
		conn = mysql.connect()
		cursor = conn.cursor()

		cursor.callproc('postMessage', (session.get('user'), _user, None, None, _title, _body, None, _visibility))

		data = cursor.fetchall()
		# data = [[username, friend]]

		if session.get('user') == _user:
			url = "/users/" + _user
		else:
			url = "/userHome"
			
		return redirect(url)

	except Exception as e:
		return render_template('error.html', error = str(e))

	finally:
		cursor.close()
		conn.close()

def getProfileData(data, index):
	'''Returns the value from the current user's profile'''
	# SQL NULL values are represented as None in Python
	if (data[0][index]) is None:
		return ''
	else:
		return data[0][index]

@app.route('/editProfile')
def editProfile():
	'''Allow the user to edit their profile'''
	try:
		conn = mysql.connect()
		cursor = conn.cursor()

		# get the profile of the current session's user
		_user = session.get('user')
		cursor.callproc('getProfile', [_user,])

		data = cursor.fetchall()
		# data = [[username, address, city, state, fname, lname, age, bio, photo, visibility], ...]

		address = getProfileData(data, 1)
		city = getProfileData(data, 2)
		state = getProfileData(data, 3)
		fname = getProfileData(data, 4)
		lname = getProfileData(data, 5)
		age = getProfileData(data, 6)
		bio = getProfileData(data, 7)
		# TODO: implement sending of photo data
		# photo = getProfileData(data, 8)
		visibility = getProfileData(data, 9)

		return render_template('editProfile.html', curr_address = address, curr_city = city, curr_state = state, curr_fname = fname, curr_lname = lname, curr_age = age, curr_bio = bio, curr_visibility = visibility)
	
	except Exception as e:
		return render_template('error.html', error = str(e))

	finally:
		cursor.close()
		conn.close()

@app.route('/updateProfile', methods=['POST'])
def updateProfile():
	'''Update the user's profile'''
	_un = session.get('user')
	_address = request.form['address']
	_city = request.form['city']
	_state = request.form['state']
	_fname = request.form['fname']
	_lname = request.form['lname']
	_age = request.form['age']
	_bio = request.form['bio']
	# TODO: implement sending of photo data
	# _photo = request.form['username']
	_visibility = request.form['visibility']

	# set _age to -1 if user left it blank (Procedure will check for -1 and set it to NULL)
	if _age == '':
		_age = -1
	else:
		_age = int(_age)

	try:
		conn = mysql.connect()
		cursor = conn.cursor()

		cursor.callproc('editProfile', (_un, _address, _city, _state, _fname, _lname, _age, _bio, None, _visibility))

		data = cursor.fetchall()

		if len(data) is 0:
			# commit the new user to the database
			conn.commit()
			return redirect('/editProfile')
		else:
			# don't commit any changes to the database
			conn.rollback()
			return render_template('error.html', error = "Invalid update: no changes made to your profile.")
			## line below returns error description from MySQL
			# return json.dumps({'error': str(data[0])})

	except Exception as e:
		return render_template('error.html', error = str(e))

	finally:
		cursor.close()
		conn.close()

@app.route('/showFriendRequests')
def friendRequests():
	try:
		conn = mysql.connect()
		cursor = conn.cursor()

		cursor.callproc('getFriendRequests', [session.get('user'), ])

		data = cursor.fetchall()
		# data = [[requester], [requester], ...]

		return render_template("friendRequests.html", requests = data)

	except Exception as e:
		return render_template('error.html', error = str(e))

	finally:
		cursor.close()
		conn.close()

@app.route('/requestFriend', methods=['POST'])
def requestFriend():
	_requestee = request.form['requestFriend']

	try:
		conn = mysql.connect()
		cursor = conn.cursor()

		cursor.callproc('requestFriend', (session.get('user'), _requestee))

		data = cursor.fetchall()
		# data = [[requester], [requester], ...]

		if len(data) is 0:
			# commit the new user to the database
			conn.commit()
			return redirect('/users/' + _requestee)
		else:
			# don't commit any changes to the database
			conn.rollback()
			return render_template('error.html', error = "Invalid update: no changes made to your friend requests.")
			## line below returns error description from MySQL
			# return json.dumps({'error': str(data[0])})

	except Exception as e:
		return render_template('error.html', error = str(e))

	finally:
		cursor.close()
		conn.close()

@app.route('/acceptFriend', methods=['POST'])
def acceptFriend():
	_requester = request.form['requester']

	try:
		conn = mysql.connect()
		cursor = conn.cursor()

		cursor.callproc('acceptFriend', (session.get('user'), _requester))

		data = cursor.fetchall()
		# data = [[requester], [requester], ...]

		if len(data) is 0:
			# commit the new user to the database
			conn.commit()
			return redirect('/showFriendRequests')
		else:
			# don't commit any changes to the database
			conn.rollback()
			return render_template('error.html', error = "Invalid update: no changes made to your friend requests.")
			## line below returns error description from MySQL
			# return json.dumps({'error': str(data[0])})

	except Exception as e:
		return render_template('error.html', error = str(e))

	finally:
		cursor.close()
		conn.close()

@app.route('/rejectFriend', methods=['POST'])
def rejectFriend():
	_requester = request.form['requester']

	try:
		conn = mysql.connect()
		cursor = conn.cursor()

		cursor.callproc('rejectFriend', (session.get('user'), _requester))

		data = cursor.fetchall()
		# data = [[requester], [requester], ...]

		if len(data) is 0:
			# commit the new user to the database
			conn.commit()
			return redirect('/showFriendRequests')
		else:
			# don't commit any changes to the database
			conn.rollback()
			return render_template('error.html', error = "Invalid update: no changes made to your friend requests.")
			## line below returns error description from MySQL
			# return json.dumps({'error': str(data[0])})

	except Exception as e:
		return render_template('error.html', error = str(e))

	finally:
		cursor.close()
		conn.close()

@app.route('/logout')
def logout():
	'''Remove this user from the session and take them back to the index page'''
	session.pop('user', None)
	return redirect('/')

@app.route('/validateLogin', methods=['POST'])
def validateLogin():
	'''Check the user's sign in credentials'''
	try:
		_un = request.form['username']
		_pw = request.form['password']

		conn = mysql.connect()
		cursor = conn.cursor()

		cursor.callproc('validateLogin', (_un, _pw))

		data = cursor.fetchall()

		if len(data) > 0:
			# data returned from MySQL Procedure places username as first index
			session['user'] = data[0][0]
			return redirect('/userHome')
		else:
			return render_template('error.html', error = 'Wrong username or password.')

	except Exception as e:
		return render_template('error.html', error = str(e))

	finally:
		cursor.close()
		conn.close()

@app.route('/signUp', methods=['POST'])
def signUp():
	try:
		_un = request.form['username']
		_email = request.form['email']
		_pw = request.form['password']
		_zipcode = request.form['zipcode']

		conn = mysql.connect()
		cursor = conn.cursor()
		
		if _un and _email and _pw and _zipcode:

			cursor.callproc('signupUser', (_un, _email, _pw, _zipcode))
			
			data = cursor.fetchall()

			if len(data) is 0:
				# commit the new user to the database
				conn.commit()
				# TODO: Return a template with the home page link or user to their home page
				session['user'] = _un
				return redirect('/userHome')
			else:
				# don't commit any changes to the database
				conn.rollback()
				return render_template('error.html', error = "Error: Username or Email already exists.")
				## line below returns error description from MySQL
				# return json.dumps({'error': str(data[0])})
		
		else:
			return json.dumps({'html':'All fields required'})

	except Exception as e:
		return render_template('error.html', error="Error: Username or Email already exists.")
		# return json.dumps({'error': str(e)})
	
	finally:
		cursor.close()
		conn.close()
	
if __name__ == '__main__':
    app.run()
