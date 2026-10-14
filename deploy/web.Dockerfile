FROM node:24.19.0-bookworm-slim@sha256:a9f5f7c91a432850b2a8a7797adf5eadb6c733ceed61167806cee7ea7fbc29df AS build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
COPY --from=npm_cache / /npm-cache/_cacache
RUN --network=none npm ci --offline --cache=/npm-cache
COPY frontend ./
RUN --network=none npm run build

FROM nginx:1.30.5-alpine@sha256:0985e772fb9f729e6fa0980da05fca5d9c468e870eed43071545afa9d2e27d94
COPY --from=build --chmod=755 /build/frontend/dist /srv/pathable
COPY --chmod=644 deploy/nginx.conf /etc/nginx/nginx.conf
COPY --chmod=644 deploy/security-headers.conf /etc/nginx/security-headers.conf
USER 10001:10001
EXPOSE 8443
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
