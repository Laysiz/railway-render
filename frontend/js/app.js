// Главный класс приложения
class TrainApp {
    constructor() {
        this.currentPage = 'calendar';
        this.selectedDate = new Date().toISOString().split('T')[0];
        this.currentTrain = null;
        this.currentWagon = null;
        this.user = null;
        
        this.init();
    }

    async init() {
        // Проверяем авторизацию
        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = 'login.html';
            return;
        }

        // Получаем информацию о пользователе
        try {
            const userStr = localStorage.getItem('user');
            if (userStr) {
                this.user = JSON.parse(userStr);
            } else {
                const response = await api.getCurrentUser();
                if (response.success) {
                    this.user = response.user;
                    localStorage.setItem('user', JSON.stringify(this.user));
                }
            }
        } catch (error) {
            console.error('Ошибка получения пользователя:', error);
        }

        // Обновляем информацию о пользователе в шапке
        this.updateUserInfo();

        // Показываем пункт меню "Пользователи" только для админов
        if (this.user && this.user.role === 'Администратор') {
            document.getElementById('usersMenuItem').style.display = 'flex';
        }

        // Инициализируем обработчики событий
        this.initEventListeners();

        // Загружаем начальную страницу
        this.loadPage(this.currentPage);
    }

    updateUserInfo() {
        const userInfoEl = document.getElementById('userInfo');
        if (this.user) {
            let roleIcon = '';
            switch (this.user.role) {
                case 'Администратор': roleIcon = '👑'; break;
                case 'Руководитель': roleIcon = '👔'; break;
                case 'Инженер': roleIcon = '🔧'; break;
                case 'ПЭМ': roleIcon = '👷'; break;
                default: roleIcon = '💻';
            }
            userInfoEl.innerHTML = `${roleIcon} ${this.user.full_name || this.user.login}`;
        }
    }

    initEventListeners() {
        // Меню
        document.getElementById('menuToggle').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });

        // Пункты меню
        document.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const page = e.currentTarget.dataset.page;
                if (page) {
                    this.switchPage(page);
                }
            });
        });

        // Кнопка выхода
        document.getElementById('logoutBtn').addEventListener('click', () => {
            this.logout();
        });

        // Закрытие модальных окон по клику на overlay
        document.getElementById('modalOverlay').addEventListener('click', (e) => {
            if (e.target === document.getElementById('modalOverlay')) {
                this.closeModal();
            }
        });
    }

    switchPage(page) {
        // Обновляем активный пункт меню
        document.querySelectorAll('.menu-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`.menu-item[data-page="${page}"]`).classList.add('active');

        // Закрываем меню на мобильных
        if (window.innerWidth <= 768) {
            document.getElementById('sidebar').classList.remove('open');
        }

        // Загружаем страницу
        this.currentPage = page;
        this.loadPage(page);
    }

    async loadPage(page) {
        // Показываем загрузку
        document.getElementById('loadingPage').style.display = 'flex';
        document.getElementById('pageContent').innerHTML = '';

        try {
            let html = '';
            switch (page) {
                case 'calendar':
                    html = await this.renderCalendarPage();
                    break;
                case 'trains':
                    html = await this.renderTrainsPage();
                    break;
                case 'search':
                    html = this.renderSearchPage();
                    break;
                case 'detached':
                    html = await this.renderDetachedPage();
                    break;
                case 'users':
                    html = await this.renderUsersPage();
                    break;
            }

            document.getElementById('pageContent').innerHTML = html;
            this.initializePageHandlers(page);
        } catch (error) {
            console.error('Ошибка загрузки страницы:', error);
            document.getElementById('pageContent').innerHTML = `
                <div class="card">
                    <div style="text-align: center; padding: 40px; color: var(--danger);">
                        <i class="fas fa-exclamation-triangle" style="font-size: 48px; margin-bottom: 20px;"></i>
                        <h3>Ошибка загрузки</h3>
                        <p>${error.message}</p>
                        <button class="btn btn-primary" onclick="app.loadPage('${page}')">
                            <i class="fas fa-redo"></i> Повторить
                        </button>
                    </div>
                </div>
            `;
        } finally {
            document.getElementById('loadingPage').style.display = 'none';
        }
    }

    // Страница календаря
    async renderCalendarPage() {
        const currentDate = new Date(this.selectedDate);
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        
        const startDay = firstDay.getDay() || 7; // Переводим воскресенье (0) в 7
        const daysInMonth = lastDay.getDate();
        
        let calendarDays = [];
        
        // Добавляем дни предыдущего месяца
        const prevMonthLastDay = new Date(year, month, 0).getDate();
        for (let i = startDay - 1; i > 0; i--) {
            calendarDays.push({
                day: prevMonthLastDay - i + 1,
                currentMonth: false,
                date: new Date(year, month - 1, prevMonthLastDay - i + 1)
            });
        }
        
        // Добавляем дни текущего месяца
        for (let i = 1; i <= daysInMonth; i++) {
            calendarDays.push({
                day: i,
                currentMonth: true,
                date: new Date(year, month, i)
            });
        }
        
        // Добавляем дни следующего месяца
        const totalCells = Math.ceil(calendarDays.length / 7) * 7;
        const nextMonthDays = totalCells - calendarDays.length;
        for (let i = 1; i <= nextMonthDays; i++) {
            calendarDays.push({
                day: i,
                currentMonth: false,
                date: new Date(year, month + 1, i)
            });
        }
        
        // Формируем недели
        const weeks = [];
        for (let i = 0; i < calendarDays.length; i += 7) {
            weeks.push(calendarDays.slice(i, i + 7));
        }
        
        const monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                           'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
        
        const today = new Date().toISOString().split('T')[0];
        const selectedDateStr = this.selectedDate;
        
        return `
            <div class="card">
                <div class="calendar-header">
                    <h2 class="calendar-month">${monthNames[month]} ${year}</h2>
                    <div>
                        <button class="calendar-nav-btn" id="prevMonth">
                            <i class="fas fa-chevron-left"></i>
                        </button>
                        <button class="calendar-nav-btn" id="nextMonth">
                            <i class="fas fa-chevron-right"></i>
                        </button>
                    </div>
                </div>
                
                <div class="calendar-weekdays">
                    <div>Пн</div>
                    <div>Вт</div>
                    <div>Ср</div>
                    <div>Чт</div>
                    <div>Пт</div>
                    <div>Сб</div>
                    <div>Вс</div>
                </div>
                
                <div class="calendar-days">
                    ${weeks.flat().map(day => {
                        const dateStr = day.date.toISOString().split('T')[0];
                        const classes = ['calendar-day'];
                        if (day.currentMonth) classes.push('current-month');
                        else classes.push('other-month');
                        if (dateStr === today) classes.push('today');
                        if (dateStr === selectedDateStr) classes.push('selected');
                        return `<div class="${classes.join(' ')}" data-date="${dateStr}">${day.day}</div>`;
                    }).join('')}
                </div>
                
                <div style="margin-top: 20px; display: flex; gap: 10px; justify-content: center;">
                    <button class="btn btn-primary" id="goToday">Сегодня</button>
                    <button class="btn btn-outline" id="goTomorrow">Завтра</button>
                    <button class="btn btn-outline" id="goYesterday">Вчера</button>
                </div>
            </div>
            
            <div class="card" style="margin-top: 20px;">
                <div class="card-header">
                    <h3 class="card-title">Поезда на ${new Date(selectedDateStr).toLocaleDateString('ru-RU')}</h3>
                    <div class="filter-container">
                        <button class="filter-btn active" data-filter="all">Все</button>
                        <button class="filter-btn" data-filter="depot">В депо</button>
                        <button class="filter-btn" data-filter="trip">В рейсе</button>
                    </div>
                </div>
                
                <div id="trainsList" class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Поезд</th>
                                <th>ПЭМ</th>
                                <th>Статус</th>
                                <th>Дней в рейсе</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody id="trainsTableBody">
                            <tr>
                                <td colspan="5" style="text-align: center;">Загрузка...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    // Страница со списком поездов
    async renderTrainsPage() {
        return `
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">Управление поездами</h2>
                    <button class="btn btn-primary" id="addTrainBtn">
                        <i class="fas fa-plus"></i> Новый поезд
                    </button>
                </div>
                
                <div class="filter-container">
                    <input type="text" class="form-control" placeholder="Поиск по названию..." id="trainSearch" style="max-width: 300px;">
                </div>
                
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Название</th>
                                <th>ПЭМ</th>
                                <th>Дата в депо</th>
                                <th>Дней в рейсе</th>
                                <th>Дата создания</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody id="trainsTableBody">
                            <tr>
                                <td colspan="6" style="text-align: center;">Загрузка...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    // Страница поиска вагона
    renderSearchPage() {
        return `
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">🔍 Поиск вагона</h2>
                </div>
                
                <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                    <input type="text" class="form-control" placeholder="Введите номер вагона..." id="searchInput">
                    <button class="btn btn-primary" id="searchBtn">
                        <i class="fas fa-search"></i> Поиск
                    </button>
                </div>
                
                <div id="searchResults" style="display: none;">
                    <h3 style="margin-bottom: 15px;">Результаты поиска:</h3>
                    <div class="table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Номер</th>
                                    <th>Тип</th>
                                    <th>Поезд</th>
                                    <th>Статус</th>
                                    <th>Действия</th>
                                </tr>
                            </thead>
                            <tbody id="searchResultsBody"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }

    // Страница отцепленных вагонов
    async renderDetachedPage() {
        return `
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">📦 Отцепленные вагоны</h2>
                    <button class="btn btn-primary" id="refreshDetached">
                        <i class="fas fa-sync"></i> Обновить
                    </button>
                </div>
                
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Номер вагона</th>
                                <th>Тип</th>
                                <th>Поезд</th>
                                <th>Дата отцепа</th>
                                <th>Причина</th>
                                <th>Заявок</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody id="detachedTableBody">
                            <tr>
                                <td colspan="7" style="text-align: center;">Загрузка...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    // Страница управления пользователями (только для админов)
    async renderUsersPage() {
        if (this.user.role !== 'Администратор') {
            return '<div class="card"><p style="color: var(--danger);">Доступ запрещен</p></div>';
        }
        
        return `
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">👥 Управление пользователями</h2>
                    <button class="btn btn-primary" id="addUserBtn">
                        <i class="fas fa-plus"></i> Добавить
                    </button>
                </div>
                
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Логин</th>
                                <th>Полное имя</th>
                                <th>Роль</th>
                                <th>Статус</th>
                                <th>Дата создания</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody id="usersTableBody">
                            <tr>
                                <td colspan="6" style="text-align: center;">Загрузка...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    // Инициализация обработчиков для страницы
    initializePageHandlers(page) {
        switch (page) {
            case 'calendar':
                this.initCalendarHandlers();
                this.loadTrainsForDate();
                break;
            case 'trains':
                this.initTrainsHandlers();
                this.loadAllTrains();
                break;
            case 'search':
                this.initSearchHandlers();
                break;
            case 'detached':
                this.initDetachedHandlers();
                this.loadDetachedWagons();
                break;
            case 'users':
                this.initUsersHandlers();
                this.loadUsers();
                break;
        }
    }

    // Обработчики для календаря
    initCalendarHandlers() {
        document.querySelectorAll('.calendar-day').forEach(day => {
            day.addEventListener('click', (e) => {
                const date = e.currentTarget.dataset.date;
                if (date) {
                    this.selectedDate = date;
                    this.loadPage('calendar');
                }
            });
        });

        document.getElementById('prevMonth')?.addEventListener('click', () => {
            const date = new Date(this.selectedDate);
            date.setMonth(date.getMonth() - 1);
            this.selectedDate = date.toISOString().split('T')[0];
            this.loadPage('calendar');
        });

        document.getElementById('nextMonth')?.addEventListener('click', () => {
            const date = new Date(this.selectedDate);
            date.setMonth(date.getMonth() + 1);
            this.selectedDate = date.toISOString().split('T')[0];
            this.loadPage('calendar');
        });

        document.getElementById('goToday')?.addEventListener('click', () => {
            this.selectedDate = new Date().toISOString().split('T')[0];
            this.loadPage('calendar');
        });

        document.getElementById('goTomorrow')?.addEventListener('click', () => {
            const date = new Date();
            date.setDate(date.getDate() + 1);
            this.selectedDate = date.toISOString().split('T')[0];
            this.loadPage('calendar');
        });

        document.getElementById('goYesterday')?.addEventListener('click', () => {
            const date = new Date();
            date.setDate(date.getDate() - 1);
            this.selectedDate = date.toISOString().split('T')[0];
            this.loadPage('calendar');
        });

        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.loadTrainsForDate(e.currentTarget.dataset.filter);
            });
        });
    }

    // Загрузка поездов для выбранной даты
    async loadTrainsForDate(filter = 'all') {
        try {
            const response = await api.getTrains(this.selectedDate);
            const tbody = document.getElementById('trainsTableBody');
            
            if (!response.success) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--danger);">${response.message}</td></tr>`;
                return;
            }
            
            let trains = response.trains || [];
            
            // Применяем фильтр
            if (filter !== 'all') {
                trains = trains.filter(t => t.status === filter);
            }
            
            if (trains.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Нет поездов на эту дату</td></tr>';
                return;
            }
            
            tbody.innerHTML = trains.map(train => `
                <tr>
                    <td><strong>${train.name}</strong></td>
                    <td>${train.pem_fio || '-'}</td>
                    <td>
                        <span class="status-badge ${train.status === 'depot' ? 'depot' : 'trip'}">
                            ${train.status === 'depot' ? '🏠 В депо' : '🚂 В рейсе'}
                        </span>
                    </td>
                    <td>${train.days_in_trip || 0} / ${train.trip_days} дн.</td>
                    <td>
                        <button class="btn btn-sm btn-primary view-train" data-id="${train.id}">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${this.user.role === 'Администратор' || this.user.role === 'Руководитель' ? `
                            <button class="btn btn-sm btn-warning edit-train" data-id="${train.id}">
                                <i class="fas fa-edit"></i>
                            </button>
                        ` : ''}
                    </td>
                </tr>
            `).join('');
            
            // Добавляем обработчики
            document.querySelectorAll('.view-train').forEach(btn => {
                btn.addEventListener('click', () => this.viewTrain(btn.dataset.id));
            });
            
            document.querySelectorAll('.edit-train').forEach(btn => {
                btn.addEventListener('click', () => this.editTrain(btn.dataset.id));
            });
            
        } catch (error) {
            console.error('Ошибка загрузки поездов:', error);
            document.getElementById('trainsTableBody').innerHTML = 
                `<tr><td colspan="5" style="text-align: center; color: var(--danger);">Ошибка загрузки: ${error.message}</td></tr>`;
        }
    }

    // Загрузка всех поездов
    async loadAllTrains() {
        try {
            const response = await api.getTrains();
            const tbody = document.getElementById('trainsTableBody');
            
            if (!response.success) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger);">${response.message}</td></tr>`;
                return;
            }
            
            const trains = response.trains || [];
            
            if (trains.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Нет поездов</td></tr>';
                return;
            }
            
            tbody.innerHTML = trains.map(train => `
                <tr>
                    <td><strong>${train.name}</strong></td>
                    <td>${train.pem_fio || '-'}</td>
                    <td>${new Date(train.depot_date).toLocaleDateString('ru-RU')}</td>
                    <td>${train.trip_days}</td>
                    <td>${train.created_at ? new Date(train.created_at).toLocaleDateString('ru-RU') : '-'}</td>
                    <td>
                        <button class="btn btn-sm btn-primary view-train" data-id="${train.id}">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${this.user.role === 'Администратор' || this.user.role === 'Руководитель' ? `
                            <button class="btn btn-sm btn-warning edit-train" data-id="${train.id}">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-danger delete-train" data-id="${train.id}" data-name="${train.name}">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : ''}
                    </td>
                </tr>
            `).join('');
            
            // Добавляем обработчики
            document.querySelectorAll('.view-train').forEach(btn => {
                btn.addEventListener('click', () => this.viewTrain(btn.dataset.id));
            });
            
            document.querySelectorAll('.edit-train').forEach(btn => {
                btn.addEventListener('click', () => this.editTrain(btn.dataset.id));
            });
            
            document.querySelectorAll('.delete-train').forEach(btn => {
                btn.addEventListener('click', () => this.deleteTrain(btn.dataset.id, btn.dataset.name));
            });
            
            // Поиск
            document.getElementById('trainSearch')?.addEventListener('input', (e) => {
                const search = e.target.value.toLowerCase();
                document.querySelectorAll('#trainsTableBody tr').forEach(row => {
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(search) ? '' : 'none';
                });
            });
            
        } catch (error) {
            console.error('Ошибка загрузки поездов:', error);
            document.getElementById('trainsTableBody').innerHTML = 
                `<tr><td colspan="6" style="text-align: center; color: var(--danger);">Ошибка загрузки: ${error.message}</td></tr>`;
        }
    }

    // Обработчики для страницы поездов
    initTrainsHandlers() {
        document.getElementById('addTrainBtn')?.addEventListener('click', () => {
            this.showAddTrainModal();
        });
    }

    // Показать модальное окно добавления поезда
    showAddTrainModal(train = null) {
        const isEdit = !!train;
        const modal = document.getElementById('modalContainer');
        
        modal.innerHTML = `
            <div class="modal-header">
                <h3 class="modal-title">${isEdit ? 'Редактирование' : 'Добавление'} поезда</h3>
                <button class="modal-close" onclick="app.closeModal()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label for="trainName">Название поезда *</label>
                    <input type="text" class="form-control" id="trainName" value="${isEdit ? train.name : ''}" placeholder="Введите название">
                </div>
                <div class="form-group">
                    <label for="trainPem">ФИО ПЭМ</label>
                    <input type="text" class="form-control" id="trainPem" value="${isEdit ? (train.pem_fio || '') : ''}" placeholder="Введите ФИО">
                </div>
                <div class="form-group">
                    <label for="trainDepotDate">Дата в депо *</label>
                    <input type="date" class="form-control" id="trainDepotDate" value="${isEdit ? train.depot_date : this.selectedDate}">
                </div>
                <div class="form-group">
                    <label for="trainTripDays">Дней в рейсе *</label>
                    <input type="number" class="form-control" id="trainTripDays" value="${isEdit ? train.trip_days : 7}" min="1" max="365">
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="app.closeModal()">Отмена</button>
                <button class="btn btn-primary" id="saveTrainBtn">Сохранить</button>
            </div>
        `;
        
        document.getElementById('modalOverlay').style.display = 'flex';
        
        document.getElementById('saveTrainBtn').addEventListener('click', async () => {
            const name = document.getElementById('trainName').value.trim();
            const pemFio = document.getElementById('trainPem').value.trim();
            const depotDate = document.getElementById('trainDepotDate').value;
            const tripDays = parseInt(document.getElementById('trainTripDays').value);
            
            if (!name || !depotDate || !tripDays) {
                this.showToast('Заполните все обязательные поля', 'error');
                return;
            }
            
            try {
                let response;
                if (isEdit) {
                    response = await api.updateTrain(train.id, {
                        name,
                        pem_fio: pemFio,
                        depot_date: depotDate,
                        trip_days: tripDays
                    });
                } else {
                    response = await api.addTrain({
                        name,
                        pem_fio: pemFio,
                        depot_date: depotDate,
                        trip_days: tripDays
                    });
                }
                
                if (response.success) {
                    this.showToast(response.message, 'success');
                    this.closeModal();
                    this.loadPage(this.currentPage);
                } else {
                    this.showToast(response.message, 'error');
                }
            } catch (error) {
                this.showToast('Ошибка: ' + error.message, 'error');
            }
        });
    }

    // Просмотр состава поезда
    async viewTrain(trainId) {
        try {
            const response = await api.getWagons(trainId);
            
            if (!response.success) {
                this.showToast(response.message, 'error');
                return;
            }
            
            const wagons = response.wagons || [];
            
            const modal = document.getElementById('modalContainer');
            modal.innerHTML = `
                <div class="modal-header">
                    <h3 class="modal-title">Состав поезда</h3>
                    <button class="modal-close" onclick="app.closeModal()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
                    ${wagons.length === 0 ? '<p>Нет вагонов</p>' : `
                        <table class="data-table" style="min-width: auto;">
                            <thead>
                                <tr>
                                    <th>№ вагона</th>
                                    <th>Тип</th>
                                    <th>Системы</th>
                                    <th>Заявки</th>
                                    <th>Действия</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${wagons.map(wagon => `
                                    <tr>
                                        <td>${wagon.number}</td>
                                        <td>${wagon.type}</td>
                                        <td>
                                            <div style="display: flex; gap: 5px;">
                                                ${['im', 'skdu', 'svnr', 'skbispp'].map(sys => {
                                                    const hasSys = wagon[`has_${sys}`];
                                                    const status = wagon[sys];
                                                    let icon = '';
                                                    if (hasSys) {
                                                        icon = status ? '✅' : '❌';
                                                    } else {
                                                        icon = '➖';
                                                    }
                                                    return `<span title="${sys.toUpperCase()}">${icon}</span>`;
                                                }).join(' ')}
                                            </div>
                                        </td>
                                        <td>${wagon.comments_count || 0}</td>
                                        <td>
                                            <button class="btn btn-sm btn-primary view-wagon-requests" data-id="${wagon.id}" data-number="${wagon.number}">
                                                <i class="fas fa-list"></i>
                                            </button>
                                            ${this.user.role === 'Администратор' || this.user.role === 'Руководитель' ? `
                                                <button class="btn btn-sm btn-warning edit-wagon-systems" data-id="${wagon.id}" data-number="${wagon.number}">
                                                    <i class="fas fa-cog"></i>
                                                </button>
                                            ` : ''}
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `}
                    
                    ${this.user.role === 'Администратор' || this.user.role === 'Руководитель' ? `
                        <div style="margin-top: 20px;">
                            <button class="btn btn-primary" id="addWagonBtn">
                                <i class="fas fa-plus"></i> Добавить вагон
                            </button>
                        </div>
                    ` : ''}
                </div>
                <div class="modal-footer">
                    <button class="btn btn-outline" onclick="app.closeModal()">Закрыть</button>
                </div>
            `;
            
            document.getElementById('modalOverlay').style.display = 'flex';
            
            // Добавляем обработчики
            document.querySelectorAll('.view-wagon-requests').forEach(btn => {
                btn.addEventListener('click', () => this.viewWagonRequests(btn.dataset.id, btn.dataset.number));
            });
            
            document.querySelectorAll('.edit-wagon-systems').forEach(btn => {
                btn.addEventListener('click', () => this.editWagonSystems(btn.dataset.id, btn.dataset.number));
            });
            
            document.getElementById('addWagonBtn')?.addEventListener('click', () => {
                this.showAddWagonModal(trainId);
            });
            
        } catch (error) {
            this.showToast('Ошибка: ' + error.message, 'error');
        }
    }

    // Просмотр заявок вагона
    async viewWagonRequests(wagonId, wagonNumber) {
        try {
            const response = await api.getRequestsForWagon(wagonId);
            
            if (!response.success) {
                this.showToast(response.message, 'error');
                return;
            }
            
            const requests = response.requests || [];
            
            const modal = document.getElementById('modalContainer');
            modal.innerHTML = `
                <div class="modal-header">
                    <h3 class="modal-title">Заявки вагона №${wagonNumber}</h3>
                    <button class="modal-close" onclick="app.closeModal()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
                    ${requests.length === 0 ? '<p>Нет заявок</p>' : `
                        <table class="data-table" style="min-width: auto;">
                            <thead>
                                <tr>
                                    <th>№ заявки</th>
                                    <th>Статус</th>
                                    <th>Система</th>
                                    <th>Создал</th>
                                    <th>Дата</th>
                                    <th>Действия</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${requests.map(req => `
                                    <tr>
                                        <td>${req.request_number}</td>
                                        <td>
                                            <span class="status-badge" style="background: ${req.status === 'Выполнено' ? '#d4edda' : req.status === 'Отложена' ? '#fff3cd' : '#cce5ff'};">
                                                ${req.status}
                                            </span>
                                        </td>
                                        <td>${req.system}</td>
                                        <td>${req.created_by}</td>
                                        <td>${req.created_at_formatted || ''}</td>
                                        <td>
                                            <button class="btn btn-sm btn-primary view-request" data-id="${req.id}">
                                                <i class="fas fa-eye"></i>
                                            </button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `}
                    
                    <div style="margin-top: 20px;">
                        <button class="btn btn-primary" id="createRequestBtn" data-wagon="${wagonId}">
                            <i class="fas fa-plus"></i> Создать заявку
                        </button>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-outline" onclick="app.closeModal()">Закрыть</button>
                </div>
            `;
            
            document.getElementById('modalOverlay').style.display = 'flex';
            
            document.querySelectorAll('.view-request').forEach(btn => {
                btn.addEventListener('click', () => this.viewRequest(btn.dataset.id));
            });
            
            document.getElementById('createRequestBtn')?.addEventListener('click', () => {
                this.showCreateRequestModal(wagonId, wagonNumber);
            });
            
        } catch (error) {
            this.showToast('Ошибка: ' + error.message, 'error');
        }
    }

    // Просмотр заявки
    async viewRequest(requestId) {
        // В реальном приложении здесь нужно получить данные заявки
        // Для простоты показываем заглушку
        this.showToast('Функция просмотра заявки будет реализована позже', 'info');
    }

    // Редактирование систем вагона
    editWagonSystems(wagonId, wagonNumber) {
        // В реальном приложении здесь нужно загрузить текущие системы
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header">
                <h3 class="modal-title">Системы вагона №${wagonNumber}</h3>
                <button class="modal-close" onclick="app.closeModal()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label>Системы:</label>
                    <div style="margin-top: 10px;">
                        ${['IM', 'SKDU', 'SVNR', 'SKBiSPP'].map(sys => `
                            <div style="margin-bottom: 15px;">
                                <div style="display: flex; align-items: center; gap: 20px;">
                                    <span style="width: 80px; font-weight: bold;">${sys}</span>
                                    <label>
                                        <input type="checkbox" class="has-system" data-system="${sys}" checked> Установлена
                                    </label>
                                    <label>
                                        <input type="checkbox" class="works-system" data-system="${sys}" checked> Работает
                                    </label>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="form-group">
                    <label for="wagonComment">Комментарий</label>
                    <textarea class="form-control" id="wagonComment" rows="3"></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="app.closeModal()">Отмена</button>
                <button class="btn btn-primary" id="saveSystemsBtn">Сохранить</button>
            </div>
        `;
        
        document.getElementById('modalOverlay').style.display = 'flex';
        
        // Привязываем чекбоксы
        document.querySelectorAll('.has-system').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const system = e.target.dataset.system;
                const worksCb = document.querySelector(`.works-system[data-system="${system}"]`);
                worksCb.disabled = !e.target.checked;
                if (!e.target.checked) {
                    worksCb.checked = false;
                }
            });
        });
        
        document.getElementById('saveSystemsBtn').addEventListener('click', async () => {
            const systems = {};
            const hasSystems = {};
            
            ['IM', 'SKDU', 'SVNR', 'SKBiSPP'].forEach(sys => {
                hasSystems[sys] = document.querySelector(`.has-system[data-system="${sys}"]`).checked;
                systems[sys] = document.querySelector(`.works-system[data-system="${sys}"]`).checked;
            });
            
            const comment = document.getElementById('wagonComment').value;
            
            try {
                const response = await api.updateWagonSystems(wagonId, { systems, has_systems: hasSystems, comment });
                
                if (response.success) {
                    this.showToast(response.message, 'success');
                    this.closeModal();
                } else {
                    this.showToast(response.message, 'error');
                }
            } catch (error) {
                this.showToast('Ошибка: ' + error.message, 'error');
            }
        });
    }

    // Показать модальное окно добавления вагона
    showAddWagonModal(trainId) {
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header">
                <h3 class="modal-title">Добавление вагона</h3>
                <button class="modal-close" onclick="app.closeModal()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label for="wagonNumber">Номер вагона *</label>
                    <input type="text" class="form-control" id="wagonNumber" placeholder="Например: 064-12345">
                </div>
                <div class="form-group">
                    <label for="wagonType">Тип вагона *</label>
                    <select class="form-control" id="wagonType">
                        <option value="Купейный">Купейный</option>
                        <option value="Плацкарт">Плацкарт</option>
                        <option value="Сидячий">Сидячий</option>
                        <option value="СВ">СВ</option>
                        <option value="Штабной">Штабной</option>
                        <option value="Ресторан">Ресторан</option>
                    </select>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="app.closeModal()">Отмена</button>
                <button class="btn btn-primary" id="saveWagonBtn">Сохранить</button>
            </div>
        `;
        
        document.getElementById('modalOverlay').style.display = 'flex';
        
        document.getElementById('saveWagonBtn').addEventListener('click', async () => {
            const number = document.getElementById('wagonNumber').value.trim();
            const type = document.getElementById('wagonType').value;
            
            if (!number) {
                this.showToast('Введите номер вагона', 'error');
                return;
            }
            
            try {
                const response = await api.addWagon(trainId, { number, type });
                
                if (response.success) {
                    this.showToast(response.message, 'success');
                    this.closeModal();
                    this.viewTrain(trainId); // Обновляем состав
                } else {
                    this.showToast(response.message, 'error');
                }
            } catch (error) {
                this.showToast('Ошибка: ' + error.message, 'error');
            }
        });
    }

    // Показать модальное окно создания заявки
    showCreateRequestModal(wagonId, wagonNumber) {
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header">
                <h3 class="modal-title">Создание заявки для вагона №${wagonNumber}</h3>
                <button class="modal-close" onclick="app.closeModal()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label for="requestPemType">Тип исполнителя *</label>
                    <select class="form-control" id="requestPemType">
                        <option value="ПЭМ">ПЭМ</option>
                        <option value="Электроник">Электроник</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="requestSystem">Система *</label>
                    <select class="form-control" id="requestSystem">
                        <option value="IM">IM</option>
                        <option value="SKDU">SKDU</option>
                        <option value="SVNR">SVNR</option>
                        <option value="SKBiSPP">SKBiSPP</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="requestDescription">Описание *</label>
                    <textarea class="form-control" id="requestDescription" rows="4" placeholder="Опишите проблему..."></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="app.closeModal()">Отмена</button>
                <button class="btn btn-primary" id="createRequestBtn">Создать</button>
            </div>
        `;
        
        document.getElementById('modalOverlay').style.display = 'flex';
        
        document.getElementById('createRequestBtn').addEventListener('click', async () => {
            const pemType = document.getElementById('requestPemType').value;
            const system = document.getElementById('requestSystem').value;
            const description = document.getElementById('requestDescription').value.trim();
            
            if (!description) {
                this.showToast('Введите описание', 'error');
                return;
            }
            
            try {
                const response = await api.createRequest(wagonId, { pem_type: pemType, system, description });
                
                if (response.success) {
                    this.showToast(response.message, 'success');
                    this.closeModal();
                    this.viewWagonRequests(wagonId, wagonNumber); // Обновляем список заявок
                } else {
                    this.showToast(response.message, 'error');
                }
            } catch (error) {
                this.showToast('Ошибка: ' + error.message, 'error');
            }
        });
    }

    // Редактирование поезда
    editTrain(trainId) {
        // Загружаем данные поезда
        api.getTrains().then(response => {
            if (response.success) {
                const train = response.trains.find(t => t.id === trainId);
                if (train) {
                    this.showAddTrainModal(train);
                }
            }
        });
    }

    // Удаление поезда
    deleteTrain(trainId, trainName) {
        if (!confirm(`Удалить поезд "${trainName}"?\nВсе вагоны будут сохранены в Отцеп.`)) {
            return;
        }
        
        api.deleteTrain(trainId).then(response => {
            if (response.success) {
                this.showToast(response.message, 'success');
                this.loadPage(this.currentPage);
            } else {
                this.showToast(response.message, 'error');
            }
        }).catch(error => {
            this.showToast('Ошибка: ' + error.message, 'error');
        });
    }

    // Обработчики для страницы поиска
    initSearchHandlers() {
        document.getElementById('searchBtn').addEventListener('click', () => {
            this.performSearch();
        });
        
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });
    }

    async performSearch() {
        const number = document.getElementById('searchInput').value.trim();
        
        if (!number) {
            this.showToast('Введите номер вагона', 'error');
            return;
        }
        
        try {
            const response = await api.searchWagon(number);
            
            if (!response.success) {
                this.showToast(response.message, 'error');
                return;
            }
            
            const results = response.results;
            const tbody = document.getElementById('searchResultsBody');
            
            if (results.found_count === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Вагоны не найдены</td></tr>';
            } else {
                const rows = [];
                
                // Вагоны в составе
                results.in_trains.forEach(wagon => {
                    rows.push(`
                        <tr>
                            <td>${wagon.number}</td>
                            <td>${wagon.type}</td>
                            <td>${wagon.train_name}</td>
                            <td><span class="status-badge depot">В составе</span></td>
                            <td>
                                <button class="btn btn-sm btn-primary view-wagon" data-id="${wagon.id}">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </td>
                        </tr>
                    `);
                });
                
                // Вагоны в отцепе
                results.in_detached.forEach(wagon => {
                    rows.push(`
                        <tr>
                            <td>${wagon.number}</td>
                            <td>${wagon.type}</td>
                            <td>${wagon.train_name}</td>
                            <td><span class="status-badge warning">Отцеп</span></td>
                            <td>
                                <button class="btn btn-sm btn-primary view-detached" data-id="${wagon.id}">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </td>
                        </tr>
                    `);
                });
                
                tbody.innerHTML = rows.join('');
            }
            
            document.getElementById('searchResults').style.display = 'block';
            
            // Добавляем обработчики
            document.querySelectorAll('.view-wagon').forEach(btn => {
                btn.addEventListener('click', () => {
                    const wagon = results.in_trains.find(w => w.id === btn.dataset.id);
                    if (wagon) {
                        this.viewTrain(wagon.train_id);
                    }
                });
            });
            
        } catch (error) {
            this.showToast('Ошибка: ' + error.message, 'error');
        }
    }

    // Обработчики для страницы отцепленных вагонов
    initDetachedHandlers() {
        document.getElementById('refreshDetached')?.addEventListener('click', () => {
            this.loadDetachedWagons();
        });
    }

    async loadDetachedWagons() {
        try {
            const response = await api.getDetachedWagons();
            const tbody = document.getElementById('detachedTableBody');
            
            if (!response.success) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger);">${response.message}</td></tr>`;
                return;
            }
            
            const wagons = response.wagons || [];
            
            if (wagons.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">Нет отцепленных вагонов</td></tr>';
                return;
            }
            
            tbody.innerHTML = wagons.map(wagon => `
                <tr>
                    <td>${wagon.wagon_number}</td>
                    <td>${wagon.wagon_type}</td>
                    <td>${wagon.train_name}</td>
                    <td>${new Date(wagon.detached_date).toLocaleDateString('ru-RU')}</td>
                    <td>${wagon.reason}</td>
                    <td>${wagon.requests_count}</td>
                    <td>
                        <button class="btn btn-sm btn-primary view-detached-details" data-id="${wagon.id}">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${this.user.role === 'Администратор' ? `
                            <button class="btn btn-sm btn-danger delete-detached" data-id="${wagon.id}" data-number="${wagon.wagon_number}">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : ''}
                    </td>
                </tr>
            `).join('');
            
            // Добавляем обработчики
            document.querySelectorAll('.view-detached-details').forEach(btn => {
                btn.addEventListener('click', () => this.viewDetachedWagon(btn.dataset.id));
            });
            
            document.querySelectorAll('.delete-detached').forEach(btn => {
                btn.addEventListener('click', () => this.deleteDetachedWagon(btn.dataset.id, btn.dataset.number));
            });
            
        } catch (error) {
            console.error('Ошибка загрузки отцепленных вагонов:', error);
            document.getElementById('detachedTableBody').innerHTML = 
                `<tr><td colspan="7" style="text-align: center; color: var(--danger);">Ошибка загрузки: ${error.message}</td></tr>`;
        }
    }

    // Просмотр отцепленного вагона
    viewDetachedWagon(detachedId) {
        // В реальном приложении здесь нужно загрузить данные
        this.showToast('Функция просмотра будет реализована позже', 'info');
    }

    // Удаление отцепленного вагона
    deleteDetachedWagon(detachedId, wagonNumber) {
        if (!confirm(`Удалить вагон ${wagonNumber} навсегда? Это действие нельзя отменить!`)) {
            return;
        }
        
        api.deleteDetachedWagon(detachedId).then(response => {
            if (response.success) {
                this.showToast(response.message, 'success');
                this.loadDetachedWagons();
            } else {
                this.showToast(response.message, 'error');
            }
        }).catch(error => {
            this.showToast('Ошибка: ' + error.message, 'error');
        });
    }

    // Обработчики для страницы пользователей
    initUsersHandlers() {
        document.getElementById('addUserBtn')?.addEventListener('click', () => {
            this.showAddUserModal();
        });
    }

    async loadUsers() {
        try {
            const response = await api.getUsers();
            const tbody = document.getElementById('usersTableBody');
            
            if (!response.success) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger);">${response.message}</td></tr>`;
                return;
            }
            
            const users = response.users || [];
            
            tbody.innerHTML = users.map(user => `
                <tr>
                    <td>${user.login}</td>
                    <td>${user.full_name || ''}</td>
                    <td>${user.role}</td>
                    <td>
                        <span class="status-badge ${user.is_active ? 'depot' : 'warning'}">
                            ${user.is_active ? 'Активен' : 'Неактивен'}
                        </span>
                    </td>
                    <td>${user.created_at ? new Date(user.created_at).toLocaleDateString('ru-RU') : '-'}</td>
                    <td>
                        <button class="btn btn-sm btn-warning edit-user" data-id="${user.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                        ${user.is_active ? `
                            <button class="btn btn-sm btn-danger deactivate-user" data-id="${user.id}" data-login="${user.login}">
                                <i class="fas fa-ban"></i>
                            </button>
                        ` : `
                            <button class="btn btn-sm btn-success activate-user" data-id="${user.id}" data-login="${user.login}">
                                <i class="fas fa-check"></i>
                            </button>
                        `}
                    </td>
                </tr>
            `).join('');
            
            // Добавляем обработчики
            document.querySelectorAll('.edit-user').forEach(btn => {
                btn.addEventListener('click', () => {
                    const user = users.find(u => u.id === btn.dataset.id);
                    if (user) {
                        this.showAddUserModal(user);
                    }
                });
            });
            
            document.querySelectorAll('.deactivate-user').forEach(btn => {
                btn.addEventListener('click', () => this.deactivateUser(btn.dataset.id, btn.dataset.login));
            });
            
            document.querySelectorAll('.activate-user').forEach(btn => {
                btn.addEventListener('click', () => this.activateUser(btn.dataset.id, btn.dataset.login));
            });
            
        } catch (error) {
            console.error('Ошибка загрузки пользователей:', error);
            document.getElementById('usersTableBody').innerHTML = 
                `<tr><td colspan="6" style="text-align: center; color: var(--danger);">Ошибка загрузки: ${error.message}</td></tr>`;
        }
    }

    // Показать модальное окно добавления/редактирования пользователя
    showAddUserModal(user = null) {
        const isEdit = !!user;
        const modal = document.getElementById('modalContainer');
        
        modal.innerHTML = `
            <div class="modal-header">
                <h3 class="modal-title">${isEdit ? 'Редактирование' : 'Добавление'} пользователя</h3>
                <button class="modal-close" onclick="app.closeModal()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label for="userLogin">Логин *</label>
                    <input type="text" class="form-control" id="userLogin" value="${isEdit ? user.login : ''}" ${isEdit ? 'readonly' : ''}>
                </div>
                <div class="form-group">
                    <label for="userFullName">Полное имя *</label>
                    <input type="text" class="form-control" id="userFullName" value="${isEdit ? (user.full_name || '') : ''}">
                </div>
                <div class="form-group">
                    <label for="userPassword">${isEdit ? 'Новый пароль (оставьте пустым, если не меняется)' : 'Пароль *'}</label>
                    <input type="password" class="form-control" id="userPassword">
                </div>
                <div class="form-group">
                    <label for="userRole">Роль *</label>
                    <select class="form-control" id="userRole">
                        <option value="Администратор" ${isEdit && user.role === 'Администратор' ? 'selected' : ''}>Администратор</option>
                        <option value="Руководитель" ${isEdit && user.role === 'Руководитель' ? 'selected' : ''}>Руководитель</option>
                        <option value="Инженер" ${isEdit && user.role === 'Инженер' ? 'selected' : ''}>Инженер</option>
                        <option value="ПЭМ" ${isEdit && user.role === 'ПЭМ' ? 'selected' : ''}>ПЭМ</option>
                        <option value="Электроник" ${isEdit && user.role === 'Электроник' ? 'selected' : ''}>Электроник</option>
                    </select>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="app.closeModal()">Отмена</button>
                <button class="btn btn-primary" id="saveUserBtn">Сохранить</button>
            </div>
        `;
        
        document.getElementById('modalOverlay').style.display = 'flex';
        
        document.getElementById('saveUserBtn').addEventListener('click', async () => {
            const login = document.getElementById('userLogin').value.trim();
            const fullName = document.getElementById('userFullName').value.trim();
            const password = document.getElementById('userPassword').value;
            const role = document.getElementById('userRole').value;
            
            if (!login || !fullName || (!isEdit && !password)) {
                this.showToast('Заполните все обязательные поля', 'error');
                return;
            }
            
            try {
                let response;
                if (isEdit) {
                    const data = { login, full_name: fullName, role };
                    if (password) {
                        data.password = password;
                    }
                    response = await api.updateUser(user.id, data);
                } else {
                    response = await api.addUser({ login, full_name: fullName, password, role });
                }
                
                if (response.success) {
                    this.showToast(response.message, 'success');
                    this.closeModal();
                    this.loadUsers();
                } else {
                    this.showToast(response.message, 'error');
                }
            } catch (error) {
                this.showToast('Ошибка: ' + error.message, 'error');
            }
        });
    }

    // Деактивация пользователя
    deactivateUser(userId, userLogin) {
        if (!confirm(`Деактивировать пользователя ${userLogin}?`)) {
            return;
        }
        
        api.deactivateUser(userId).then(response => {
            if (response.success) {
                this.showToast(response.message, 'success');
                this.loadUsers();
            } else {
                this.showToast(response.message, 'error');
            }
        }).catch(error => {
            this.showToast('Ошибка: ' + error.message, 'error');
        });
    }

    // Активация пользователя
    activateUser(userId, userLogin) {
        api.activateUser(userId).then(response => {
            if (response.success) {
                this.showToast(response.message, 'success');
                this.loadUsers();
            } else {
                this.showToast(response.message, 'error');
            }
        }).catch(error => {
            this.showToast('Ошибка: ' + error.message, 'error');
        });
    }

    // Выход из системы
    logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    }

    // Закрытие модального окна
    closeModal() {
        document.getElementById('modalOverlay').style.display = 'none';
    }

    // Показать уведомление
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
}

// Запуск приложения после загрузки страницы
document.addEventListener('DOMContentLoaded', () => {
    window.app = new TrainApp();
});