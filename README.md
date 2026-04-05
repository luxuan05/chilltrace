# Welcome to ESD G5 Team 7 Project - ChillTrace

## Project info

Our solution is a platform to manage the cold chain logistics process from buying to delivery. 

**To run the app**

1. To run frontend

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd frontend

# Step 3: Create Frontend .env file
From the report copy and paste the code into a new .env file in the frontend folder

# Step 4: Install the necessary dependencies.
npm i

# Step 5: Start the development server with auto-reloading and an instant preview.
npm run dev
```

2. To run Backend
```sh
# Step 1: Navigate to the backend folder
cd backend

# Step 2: Create Backend .env file
From the report copy and paste the code into a new .env file in the backend folder

# Step 3: Download the ca.pem file from eLearn submission
Copy or download the ca.pem file into the backend folder

# Step 4: Create virtual environment
(On Mac/Linux)
source venv/bin/activate

(On Windows)
venv\Scripts\activate

# Step 5: Replace Docker ID
In the compose.yaml file replace docker id under image

#Step 6: Run Docker Compose
docker compose up --build
```

## What technologies are used for this project?

This project is built with:

- React
- Python
- OutSystem
- MySQL
- RabbitMQ
- Docker 

