// promotions.js - JavaScript для управления акциями
console.log("promotions.js loaded");

document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded, attaching event listeners");
    // Загружаем список акций при загрузке страницы
    if (document.getElementById('promotions-table-body')) {
        loadPromotions();
    }

    // Обработчик отправки формы добавления/редактирования акции
    const promotionForm = document.getElementById('promotion-form');
    if (promotionForm) {
        promotionForm.addEventListener('submit', handlePromotionFormSubmit);
    }

    // Устанавливаем делегирование событий для кнопки подтверждения удаления
    document.addEventListener('click', function(event) {
        const confirmDeleteBtn = event.target.closest('#confirm-delete-btn');
        if (confirmDeleteBtn) {
            console.log("Confirm delete button clicked");
            handleDeleteConfirmation();
        }
    });

    // Обработчик для кнопок удаления (для открытия модального окна)
    document.addEventListener('click', function(event) {
        if (event.target && event.target.classList.contains('btn-danger') && event.target.textContent.trim() === 'Удалить') {
            const promotionId = event.target.getAttribute('data-promotion-id');
            const promotionName = event.target.getAttribute('data-promotion-name');
            if (promotionId && promotionName) {
                confirmDelete(promotionId, promotionName);
            }
        }
    });

});

// Функция для загрузки списка акций
async function loadPromotions() {
    try {
        const response = await fetch('/api/promotions');
        if (!response.ok) {
            throw new Error(`Ошибка загрузки акций: ${response.status}`);
        }
        
        const promotions = await response.json();
        displayPromotions(promotions);
    } catch (error) {
        console.error('Ошибка при загрузке акций:', error);
        showNotification('Ошибка при загрузке акций', 'danger');
    }
}

// Функция для отображения акций в таблице
function displayPromotions(promotions) {
    const tableBody = document.getElementById('promotions-table-body');
    if (!tableBody) return;
    
    // Очищаем таблицу
    tableBody.innerHTML = '';
    
    if (promotions.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center">Нет акций для отображения</td></tr>';
        return;
    }
    
    promotions.forEach(promotion => {
        const row = document.createElement('tr');
        row.dataset.promotionId = promotion.id;
        
        // Форматируем даты
        const startDate = formatDate(promotion.start_date);
        const endDate = formatDate(promotion.end_date);
        
        row.innerHTML = `
            <td>${promotion.name}</td>
            <td>${promotion.description}</td>
            <td>${promotion.course_name}</td> <!-- Отображаем название курса -->
            <td>${promotion.discounted_price}</td> <!-- Отображаем акционную цену -->
            <td>${startDate}</td>
            <td>${endDate}</td>
            <td>
                ${promotion.image_path ?
                    `<img src="/${promotion.image_path.replace('src/web_app/static/', '')}" alt="Изображение акции" style="max-width: 100px; max-height: 100px;">` :
                    'Нет изображения'
                }
            </td>
            <td>
                <a href="/promotions/${promotion.id}/edit" class="btn btn-warning btn-sm me-2">Редактировать</a>
                <button type="button" class="btn btn-danger btn-sm" data-promotion-id="${promotion.id}" data-promotion-name="${promotion.name}">Удалить</button> <!-- Используем шаблонную строку для имени -->
            </td>
        `;
        
        tableBody.appendChild(row);
    });
}

// Функция для форматирования даты
function formatDate(dateString) {
    const options = { year: 'numeric', month: '2-digit', day: '2-digit' };
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', options);
}

// Функция для обработки отправки формы добавления/редактирования акции
async function handlePromotionFormSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    // Получаем URL и метод из формы
    let url, method;
    const promotionId = form.action.match(/\/promotions\/(\d+)\/edit/);
    
    if (promotionId) {
        // Редактирование
        url = `/api/promotions/${promotionId[1]}`;
        method = 'PUT';
    } else {
        // Добавление
        url = '/api/promotions';
        method = 'POST';
    }
    
    try {
        const response = await fetch(url, {
            method: method,
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(`Акция "${result.name}" успешно ${promotionId ? 'обновлена' : 'добавлена'}`, 'success');
            
            // Перенаправляем на страницу списка акций
            setTimeout(() => {
                window.location.href = '/promotions';
            }, 1500);
        } else {
            const errorData = await response.json();
            let errorMessage = 'Ошибка: Неизвестная ошибка';

            if (errorData && errorData.detail) {
                if (Array.isArray(errorData.detail)) {
                    errorMessage = 'Ошибки валидации:\n';
                    errorData.detail.forEach(error => {
                        const loc = error.loc && error.loc.length > 0 ? error.loc[error.loc.length - 1] : 'unknown field';
                        errorMessage += `Поле '${loc}': ${error.msg}\n`;
                    });
                } else if (typeof errorData.detail === 'string') {
                    errorMessage = `Ошибка: ${errorData.detail}`;
                }
            }
            showNotification(errorMessage, 'danger');
        }
    } catch (error) {
        console.error('Ошибка при отправке формы:', error);
        showNotification('Ошибка при отправке формы', 'danger');
    }
}

// Функция для подтверждения удаления акции
function confirmDelete(promotionId, promotionName) {
    console.log("confirmDelete called with ID:", promotionId);
    document.getElementById('confirm-delete-btn').dataset.promotionId = promotionId;
    const promotionNameSpan = document.getElementById('promotionNameToDelete');
    if (promotionNameSpan) {
        promotionNameSpan.textContent = promotionName; // Заполняем имя акции в модальном окне
    }
    // Показываем модальное окно
    const deleteModalElement = document.getElementById('deleteModal');
    if (deleteModalElement) {
        const modal = new bootstrap.Modal(deleteModalElement);
        modal.show();
    }
}

// Функция для обработки подтверждения удаления
async function handleDeleteConfirmation() {
    console.log("handleDeleteConfirmation called");
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    const promotionId = parseInt(confirmDeleteBtn.dataset.promotionId);
    
    if (!promotionId) {
        console.error("No promotion ID found for deletion");
        return;
    }
    
    try {
        const response = await fetch(`/api/promotions/${promotionId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('Акция успешно удалена', 'success');
            
            // Находим строку таблицы с соответствующим promotionId и удаляем её
            const rowToRemove = document.querySelector(`tr[data-promotion-id='${promotionId}']`);
            if (rowToRemove) {
                rowToRemove.remove();
            }
            
            // Закрываем модальное окно
            const deleteModalElement = document.getElementById('deleteModal');
            if (deleteModalElement) {
                const modal = bootstrap.Modal.getInstance(deleteModalElement);
                if (modal) {
                    modal.hide();
                }
            }
        } else {
            const errorData = await response.json();
            showNotification(`Ошибка при удалении: ${errorData.detail || 'Неизвестная ошибка'}`, 'danger');
        }
    } catch (error) {
        console.error('Ошибка при удалении акции:', error);
        showNotification('Ошибка при удалении акции', 'danger');
    }
}

// Функция для отображения уведомлений
function showNotification(message, type) {
    // Удаляем существующие уведомления
    const existingAlerts = document.querySelectorAll('.alert-temp');
    existingAlerts.forEach(alert => alert.remove());
    
    // Создаем элемент уведомления
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-temp alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Вставляем уведомление в начало контейнера
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Автоматически скрываем уведомление через 5 секунд
    setTimeout(() => {
        if (alertDiv.parentNode) {
            const bsAlert = bootstrap.Alert.getInstance(alertDiv);
            if (bsAlert) {
                bsAlert.close();
            } else {
                alertDiv.remove();
            }
        }
    }, 5000);
}
