# syntax=docker/dockerfile:1

FROM node:16.17.0
WORKDIR /app
COPY ["package.json", "package-lock.json*", "./"]
COPY [".env", "./"]
RUN npm install 
COPY ["app.js", "./"]
EXPOSE 80/tcp
CMD [ "node", "app.js" ]
