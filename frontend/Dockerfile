FROM php:8.2-fpm-alpine
RUN docker-php-ext-install pdo pdo_mysql mysqli
RUN apk add --no-cache libpng-dev && docker-php-ext-install gd
WORKDIR /var/www/html
EXPOSE 9000
