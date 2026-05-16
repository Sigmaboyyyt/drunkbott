let tg = window.Telegram.WebApp;
tg.expand();
tg.enableClosingConfirmation();

let userData = {};

// Получение данных пользователя
try {
    userData = JSON.parse(tg.initDataUnsafe.user);
    document.getElementById('userName').innerText = userData.first_name || 'Игрок';
} catch(e) {}

// Загрузка баланса
async function loadBalance() {
    try {
        const response = await fetch('/get_balance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData: tg.initData })
        });
        const data = await response.json();
        document.getElementById('balance').innerText = data.balance;
    } catch(e) {}
}

loadBalance();

// Загрузка игры
async function loadGame(game) {
    let url = '';
    switch(game) {
        case 'rocket':
            url = '/rocket';
            break;
        case 'profile':
            url = '/profile';
            break;
        default:
            tg.showAlert(`🎮 Игра "${game.toUpperCase()}" скоро появится!`);
            return;
    }
    
    const response = await fetch(url);
    const html = await response.text();
    document.body.innerHTML = html;
    
    if (game === 'rocket' && typeof initRocket === 'function') {
        await initRocket();
    }
    if (game === 'profile') {
        await loadProfileData();
    }
}

// Загрузка профиля
async function loadProfileData() {
    const balance = await getBalance();
    document.getElementById('profileBalance').innerText = balance;
    
    const stats = await getUserStats();
    document.getElementById('wins').innerText = stats.wins || 0;
    document.getElementById('loses').innerText = stats.loses || 0;
    document.getElementById('totalGames').innerText = (stats.wins || 0) + (stats.loses || 0);
    document.getElementById('totalBet').innerText = stats.totalBet || 0;
    document.getElementById('totalWin').innerText = stats.totalWin || 0;
    document.getElementById('profileName').innerText = userData.first_name || 'Игрок';
}

async function getBalance() {
    try {
        const response = await fetch('/get_balance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData: tg.initData })
        });
        const data = await response.json();
        return data.balance;
    } catch(e) {
        return 10000;
    }
}

async function getUserStats() {
    try {
        const response = await fetch('/get_user_stats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData: tg.initData })
        });
        return await response.json();
    } catch(e) {
        return { wins: 0, loses: 0, totalBet: 0, totalWin: 0 };
    }
}

function goBack() {
    location.reload();
}

// Настройка кнопки закрытия
tg.MainButton.text = "ЗАКРЫТЬ";
tg.MainButton.onClick(() => tg.close());
tg.MainButton.show();