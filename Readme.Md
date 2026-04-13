# 🚀 AI Web Scraper + Intelligence Engine

An advanced web scraping tool powered by AI that not only extracts links but also analyzes and generates insights from web content.

---

## 🌟 Features

### 🔗 Smart Link Extraction

* Extracts all links from any given URL
* Handles structured and unstructured HTML
* Fast and efficient scraping

### 🧠 AI-Powered Analysis

* Generates intelligent summaries
* Identifies key patterns and insights
* Converts raw data into meaningful information

### 📊 Interactive Dashboard

* Clean and modern UI
* Displays extracted links in tabular format
* Real-time status updates

### ⚡ High Performance Backend

* Built with FastAPI for speed and scalability
* Handles multiple requests efficiently

---

## 🏗️ Project Structure

```
AI-Web-Scraper/
│
├── backend/
│   ├── main.py        # FastAPI backend
│   ├── scraper.py     # Scraping logic
│
├── frontend/
│   ├── index.html     # UI
│   ├── script.js      # API calls
│   ├── style.css      # Styling
│
└── README.md
```

---

## ⚙️ Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/ai-web-scraper.git
cd ai-web-scraper
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Run the Project

### Start Backend (FastAPI)

```bash
uvicorn main:app --reload
```

Backend will run at:

```
http://127.0.0.1:8000
```

### Run Frontend

Open `frontend/index.html` with Live Server or browser:

```
http://127.0.0.1:5500/frontend/index.html
```

---

## 🔑 Environment Variables

Create a `.env` file in the backend folder:

```
API_KEY=your_api_key_here
```

> ⚠️ Required for AI analysis feature

---

## 📡 API Endpoints

### POST /scrape

Extracts links from a URL

**Request:**

```json
{
  "url": "https://example.com"
}
```

**Response:**

```json
{
  "links": [...]
}
```

---

### POST /analyze

Generates AI insights

**Request:**

```json
{
  "content": "webpage content"
}
```

---

## ❗ Common Issues

### AI Analysis Error

```
Could not resolve authentication method
```

✅ Fix:

* Set API key properly
* Ensure headers are configured

### CORS Error

* Check FastAPI CORS settings

---

## 🚀 Future Improvements

* Multi-page crawling
* AI summarization across pages
* Keyword clustering
* Export to CSV / JSON
* Chrome Extension

---

## 🧠 Use Cases

* Data Science research
* Competitive analysis
* SEO insights
* Automation pipelines

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repo
2. Create a new branch
3. Submit a pull request

---

## 📜 License

This project is open-source and available under the MIT License.

---
