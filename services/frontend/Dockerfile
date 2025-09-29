# Simple Frontend Dockerfile for Development
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json ./
RUN npm install

# Copy source code
COPY . .

# Build the app
RUN npm run build

EXPOSE 3000

# Start the application
CMD ["npm", "start"]