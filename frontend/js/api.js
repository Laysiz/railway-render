// API для работы с бэкендом
// ВАЖНО: для Render используем относительный путь
const API_BASE_URL = '/api';

class ApiClient {
    constructor() {
        this.baseUrl = API_BASE_URL;
    }

    // Получить заголовки с токеном
    getHeaders() {
        const token = localStorage.getItem('token');
        return {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
        };
    }

    // Обработка ответа
    async handleResponse(response) {
        if (!response.ok) {
            if (response.status === 401) {
                // Неавторизован - перенаправляем на страницу входа
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                window.location.href = 'login.html';
                throw new Error('Сессия истекла');
            }
            
            const error = await response.json().catch(() => ({}));
            throw new Error(error.message || `Ошибка ${response.status}`);
        }
        
        return response.json();
    }

    // GET запрос
    async get(endpoint) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'GET',
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    // POST запрос
    async post(endpoint, data) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify(data)
        });
        return this.handleResponse(response);
    }

    // PUT запрос
    async put(endpoint, data) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'PUT',
            headers: this.getHeaders(),
            body: JSON.stringify(data)
        });
        return this.handleResponse(response);
    }

    // DELETE запрос
    async delete(endpoint) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        return this.handleResponse(response);
    }

    // Аутентификация
    async login(login, password) {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login, password })
        });
        return response.json();
    }

    async getCurrentUser() {
        return this.get('/auth/me');
    }

    // Поезда
    async getTrains(date) {
        const url = date ? `/trains?date=${date}` : '/trains';
        return this.get(url);
    }

    async addTrain(data) {
        return this.post('/trains', data);
    }

    async updateTrain(trainId, data) {
        return this.put(`/trains/${trainId}`, data);
    }

    async updateTrainDates(trainId, data) {
        return this.put(`/trains/${trainId}/dates`, data);
    }

    async deleteTrain(trainId) {
        return this.delete(`/trains/${trainId}`);
    }

    // Вагоны
    async getWagons(trainId) {
        return this.get(`/trains/${trainId}/wagons`);
    }

    async addWagon(trainId, data) {
        return this.post(`/trains/${trainId}/wagons`, data);
    }

    async updateWagonNumber(wagonId, data) {
        return this.put(`/wagons/${wagonId}`, data);
    }

    async updateWagonSystems(wagonId, data) {
        return this.put(`/wagons/${wagonId}/systems`, data);
    }

    async deleteWagon(wagonId) {
        return this.delete(`/wagons/${wagonId}`);
    }

    // Поиск вагонов
    async searchWagon(number) {
        return this.get(`/wagons/search?number=${encodeURIComponent(number)}`);
    }

    // Заявки
    async getRequestsForWagon(wagonId) {
        return this.get(`/wagons/${wagonId}/requests`);
    }

    async createRequest(wagonId, data) {
        return this.post(`/wagons/${wagonId}/requests`, data);
    }

    async updateRequestStatus(requestId, data) {
        return this.put(`/requests/${requestId}/status`, data);
    }

    // Комментарии
    async getComments(requestId) {
        return this.get(`/requests/${requestId}/comments`);
    }

    async addComment(requestId, data) {
        return this.post(`/requests/${requestId}/comments`, data);
    }

    // Отцепленные вагоны
    async getDetachedWagons() {
        return this.get('/detached-wagons');
    }

    async deleteDetachedWagon(detachedId) {
        return this.delete(`/detached-wagons/${detachedId}`);
    }

    // Пользователи (для админов)
    async getUsers() {
        return this.get('/users');
    }

    async addUser(data) {
        return this.post('/users', data);
    }

    async updateUser(userId, data) {
        return this.put(`/users/${userId}`, data);
    }

    async deactivateUser(userId) {
        return this.post(`/users/${userId}/deactivate`, {});
    }

    async activateUser(userId) {
        return this.post(`/users/${userId}/activate`, {});
    }
}

// Глобальный экземпляр API
const api = new ApiClient();