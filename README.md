# **NASA-Hackathon**
This project is...

---

## **Project Structure**

```
NASA-Hackthon/
│
├── backend/                   
│   ├── app.py                 # Main backend server using FastAPI
│   ├── requirements.txt       # Python dependencies
│
└── frontend/                  # Vite + React Frontend for user interactions
    ├── src/
    │   └── components/        # React components for chat and UI
    ├── package.json           # Node.js dependencies
    └── public/                # Public assets (e.g., index.html, images, and other static files)
```

---

## **Prerequisites**

### **Backend:**

- **Python 3.7 or higher**
- **Pip** (Python package manager)
- **Virtual Environment (optional but recommended)**

### **Frontend:**

- **Node.js** (v14 or higher recommended)
- **npm** (Node package manager)
- **Vite** for React development

---

## **Setup Instructions**

### **1. Clone the Repository**

```bash
git clone https://github.com/dfsb4/NASA-Hackathon.git
```

---

### **2. Backend Setup**

1. Navigate to the backend directory:

   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment** (optional but recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # For MacOS / Linux
   .\venv\Scripts\activate   # For Windows
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**

   - Create a `.env` file in the `backend` directory.
   - Add your **Gemini API Key**
   - Add your **Earthdata account**
     ```
     GEMINI_API_KEY=your_gemini_api_key_here
     EARTHDATA_USERNAME=dfsb4
     EARTHDATA_PASSWORD=Sbjerk4@gmail.com
     ```
5. **Download the Dataset**
   ```bash
   cd backend/utils
   python download_mon.py
   ```
   
6. **Start the Backend Server:**

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 # For MacOS
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload # For Windows

   ```

6. **Backend Server** will run at:

   ```
   curl http://127.0.0.1:8000/api/health
   ```

---

### **3. Frontend Setup (Vite + React)**

1. Navigate to the frontend directory:

   ```bash
   cd ../frontend
   ```

2. **Install dependencies:**

   ```bash
   npm install
   npm install react-simple-maps d3-geo
   ```

3. **Start the Vite Development Server:**

   ```bash
   npm run dev
   ```

4. **Frontend will be accessible at:**

   ```
   http://localhost:5173/
   ```

---

## **Usage**

- Open your browser and go to **[http://localhost:5173](http://localhost:5173)**
- Enter your travel-related query in the chatbox.
- The AI will provide relevant travel recommendations using the RAG + Gemini API pipeline.

---

## **Troubleshooting**

- **API Key Error:** Ensure `GEMINI_API_KEY` is correctly set in the `.env` file.
- **Module Not Found:** Double-check if dependencies are installed:
  - Backend: `pip install -r requirements.txt`
  - Frontend: `npm install`
- **Port Conflicts:** Ensure no other services are running on port `5000` or `5173`.

---

## **Credits**

- **Google Gemini API** for advanced language generation.
- **ChromaDB** for efficient vector storage and semantic retrieval.
- **LangChain** for embedding and language model integration.
- **Vite + React** for frontend development.
- **Flask** for backend development.

---

## **License**

This project is licensed under the **MIT License**. Feel free to use and modify it for your own purposes.

