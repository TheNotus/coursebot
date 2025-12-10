#!/bin/bash

# Проверка, установлен ли poetry
if ! command -v poetry &> /dev/null
then
    echo "Poetry не найден. Пожалуйста, установите Poetry: https://python-poetry.org/docs/#installation"
    exit 1
fi

echo "Установка зависимостей с помощью Poetry..."
poetry install

echo "Установка завершена."