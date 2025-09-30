# Event Queue Application

This web application allows attendees to scan a QR code to enter their group size, informs them of their turn, and provides an admin interface to manage entry and track the number of attendees at an event.

## Features

- Attendees can enter their group size via a web form after scanning a QR code.
- Real-time updates on the status of the queue for attendees.
- Admin interface to manage the queue and track the number of attendees.
- Database integration to store queue information.

## Project Structure

```
event-queue-app
├── app.py                # Main application file with Flask routes and logic
├── config.py             # Configuration settings for the Flask application
├── requirements.txt      # List of dependencies required for the project
├── README.md             # Documentation for the project
├── db
│   └── schema.sql       # SQL schema for the database
├── scripts
│   └── generate_qr.py   # Script to generate QR codes for attendees
├── templates
│   ├── base.html        # Base HTML template for the application
│   ├── join.html        # Template for attendees to enter group size
│   ├── status.html      # Template to display queue status to attendees
│   └── admin.html       # Template for the admin interface
├── static
│   ├── css
│   │   └── styles.css    # CSS styles for the application
│   └── js
│       └── main.js       # JavaScript for client-side functionality
└── tests
    └── test_app.py       # Unit tests for the application
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd event-queue-app
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up the database:
   - Run the SQL schema to create the necessary tables:
     ```
     sqlite3 db/queue.db < db/schema.sql
     ```

4. Run the application:
   ```
   python app.py
   ```

5. Access the application in your web browser at `http://127.0.0.1:5000`.

## Usage

- Attendees can scan the QR code to access the join page and enter their group size.
- Admins can access the admin interface to manage the queue and track attendees.

## License

This project is licensed under the MIT License.