from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///p2p_lending.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    balance = db.Column(db.Float, default=10000)
    loans = db.relationship('Loan', backref='borrower', lazy=True)
    investments = db.relationship('Investment', backref='investor', lazy=True)

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    term = db.Column(db.Integer, nullable=False)  # in months
    status = db.Column(db.String(20), default='open')
    funded_amount = db.Column(db.Float, default=0)
    borrower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    investments = db.relationship('Investment', backref='loan', lazy=True)

class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    investor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    loan_id = db.Column(db.Integer, db.ForeignKey('loan.id'), nullable=False)

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and (user.password == request.form['password']):
            session['user_id'] = user.id
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/create_loan', methods=['GET', 'POST'])
def create_loan():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_loan = Loan(
            amount=float(request.form['amount']),
            interest_rate=float(request.form['interest_rate']),
            term=int(request.form['term']),
            borrower_id=session['user_id']
        )
        db.session.add(new_loan)
        db.session.commit()
        flash('Loan created successfully.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('create_loan.html')

@app.route('/loans')
def loans():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    open_loans = Loan.query.filter_by(status='open').all()
    return render_template('loans.html', loans=open_loans)

@app.route('/invest/<int:loan_id>', methods=['GET', 'POST'])
def invest(loan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    loan = Loan.query.get_or_404(loan_id)
    if request.method == 'POST':
        amount = float(request.form['amount'])
        user = User.query.get(session['user_id'])
        if user.balance < amount:
            flash('Insufficient balance.', 'error')
        elif loan.status != 'open':
            flash('This loan is not open for investment.', 'error')
        else:
            new_investment = Investment(amount=amount, investor_id=user.id, loan_id=loan.id)
            user.balance -= amount
            loan.funded_amount += amount
            if loan.funded_amount >= loan.amount:
                loan.status = 'funded'
            db.session.add(new_investment)
            db.session.commit()
            flash('Investment successful.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('invest.html', loan=loan)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)