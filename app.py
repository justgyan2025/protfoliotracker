from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from dotenv import load_dotenv
import os
import pyrebase
import json
import yfinance as yf
import requests
from datetime import datetime
import traceback

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')
app.secret_key = os.urandom(24)

# Firebase configuration
firebase_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL")
}

# Initialize Firebase
firebase = pyrebase.initialize_app(firebase_config)
auth_firebase = firebase.auth()
db = firebase.database()

# Function to get stock data
def get_stock_data(ticker):
    # Clean the ticker input
    ticker = ticker.strip().upper()
    
    # Remove any existing suffixes
    if ticker.endswith('.NS') or ticker.endswith('.BO'):
        base_ticker = ticker[:-3]
    else:
        base_ticker = ticker
    
    # Try NSE first
    nse_ticker = f"{base_ticker}.NS"
    try:
        # Use a more reliable method to get current price
        stock = yf.Ticker(nse_ticker)
        
        # Try multiple methods to get the price
        price = None
        name = None
        
        # Method 1: Try getting from recent history
        try:
            hist = stock.history(period="1d")
            if not hist.empty and 'Close' in hist.columns:
                price = float(hist['Close'].iloc[-1])
        except Exception as e:
            print(f"NSE history error: {str(e)}")
        
        # Method 2: Try getting from quote
        if price is None:
            try:
                todays_data = stock.info
                price = float(todays_data.get('regularMarketPrice', 0))
                if price == 0:
                    price = float(todays_data.get('previousClose', 0))
            except Exception as e:
                print(f"NSE quote error: {str(e)}")
        
        # Get company name
        try:
            info = stock.info
            name = info.get('shortName', info.get('longName', nse_ticker))
        except Exception as e:
            print(f"NSE name error: {str(e)}")
            name = nse_ticker
        
        # If we found a valid price, return the data
        if price and price > 0:
            return {
                'name': name,
                'current_price': price,
                'exchange': 'NSE',
                'symbol': nse_ticker
            }
    except Exception as e:
        print(f"NSE overall error: {str(e)}")
        traceback.print_exc()
    
    # If NSE fails, try BSE
    bse_ticker = f"{base_ticker}.BO"
    try:
        stock = yf.Ticker(bse_ticker)
        
        # Try multiple methods to get the price
        price = None
        name = None
        
        # Method 1: Try getting from recent history
        try:
            hist = stock.history(period="1d")
            if not hist.empty and 'Close' in hist.columns:
                price = float(hist['Close'].iloc[-1])
        except Exception as e:
            print(f"BSE history error: {str(e)}")
        
        # Method 2: Try getting from quote
        if price is None:
            try:
                todays_data = stock.info
                price = float(todays_data.get('regularMarketPrice', 0))
                if price == 0:
                    price = float(todays_data.get('previousClose', 0))
            except Exception as e:
                print(f"BSE quote error: {str(e)}")
        
        # Get company name
        try:
            info = stock.info
            name = info.get('shortName', info.get('longName', bse_ticker))
        except Exception as e:
            print(f"BSE name error: {str(e)}")
            name = bse_ticker
        
        # If we found a valid price, return the data
        if price and price > 0:
            return {
                'name': name,
                'current_price': price,
                'exchange': 'BSE',
                'symbol': bse_ticker
            }
    except Exception as e:
        print(f"BSE overall error: {str(e)}")
        traceback.print_exc()
    
    # If both fail, try a direct approach for well-known Indian stocks
    try:
        # Try to get data from an alternative source - Yahoo Finance direct API
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{base_ticker}.NS?interval=1d"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                result = data['chart']['result'][0]
                if 'meta' in result and 'regularMarketPrice' in result['meta']:
                    price = float(result['meta']['regularMarketPrice'])
                    name = base_ticker
                    if 'shortName' in result['meta']:
                        name = result['meta']['shortName']
                    
                    return {
                        'name': name,
                        'current_price': price,
                        'exchange': 'NSE',
                        'symbol': f"{base_ticker}.NS"
                    }
    except Exception as e:
        print(f"Direct Yahoo API error: {str(e)}")
    
    # If everything fails, return default values
    return {
        'name': base_ticker,
        'current_price': 0,
        'exchange': 'Unknown',
        'symbol': base_ticker
    }

# Routes
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    try:
        user = auth_firebase.sign_in_with_email_and_password(email, password)
        user_id = user['localId']
        id_token = user['idToken']
        # Return token to client for future requests
        return redirect(url_for('dashboard', token=id_token))
    except Exception as e:
        error_message = json.loads(e.args[1])['error']['message']
        flash(f"Login failed: {error_message}")
        return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    token = request.args.get('token')
    if not token:
        return redirect(url_for('index'))
    
    try:
        # Verify the token
        user = auth_firebase.get_account_info(token)
        user_id = user['users'][0]['localId']
        
        # Get user's stocks from Firebase
        user_stocks = db.child("users").child(user_id).child("stocks").get(token=token).val() or {}
        
        # Get updated stock information
        stock_data = {}
        for ticker, details in user_stocks.items():
            try:
                # Use the stored symbol if available
                symbol_to_use = details.get('symbol', ticker)
                
                # Get current stock data
                stock_info = get_stock_data(symbol_to_use)
                
                stock_data[ticker] = {
                    'name': details.get('name', stock_info['name']),
                    'current_price': stock_info['current_price'],
                    'quantity': details.get('quantity', 0),
                    'purchase_price': details.get('purchase_price', 0),
                    'exchange': details.get('exchange', stock_info['exchange']),
                    'symbol': details.get('symbol', symbol_to_use)
                }
            except Exception as e:
                # Use existing data if fetch fails
                stock_data[ticker] = {
                    'name': details.get('name', ticker),
                    'current_price': 0,
                    'quantity': details.get('quantity', 0),
                    'purchase_price': details.get('purchase_price', 0),
                    'exchange': details.get('exchange', 'Unknown'),
                    'symbol': details.get('symbol', ticker)
                }
        
        # Get user's mutual funds from Firebase
        mutual_funds = db.child("users").child(user_id).child("mutual_funds").get(token=token).val() or {}
        
        return render_template('dashboard.html', 
                              stocks=stock_data, 
                              mutual_funds=mutual_funds,
                              token=token)
    except Exception as e:
        return redirect(url_for('index'))

@app.route('/stocks')
def stocks():
    token = request.args.get('token')
    if not token:
        return redirect(url_for('index'))
    
    try:
        # Verify the token
        user = auth_firebase.get_account_info(token)
        user_id = user['users'][0]['localId']
        
        # Get user's stocks from Firebase
        user_stocks = db.child("users").child(user_id).child("stocks").get(token=token).val() or {}
        
        # Get updated stock information
        stock_data = {}
        for ticker, details in user_stocks.items():
            try:
                # Use the stored symbol if available
                symbol_to_use = details.get('symbol', ticker)
                
                # Get current stock data
                stock_info = get_stock_data(symbol_to_use)
                
                stock_data[ticker] = {
                    'name': details.get('name', stock_info['name']),
                    'current_price': stock_info['current_price'],
                    'quantity': details.get('quantity', 0),
                    'purchase_price': details.get('purchase_price', 0),
                    'exchange': details.get('exchange', stock_info['exchange']),
                    'symbol': details.get('symbol', symbol_to_use)
                }
            except Exception as e:
                print(f"Error updating stock {ticker}: {str(e)}")
                # Use existing data if fetch fails
                stock_data[ticker] = {
                    'name': details.get('name', ticker),
                    'current_price': 0,
                    'quantity': details.get('quantity', 0),
                    'purchase_price': details.get('purchase_price', 0),
                    'exchange': details.get('exchange', 'Unknown'),
                    'symbol': details.get('symbol', ticker),
                    'error': str(e)
                }
        
        return render_template('stocks.html', stocks=stock_data, token=token)
    except Exception as e:
        flash(f"Error: {str(e)}")
        return redirect(url_for('index'))

@app.route('/get_stock_info', methods=['POST'])
def get_stock_info():
    ticker = request.form.get('ticker')
    if not ticker:
        return jsonify({'error': 'No ticker provided'})
    
    try:
        print(f"Fetching stock info for: {ticker}")
        stock_info = get_stock_data(ticker)
        print(f"Stock info result: {stock_info}")
        return jsonify(stock_info)
    except Exception as e:
        print(f"Error in get_stock_info route: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f"Failed to fetch stock information: {str(e)}"})

@app.route('/add_stock', methods=['POST'])
def add_stock():
    token = request.form.get('token')
    if not token:
        return redirect(url_for('index'))
    
    try:
        # Verify the token
        user = auth_firebase.get_account_info(token)
        user_id = user['users'][0]['localId']
        
        ticker = request.form.get('ticker')
        symbol = request.form.get('symbol')  # Get the full symbol including exchange suffix
        quantity = float(request.form.get('quantity'))
        purchase_price = float(request.form.get('purchase_price'))
        
        # Use the symbol if provided, otherwise use ticker
        stock_ticker = symbol if symbol else ticker
        
        # Get stock info using the helper function
        stock_info = get_stock_data(stock_ticker)
        
        if stock_info['current_price'] == 0:
            flash(f"Error: Could not find stock information for {ticker}")
            return redirect(url_for('stocks', token=token))
            
        # Save to Firebase
        stock_data = {
            'name': stock_info['name'],
            'quantity': quantity,
            'purchase_price': purchase_price,
            'exchange': stock_info['exchange'],
            'symbol': stock_info['symbol']
        }
        
        # Use the base ticker (without .NS or .BO) as the key
        base_ticker = ticker.strip().upper()
        if base_ticker.endswith('.NS') or base_ticker.endswith('.BO'):
            base_ticker = base_ticker[:-3]
            
        db.child("users").child(user_id).child("stocks").child(base_ticker).set(stock_data, token=token)
        
        flash(f"Stock {stock_info['name']} added successfully!")
        return redirect(url_for('stocks', token=token))
    except Exception as e:
        flash(f"Error adding stock: {str(e)}")
        return redirect(url_for('stocks', token=token))

@app.route('/mutual_funds')
def mutual_funds():
    token = request.args.get('token')
    if not token:
        return redirect(url_for('index'))
    
    try:
        # Verify the token
        user = auth_firebase.get_account_info(token)
        user_id = user['users'][0]['localId']
        
        # Get user's mutual funds from Firebase
        user_funds = db.child("users").child(user_id).child("mutual_funds").get(token=token).val() or {}
        
        # Get updated mutual fund information
        fund_data = {}
        for scheme_code, details in user_funds.items():
            try:
                response = requests.get(f"https://api.mfapi.in/mf/{scheme_code}")
                if response.status_code == 200:
                    fund_info = response.json()
                    scheme_name = fund_info.get('meta', {}).get('scheme_name', f"Fund {scheme_code}")
                    current_nav = float(fund_info.get('data', [{}])[0].get('nav', 0))
                    
                    fund_data[scheme_code] = {
                        'name': scheme_name,
                        'current_nav': current_nav,
                        'units': details.get('units', 0),
                        'purchase_nav': details.get('purchase_nav', 0)
                    }
                else:
                    fund_data[scheme_code] = details
            except Exception as e:
                fund_data[scheme_code] = {
                    'name': f"Fund {scheme_code}",
                    'current_nav': 0,
                    'units': details.get('units', 0),
                    'purchase_nav': details.get('purchase_nav', 0),
                    'error': str(e)
                }
        
        return render_template('mutual_funds.html', funds=fund_data, token=token)
    except Exception as e:
        return redirect(url_for('index'))

@app.route('/add_mutual_fund', methods=['POST'])
def add_mutual_fund():
    token = request.form.get('token')
    if not token:
        return redirect(url_for('index'))
    
    try:
        # Verify the token
        user = auth_firebase.get_account_info(token)
        user_id = user['users'][0]['localId']
        
        scheme_code = request.form.get('scheme_code')
        units = float(request.form.get('units'))
        purchase_nav = float(request.form.get('purchase_nav'))
        
        # Verify mutual fund exists
        response = requests.get(f"https://api.mfapi.in/mf/{scheme_code}")
        if response.status_code == 200:
            fund_info = response.json()
            scheme_name = fund_info.get('meta', {}).get('scheme_name', f"Fund {scheme_code}")
            
            # Save to Firebase
            fund_data = {
                'name': scheme_name,
                'units': units,
                'purchase_nav': purchase_nav
            }
            
            db.child("users").child(user_id).child("mutual_funds").child(scheme_code).set(fund_data, token=token)
            
            return redirect(url_for('mutual_funds', token=token))
        else:
            flash(f"Error: Mutual fund scheme code {scheme_code} not found")
            return redirect(url_for('mutual_funds', token=token))
    except Exception as e:
        flash(f"Error adding mutual fund: {str(e)}")
        return redirect(url_for('mutual_funds', token=token))

@app.route('/logout')
def logout():
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True) 