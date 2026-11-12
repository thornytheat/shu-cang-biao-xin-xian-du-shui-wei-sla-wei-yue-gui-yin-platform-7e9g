FROM node:20-alpine AS build
WORKDIR /app

# 构建期 registry 可覆盖（默认国内镜像，避免 npm registry 不可达）
ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN npm config set registry ${NPM_REGISTRY}

COPY package.json /app/package.json
RUN npm install --registry=${NPM_REGISTRY} --no-audit --no-fund

COPY . /app
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
