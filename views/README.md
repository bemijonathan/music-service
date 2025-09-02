# Views Folder Structure

This folder contains the frontend assets and templates for the Dhive AI Music Generator API.

## 📁 Folder Structure

```
views/
├── static/
│   ├── css/
│   │   └── style.css          # Main stylesheet for the documentation page
│   └── js/
│       └── app.js             # JavaScript functionality for interactive testing
└── templates/
    └── index.html             # Main HTML template for the API documentation
```

## 🎨 Files Description

### `static/css/style.css`
- Contains all the CSS styles for the documentation page
- Includes responsive design for mobile devices
- Professional gradient backgrounds and modern UI elements
- Color-coded status indicators and form styling

### `static/js/app.js`
- Handles all interactive functionality
- API testing functions with fetch requests
- Form validation and submission
- Real-time status checking with auto-refresh
- Tab switching and UI interactions

### `templates/index.html`
- Main HTML template using Jinja2 templating
- Three main sections: Overview, API Endpoints, Interactive Testing
- Forms for testing all API endpoints
- Responsive grid layout for different screen sizes

## 🚀 How It Works

1. **Flask Integration**: The `routes.py` file uses `render_template('index.html')` to serve the documentation page
2. **Static Files**: CSS and JS files are served via Flask's `url_for('static', filename='...')` function
3. **Interactive Testing**: Users can test all API endpoints directly from the browser
4. **Real-time Updates**: Status checking with automatic refresh functionality

## 🎯 Features

- **📖 Complete API Documentation** - All endpoints documented with examples
- **🧪 Interactive Testing** - Test forms for all API endpoints
- **📱 Responsive Design** - Works on desktop and mobile devices
- **🎨 Modern UI** - Professional design with gradients and animations
- **⚡ Real-time Status** - Auto-refresh for song generation status
- **🔄 Auto-population** - Task IDs automatically filled from responses

## 🛠️ Usage

1. Start your Flask application: `python main.py`
2. Visit `http://127.0.0.1:5000` in your browser
3. Navigate through the tabs to explore documentation and test endpoints
4. Use the interactive forms to test the API in real-time

## 📝 Customization

To modify the appearance or functionality:

1. **Styling**: Edit `static/css/style.css`
2. **JavaScript**: Edit `static/js/app.js`
3. **HTML Structure**: Edit `templates/index.html`
4. **Add New Endpoints**: Update the HTML template and JavaScript accordingly

## 🔧 Flask Configuration

Make sure your Flask app is configured to serve static files and templates:

```python
app = Flask(__name__,
    static_folder='views/static',
    template_folder='views/templates'
)
```

The current setup uses the default Flask static and template folder locations, so no additional configuration is needed.
