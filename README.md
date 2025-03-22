# Investment Tracker

A Flask web application for tracking your investments, including stocks and mutual funds.

## Features

- Firebase Authentication (login only)
- Dashboard showing investment summary
- Stock tracking with real-time data using yfinance
- Mutual Fund tracking with real-time NAV data using MFAPI
- Firebase Database integration for data storage

## Prerequisites

- Python 3.8+
- Firebase account with Authentication and Realtime Database enabled

## Setup

1. Clone the repository:
```
git clone <repository-url>
cd investment-tracker
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Create a Firebase project:
   - Go to the [Firebase Console](https://console.firebase.google.com/)
   - Create a new project or use an existing one
   - Enable Email/Password Authentication
   - Create a Realtime Database

4. Set up environment variables:
   - The .env file is already set up in the root directory with the following variables:
   ```
   FIREBASE_API_KEY=AIzaSyBmsWUtBO6eEcmSWlWB9vSYYmUXkCUpF1k
   FIREBASE_AUTH_DOMAIN=firstapp-a538a.firebaseapp.com
   FIREBASE_PROJECT_ID=firstapp-a538a
   FIREBASE_STORAGE_BUCKET=firstapp-a538a.appspot.com
   FIREBASE_MESSAGING_SENDER_ID=914063013857
   FIREBASE_APP_ID=1:914063013857:web:e2ac502710efe0bf4884a0
   FIREBASE_DATABASE_URL=https://firstapp-a538a-default-rtdb.firebaseio.com
   ```
   - You can keep these values or update them with your own Firebase project credentials

5. Run the application:
```
python app.py
```

The application will be available at `http://localhost:5000`.

## Usage

1. Login using an email and password that is registered in your Firebase Authentication.
2. Add stocks by providing ticker symbols, quantity, and purchase price.
3. Add mutual funds by providing scheme codes, units, and purchase NAV.
4. View your investment portfolio on the dashboard.

## API Information

- Stock data is fetched using yfinance library
- Mutual fund data is fetched from https://api.mfapi.in/mf/{scheme_code}

## Notes for Firebase Setup

1. Make sure to create at least one user in Firebase Authentication before using the app
2. The app does not include a registration feature, so users must be pre-registered in Firebase 