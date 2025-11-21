const sections = [
    {
        id: 'mi-lista',
        name: 'Mi Lista',
        icon: '❤️',
        color: 'from-red-600 to-pink-600',
        description: 'Tus animes guardados',
        badge: '12 series',
        endpoint: '/api/mi-lista'
    },
    {
        id: 'proyectar',
        name: 'Proyectar Éxito',
        icon: '🔥',
        color: 'from-orange-500 to-yellow-500',
        description: 'Lo que será tendencia',
        badge: 'HOT',
        endpoint: '/api/proyectar-exito'
    },
    {
        id: 'pronostico',
        name: 'Pronóstico Rating',
        icon: '⭐',
        color: 'from-yellow-400 to-amber-500',
        description: 'Ratings esperados',
        badge: '⭐ 8.5+',
        endpoint: '/api/pronostico-rating'
    },
    {
        id: 'mapa',
        name: 'Mapa de Nichos',
        icon: '🗺️',
        color: 'from-teal-500 to-emerald-600',
        description: 'Explora géneros',
        badge: '24 nichos',
        endpoint: '/api/mapa-nichos'
    },
    {
        id: 'adn',
        name: 'ADN de Contenido',
        icon: '🧬',
        color: 'from-purple-600 to-indigo-600',
        description: 'Análisis profundo',
        badge: 'IA',
        endpoint: '/api/animes?limit=10'
    },
    {
        id: 'joyas',
        name: 'Joyas Ocultas',
        icon: '💎',
        color: 'from-blue-600 to-cyan-500',
        description: 'Descubre tesoros',
        badge: '💎 Nuevo',
        endpoint: '/api/joyas-ocultas'
    }
];

function generateCards() {
    const container = document.getElementById('cards-container');
    
    sections.forEach(section => {
        const card = document.createElement('button');
        card.className = 'card relative group overflow-hidden rounded-xl bg-slate-900 border-2 border-slate-800 smooth-transition hover:scale-105 hover:-translate-y-1 hover:border-slate-700';
        card.setAttribute('data-section', section.id);
        card.onclick = () => handleSectionClick(section.id);
        
        card.innerHTML = `
            <div class="absolute inset-0 bg-gradient-to-br ${section.color} opacity-0 group-hover:opacity-20 smooth-transition"></div>
            <div class="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${section.color} opacity-30 blur-2xl group-hover:opacity-50 smooth-transition"></div>
            
            <div class="relative p-6">
                <div class="absolute top-4 right-4 px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r ${section.color} text-white badge-pulse">
                    ${section.badge}
                </div>
                
                <div class="w-16 h-16 rounded-2xl bg-gradient-to-br ${section.color} flex items-center justify-center mb-4 group-hover:scale-110 smooth-transition text-3xl hover-glow">
                    ${section.icon}
                </div>
                
                <h3 class="text-xl font-bold mb-2 text-white group-hover:text-transparent group-hover:bg-gradient-to-r group-hover:bg-clip-text group-hover:from-pink-400 group-hover:to-cyan-400 smooth-transition">
                    ${section.name}
                </h3>
                <p class="text-gray-400 text-sm">
                    ${section.description}
                </p>
                
                <div class="mt-4 flex items-center text-sm font-medium text-gray-500 group-hover:text-pink-400 smooth-transition">
                    Ver más
                    <span class="ml-2 group-hover:translate-x-1 smooth-transition">→</span>
                </div>
            </div>

            <div class="shine absolute inset-0 opacity-0 group-hover:opacity-100 smooth-transition pointer-events-none">
                <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full"></div>
            </div>
        `;
        
        container.appendChild(card);
    });
}

async function handleSectionClick(sectionId) {
    const section = sections.find(s => s.id === sectionId);
    
    document.querySelectorAll('.card').forEach(card => {
        card.classList.remove('active-card');
    });
    document.querySelector(`[data-section="${sectionId}"]`).classList.add('active-card');
    
    const display = document.getElementById('section-display');
    display.classList.remove('hidden');
    
    const iconEl = document.getElementById('section-icon');
    iconEl.className = `w-12 h-12 rounded-xl bg-gradient-to-br ${section.color} flex items-center justify-center text-2xl smooth-transition`;
    iconEl.textContent = section.icon;
    
    document.getElementById('section-title').textContent = section.name;
    document.getElementById('section-description').textContent = section.description;
    
    const contentEl = document.getElementById('section-content');
    contentEl.innerHTML = '<div class="flex justify-center"><div class="loading-spinner"></div></div>';
    
    display.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    try {
        const response = await fetch(section.endpoint);
        if (!response.ok) throw new Error('Error en la petición');
        
        const data = await response.json();
        displayContent(sectionId, data);
    } catch (error) {
        console.error('Error:', error);
        contentEl.innerHTML = '<p class="text-red-400 text-center">⚠️ No se pudo cargar los datos</p>';
    }
}

function displayContent(sectionId, data) {
    const contentEl = document.getElementById('section-content');
    
    switch(sectionId) {
        case 'mi-lista':
            displayAnimeList(data.animes || []);
            break;
        case 'proyectar':
            displayAnimeList(data.trending || []);
            break;
        case 'pronostico':
            displayAnimeList(data.high_rated || []);
            break;
        case 'mapa':
            displayGenres(data.genres || []);
            break;
        case 'adn':
            displayAnimeList(data.animes || []);
            break;
        case 'joyas':
            displayAnimeList(data.hidden_gems || []);
            break;
        default:
            contentEl.innerHTML = '<p class="text-center text-gray-400">Sin datos disponibles</p>';
    }
}

function displayAnimeList(animes) {
    const contentEl = document.getElementById('section-content');
    
    if (!animes || animes.length === 0) {
        contentEl.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📺</div>
                <h3 class="text-xl font-bold mb-2">No hay animes disponibles</h3>
                <p>Conecta tu archivo Parquet para ver los datos</p>
            </div>
        `;
        return;
    }
    
    const grid = document.createElement('div');
    grid.className = 'anime-grid';
    
    animes.forEach(anime => {
        const card = document.createElement('div');
        card.className = 'anime-card';
        
        const imageUrl = anime.image_url || anime.img_url || 'https://via.placeholder.com/200x250?text=No+Image';
        const title = anime.title || anime.name || 'Sin título';
        const score = anime.score || anime.rating || 'N/A';
        const genres = anime.genres || anime.genre || '';
        
        card.innerHTML = `
            <img src="${imageUrl}" alt="${title}" onerror="this.src='https://via.placeholder.com/200x250?text=No+Image'">
            <div class="p-4">
                <div class="anime-title">${title}</div>
                <div class="flex items-center justify-between mb-3">
                    <span class="anime-rating">⭐ ${score}</span>
                    ${anime.episodes ? `<span class="text-gray-400 text-sm">${anime.episodes} eps</span>` : ''}
                </div>
                ${genres ? `<div class="anime-genre">${genres.split(',')[0]}</div>` : ''}
            </div>
        `;
        
        grid.appendChild(card);
    });
    
    contentEl.innerHTML = '';
    contentEl.appendChild(grid);
}

function displayGenres(genres) {
    const contentEl = document.getElementById('section-content');
    
    if (!genres || genres.length === 0) {
        contentEl.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🗺️</div>
                <h3 class="text-xl font-bold mb-2">No hay géneros disponibles</h3>
            </div>
        `;
        return;
    }
    
    const list = document.createElement('div');
    list.className = 'genre-list';
    
    genres.forEach(genre => {
        const item = document.createElement('div');
        item.className = 'genre-item';
        item.textContent = genre;
        item.onclick = () => alert(`Próximamente: filtrar por ${genre}`);
        list.appendChild(item);
    });
    
    contentEl.innerHTML = '';
    contentEl.appendChild(list);
}

document.addEventListener('DOMContentLoaded', generateCards);