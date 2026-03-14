# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# SPA fallback + API proxy config
RUN cat > /etc/nginx/conf.d/default.conf <<- 'EOF'
	server {
		listen 80;
		server_name _;
		root /usr/share/nginx/html;
		index index.html;

		location /api/ {
			proxy_pass http://backend:8000;
			proxy_set_header Host $host;
			proxy_set_header X-Real-IP $remote_addr;
			proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
			proxy_set_header X-Forwarded-Proto $scheme;
			proxy_buffering off;
			proxy_cache off;
			chunked_transfer_encoding on;
		}

		location / {
			try_files $uri $uri/ /index.html;
		}

		location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
			expires 1y;
			add_header Cache-Control "public, immutable";
		}
	}
EOF

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
