# syntax=docker/dockerfile:1
# Stage 1: Build (работает на ARM и AMD64)
FROM --platform=$BUILDPLATFORM node:22-alpine3.22 AS builder
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
# Передаём URL API при сборке
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Stage 2: Serve via nginx (финальный образ для AMD64 в кластере)
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
